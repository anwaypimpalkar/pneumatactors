import pygame
import math
import time

# Initialize pygame
pygame.init()

# Set up display
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pneumatactor Virtual Task")

# Set background color to black
screen.fill((0, 0, 0))

# Define colors
red = (255, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)
green = (0, 255, 0)

# Font for countdown
font = pygame.font.SysFont(None, 100)

# Ball physics parameters
ball_mass = 1.0
friction_coefficient = 0.8
normal_force_factor = 0.5

# Countdown timer variable
countdown_timer = 3


# Function to reset simulation
def reset_sim():
    global center_y, sphere_velocity_y, sphere_grounded
    global left_block_rect, right_block_rect, left_velocity, right_velocity
    global countdown_timer

    center_y = height // 2
    sphere_velocity_y = 0
    sphere_grounded = False
    left_block_rect.x = left_block_x
    right_block_rect.x = right_block_x
    left_velocity = 0
    right_velocity = 0

    for i in range(countdown_timer, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = font.render(str(i), True, white)
        screen.blit(countdown_text, (width // 2 - 30, height // 2 - 50))
        pygame.display.flip()
        time.sleep(1)


# Calculate the center of the window and the radius
center_x = width // 2
center_y = height // 2
radius = 50

# Block dimensions
block_width = 100
block_height = 200
initial_distance = radius * 1.5 + block_width
block_move_speed = 2

# Gravity constant
gravity = 0.001
sphere_velocity_y = 0
sphere_grounded = False

# Spring constants and damping
spring_constant = 0.02
damping = 0.9

# Calculate initial positions for blocks
left_block_x = center_x - radius - block_width - initial_distance // 2
right_block_x = center_x + radius + initial_distance // 2

left_block_rect = pygame.Rect(
    left_block_x, center_y - block_height // 2, block_width, block_height
)
right_block_rect = pygame.Rect(
    right_block_x, center_y - block_height // 2, block_width, block_height
)

left_velocity = 0
right_velocity = 0


# Function to check collision
def check_collision(circle_center, radius, rect):
    closest_x = max(rect.left, min(circle_center[0], rect.right))
    closest_y = max(rect.top, min(circle_center[1], rect.bottom))
    distance_x = circle_center[0] - closest_x
    distance_y = circle_center[1] - closest_y
    distance = math.sqrt(distance_x**2 + distance_y**2)
    return distance < radius


# Display initial countdown
reset_sim()

# Event loop
running = True
while running:
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
    if check_collision(
        (center_x, center_y), radius, left_block_rect
    ) or check_collision((center_x, center_y), radius, right_block_rect):
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

    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        left_velocity += block_move_speed
        right_velocity -= block_move_speed

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

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                reset_sim()

    pygame.display.flip()

pygame.quit()
