import os
import random
import math
from dataclasses import dataclass

import pygame

from core.scene import Scene
from settings import BASE_HEIGHT, BASE_WIDTH


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    radius: int
    damage: int
    owner: str
    width: int | None = None
    height: int | None = None
    is_crit: bool = False
    has_dealt_damage: bool = False

    @property
    def rect(self):
        width = self.width if self.width is not None else self.radius * 2
        height = self.height if self.height is not None else self.radius * 2
        return pygame.Rect(
            int(self.x - width / 2),
            int(self.y - height / 2),
            width,
            height,
        )


@dataclass
class Enemy:
    x: float
    y: float
    width: int
    height: int
    max_health: int
    health: int
    fire_cooldown: float
    bullet_speed: float
    damage: int
    color: tuple[int, int, int]
    enemy_type: str
    shoot_timer: float = 0.0
    move_direction: int = 1
    move_speed: float = 0.0
    direction_timer: float = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)


@dataclass
class UpgradeDrop:
    x: float
    y: float
    width: int
    height: int
    speed: float
    label: str
    effect: str
    color: tuple[int, int, int]

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)


class SpaceGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.asset_dir = os.path.join(os.path.dirname(__file__), "images")
        self.hud_height = 54
        self.play_height = BASE_HEIGHT - self.hud_height
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.text_font = pygame.font.SysFont("arial", 15)
        self.small_font = pygame.font.SysFont("arial", 12)
        self.big_font = pygame.font.SysFont("arial", 22, bold=True)

        self.player_size = (28, 18)
        self.player_x = 48.0
        self.player_y = self.play_height / 2 - self.player_size[1] / 2
        self.player_speed = 165.0
        self.max_health = 100
        self.player_health = self.max_health
        self.player_damage = 10
        self.player_fire_cooldown = 0.22
        self.player_fire_timer = 0.0
        self.player_bullet_speed = 340.0
        self.player_bullet_radius = 4
        self.player_armor = 0
        self.side_shot_level = 0
        self.spread_shot_level = 0
        self.crit_chance = 0.0
        self.crit_damage_bonus = 0.0
        self.overheal_bonus = 0
        self.heal_on_kill = 0

        self.round_number = 1
        self.score = 0
        self.bullets = []
        self.enemies = []
        self.upgrade_drop = None
        self.round_transition_timer = 0.0
        self.game_over = False
        self.show_instructions = True

        self.upgrades = [
            {"label": "Rapid Fire", "effect": "fire_rate", "color": (255, 220, 110)},
            {"label": "Hull Up", "effect": "max_health", "color": (120, 255, 160)},
            {"label": "Thrusters", "effect": "move_speed", "color": (120, 210, 255)},
            {"label": "Heavy Shot", "effect": "damage", "color": (255, 140, 140)},
            {"label": "Turbo Bolt", "effect": "bullet_speed", "color": (255, 175, 90)},
            {"label": "Shield Plating", "effect": "armor", "color": (175, 170, 255)},
            {"label": "Wider Shot", "effect": "bullet_size", "color": (255, 120, 200)},
        ]
        self.special_upgrades = [
            {"label": "Side Shot", "effect": "side_shot", "color": (255, 210, 120)},
            {"label": "Spread Shot", "effect": "spread_shot", "color": (120, 235, 255)},
            {"label": "Crit Core", "effect": "crit", "color": (255, 150, 120)},
            {"label": "Repair Matrix", "effect": "heal_on_kill", "color": (120, 255, 170)},
            {"label": "Overcharge Hull", "effect": "overheal", "color": (120, 200, 255)},
        ]

        self.upgrade_pool = []
        self.special_upgrade_pool = []
        self.collected_buffs = []
        self.collected_upgrades = []
        self.last_buff_label = ""
        self.last_upgrade_label = ""
        self.player_sprite = self.load_player_sprite()
        self.enemy_sprites = self.load_enemy_sprites()
        self.upgrade_sprite = self.load_upgrade_sprite()
        self.background_images = self.load_backgrounds()
        self.current_background = self.choose_background()
        self.reset_upgrade_pool()
        self.reset_special_upgrade_pool()

        self.spawn_round(self.round_number)

    def reset_game(self):
        self.player_x = 48.0
        self.player_y = self.play_height / 2 - self.player_size[1] / 2
        self.player_speed = 165.0
        self.max_health = 100
        self.player_health = self.max_health
        self.player_damage = 10
        self.player_fire_cooldown = 0.22
        self.player_fire_timer = 0.0
        self.player_bullet_speed = 340.0
        self.player_bullet_radius = 4
        self.player_armor = 0
        self.side_shot_level = 0
        self.spread_shot_level = 0
        self.crit_chance = 0.0
        self.crit_damage_bonus = 0.0
        self.overheal_bonus = 0
        self.heal_on_kill = 0

        self.round_number = 1
        self.score = 0
        self.bullets = []
        self.enemies = []
        self.upgrade_drop = None
        self.round_transition_timer = 0.0
        self.game_over = False
        self.show_instructions = True
        self.upgrade_pool = []
        self.special_upgrade_pool = []
        self.collected_buffs = []
        self.collected_upgrades = []
        self.last_buff_label = ""
        self.last_upgrade_label = ""
        self.current_background = self.choose_background()
        self.reset_upgrade_pool()
        self.reset_special_upgrade_pool()

        self.spawn_round(self.round_number)

    def load_player_sprite(self):
        sprite_path = os.path.join(self.asset_dir, "player_spaceship.png")
        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()
            return pygame.transform.smoothscale(sprite, (42, 28))
        except pygame.error:
            return None

    def load_enemy_sprites(self):
        sprites = {}
        sprite_files = {
            "normal": "enemy_spaceship_1.png",
            "elite": "enemy_spaceship_2.png",
            "heavy": "enemy_spaceship_3.png",
            "boss": "enemy_boss.png",
        }

        for enemy_type, file_name in sprite_files.items():
            sprite_path = os.path.join(self.asset_dir, file_name)
            try:
                sprites[enemy_type] = pygame.image.load(sprite_path).convert_alpha()
            except pygame.error:
                sprites[enemy_type] = None

        return sprites

    def load_upgrade_sprite(self):
        sprite_path = os.path.join(self.asset_dir, "upgrade.png")
        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()
            return pygame.transform.smoothscale(sprite, (26, 26))
        except pygame.error:
            return None

    def load_backgrounds(self):
        backgrounds = []
        for file_name in sorted(os.listdir(self.asset_dir)):
            if file_name.startswith("achtergrond") and file_name.endswith(".png"):
                path = os.path.join(self.asset_dir, file_name)
                try:
                    image = pygame.image.load(path).convert()
                    backgrounds.append(pygame.transform.smoothscale(image, (BASE_WIDTH, self.play_height)))
                except pygame.error:
                    continue
        return backgrounds

    def choose_background(self):
        if not self.background_images:
            return None
        return random.choice(self.background_images)

    def reset_upgrade_pool(self):
        self.upgrade_pool = self.upgrades.copy()
        random.shuffle(self.upgrade_pool)

    def reset_special_upgrade_pool(self):
        self.special_upgrade_pool = self.special_upgrades.copy()
        random.shuffle(self.special_upgrade_pool)

    def get_random_upgrade_y(self, upgrade_height):
        min_y = 18
        max_y = self.play_height - upgrade_height - 18
        return random.randint(min_y, max_y)

    def is_boss_round(self, round_number):
        return round_number > 0 and round_number % 10 == 0

    def wrap_text(self, text, font, max_width):
        if not text:
            return [""]

        words = text.split()
        lines = []
        current_line = words[0]

        for word in words[1:]:
            test_line = f"{current_line} {word}"
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        lines.append(current_line)
        return lines

    def spawn_round(self, round_number):
        self.enemies = []
        self.bullets = [bullet for bullet in self.bullets if bullet.owner == "player"]

        if self.is_boss_round(round_number):
            self.spawn_boss_round(round_number)
            return

        if round_number <= 4:
            enemy_count = random.randint(3, 6)
        elif round_number <= 10:
            enemy_count = random.randint(5, 9)
        else:
            enemy_count = random.randint(8, 12)
        spacing = self.play_height / (enemy_count + 1)
        enemy_types = ["elite" if index % 3 == 2 else "normal" for index in range(enemy_count)]
        if round_number >= 5:
            heavy_count = 0
            heavy_roll = random.random()
            if heavy_roll < 0.14:
                heavy_count = 2
            elif heavy_roll < 0.44:
                heavy_count = 1

            for replace_index in random.sample(range(enemy_count), k=min(heavy_count, enemy_count)):
                enemy_types[replace_index] = "heavy"
        random.shuffle(enemy_types)

        for index in range(enemy_count):
            enemy_type = enemy_types[index]
            x = BASE_WIDTH - 90 - random.randint(0, 45)
            base_health = 22 + round_number * 8
            base_damage = 7 + round_number * 2

            if enemy_type == "elite":
                max_health = int(base_health * 1.45)
                damage = int(base_damage * 1.35)
                fire_cooldown = max(1.7 - round_number * 0.035, 0.7)
                bullet_speed = 185 + round_number * 9
                color = (210, 120, 90)
            elif enemy_type == "heavy":
                max_health = base_health * 2
                damage = max(4, int(base_damage * 0.75))
                fire_cooldown = max(2.15 - round_number * 0.03, 1.1)
                bullet_speed = 120 + round_number * 5
                color = (130, 110, 200)
            else:
                max_health = base_health
                damage = base_damage
                fire_cooldown = max(1.45 - round_number * 0.04, 0.5)
                bullet_speed = 175 + round_number * 8
                color_shift = min(100 + round_number * 7, 220)
                color = (color_shift, 90, 120)

            if enemy_type == "heavy":
                width = min(54, 30 + max_health // 18)
                height = min(36, 18 + max_health // 28)
            else:
                width = min(44, 24 + max_health // 15 + damage // 10)
                height = min(32, 16 + max_health // 24 + damage // 14)
            y = spacing * (index + 1) - height / 2 + random.randint(-8, 8)
            enemy = Enemy(
                x=x,
                y=max(18, min(self.play_height - height - 18, y)),
                width=width,
                height=height,
                max_health=max_health,
                health=max_health,
                fire_cooldown=fire_cooldown,
                bullet_speed=bullet_speed,
                damage=damage,
                color=color,
                enemy_type=enemy_type,
                shoot_timer=random.uniform(0.1, fire_cooldown),
                move_direction=random.choice([-1, 1]),
                move_speed=26 + round_number * 3 + random.uniform(0, 18),
                direction_timer=random.uniform(0.4, 1.4),
            )
            self.enemies.append(enemy)

    def spawn_boss_round(self, round_number):
        max_health = 340 + round_number * 38
        damage = 12 + round_number * 2
        width = 108
        height = 74
        enemy = Enemy(
            x=BASE_WIDTH - 150,
            y=self.play_height / 2 - height / 2,
            width=width,
            height=height,
            max_health=max_health,
            health=max_health,
            fire_cooldown=max(1.0 - round_number * 0.01, 0.5),
            bullet_speed=220 + round_number * 6,
            damage=damage,
            color=(210, 80, 120),
            enemy_type="boss",
            shoot_timer=0.3,
            move_direction=random.choice([-1, 1]),
            move_speed=42 + round_number * 1.5,
            direction_timer=random.uniform(0.8, 1.6),
        )
        self.enemies.append(enemy)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))
                return

            if self.show_instructions and event.key == pygame.K_RETURN:
                self.show_instructions = False
                return

            if self.game_over and event.key == pygame.K_RETURN:
                self.reset_game()

    def update(self, dt):
        if self.show_instructions or self.game_over:
            return

        self.player_fire_timer += dt
        self.round_transition_timer = max(0.0, self.round_transition_timer - dt)

        self.update_player(dt)
        self.update_enemies(dt)
        self.update_bullets(dt)
        self.update_upgrade(dt)
        self.check_round_clear()

    def update_player(self, dt):
        keys = pygame.key.get_pressed()
        move_x = 0
        move_y = 0

        if keys[pygame.K_LEFT]:
            move_x -= 1
        if keys[pygame.K_RIGHT]:
            move_x += 1
        if keys[pygame.K_UP]:
            move_y -= 1
        if keys[pygame.K_DOWN]:
            move_y += 1

        if move_x or move_y:
            length = max((move_x * move_x + move_y * move_y) ** 0.5, 1)
            self.player_x += move_x / length * self.player_speed * dt
            self.player_y += move_y / length * self.player_speed * dt

        self.player_x = max(12, min(BASE_WIDTH * 0.48, self.player_x))
        self.player_y = max(14, min(self.play_height - self.player_size[1] - 14, self.player_y))

        if self.player_fire_timer >= self.player_fire_cooldown and self.enemies:
            self.player_fire_timer = 0.0
            self.spawn_player_bullet()

    def roll_player_shot_damage(self):
        damage = self.player_damage
        is_crit = random.random() < self.crit_chance
        if is_crit:
            damage = max(damage + 1, int(round(damage * (2.0 + self.crit_damage_bonus))))
        return damage, is_crit

    def spawn_player_projectile(self, angle_degrees=0, y_offset=0.0):
        angle = math.radians(angle_degrees)
        damage, is_crit = self.roll_player_shot_damage()
        self.bullets.append(
            Bullet(
                x=self.player_x + self.player_size[0] + 2,
                y=self.player_y + self.player_size[1] / 2 + y_offset,
                vx=math.cos(angle) * self.player_bullet_speed,
                vy=math.sin(angle) * self.player_bullet_speed,
                radius=self.player_bullet_radius,
                damage=damage,
                owner="player",
                is_crit=is_crit,
            )
        )

    def spawn_player_bullet(self):
        self.spawn_player_projectile()

        side_offsets = []
        for level in range(self.side_shot_level):
            lane = level // 2 + 1
            direction = 1 if level % 2 == 0 else -1
            side_offsets.append(direction * lane * 8)

        for offset in side_offsets:
            self.spawn_player_projectile(y_offset=offset)

        for _ in range(self.spread_shot_level):
            self.spawn_player_projectile(angle_degrees=-30)
            self.spawn_player_projectile(angle_degrees=30)

    def spawn_enemy_bullet(self, enemy, angle_offset=0):
        angle = math.radians(180 + angle_offset)
        bullet_radius = 4
        bullet_width = None
        bullet_height = None

        if enemy.enemy_type == "heavy":
            bullet_radius = 3
            bullet_width = 30
            bullet_height = 6

        self.bullets.append(
            Bullet(
                x=enemy.x - 4,
                y=enemy.y + enemy.height / 2,
                vx=math.cos(angle) * enemy.bullet_speed,
                vy=math.sin(angle) * enemy.bullet_speed,
                radius=bullet_radius,
                damage=enemy.damage,
                owner="enemy",
                width=bullet_width,
                height=bullet_height,
            )
        )

    def get_player_heal_cap(self):
        return self.max_health + self.overheal_bonus

    def heal_player(self, amount):
        self.player_health = min(self.get_player_heal_cap(), self.player_health + amount)

    def update_enemies(self, dt):
        for enemy in self.enemies:
            enemy.shoot_timer += dt
            enemy.direction_timer -= dt

            if enemy.direction_timer <= 0:
                enemy.move_direction = random.choice([-1, 1])
                enemy.direction_timer = random.uniform(0.5, 1.5)

            enemy.y += enemy.move_direction * enemy.move_speed * dt
            min_y = 10
            max_y = self.play_height - enemy.height - 10

            if enemy.y <= min_y:
                enemy.y = min_y
                enemy.move_direction = 1
                enemy.direction_timer = random.uniform(0.4, 1.1)
            elif enemy.y >= max_y:
                enemy.y = max_y
                enemy.move_direction = -1
                enemy.direction_timer = random.uniform(0.4, 1.1)

            if enemy.shoot_timer >= enemy.fire_cooldown:
                enemy.shoot_timer = 0.0
                if enemy.enemy_type == "boss":
                    for angle in (-35, -18, 0, 18, 35):
                        self.spawn_enemy_bullet(enemy, angle)
                elif enemy.enemy_type == "elite":
                    self.spawn_enemy_bullet(enemy, 30)
                    self.spawn_enemy_bullet(enemy, -30)
                elif enemy.enemy_type == "heavy":
                    self.spawn_enemy_bullet(enemy)
                else:
                    self.spawn_enemy_bullet(enemy)

    def update_bullets(self, dt):
        player_rect = pygame.Rect(
            int(self.player_x),
            int(self.player_y),
            self.player_size[0],
            self.player_size[1],
        )

        active_bullets = []
        active_enemies = []

        for bullet in self.bullets:
            bullet.x += bullet.vx * dt
            bullet.y += bullet.vy * dt
            bullet_rect = bullet.rect

            if (
                bullet.x < -20
                or bullet.x > BASE_WIDTH + 20
                or bullet.y < -20
                or bullet.y > self.play_height + 20
            ):
                continue

            if bullet.owner == "player":
                hit_enemy = False
                for enemy in self.enemies:
                    if bullet_rect.colliderect(enemy.rect):
                        enemy.health -= bullet.damage
                        hit_enemy = True
                        if enemy.health <= 0:
                            self.score += 1
                            if self.heal_on_kill > 0:
                                self.heal_player(self.heal_on_kill)
                        break
                if hit_enemy:
                    continue
            else:
                if bullet_rect.colliderect(player_rect) and not bullet.has_dealt_damage:
                    self.player_health -= max(1, bullet.damage - self.player_armor)
                    bullet.has_dealt_damage = True
                    if self.player_health <= 0:
                        self.player_health = 0
                        self.game_over = True
                    if bullet.width is None or bullet.height is None:
                        continue

            active_bullets.append(bullet)

        for enemy in self.enemies:
            if enemy.health > 0:
                active_enemies.append(enemy)

        self.bullets = active_bullets
        self.enemies = active_enemies

    def update_upgrade(self, dt):
        if not self.upgrade_drop:
            return

        self.upgrade_drop.x -= self.upgrade_drop.speed * dt

        player_rect = pygame.Rect(
            int(self.player_x),
            int(self.player_y),
            self.player_size[0],
            self.player_size[1],
        )

        if self.upgrade_drop.rect.colliderect(player_rect):
            self.apply_special_upgrade(self.upgrade_drop.effect)
            self.collected_upgrades.append(self.upgrade_drop.label)
            self.last_upgrade_label = self.upgrade_drop.label
            self.upgrade_drop = None
            return

        if self.upgrade_drop.x + self.upgrade_drop.width < 0:
            self.upgrade_drop = None

    def check_round_clear(self):
        if self.enemies or self.round_transition_timer > 0:
            return

        cleared_round = self.round_number
        was_boss_round = self.is_boss_round(cleared_round)
        self.heal_player(5)
        self.grant_round_buff()

        if was_boss_round:
            self.heal_player(30)
            self.grant_boss_reward()

        if cleared_round % 3 == 0 and not was_boss_round:
            if not self.special_upgrade_pool:
                self.reset_special_upgrade_pool()

            upgrade = self.special_upgrade_pool.pop()
            self.upgrade_drop = UpgradeDrop(
                x=BASE_WIDTH + 12,
                y=self.get_random_upgrade_y(24),
                width=24,
                height=24,
                speed=48.0,
                label=upgrade["label"],
                effect=upgrade["effect"],
                color=upgrade["color"],
            )

        self.round_number += 1
        self.round_transition_timer = 1.1
        self.spawn_round(self.round_number)

    def grant_round_buff(self):
        if not self.upgrade_pool:
            self.reset_upgrade_pool()

        buff = self.upgrade_pool.pop()
        self.apply_buff(buff["effect"])
        self.collected_buffs.append(buff["label"])
        self.last_buff_label = buff["label"]

    def grant_boss_reward(self):
        if not self.special_upgrade_pool:
            self.reset_special_upgrade_pool()

        upgrade = self.special_upgrade_pool.pop()
        self.apply_special_upgrade(upgrade["effect"])
        self.collected_upgrades.append(upgrade["label"])
        self.last_upgrade_label = upgrade["label"]

    def apply_buff(self, effect):
        if effect == "fire_rate":
            self.player_fire_cooldown = max(0.1, self.player_fire_cooldown - 0.025)
        elif effect == "max_health":
            self.max_health += 20
            self.player_health = min(self.get_player_heal_cap(), self.player_health + 20)
        elif effect == "move_speed":
            self.player_speed += 18
        elif effect == "damage":
            self.player_damage += 3
        elif effect == "bullet_speed":
            self.player_bullet_speed += 45
        elif effect == "armor":
            self.player_armor += 1
        elif effect == "bullet_size":
            self.player_bullet_radius += 1

    def apply_special_upgrade(self, effect):
        if effect == "side_shot":
            self.side_shot_level += 1
        elif effect == "spread_shot":
            self.spread_shot_level += 1
        elif effect == "crit":
            self.crit_chance = min(1.0, self.crit_chance + 0.05)
            self.crit_damage_bonus += 0.10
        elif effect == "heal_on_kill":
            self.heal_on_kill += 1
        elif effect == "overheal":
            self.overheal_bonus += 25

    def draw(self, surface):
        self.draw_background(surface)

        if self.show_instructions:
            self.draw_instructions(surface)
            return

        self.draw_upgrade(surface)
        self.draw_bullets(surface)
        self.draw_player(surface)
        self.draw_enemies(surface)
        self.draw_hud(surface)

        if self.round_transition_timer > 0:
            self.draw_round_banner(surface)

        if self.game_over:
            self.draw_game_over(surface)

    def draw_background(self, surface):
        if self.current_background:
            surface.blit(self.current_background, (0, 0))
        else:
            surface.fill((7, 10, 26), pygame.Rect(0, 0, BASE_WIDTH, self.play_height))

        player_zone = pygame.Rect(0, 0, int(BASE_WIDTH * 0.45), self.play_height)
        enemy_zone = pygame.Rect(int(BASE_WIDTH * 0.58), 0, BASE_WIDTH, self.play_height)
        shade = pygame.Surface((BASE_WIDTH, self.play_height), pygame.SRCALPHA)
        pygame.draw.rect(shade, (8, 14, 28, 105), player_zone)
        pygame.draw.rect(shade, (24, 10, 20, 95), enemy_zone)
        surface.blit(shade, (0, 0))
        pygame.draw.line(surface, (70, 90, 150), (BASE_WIDTH // 2, 8), (BASE_WIDTH // 2, self.play_height - 8), 1)

    def draw_player(self, surface):
        if self.player_sprite:
            rect = self.player_sprite.get_rect(center=(int(self.player_x + self.player_size[0] / 2), int(self.player_y + self.player_size[1] / 2)))
            surface.blit(self.player_sprite, rect)
        else:
            ship_points = [
                (int(self.player_x), int(self.player_y)),
                (int(self.player_x), int(self.player_y + self.player_size[1])),
                (int(self.player_x + self.player_size[0]), int(self.player_y + self.player_size[1] / 2)),
            ]
            pygame.draw.polygon(surface, (80, 210, 255), ship_points)
            pygame.draw.polygon(surface, (230, 250, 255), ship_points, 2)
            pygame.draw.rect(surface, (255, 160, 80), (self.player_x - 6, self.player_y + 5, 6, 8))

    def draw_enemies(self, surface):
        for enemy in self.enemies:
            rect = enemy.rect
            enemy_sprite = self.enemy_sprites.get(enemy.enemy_type)
            if enemy_sprite:
                scaled_sprite = pygame.transform.smoothscale(enemy_sprite, (rect.width + 10, rect.height + 8))
                sprite_rect = scaled_sprite.get_rect(center=rect.center)
                surface.blit(scaled_sprite, sprite_rect)
            else:
                pygame.draw.rect(surface, enemy.color, rect, border_radius=5)
                pygame.draw.rect(surface, (255, 220, 230), rect, 2, border_radius=5)

            bar_rect = pygame.Rect(rect.x, rect.y - 7, rect.width, 4)
            fill_width = int(bar_rect.width * max(0, enemy.health) / enemy.max_health)
            pygame.draw.rect(surface, (55, 20, 25), bar_rect, border_radius=2)
            pygame.draw.rect(
                surface,
                (110, 255, 150),
                (bar_rect.x, bar_rect.y, fill_width, bar_rect.height),
                border_radius=2,
            )

    def draw_bullets(self, surface):
        for bullet in self.bullets:
            if bullet.owner == "player":
                color = (255, 220, 110) if bullet.is_crit else (110, 235, 255)
                pygame.draw.circle(surface, color, (int(bullet.x), int(bullet.y)), bullet.radius)
                continue

            if bullet.width is not None and bullet.height is not None:
                color = (190, 150, 255)
                pygame.draw.rect(surface, color, bullet.rect, border_radius=3)
                pygame.draw.rect(surface, (245, 235, 255), bullet.rect, 1, border_radius=3)
            else:
                color = (255, 110, 110)
                pygame.draw.circle(surface, color, (int(bullet.x), int(bullet.y)), bullet.radius)

    def draw_upgrade(self, surface):
        if not self.upgrade_drop:
            return

        rect = self.upgrade_drop.rect
        if self.upgrade_sprite:
            sprite_rect = self.upgrade_sprite.get_rect(center=rect.center)
            surface.blit(self.upgrade_sprite, sprite_rect)
        else:
            pygame.draw.rect(surface, self.upgrade_drop.color, rect, border_radius=5)
            pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=5)

    def draw_hud(self, surface):
        hud_rect = pygame.Rect(0, self.play_height, BASE_WIDTH, self.hud_height)
        pygame.draw.rect(surface, (8, 12, 20), hud_rect)
        pygame.draw.line(surface, (200, 220, 255), (0, hud_rect.y), (BASE_WIDTH, hud_rect.y), 2)

        health_bar_bg = pygame.Rect(12, hud_rect.y + 10, 130, 10)
        health_fill = int(health_bar_bg.width * min(self.player_health, self.max_health) / self.max_health)
        pygame.draw.rect(surface, (60, 25, 25), health_bar_bg, border_radius=5)
        pygame.draw.rect(
            surface,
            (100, 255, 140),
            (health_bar_bg.x, health_bar_bg.y, health_fill, health_bar_bg.height),
            border_radius=5,
        )

        left_text = self.small_font.render(
            f"HP {int(self.player_health)}/{int(self.max_health)}  Armor {self.player_armor}  Score {self.score}  Round {self.round_number}",
            True,
            (255, 255, 255),
        )
        right_text = self.small_font.render(
            f"Crit {int(self.crit_chance * 100)}% x{2.0 + self.crit_damage_bonus:.1f}  Side +{self.side_shot_level}  Spread {self.spread_shot_level}  Heal +5/+{self.heal_on_kill}",
            True,
            (210, 235, 255),
        )

        surface.blit(left_text, (12, hud_rect.y + 24))
        surface.blit(right_text, (12, hud_rect.y + 38))

    def draw_round_banner(self, surface):
        if self.is_boss_round(self.round_number):
            label_text = f"Boss Round {self.round_number}"
            border_color = (255, 130, 130)
        else:
            label_text = f"Round {self.round_number}"
            border_color = (255, 240, 180)

        label = self.big_font.render(label_text, True, (255, 240, 180))
        rect = label.get_rect(center=(BASE_WIDTH // 2, 24))
        panel = rect.inflate(22, 26)
        pygame.draw.rect(surface, (16, 18, 32), panel, border_radius=8)
        pygame.draw.rect(surface, border_color, panel, 2, border_radius=8)
        surface.blit(label, rect)
        if self.last_buff_label:
            buff_text = self.small_font.render(f"Buff: {self.last_buff_label}", True, (120, 255, 160))
            buff_rect = buff_text.get_rect(center=(BASE_WIDTH // 2, rect.centery + 18))
            surface.blit(buff_text, buff_rect)
        if self.last_upgrade_label:
            upgrade_text = self.small_font.render(f"Special: {self.last_upgrade_label}", True, (120, 210, 255))
            upgrade_rect = upgrade_text.get_rect(center=(BASE_WIDTH // 2, rect.centery + 31))
            surface.blit(upgrade_text, upgrade_rect)

    def draw_instructions(self, surface):
        panel = pygame.Rect(26, 22, BASE_WIDTH - 52, BASE_HEIGHT - 44)
        pygame.draw.rect(surface, (10, 15, 30), panel, border_radius=14)
        pygame.draw.rect(surface, (180, 220, 255), panel, 2, border_radius=14)

        title = self.title_font.render("SPACE SHOOTER", True, (255, 240, 180))
        surface.blit(title, (panel.x + 18, panel.y + 14))

        sections = [
            ("Doel", ["Versla elke ronde alle vijanden en overleef zo lang mogelijk."]),
            ("Besturing", ["Pijltjes om te bewegen.", "Je schip schiet automatisch rechtdoor naar rechts."]),
            (
                "Regels",
                [
                    "Elke verslagen enemy geeft 1 punt.",
                    "Enemies schieten ook terug, maar trager dan jij.",
                    "Na elke gehaalde ronde krijg je automatisch 1 buff op je basisstats.",
                    "Na elke ronde heal je automatisch 5 HP.",
                    "Na elke 3 rondes dropt er een speciale upgrade die je moet oppakken.",
                    "Vanaf ronde 5 kan er soms een zeldzame zware enemy verschijnen, maximaal 2 per ronde.",
                    "Elke 10e ronde is een boss fight, beginnend bij ronde 10.",
                    "Na een boss fight krijg je direct 30 HP en 1 random special upgrade.",
                    "Side Shot geeft 1 extra rechte kogel, Spread Shot 2 diagonale kogels.",
                    "Crit Core geeft +5% crit chance en +10% crit damage.",
                    "Repair Matrix geeft +1 HP per kill.",
                    "Overcharge Hull laat healing boven je max HP komen.",
                    "Elke nieuwe ronde worden enemies sterker.",
                ],
            ),
        ]

        max_text_width = panel.width - 42
        y = panel.y + 48

        for heading, items in sections:
            heading_text = self.text_font.render(f"{heading}:", True, (255, 240, 180))
            surface.blit(heading_text, (panel.x + 18, y))
            y += 17

            for item in items:
                wrapped_lines = self.wrap_text(item, self.small_font, max_text_width - 12)
                for wrapped_line in wrapped_lines:
                    line_text = self.small_font.render(wrapped_line, True, (235, 240, 255))
                    surface.blit(line_text, (panel.x + 28, y))
                    y += 13
                y += 3

            y += 3

        start_text = self.text_font.render("ENTER om te starten", True, (120, 255, 160))
        back_text = self.text_font.render("ESC om terug te gaan", True, (120, 255, 160))
        surface.blit(start_text, (panel.x + 18, panel.bottom - 40))
        surface.blit(back_text, (panel.x + 18, panel.bottom - 22))

    def draw_game_over(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        panel = pygame.Rect(95, 70, 290, 125)
        pygame.draw.rect(surface, (15, 20, 34), panel, border_radius=14)
        pygame.draw.rect(surface, (255, 160, 160), panel, 2, border_radius=14)

        title = self.big_font.render("Game Over", True, (255, 180, 180))
        score = self.text_font.render(f"Score: {self.score}", True, (255, 255, 255))
        round_text = self.text_font.render(f"Gehaald tot ronde {self.round_number}", True, (255, 255, 255))
        retry = self.text_font.render("ENTER = opnieuw  |  ESC = menu", True, (120, 255, 160))

        surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 98)))
        surface.blit(score, score.get_rect(center=(BASE_WIDTH // 2, 128)))
        surface.blit(round_text, round_text.get_rect(center=(BASE_WIDTH // 2, 150)))
        surface.blit(retry, retry.get_rect(center=(BASE_WIDTH // 2, 177)))
