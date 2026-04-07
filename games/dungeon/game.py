import pygame
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
import random
import math

class DungeonGame(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont("arial", 60)

        # --- Map settings ---
        self.tile_size = 30
        self.viewport_width = BASE_WIDTH // self.tile_size
        self.viewport_height = BASE_HEIGHT // self.tile_size
        self.map_width = self.viewport_width * 10
        self.map_height = self.viewport_height * 10

        # --- Movement ---
        self.move_delay = 0.12
        self.time_since_move = 0.0

        # --- Fog of War ---
        self.vision_radius = 6
        self.explored = set()
        self.visible = set()

        # --- Generate dungeon ---
        self.walls, (self.player_x, self.player_y) = self.generate_rooms_and_corridors()

        # Load player image (placeholder - replace with your PNG path)
        try:
            self.player_image = pygame.image.load("games/dungeon/dungeon_explorer.png").convert_alpha()
            self.player_image = pygame.transform.scale(self.player_image, (self.tile_size, self.tile_size))
        except:
            self.player_image = None

        # Load power-up images (placeholder - replace with your PNG paths)
        self.powerup_images = {}
        try:
            powerup_img = pygame.image.load("games/dungeon/time_power-up.png").convert_alpha()
            self.powerup_images['time'] = pygame.transform.scale(powerup_img, (self.tile_size, self.tile_size))
        except:
            self.powerup_images['time'] = None
        try:
            speed_img = pygame.image.load("games/dungeon/speed_power-up.png").convert_alpha()
            self.powerup_images['speed'] = pygame.transform.scale(speed_img, (self.tile_size, self.tile_size))
        except:
            self.powerup_images['speed'] = None

        # Player facing direction
        self.facing = 'right'

        # Timer
        self.timer = 60.0
        self.game_over = False

        # Score and dots
        self.score = 0
        self.dots = set()
        for _ in range(100):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y):
                self.dots.add((x, y))

        # Enemies
        self.enemies = []
        self.spawn_enemies()

        # Power-ups
        self.powerups = {}
        self.time_powerup_count = 6
        self.speed_powerup_count = 4
        self.spawn_powerups()

        # Speed boost state
        self.speed_boost_active = False
        self.speed_boost_time_remaining = 0.0
        self.speed_multiplier = 1.5

        # Stun state
        self.stunned = False
        self.stun_time_remaining = 0.0

        # Instructions screen
        self.show_instructions = True

    def generate_rooms_and_corridors(self):
        all_walls = {(x, y) for x in range(self.map_width) for y in range(self.map_height)}

        room_min_w, room_min_h = 3, 3
        room_max_w, room_max_h = 6, 6
        room_count = 45
        rooms = []

        def overlaps(r1, r2):
            x1, y1, w1, h1 = r1
            x2, y2, w2, h2 = r2
            return not (x1 + w1 + 1 < x2 or x2 + w2 + 1 < x1 or y1 + h1 + 1 < y2 or y2 + h2 + 1 < y1)

        sections_x = 5
        sections_y = 5
        section_width = self.map_width // sections_x
        section_height = self.map_height // sections_y

        for sx in range(sections_x):
            for sy in range(sections_y):
                section_x_start = sx * section_width
                section_x_end = (sx + 1) * section_width - 1
                section_y_start = sy * section_height
                section_y_end = (sy + 1) * section_height - 1

                placed = False
                for attempt in range(20):
                    w = random.randint(room_min_w, room_max_w)
                    h = random.randint(room_min_h, room_max_h)
                    x = random.randint(max(1, section_x_start), min(section_x_end - w, self.map_width - w - 2))
                    y = random.randint(max(1, section_y_start), min(section_y_end - h, self.map_height - h - 2))
                    new_room = (x, y, w, h)

                    if not any(overlaps(new_room, existing) for existing in rooms):
                        rooms.append(new_room)
                        placed = True
                        break

                if not placed:
                    w = random.randint(room_min_w, room_max_w)
                    h = random.randint(room_min_h, room_max_h)
                    x = random.randint(max(1, section_x_start), min(section_x_end - w, self.map_width - w - 2))
                    y = random.randint(max(1, section_y_start), min(section_y_end - h, self.map_height - h - 2))
                    rooms.append((x, y, w, h))

        for _ in range(200):
            if len(rooms) >= room_count:
                break
            w = random.randint(room_min_w, room_max_w)
            h = random.randint(room_min_h, room_max_h)
            x = random.randint(1, self.map_width - w - 2)
            y = random.randint(1, self.map_height - h - 2)
            new_room = (x, y, w, h)

            if not any(overlaps(new_room, existing) for existing in rooms):
                rooms.append(new_room)

        if not rooms:
            rooms = [(1, 1, 8, 5)]

        for x, y, w, h in rooms:
            for ry in range(y, y + h):
                for rx in range(x, x + w):
                    all_walls.discard((rx, ry))

        def carve_corridor(a, b):
            ax, ay = a
            bx, by = b

            corridor_width = random.randint(1, 3)
            width_offset = corridor_width // 2

            if random.random() < 0.5:
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((x, ay - width_offset + w))
                for y in range(min(ay, by), max(ay, by) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((bx - width_offset + w, y))
            else:
                for y in range(min(ay, by), max(ay, by) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((ax - width_offset + w, y))
                for x in range(min(ax, bx), max(ax, bx) + 1):
                    for w in range(corridor_width):
                        all_walls.discard((x, by - width_offset + w))

        centers = [(x + w // 2, y + h // 2) for x, y, w, h in rooms]

        for i in range(1, len(centers)):
            carve_corridor(centers[i - 1], centers[i])

        for i in range(self.map_width):
            all_walls.add((i, 0))
            all_walls.add((i, self.map_height - 1))

        for i in range(self.map_height):
            all_walls.add((0, i))
            all_walls.add((self.map_width - 1, i))

        return all_walls, centers[0]

    def spawn_enemies(self):
        """Spawn 4 type 1, 8 type 2, 7 type 3 enemies"""
        enemy_configs = [
            (1, 5), 
            (2, 8), 
            (3, 7), 
        ]

        for enemy_type, count in enemy_configs:
            for _ in range(count):
                attempts = 0
                while attempts < 50:
                    x = random.randint(0, self.map_width - 1)
                    y = random.randint(0, self.map_height - 1)
                    if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y):
                        self.enemies.append(Enemy(x, y, enemy_type, self.walls))
                        break
                    attempts += 1

    def spawn_powerups(self):
        self.powerups.clear()
        total_needed = self.time_powerup_count + self.speed_powerup_count
        spawned_time = 0
        spawned_speed = 0
        attempts = 0

        while (spawned_time < self.time_powerup_count or spawned_speed < self.speed_powerup_count) and attempts < 500:
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            pos = (x, y)
            if pos in self.walls or pos == (self.player_x, self.player_y) or pos in self.dots:
                attempts += 1
                continue

            enemy_positions = {(enemy.x, enemy.y) for enemy in self.enemies}
            if pos in enemy_positions or pos in self.powerups:
                attempts += 1
                continue

            if spawned_time < self.time_powerup_count and spawned_speed < self.speed_powerup_count:
                powerup_type = random.choice(['time', 'speed'])
            elif spawned_time < self.time_powerup_count:
                powerup_type = 'time'
            else:
                powerup_type = 'speed'

            self.powerups[pos] = powerup_type
            if powerup_type == 'time':
                spawned_time += 1
            else:
                spawned_speed += 1
            attempts += 1

        # Ensure fixed counts even if random placement struggles:
        if spawned_time < self.time_powerup_count or spawned_speed < self.speed_powerup_count:
            available_positions = [
                (x, y)
                for x in range(self.map_width)
                for y in range(self.map_height)
                if (x, y) not in self.walls
                and (x, y) != (self.player_x, self.player_y)
                and (x, y) not in self.dots
                and (x, y) not in self.powerups
                and (x, y) not in {(enemy.x, enemy.y) for enemy in self.enemies}
            ]
            random.shuffle(available_positions)
            for pos in available_positions:
                if spawned_time < self.time_powerup_count:
                    self.powerups[pos] = 'time'
                    spawned_time += 1
                elif spawned_speed < self.speed_powerup_count:
                    self.powerups[pos] = 'speed'
                    spawned_speed += 1
                if spawned_time >= self.time_powerup_count and spawned_speed >= self.speed_powerup_count:
                    break

    def reset_game(self):
        """Reset the game to play again"""
        # New map
        self.walls, (self.player_x, self.player_y) = self.generate_rooms_and_corridors()

        # Reset timer and score
        self.timer = 60.0
        self.game_over = False
        self.score = 0

        # Reset visibility
        self.explored.clear()
        self.visible.clear()

        # Reset dots
        self.dots.clear()
        for _ in range(100):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            if (x, y) not in self.walls and (x, y) != (self.player_x, self.player_y):
                self.dots.add((x, y))

        # Reset player state
        self.facing = 'right'
        self.time_since_move = 0.0
        self.stunned = False
        self.stun_time_remaining = 0.0
        self.speed_boost_active = False
        self.speed_boost_time_remaining = 0.0

        # Reset enemies
        self.enemies.clear()
        self.spawn_enemies()

        # Reset power-ups
        self.spawn_powerups()

        # Reset instructions
        self.show_instructions = True

    # --- Line of sight ---
    def has_line_of_sight(self, x0, y0, x1, y1):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0

        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1

        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if (x, y) in self.walls and (x, y) != (x0, y0):
                    return False
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if (x, y) in self.walls and (x, y) != (x0, y0):
                    return False
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy

        return True

    def update_visibility(self):
        self.visible.clear()

        for dy in range(-self.vision_radius, self.vision_radius + 1):
            for dx in range(-self.vision_radius, self.vision_radius + 1):

                x = self.player_x + dx
                y = self.player_y + dy

                if not (0 <= x < self.map_width and 0 <= y < self.map_height):
                    continue

                if dx * dx + dy * dy > self.vision_radius * self.vision_radius:
                    continue

                if self.has_line_of_sight(self.player_x, self.player_y, x, y):
                    self.visible.add((x, y))
                    self.explored.add((x, y))

    def handle_events(self, event):
        if self.show_instructions:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.show_instructions = False
                elif event.key == pygame.K_ESCAPE:
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
            return

        if self.game_over:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.reset_game()
                elif event.key == pygame.K_ESCAPE:
                    from ui.home_menu import HomeMenu
                    self.manager.set_scene(HomeMenu(self.manager))
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        if self.show_instructions or self.game_over:
            return

        # Handle stun
        if self.stunned:
            self.stun_time_remaining -= dt
            if self.stun_time_remaining <= 0:
                self.stunned = False

        # Handle speed boost
        if self.speed_boost_active:
            self.speed_boost_time_remaining -= dt
            if self.speed_boost_time_remaining <= 0:
                self.speed_boost_active = False

        self.time_since_move += dt
        self.timer -= dt

        if self.timer <= 0:
            self.game_over = True
            return

        keys = pygame.key.get_pressed()

        # Apply speed boost and stun delay
        move_delay = self.move_delay / self.speed_multiplier if self.speed_boost_active else self.move_delay
        if self.stunned:
            move_delay *= 2

        if self.time_since_move >= move_delay:
            old_x, old_y = self.player_x, self.player_y
            new_x = self.player_x
            new_y = self.player_y

            if keys[pygame.K_LEFT]:
                new_x -= 1
            elif keys[pygame.K_RIGHT]:
                new_x += 1
            elif keys[pygame.K_UP]:
                new_y -= 1
            elif keys[pygame.K_DOWN]:
                new_y += 1

            new_x = max(0, min(self.map_width - 1, new_x))
            new_y = max(0, min(self.map_height - 1, new_y))

            if (new_x, new_y) not in self.walls:
                self.player_x, self.player_y = new_x, new_y
                # Update facing direction
                if new_x < old_x:
                    self.facing = 'left'
                elif new_x > old_x:
                    self.facing = 'right'
                elif new_y < old_y:
                    self.facing = 'up'
                elif new_y > old_y:
                    self.facing = 'down'

                # Check for dots
                if (self.player_x, self.player_y) in self.dots:
                    self.dots.remove((self.player_x, self.player_y))
                    self.score += random.randint(1, 5)

                if (self.player_x, self.player_y) in self.powerups:
                    powerup_type = self.powerups.pop((self.player_x, self.player_y))
                    if powerup_type == 'time':
                        self.timer += 5.0
                    elif powerup_type == 'speed':
                        self.speed_boost_active = True
                        self.speed_boost_time_remaining = 6.0

            self.time_since_move = 0.0

        # 👁️ update zicht
        self.update_visibility()

        # Update enemies
        for enemy in self.enemies:
            enemy.update(dt, self.player_x, self.player_y, self.has_line_of_sight)
            # Check collision with player
            if enemy.x == self.player_x and enemy.y == self.player_y:
                if enemy.can_attack():
                    enemy.attack()
                    if enemy.type == 1:  # Instant death
                        self.game_over = True
                    elif enemy.type == 2:  # Point drain
                        self.score = max(0, self.score - 4)
                    elif enemy.type == 3:  # Stun
                        self.stunned = True
                        self.stun_time_remaining = 3.0

    def draw(self, surface):
        if self.show_instructions:
            surface.fill((0, 0, 0))
            title_font = pygame.font.SysFont("arial", 80)
            text_font = pygame.font.SysFont("arial", 40)
            small_font = pygame.font.SysFont("arial", 35)

            title = title_font.render("DUNGEON EXPLORER", True, (255, 255, 255))
            surface.blit(title, (BASE_WIDTH // 2 - title.get_width() // 2, 30))

            y_pos = 130
            line_height = 50

            # Goal
            goal_text = text_font.render("GOAL: Collect yellow dots to earn points!", True, (255, 255, 0))
            surface.blit(goal_text, (50, y_pos))
            y_pos += line_height

            # Timer
            timer_text = text_font.render("60 second time limit", True, (255, 0, 0))
            surface.blit(timer_text, (50, y_pos))
            y_pos += line_height + 20

            # Enemies
            enemies_title = text_font.render("ENEMIES:", True, (255, 200, 100))
            surface.blit(enemies_title, (50, y_pos))
            y_pos += line_height - 10

            red_text = small_font.render("Red (slow) - Instant death!", True, (255, 100, 100))
            surface.blit(red_text, (100, y_pos))
            y_pos += 45

            purple_text = small_font.render("Purple (medium) - Lose 4 points", True, (200, 150, 255))
            surface.blit(purple_text, (100, y_pos))
            y_pos += 45

            orange_text = small_font.render("Orange (fast) - Stun for 3 seconds", True, (255, 200, 100))
            surface.blit(orange_text, (100, y_pos))
            y_pos += 45

            powerup_text = small_font.render("Green - +5 seconds", True, (100, 255, 100))
            surface.blit(powerup_text, (100, y_pos))
            y_pos += 45

            speed_text = small_font.render("Blue - 1.5x speed for 6 seconds", True, (100, 180, 255))
            surface.blit(speed_text, (100, y_pos))
            y_pos += 60

            # Controls
            controls_title = text_font.render("CONTROLS:", True, (100, 200, 255))
            surface.blit(controls_title, (50, y_pos))
            y_pos += line_height - 10

            arrow_text = small_font.render("Arrow keys to move", True, (200, 200, 200))
            surface.blit(arrow_text, (100, y_pos))
            y_pos += 45

            esc_text = small_font.render("ESC to return to menu", True, (200, 200, 200))
            surface.blit(esc_text, (100, y_pos))
            y_pos += 70

            # Start instruction
            start_text = text_font.render("Press ENTER to start", True, (100, 255, 100))
            surface.blit(start_text, (BASE_WIDTH // 2 - start_text.get_width() // 2, BASE_HEIGHT - 80))
            return

        if self.game_over:
            surface.fill((0, 0, 0))
            game_over_text = self.font.render("Time's Up!", True, (255, 255, 255))
            instruction_text = self.font.render("Press ENTER to play again", True, (200, 200, 200))
            final_score_text = self.font.render(f"Final Score: {self.score}", True, (255, 255, 0))
            surface.blit(game_over_text, (BASE_WIDTH // 2 - game_over_text.get_width() // 2, BASE_HEIGHT // 2 - game_over_text.get_height() // 2 - 50))
            surface.blit(instruction_text, (BASE_WIDTH // 2 - instruction_text.get_width() // 2, BASE_HEIGHT // 2 - instruction_text.get_height() // 2 + 50))
            surface.blit(final_score_text, (BASE_WIDTH // 2 - final_score_text.get_width() // 2, BASE_HEIGHT // 2 - final_score_text.get_height() // 2 + 150))
            return

        surface.fill((50, 80, 120))

        # Draw timer
        timer_text = self.font.render(f"Time: {int(self.timer)}", True, (255, 0, 0))
        surface.blit(timer_text, (10, 10))

        # Draw score
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 0))
        surface.blit(score_text, (10, 80))

        tile_colors = [
            (70, 110, 140),
            (90, 130, 170),
            (110, 150, 190),
            (130, 170, 210),
        ]

        cam_x = self.player_x - self.viewport_width // 2
        cam_y = self.player_y - self.viewport_height // 2

        cam_x = max(0, min(self.map_width - self.viewport_width, cam_x))
        cam_y = max(0, min(self.map_height - self.viewport_height, cam_y))

        for y in range(self.viewport_height):
            for x in range(self.viewport_width):
                wx = cam_x + x
                wy = cam_y + y

                rect = pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )

                # 🌑 nooit gezien
                if (wx, wy) not in self.explored:
                    pygame.draw.rect(surface, (0, 0, 0), rect)
                    continue

                color = tile_colors[(wx + wy) % len(tile_colors)]

                # 🌘 niet zichtbaar nu
                if (wx, wy) not in self.visible:
                    color = (40, 40, 40)

                # if wx == self.player_x and wy == self.player_y:
                #     color = (220, 220, 60)

                pygame.draw.rect(surface, color, rect)

                if (wx, wy) in self.walls:
                    wall_color = (30, 30, 30)
                    if (wx, wy) not in self.visible:
                        wall_color = (15, 15, 15)
                    pygame.draw.rect(surface, wall_color, rect)

                pygame.draw.rect(surface, (80, 80, 80), rect, 1)

        # Draw enemies
        for enemy in self.enemies:
            ex = enemy.x - cam_x
            ey = enemy.y - cam_y
            if 0 <= ex < self.viewport_width and 0 <= ey < self.viewport_height:
                if (enemy.x, enemy.y) in self.visible:
                    enemy_x_pos = ex * self.tile_size + self.tile_size // 2
                    enemy_y_pos = ey * self.tile_size + self.tile_size // 2
                    if enemy.type == 1:
                        pygame.draw.circle(surface, (255, 0, 0), (enemy_x_pos, enemy_y_pos), 7)  # Red
                    elif enemy.type == 2:
                        pygame.draw.circle(surface, (200, 100, 255), (enemy_x_pos, enemy_y_pos), 6)  # Purple
                    elif enemy.type == 3:
                        pygame.draw.circle(surface, (255, 165, 0), (enemy_x_pos, enemy_y_pos), 5)  # Orange

        # Draw dots
        for dot in self.dots:
            dx = dot[0] - cam_x
            dy = dot[1] - cam_y
            if 0 <= dx < self.viewport_width and 0 <= dy < self.viewport_height:
                if dot in self.visible:
                    dot_x = dx * self.tile_size + self.tile_size // 2
                    dot_y = dy * self.tile_size + self.tile_size // 2
                    pygame.draw.circle(surface, (255, 255, 0), (dot_x, dot_y), 5)

        # Draw power-ups
        for pos, powerup_type in self.powerups.items():
            px = pos[0] - cam_x
            py = pos[1] - cam_y
            if 0 <= px < self.viewport_width and 0 <= py < self.viewport_height:
                if pos in self.visible:
                    image = self.powerup_images.get(powerup_type)
                    if image:
                        powerup_rect = image.get_rect()
                        powerup_rect.topleft = (px * self.tile_size, py * self.tile_size)
                        surface.blit(image, powerup_rect)
                    else:
                        powerup_x = px * self.tile_size + self.tile_size // 2
                        powerup_y = py * self.tile_size + self.tile_size // 2
                        if powerup_type == 'time':
                            pygame.draw.circle(surface, (100, 255, 100), (powerup_x, powerup_y), 6)
                        else:
                            pygame.draw.circle(surface, (100, 180, 255), (powerup_x, powerup_y), 6)
                        pygame.draw.circle(surface, (255, 255, 255), (powerup_x, powerup_y), 2)

        # player
        player_x_pos = (self.player_x - cam_x) * self.tile_size
        player_y_pos = (self.player_y - cam_y) * self.tile_size

        if self.player_image:
            angle = {'right': 270, 'down': 180, 'left': 90, 'up': 0}[self.facing]
            rotated_image = pygame.transform.rotate(self.player_image, angle)
            rect = rotated_image.get_rect(center=(player_x_pos + self.tile_size // 2, player_y_pos + self.tile_size // 2))
            surface.blit(rotated_image, rect)
        else:
            player_rect = pygame.Rect(
                player_x_pos + 4,
                player_y_pos + 4,
                self.tile_size - 8,
                self.tile_size - 8
            )
            pygame.draw.rect(surface, (220, 30, 30), player_rect)


class Enemy:
    def __init__(self, x, y, enemy_type, walls):
        self.x = x
        self.y = y
        self.type = enemy_type  # 1 = instant death (slow), 2 = point drain (medium), 3 = stun (fast)
        self.walls = walls
        self.vision_radius = 6

        # Movement speed varies by type
        if enemy_type == 1:
            self.move_delay = 0.8  # Slow
        elif enemy_type == 2:
            self.move_delay = 0.3  # Normal
        else:  # type 3
            self.move_delay = 0.4  # Fast

        self.time_since_move = 0.0
        self.attack_cooldown = 5.0
        self.last_attack_time = 0.0

    def update(self, dt, player_x, player_y, has_line_of_sight_func):
        self.time_since_move += dt
        self.last_attack_time += dt

        # Calculate distance to player
        distance = math.sqrt((self.x - player_x) ** 2 + (self.y - player_y) ** 2)

        # Check if player is in vision range and has line of sight
        if distance <= self.vision_radius and has_line_of_sight_func(self.x, self.y, player_x, player_y):
            # Chase player
            if self.time_since_move >= self.move_delay:
                self.move_towards_player(player_x, player_y)
                self.time_since_move = 0.0

    def move_towards_player(self, player_x, player_y):
        new_x = self.x
        new_y = self.y

        # Move closer to player
        if self.x < player_x:
            new_x += 1
        elif self.x > player_x:
            new_x -= 1

        if self.y < player_y:
            new_y += 1
        elif self.y > player_y:
            new_y -= 1

        # Check wall collision
        if (new_x, new_y) not in self.walls:
            self.x = new_x
            self.y = new_y

    def can_attack(self):
        return self.last_attack_time >= self.attack_cooldown

    def attack(self):
        self.last_attack_time = 0.0