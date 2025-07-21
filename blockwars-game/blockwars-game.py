#!/usr/bin/python3
# Description: blockwars - A simple game written in Python.
# Usage: python3 blockwars.py
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
pygame.display.set_caption("Block Wars")

# Hide mouse cursor
pygame.mouse.set_visible(False)

# Define colors
NEON_BLUE = (0, 200, 255)
BLUE = (0, 200, 255)  # Player glow blue
RED = (255, 0, 0)
DARK_GRAY = (50, 50, 50)

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
        self.size = 20
        self.speed = 3  # Start speed will be set in game()
        self.direction = None

    def move(self, keys, joystick_axes):
        if joystick_axes[1] < -0.5:
            self.y -= self.speed
            self.direction = 'up'
        elif joystick_axes[1] > 0.5:
            self.y += self.speed
            self.direction = 'down'
        if joystick_axes[0] < -0.5:
            self.x -= self.speed
            self.direction = 'left'
        elif joystick_axes[0] > 0.5:
            self.x += self.speed
            self.direction = 'right'

        if keys[pygame.K_w]:
            self.y -= self.speed
            self.direction = 'up'
        if keys[pygame.K_s]:
            self.y += self.speed
            self.direction = 'down'
        if keys[pygame.K_a]:
            self.x -= self.speed
            self.direction = 'left'
        if keys[pygame.K_d]:
            self.x += self.speed
            self.direction = 'right'

        if self.x < 0:
            self.x = SCREEN_WIDTH - self.size
        elif self.x > SCREEN_WIDTH - self.size:
            self.x = 0
        if self.y < 0:
            self.y = SCREEN_HEIGHT - self.size
        elif self.y > SCREEN_HEIGHT - self.size:
            self.y = 0

    def draw(self):
        rect = pygame.Rect(self.x, self.y, self.size, self.size)
        draw_glow_rect(screen, rect, BLUE, glow_radius=10)

# Projectile class
class Projectile:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.size = 5
        self.color = BLUE
        self.speed = 15
        self.direction = direction

    def move(self):
        if self.direction == 'up':
            self.y -= self.speed
        elif self.direction == 'down':
            self.y += self.speed
        elif self.direction == 'left':
            self.x -= self.speed
        elif self.direction == 'right':
            self.x += self.speed

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.size, self.size))

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
            self.x = random.randint(0, SCREEN_WIDTH - 20)
            self.y = 0
        elif edge == "bottom":
            self.x = random.randint(0, SCREEN_WIDTH - 20)
            self.y = SCREEN_HEIGHT - 20
        elif edge == "left":
            self.x = 0
            self.y = random.randint(0, SCREEN_HEIGHT - 20)
        else:
            self.x = SCREEN_WIDTH - 20
            self.y = random.randint(0, SCREEN_HEIGHT - 20)
        self.size = 20
        self.speed = speed

    def move(self, player_x, player_y):
        if self.x < player_x:
            self.x += self.speed
        elif self.x > player_x:
            self.x -= self.speed
        if self.y < player_y:
            self.y += self.speed
        elif self.y > player_y:
            self.y -= self.speed

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
    controller_active = False

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
                    if player.direction:
                        projectiles.append(Projectile(player.x + player.size // 2, player.y + player.size // 2, player.direction))
                        if FIRE_SOUND:
                            FIRE_SOUND.play()
            if event.type == pygame.JOYBUTTONDOWN:
                controller_active = True
                if event.button == 7 or event.button == 6:
                    paused = not paused
                    paused_by_controller = True
                elif paused and event.button == 2:
                    running = False
                elif not paused and event.button == 0:
                    if player.direction:
                        projectiles.append(Projectile(player.x + player.size // 2, player.y + player.size // 2, player.direction))
                        if FIRE_SOUND:
                            FIRE_SOUND.play()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not paused and event.button == 1:
                    if player.direction:
                        projectiles.append(Projectile(player.x + player.size // 2, player.y + player.size // 2, player.direction))
                        if FIRE_SOUND:
                            FIRE_SOUND.play()

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
            if projectile.x < 0 or projectile.x > SCREEN_WIDTH or projectile.y < 0 or projectile.y > SCREEN_HEIGHT:
                projectiles.remove(projectile)

        for enemy in enemies[:]:
            enemy.move(player.x, player.y)
            enemy.draw()

            if pygame.Rect(player.x, player.y, player.size, player.size).colliderect(pygame.Rect(enemy.x, enemy.y, enemy.size, enemy.size)):
                if not player_dead:
                    if DIE_SOUND:
                        DIE_SOUND.play()
                    rumble(duration=1000, strength=1.0)
                    player_dead = True
                    explosions.append(Explosion(player.x + player.size // 2, player.y + player.size // 2, color=BLUE))

            for projectile in projectiles[:]:
                if pygame.Rect(enemy.x, enemy.y, enemy.size, enemy.size).colliderect(pygame.Rect(projectile.x, projectile.y, projectile.size, projectile.size)):
                    explosions.append(Explosion(enemy.x + enemy.size // 2, enemy.y + enemy.size // 2))
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
    neon_blue = (0, 200, 255)  # Same as player glow blue
    final_score_text = font_large.render(f"Final Score: {score}", True, neon_blue)
    screen.fill(DARK_GRAY)
    screen.blit(final_score_text, (SCREEN_WIDTH // 2 - final_score_text.get_width() // 2,
                                  SCREEN_HEIGHT // 2 - final_score_text.get_height() // 2))
    pygame.display.flip()
    time.sleep(2)


if __name__ == "__main__":
    game()

pygame.quit()

