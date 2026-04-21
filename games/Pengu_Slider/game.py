import pygame
import math
import random
from enum import Enum
from core.scene import Scene
from settings import BASE_WIDTH, BASE_HEIGHT
import os
import json
from ui.lockscreen import LockScreen

pygame.init()

FPS = 60
BASE_WINDOW_WIDTH = BASE_WIDTH
BASE_WINDOW_HEIGHT = BASE_HEIGHT
BASE_ICE_WIDTH = int(BASE_WINDOW_WIDTH * 0.7)
BASE_ICE_HEIGHT = int(BASE_WINDOW_HEIGHT * 0.8)

MAX_SPEED = 60  # 4x harder than before
FRICTION = 0.98  # Ice friction (slippery)
ACCELERATION = 6
MAX_PLAYERS = 50  # Support many players

class GameState(Enum):
    START_SCREEN = 0
    WAITING_FOR_INPUT = 1
    MOVING = 2
    GAME_OVER = 3
    SETTINGS = 4

class Player:
    def __init__(self, x, y, color, player_id, is_human=False, radius=25):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.vx = 0  # velocity x
        self.vy = 0  # velocity y
        self.player_id = player_id
        self.alive = True
        self.is_human = is_human
        self.ai_direction = None
        self.scheduled_direction = 0  # Direction to move this round
        self.scheduled_force = 0  # Force to use this round (0-1)
        self.last_direction = 0  # Last direction the player was pushed
        
        # Maak direct de pixel-art pinguïn aan bij het spawnen
        self.colored_penguin = self.create_pixel_penguin()
        
    def create_pixel_penguin(self):
        """Maakt een pinguïn pixel voor pixel, gebaseerd op de referentiefoto."""
        pixel_art = [
            "........ZZZZZZZZZ........",
            "......ZZCCCCCCCCCZZ......",
            ".....ZCCCCCCCCCCCCCZ.....",
            "....ZCCCCCWWWWWCCCCCZ....",
            "...ZCCCCCWWWWWWWCCCCCZ...",
            "...ZCCCCWZZWWWZZWCCCCZ...",
            "...ZCCCCWZZWWWZZWCCCCZ...",
            "...ZCCCCWWWOOOWWWCCCCZ...",
            "...ZCCCCCWOOOOOWCCCCCZ...",
            "....ZCCCCCWOOOWCCCCCZ....",
            "....ZCCCCCCWWWCCCCCCZ....",
            "...ZCCCCCCCCCCCCCCCCCZ...",
            "..ZCCZCCCWWWWWWWCCCZCCZ..",
            "..ZCCZ.ZCCWWWWWCCZ.ZCCZ..",
            ".ZCCZ..ZCCWWWWWCCZ..ZCCZ.",
            ".ZCCZ..ZCCWWWWWCCZ..ZCCZ.",
            ".ZZZZ..ZCCWWWWWCCZ..ZZZZ.",
            ".......ZZCCWWWCCZZ.......",
            "........ZZCCCCCZZ........",
            "......ZOOZZZZZZZOOZ......",
            ".....ZOOOOZ...ZOOOOZ.....",
            ".....ZOOOOZ...ZOOOOZ.....",
            "......ZZZZ.....ZZZZ......"
        ]
        
        width = len(pixel_art[0])
        height = len(pixel_art)
        
        # Maak een onzichtbaar canvas
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Bepaal de kleuren voor de letters
        color_map = {
            '.': (0, 0, 0, 0),        # Transparant
            'Z': (20, 25, 40, 255),   # Donkerblauw/Zwart (randen)
            'W': (240, 240, 240, 255),# Wit (gezicht)
            'O': (255, 150, 0, 255),  # Oranje (snavel/voeten)
            'C': self.color           # De unieke kleur van deze speler
        }
        
        # Teken de pixels
        for y, row in enumerate(pixel_art):
            for x, char in enumerate(row):
                kleur = color_map.get(char, (0, 0, 0, 0))
                surface.set_at((x, y), kleur)
        
        # Schaal de pinguïn op naar de spelergrootte
        size = int(self.radius * 2)
        scaled_penguin = pygame.transform.scale(surface, (size, size))
        
        # Draai hem een kwartslag zodat de richtingshoeken kloppen met pygame
        scaled_penguin = pygame.transform.rotate(scaled_penguin, -90)
        
        return scaled_penguin
        
    def update(self):
        # Apply friction
        self.vx *= FRICTION
        self.vy *= FRICTION
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Stop if moving too slow
        if abs(self.vx) < 0.1:
            self.vx = 0
        if abs(self.vy) < 0.1:
            self.vy = 0
    
    def push(self, direction_angle, force=1.0):
        """Push the player in a direction with given force (0-1)"""
        self.last_direction = direction_angle  # Store direction for penguin rotation
        rad = math.radians(direction_angle)
        actual_force = ACCELERATION * force
        self.vx += math.cos(rad) * actual_force
        self.vy += math.sin(rad) * actual_force
        
        # Cap speed
        speed = math.sqrt(self.vx**2 + self.vy**2)
        if speed > MAX_SPEED:
            self.vx = (self.vx / speed) * MAX_SPEED
            self.vy = (self.vy / speed) * MAX_SPEED
    
    def is_on_ice(self, game):
        """Check if player is still on the ice (circular arena)"""
        # Calculate circle center
        center_x = game.ice_x + game.ice_width / 2
        center_y = game.ice_y + game.ice_height / 2
        radius = game.get_circle_radius()
        
        # Check if player's CENTER is still within the circle
        distance = math.sqrt((self.x - center_x)**2 + (self.y - center_y)**2)
        return distance < radius
    
    def get_distance_to(self, other_x, other_y):
        """Calculate distance to a point"""
        dx = other_x - self.x
        dy = other_y - self.y
        return math.sqrt(dx**2 + dy**2)
    
    def get_angle_to(self, other_x, other_y):
        """Get angle to a point"""
        dx = other_x - self.x
        dy = other_y - self.y
        return math.degrees(math.atan2(dy, dx))
    
    def draw(self, screen, show_direction=None, direction_angle=None, force=0):
        if self.alive:
            # Use direction_angle if provided, otherwise use last known direction
            current_angle = direction_angle if direction_angle is not None else self.last_direction
            
            # Rotate penguin to face direction of movement
            rotation_angle = -current_angle
            rotated_penguin = pygame.transform.rotate(self.colored_penguin, rotation_angle)
            rect = rotated_penguin.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(rotated_penguin, rect)
            
            # Draw player number
            font = pygame.font.Font(None, 24)
            text = font.render(str(self.player_id + 1), True, (255, 255, 255))
            text_rect = text.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(text, text_rect)
            
            # Show direction arrow if aiming
            if show_direction and direction_angle is not None:
                arrow_length = 40 + (force * 80)  # Length based on force (40-120)
                rad = math.radians(direction_angle)
                end_x = self.x + math.cos(rad) * arrow_length
                end_y = self.y + math.sin(rad) * arrow_length
                pygame.draw.line(screen, (255, 255, 0), (self.x, self.y), (end_x, end_y), 5)
                # Arrowhead
                angle_left = direction_angle + 150
                angle_right = direction_angle - 150
                head_len = 15
                left_x = end_x + math.cos(math.radians(angle_left)) * head_len
                left_y = end_y + math.sin(math.radians(angle_left)) * head_len
                right_x = end_x + math.cos(math.radians(angle_right)) * head_len
                right_y = end_y + math.sin(math.radians(angle_right)) * head_len
                pygame.draw.line(screen, (255, 255, 0), (end_x, end_y), (left_x, left_y), 4)
                pygame.draw.line(screen, (255, 255, 0), (end_x, end_y), (right_x, right_y), 4)


class AdventureGame(Scene):
    def __init__(self, manager, num_players=4):
        super().__init__(manager)
        
        # Use base surface dimensions for scaling consistency
        if num_players is None:
            num_players = 4
        
        size_factor = max(0.6, min(1.5, 0.4 + (num_players / MAX_PLAYERS) * 1.0))
        
        # Use base window dimensions (will scale with rendering pipeline)
        self.window_width = BASE_WINDOW_WIDTH
        self.window_height = BASE_WINDOW_HEIGHT
        self.ice_width = int(self.window_width * 0.7)
        self.ice_height = int(self.window_height * 0.8)
        self.ice_x = (self.window_width - self.ice_width) // 2
        self.ice_y = (self.window_height - self.ice_height) // 2
        
        # Calculate player radius based on number of players (fewer players = bigger blobs)
        self.player_radius = int(4 + 9 * (MAX_PLAYERS - num_players) / MAX_PLAYERS)
        
        self.num_players = num_players
        self.players = []
        self.state = GameState.START_SCREEN
        self.direction_angle = 0
        self.current_force = 0.5
        self.round_counter = 0
        self.colors = self.generate_colors(num_players)
        self.circle_shrink_factor = 1.0  # Track circle radius shrinking per round
        self.wave_offset = 0
        self._win_counted = False  # Track if win has been counted
        
        # Start screen variables
        self.selected_players = 4
        self.button_play_rect = None
    
    def generate_colors(self, num_players):
        """Generate unique colors for all players"""
        colors = []
        for i in range(num_players):
            hue = (i / max(num_players, 1)) * 360
            saturation = 0.8
            value = 1.0
            
            # HSV to RGB conversion
            h = (hue / 60) % 6
            c = value * saturation
            x = c * (1 - abs(h % 2 - 1))
            m = value - c
            
            if 0 <= h < 1:
                r, g, b = c, x, 0
            elif 1 <= h < 2:
                r, g, b = x, c, 0
            elif 2 <= h < 3:
                r, g, b = 0, c, x
            elif 3 <= h < 4:
                r, g, b = 0, x, c
            elif 4 <= h < 5:
                r, g, b = x, 0, c
            else:
                r, g, b = c, 0, x
            
            # Convert to 0-255 range and clamp
            r = max(0, min(255, int((r + m) * 255)))
            g = max(0, min(255, int((g + m) * 255)))
            b = max(0, min(255, int((b + m) * 255)))
            
            colors.append((r, g, b))
        return colors
    
    def get_random_position(self, placed_positions):
        """Get a random position on ice (circular arena) without overlapping with other players"""
        min_distance = self.player_radius * 2 + 10
        max_attempts = 100
        
        # Calculate circle parameters (initial full size)
        center_x = self.ice_x + self.ice_width / 2
        center_y = self.ice_y + self.ice_height / 2
        max_radius = min(self.ice_width, self.ice_height) / 2 - self.player_radius - 5
        
        for _ in range(max_attempts):
            # Generate random point in circle using polar coordinates
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, max_radius)
            x = center_x + distance * math.cos(angle)
            y = center_y + distance * math.sin(angle)
            
            # Check if this position overlaps with any existing player
            valid = True
            for px, py in placed_positions:
                distance_to_other = math.sqrt((x - px)**2 + (y - py)**2)
                if distance_to_other < min_distance:
                    valid = False
                    break
            
            if valid:
                return x, y
        
        # Fallback: place somewhere in center
        return (center_x, center_y)
    
    def init_players(self):
        """Initialize players at the ice arena with random positions"""
        placed_positions = []
        
        for i in range(self.num_players):
            is_human = (i == 0)  # Only first player is human
            x, y = self.get_random_position(placed_positions)
            placed_positions.append((x, y))
            player = Player(x, y, self.colors[i], i, is_human, self.player_radius)
            self.players.append(player)
    
    def start_game(self):
        """Initialize game with selected number of players"""
        self.num_players = self.selected_players
        self.colors = self.generate_colors(self.num_players)
        self.players = []
        self.init_players()
        self.state = GameState.WAITING_FOR_INPUT
        self.round_counter = 0
        self.circle_shrink_factor = 1.0  # Reset circle to full size
        self._win_counted = False  # Reset win counter flag
    
    def draw_start_screen(self):
        """Draw the start screen"""
        self.screen.fill((25, 50, 120))
        
        font_large = pygame.font.Font(None, 48)
        font_medium = pygame.font.Font(None, 28)
        font_small = pygame.font.Font(None, 20)
        
        # Title
        title = font_large.render("ICE SUMO", True, (255, 255, 100))
        title_rect = title.get_rect(center=(self.window_width // 2, 30))
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = font_small.render("Last One Standing Wins!", True, (200, 230, 255))
        subtitle_rect = subtitle.get_rect(center=(self.window_width // 2, 65))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Player count selector
        label = font_medium.render("Number of Players:", True, (255, 255, 255))
        label_rect = label.get_rect(center=(self.window_width // 2, 110))
        self.screen.blit(label, label_rect)
        
        # Decrease button
        decrease_rect = pygame.Rect(self.window_width // 2 - 120, 145, 50, 40)
        pygame.draw.rect(self.screen, (100, 150, 200), decrease_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), decrease_rect, 2)
        decrease_text = font_medium.render("<", True, (255, 255, 255))
        self.screen.blit(decrease_text, (decrease_rect.x + 15, decrease_rect.y + 8))
        
        # Number display
        number = font_large.render(str(self.selected_players), True, (255, 255, 100))
        number_rect = number.get_rect(center=(self.window_width // 2, 165))
        self.screen.blit(number, number_rect)
        
        # Increase button
        increase_rect = pygame.Rect(self.window_width // 2 + 70, 145, 50, 40)
        pygame.draw.rect(self.screen, (100, 150, 200), increase_rect)
        pygame.draw.rect(self.screen, (255, 255, 255), increase_rect, 2)
        increase_text = font_medium.render(">", True, (255, 255, 255))
        self.screen.blit(increase_text, (increase_rect.x + 12, increase_rect.y + 8))
        
        # Play button
        self.button_play_rect = pygame.Rect(self.window_width // 2 - 60, 210, 120, 40)
        pygame.draw.rect(self.screen, (50, 200, 100), self.button_play_rect)
        pygame.draw.rect(self.screen, (100, 255, 150), self.button_play_rect, 3)
        play_text = font_medium.render("PLAY", True, (255, 255, 255))
        play_text_rect = play_text.get_rect(center=self.button_play_rect.center)
        self.screen.blit(play_text, play_text_rect)
        
        pygame.display.flip()
        return decrease_rect, increase_rect
    
    def draw_end_screen(self):
        """Draw the end game screen"""
        self.screen.fill((25, 50, 120))
        
        font_large = pygame.font.Font(None, 66)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 36)
        
        # Get winner info
        alive = self.get_alive_players()
        human_player = next((p for p in alive if p.is_human), None)
        
        if human_player:
            result_text = "YOU WIN!"
            result_color = (100, 255, 100)
            detail = "You are the last one standing!"
        else:
            result_text = "GAME OVER"
            result_color = (255, 100, 100)
            detail = "Better luck next time!"
        
        # Title
        title = font_large.render(result_text, True, result_color)
        title_rect = title.get_rect(center=(self.window_width // 2, 100))
        self.screen.blit(title, title_rect)
        
        # Detail
        detail_text = font_small.render(detail, True, (200, 230, 255))
        detail_rect = detail_text.get_rect(center=(self.window_width // 2, 200))
        self.screen.blit(detail_text, detail_rect)
        
        # Restart button
        restart_rect = pygame.Rect(self.window_width // 2 - 150, 350, 300, 70)
        pygame.draw.rect(self.screen, (50, 200, 100), restart_rect)
        pygame.draw.rect(self.screen, (100, 255, 150), restart_rect, 4)
        restart_text = font_medium.render("PLAY AGAIN", True, (255, 255, 255))
        restart_text_rect = restart_text.get_rect(center=restart_rect.center)
        self.screen.blit(restart_text, restart_text_rect)
        
        # Settings button
        settings_rect = pygame.Rect(self.window_width // 2 - 150, 470, 300, 70)
        pygame.draw.rect(self.screen, (100, 150, 200), settings_rect)
        pygame.draw.rect(self.screen, (150, 200, 255), settings_rect, 4)
        settings_text = font_medium.render("SETTINGS", True, (255, 255, 255))
        settings_text_rect = settings_text.get_rect(center=settings_rect.center)
        self.screen.blit(settings_text, settings_text_rect)
        
        pygame.display.flip()
        return restart_rect, settings_rect
    
    def get_alive_players(self):
        """Get list of alive players"""
        return [p for p in self.players if p.alive]
    
    def get_circle_radius(self):
        """Get the current circle radius, shrinking after each round"""
        base_radius = min(self.ice_width, self.ice_height) / 2
        shrink_factor = max(0.15, self.circle_shrink_factor)
        return base_radius * shrink_factor
    
    def cpu_decide_move(self, player):
        """AI decision making for CPU players - returns (direction, force)"""
        alive_players = self.get_alive_players()
        other_players = [p for p in alive_players if p.player_id != player.player_id]
        
        # Calculate distance from center and safety
        center_x = self.ice_x + self.ice_width / 2
        center_y = self.ice_y + self.ice_height / 2
        distance_from_center = math.sqrt((player.x - center_x)**2 + (player.y - center_y)**2)
        circle_radius = self.get_circle_radius()
        
        # Calculate safe margin - how close to edge the player can get
        safe_margin = player.radius + 20
        danger_distance = circle_radius - safe_margin
        is_near_edge = distance_from_center > danger_distance * 0.8
        is_critical_edge = distance_from_center > danger_distance
        
        # First priority: if critical edge, move back to center
        if is_critical_edge:
            direction = math.degrees(math.atan2(center_y - player.y, center_x - player.x))
            force = 0.3 + 0.2 * random.random()
            return direction % 360, force
        
        # Calculate the maximum safe force based on distance to edge
        distance_to_edge = danger_distance - distance_from_center
        if distance_to_edge > 100:
            max_safe_force = 1.0
        elif distance_to_edge > 50:
            max_safe_force = 0.7
        elif distance_to_edge > 20:
            max_safe_force = 0.4
        else:
            max_safe_force = 0.2
        
        if not other_players:
            if is_near_edge:
                direction = math.degrees(math.atan2(center_y - player.y, center_x - player.x))
                force = min(max_safe_force, 0.2 + 0.2 * random.random())
            else:
                direction = random.randint(0, 360)
                force = min(max_safe_force, 0.2 + 0.4 * random.random())
            return direction % 360, force
        
        # Strategy based on distance from edge
        strategy = random.random()
        
        if strategy < 0.7:  # Chase strategy
            closest = min(other_players, key=lambda p: player.get_distance_to(p.x, p.y))
            direction = player.get_angle_to(closest.x, closest.y)
            direction += random.randint(-20, 20)
            
            if is_near_edge:
                base_force = 0.2 + 0.15 * random.random()
            else:
                base_force = 0.4 + 0.4 * random.random()
            
            force = min(max_safe_force, base_force)
        else:  # Evade strategy
            if is_near_edge:
                direction = math.degrees(math.atan2(center_y - player.y, center_x - player.x))
                force = min(max_safe_force, 0.2 + 0.2 * random.random())
            else:
                closest = min(other_players, key=lambda p: player.get_distance_to(p.x, p.y))
                direction = player.get_angle_to(closest.x, closest.y)
                direction += 180
                direction += random.randint(-20, 20)
                force = min(max_safe_force, 0.3 + 0.3 * random.random())
        
        return direction % 360, force
    
    def check_collisions(self):
        """Check and handle collisions between players with improved physics."""
        players = self.get_alive_players()
        STATIONARY_THRESHOLD = 0.5  # Players slower than this are considered stationary

        for i in range(len(players)):
            for j in range(i + 1, len(players)):
                p1, p2 = players[i], players[j]
                
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                dist_squared = dx**2 + dy**2
                
                # If circles overlap
                if 0 < dist_squared < (p1.radius + p2.radius)**2:
                    dist = math.sqrt(dist_squared)
                    
                    # --- Overlap Resolution ---
                    # Push players apart so they don't stick together
                    nx = dx / dist  # Normal vector x from p1 to p2
                    ny = dy / dist  # Normal vector y from p1 to p2
                    overlap = (p1.radius + p2.radius - dist) / 2.0 + 1.0
                    p1.x -= nx * overlap
                    p1.y -= ny * overlap
                    p2.x += nx * overlap
                    p2.y += ny * overlap

                    # --- Collision Physics ---
                    speed1 = math.sqrt(p1.vx**2 + p1.vy**2)
                    speed2 = math.sqrt(p2.vx**2 + p2.vy**2)

                    p1_stationary = speed1 < STATIONARY_THRESHOLD
                    p2_stationary = speed2 < STATIONARY_THRESHOLD

                    # Case 1: A moving player hits a stationary player
                    # The stationary player gets the full velocity, the moving one stops.
                    if p1_stationary and not p2_stationary:
                        p1.vx, p1.vy = p2.vx, p2.vy
                        p2.vx, p2.vy = 0, 0
                    elif not p1_stationary and p2_stationary:
                        p2.vx, p2.vy = p1.vx, p1.vy
                        p1.vx, p1.vy = 0, 0
                    
                    # Case 2: Both players are moving
                    elif not p1_stationary and not p2_stationary:
                        # Relative velocity along the collision normal
                        vel_along_normal = (p2.vx - p1.vx) * nx + (p2.vy - p1.vy) * ny

                        # Only resolve collision if they are moving towards each other
                        if vel_along_normal < 0:
                            
                            # Decompose velocities into normal and tangential components
                            v1n_scalar = p1.vx * nx + p1.vy * ny
                            v1tx = p1.vx - v1n_scalar * nx
                            v1ty = p1.vy - v1n_scalar * ny
                            
                            v2n_scalar = p2.vx * nx + p2.vy * ny
                            v2tx = p2.vx - v2n_scalar * nx
                            v2ty = p2.vy - v2n_scalar * ny

                            # Dot product of velocities to check for head-on vs rear-end
                            dot_product = p1.vx * p2.vx + p1.vy * p2.vy

                            if dot_product < 0: # Head-on collision
                                # They bounce off each other by swapping normal velocities.
                                new_v1n_scalar = v2n_scalar
                                new_v2n_scalar = v1n_scalar
                            else: # Rear-end collision
                                # The chaser (p1, since v1n_scalar > v2n_scalar) loses most 
                                # of its speed to the other player.
                                new_v1n_scalar = v1n_scalar * 0.2 + v2n_scalar * 0.8
                                new_v2n_scalar = v1n_scalar * 0.8 + v2n_scalar * 0.2
                            
                            # Recombine velocities from new normal and old tangential components
                            p1.vx = v1tx + new_v1n_scalar * nx
                            p1.vy = v1ty + new_v1n_scalar * ny
                            p2.vx = v2tx + new_v2n_scalar * nx
                            p2.vy = v2ty + new_v2n_scalar * ny

                    # Cap speed for both players after collision
                    for p in [p1, p2]:
                        speed = math.sqrt(p.vx**2 + p.vy**2)
                        if speed > MAX_SPEED:
                            p.vx = (p.vx / speed) * MAX_SPEED
                            p.vy = (p.vy / speed) * MAX_SPEED
    
    def update(self, dt):
        """Update game state"""
        if self.state == GameState.MOVING:
            for player in self.get_alive_players():
                player.update()
            
            self.check_collisions()
            
            for player in self.get_alive_players():
                if not player.is_on_ice(self):
                    player.alive = False
            
            all_stopped = all(
                player.vx == 0 and player.vy == 0 
                for player in self.get_alive_players()
            )
            
            if all_stopped:
                alive_count = len(self.get_alive_players())
                
                if alive_count <= 1:
                    self.state = GameState.GAME_OVER
                    # Count the win only once when transitioning to GAME_OVER
                    if not self._win_counted:
                        alive_players = self.get_alive_players()
                        if alive_players and alive_players[0].is_human:
                            self.wincount_up()
                        self._win_counted = True
                else:
                    self.state = GameState.WAITING_FOR_INPUT
                    self.round_counter += 1
                    if self.round_counter % 3 == 0:
                        self.circle_shrink_factor *= 0.9
                    for player in self.players:
                        player.scheduled_direction = 0
                        player.scheduled_force = 0
        
        elif self.state == GameState.WAITING_FOR_INPUT:
            human_player = next((p for p in self.get_alive_players() if p.is_human), None)
            
            for player in self.get_alive_players():
                if not player.is_human:
                    if player.scheduled_force == 0:
                        direction, force = self.cpu_decide_move(player)
                        player.scheduled_direction = direction
                        player.scheduled_force = force
            
            cpu_all_ready = all(
                p.scheduled_force > 0 for p in self.get_alive_players() if not p.is_human
            )
            
            if not human_player:
                if cpu_all_ready and len(self.get_alive_players()) > 0:
                    for player in self.get_alive_players():
                        player.push(player.scheduled_direction, player.scheduled_force)
                    self.state = GameState.MOVING
            else:
                if cpu_all_ready and human_player.scheduled_force > 0:
                    for player in self.get_alive_players():
                        player.push(player.scheduled_direction, player.scheduled_force)
                    self.state = GameState.MOVING
            
            # Handle continuous keyboard input for smooth control
            if human_player:
                keys = pygame.key.get_pressed()
                
                rotation_speed = 300 * dt  # 300 degrees per second
                force_speed = 0.4 * dt  # Change 0.4 per second
                
                if keys[pygame.K_LEFT]:
                    self.direction_angle -= rotation_speed
                    self.direction_angle %= 360
                if keys[pygame.K_RIGHT]:
                    self.direction_angle += rotation_speed
                    self.direction_angle %= 360
                
                if keys[pygame.K_UP]:
                    self.current_force = min(self.current_force + force_speed, 1.0)
                if keys[pygame.K_DOWN]:
                    self.current_force = max(self.current_force - force_speed, 0.1)
        
        self.wave_offset += 0.02
    
    def handle_events(self, event):
        """Handle player input"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from ui.home_menu import HomeMenu
                self.manager.set_scene(HomeMenu(self.manager))
                return
            
            if self.state == GameState.START_SCREEN:
                if event.key == pygame.K_LEFT:
                    self.selected_players = max(2, self.selected_players - 1)
                elif event.key == pygame.K_RIGHT:
                    self.selected_players = min(MAX_PLAYERS, self.selected_players + 1)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.start_game()
            
            if self.state == GameState.WAITING_FOR_INPUT:
                human_player = next((p for p in self.get_alive_players() if p.is_human), None)
                if human_player:
                    if event.key == pygame.K_SPACE:
                        human_player.scheduled_force = self.current_force
                        human_player.scheduled_direction = self.direction_angle
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Scale mouse position from screen space to base surface space
            from settings import screen
            screen_width = screen.get_width()
            screen_height = screen.get_height()
            scale_x = BASE_WINDOW_WIDTH / screen_width
            scale_y = BASE_WINDOW_HEIGHT / screen_height
            
            mouse_pos = event.pos
            scaled_mouse_x = mouse_pos[0] * scale_x
            scaled_mouse_y = mouse_pos[1] * scale_y
            scaled_mouse_pos = (scaled_mouse_x, scaled_mouse_y)
            
            if self.state == GameState.START_SCREEN:
                decrease_rect = pygame.Rect(self.window_width // 2 - 120, 145, 50, 40)
                increase_rect = pygame.Rect(self.window_width // 2 + 70, 145, 50, 40)
                
                if decrease_rect.collidepoint(scaled_mouse_pos):
                    self.selected_players = max(2, self.selected_players - 1)
                elif increase_rect.collidepoint(scaled_mouse_pos):
                    self.selected_players = min(MAX_PLAYERS, self.selected_players + 1)
                elif self.button_play_rect and self.button_play_rect.collidepoint(scaled_mouse_pos):
                    self.start_game()
            
            elif self.state == GameState.GAME_OVER:
                restart_rect = pygame.Rect(self.window_width // 2 - 150, 350, 300, 70)
                
                if restart_rect.collidepoint(scaled_mouse_pos):
                    self.state = GameState.START_SCREEN

    def draw_waves(self):
        """Draw animated wave background"""
        self.screen.fill((10, 30, 80))
        
        wave_color = (30, 80, 180)
        wave_height = 40
        
        for i in range(0, self.window_width, 100):
            y = self.window_height // 2 + wave_height * math.sin((i + self.wave_offset * 50) / 100)
            pygame.draw.line(self.screen, wave_color, (i, self.window_height // 2), (i, y), 3)
    
    def draw_pixelated_ice(self):
        """Draws the ice plateau with a retro, pixelated look."""
        center_x = self.ice_x + self.ice_width / 2
        center_y = self.ice_y + self.ice_height / 2
        current_radius = self.get_circle_radius()
        pixel_size = 12

        for x in range(self.ice_x, self.ice_x + self.ice_width, pixel_size):
            for y in range(self.ice_y, self.ice_y + self.ice_height, pixel_size):
                distance = math.sqrt((x + pixel_size / 2 - center_x)**2 + (y + pixel_size / 2 - center_y)**2)
                if distance < current_radius:
                    pygame.draw.rect(self.screen, (200, 230, 255), (x, y, pixel_size, pixel_size))
                    pygame.draw.rect(self.screen, (100, 150, 200), (x, y, pixel_size, pixel_size), 1)

    def draw(self, surface):
        """Draw the game"""
        self.screen = surface
        
        if self.state == GameState.START_SCREEN:
            self.draw_start_screen()
        elif self.state == GameState.GAME_OVER:
            self.draw_end_screen()
        else:
            # Drawing gameplay (WAITING_FOR_INPUT or MOVING states)
            self.draw_waves()
            self.draw_pixelated_ice()
            
            human_player = next((p for p in self.get_alive_players() if p.is_human), None)
            
            for player in self.players:
                if player.alive:
                    if self.state == GameState.WAITING_FOR_INPUT:
                        if player.is_human:
                            player.draw(self.screen, True, self.direction_angle, self.current_force)
                        else:
                            player.draw(self.screen)
                    else:
                        player.draw(self.screen)
            
            font = pygame.font.Font(None, 36)
            small_font = pygame.font.Font(None, 24)
            
            alive_count = len(self.get_alive_players())
            status_text = f"Players remaining: {alive_count}"
            
            if self.state == GameState.WAITING_FOR_INPUT:
                status_text += " | Planning phase"
                if human_player:
                    force_pct = int(self.current_force * 100)
                    angle_txt = int(self.direction_angle)
                    instruction = small_font.render(
                        f"←/→ to rotate ({angle_txt}°) | ↑/↓ for power ({force_pct}%) | SPACE to push", 
                        True, (255, 255, 255)
                    )
                    text_rect = instruction.get_rect()
                    text_rect.x = 5
                    text_rect.y = self.window_height - 35
                    pygame.draw.rect(self.screen, (0, 0, 0), text_rect.inflate(10, 10))
                    self.screen.blit(instruction, (10, self.window_height - 30))
            elif self.state == GameState.MOVING:
                status_text += " | Everyone moving!"
            
            text = font.render(status_text, True, (255, 255, 255))
            text_rect = text.get_rect()
            text_rect.x = 5
            text_rect.y = 5
            pygame.draw.rect(self.screen, (0, 0, 0), text_rect.inflate(10, 10))
            self.screen.blit(text, (10, 10))

    def get_user(self):
        # prefer manager's current_user if already set
        user = getattr(self.manager, 'current_user', None)
        if user:
            return user

        # fallback: create a LockScreen with the same manager and ask it
        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or 0
        except Exception:
            return 0

    def user_highscore(self, score):
        self.user = self.get_user()
        path = os.path.join("data", "users.json")
        target_user = self.user 
        
        try:
            with open(path, 'r') as file:
                data = json.load(file)
        except FileNotFoundError:
            print("User data not found")
            return
        
        found = False
        for player in data["users"]:
            if player["name"] == target_user:
                # Zorg dat highscores object bestaat
                if "highscores" not in player:
                    player["highscores"] = {}
                
                
                current = player["highscores"].get("Pengu", 0)
                if score > current:
                    player["highscores"]["Pengu"] = score
                found = True
                break
                
        if found:
            with open(path, 'w') as file:
                json.dump(data, file, indent=4)
            print(f"Score {score} opgeslagen voor {target_user}")
        else:
            print(f"Gebruiker {target_user} niet gevonden in JSON")

    def _save_highscore(self):
        # normalize score to tens
        best = (self.highscore // 10) * 10

        # update user's Highscore in data/users.json, keeping only the highest value
        path = os.path.join("data", "users.json")

        try:
            with open(path, "r", encoding="utf-8") as f:
                users_data = json.load(f)
        except Exception:
            users_data = {"users": []}

        target = self.user
        target_name = None
        if isinstance(target, dict):
            target_name = target.get("name")
        elif isinstance(target, str):
            target_name = target

        if target_name:
            updated = False
            for player in users_data.get("users", []):
                if player.get("name") == target_name:
                    if "highscores" not in player:
                        player["highscores"] = {}
                    
                    cur_val = player["highscores"].get("Pengu", 0)
                    try:
                        cur_val = int(cur_val)
                    except Exception:
                        cur_val = 0

                    if best > cur_val:
                        player["highscores"]["Pengu"] = best
                    else:
                        player["highscores"]["Pengu"] = cur_val

                    updated = True
                    break

            if updated:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(users_data, f, indent=4)
                except Exception:
                    pass

    def wincount_up(self):
        path = os.path.join("data", "users.json")
        user_to_find = self.get_user()
        
        print(f"DEBUG: Op zoek naar gebruiker: '{user_to_find}'")

        try:
            with open(path, "r", encoding="utf-8") as f:
                users_data = json.load(f)
        except Exception as e:
            print(f"DEBUG: Kan bestand niet lezen: {e}")
            return

        found = False
        if "users" in users_data:
            for user_entry in users_data['users']:
                current_username = user_to_find['name'] 
                
                if user_entry['name'] == current_username:
                    score = user_entry['highscores'].get('Pengu', 0)
                    user_entry['highscores']['Pengu'] = score + 1
                    
                    print(f"Succes! Score voor {current_username} is nu {score + 1}")
                    found = True
                    break
        
        if not found:
            print(f"DEBUG: Gebruiker '{user_to_find}' is NIET gevonden in de lijst.")

        # Opslaan
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(users_data, f, indent=4)
                print(f"DEBUG: Bestand succesvol opgeslagen in {os.path.abspath(path)}")
        except Exception as e:
            print(f"DEBUG: Fout bij opslaan: {e}")       
                        


