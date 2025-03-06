import pygame
import pygame_gui
import math
import time
import csv


# Function to load variables from CSV
def load_config(filename="config.csv"):
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

# Initialize pygame
pygame.init()

# Set up display
width, height = config["width"], config["height"]
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pneumatactor Virtual Task")

# GUI Manager for Pygame
manager = pygame_gui.UIManager((width, height))

# Define colors
red = (255, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)
green = (0, 255, 0)

# Font for countdown
font = pygame.font.SysFont(None, 100)

# Load variables from config
ball_mass = config["ball_mass"]
friction_coefficient = config["friction_coefficient"]
normal_force_factor = config["normal_force_factor"]
countdown_timer = config["countdown_timer"]
radius = config["radius"]
block_width = config["block_width"]
block_height = config["block_height"]
initial_distance = radius * config["initial_distance_factor"] + block_width
block_move_speed = config["block_move_speed"]
gravity = config["gravity"]
spring_constant = config["spring_constant"]
damping = config["damping"]
slider_granularity = 1000  # High granularity for fine control

slider_value = 0  # Global variable for slider value

# Create Slider UI in Pygame (with high granularity)
slider_rect = pygame.Rect((250, 550), (300, 20))  # Slider position
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
    global collision_detected  # Reset collision tracking

    center_y = height // 2
    sphere_velocity_y = 0
    sphere_grounded = False
    left_block_rect.x = left_block_x
    right_block_rect.x = right_block_x
    left_velocity = 0
    right_velocity = 0
    collision_detected = False  # Reset collision flag

    for i in range(countdown_timer, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = font.render(str(i), True, white)
        screen.blit(countdown_text, (width // 2 - 30, height // 2 - 50))
        pygame.display.flip()
        time.sleep(1)


# Calculate the center of the window
center_x = width // 2
center_y = height // 2

# Calculate initial positions for blocks
left_block_x = center_x - radius - block_width - initial_distance // 2
right_block_x = center_x + radius + initial_distance // 2

left_block_rect = pygame.Rect(
    left_block_x, center_y - block_height // 2, block_width, block_height
)
right_block_rect = pygame.Rect(
    right_block_x, center_y - block_height // 2, block_width, block_height
)

left_velocity = 0.0  # Keep as float for smoother movement
right_velocity = 0.0
sphere_velocity_y = 0.0
sphere_grounded = False

collision_detected = False  # Track if a collision is occurring


# Function to check collision and print distance to sphere walls
def check_collision(circle_center, radius, rect, is_left):
    global collision_detected  # Track state of collision

    # Sphere boundary x-coordinates
    sphere_left_x = circle_center[0] - radius
    sphere_right_x = circle_center[0] + radius

    # Inner edge of the block (depends on whether it's the left or right block)
    rect_inner_edge_x = rect.right if is_left else rect.left

    # Compute distance to sphere boundary
    if is_left:
        distance_to_sphere_wall = (
            sphere_left_x - rect_inner_edge_x
        )  # Left block distance
    else:
        distance_to_sphere_wall = (
            rect_inner_edge_x - sphere_right_x
        )  # Right block distance

    # Print distance (0 when touching)
    print(f"{distance_to_sphere_wall:.2f}")

    # Standard collision detection
    closest_x = max(rect.left, min(circle_center[0], rect.right))
    closest_y = max(rect.top, min(circle_center[1], rect.bottom))
    distance_x = circle_center[0] - closest_x
    distance_y = circle_center[1] - closest_y
    distance = math.sqrt(distance_x**2 + distance_y**2)

    is_colliding = distance < radius

    if is_colliding and not collision_detected:
        print("Collision!")  # Print only when first entering collision
        collision_detected = True  # Set flag so it doesn't print continuously
    elif not is_colliding:
        collision_detected = False  # Reset flag when leaving collision

    return is_colliding


# Function to handle user input from slider
def handle_input():
    global left_velocity, right_velocity, slider_value

    # Map slider range (-1000 to 1000) to movement range (-block_move_speed to block_move_speed)
    mapped_value = (slider_value / slider_granularity) * block_move_speed

    # Apply mapped movement with smooth scaling
    left_velocity += mapped_value
    right_velocity -= mapped_value


# Display initial countdown
reset_sim()

clock = pygame.time.Clock()

# Event loop
running = True
while running:
    time_delta = clock.tick(60) / 1000.0  # Frame rate

    screen.fill((0, 0, 0))
    pygame.draw.circle(screen, red, (center_x, center_y), radius)

    # Apply gravity
    if not sphere_grounded:
        sphere_velocity_y += gravity
    center_y += sphere_velocity_y

    # Collision detection with ground
    if center_y >= height - radius:
        center_y = height - radius
        sphere_velocity_y = 0
        sphere_grounded = True

    # Collision detection with blocks
    # Check collision and print distances
    is_colliding_left = check_collision(
        (center_x, center_y), radius, left_block_rect, is_left=True
    )
    is_colliding_right = check_collision(
        (center_x, center_y), radius, right_block_rect, is_left=False
    )

    if is_colliding_left or is_colliding_right:
        squeeze_distance = (left_block_rect.right - center_x + radius) + (
            center_x + radius - right_block_rect.left
        )
        normal_force = normal_force_factor * squeeze_distance
        friction_force = friction_coefficient * normal_force
        gravity_force = ball_mass * gravity

        if friction_force >= gravity_force:
            sphere_velocity_y = 0
        else:
            sphere_velocity_y += gravity

    pygame.draw.rect(screen, blue, left_block_rect)
    pygame.draw.rect(screen, green, right_block_rect)

    # Process pygame events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                reset_sim()
        manager.process_events(event)  # Pass events to UI manager

    # Update UI manager
    manager.update(time_delta)

    # Read slider value
    slider_value = slider.get_current_value()
    handle_input()

    # Apply spring behavior
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

    if left_block_rect.left < 0:
        left_block_rect.left = 0
        left_velocity = 0
    if right_block_rect.right > width:
        right_block_rect.right = width
        right_velocity = 0

    # Draw the UI elements
    manager.draw_ui(screen)

    pygame.display.flip()

pygame.quit()
