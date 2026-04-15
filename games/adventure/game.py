import random

import pygame

from core.scene import Scene
from settings import BASE_HEIGHT, BASE_WIDTH


class AdventureGame(Scene):
    DIFFICULTIES = [
        {
            "name": "Easy",
            "cols": 5,
            "rows": 4,
            "min_piece": 2,
            "max_piece": 4,
            "cell_size": 28,
        },
        {
            "name": "Medium",
            "cols": 6,
            "rows": 5,
            "min_piece": 3,
            "max_piece": 4,
            "cell_size": 22,
        },
        {
            "name": "Hard",
            "cols": 7,
            "rows": 6,
            "min_piece": 3,
            "max_piece": 5,
            "cell_size": 18,
        },
    ]

    COLORS = [
        (236, 112, 99),
        (93, 173, 226),
        (88, 214, 141),
        (245, 176, 65),
        (165, 105, 189),
        (72, 201, 176),
        (244, 208, 63),
        (234, 153, 153),
        (133, 193, 233),
        (249, 231, 159),
        (169, 223, 191),
        (245, 183, 177),
    ]

    def __init__(self, manager):
        super().__init__(manager)
        self.title_font = pygame.font.SysFont("arial", 28, bold=True)
        self.subtitle_font = pygame.font.SysFont("arial", 18, bold=True)
        self.body_font = pygame.font.SysFont("arial", 14)
        self.small_font = pygame.font.SysFont("arial", 12)

        self.state = "difficulty"
        self.selected_difficulty = 0
        self.current_difficulty = None

        self.tray_index = 0
        self.selected_piece_id = None
        self.active_anchor = [0, 0]
        self.selected_origin_anchor = None
        self.message = "Choose a difficulty to start."
        self.win_message = ""

        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.tray_rect = pygame.Rect(0, 0, 0, 0)
        self.board_origin = (0, 0)
        self.cell_size = 24

        self.pieces = []
        self.piece_lookup = {}
        self.placed_cells = {}

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            if self.state == "playing" and self.selected_piece_id is not None:
                self._cancel_selected_piece()
                return

            from ui.Games_menu import Game_Menu

            self.manager.set_scene(Game_Menu(self.manager))
            return

        if self.state == "difficulty":
            self._handle_difficulty_events(event.key)
            return

        if self.state == "won":
            self._handle_won_events(event.key)
            return

        if event.key == pygame.K_l and self.selected_piece_id is not None:
            self._rotate_selected_piece()
            return

        if event.key == pygame.K_b:
            self._handle_b_action()
            return

        if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            self._handle_direction(event.key)

    def update(self, dt):
        pass

    def draw(self, surface):
        self._draw_background(surface)

        if self.state == "difficulty":
            self._draw_difficulty_screen(surface)
        else:
            self._draw_game_screen(surface)
            if self.state == "won":
                self._draw_win_overlay(surface)

    def _handle_difficulty_events(self, key):
        if key == pygame.K_UP:
            self.selected_difficulty = (self.selected_difficulty - 1) % len(self.DIFFICULTIES)
        elif key == pygame.K_DOWN:
            self.selected_difficulty = (self.selected_difficulty + 1) % len(self.DIFFICULTIES)
        elif key in (pygame.K_RETURN, pygame.K_b):
            self._start_game(self.selected_difficulty)

    def _handle_won_events(self, key):
        if key in (pygame.K_RETURN, pygame.K_b):
            self._start_game(self.selected_difficulty)
        elif key == pygame.K_UP:
            self.selected_difficulty = (self.selected_difficulty - 1) % len(self.DIFFICULTIES)
            self._start_game(self.selected_difficulty)
        elif key == pygame.K_DOWN:
            self.selected_difficulty = (self.selected_difficulty + 1) % len(self.DIFFICULTIES)
            self._start_game(self.selected_difficulty)

    def _start_game(self, difficulty_index):
        config = self.DIFFICULTIES[difficulty_index]
        self.selected_difficulty = difficulty_index
        self.current_difficulty = config
        self.state = "playing"
        self.tray_index = 0
        self.selected_piece_id = None
        self.active_anchor = [0, 0]
        self.selected_origin_anchor = None
        self.message = "Pick a block with B, move it with the D-pad, place it with B."
        self.win_message = ""

        self.cell_size = config["cell_size"]
        self._build_layout(config)

    def _build_layout(self, config):
        cols = config["cols"]
        rows = config["rows"]

        board_pixel_width = cols * self.cell_size
        board_pixel_height = rows * self.cell_size

        board_x = 26
        board_y = (BASE_HEIGHT - board_pixel_height) // 2 + 10
        tray_x = board_x + board_pixel_width + 26
        tray_y = 46
        tray_width = BASE_WIDTH - tray_x - 16
        tray_height = BASE_HEIGHT - 76

        self.board_origin = (board_x, board_y)
        self.board_rect = pygame.Rect(board_x, board_y, board_pixel_width, board_pixel_height)
        self.tray_rect = pygame.Rect(tray_x, tray_y, tray_width, tray_height)

        self.pieces = self._generate_pieces(config)
        self.piece_lookup = {piece["id"]: piece for piece in self.pieces}
        self.placed_cells = {}

    def _generate_pieces(self, config):
        cols = config["cols"]
        rows = config["rows"]
        cells = [(x, y) for y in range(rows) for x in range(cols)]
        remaining = set(cells)

        target_sizes = self._build_piece_sizes(
            len(cells), config["min_piece"], config["max_piece"]
        )
        random.shuffle(target_sizes)

        pieces = []
        for piece_id, target_size in enumerate(target_sizes):
            seed = random.choice(tuple(remaining))
            group = {seed}

            while len(group) < target_size:
                frontier = []
                for cell in group:
                    for neighbor in self._neighbors(cell, cols, rows):
                        if neighbor in remaining and neighbor not in group:
                            frontier.append(neighbor)

                if not frontier:
                    break

                group.add(random.choice(frontier))

            remaining -= group

            if remaining and len(remaining) <= 2:
                extra_cells = set(remaining)
                group.update(extra_cells)
                remaining.clear()

            normalized = self._normalize_shape(group)
            rotation = random.randint(0, 3)

            pieces.append(
                {
                    "id": piece_id,
                    "base_cells": normalized,
                    "rotation": rotation,
                    "placed_at": None,
                    "color": self.COLORS[piece_id % len(self.COLORS)],
                }
            )

            if not remaining:
                break

        if remaining:
            pieces.append(
                {
                    "id": len(pieces),
                    "base_cells": self._normalize_shape(remaining),
                    "rotation": random.randint(0, 3),
                    "placed_at": None,
                    "color": self.COLORS[len(pieces) % len(self.COLORS)],
                }
            )

        return pieces

    def _build_piece_sizes(self, total_cells, minimum, maximum):
        sizes = []
        remaining = total_cells

        while remaining > 0:
            allowed = []
            for size in range(minimum, maximum + 1):
                if size > remaining:
                    continue

                leftover = remaining - size
                if leftover == 1:
                    continue

                allowed.append(size)

            if not allowed:
                sizes.append(remaining)
                break

            size = random.choice(allowed)
            sizes.append(size)
            remaining -= size

        return sizes

    def _neighbors(self, cell, cols, rows):
        x, y = cell
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                yield (nx, ny)

    def _normalize_shape(self, cells):
        min_x = min(x for x, _ in cells)
        min_y = min(y for _, y in cells)
        normalized = [(x - min_x, y - min_y) for x, y in cells]
        normalized.sort()
        return normalized

    def _rotated_cells(self, piece):
        cells = piece["base_cells"]
        rotation = piece["rotation"] % 4
        rotated = cells

        for _ in range(rotation):
            rotated = [(-y, x) for x, y in rotated]

        min_x = min(x for x, _ in rotated)
        min_y = min(y for _, y in rotated)
        normalized = [(x - min_x, y - min_y) for x, y in rotated]
        normalized.sort()
        return normalized

    def _handle_direction(self, key):
        if self.selected_piece_id is None:
            self._move_tray_focus(key)
        else:
            self._move_selected_piece(key)

    def _move_tray_focus(self, key):
        total = len(self.pieces)
        if total == 0:
            return

        columns = self._tray_columns()
        rows = (total + columns - 1) // columns
        row = self.tray_index // columns
        col = self.tray_index % columns

        if key == pygame.K_LEFT:
            if col > 0:
                self.tray_index -= 1
        elif key == pygame.K_RIGHT:
            if col < columns - 1 and self.tray_index + 1 < total:
                self.tray_index += 1
        elif key == pygame.K_UP:
            if row > 0:
                self.tray_index -= columns
        elif key == pygame.K_DOWN:
            if row + 1 < rows and self.tray_index + columns < total:
                self.tray_index += columns

    def _move_selected_piece(self, key):
        piece = self.piece_lookup[self.selected_piece_id]
        dx = 0
        dy = 0

        if key == pygame.K_LEFT:
            dx = -1
        elif key == pygame.K_RIGHT:
            dx = 1
        elif key == pygame.K_UP:
            dy = -1
        elif key == pygame.K_DOWN:
            dy = 1

        self.active_anchor[0] += dx
        self.active_anchor[1] += dy
        self._clamp_anchor(piece)

    def _handle_b_action(self):
        if self.selected_piece_id is None:
            self._select_piece_from_tray()
        else:
            self._place_selected_piece()

    def _select_piece_from_tray(self):
        if not self.pieces:
            return

        piece = self.pieces[self.tray_index]
        self.selected_origin_anchor = piece["placed_at"]
        if piece["placed_at"] is not None:
            self.active_anchor = [piece["placed_at"][0], piece["placed_at"][1]]
            self._remove_piece(piece)
            self.message = "Placed block picked up. Move it with the D-pad and press B to place."
        else:
            self.active_anchor = [0, 0]
            self.message = "Block selected. Move it with the D-pad and press B to place."

        self.selected_piece_id = piece["id"]
        self._clamp_anchor(piece)

    def _place_selected_piece(self):
        piece = self.piece_lookup[self.selected_piece_id]
        anchor = tuple(self.active_anchor)
        if self._can_place_piece(piece, anchor):
            self._place_piece(piece, anchor)
            self.selected_piece_id = None
            self.selected_origin_anchor = None
            self.message = "Block placed."
            if self._is_solved():
                self.state = "won"
                self.win_message = (
                    f"{self.current_difficulty['name']} puzzle solved. "
                    "Press B to play again."
                )
        else:
            self.message = "That block does not fit there."

    def _rotate_selected_piece(self):
        piece = self.piece_lookup[self.selected_piece_id]
        piece["rotation"] = (piece["rotation"] + 1) % 4
        self._clamp_anchor(piece)
        self.message = "Block rotated."

    def _cancel_selected_piece(self):
        self.selected_piece_id = None
        self.selected_origin_anchor = None
        self.message = "Selected block returned to the tray."

    def _can_place_piece(self, piece, anchor):
        cols = self.current_difficulty["cols"]
        rows = self.current_difficulty["rows"]
        ax, ay = anchor

        for dx, dy in self._rotated_cells(piece):
            x = ax + dx
            y = ay + dy
            if not (0 <= x < cols and 0 <= y < rows):
                return False
            if (x, y) in self.placed_cells:
                return False

        return True

    def _place_piece(self, piece, anchor):
        piece["placed_at"] = anchor

        for dx, dy in self._rotated_cells(piece):
            cell = (anchor[0] + dx, anchor[1] + dy)
            self.placed_cells[cell] = piece["id"]

    def _remove_piece(self, piece):
        piece["placed_at"] = None
        for cell, piece_id in list(self.placed_cells.items()):
            if piece_id == piece["id"]:
                del self.placed_cells[cell]

    def _clamp_anchor(self, piece):
        cols = self.current_difficulty["cols"]
        rows = self.current_difficulty["rows"]
        rotated = self._rotated_cells(piece)
        max_x = max(x for x, _ in rotated)
        max_y = max(y for _, y in rotated)

        self.active_anchor[0] = max(0, min(self.active_anchor[0], cols - max_x - 1))
        self.active_anchor[1] = max(0, min(self.active_anchor[1], rows - max_y - 1))

    def _tray_columns(self):
        piece_count = len(self.pieces)
        if piece_count <= 6:
            return 2
        if piece_count <= 12:
            return 3
        return 4

    def _is_solved(self):
        target_cells = self.current_difficulty["cols"] * self.current_difficulty["rows"]
        return len(self.placed_cells) == target_cells

    def _draw_background(self, surface):
        top = (40, 72, 110)
        bottom = (197, 224, 240)
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(top[0] * (1 - ratio) + bottom[0] * ratio)
            g = int(top[1] * (1 - ratio) + bottom[1] * ratio)
            b = int(top[2] * (1 - ratio) + bottom[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _draw_difficulty_screen(self, surface):
        title = self.title_font.render("Puzzle Blocks", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 52)))

        subtitle = self.body_font.render(
            "Every puzzle is randomized and always solvable.", True, (240, 245, 248)
        )
        surface.blit(subtitle, subtitle.get_rect(center=(BASE_WIDTH // 2, 78)))

        card_width = 190
        card_height = 42
        start_y = 112

        for index, config in enumerate(self.DIFFICULTIES):
            rect = pygame.Rect(0, 0, card_width, card_height)
            rect.center = (BASE_WIDTH // 2, start_y + index * 52)

            selected = index == self.selected_difficulty
            fill = (255, 216, 120) if selected else (248, 249, 250)
            border = (55, 63, 81)
            pygame.draw.rect(surface, fill, rect, border_radius=10)
            pygame.draw.rect(surface, border, rect, 2, border_radius=10)

            label = self.subtitle_font.render(config["name"], True, (25, 32, 46))
            info = self.small_font.render(
                f"{config['cols']}x{config['rows']} board", True, (60, 67, 81)
            )

            surface.blit(label, label.get_rect(center=(rect.centerx, rect.centery - 7)))
            surface.blit(info, info.get_rect(center=(rect.centerx, rect.centery + 10)))

        hint_lines = [
            "Up and down choose a difficulty.",
            "Press B or Enter to start. Esc returns to the games menu.",
        ]
        for index, line in enumerate(hint_lines):
            hint = self.body_font.render(line, True, (245, 248, 250))
            surface.blit(hint, hint.get_rect(center=(BASE_WIDTH // 2, 235 + index * 16)))

    def _draw_game_screen(self, surface):
        title = self.title_font.render("Puzzle Blocks", True, (255, 255, 255))
        surface.blit(title, (18, 12))

        difficulty = self.current_difficulty["name"]
        info = self.body_font.render(f"Difficulty: {difficulty}", True, (241, 245, 250))
        surface.blit(info, (18, 42))

        self._draw_board(surface)
        self._draw_tray(surface)
        self._draw_controls(surface)

    def _draw_board(self, surface):
        pygame.draw.rect(surface, (238, 244, 247), self.board_rect, border_radius=8)
        pygame.draw.rect(surface, (45, 58, 73), self.board_rect, 2, border_radius=8)

        cols = self.current_difficulty["cols"]
        rows = self.current_difficulty["rows"]
        board_x, board_y = self.board_origin

        for y in range(rows):
            for x in range(cols):
                rect = pygame.Rect(
                    board_x + x * self.cell_size,
                    board_y + y * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                cell_owner = self.placed_cells.get((x, y))
                fill = (253, 253, 253)
                if cell_owner is not None:
                    fill = self.piece_lookup[cell_owner]["color"]

                pygame.draw.rect(surface, fill, rect.inflate(-2, -2), border_radius=4)
                pygame.draw.rect(surface, (125, 138, 150), rect, 1)

        if self.selected_piece_id is not None:
            piece = self.piece_lookup[self.selected_piece_id]
            self._draw_piece_preview(surface, piece, tuple(self.active_anchor), alpha=120)

    def _draw_tray(self, surface):
        pygame.draw.rect(surface, (244, 247, 249), self.tray_rect, border_radius=8)
        pygame.draw.rect(surface, (45, 58, 73), self.tray_rect, 2, border_radius=8)

        title = self.subtitle_font.render("Blocks", True, (35, 42, 54))
        surface.blit(title, (self.tray_rect.x + 10, self.tray_rect.y + 8))

        status = self._status_text()
        status_label = self.small_font.render(status, True, (60, 67, 81))
        surface.blit(status_label, (self.tray_rect.x + 10, self.tray_rect.y + 24))

        if not self.pieces:
            return

        columns = self._tray_columns()
        rows = (len(self.pieces) + columns - 1) // columns
        horizontal_gap = 6
        vertical_gap = 6
        origin_x = self.tray_rect.x + 10
        origin_y = self.tray_rect.y + 42
        available_width = self.tray_rect.width - 20 - horizontal_gap * (columns - 1)
        available_height = self.tray_rect.height - 52 - vertical_gap * max(0, rows - 1)
        slot_width = max(40, available_width // columns)
        slot_height = max(28, available_height // max(1, rows))

        for index, piece in enumerate(self.pieces):
            row = index // columns
            col = index % columns
            rect = pygame.Rect(
                origin_x + col * (slot_width + horizontal_gap),
                origin_y + row * (slot_height + vertical_gap),
                slot_width,
                slot_height,
            )

            selected = self.selected_piece_id is None and index == self.tray_index
            fill = (255, 221, 135) if selected else (233, 239, 243)
            if piece["id"] == self.selected_piece_id:
                fill = (195, 228, 255)
            elif piece["placed_at"] is not None:
                fill = (208, 235, 214)

            pygame.draw.rect(surface, fill, rect, border_radius=8)
            pygame.draw.rect(surface, (90, 104, 118), rect, 2, border_radius=8)
            self._draw_piece_in_slot(surface, piece, rect)

    def _draw_piece_in_slot(self, surface, piece, rect):
        cells = self._rotated_cells(piece)
        min_x = min(x for x, _ in cells)
        max_x = max(x for x, _ in cells)
        min_y = min(y for _, y in cells)
        max_y = max(y for _, y in cells)

        width = max_x - min_x + 1
        height = max_y - min_y + 1
        tile_size = max(5, min(12, min((rect.width - 10) // width, (rect.height - 10) // height)))

        start_x = rect.x + (rect.width - width * tile_size) // 2
        start_y = rect.y + (rect.height - height * tile_size) // 2

        for x, y in cells:
            cell_rect = pygame.Rect(
                start_x + x * tile_size,
                start_y + y * tile_size,
                tile_size,
                tile_size,
            )
            pygame.draw.rect(surface, piece["color"], cell_rect.inflate(-1, -1), border_radius=3)
            pygame.draw.rect(surface, (57, 65, 76), cell_rect, 1, border_radius=3)

    def _draw_piece_preview(self, surface, piece, anchor, alpha):
        preview = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        valid = self._can_place_piece(piece, anchor)
        color = piece["color"] if valid else (210, 90, 90)
        border = (40, 46, 55, alpha)

        for dx, dy in self._rotated_cells(piece):
            rect = pygame.Rect(
                self.board_origin[0] + (anchor[0] + dx) * self.cell_size,
                self.board_origin[1] + (anchor[1] + dy) * self.cell_size,
                self.cell_size,
                self.cell_size,
            )
            pygame.draw.rect(
                preview,
                (*color, alpha),
                rect.inflate(-2, -2),
                border_radius=4,
            )
            pygame.draw.rect(preview, border, rect, 1, border_radius=4)

        surface.blit(preview, (0, 0))

    def _draw_controls(self, surface):
        lines = [
            "D-pad: choose a block or move the selected block",
            "B: pick up from tray / place on the board",
            "L: rotate the selected block",
            "Esc: return block or leave game",
        ]

        for index, line in enumerate(lines):
            label = self.small_font.render(line, True, (247, 249, 251))
            surface.blit(label, (18, 204 + index * 14))

    def _status_text(self):
        if self.selected_piece_id is not None:
            return "Selected block: move with D-pad, B places it"
        return "Tray: yellow is current, green blocks are already placed"

    def _draw_win_overlay(self, surface):
        overlay = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 12, 18, 150))
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(0, 0, 280, 108)
        box.center = (BASE_WIDTH // 2, BASE_HEIGHT // 2)
        pygame.draw.rect(surface, (245, 247, 250), box, border_radius=10)
        pygame.draw.rect(surface, (43, 53, 66), box, 2, border_radius=10)

        title = self.title_font.render("Puzzle Solved", True, (31, 40, 53))
        detail = self.body_font.render(self.win_message, True, (62, 70, 83))
        hint = self.small_font.render(
            "Press B to replay, Up/Down to switch difficulty, Esc to leave.",
            True,
            (62, 70, 83),
        )

        surface.blit(title, title.get_rect(center=(box.centerx, box.y + 28)))
        surface.blit(detail, detail.get_rect(center=(box.centerx, box.y + 56)))
        surface.blit(hint, hint.get_rect(center=(box.centerx, box.y + 82)))
