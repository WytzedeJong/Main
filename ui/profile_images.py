import os
import pygame

PROFILE_IMAGES_DIR = os.path.join("data", "images")
IMAGE_EXTENSIONS = (".png")

_cache: dict[str, pygame.Surface] = {}


def list_profile_images() -> list[str]:
    if not os.path.isdir(PROFILE_IMAGES_DIR):
        return []

    files = []
    for name in os.listdir(PROFILE_IMAGES_DIR):
        if name.lower().endswith(IMAGE_EXTENSIONS):
            files.append(name)
    return sorted(files)


def profile_image_path(filename: str) -> str:
    return os.path.join(PROFILE_IMAGES_DIR, filename)


def load_profile_image(filename: str) -> pygame.Surface | None:
    if not filename:
        return None

    if filename in _cache:
        return _cache[filename]

    path = profile_image_path(filename)
    if not os.path.isfile(path):
        return None

    try:
        image = pygame.image.load(path).convert_alpha()
    except Exception:
        return None

    _cache[filename] = image
    return image


def get_user_profile_image(user: dict) -> str | None:
    profile = user.get("profile_image")
    if profile and _is_image_filename(profile):
        return profile

    icon = user.get("icon")
    if icon and _is_image_filename(icon):
        return icon

    return None


def _is_image_filename(name: str) -> bool:
    return isinstance(name, str) and name.lower().endswith(IMAGE_EXTENSIONS)


def _scale_to_cover(surface: pygame.Surface, width: int, height: int) -> pygame.Surface:
    w, h = max(1, int(width)), max(1, int(height))
    iw, ih = surface.get_size()
    scale = max(w / iw, h / ih)
    scaled = pygame.transform.smoothscale(
        surface, (max(1, int(iw * scale)), max(1, int(ih * scale)))
    )
    sw, sh = scaled.get_size()
    crop = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)
    return scaled.subsurface(crop).copy()


def draw_profile_avatar(
    surface: pygame.Surface,
    user: dict,
    center: tuple[int, int],
    size: int,
    *,
    selected: bool = False,
    border_color: tuple[int, int, int] = (0, 0, 0),
) -> pygame.Rect:
    cx, cy = center
    rect = pygame.Rect(cx - size // 2, cy - size // 2, size, size)

    if selected:
        pygame.draw.ellipse(surface, (0, 120, 215), rect.inflate(12, 12), 3)

    color = user.get("color", (200, 200, 200))
    if isinstance(color, list):
        color = tuple(color)

    pygame.draw.ellipse(surface, color, rect)
    pygame.draw.ellipse(surface, border_color, rect, 2)

    filename = get_user_profile_image(user)
    if filename:
        image = load_profile_image(filename)
        if image is not None:
            inner = rect.width - 4
            avatar = _scale_to_cover(image, inner, inner)
            clip = pygame.Surface((inner, inner), pygame.SRCALPHA)
            clip.blit(avatar, (0, 0))
            mask = pygame.Surface((inner, inner), pygame.SRCALPHA)
            pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
            clip.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(clip, (rect.x + 2, rect.y + 2))

    return rect
