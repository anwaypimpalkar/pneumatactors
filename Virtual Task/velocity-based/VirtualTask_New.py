import pygame
import math
import time

# Initialize pygame
pygame.init()

# Set up display
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pygame Environment")

# Set background color to black
screen.fill((0, 0, 0))

# Define colors
red = (255, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)
green = (0, 255, 0)

# Font for countdown
font = pygame.font.SysFont(None, 100)


def reset_sim():
    global center_y, sphere_velocity_y, sphere_grounded
    global left_block_rect, right_block_rect, left_velocity, right_velocity
    center_y = height // 2
    sphere_velocity_y = 0
    sphere_grounded = False
    left_block_rect.x = left_block_x
    right_block_rect.x = right_block_x
    left_velocity = 0
    right_velocity = 0
    for i in range(5, 0, -1):
        screen.fill((0, 0, 0))
        countdown_text = font.render(str(i), True, white)
        screen.blit(countdown_text, (width // 2 - 30, height // 2 - 50))
        pygame.display.flip()
        time.sleep(1)


# Calculate the center of the window and the radius (diameter = 100, so radius = 50)
center_x = width // 2
center_y = height // 2
radius = 50

# Block dimensions
block_width = 100
block_height = 200

# Initial distance between blocks
initial_distance = radius * 2 + block_width
block_move_speed = 2  # Slower speed for blocks

# Gravity constant
gravity = 0.05
sphere_velocity_y = 0  # Initial vertical velocity (no initial movement)
sphere_grounded = False  # Whether the sphere is on the ground (not falling)

# Spring constants and damping
spring_constant = 0.02  # Slower spring effect
damping = 0.9

# Calculate initial positions for the white blocks
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


# Function to detect collision between the red circle and white blocks
def check_collision(circle_center, radius, rect):
    closest_x = max(rect.left, min(circle_center[0], rect.right))
    closest_y = max(rect.top, min(circle_center[1], rect.bottom))
    distance_x = circle_center[0] - closest_x
    distance_y = circle_center[1] - closest_y
    distance = math.sqrt(distance_x**2 + distance_y**2)
    return distance < radius


# Display initial countdown
reset_sim()

# Event loop placeholder
running = True
while running:
    screen.fill((0, 0, 0))
    pygame.draw.circle(screen, red, (center_x, center_y), radius)

    if not sphere_grounded:
        sphere_velocity_y += gravity

    center_y += sphere_velocity_y

    if center_y >= height - radius:
        center_y = height - radius
        sphere_velocity_y = 0
        sphere_grounded = True

    if check_collision((center_x, center_y), radius, left_block_rect):
        sphere_velocity_y = 0
        sphere_grounded = True
        center_y = left_block_rect.top - radius

    if check_collision((center_x, center_y), radius, right_block_rect):
        sphere_velocity_y = 0
        sphere_grounded = True
        center_y = right_block_rect.top - radius

    pygame.draw.rect(screen, blue, left_block_rect)
    pygame.draw.rect(screen, green, right_block_rect)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP]:
        left_velocity += block_move_speed
        right_velocity -= block_move_speed

    # Spring behavior for left block
    left_displacement = left_block_rect.x - left_block_x
    left_force = -spring_constant * left_displacement
    left_velocity += left_force
    left_velocity *= damping
    left_block_rect.x += int(left_velocity)

    # Spring behavior for right block
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
