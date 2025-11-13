#!/usr/bin/python3
# Description: Grogy vs TIE Fighters - A Star Wars-ish Pygame written in Python.
# Usage: python3 game-groguvstiefighters.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import pygame
import random
import math

pygame.init()
pygame.mixer.init()

info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Grogu TIE Fighters")
pygame.mouse.set_visible(False)

try:
    grogu_img = pygame.image.load("image-grogu.png")
    grogu_img = pygame.transform.scale(grogu_img, (60, 60))
except:
    grogu_img = None

try:
    tiefighter_img = pygame.image.load("image-tiefighter.png")
    tiefighter_img = pygame.transform.scale(tiefighter_img, (70, 70))
except:
    tiefighter_img = None

try:
    laser_sound = pygame.mixer.Sound("audio-laser.mp3")
except:
    laser_sound = None

try:
    explode_sound = pygame.mixer.Sound("audio-explode.mp3")
except:
    explode_sound = None

try:
    pygame.mixer.music.load("audio-music.mp3")
    pygame.mixer.music.play(-1)
except:
    print("audio-music.mp3 not found or failed to load")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (50, 150, 255)
RED = (255, 50, 50)
YELLOW = (255, 255, 100)
GREEN = (50, 255, 50)

clock = pygame.time.Clock()
FPS = 60

font_large = pygame.font.Font(None, 100)
font_small = pygame.font.Font(None, 40)
font_default = pygame.font.Font(None, 36)

class Player:
    def __init__(self):
        self.x = WIDTH // 4
        self.y = HEIGHT // 2
        self.radius = 30
        self.speed = 5
        self.color = BLUE
        self.lives = 3
    def move(self, keys):
        if keys[pygame.K_w] and self.y - self.radius > 0:
            self.y -= self.speed
        if keys[pygame.K_s] and self.y + self.radius < HEIGHT:
            self.y += self.speed
        if keys[pygame.K_a] and self.x - self.radius > 0:
            self.x -= self.speed
        if keys[pygame.K_d] and self.x + self.radius < WIDTH:
            self.x += self.speed
    def draw(self):
        if grogu_img:
            img_rect = grogu_img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(grogu_img, img_rect)
        else:
            pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

class Bullet:
    def __init__(self, x, y, direction, color=YELLOW):
        self.x = x
        self.y = y
        self.radius = 5
        self.speed = 35
        self.direction = direction
        self.color = color
    def update(self):
        self.x += self.speed * self.direction
    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
    def off_screen(self):
        return self.x < 0 or self.x > WIDTH

class Enemy:
    def __init__(self):
        self.x = WIDTH + 30
        self.y = random.randint(50, HEIGHT - 50)
        self.start_y = self.y
        self.radius = 35
        self.speed = WIDTH * 0.005
        self.color = RED
        self.shoot_cooldown = 0
        self.shoot_delay = random.randint(60, 120)
        self.oscillation_offset = random.uniform(0, 2*math.pi)
    def update(self):
        self.x -= self.speed
        self.shoot_cooldown += 1
        self.y = self.start_y + math.sin(pygame.time.get_ticks() * 0.003 + self.oscillation_offset) * 30
    def draw(self):
        if tiefighter_img:
            img_rect = tiefighter_img.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(tiefighter_img, img_rect)
        else:
            rect = pygame.Rect(int(self.x - self.radius), int(self.y - self.radius), self.radius * 2, self.radius * 2)
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), 5)
    def can_shoot(self):
        return self.shoot_cooldown >= self.shoot_delay
    def shoot(self):
        self.shoot_cooldown = 0
        self.shoot_delay = random.randint(60, 120)
        return Bullet(self.x - self.radius, self.y, -1, RED)
    def off_screen(self):
        return self.x < -self.radius * 2

class Explosion:
    def __init__(self, x, y, max_radius=50, color=YELLOW):
        self.x = x
        self.y = y
        self.radius = 1
        self.max_radius = max_radius
        self.color = color
        self.life = 10
    def update(self):
        self.radius += self.max_radius / self.life
        self.life -= 1
    def draw(self):
        alpha_surface = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        pygame.draw.circle(alpha_surface, (*self.color, int(255 * (self.life / 10))), (int(self.radius), int(self.radius)), int(self.radius))
        screen.blit(alpha_surface, (self.x - self.radius, self.y - self.radius))
    def done(self):
        return self.life <= 0

def show_start_screen():
    waiting = True
    while waiting:
        screen.fill(BLACK)
        title_text = font_large.render("BABY YODA vs TIE FIGHTERS", True, YELLOW)
        subtitle_text = font_small.render("Press any key to begin...", True, YELLOW)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, HEIGHT//2 - 80))
        screen.blit(subtitle_text, (WIDTH//2 - subtitle_text.get_width()//2, HEIGHT//2 + 40))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
        clock.tick(FPS)

show_start_screen()

player = Player()
player_bullets = []
enemy_bullets = []
enemies = []
explosions = []
score = 0
enemy_spawn_timer = 0
enemy_spawn_delay = 90
star_offset = 0

running = True
while running:
    clock.tick(FPS)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_ESCAPE, pygame.K_q]:
                running = False
            if event.key in [pygame.K_LALT, pygame.K_RALT, pygame.K_SPACE]:
                player_bullets.append(Bullet(player.x + player.radius, player.y, 1, YELLOW))
                if laser_sound:
                    laser_sound.play()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            player_bullets.append(Bullet(player.x + player.radius, player.y, 1, YELLOW))
            if laser_sound:
                laser_sound.play()

    keys = pygame.key.get_pressed()
    player.move(keys)

    enemy_spawn_timer += 1
    if enemy_spawn_timer >= enemy_spawn_delay:
        enemies.append(Enemy())
        enemy_spawn_timer = 0
        enemy_spawn_delay = random.randint(60, 120)

    for bullet in player_bullets[:]:
        bullet.update()
        if bullet.off_screen():
            player_bullets.remove(bullet)

    for enemy in enemies[:]:
        enemy.update()
        if enemy.can_shoot():
            enemy_bullets.append(enemy.shoot())
        if enemy.off_screen():
            enemies.remove(enemy)

    for bullet in enemy_bullets[:]:
        bullet.update()
        if bullet.off_screen():
            enemy_bullets.remove(bullet)

    for bullet in player_bullets[:]:
        for enemy in enemies[:]:
            dist = math.sqrt((bullet.x - enemy.x)**2 + (bullet.y - enemy.y)**2)
            if dist < bullet.radius + enemy.radius:
                if bullet in player_bullets:
                    player_bullets.remove(bullet)
                if enemy in enemies:
                    enemies.remove(enemy)
                    if explode_sound:
                        explode_sound.play()
                    explosions.append(Explosion(enemy.x, enemy.y, max_radius=50, color=YELLOW))
                score += 100
                break

    for bullet in enemy_bullets[:]:
        dist = math.sqrt((bullet.x - player.x)**2 + (bullet.y - player.y)**2)
        if dist < bullet.radius + player.radius:
            if bullet in enemy_bullets:
                enemy_bullets.remove(bullet)
            player.lives -= 1
            if explode_sound:
                explode_sound.play()
            explosions.append(Explosion(player.x, player.y, max_radius=60, color=RED))

    for enemy in enemies[:]:
        dist = math.sqrt((enemy.x - player.x)**2 + (enemy.y - player.y)**2)
        if dist < enemy.radius + player.radius:
            player.lives -= 1
            enemies.remove(enemy)
            if explode_sound:
                explode_sound.play()
            explosions.append(Explosion(player.x, player.y, max_radius=60, color=RED))

    explosions = [exp for exp in explosions if not exp.done()]
    for exp in explosions:
        exp.update()

    if player.lives <= 0:
        pygame.mixer.music.fadeout(2000)
        screen.fill(BLACK)
        game_over_text = font_default.render(f"GAME OVER!", True, YELLOW)
        score_text_display = font_default.render(f"Final Score: {score}", True, YELLOW)
        restart_text = font_default.render("Press R to Restart", True, YELLOW)
        screen.blit(game_over_text, (WIDTH//2 - 120, HEIGHT//2 - 60))
        screen.blit(score_text_display, (WIDTH//2 - 140, HEIGHT//2 - 10))
        screen.blit(restart_text, (WIDTH//2 - 150, HEIGHT//2 + 40))
        pygame.display.flip()
        start_time = pygame.time.get_ticks()
        waiting = True
        while waiting:
            current_time = pygame.time.get_ticks()
            if current_time - start_time > 3000:
                waiting = False
                running = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        try:
                            pygame.mixer.music.play(-1)
                        except:
                            pass
                        player = Player()
                        player_bullets = []
                        enemy_bullets = []
                        enemies = []
                        explosions = []
                        score = 0
                        enemy_spawn_timer = 0
                        star_offset = 0
                        waiting = False
                    elif event.key in [pygame.K_ESCAPE, pygame.K_q]:
                        waiting = False
                        running = False

    screen.fill(BLACK)
    star_offset -= 2
    if star_offset <= -WIDTH:
        star_offset = 0
    for i in range(100):
        x = ((i * 73) + star_offset) % WIDTH
        y = (i * 137) % HEIGHT
        pygame.draw.circle(screen, WHITE, (x, y), 1)

    player.draw()
    for bullet in player_bullets:
        bullet.draw()
    for bullet in enemy_bullets:
        bullet.draw()
    for enemy in enemies:
        enemy.draw()
    for exp in explosions:
        exp.draw()

    score_text = font_default.render(f"Score: {score}", True, WHITE)
    screen.blit(score_text, (10, HEIGHT - 50))
    lives_text = font_default.render(f"Lives: {player.lives}", True, WHITE)
    screen.blit(lives_text, (WIDTH - 150, HEIGHT - 50))
    pygame.display.flip()

pygame.quit()
