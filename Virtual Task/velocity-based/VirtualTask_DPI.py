import pygame
import pygame_gui
import math
import time
import csv


# Function to load variables from CSV
def load_config(filename="config copy.csv"):
    config = {}
    with open(filename, mode="r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            key, value = row
            try:
                config[key] = float(value) if "." in value else int(value)
            except ValueError:
                config[key] = value  # Keep as string if conversion fails
    return config


# Load configuration
config = load_config()

# DPI Scaling Factor (Increase for Higher Resolution)
dpi_scale = 1.5  # Set to 1.5, 2.0, etc., for higher DPI

# Initialize pygame
pygame.init()

# Set up display with scaling
width, height = int(config["width"] * dpi_scale), int(config["height"] * dpi_scale)
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pneumatactor Virtual Task")

# GUI Manager for Pygame
manager = pygame_gui.UIManager((width, height))

# Define colors
red = (255, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)
green = (0, 255, 0)

# Font for countdown with scaling
font = pygame.font.SysFont(None, int(100 * dpi_scale))

# Load variables from config and apply DPI scaling
ball_mass = config["ball_mass"]
friction_coefficient = config["friction_coefficient"]
normal_force_factor = config["normal_force_factor"]
countdown_timer = config["countdown_timer"]
radius = int(config["radius"] * dpi_scale)
block_width = int(config["block_width"] * dpi_scale)
block_height = int(config["block_height"] * dpi_scale)
initial_distance = radius * config["initial_distance_factor"] + block_width
block_move_speed = config["block_move_speed"] * dpi_scale  # Scale movement speed
gravity = config["gravity"]
spring_constant = config["spring_constant"] * dpi_scale  # Scale spring force
damping = config["damping"]
slider_granularity = 1000  # High granularity for fine control

slider_value = 0  # Global variable for slider value

# Create Slider UI in Pygame (with high granularity and scaling)
slider_rect = pygame.Rect(
    (int(250 * dpi_scale), int(550 * dpi_scale)),
    (int(300 * dpi_scale), int(20 * dpi_scale)),
)
slider = pygame_gui.elements.UIHorizontalSlider(
    relative_rect=slider_rect,
    start_value=0,
    value_range=(-slider_granularity, slider_granularity),  # Expanded range
    manager=manager,
)


# Function to reset simulation
def reset_sim():
    global center_y, sphere_velocity_y, sphere_grounded
    global left_block_rect, right_block_rect, left_velocity, right_velocity
    global collision_detected

    center_y = height // 2
    sphere_velocity_y = 0
    sphere_grounded = False
    left_block_rect.x = left_block_x
    right_block_rect.x = right_block_x
    left_velocity = 0
    right_velocity = 0
    collision_detected = False

    for i in range(countdown_timer, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = font.render(str(i), True, white)
        screen.blit(
            countdown_text,
            (width // 2 - int(30 * dpi_scale), height // 2 - int(50 * dpi_scale)),
        )
        pygame.display.flip()
        time.sleep(1)


# Calculate the center of the window
center_x = width // 2
center_y = height // 2

# Calculate initial positions for blocks
left_block_x = center_x - radius - block_width - int(initial_distance // 2)
right_block_x = center_x + radius + int(initial_distance // 2)

left_block_rect = pygame.Rect(
    left_block_x, center_y - block_height // 2, block_width, block_height
)
right_block_rect = pygame.Rect(
    right_block_x, center_y - block_height // 2, block_width, block_height
)

left_velocity = 0.0
right_velocity = 0.0
sphere_velocity_y = 0.0
sphere_grounded = False

collision_detected = False


# Function to handle user input from slider (Fix movement scaling)
def handle_input():
    global left_velocity, right_velocity, slider_value

    mapped_value = (slider_value / slider_granularity) * block_move_speed

    # Apply scaled movement (fix issue where rects stopped moving)
    left_velocity = mapped_value
    right_velocity = -mapped_value


# Display initial countdown
reset_sim()

clock = pygame.time.Clock()

# Event loop
running = True
while running:
    time_delta = clock.tick(60) / 1000.0

    screen.fill((0, 0, 0))
    pygame.draw.circle(screen, red, (center_x, center_y), radius)

    # Apply gravity
    if not sphere_grounded:
        sphere_velocity_y += gravity
    center_y += sphere_velocity_y

    # Apply user input to update block velocities
    slider_value = slider.get_current_value()
    handle_input()

    # Apply spring behavior (Fix movement scaling)
    left_displacement = left_block_rect.x - left_block_x
    left_force = -spring_constant * left_displacement
    left_velocity += left_force
    left_velocity *= damping
    left_block_rect.x += int(left_velocity)

    right_displacement = right_block_rect.x - right_block_x
    right_force = -spring_constant * right_displacement
    right_velocity += right_force
    right_velocity *= damping
    right_block_rect.x += int(right_velocity)

    # Prevent blocks from moving out of bounds
    if left_block_rect.left < 0:
        left_block_rect.left = 0
        left_velocity = 0
    if right_block_rect.right > width:
        right_block_rect.right = width
        right_velocity = 0

    pygame.draw.rect(screen, blue, left_block_rect)
    pygame.draw.rect(screen, green, right_block_rect)

    # Process pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                reset_sim()
        manager.process_events(event)

    # Update UI manager
    manager.update(time_delta)

    # Draw UI elements
    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
