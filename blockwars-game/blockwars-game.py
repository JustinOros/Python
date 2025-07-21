#!/usr/bin/python3
# Description: blockwars - A simple game written in Python.
# Usage: python3 blockwars-game.py
# Author: Justin Oros (improved by ChatGPT)
# Source: https://github.com/JustinOros

import pygame
import random
import time
import os

# Initialize pygame
pygame.init()

# Set up full-screen mode
SCREEN_WIDTH = pygame.display.Info().current_w
SCREEN_HEIGHT = pygame.display.Info().current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Block Wars")

# Hide mouse cursor
pygame.mouse.set_visible(False)

# Define colors
NEON_BLUE = (0, 200, 255)  # Used for UI text
BLUE = (0, 200, 255)       # Player glow blue (same as NEON_BLUE)
RED = (255, 0, 0)
DARK_GRAY = (50, 50, 50)

# Define constants
PLAYER_SIZE = 20
ENEMY_SIZE = 20
PROJECTILE_SIZE = 5

# Function to load sound safely
def load_sound(filename):
    if os.path.exists(filename):
        return pygame.mixer.Sound(filename)
    else:
        print(f"Warning: {filename} not found. Sound will be disabled.")
        return None

# Load sounds
GO_SOUND = load_sound("audio_go.wav")
FIRE_SOUND = load_sound("audio_playerfire.wav")
DIE_SOUND = load_sound("audio_playerdeath.wav")
LEVEL_UP_SOUND = load_sound("audio_levelup.wav")
ENEMY_DEATH_SOUND = load_sound("audio_enemydeath.wav")
EXPLOSION_SOUND = load_sound("explosion_sound.wav")

# Set font for score
font = pygame.font.SysFont(None, 30)

# Initialize the joystick (controller)
pygame.joystick.init()
controller = None
if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    controller.init()

# Draw glowing rectangle ONLY (no solid fill)
def draw_glow_rect(surf, rect, glow_color, glow_radius):
    glow_surface = pygame.Surface((rect.width + glow_radius*2, rect.height + glow_radius*2), pygame.SRCALPHA)
    max_glow = int(glow_radius * 0.6)
    for i in range(max_glow, 0, -1):
        alpha = int(255 * (i / max_glow) ** 2)
        glow_rect = pygame.Rect(
            glow_radius - i,
            glow_radius - i,
            rect.width + i * 2,
            rect.height + i * 2
        )
        pygame.draw.rect(
            glow_surface,
            glow_color + (alpha,),
            glow_rect,
            border_radius=3,
            width=2
        )
    surf.blit(glow_surface, (rect.x - glow_radius, rect.y - glow_radius))

# Player class
class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.size = PLAYER_SIZE
        self.speed = 3  # Will be set in game()
        self.direction = None  # Current movement direction vector (dx, dy)
        self.last_direction = (0, -1)  # Default facing up

    def move(self, keys, joystick_axes):
        move_x, move_y = 0, 0

        # Joystick input with deadzone
        axis_x = joystick_axes[0]
        axis_y = joystick_axes[1]
        deadzone = 0.3

        if abs(axis_x) > deadzone:
            move_x = self.speed * (1 if axis_x > 0 else -1)
        if abs(axis_y) > deadzone:
            move_y = self.speed * (1 if axis_y > 0 else -1)

        # Keyboard input only if joystick inactive this frame
        if move_x == 0 and move_y == 0:
            if keys[pygame.K_a]:
                move_x = -self.speed
            elif keys[pygame.K_d]:
                move_x = self.speed

            if keys[pygame.K_w]:
                move_y = -self.speed
            elif keys[pygame.K_s]:
                move_y = self.speed

        self.x += move_x
        self.y += move_y

        # Screen wrapping
        if self.x < 0:
            self.x = SCREEN_WIDTH - self.size
        elif self.x > SCREEN_WIDTH - self.size:
            self.x = 0
        if self.y < 0:
            self.y = SCREEN_HEIGHT - self.size
        elif self.y > SCREEN_HEIGHT - self.size:
            self.y = 0

        # Set current direction vector normalized to -1, 0, or 1 on each axis
        norm_dx = 0
        norm_dy = 0
        if move_x > 0:
            norm_dx = 1
        elif move_x < 0:
            norm_dx = -1
        if move_y > 0:
            norm_dy = 1
        elif move_y < 0:
            norm_dy = -1

        if norm_dx == 0 and norm_dy == 0:
            self.direction = None
        else:
            self.direction = (norm_dx, norm_dy)
            self.last_direction = self.direction  # Update last known direction

    def draw(self):
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        draw_glow_rect(screen, rect, BLUE, glow_radius=10)

# Projectile class
class Projectile:
    def __init__(self, x, y, direction_vector):
        self.x = x
        self.y = y
        self.size = PROJECTILE_SIZE
        self.color = BLUE
        self.speed = 15
        self.dir_x, self.dir_y = direction_vector

    def move(self):
        # Normalize direction so diagonal speed isn't faster
        length = (self.dir_x ** 2 + self.dir_y ** 2) ** 0.5
        if length == 0:
            return
        self.x += self.speed * self.dir_x / length
        self.y += self.speed * self.dir_y / length

    def draw(self):
        pygame.draw.rect(screen, self.color, (int(self.x), int(self.y), self.size, self.size))

# Explosion class
class Explosion:
    def __init__(self, x, y, color=RED):
        self.x = x
        self.y = y
        self.size = 50
        self.lifetime = 10
        self.color = color

    def draw(self):
        pygame.draw.circle(screen, self.color, (self.x, self.y), self.size)
        self.lifetime -= 1

    def is_alive(self):
        return self.lifetime > 0

# Enemy class
class Enemy:
    def __init__(self, speed):
        edge = random.choice(["top", "bottom", "left", "right"])
        if edge == "top":
            self.x = random.randint(0, SCREEN_WIDTH - ENEMY_SIZE)
            self.y = 0
        elif edge == "bottom":
            self.x = random.randint(0, SCREEN_WIDTH - ENEMY_SIZE)
            self.y = SCREEN_HEIGHT - ENEMY_SIZE
        elif edge == "left":
            self.x = 0
            self.y = random.randint(0, SCREEN_HEIGHT - ENEMY_SIZE)
        else:
            self.x = SCREEN_WIDTH - ENEMY_SIZE
            self.y = random.randint(0, SCREEN_HEIGHT - ENEMY_SIZE)
        self.size = ENEMY_SIZE
        self.speed = speed

    def move(self, player_x, player_y):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = max((dx ** 2 + dy ** 2) ** 0.5, 0.001)  # Avoid zero division
        self.x += self.speed * dx / dist
        self.y += self.speed * dy / dist

    def draw(self):
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        draw_glow_rect(screen, rect, RED, glow_radius=10)

# Pause screen
def draw_pause_screen(paused_by_controller):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pause_font = pygame.font.SysFont(None, 100)
    instruction_font = pygame.font.SysFont(None, 40)
    pause_text = pause_font.render("PAUSED", True, NEON_BLUE)

    if paused_by_controller:
        instruction = "Press START to resume or X to Exit."
    else:
        instruction = "Press ESC to resume or Q to Quit."

    instruction_text = instruction_font.render(instruction, True, NEON_BLUE)

    screen.blit(pause_text, (
        SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
        SCREEN_HEIGHT // 2 - pause_text.get_height() // 2 - 30
    ))
    screen.blit(instruction_text, (
        SCREEN_WIDTH // 2 - instruction_text.get_width() // 2,
        SCREEN_HEIGHT // 2 + 30
    ))

# Helper function to fire projectile
def fire_projectile(player, projectiles):
    # Use last_direction if no current direction
    direction = player.direction if player.direction is not None else player.last_direction
    if direction != (0, 0):
        px = player.x + player.size // 2 - PROJECTILE_SIZE // 2
        py = player.y + player.size // 2 - PROJECTILE_SIZE // 2
        projectiles.append(Projectile(px, py, direction))
        if FIRE_SOUND:
            FIRE_SOUND.play()

# Main game loop
def game():
    clock = pygame.time.Clock()
    player = Player()
    projectiles = []
    explosions = []
    level = 1
    score = 0
    enemy_speed = 2
    enemies = [Enemy(enemy_speed)]
    player.speed = enemy_speed + 1  # Player slightly faster than enemies
    running = True
    paused = False
    paused_by_controller = False
    player_dead = False
    controller_active = controller is not None  # Set active if controller connected

    def rumble(duration=300, strength=1.0):
        if controller_active and controller and hasattr(controller, "rumble"):
            try:
                controller.rumble(strength, strength, duration)
            except Exception as e:
                print(f"Rumble error: {e}")

    if GO_SOUND:
        GO_SOUND.play()

    while running:
        screen.fill(DARK_GRAY)
        keys = pygame.key.get_pressed()
        joystick_axes = [controller.get_axis(0), controller.get_axis(1)] if controller else [0, 0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                    paused_by_controller = False
                elif paused and event.key == pygame.K_q:
                    running = False
                elif not paused and event.key == pygame.K_SPACE:
                    fire_projectile(player, projectiles)

            if event.type == pygame.JOYBUTTONDOWN:
                controller_active = True  # Joystick input detected, activate rumble
                # Button mapping notes:
                # 7 or 6 = START buttons (pause/resume)
                # 2 = X button (quit when paused)
                # 0 = A button (fire projectile)
                if event.button == 7 or event.button == 6:
                    paused = not paused
                    paused_by_controller = True
                elif paused and event.button == 2:
                    running = False
                elif not paused and event.button == 0:
                    fire_projectile(player, projectiles)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if not paused and event.button == 1:  # Left mouse button
                    fire_projectile(player, projectiles)

        if paused:
            draw_pause_screen(paused_by_controller)
            pygame.display.flip()
            clock.tick(60)
            continue

        if player_dead:
            for explosion in explosions[:]:
                explosion.draw()
                if not explosion.is_alive():
                    explosions.remove(explosion)
            pygame.display.flip()
            clock.tick(60)
            if not explosions:
                show_final_score(score)
                running = False
            continue

        player.move(keys, joystick_axes)

        for projectile in projectiles[:]:
            projectile.move()
            projectile.draw()
            # Remove projectile if out of screen
            if (projectile.x < 0 or projectile.x > SCREEN_WIDTH or
                projectile.y < 0 or projectile.y > SCREEN_HEIGHT):
                projectiles.remove(projectile)

        for enemy in enemies[:]:
            enemy.move(player.x, player.y)
            enemy.draw()

            player_rect = pygame.Rect(player.x, player.y, player.size, player.size)
            enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.size, enemy.size)

            if player_rect.colliderect(enemy_rect):
                if not player_dead:
                    if DIE_SOUND:
                        DIE_SOUND.play()
                    rumble(duration=1000, strength=1.0)
                    player_dead = True
                    explosions.append(Explosion(player.x + player.size // 2,
                                                player.y + player.size // 2,
                                                color=BLUE))

            for projectile in projectiles[:]:
                projectile_rect = pygame.Rect(projectile.x, projectile.y, projectile.size, projectile.size)
                if enemy_rect.colliderect(projectile_rect):
                    explosions.append(Explosion(enemy.x + enemy.size // 2,
                                                enemy.y + enemy.size // 2))
                    if ENEMY_DEATH_SOUND:
                        ENEMY_DEATH_SOUND.play()
                    rumble(duration=150, strength=0.5)
                    enemies.remove(enemy)
                    projectiles.remove(projectile)
                    score += 100
                    break

        for explosion in explosions[:]:
            explosion.draw()
            if not explosion.is_alive():
                explosions.remove(explosion)

        if not enemies:
            level += 1
            if LEVEL_UP_SOUND:
                LEVEL_UP_SOUND.play()

            # Increase enemy speed every 2 levels, cap at 8
            if level % 2 == 0 and enemy_speed < 8:
                enemy_speed += 1

            player.speed = enemy_speed + 1  # Player stays slightly faster

            enemies = [Enemy(enemy_speed) for _ in range(level)]

        player.draw()

        score_text = font.render(f"Score: {score}", True, NEON_BLUE)
        level_text = font.render(f"Level: {level}", True, NEON_BLUE)
        screen.blit(score_text, (10, 10))
        screen.blit(level_text, (SCREEN_WIDTH - level_text.get_width() - 10, 10))

        pygame.display.flip()
        clock.tick(60)

# Show final score on death
def show_final_score(score):
    font_large = pygame.font.SysFont(None, 80)
    if score == 0:
        text = "GAME OVER"
    else:
        text = f"Final Score: {score}"
    final_score_text = font_large.render(text, True, RED)
    screen.fill(DARK_GRAY)
    screen.blit(final_score_text, (SCREEN_WIDTH // 2 - final_score_text.get_width() // 2,
                                  SCREEN_HEIGHT // 2 - final_score_text.get_height() // 2))
    pygame.display.flip()

    # Instead of time.sleep (which blocks), wait for 2 seconds with event handling
    wait_start = pygame.time.get_ticks()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                waiting = False
            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
        if pygame.time.get_ticks() - wait_start > 2000:
            waiting = False
        pygame.time.Clock().tick(30)

if __name__ == "__main__":
    game()

pygame.quit()

