import pygame
import json
import os
from core.scene import Scene
from settings import base_surface, screen, BASE_WIDTH, BASE_HEIGHT
from config import styles
from ui.settings_menu import SettingsMenu
from ui.Games_menu import Game_Menu
from ui.lockscreen import LockScreen
from ui.vierkantjes import vierkantjes


def _format_money(value):
    value = float(value)
    if value < 0:
        return f"-${_format_money(-value)[1:]}"
    if value < 1000:
        if value == int(value):
            return f"${int(value)}"
        return f"${value:.2f}"
    suffixes = ["", "K", "M", "B", "T", "Qa", "Qi", "Se", "Sx", "Sp", "Oc", "No"]
    tier = 0
    while value >= 1000 and tier < len(suffixes) - 1:
        value /= 1000
        tier += 1
    if value >= 100:
        return f"${value:.1f}{suffixes[tier]}"
    if value >= 10:
        return f"${value:.2f}{suffixes[tier]}"
    return f"${value:.3f}{suffixes[tier]}"


class Highscore(Scene):
    ACHIEVEMENT_TARGETS = {
        "Monkey": {
            "1000_points": 1000,
        }
    }

    ACHIEVEMENT_DESCRIPTIONS = {
        "Monkey": {
            "1000_points": "Behaal een score van 1000",
        }
    }

    def __init__(self, manager):
        super().__init__(manager)
        self.styles = styles
        self.sq = vierkantjes
        self.user = self.get_user()
        self.game_keys = self.get_members()
        self.selected_x = 0
        self.selected_y = 0

        self.current_scroll_x = 0.0
        self.current_scroll_y = 0.0

        self.highscores = self.load_highscores()
        self.achievements = self.load_achievements()

    def _fonts(self):
        s = self.styles
        return {
            "title": s.create_font(s.FONT_HOME_TITLE_SIZE, bold=True),
            "card": s.create_font(s.FONT_HOME_CARD_SIZE, bold=True),
            "body": s.create_font(s.FONT_HOME_CARD_SIZE - 4),
            "small": s.create_font(max(8, s.FONT_HOME_CARD_SIZE - 6)),
        }

    def _c(self):
        s = self.styles
        bg = s.BACKGROUND if isinstance(s.BACKGROUND, tuple) else (255, 255, 255)
        cc = s.CARD_COLOR
        txt = s.TEXT_SET
        dim = tuple((t * 2 + b) // 3 for t, b in zip(txt, bg))
        sel = s.CARD_SELECTED
        done_bar = tuple(min(255, v + 40) for v in sel)
        return {
            "bg": bg,
            "card": cc,
            "card_sel": sel,
            "card_dark": tuple(max(0, v - 30) for v in cc),
            "border": dim,
            "border_sel": sel,
            "text": txt,
            "text_dim": dim,
            "bar_bg": tuple(max(0, v - 60) for v in bg),
            "bar_fill": sel,
            "bar_done": done_bar,
        }

    @staticmethod
    def _draw_progress_bar(surface, x, y, w, h, pct, color_fill, color_bg):
        pygame.draw.rect(surface, color_bg, (x, y, w, h), border_radius=2)
        fill_w = int(w * min(1.0, pct))
        if fill_w > 0:
            pygame.draw.rect(surface, color_fill, (x, y, fill_w, h), border_radius=2)

    def get_user(self):
        user = getattr(self.manager, 'current_user', None)
        if user:
            return user
        try:
            lock = LockScreen(self.manager)
            return lock.get_user() or 0
        except Exception:
            return 0

    def _get_username(self):
        if isinstance(self.user, dict):
            return self.user.get("name")
        if isinstance(self.user, str):
            return self.user
        return None

    def get_members(self):
        username = self._get_username()
        if not username:
            return []
        path = os.path.join("data", "users.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for player in data.get("users", []):
                if player.get("name") == username:
                    return list(player.get("highscores", {}).keys())
        except Exception as e:
            print(f"Error loading members: {e}")
        return []

    def load_highscores(self):
        highscores = {key: 0 for key in self.game_keys}
        username = self._get_username()
        if not username:
            return highscores
        path = os.path.join("data", "users.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for player in data.get("users", []):
                if player.get("name") == username:
                    highscores.update(player.get("highscores", {}))
                    return highscores
        except Exception as e:
            print(f"Error loading highscores: {e}")
        return highscores

    def load_achievements(self):
        achievements = {key: [] for key in self.game_keys}
        username = self._get_username()
        if not username:
            return achievements
        path = os.path.join("data", "users.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for player in data.get("users", []):
                if player.get("name") == username:
                    ua = player.get("achievements", {})
                    for gk in self.game_keys:
                        achievements[gk] = ua.get(gk, [])
                    return achievements
        except Exception as e:
            print(f"Error loading achievements: {e}")
        return achievements

    def _format_achievement_name(self, key):
        if key == "1000_points":
            return "1000+ Pts"
        return key.replace("_", " ").title()

    def _get_achievement_description(self, game_name, key):
        desc = self.ACHIEVEMENT_DESCRIPTIONS.get(game_name, {}).get(key)
        if desc:
            return desc
        target = self._get_achievement_target(game_name, key)
        return f"Score van {target}" if target else self._format_achievement_name(key)

    def _get_achievement_target(self, game_name, key):
        t = self.ACHIEVEMENT_TARGETS.get(game_name, {}).get(key)
        if t:
            return t
        if key.endswith("_points"):
            val = key.removesuffix("_points").replace("_", "")
            if val.isdigit():
                return int(val)
        return None

    def _get_achievement_data(self, game_name):
        if game_name == "Puzzle":
            return []
        all_keys = list(self.ACHIEVEMENT_TARGETS.get(game_name, {}).keys())
        for k in self.achievements.get(game_name, []):
            if k not in all_keys:
                all_keys.append(k)
        score = self.highscores.get(game_name, 0)
        result = []
        for k in all_keys:
            target = self._get_achievement_target(game_name, k)
            earned = k in self.achievements.get(game_name, [])
            pct = min(1.0, score / target) if (target and target > 0) else (1.0 if earned else 0.0)
            result.append({
                "name": self._format_achievement_name(k),
                "desc": self._get_achievement_description(game_name, k),
                "target": target,
                "earned": earned,
                "pct": pct,
                "score": score,
            })
        return result

    def handle_events(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_RIGHT:
            if self.selected_x < len(self.game_keys) - 1:
                self.selected_x += 1
            self.selected_y = 0
        elif k == pygame.K_LEFT:
            if self.selected_x > 0:
                self.selected_x -= 1
            self.selected_y = 0

        elif k == pygame.K_ESCAPE:
            from ui.home_menu import HomeMenu
            self.manager.set_scene(HomeMenu(self.manager))

    def update(self, dt):
        speed = 8 * dt
        self.current_scroll_x += (self.selected_x - self.current_scroll_x) * min(1.0, speed)
        self.current_scroll_y += (self.selected_y - self.current_scroll_y) * min(1.0, speed)

    def draw_gradient(self, surface):
        for y in range(BASE_HEIGHT):
            ratio = y / BASE_HEIGHT
            r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
            g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
            b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (BASE_WIDTH, y))

    def _draw_header(self, surface, f, c):
        username = self._get_username() or "Guest"

        title = f["title"].render("Highscores", True, self.styles.TEXT_COLOR)
        surface.blit(title, (30, 18))

        pygame.draw.line(surface, self.styles.CARD_COLOR,
                         (30, 18 + title.get_height() + 2),
                         (30 + title.get_width(), 18 + title.get_height() + 2), 2)

        badge_surf = f["body"].render(f"Player: {username}", True, self.styles.TEXT_COLOR)
        bx = BASE_WIDTH - badge_surf.get_width() - 16
        pygame.draw.rect(surface, self.styles.CARD_COLOR,
                         (bx - 6, 14, badge_surf.get_width() + 12, badge_surf.get_height() + 6),
                         border_radius=6)
        surface.blit(badge_surf, (bx, 17))

    def _draw_game_tabs(self, surface, f, c, tab_y):
        if not self.game_keys:
            return

        tab_w = 80
        tab_h = 20
        spacing = 6
        MARGIN = 20  # blank space on each side before clipping

        # Compute pixel scroll so the selected tab stays centred
        visible_w = BASE_WIDTH - 2 * MARGIN
        center_offset = visible_w / 2 - tab_w / 2
        scroll_px = self.current_scroll_x * (tab_w + spacing)
        start_x = MARGIN + center_offset - scroll_px

        # Clip so tabs never render outside the margin area
        clip_rect = pygame.Rect(MARGIN, tab_y - 2, visible_w, tab_h + 4)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        for i, name in enumerate(self.game_keys):
            tx = int(start_x + i * (tab_w + spacing))
            # Skip tabs fully outside the visible area (cheap early-out)
            if tx + tab_w < MARGIN or tx > BASE_WIDTH - MARGIN:
                continue
            active = (i == self.selected_x)
            bg = self.styles.CARD_SELECTED if active else self.styles.CARD_COLOR
            pygame.draw.rect(surface, bg, (tx, tab_y, tab_w, tab_h), border_radius=4)
            label = f["small"].render(name, True, self.styles.TEXT_SET)
            lx = tx + (tab_w - label.get_width()) // 2
            ly = tab_y + (tab_h - label.get_height()) // 2
            surface.blit(label, (lx, ly))

        surface.set_clip(old_clip)

        # Gradient fade on both edges to hint at off-screen tabs
        fade_w = 30
        ratio = tab_y / BASE_HEIGHT
        r = int(self.styles.BG_TOP[0] * (1 - ratio) + self.styles.BG_BOTTOM[0] * ratio)
        g = int(self.styles.BG_TOP[1] * (1 - ratio) + self.styles.BG_BOTTOM[1] * ratio)
        b = int(self.styles.BG_TOP[2] * (1 - ratio) + self.styles.BG_BOTTOM[2] * ratio)
        bg_col = (r, g, b)

        fade_surf = pygame.Surface((fade_w, tab_h + 4), pygame.SRCALPHA)
        for i in range(fade_w):
            alpha = int(220 * (1 - i / fade_w))
            pygame.draw.line(fade_surf, (*bg_col, alpha), (i, 0), (i, tab_h + 3))

        # Left edge fade
        surface.blit(fade_surf, (MARGIN, tab_y - 2))
        # Right edge fade (mirror horizontally)
        surface.blit(pygame.transform.flip(fade_surf, True, False),
                     (BASE_WIDTH - MARGIN - fade_w, tab_y - 2))

    def _draw_score_card(self, surface, game_name, cx, cy, w, h, is_selected, f, c):
        bg = self.styles.CARD_COLOR
        pygame.draw.rect(surface, bg, (cx, cy, w, h), border_radius=10)

        pad = 12
        inner_x = cx + pad
        inner_w = w - 2 * pad
        text_y = cy + pad

        # Game naam
        lbl = f["small"].render(game_name, True, self.styles.TEXT_SET)
        surface.blit(lbl, (inner_x, text_y))
        text_y += lbl.get_height() + 4

        pygame.draw.line(surface, self.styles.TEXT_SET,
                         (inner_x, text_y), (cx + w - pad, text_y), 1)
        text_y += 8

        if game_name == "Puzzle":
            puzzle_times = self.highscores.get(game_name, {})
            for diff in ["Easy", "Medium", "Hard", "Extra Hard"]:
                t = puzzle_times.get(diff, "--:--") if isinstance(puzzle_times, dict) else "--:--"
                done = t != "--:--"
                col = self.styles.TEXT_SET if done else c["text_dim"]
                ns = f["small"].render(diff, True, c["text_dim"])
                ts = f["small"].render(t, True, col)
                surface.blit(ns, (inner_x, text_y))
                surface.blit(ts, (cx + w - pad - ts.get_width(), text_y))
                text_y += ns.get_height() + 5

        elif game_name == "Farm Nation":
            farm_data = self.highscores.get(game_name, {})
            if not isinstance(farm_data, dict):
                farm_data = {}

            # Label + waarde naast elkaar, drie rijen
            stats = [
                ("Money",    _format_money(farm_data.get("money", 0.0))),
                ("Clicks",   str(farm_data.get("total_clicks", 0))),
                ("Rebirths", str(farm_data.get("rebirths", 0))),
            ]
            for label, value in stats:
                label_surf = f["small"].render(label, True, c["text_dim"])
                value_surf = f["small"].render(value, True, self.styles.TEXT_SET)
                surface.blit(label_surf, (inner_x, text_y))
                surface.blit(value_surf, (cx + w - pad - value_surf.get_width(), text_y))
                text_y += label_surf.get_height() + 6

        else:
            score = self.highscores.get(game_name, 0)

            score_surf = f["card"].render(str(score), True, self.styles.TEXT_SET)
            surface.blit(score_surf, (cx + (w - score_surf.get_width()) // 2, text_y))
            text_y += score_surf.get_height() + 4

            if game_name == "Monkey":
                unit = "Score"
            elif game_name == "Pengu":
                unit = "Wins"
            elif game_name == "Dungeon" or game_name == "Racer":
                unit = "Points"
            else:
                unit = "Round"

            unit_surf = f["small"].render(unit, True, self.styles.TEXT_SET)
            surface.blit(unit_surf, (cx + (w - unit_surf.get_width()) // 2, text_y))
            text_y += unit_surf.get_height() + 12

            if game_name != "Monkey":
                targets = self.ACHIEVEMENT_TARGETS.get(game_name, {})
                if targets:
                    first_target = next(iter(targets.values()))
                    if first_target > 0:
                        pct = min(1.0, score / first_target)
                        bar_col = c["bar_done"] if pct >= 1.0 else c["bar_fill"]

                        self._draw_progress_bar(surface, inner_x, text_y, inner_w, 7, pct, bar_col, c["bar_bg"])
                        text_y += 11

                        pt_surf = f["small"].render(f"{score}/{first_target}", True, self.styles.TEXT_SET)
                        surface.blit(pt_surf, (inner_x, text_y))

    def _draw_achievements_panel(self, surface, game_name, px, py, pw, ph, is_selected, f, c):
        achiev_data = self._get_achievement_data(game_name)

        bg = self.styles.CARD_COLOR
        pygame.draw.rect(surface, bg, (px, py, pw, ph), border_radius=10)

        pad = 12
        ty = py + pad

        lbl = f["small"].render("Achievements", True, self.styles.TEXT_SET)
        surface.blit(lbl, (px + pad, ty))
        ty += lbl.get_height() + 4
        pygame.draw.line(surface, self.styles.TEXT_SET, (px + pad, ty), (px + pw - pad, ty), 1)
        ty += 8

        if game_name == "Puzzle":
            msg = f["small"].render("No achievements Puzzle", True, self.styles.TEXT_SET)
            surface.blit(msg, (px + (pw - msg.get_width()) // 2, ty))
            return

        if not achiev_data:
            msg = f["small"].render("No achievements yet", True, self.styles.TEXT_SET)
            surface.blit(msg, (px + pad, ty))
            return

        row_h = 56
        for a in achiev_data:
            if ty + row_h > py + ph - pad:
                break

            earned = a["earned"]
            row_bg = self.styles.CARD_COLOR if is_selected else tuple(min(255, v + 15) for v in self.styles.CARD_COLOR)
            pygame.draw.rect(surface, row_bg,
                             (px + pad, ty, pw - 2 * pad, row_h - 6), border_radius=6)
            pygame.draw.rect(surface, self.styles.CARD_SELECTED,
                             (px + pad, ty, 4, row_h - 6), border_radius=3)

            icon_sym = "+" if earned else "-"
            icon_s = f["body"].render(icon_sym, True, self.styles.TEXT_SET)
            surface.blit(icon_s, (px + pad + 8, ty + (row_h - 6 - icon_s.get_height()) // 2))

            tx_start = px + pad + 28
            name_surf = f["body"].render(a["name"], True, self.styles.TEXT_SET)
            desc_surf = f["small"].render(a["desc"], True, self.styles.TEXT_SET)
            surface.blit(name_surf, (tx_start, ty + 4))
            surface.blit(desc_surf, (tx_start, ty + 4 + name_surf.get_height() + 2))

            pct_label = "Done!" if earned else f"{int(a['pct'] * 100)}%"
            pct_surf = f["small"].render(pct_label, True, self.styles.TEXT_SET)
            surface.blit(pct_surf, (px + pw - pad - pct_surf.get_width() - 6, ty + 4))

            bar_y = ty + row_h - 14
            bar_col = c["bar_done"] if earned else c["bar_fill"]
            self._draw_progress_bar(surface, tx_start, bar_y,
                                    pw - 2 * pad - 28 - 6, 5, a["pct"], bar_col, c["bar_bg"])
            ty += row_h

    def draw(self, surface):
        base_surface.fill((0, 0, 0))
        self.draw_gradient(base_surface)
        self.sq.vierkantjes(self)

        f = self._fonts()
        c = self._c()

        self._draw_header(base_surface, f, c)
        self._draw_game_tabs(base_surface, f, c, tab_y=60)

        AREA_Y = 92
        AREA_H = BASE_HEIGHT - AREA_Y - 28
        SCORE_W = 160
        SCORE_H = min(AREA_H, 210)
        GAP = 12
        SCORE_X = 20
        SCORE_Y = AREA_Y + (AREA_H - SCORE_H) // 2
        ACHIEV_X = SCORE_X + SCORE_W + GAP
        ACHIEV_Y = SCORE_Y
        ACHIEV_W = BASE_WIDTH - ACHIEV_X - 20
        ACHIEV_H = SCORE_H

        if 0 <= self.selected_x < len(self.game_keys):
            game_name = self.game_keys[self.selected_x]
            self._draw_score_card(base_surface, game_name, SCORE_X, SCORE_Y,
                                  SCORE_W, SCORE_H, self.selected_y == 0, f, c)
            self._draw_achievements_panel(base_surface, game_name, ACHIEV_X, ACHIEV_Y,
                                          ACHIEV_W, ACHIEV_H, self.selected_y == 1, f, c)