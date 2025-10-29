#!/usr/bin/env python3
# Description: Tron Ares Screensaver.
# Usage: python3 screensaver-tron-ares.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import pygame
import sys
import os
import random

pygame.init()

info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Tron Disc")
pygame.mouse.set_visible(False)

try:
    pygame.mixer.music.load('screensaver-tron-ares-music.mp3')
    pygame.mixer.music.play(-1)
except pygame.error as e:
    print(f"Error loading screensaver-tron-ares-music.mp3: {e}")
    print("Continuing without music...")

try:
    wallpaper_original = pygame.image.load('screensaver-tron-ares-wallpaper.png')
except pygame.error as e:
    print(f"Error loading screensaver-tron-ares-wallpaper.png: {e}")
    pygame.quit()
    sys.exit()

try:
    disc_original = pygame.image.load('screensaver-tron-ares-disc.png')
    DISC_SIZE = 180
    disc_original = pygame.transform.scale(disc_original, (DISC_SIZE, DISC_SIZE))
except pygame.error as e:
    print(f"Error loading screensaver-tron-ares-disc.png: {e}")
    pygame.quit()
    sys.exit()

disc_x = SCREEN_WIDTH // 2
disc_y = SCREEN_HEIGHT // 2
disc_speed_x = 7
disc_speed_y = 7
disc_angle = 0
disc_rotation_speed = -2
base_speed = 5
max_speed = 15
deceleration = 0.05
breathing_time = 0
breathing_speed = 0.02
breathing_scale_min = 1.0
breathing_scale_max = 1.1
num_bars = 10
bar_width = SCREEN_WIDTH // num_bars
max_bar_height = int(SCREEN_HEIGHT * 0.25)
bar_heights = [random.randint(10, max_bar_height) for _ in range(num_bars)]
bar_targets = [random.randint(10, max_bar_height) for _ in range(num_bars)]
bar_speeds = [random.uniform(5, 15) for _ in range(num_bars)]

clock = pygame.time.Clock()
FPS = 60

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                running = False
    
    disc_x += disc_speed_x
    disc_y += disc_speed_y
    
    breathing_time += breathing_speed
    breathing_scale = breathing_scale_min + (breathing_scale_max - breathing_scale_min) * (0.5 + 0.5 * pygame.math.Vector2(1, 0).rotate(breathing_time * 180 / 3.14159).x)
    
    for i in range(num_bars):
        if abs(bar_heights[i] - bar_targets[i]) < 5:
            bar_targets[i] = random.randint(10, max_bar_height)
            bar_speeds[i] = random.uniform(5, 15)
        
        if bar_heights[i] < bar_targets[i]:
            bar_heights[i] = min(bar_heights[i] + bar_speeds[i], bar_targets[i])
        else:
            bar_heights[i] = max(bar_heights[i] - bar_speeds[i], bar_targets[i])
    
    current_speed = (disc_speed_x**2 + disc_speed_y**2)**0.5
    if current_speed > base_speed:
        speed_ratio = disc_speed_x / current_speed
        current_speed = max(base_speed, current_speed - deceleration)
        disc_speed_x = speed_ratio * current_speed
        disc_speed_y = ((current_speed**2 - disc_speed_x**2)**0.5) * (1 if disc_speed_y > 0 else -1)
    
    disc_angle += disc_rotation_speed
    if disc_angle >= 360:
        disc_angle -= 360
    
    if disc_x <= 0 or disc_x >= SCREEN_WIDTH - DISC_SIZE:
        disc_speed_x = -disc_speed_x
        disc_rotation_speed = -disc_rotation_speed
        disc_x = max(0, min(disc_x, SCREEN_WIDTH - DISC_SIZE))
        current_speed = (disc_speed_x**2 + disc_speed_y**2)**0.5
        speed_ratio_x = disc_speed_x / current_speed
        speed_ratio_y = disc_speed_y / current_speed
        disc_speed_x = speed_ratio_x * max_speed
        disc_speed_y = speed_ratio_y * max_speed
    
    if disc_y <= 0 or disc_y >= SCREEN_HEIGHT - DISC_SIZE:
        disc_speed_y = -disc_speed_y
        disc_rotation_speed = -disc_rotation_speed
        disc_y = max(0, min(disc_y, SCREEN_HEIGHT - DISC_SIZE))
        current_speed = (disc_speed_x**2 + disc_speed_y**2)**0.5
        speed_ratio_x = disc_speed_x / current_speed
        speed_ratio_y = disc_speed_y / current_speed
        disc_speed_x = speed_ratio_x * max_speed
        disc_speed_y = speed_ratio_y * max_speed
    
    scaled_width = int(SCREEN_WIDTH * breathing_scale)
    scaled_height = int(SCREEN_HEIGHT * breathing_scale)
    wallpaper = pygame.transform.scale(wallpaper_original, (scaled_width, scaled_height))
    wallpaper_x = (SCREEN_WIDTH - scaled_width) // 2
    wallpaper_y = (SCREEN_HEIGHT - scaled_height) // 2
    screen.blit(wallpaper, (wallpaper_x, wallpaper_y))
    
    for i in range(num_bars):
        bar_x = i * bar_width
        bar_y = SCREEN_HEIGHT - int(bar_heights[i])
        bar_height = int(bar_heights[i])
        
        bar_surface = pygame.Surface((bar_width, bar_height), pygame.SRCALPHA)
        
        for y in range(bar_height):
            alpha = int(255 * (1 - y / bar_height))
            color = (255, 0, 0, alpha)
            pygame.draw.line(bar_surface, color, (0, y), (bar_width - 2, y))
        
        screen.blit(bar_surface, (bar_x, bar_y))
    
    rotated_disc = pygame.transform.rotate(disc_original, disc_angle)
    rotated_rect = rotated_disc.get_rect(center=(disc_x + DISC_SIZE // 2, disc_y + DISC_SIZE // 2))
    screen.blit(rotated_disc, rotated_rect)
    
    pygame.display.flip()
    
    clock.tick(FPS)

pygame.quit()
sys.exit()
