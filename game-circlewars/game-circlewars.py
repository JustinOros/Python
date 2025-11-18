#!/usr/bin/python3
# Description: circlewars - A Pygame written in Python.
# Usage: python3 game-circlewars.py
# Author: Justin Oros
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
pygame.display.set_caption("Circle Wars")  # <-- Renamed here

# Initially hide mouse cursor; will toggle visible when mouse active
pygame.mouse.set_visible(False)

# Define colors
BLUE = (0, 200, 255)
RED = (255, 0, 0)
DARK_GRAY = (50, 50, 50)
WHITE = (255, 255, 255)

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
GO_SOUND = load_sound("audio-go.wav")
FIRE_SOUND = load_sound("audio-playerfire.wav")
DIE_SOUND = load_sound("audio-playerdeath.wav")
LEVEL_UP_SOUND = load_sound("audio-levelup.wav")
ENEMY_DEATH_SOUND = load_sound("audio-enemydeath.wav")
EXPLOSION_SOUND = load_sound("audio-playerdeath.wav")

# Load background music (pygame.mixer.music)
if os.path.exists("audio-music.mp3"):
    try:
        pygame.mixer.music.load("audio-music.mp3")
    except Exception as e:
        print(f"Error loading background music: {e}")
else:
    print("Warning: audio-music.mp3 not found. Background music disabled.")

# Set font for score
font = pygame.font.SysFont(None, 30)

# Initialize the joystick (controller)
pygame.joystick.init()
controller = None
if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    controller.init()

# Draw glowing circle ONLY (no solid fill)
def draw_glow_circle(surf, center, radius, glow_color, glow_radius):
    glow_surface = pygame.Surface((radius*2 + glow_radius*2, radius*2 + glow_radius*2), pygame.SRCALPHA)
    max_glow = int(glow_radius * 0.6)
    for i in range(max_glow, 0, -1):
        alpha = int(255 * (i / max_glow) ** 2)
        pygame.draw.circle(
            glow_surface,
            glow_color + (alpha,),
            (radius + glow_radius, radius + glow_radius),
            radius + i,
            width=2
        )
    surf.blit(glow_surface, (center[0] - radius - glow_radius, center[1] - radius - glow_radius))

# Helper function for circle collision
def circles_collide(x1, y1, r1, x2, y2, r2):
    dist_sq = (x1 - x2)**2 + (y1 - y2)**2
    radius_sum_sq = (r1 + r2)**2
    return dist_sq <= radius_sum_sq

# Draw small white crosshair at given position
def draw_crosshair(surf, pos):
    size = 10
    color = WHITE
    x, y = pos
    pygame.draw.line(surf, color, (x - size // 2, y), (x + size // 2, y), 2)
    pygame.draw.line(surf, color, (x, y - size // 2), (x, y + size // 2), 2)

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
        center = (int(self.x + self.size // 2), int(self.y + self.size // 2))
        radius = self.size // 2
        draw_glow_circle(screen, center, radius, BLUE, glow_radius=10)

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
        center = (int(self.x + self.size // 2), int(self.y + self.size // 2))
        radius = self.size // 2
        pygame.draw.circle(screen, self.color, center, radius)

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
        center = (int(self.x + self.size // 2), int(self.y + self.size // 2))
        radius = self.size // 2
        draw_glow_circle(screen, center, radius, RED, glow_radius=10)

# Pause screen
def draw_pause_screen(paused_by_controller):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    pause_font = pygame.font.SysFont(None, 100)
    instruction_font = pygame.font.SysFont(None, 40)
    pause_text = pause_font.render("PAUSED", True, BLUE)

    if paused_by_controller:
        instruction = "Press START to resume or X to Exit."
    else:
        instruction = "Press ESC to resume or Q to Quit."

    instruction_text = instruction_font.render(instruction, True, BLUE)

    screen.blit(pause_text, (
        SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
        SCREEN_HEIGHT // 2 - pause_text.get_height() // 2 - 30
    ))
    screen.blit(instruction_text, (
        SCREEN_WIDTH // 2 - instruction_text.get_width() // 2,
        SCREEN_HEIGHT // 2 + 30
    ))

# Helper function to fire projectile toward target_pos or fallback to last direction
def fire_projectile(player, projectiles, target_pos=None):
    px = player.x + player.size // 2
    py = player.y + player.size // 2

    if target_pos is None:
        # fallback: use player.last_direction
        direction = player.direction if player.direction is not None else player.last_direction
        dir_x, dir_y = direction
    else:
        # Calculate normalized direction vector from player center to target_pos
        dir_x = target_pos[0] - px
        dir_y = target_pos[1] - py
        length = (dir_x ** 2 + dir_y ** 2) ** 0.5
        if length == 0:
            return  # no shooting if zero length vector
        dir_x /= length
        dir_y /= length

    projectile_start_x = px - PROJECTILE_SIZE // 2
    projectile_start_y = py - PROJECTILE_SIZE // 2
    projectiles.append(Projectile(projectile_start_x, projectile_start_y, (dir_x, dir_y)))

    if FIRE_SOUND:
        FIRE_SOUND.play()

# Intro screen
def intro_screen():
    # Start background music looping indefinitely if not already playing
    if not pygame.mixer.music.get_busy():
        try:
            pygame.mixer.music.play(-1)  # loop forever
        except Exception as e:
            print(f"Failed to play background music: {e}")

    title_font = pygame.font.SysFont(None, 150, bold=True)
    subtitle_font = pygame.font.SysFont(None, 50)
    waiting = True
    while waiting:
        screen.fill(DARK_GRAY)
        
        # Render the title text "CIRCLE WARS"
        title_text = title_font.render("CIRCLE WARS", True, BLUE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(title_text, title_rect)
        
        # Render the subtitle "Press any key to begin..."
        subtitle_text = subtitle_font.render("Press any key to begin...", True, BLUE)
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
        screen.blit(subtitle_text, subtitle_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.JOYBUTTONDOWN:
                waiting = False

        pygame.time.Clock().tick(60)

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
    controller_active = False  # Start assuming keyboard usage

    # Mouse activity tracking for cursor visibility and crosshair
    MOUSE_INACTIVE_TIMEOUT = 2000  # milliseconds
    last_mouse_move_time = 0
    mouse_active = False

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

            # Track input method for rumble control
            if event.type in [pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN]:
                controller_active = True
            elif event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                controller_active = False

            # Track mouse movement for cursor visibility
            if event.type == pygame.MOUSEMOTION:
                last_mouse_move_time = pygame.time.get_ticks()
                mouse_active = True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                    paused_by_controller = False
                elif paused and event.key == pygame.K_q:
                    running = False
                elif not paused and event.key == pygame.K_SPACE:
                    fire_projectile(player, projectiles)

            if event.type == pygame.JOYBUTTONDOWN:
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
                    if mouse_active:
                        fire_projectile(player, projectiles, pygame.mouse.get_pos())
                    else:
                        fire_projectile(player, projectiles)

        # Also check if keyboard movement keys are pressed, set controller_active to False
        if keys[pygame.K_w] or keys[pygame.K_a] or keys[pygame.K_s] or keys[pygame.K_d]:
            controller_active = False

        # Update mouse cursor visibility based on inactivity timeout
        current_time = pygame.time.get_ticks()
        if current_time - last_mouse_move_time > MOUSE_INACTIVE_TIMEOUT:
            mouse_active = False

        # HIDE the OS cursor ALWAYS to avoid overlap with crosshair
        pygame.mouse.set_visible(False)

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

            # Circle collision for player and enemy
            player_center = (player.x + player.size // 2, player.y + player.size // 2)
            enemy_center = (enemy.x + enemy.size // 2, enemy.y + enemy.size // 2)

            if circles_collide(player_center[0], player_center[1], player.size // 2,
                               enemy_center[0], enemy_center[1], enemy.size // 2):
                if not player_dead:
                    if DIE_SOUND:
                        DIE_SOUND.play()
                    rumble(duration=1000, strength=1.0)
                    player_dead = True
                    explosions.append(Explosion(player_center[0], player_center[1], color=BLUE))

            for projectile in projectiles[:]:
                projectile_center = (projectile.x + projectile.size // 2, projectile.y + projectile.size // 2)
                if circles_collide(enemy_center[0], enemy_center[1], enemy.size // 2,
                                   projectile_center[0], projectile_center[1], projectile.size // 2):
                    explosions.append(Explosion(enemy_center[0], enemy_center[1]))
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

        # Draw crosshair if mouse active
        if mouse_active:
            draw_crosshair(screen, pygame.mouse.get_pos())

        score_text = font.render(f"Score: {score}", True, BLUE)
        level_text = font.render(f"Level: {level}", True, BLUE)
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
    # Show it centered
    screen.fill(DARK_GRAY)
    text_surface = font_large.render(text, True, RED)
    screen.blit(text_surface, ((SCREEN_WIDTH - text_surface.get_width()) // 2,
                               (SCREEN_HEIGHT - text_surface.get_height()) // 2))
    pygame.display.flip()
    pygame.time.wait(4000)

if __name__ == "__main__":
    intro_screen()
    game()
    pygame.quit()

