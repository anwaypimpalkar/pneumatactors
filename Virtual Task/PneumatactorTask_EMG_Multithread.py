import pygame
import pygame_gui
import math
import time
import csv
import threading
import platform
from scipy.signal import butter, filtfilt

if platform.system() == "Darwin":  # macOS
    from aardvark_api_mac.python.aardvark_py import *
elif platform.system() == "Windows":
    from aardvark_api_windows.python.aardvark_py import *
else:
    raise RuntimeError("Need to download OS-specific Aardvark API.")

import os
# Set QUARC DLL Path before importing Quanser modules
quarc_dll_path = r"C:\Program Files\Quanser\QUARC"
os.add_dll_directory(quarc_dll_path)
from quanser.hardware import HIL, HILError

import time
import numpy as np
import threading
from collections import deque

# Constants
BOARD_TYPE = "qpid_e"
BOARD_IDENTIFIER = "0"
FREQUENCY = 1e5  # Hz
INPUT_CHANNELS = np.array([1, 2], dtype=np.uint32)  # FLEXION_EMG (Ch 1), EXTENSION_EMG (Ch 2)

# Shared Data
latest_emg = np.zeros(len(INPUT_CHANNELS))  # Raw EMG
processed_emg = np.zeros(len(INPUT_CHANNELS))  # Filtered EMG
lock_emg = threading.Lock()
lock_processed = threading.Lock()
lock_i2c = threading.Lock()
lock = threading.Lock()
WINDOW_SIZE = 20  # Number of samples needed before filtering
emg_window_buffer = {ch: deque(maxlen=WINDOW_SIZE) for ch in range(len(INPUT_CHANNELS))}

def collect_emg_data():
    """Thread function to continuously collect EMG data."""
    global latest_emg
    period = 1.0 / FREQUENCY

    card = HIL()
    card.open(BOARD_TYPE, BOARD_IDENTIFIER)

    input_buffer = np.zeros(len(INPUT_CHANNELS), dtype=np.float64)

    try:
        while True:
            card.read_analog(INPUT_CHANNELS, len(INPUT_CHANNELS), input_buffer)
            with lock_emg:
                latest_emg[:] = input_buffer  # Update shared EMG array
            time.sleep(period)  # Maintain sampling rate
    except KeyboardInterrupt:
        print("EMG data collection stopped.")
    finally:
        if card.is_valid():
            card.close()
        print("DAQ device closed.")


def read_latest_emg():
    """Function to safely read the latest EMG data."""
    with lock_emg:
        return np.copy(latest_emg)  # Return a copy to prevent modification during read

def butter_lowpass_filter(data, cutoff=10, fs=1000, order=4):
    """Applies a low-pass Butterworth filter, ensuring sufficient input length."""
    if len(data) < (order * 3):  # filtfilt requires at least `3 * order` samples
        return np.mean(data) if len(data) > 0 else 0  # Return average if data exists, else 0
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def emg_processing_thread():
    """Thread function to process EMG data."""
    global processed_emg

    while True:
        with lock_emg:
            latest_read_emg = np.copy(latest_emg)

        # Process EMG (rectify + filter)
        for i, val in enumerate(latest_read_emg):
            emg_window_buffer[i].append(np.abs(val))

        if all(len(emg_window_buffer[i]) >= max(WINDOW_SIZE, 3 * 4) for i in range(len(INPUT_CHANNELS))):
            filtered_values = np.array([
                butter_lowpass_filter(list(emg_window_buffer[i]))[-1]  # Extract the latest filtered value
                for i in range(len(INPUT_CHANNELS))
            ])
            with lock_processed:
                processed_emg[:] = filtered_values  # Store processed EMG
        else:
            with lock_processed:
                processed_emg[:] = np.zeros(len(INPUT_CHANNELS))

        time.sleep(0.001)  # Small delay to allow updates

def i2c_control_thread():
    """Thread function for handling I2C communication."""
    global mapped_value

    while True:
        with lock_processed:
            flexion_emg = processed_emg[0]  # Read processed EMG safely

        mapped_value = map_range(flexion_emg, in_min=0, in_max=5, out_min=0, out_max=block_move_range)

        # Compute pump pressure
        left_display_x, right_display_x = handle_input()

        with lock_i2c:
            check_collision()  # Handles all I2C communication

        time.sleep(0.001)  # Adjust based on system latency


# Function to load variables from CSV
def load_config(filename="config.csv"):
    config = {}
    with open(filename, mode="r") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            key, value = row
            try:
                config[key] = float(value)  # Force numeric values to be float
            except ValueError:
                config[key] = value  # Keep as string if conversion fails
    return config

config = load_config()  # Load main config

# Function to load mapping config from CSV
def load_mapping_config(filename=config["map_file"]):
    mapping_config = {}
    with open(filename, mode="r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            key, value = row
            try:
                mapping_config[key] = float(
                    value
                )  # Ensure all numeric values are floats
            except ValueError:
                mapping_config[key] = value  # Keep as string if conversion fails
    return mapping_config

# Load configuration files
mapping_config = load_mapping_config()  # Load mapping config

# Initialize pygame
pygame.init()

# Load parameters from config
dpi_scale = config["dpi_scale"]
width, height = int(config["width"] * dpi_scale), int(config["height"] * dpi_scale)
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pneumatactor Virtual Task")

# GUI Manager
manager = pygame_gui.UIManager((width, height))

# Colors
red, white, blue, green, bluegrey = (
    (255, 0, 0),
    (255, 255, 255),
    (0, 0, 255),
    (0, 255, 0),
    (119, 136, 153),
)

# Font scaling from config
font = pygame.font.SysFont(None, int(config["font_scale"] * dpi_scale))

# Game parameters from config
radius = int(config["radius"] * dpi_scale)
block_width = int(config["block_width"] * dpi_scale)
block_height = int(config["block_height"] * dpi_scale)
initial_distance = radius * config["initial_distance_factor"] + block_width
block_move_range = config["block_move_range"] * dpi_scale
slider_granularity = config["slider_granularity"]
gravity = config["gravity"] * dpi_scale
speed_reduction_factor = config["speed_reduction_factor"]

# I2C and hardware control from config
VALVE_ADDRESS = int(config["VALVE_ADDRESS"])
PUMP_ADDRESS = int(config["PUMP_ADDRESS"])
I2C_BITRATE = int(config["I2C_BITRATE"])
pump_initial_offset = int(config["pump_initial_offset"])
collision_vibration = int(config["collision_vibration"])
collision_pressure = int(config["collision_pressure"])
collision_duration = float(config["collision_duration"])
object_broken_threshold = int(config["object_broken_threshold"])
success_range_low = int(config["success_range_low"])
success_range_high = int(config["success_range_high"])
success_duration_required = float(config["success_duration_required"])

# Initialize Aardvark Device
aardvark_handle = aa_open(0)

if aardvark_handle <= 0:
    print(f"Unable to open Aardvark device. Error code: {aardvark_handle}")
else:
    aa_configure(aardvark_handle, AA_CONFIG_SPI_I2C)
    aa_i2c_bitrate(aardvark_handle, I2C_BITRATE)
    aa_i2c_pullup(aardvark_handle, AA_I2C_PULLUP_BOTH)

intersect_state = False
game_paused = False
object_dropped = False
success_timer = 0
success_achieved = False
last_pump_value = -1
last_frequency_value = -1

# Initialize Pygame mixer for audio playback
pygame.mixer.init()

# Load sound effects
shatter_sound = pygame.mixer.Sound("audio/glass-shatter.mp3")
drop_sound = pygame.mixer.Sound("audio/glass-dropped.mp3")  # Load the drop sound

# Track if the object has been broken
object_broken = False

mapped_value =0 

# Slider UI
slider_rect = pygame.Rect(
    (int(250 * dpi_scale), int(550 * dpi_scale)),
    (int(300 * dpi_scale), int(20 * dpi_scale)),
)
slider = pygame_gui.elements.UIHorizontalSlider(
    relative_rect=slider_rect,
    start_value=0,
    value_range=(-slider_granularity, slider_granularity),
    manager=manager,
)

# Step 1: Compute block positions first
left_block_x = (width // 2) - radius - block_width - int(initial_distance // 2)
right_block_x = (width // 2) + radius + int(initial_distance // 2)

left_block_rect = pygame.Rect(
    left_block_x, (height // 2) - (block_height // 2), block_width, block_height
)
right_block_rect = pygame.Rect(
    right_block_x, (height // 2) - (block_height // 2), block_width, block_height
)

# Step 2: Set square/circle center_x
center_x = width // 2  # Keep X centered

# Step 3: Ensure square starts EXACTLY on top of blocks
center_y = left_block_rect.top - radius  # Align bottom of square with top of blocks

def map_range(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def handle_input():
    """Replaces slider input with real-time Flexion EMG mapping."""
    global mapped_value

    # Read latest EMG data
    flexion_emg = processed_emg[0]  # Fetch flexion & extension EMG

    # Map the EMG value [0,5] to slider range [-slider_granularity, slider_granularity]
    mapped_value = map_range(flexion_emg, in_min=0, in_max=5, out_min = 0, out_max= block_move_range)

    # Backend block positions (for calculations)
    left_block_rect.x = left_block_x + int(mapped_value)
    right_block_rect.x = right_block_x - int(mapped_value)

    # Prevent overlap in rendering by stopping at sphere’s edge
    left_visual_limit = center_x - radius  # Left sphere boundary
    right_visual_limit = center_x + radius  # Right sphere boundary

    # Ensure smooth positioning
    left_display_x = min(left_block_rect.x, left_visual_limit - block_width)
    right_display_x = max(right_block_rect.x, right_visual_limit)

    return left_display_x, right_display_x


# Function to send a number to a specific I2C address using an open Aardvark handle
def send_number_to_address(DEVICE_ADDRESS, number):
    global aardvark_handle  # Use the already opened Aardvark device

    if aardvark_handle <= 0:
        print("Aardvark device not open. Cannot send data.")
        return

    # Prepare the data to send
    data = array("B", [int(number)])

    # Write the data to the I2C device
    num_written = aa_i2c_write(aardvark_handle, DEVICE_ADDRESS, AA_I2C_NO_FLAGS, data)

    if num_written < 0:
        print(f"Error writing to {hex(DEVICE_ADDRESS)}. Error code: {num_written}")
    elif num_written != len(data):
        print(
            f"Partial write to {hex(DEVICE_ADDRESS)}. Expected {len(data)} bytes, wrote {num_written} bytes."
        )
    # else:
    #     print(f"Successfully sent {number} to address {hex(DEVICE_ADDRESS)}")


def check_collision():
    """Main function to check collision, adjust ball behavior, and send feedback signals."""
    global ball_velocity_y, intersect_state, last_pump_value, object_broken, game_paused

    # Calculate distances between the sphere edge and block inner edges
    distance_left, distance_right = calculate_distances()

    # Adjust ball behavior if blocks penetrate the sphere
    adjust_ball_velocity(distance_left, distance_right)

    # Compute and send the appropriate pump pressure
    handle_pump_pressure(distance_left)

    # Compute and send the appropriate vibration frequency
    handle_vibration_frequency(distance_left)

    # Handle collision effects
    handle_collision_feedback(distance_left, distance_right)

    # Handle object break conditions
    handle_object_break(distance_left, distance_right)


def calculate_distances():
    """Calculate the distances between the sphere edge and the inner edges of the blocks."""
    sphere_left_x = center_x - radius
    sphere_right_x = center_x + radius

    left_inner_edge_x = left_block_rect.right
    right_inner_edge_x = right_block_rect.left

    distance_left = sphere_left_x - left_inner_edge_x
    distance_right = right_inner_edge_x - sphere_right_x

    return distance_left, distance_right


def adjust_ball_velocity(distance_left, distance_right):
    """Slow down the ball based on penetration depth when blocks enter the sphere."""
    global ball_velocity_y

    if distance_left < 0 or distance_right < 0:
        penetration_depth = abs(min(distance_left, distance_right, 0))
        slow_factor = max(
            0.2, 1 - (penetration_depth / (radius / 2)) * speed_reduction_factor
        )
        ball_velocity_y *= slow_factor


def handle_pump_pressure(distance_left):
    """Compute and send the pump pressure using linear mapping, with integrated offset handling."""
    global last_pump_value

    # Retrieve mapping configuration values
    min_distance = config["min_distance_to_render_feedback"]
    max_distance = config["max_distance_to_render_feedback"]
    
    # Apply offset directly to the minimum pressure value
    min_pressure = mapping_config["force_to_pressure_min"] + mapping_config["pump_initial_offset"] + mapping_config["baseline_pressure_value"]
    max_pressure = mapping_config["force_to_pressure_max"] + mapping_config["pump_initial_offset"] + mapping_config["baseline_pressure_value"]

    if distance_left < 0:
        # Clamp the distance within the min/max range for mapping
        clamped_distance = max(min_distance, min(abs(distance_left), max_distance))

        # Linearly map the distance to the adjusted pressure range
        mapped_pressure = int(
            min_pressure
            + (max_pressure - min_pressure)
            * (clamped_distance - min_distance)
            / (max_distance - min_distance)
        )

        # Ensure the mapped pressure stays within a valid range (0-255)
        new_pump_value = min(mapped_pressure, 255)

        # Only send if the value has changed
        if new_pump_value != last_pump_value:
            # print(f"Sending pressure: {new_pump_value}")
            send_number_to_address(PUMP_ADDRESS, new_pump_value)
            last_pump_value = new_pump_value

    else:
        # Reset to baseline pressure when no force is applied
        baseline_pressure = int(mapping_config["baseline_pressure_value"])
        if last_pump_value != baseline_pressure:
            send_number_to_address(PUMP_ADDRESS, baseline_pressure)
            last_pump_value = baseline_pressure




def handle_vibration_frequency(distance_left):
    """Compute and send the vibration frequency using linear mapping, with integrated offset handling."""
    global last_frequency_value

    # Retrieve mapping configuration values
    min_distance = config["min_distance_to_render_feedback"]
    max_distance = config["max_distance_to_render_feedback"]

    # Apply offset directly to the minimum and maximum vibration values
    min_vibration = mapping_config["force_to_vibration_min"] + mapping_config["vibration_offset"]
    max_vibration = mapping_config["force_to_vibration_max"] + mapping_config["vibration_offset"]

    if distance_left < 0:
        # Clamp the distance within the min/max range for mapping
        clamped_distance = max(min_distance, min(abs(distance_left), max_distance))

        # Linearly map the distance to the adjusted vibration range
        mapped_vibration = int(
            min_vibration
            + (max_vibration - min_vibration)
            * (clamped_distance - min_distance)
            / (max_distance - min_distance)
        )

        # Ensure the mapped vibration is within the valid range [0, 100]
        new_frequency_value = min(mapped_vibration, 100)

        # Only send if the value has changed
        if new_frequency_value != last_frequency_value:
            send_number_to_address(VALVE_ADDRESS, new_frequency_value)
            last_frequency_value = new_frequency_value

    else:
        # Reset to 0 when no force is applied
        if last_frequency_value != 0:
            send_number_to_address(VALVE_ADDRESS, 0)
            last_frequency_value = 0



def handle_collision_feedback(distance_left, distance_right):
    """Handle collision detection and send vibration signals."""
    global intersect_state

    is_colliding = distance_left <= 0 or distance_right <= 0
    if is_colliding and not intersect_state:
        intersect_state = True
        print("Collision!")

        send_number_to_address(
            VALVE_ADDRESS, int(mapping_config["at_collision_vibration_value"])
        )
        send_number_to_address(
            PUMP_ADDRESS, int(mapping_config["at_collision_pressure_value"] + mapping_config["baseline_pressure_value"])
        )

        if int(mapping_config["at_collision_vibration_duration"]) != -1:
            threading.Timer(
                float(mapping_config["at_collision_vibration_duration"]),
                lambda: send_number_to_address(VALVE_ADDRESS, 0),
            ).start()

        if int(mapping_config["at_collision_pressure_duration"]) != -1:
            threading.Timer(
                float(mapping_config["at_collision_pressure_duration"]),
                lambda: send_number_to_address(PUMP_ADDRESS, mapping_config["baseline_pressure_value"]),
            ).start()

    elif not is_colliding:
        intersect_state = False


def handle_object_break(distance_left, distance_right):
    """Check if the object has broken and trigger necessary actions."""
    global object_broken, game_paused

    if not object_broken and (
        distance_left < int(config["object_broken_threshold"])
        or distance_right < int(config["object_broken_threshold"])
    ):
        print("Object Broken!")
        shatter_sound.play()
        object_broken = True
        game_paused = True
        reset_all_devices()


def check_success(time_delta):
    global success_timer, success_achieved, game_paused

    if success_achieved or game_paused:
        return  # Don't update if the game is already paused

    sphere_left_x = center_x - radius
    left_inner_edge_x = left_block_rect.right
    distance_left = sphere_left_x - left_inner_edge_x

    # Check if the object is within the success range
    if success_range_low <= distance_left <= success_range_high:
        success_timer += time_delta  # Increment timer
        if (
            success_timer >= success_duration_required
        ):  # If object stays in range for required duration
            print("Success!")
            success_achieved = True
            game_paused = True
            reset_all_devices()
    else:
        success_timer = 0  # Reset timer if condition is not met


def check_if_dropped():
    global object_dropped, game_paused

    object_top = center_y - radius  # Top edge of the object
    lowest_block_bottom = max(
        left_block_rect.bottom, right_block_rect.bottom
    )  # Lowest block bottom

    if not object_dropped and object_top > lowest_block_bottom:
        print("You dropped the object!")
        drop_sound.play()  # Play the drop sound once
        object_dropped = True  # Prevent multiple triggers
        game_paused = True  # Pause simulation
        reset_all_devices()  # Send 0 to all devices


def display_drop_message():
    message = "You dropped the object!"
    text_surface = font.render(message, True, white)
    text_width, text_height = text_surface.get_size()

    # Add padding around the text
    padding_x, padding_y = 20, 15
    box_width, box_height = text_width + 2 * padding_x, text_height + 2 * padding_y

    # Center the overlay
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2

    # Draw the box and outline
    overlay_rect = pygame.Rect(box_x, box_y, box_width, box_height)
    pygame.draw.rect(screen, (0, 0, 0), overlay_rect)  # Black background
    pygame.draw.rect(screen, white, overlay_rect, 5)  # White outline

    # Center the text inside the box
    text_rect = text_surface.get_rect(center=overlay_rect.center)
    screen.blit(text_surface, text_rect)


# Overlay function to show "You broke the object!"
def display_break_message():
    message = "You broke the object!"  # The text to display
    text_surface = font.render(message, True, white)
    text_width, text_height = text_surface.get_size()

    # Add padding around the text
    padding_x, padding_y = 20, 15  # Extra space around the text
    box_width, box_height = text_width + 2 * padding_x, text_height + 2 * padding_y

    # Center the overlay
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2

    # Draw the box and outline
    overlay_rect = pygame.Rect(box_x, box_y, box_width, box_height)
    pygame.draw.rect(screen, (0, 0, 0), overlay_rect)  # Black background
    pygame.draw.rect(screen, white, overlay_rect, 5)  # White outline

    # Center the text inside the box
    text_rect = text_surface.get_rect(center=overlay_rect.center)
    screen.blit(text_surface, text_rect)


def display_success_message():
    message = "Success!"
    text_surface = font.render(message, True, white)
    text_width, text_height = text_surface.get_size()

    # Add padding around the text
    padding_x, padding_y = 20, 15
    box_width, box_height = text_width + 2 * padding_x, text_height + 2 * padding_y

    # Center the overlay
    box_x = (width - box_width) // 2
    box_y = (height - box_height) // 2

    # Draw the box and outline
    overlay_rect = pygame.Rect(box_x, box_y, box_width, box_height)
    pygame.draw.rect(screen, (0, 0, 0), overlay_rect)  # Black background
    pygame.draw.rect(screen, white, overlay_rect, 5)  # White outline

    # Center the text inside the box
    text_rect = text_surface.get_rect(center=overlay_rect.center)
    screen.blit(text_surface, text_rect)


def reset_all_devices(baseline_pressure=True):
    """Send 0 to all relevant I2C addresses to reset devices, except keep baseline pressure."""
    global aardvark_handle

    if aardvark_handle <= 0:
        print("Aardvark device not open. Cannot reset devices.")
        return

    addresses = [VALVE_ADDRESS]  # Reset only the valve, not the pump baseline
    for addr in addresses:
        send_number_to_address(addr, 0)

    # Reset the pump to baseline instead of 0
    if baseline_pressure:
        send_number_to_address(PUMP_ADDRESS, mapping_config["baseline_pressure_value"])
        print("All devices reset (Pump at baseline pressure).")
    else:
        send_number_to_address(PUMP_ADDRESS, 0)
        print("All devices reset (Pump at 0).")


def reset_sim():
    global center_y, ball_velocity_y, left_block_rect, right_block_rect
    global intersect_state, object_broken, object_dropped, success_achieved
    global game_paused, mapped_value, success_timer

    center_y = left_block_rect.top - radius
    ball_velocity_y = 0
    intersect_state = False
    object_broken = False
    object_dropped = False
    success_achieved = False  # Reset success state
    game_paused = False  # Resume updates
    success_timer = 0  # Reset success timer
    mapped_value = 0
    slider.set_current_value(0)
    left_block_rect.x = left_block_x
    right_block_rect.x = right_block_x

    # Send the baseline pressure value at the start
    baseline_pressure = int(mapping_config["baseline_pressure_value"])
    send_number_to_address(PUMP_ADDRESS, baseline_pressure)
    last_pump_value = baseline_pressure  # Track last sent pump value

    for i in range(3, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = font.render(str(i), True, white)
        screen.blit(
            countdown_text,
            (width // 2 - int(30 * dpi_scale), height // 2 - int(50 * dpi_scale)),
        )
        pygame.display.flip()
        time.sleep(1)


def draw_glass_effect(surface, x, y, width, height):
    glass_color = (173, 216, 230)  # Light blue with transparency
    reflection_color = (
        255,
        255,
        255,
    )  # White for reflections

    glass_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    glass_surface.fill(glass_color)  # Fill the glass effect

    # Add diagonal reflections
    pygame.draw.polygon(
        glass_surface, reflection_color, [(0, 0), (width * 0.4, 0), (0, height * 0.4)]
    )
    pygame.draw.polygon(
        glass_surface,
        reflection_color,
        [(width, height), (width * 0.6, height), (width, height * 0.6)],
    )

    surface.blit(glass_surface, (x, y))  # Render onto main screen

# Initialize Threads
emg_thread = threading.Thread(target=collect_emg_data, daemon=True)
process_thread = threading.Thread(target=emg_processing_thread, daemon=True)
i2c_thread = threading.Thread(target=i2c_control_thread, daemon=True)

# Start simulation
reset_sim()
clock = pygame.time.Clock()
running = True

# Start Threads
emg_thread.start()
process_thread.start()
i2c_thread.start()

while running:
    time_delta = clock.tick(60) / 1000.0  # Limit FPS to 60

    screen.fill((0, 0, 0))  # Clear screen

    # Process events (quit, reset, etc.)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                reset_sim()
        manager.process_events(event)

    manager.update(time_delta)

    # Only update physics if the game isn't paused
    if not game_paused:
        # Apply gravity
        ball_velocity_y += gravity
        center_y += ball_velocity_y

        # Prevent ball from sinking below the ground
        if center_y >= height - radius:
            center_y = height - radius
            ball_velocity_y = 0

    # Draw either a square or a circle, depending on config
    if config["render_shape"] == "square":
        draw_glass_effect(screen, center_x - radius, center_y - radius, radius * 2, radius * 2)
    else:
        pygame.draw.circle(screen, red, (center_x, center_y), radius)

    # Retrieve latest block positions using processed EMG data
    left_display_x, right_display_x = handle_input()

    # Render block positions
    pygame.draw.rect(screen, bluegrey, (left_display_x, left_block_rect.y, block_width, block_height))
    pygame.draw.rect(screen, bluegrey, (right_display_x, right_block_rect.y, block_width, block_height))

    # Check for object drop or success
    check_if_dropped()
    if not game_paused:
        check_success(time_delta)

    # Display overlays if needed
    if success_achieved:
        display_success_message()
    if object_dropped:
        display_drop_message()
    if object_broken:
        display_break_message()

    # Draw UI
    manager.draw_ui(screen)
    pygame.display.flip()

# Cleanup before exiting
reset_all_devices(baseline_pressure=False)
if aardvark_handle > 0:
    aa_close(aardvark_handle)
    print("Aardvark device closed.")
pygame.quit()

