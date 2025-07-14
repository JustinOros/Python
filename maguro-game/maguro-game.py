import pygame
import random
import sys
import math

pygame.init()
pygame.mixer.init()
pygame.joystick.init()

pygame.mixer.music.load("audio_music.mp3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

pygame.display.set_caption("Cat Catcher")
clock = pygame.time.Clock()

wallpaper = pygame.image.load("wallpaper.jpg").convert()
wallpaper = pygame.transform.scale(wallpaper, (WIDTH, HEIGHT))

CAT_SIZE = [160, 160]
SUSHI_SIZE = (50, 50)
CLOUD_SIZE = (200, 120)
PETAL_SIZE = (30, 30)

cat_left_base = pygame.image.load("tuna-left.png").convert_alpha()
cat_right_base = pygame.image.load("tuna-right.png").convert_alpha()

cat_left = pygame.transform.smoothscale(cat_left_base, CAT_SIZE)
cat_right = pygame.transform.smoothscale(cat_right_base, CAT_SIZE)

sushi_imgs = []
for i in [1, 2, 4, 5]:
    img = pygame.image.load(f"sushi{i}.png").convert_alpha()
    img = pygame.transform.smoothscale(img, SUSHI_SIZE)
    sushi_imgs.append(img)

wasabi_img = pygame.image.load("sushi3.png").convert_alpha()
wasabi_img = pygame.transform.smoothscale(wasabi_img, SUSHI_SIZE)

cloud_base = pygame.image.load("cloud.png").convert_alpha()
cloud_img = pygame.transform.smoothscale(cloud_base, CLOUD_SIZE)

petal_base = pygame.image.load("petal.png").convert_alpha()
petal_img = pygame.transform.smoothscale(petal_base, PETAL_SIZE)
petal_img_flipped = pygame.transform.flip(petal_img, True, False)
petal_toggle = False

chomp_sound = pygame.mixer.Sound("audio_chomp.mp3")
meow_sound = pygame.mixer.Sound("audio_meow.mp3")

joystick = None
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

font = pygame.font.SysFont(None, 48)

cat_img = cat_right
cat_facing = "right"
cat_rect = cat_img.get_rect()
cat_rect.centerx = WIDTH // 2
cat_rect.bottom = HEIGHT

cat_speed = 14
score = 0
game_over = False
game_over_time = None
paused = False
pause_by_controller = False
sushi_fall_speed = 5
sushi_interval = 125
objects = []

clouds = []
cloud_spawn_interval = 4000
last_cloud_spawn = 0
cloud_speed_multiplier = 1.0

petals = []
petal_spawn_interval = 200
last_petal_spawn = 0
petal_fall_speed = 3
petal_speed_multiplier = 1.0

start_time = pygame.time.get_ticks()
speed_increase_time = start_time

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
    global score, objects, game_over, cat_rect, cat_img, cat_facing, game_over_time, paused, pause_by_controller
    global start_time, speed_increase_time, sushi_fall_speed, CAT_SIZE, cat_left, cat_right
    global clouds, last_cloud_spawn, cloud_speed_multiplier
    global petals, last_petal_spawn, petal_fall_speed, petal_speed_multiplier, petal_toggle
    score = 0
    objects = []
    game_over = False
    game_over_time = None
    paused = False
    pause_by_controller = False
    CAT_SIZE = [160, 160]
    cat_left = pygame.transform.smoothscale(cat_left_base, CAT_SIZE)
    cat_right = pygame.transform.smoothscale(cat_right_base, CAT_SIZE)
    cat_facing = "right"
    cat_img = cat_right
    cat_rect = cat_img.get_rect()
    cat_rect.centerx = WIDTH // 2
    cat_rect.bottom = HEIGHT
    sushi_fall_speed = 5
    clouds.clear()
    last_cloud_spawn = pygame.time.get_ticks() - 4000
    cloud_speed_multiplier = 1.0
    petals.clear()
    last_petal_spawn = pygame.time.get_ticks() - petal_spawn_interval
    petal_fall_speed = 3
    petal_speed_multiplier = 1.0
    petal_toggle = False
    start_time = pygame.time.get_ticks()
    speed_increase_time = start_time

def spawn_sushi():
    x = random.randint(50, WIDTH - 50)
    is_wasabi = random.random() < 0.1
    img = wasabi_img if is_wasabi else random.choice(sushi_imgs)
    rect = img.get_rect(midtop=(x, -40))
    objects.append({'img': img, 'rect': rect, 'wasabi': is_wasabi})

def spawn_cloud():
    y = 50
    direction = random.choice(["left_to_right", "right_to_left"])
    if direction == "left_to_right":
        x = -CLOUD_SIZE[0]
        speed = 1.5
    else:
        x = WIDTH + CLOUD_SIZE[0]
        speed = -1.5
    rect = cloud_img.get_rect(topleft=(x, y))
    phase = random.uniform(0, 2 * math.pi)
    clouds.append({'rect': rect, 'speed': speed, 'base_y': y, 'phase': phase})

def spawn_petal():
    global petal_toggle
    x = random.randint(0, WIDTH)
    y = -PETAL_SIZE[1]
    image = petal_img_flipped if petal_toggle else petal_img
    petal_toggle = not petal_toggle
    rect = image.get_rect(topleft=(x, y))
    horizontal_drift = random.uniform(-0.5, 0.5)
    phase = random.uniform(0, 2 * math.pi)
    spawn_time = pygame.time.get_ticks()
    petals.append({'rect': rect, 'drift': horizontal_drift, 'base_x': x, 'phase': phase, 'img': image, 'spawn_time': spawn_time})

reset_game()
last_spawn = pygame.time.get_ticks()

while True:
    dt = clock.tick(60)
    screen.blit(wallpaper, (0, 0))

    keys = pygame.key.get_pressed()
    move = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not game_over:
                    paused = not paused
                    pause_by_controller = False
                    if paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
            elif event.key == pygame.K_q:
                pygame.quit()
                sys.exit()
            elif game_over and not paused:
                reset_game()
        if joystick and event.type == pygame.JOYBUTTONDOWN:
            if event.button == 7 or event.button == 6:
                if not game_over:
                    paused = not paused
                    pause_by_controller = True
                    if paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
            elif paused and event.button == 2:
                pygame.quit()
                sys.exit()
            elif game_over and not paused:
                reset_game()

    if paused:
        draw_centered_text("PAUSED", (255, 255, 255))
        small_font = pygame.font.SysFont(None, 32)
        if pause_by_controller:
            instruction = small_font.render("Press START to resume or X to quit.", True, (255, 255, 255))
        else:
            instruction = small_font.render("Press ESC to resume or Q to quit.", True, (255, 255, 255))
        instr_rect = instruction.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
        screen.blit(instruction, instr_rect)
        pygame.display.flip()
        continue

    now = pygame.time.get_ticks()

    if now - speed_increase_time > 30000:
        sushi_fall_speed += 1
        cloud_speed_multiplier += 0.1
        petal_speed_multiplier += 0.1
        speed_increase_time = now

    if now - last_cloud_spawn > cloud_spawn_interval:
        spawn_cloud()
        last_cloud_spawn = now

    if now - last_petal_spawn > petal_spawn_interval:
        spawn_petal()
        last_petal_spawn = now

    for cloud in clouds[:]:
        cloud['rect'].x += cloud['speed'] * cloud_speed_multiplier
        time_seconds = now / 1000
        vertical_offset = 10 * math.sin(2 * math.pi * time_seconds + cloud['phase'])
        cloud['rect'].y = cloud['base_y'] + vertical_offset
        if cloud['speed'] > 0 and cloud['rect'].left > WIDTH:
            clouds.remove(cloud)
        elif cloud['speed'] < 0 and cloud['rect'].right < 0:
            clouds.remove(cloud)

    for petal in petals[:]:
        petal['rect'].y += petal_fall_speed * petal_speed_multiplier
        sway = 15 * math.sin(0.5 * now / 1000 + petal['phase'])
        time_since_spawn = (now - petal['spawn_time']) / 1000
        drift_speed = 0.5 * petal_speed_multiplier
        petal['rect'].x = petal['base_x'] + sway + petal['drift'] * petal_speed_multiplier + drift_speed * time_since_spawn * 60
        if petal['rect'].top > HEIGHT:
            petals.remove(petal)

    if not game_over:
        if keys[pygame.K_a]:
            move = -cat_speed
            cat_facing = "left"
        elif keys[pygame.K_d]:
            move = cat_speed
            cat_facing = "right"

        if joystick:
            axis = joystick.get_axis(0)
            if abs(axis) > 0.2:
                move = int(axis * cat_speed)
                cat_facing = "left" if axis < 0 else "right"

        cat_img = cat_left if cat_facing == "left" else cat_right

        cat_rect.x += move
        cat_rect.x = max(0, min(WIDTH - cat_rect.width, cat_rect.x))
        cat_rect.bottom = HEIGHT

        if now - last_spawn > sushi_interval:
            spawn_sushi()
            last_spawn = now

        tuna_mid_y = cat_rect.top + cat_rect.height // 2

        for obj in objects[:]:
            obj['rect'].y += sushi_fall_speed
            horizontal_overlap = obj['rect'].right > cat_rect.left and obj['rect'].left < cat_rect.right
            if horizontal_overlap and obj['rect'].bottom >= tuna_mid_y:
                if obj['wasabi']:
                    meow_sound.play()
                    game_over = True
                    game_over_time = None
                else:
                    score += 1
                    chomp_sound.play()
                    mid_x = cat_rect.centerx
                    CAT_SIZE[0] += 1
                    CAT_SIZE[1] += 1
                    cat_left = pygame.transform.smoothscale(cat_left_base, CAT_SIZE)
                    cat_right = pygame.transform.smoothscale(cat_right_base, CAT_SIZE)
                    cat_img = cat_left if cat_facing == "left" else cat_right
                    cat_rect = cat_img.get_rect()
                    cat_rect.centerx = mid_x
                    cat_rect.bottom = HEIGHT
                objects.remove(obj)
            elif obj['rect'].top > HEIGHT:
                objects.remove(obj)
    else:
        if game_over_time is None:
            game_over_time = now
        elif now - game_over_time >= 3000:
            pygame.quit()
            sys.exit()

    for cloud in clouds:
        screen.blit(cloud_img, cloud['rect'])

    for petal in petals:
        screen.blit(petal['img'], petal['rect'])

    screen.blit(cat_img, cat_rect)

    for obj in objects:
        screen.blit(obj['img'], obj['rect'])

    draw_text(f"Score: {score}", (10, 10))

    if game_over:
        draw_centered_multiline_text([f"Final Score: {score}", "Game Over!"], color=(255, 0, 0))

    pygame.display.flip()
