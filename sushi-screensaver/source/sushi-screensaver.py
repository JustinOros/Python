#!/usr/bin/env python3
# Description: Sushi Screensaver.
# Usage: python3 sushi-screensaver.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import pygame
import random
import os
import sys

# Initialize pygame modules
pygame.init()

# Get the current display size to create a fullscreen window
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
FPS = 60  # Frames per second

# Background color (black)
BG_COLOR = (0, 0, 0)

def load_sushi_images():
    """
    Loads sushi images from the local directory, scales them to 80x80 pixels,
    and returns them as a list of pygame Surfaces.
    """
    images = []
    for i in range(1, 6):  # sushi1.png to sushi5.png
        path = os.path.join(os.path.dirname(__file__), f"sushi{i}.png")
        if not os.path.exists(path):
            print(f"❌ Missing image: sushi{i}.png")
            sys.exit()  # Exit if any image is missing
        img = pygame.image.load(path).convert_alpha()  # Load image with transparency
        images.append(pygame.transform.scale(img, (80, 80)))  # Scale to double size (80x80)
    return images

class Sushi(pygame.sprite.Sprite):
    """
    A sushi sprite that falls from the top of the screen to the bottom
    at a random speed and resets its position once it moves off the bottom.
    """
    def __init__(self, images):
        super().__init__()
        self.images = images
        self.image = random.choice(self.images)  # Random sushi image
        self.rect = self.image.get_rect()
        # Start at a random horizontal position within the screen width
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        # Start slightly above the visible screen (random y between -100 and -40)
        self.rect.y = random.randint(-100, -40)
        self.speed = random.uniform(2, 5)  # Random falling speed

    def update(self):
        """
        Update sushi position by moving it downwards.
        When it moves off the bottom, reset to a new random position at the top.
        """
        self.rect.y += self.speed  # Move down by speed
        if self.rect.top > SCREEN_HEIGHT:  # If sushi is below the screen
            # Reset vertical position to top off-screen
            self.rect.y = random.randint(-100, -40)
            # Reset horizontal position randomly within screen width
            self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
            self.speed = random.uniform(2, 5)  # New random speed
            self.image = random.choice(self.images)  # Pick a new sushi image

# Create fullscreen window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Sushi Screensaver")
clock = pygame.time.Clock()  # Clock to control frame rate
pygame.mouse.set_visible(False) # Hide mouse cursor

# Load sushi images into a list
sushi_images = load_sushi_images()

# Create a group to hold multiple sushi sprites
sushi_group = pygame.sprite.Group()
for _ in range(30):  # Create 30 sushi sprites
    sushi_group.add(Sushi(sushi_images))

# Main loop to run the screensaver
running = True
while running:
    screen.fill(BG_COLOR)  # Fill screen with background color

    # Handle events like quit, key presses, and mouse clicks
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False  # Exit on window close
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False  # Exit on ESC key press
            # Other keys do nothing here, but could be handled if needed
        elif event.type == pygame.MOUSEBUTTONDOWN:
            running = False  # Exit on any mouse click

    sushi_group.update()  # Update all sushi positions
    sushi_group.draw(screen)  # Draw all sushi sprites on the screen

    pygame.display.flip()  # Update the full display surface to the screen
    clock.tick(FPS)  # Maintain the frame rate

pygame.quit()  # Clean up and close pygame

