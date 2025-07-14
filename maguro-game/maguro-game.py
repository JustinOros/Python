import pygame
import random
import sys
import math

pygame.init()
pygame.mixer.init()
pygame.joystick.init()

# Constants
WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
SCREEN_SIZE = (WIDTH, HEIGHT)
CAT_INITIAL_SIZE = [160, 160]
CAT_MAX_SIZE = [320, 320]
SUSHI_SIZE = (50, 50)
CLOUD_SIZE = (200, 120)
PETAL_SIZE = (30, 30)
GAME_OVER_DELAY = 3000  # ms
WASABI_CHANCE = 0.1

# Helper Functions
def quit_game():
    pygame.quit()
    sys.exit()


class Cat:
    def __init__(self, cat_right_img, pos, speed):
        self.cat_right_base = cat_right_img  # Only right-facing base image
        self.size = CAT_INITIAL_SIZE.copy()
        self.speed = speed
        self.facing = "right"
        # Prepare the right-facing scaled image
        self.image_right = pygame.transform.smoothscale(self.cat_right_base, self.size)
        # Prepare flipped left-facing image
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_right
        self.rect = self.image.get_rect()
        self.rect.centerx, self.rect.bottom = pos
        self.grow_step = 1

    def update_image(self):
        if self.facing == "left":
            # Flip the right image horizontally to face left
            self.image = pygame.transform.flip(self.image_right, True, False)
        else:
            self.image = self.image_right

    def move(self, dx):
        self.rect.x += dx * self.speed
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))
        self.rect.bottom = HEIGHT

    def grow(self):
        # Increase size but clamp
        self.size[0] = min(self.size[0] + self.grow_step, CAT_MAX_SIZE[0])
        self.size[1] = min(self.size[1] + self.grow_step, CAT_MAX_SIZE[1])
        self.image_right = pygame.transform.smoothscale(self.cat_right_base, self.size)
        self.update_image()
        # Reset rect to bottom center
        mid_x = self.rect.centerx
        self.rect = self.image.get_rect()
        self.rect.centerx = mid_x
        self.rect.bottom = HEIGHT

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Sushi:
    def __init__(self, image, pos, wasabi=False, speed=5):
        self.image = image
        self.rect = self.image.get_rect(midtop=pos)
        self.wasabi = wasabi
        self.speed = speed

    def update(self, dt):
        self.rect.y += self.speed * dt / 16.67

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def off_screen(self):
        return self.rect.top > HEIGHT


class Cloud:
    def __init__(self, image, speed_multiplier=1.0):
        self.image = image
        self.speed_multiplier = speed_multiplier
        self.size = self.image.get_size()
        self.y = 50
        self.phase = random.uniform(0, 2 * math.pi)
        self.speed = random.choice([-1.5, 1.5]) * speed_multiplier
        if self.speed > 0:
            self.rect = self.image.get_rect(topleft=(-self.size[0], self.y))
        else:
            self.rect = self.image.get_rect(topleft=(WIDTH + self.size[0], self.y))
        self.base_y = self.y

    def update(self, dt, now):
        self.rect.x += self.speed * dt / 16.67
        vertical_offset = 10 * math.sin(2 * math.pi * now / 1000 + self.phase)
        self.rect.y = self.base_y + vertical_offset

    def off_screen(self):
        if self.speed > 0:
            return self.rect.left > WIDTH
        else:
            return self.rect.right < 0

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Petal:
    def __init__(self, image, pos, petal_toggle, speed_multiplier=1.0):
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)
        self.speed_multiplier = speed_multiplier
        self.drift = random.uniform(-0.5, 0.5)
        self.phase = random.uniform(0, 2 * math.pi)
        self.base_x = pos[0]
        self.spawn_time = pygame.time.get_ticks()
        self.petal_toggle = petal_toggle

    def update(self, dt, now):
        self.rect.y += 3 * self.speed_multiplier * dt / 16.67
        sway = 15 * math.sin(0.5 * now / 1000 + self.phase)
        time_since_spawn = (now - self.spawn_time) / 1000
        drift_speed = 0.5 * self.speed_multiplier
        self.rect.x = self.base_x + sway + self.drift * self.speed_multiplier + drift_speed * time_since_spawn * 60

    def off_screen(self):
        return self.rect.top > HEIGHT

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Spawner:
    def __init__(self, spawn_interval_ms):
        self.spawn_interval = spawn_interval_ms
        self.last_spawn = 0

    def can_spawn(self, now):
        return now - self.last_spawn > self.spawn_interval

    def update_spawn_time(self, now):
        self.last_spawn = now


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode(SCREEN_SIZE, pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        pygame.display.set_caption("Maguro!")

        # Load assets
        self.wallpaper = pygame.image.load("wallpaper.jpg").convert()
        self.wallpaper = pygame.transform.scale(self.wallpaper, SCREEN_SIZE)

        # Only load the right-facing cat image
        self.cat_right_base = pygame.image.load("cat.png").convert_alpha()

        self.sushi_images = []
        for i in [1, 2, 4, 5]:
            img = pygame.image.load(f"sushi{i}.png").convert_alpha()
            img = pygame.transform.smoothscale(img, SUSHI_SIZE)
            self.sushi_images.append(img)
        self.wasabi_img = pygame.image.load("sushi3.png").convert_alpha()
        self.wasabi_img = pygame.transform.smoothscale(self.wasabi_img, SUSHI_SIZE)

        self.cloud_base = pygame.image.load("cloud.png").convert_alpha()
        self.cloud_img = pygame.transform.smoothscale(self.cloud_base, CLOUD_SIZE)

        self.petal_base = pygame.image.load("petal.png").convert_alpha()
        self.petal_img = pygame.transform.smoothscale(self.petal_base, PETAL_SIZE)
        self.petal_img_flipped = pygame.transform.flip(self.petal_img, True, False)

        # Sounds
        pygame.mixer.music.load("audio_music.mp3")
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        self.chomp_sound = pygame.mixer.Sound("audio_chomp.mp3")
        self.meow_sound = pygame.mixer.Sound("audio_meow.mp3")

        # Joystick
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

        # Game entities
        self.cat = Cat(self.cat_right_base, (WIDTH // 2, HEIGHT), 14)
        self.sushis = []
        self.clouds = []
        self.petals = []
        self.petal_toggle = False

        # Spawners
        self.sushi_spawner = Spawner(125)
        self.cloud_spawner = Spawner(4000)
        self.petal_spawner = Spawner(200)

        self.score = 0
        self.game_over = False
        self.game_over_time = None
        self.paused = False
        self.pause_by_controller = False

        self.sushi_fall_speed = 5
        self.cloud_speed_multiplier = 1.0
        self.petal_speed_multiplier = 1.0

        self.font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 32)

        self.clock = pygame.time.Clock()
        self.speed_increase_time = pygame.time.get_ticks()

    def draw_text(self, text, pos, color=(255, 255, 255)):
        surf = self.font.render(text, True, color)
        self.screen.blit(surf, pos)

    def draw_centered_text(self, text, color=(255, 255, 255)):
        surf = self.font.render(text, True, color)
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(surf, rect)

    def draw_centered_multiline_text(self, lines, color=(255, 255, 255), line_spacing=10):
        total_height = 0
        rendered_lines = []
        for line in lines:
            surf = self.font.render(line, True, color)
            rendered_lines.append(surf)
            total_height += surf.get_height() + line_spacing
        total_height -= line_spacing
        y = (HEIGHT - total_height) // 2
        for surf in rendered_lines:
            rect = surf.get_rect(center=(WIDTH // 2, y + surf.get_height() // 2))
            self.screen.blit(surf, rect)
            y += surf.get_height() + line_spacing

    def spawn_sushi(self):
        x = random.randint(50, WIDTH - 50)
        is_wasabi = random.random() < WASABI_CHANCE
        img = self.wasabi_img if is_wasabi else random.choice(self.sushi_images)
        sushi = Sushi(img, (x, -40), wasabi=is_wasabi, speed=self.sushi_fall_speed)
        self.sushis.append(sushi)

    def spawn_cloud(self):
        cloud = Cloud(self.cloud_img, self.cloud_speed_multiplier)
        self.clouds.append(cloud)

    def spawn_petal(self):
        x = random.randint(0, WIDTH)
        image = self.petal_img_flipped if self.petal_toggle else self.petal_img
        self.petal_toggle = not self.petal_toggle
        petal = Petal(image, (x, -PETAL_SIZE[1]), self.petal_toggle, self.petal_speed_multiplier)
        self.petals.append(petal)

    def reset_game(self):
        self.score = 0
        self.sushis.clear()
        self.clouds.clear()
        self.petals.clear()
        self.petal_toggle = False
        self.game_over = False
        self.game_over_time = None
        self.paused = False
        self.pause_by_controller = False
        self.sushi_fall_speed = 5
        self.cloud_speed_multiplier = 1.0
        self.petal_speed_multiplier = 1.0
        self.cat = Cat(self.cat_right_base, (WIDTH // 2, HEIGHT), 14)
        now = pygame.time.get_ticks()
        self.sushi_spawner.last_spawn = now
        self.cloud_spawner.last_spawn = now - self.cloud_spawner.spawn_interval
        self.petal_spawner.last_spawn = now - self.petal_spawner.spawn_interval
        self.speed_increase_time = now

        pygame.mixer.music.play(-1)

    def pause(self, by_controller=False):
        self.paused = True
        self.pause_by_controller = by_controller
        pygame.mixer.music.pause()

    def unpause(self):
        self.paused = False
        pygame.mixer.music.unpause()

    def run(self):
        while True:
            dt = self.clock.tick(60)
            now = pygame.time.get_ticks()
            self.screen.blit(self.wallpaper, (0, 0))
            keys = pygame.key.get_pressed()
            move = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_game()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if not self.game_over:
                            if self.paused:
                                self.unpause()
                            else:
                                self.pause(by_controller=False)
                    elif event.key == pygame.K_q:
                        quit_game()
                    elif self.game_over and not self.paused:
                        self.reset_game()
                if self.joystick and event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 7 or event.button == 6:
                        if not self.game_over:
                            if self.paused:
                                self.unpause()
                            else:
                                self.pause(by_controller=True)
                    elif self.paused and event.button == 2:
                        quit_game()
                    elif self.game_over and not self.paused:
                        self.reset_game()

            if self.paused:
                self.draw_centered_text("PAUSED", (255, 255, 255))
                if self.pause_by_controller:
                    instruction = self.small_font.render("Press START to resume or X to quit.", True, (255, 255, 255))
                else:
                    instruction = self.small_font.render("Press ESC to resume or Q to quit.", True, (255, 255, 255))
                instr_rect = instruction.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
                self.screen.blit(instruction, instr_rect)
                pygame.display.flip()
                continue

            # Difficulty increase every 30 seconds
            if now - self.speed_increase_time > 30000:
                self.sushi_fall_speed += 1
                self.cloud_speed_multiplier += 0.1
                self.petal_speed_multiplier += 0.1
                self.speed_increase_time = now

            # Spawn clouds, petals, sushi
            if self.cloud_spawner.can_spawn(now):
                self.spawn_cloud()
                self.cloud_spawner.update_spawn_time(now)
            if self.petal_spawner.can_spawn(now):
                self.spawn_petal()
                self.petal_spawner.update_spawn_time(now)
            if not self.game_over and self.sushi_spawner.can_spawn(now):
                self.spawn_sushi()
                self.sushi_spawner.update_spawn_time(now)

            # Update clouds
            for cloud in self.clouds[:]:
                cloud.update(dt, now)
                if cloud.off_screen():
                    self.clouds.remove(cloud)

            # Update petals
            for petal in self.petals[:]:
                petal.update(dt, now)
                if petal.off_screen():
                    self.petals.remove(petal)

            if not self.game_over:
                # Handle input
                if keys[pygame.K_a]:
                    move = -1
                    self.cat.facing = "left"
                elif keys[pygame.K_d]:
                    move = 1
                    self.cat.facing = "right"

                if self.joystick:
                    axis = self.joystick.get_axis(0)
                    if abs(axis) > 0.2:
                        move = int(axis / abs(axis))  # normalize to -1 or 1
                        self.cat.facing = "left" if axis < 0 else "right"

                self.cat.update_image()
                self.cat.move(move)

                tuna_mid_y = self.cat.rect.top + self.cat.rect.height // 2

                # Update sushi positions and collisions
                for sushi in self.sushis[:]:
                    sushi.speed = self.sushi_fall_speed
                    sushi.update(dt)

                    horizontal_overlap = sushi.rect.right > self.cat.rect.left and sushi.rect.left < self.cat.rect.right
                    if horizontal_overlap and sushi.rect.bottom >= tuna_mid_y:
                        if sushi.wasabi:
                            self.meow_sound.play()
                            self.game_over = True
                            self.game_over_time = None
                        else:
                            self.score += 1
                            self.chomp_sound.play()
                            self.cat.grow()
                        self.sushis.remove(sushi)
                    elif sushi.off_screen():
                        self.sushis.remove(sushi)

            else:
                if self.game_over_time is None:
                    self.game_over_time = now
                elif now - self.game_over_time >= GAME_OVER_DELAY:
                    quit_game()

            # Draw everything
            for cloud in self.clouds:
                cloud.draw(self.screen)
            for petal in self.petals:
                petal.draw(self.screen)
            self.cat.draw(self.screen)
            for sushi in self.sushis:
                sushi.draw(self.screen)

            self.draw_text(f"Score: {self.score}", (10, 10))

            if self.game_over:
                self.draw_centered_multiline_text([f"Final Score: {self.score}", "Game Over!"], color=(255, 0, 0))

            pygame.display.flip()


if __name__ == "__main__":
    game = Game()
    game.reset_game()
    game.run()

