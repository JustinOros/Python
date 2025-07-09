import pygame
import random
import os
import sys

# Initialize pygame
pygame.init()

# Get display size for fullscreen
SCREEN_WIDTH, SCREEN_HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
FPS = 60

# Colors
BG_COLOR = (0, 0, 0)  # Black background

# Load sushi images
def load_sushi_images():
    images = []
    for i in range(1, 6):  # sushi1.png to sushi5.png
        path = os.path.join(os.path.dirname(__file__), f"sushi{i}.png")
        if not os.path.exists(path):
            print(f"❌ Missing image: sushi{i}.png")
            sys.exit()
        img = pygame.image.load(path).convert_alpha()
        # Scale sushi images to 80x80 (double size)
        images.append(pygame.transform.scale(img, (80, 80)))
    return images

# Sushi sprite
class Sushi(pygame.sprite.Sprite):
    def __init__(self, images):
        super().__init__()
        self.images = images
        self.image = random.choice(self.images)
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = random.randint(-100, -40)
        self.speed = random.uniform(2, 5)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            self.rect.y = random.randint(-100, -40)
            self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
            self.speed = random.uniform(2, 5)
            self.image = random.choice(self.images)

# Setup fullscreen display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Sushi Screensaver")
clock = pygame.time.Clock()

# Load sushi images
sushi_images = load_sushi_images()

# Create sushi sprites
sushi_group = pygame.sprite.Group()
for _ in range(30):
    sushi_group.add(Sushi(sushi_images))

# Main loop
running = True
while running:
    screen.fill(BG_COLOR)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            else:
                # Optional: you can decide if any other key should exit or not
                pass
        elif event.type == pygame.MOUSEBUTTONDOWN:
            running = False

    sushi_group.update()
    sushi_group.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()

