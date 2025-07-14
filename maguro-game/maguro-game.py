import pygame
import random
import sys

pygame.init()
pygame.joystick.init()

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

pygame.display.set_caption("Cat Catcher")
clock = pygame.time.Clock()

CAT_SIZE = (160, 160)
SUSHI_SIZE = (50, 50)

cat_left = pygame.image.load("tuna-left.png").convert_alpha()
cat_left = pygame.transform.smoothscale(cat_left, CAT_SIZE)

cat_right = pygame.image.load("tuna-right.png").convert_alpha()
cat_right = pygame.transform.smoothscale(cat_right, CAT_SIZE)

sushi_imgs = []
for i in [1, 2, 4, 5]:
    img = pygame.image.load(f"sushi{i}.png").convert_alpha()
    img = pygame.transform.smoothscale(img, SUSHI_SIZE)
    sushi_imgs.append(img)

wasabi_img = pygame.image.load("sushi3.png").convert_alpha()
wasabi_img = pygame.transform.smoothscale(wasabi_img, SUSHI_SIZE)

joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

font = pygame.font.SysFont(None, 48)

cat_img = cat_right
cat_rect = cat_img.get_rect()
cat_rect.centerx = WIDTH // 2
cat_rect.bottom = HEIGHT + 30

cat_speed = 14
score = 0
game_over = False
game_over_time = None
paused = False
exploding = False
explode_start = None
sushi_fall_speed = 5
sushi_interval = 125
objects = []

def draw_text(text, pos, color=(255, 255, 255)):
    surf = font.render(text, True, color)
    screen.blit(surf, pos)

def draw_centered_text(text, color=(255, 255, 255)):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(surf, rect)

def draw_centered_multiline_text(lines, color=(255,255,255), line_spacing=10):
    total_height = 0
    rendered_lines = []
    for line in lines:
        surf = font.render(line, True, color)
        rendered_lines.append(surf)
        total_height += surf.get_height() + line_spacing
    total_height -= line_spacing

    y = (HEIGHT - total_height) // 2
    for surf in rendered_lines:
        rect = surf.get_rect(center=(WIDTH // 2, y + surf.get_height() // 2))
        screen.blit(surf, rect)
        y += surf.get_height() + line_spacing

def reset_game():
    global score, objects, game_over, cat_rect, cat_img, game_over_time, paused, exploding, explode_start
    score = 0
    objects = []
    game_over = False
    game_over_time = None
    paused = False
    exploding = False
    explode_start = None
    cat_rect.centerx = WIDTH // 2
    cat_rect.bottom = HEIGHT + 30
    cat_img = cat_right

def spawn_sushi():
    x = random.randint(50, WIDTH - 50)
    is_wasabi = random.random() < 0.1
    img = wasabi_img if is_wasabi else random.choice(sushi_imgs)
    rect = img.get_rect(midtop=(x, -40))
    objects.append({'img': img, 'rect': rect, 'wasabi': is_wasabi})

reset_game()
last_spawn = pygame.time.get_ticks()

while True:
    dt = clock.tick(60)
    screen.fill((30, 30, 30))

    keys = pygame.key.get_pressed()
    move = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not exploding and not game_over:
                    paused = not paused
            elif event.key == pygame.K_q:
                pygame.quit()
                sys.exit()
            elif game_over and not paused:
                reset_game()
        if joystick and event.type == pygame.JOYBUTTONDOWN:
            if event.button == 7 or event.button == 6:
                if not exploding and not game_over:
                    paused = not paused
            elif paused and event.button == 2:
                pygame.quit()
                sys.exit()
            elif game_over and not paused:
                reset_game()

    if paused:
        draw_centered_text("PAUSED", (255, 255, 0))
        pygame.display.flip()
        continue

    now = pygame.time.get_ticks()

    if exploding:
        explosion_radius = 100
        explosion_center = cat_rect.center
        pygame.draw.circle(screen, (255, 0, 0), explosion_center, explosion_radius)
        if explode_start is None:
            explode_start = now
        elif now - explode_start >= 1000:
            exploding = False
            game_over = True
            game_over_time = None
    elif not game_over:
        if keys[pygame.K_a]:
            move = -cat_speed
            cat_img = cat_left
        elif keys[pygame.K_d]:
            move = cat_speed
            cat_img = cat_right

        if joystick:
            axis = joystick.get_axis(0)
            if abs(axis) > 0.2:
                move = int(axis * cat_speed)
                cat_img = cat_left if axis < 0 else cat_right

        cat_rect.x += move
        cat_rect.x = max(0, min(WIDTH - cat_rect.width, cat_rect.x))
        cat_rect.bottom = HEIGHT + 30

        if now - last_spawn > sushi_interval:
            spawn_sushi()
            last_spawn = now

        tuna_mid_y = cat_rect.top + cat_rect.height // 2

        for obj in objects[:]:
            obj['rect'].y += sushi_fall_speed

            horizontal_overlap = obj['rect'].right > cat_rect.left and obj['rect'].left < cat_rect.right

            if horizontal_overlap and obj['rect'].bottom >= tuna_mid_y:
                if obj['wasabi']:
                    exploding = True
                    explode_start = None
                else:
                    score += 1
                objects.remove(obj)

            elif obj['rect'].top > HEIGHT:
                objects.remove(obj)

    else:
        if game_over_time is None:
            game_over_time = now
        elif now - game_over_time >= 3000:
            pygame.quit()
            sys.exit()

    if not exploding:
        screen.blit(cat_img, cat_rect)

    for obj in objects:
        screen.blit(obj['img'], obj['rect'])

    draw_text(f"Score: {score}", (10, 10))

    if game_over:
        draw_centered_multiline_text([f"Final Score: {score}", "Game Over!"], color=(255, 0, 0))

    pygame.display.flip()

