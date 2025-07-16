import pygame
import random
import sys
import math

pygame.init()
pygame.mixer.init()
pygame.joystick.init()

WIDTH, HEIGHT = pygame.display.Info().current_w, pygame.display.Info().current_h
SCREEN_SIZE = (WIDTH, HEIGHT)
CAT_INITIAL_SIZE = [160, 160]
CAT_MAX_SIZE = [320, 320]
SUSHI_SIZE = (50, 50)
CLOUD_SIZE = (200, 120)
PETAL_SIZE = (30, 30)
GAME_OVER_DELAY = 3000
WASABI_CHANCE = 0.1

def quit_game():
    pygame.quit()
    sys.exit()

class Cat:
    def __init__(self, cat_right_img, pos, speed):
        self.cat_right_base = cat_right_img
        self.size = CAT_INITIAL_SIZE.copy()
        self.speed = speed
        self.facing = "right"
        self.image_right = pygame.transform.smoothscale(self.cat_right_base, self.size)
        self.image_left = pygame.transform.flip(self.image_right, True, False)
        self.image = self.image_right
        self.rect = self.image.get_rect()
        self.rect.centerx, self.rect.bottom = pos
        self.grow_step = 1

    def update_image(self):
        if self.facing == "left":
            self.image = pygame.transform.flip(self.image_right, True, False)
        else:
            self.image = self.image_right

    def move(self, dx):
        self.rect.x += dx * self.speed
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))
        self.rect.bottom = HEIGHT

    def grow(self):
        self.size[0] = min(self.size[0] + self.grow_step, CAT_MAX_SIZE[0])
        self.size[1] = min(self.size[1] + self.grow_step, CAT_MAX_SIZE[1])
        self.image_right = pygame.transform.smoothscale(self.cat_right_base, self.size)
        self.update_image()
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
        pygame.display.set_caption("Maguro Cat Game")

        self.wallpaper = pygame.image.load("wallpaper.jpg").convert()
        self.wallpaper = pygame.transform.scale(self.wallpaper, SCREEN_SIZE)

        self.cat_right_base = pygame.image.load("cat.png").convert_alpha()

        self.sushi_images = []
        for i in [1, 2, 4, 3]:
            img = pygame.image.load(f"sushi{i}.png").convert_alpha()
            img = pygame.transform.smoothscale(img, SUSHI_SIZE)
            self.sushi_images.append(img)

        self.wasabi_img = pygame.image.load("wasabi.png").convert_alpha()
        self.wasabi_img = pygame.transform.smoothscale(self.wasabi_img, SUSHI_SIZE)

        self.cloud_base = pygame.image.load("cloud.png").convert_alpha()
        self.cloud_img = pygame.transform.smoothscale(self.cloud_base, CLOUD_SIZE)

        self.petal_base = pygame.image.load("petal.png").convert_alpha()
        self.petal_img = pygame.transform.smoothscale(self.petal_base, PETAL_SIZE)
        self.petal_img_flipped = pygame.transform.flip(self.petal_img, True, False)

        self.music_file = "audio_music.mp3"
        self.chomp_sounds = [
            pygame.mixer.Sound("audio_chomp_low.mp3"),
            pygame.mixer.Sound("audio_chomp.mp3"),
            pygame.mixer.Sound("audio_chomp_high.mp3")
        ]
        self.meow_sound = pygame.mixer.Sound("audio_meow.mp3")
        self.gamestart_sound = pygame.mixer.Sound("audio_gamestart.mp3")
        self.gameover_sound = pygame.mixer.Sound("audio_gameover.mp3")
        self.paused_sound = pygame.mixer.Sound("audio_paused.mp3")
        self.unpaused_sound = pygame.mixer.Sound("audio_unpaused.mp3")

        self.joysticks = []
        self.check_controllers()

        self.font = pygame.font.Font("font_8bit.otf", 160)
        self.jp_font = pygame.font.Font("font_notosansjp.ttf", 64)
        self.small_font = pygame.font.SysFont(None, 32)
        self.clock = pygame.time.Clock()

        self.sushis = []
        self.clouds = []
        self.petals = []

        self.reset_game()

    def check_controllers(self):
        self.joysticks.clear()
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self.joysticks.append(joy)

    def draw_intro(self):
        now = pygame.time.get_ticks()
        elapsed = now - self.intro_start_time
        if elapsed >= 3000:
            pygame.mixer.music.load(self.music_file)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            return False
        maguro_surf = self.font.render("MAGURO", True, (255, 255, 255))
        jp_surf = self.jp_font.render("マグロ", True, (255, 255, 255))
        self.screen.blit(maguro_surf, maguro_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80)))
        self.screen.blit(jp_surf, jp_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))
        return True

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
        self.sushi_spawner = Spawner(125)
        self.cloud_spawner = Spawner(4000)
        self.petal_spawner = Spawner(200)
        self.speed_increase_time = pygame.time.get_ticks()
        self.intro_start_time = pygame.time.get_ticks()
        self.gamestart_sound.play()

    def pause(self, by_controller=False):
        if not self.paused and not self.show_intro:
            self.paused = True
            self.pause_by_controller = by_controller
            pygame.mixer.music.pause()
            self.paused_sound.play()

    def unpause(self):
        if self.paused:
            self.paused = False
            pygame.mixer.music.unpause()
            self.unpaused_sound.play()

    def run(self):
        deadzone = 0.2
        self.show_intro = True

        while True:
            dt = self.clock.tick(60)
            now = pygame.time.get_ticks()
            self.screen.blit(self.wallpaper, (0, 0))
            keys = pygame.key.get_pressed()
            move = 0

            self.check_controllers()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_game()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if not self.game_over and not self.show_intro:
                            if self.paused:
                                self.unpause()
                            else:
                                self.pause(by_controller=False)
                    elif event.key == pygame.K_q:
                        quit_game()
                    elif self.game_over and not self.paused:
                        self.reset_game()
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button in [7, 6]:
                        if not self.game_over and not self.show_intro:
                            if self.paused:
                                self.unpause()
                            else:
                                self.pause(by_controller=True)
                    elif self.paused and event.button == 2:
                        quit_game()
                    elif self.game_over and not self.paused:
                        self.reset_game()

            if self.show_intro:
                if self.draw_intro():
                    pygame.display.flip()
                    continue
                else:
                    self.show_intro = False

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

            if now - self.speed_increase_time > 30000:
                self.sushi_fall_speed += 1
                self.cloud_speed_multiplier += 0.1
                self.petal_speed_multiplier += 0.1
                self.speed_increase_time = now

            if self.cloud_spawner.can_spawn(now):
                self.spawn_cloud()
                self.cloud_spawner.update_spawn_time(now)
            if self.petal_spawner.can_spawn(now):
                self.spawn_petal()
                self.petal_spawner.update_spawn_time(now)
            if not self.game_over and self.sushi_spawner.can_spawn(now):
                self.spawn_sushi()
                self.sushi_spawner.update_spawn_time(now)

            for cloud in self.clouds[:]:
                cloud.update(dt, now)
                if cloud.off_screen():
                    self.clouds.remove(cloud)

            for petal in self.petals[:]:
                petal.update(dt, now)
                if petal.off_screen():
                    self.petals.remove(petal)

            if not self.game_over:
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    move = -1
                    self.cat.facing = "left"
                elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    move = 1
                    self.cat.facing = "right"

                for joy in self.joysticks:
                    axis0 = joy.get_axis(0)
                    axis2 = joy.get_axis(2)
                    if joy.get_numhats() > 0:
                        hat_x, _ = joy.get_hat(0)
                    else:
                        hat_x = 0

                    if move == 0:
                        if abs(axis0) > deadzone:
                            move = int(axis0 / abs(axis0))
                            self.cat.facing = "left" if axis0 < 0 else "right"
                        elif abs(axis2) > deadzone:
                            move = int(axis2 / abs(axis2))
                            self.cat.facing = "left" if axis2 < 0 else "right"
                        elif hat_x != 0:
                            move = hat_x
                            self.cat.facing = "left" if hat_x < 0 else "right"

                self.cat.update_image()
                self.cat.move(move)

                cat_mid_y = self.cat.rect.top + self.cat.rect.height // 2

                for sushi in self.sushis[:]:
                    sushi.speed = self.sushi_fall_speed
                    sushi.update(dt)

                    horizontal_overlap = sushi.rect.right > self.cat.rect.left and sushi.rect.left < self.cat.rect.right
                    if horizontal_overlap and sushi.rect.bottom >= cat_mid_y:
                        if sushi.wasabi:
                            self.meow_sound.play()
                            pygame.mixer.music.stop()
                            self.gameover_sound.play()
                            self.game_over = True
                            self.game_over_time = None
                        else:
                            self.score += 1
                            random.choice(self.chomp_sounds).play()
                            self.cat.grow()
                        self.sushis.remove(sushi)
                    elif sushi.off_screen():
                        self.sushis.remove(sushi)

            else:
                if self.game_over_time is None:
                    self.game_over_time = now
                elif now - self.game_over_time >= GAME_OVER_DELAY:
                    quit_game()

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

    def draw_text(self, text, pos, color=(255, 255, 255)):
        surf = self.small_font.render(text, True, color)
        self.screen.blit(surf, pos)

    def draw_centered_text(self, text, color=(255, 255, 255)):
        surf = self.small_font.render(text, True, color)
        rect = surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(surf, rect)

    def draw_centered_multiline_text(self, lines, color=(255, 255, 255), line_spacing=10):
        total_height = 0
        rendered_lines = []
        for line in lines:
            surf = self.small_font.render(line, True, color)
            rendered_lines.append(surf)
            total_height += surf.get_height() + line_spacing
        total_height -= line_spacing
        y = (HEIGHT - total_height) // 2
        for surf in rendered_lines:
            rect = surf.get_rect(center=(WIDTH // 2, y + surf.get_height() // 2))
            self.screen.blit(surf, rect)
            y += surf.get_height() + line_spacing

if __name__ == "__main__":
    game = Game()
    game.reset_game()
    game.run()

