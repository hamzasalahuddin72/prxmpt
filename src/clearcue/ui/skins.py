from __future__ import annotations

import json
import re
from dataclasses import dataclass

from clearcue.resources import resource_path


DEFAULT_SKIN_ID = "midnight"
SKIN_FILES = (
    ("midnight", "skins/midnight.json"),
    ("azure_knight", "skins/azure-knight.json"),
    ("rose_quartz", "skins/rose-quartz.json"),
)
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class Skin:
    id: str
    name: str
    base_color: str
    base_opacity: float
    accent_color: str
    accent_opacity: float

    def rgba(self, role: str, opacity: float | None = None) -> tuple[int, int, int, int]:
        color = self.base_color if role == "base" else self.accent_color
        default_opacity = self.base_opacity if role == "base" else self.accent_opacity
        alpha = default_opacity if opacity is None else opacity
        return (
            int(color[1:3], 16),
            int(color[3:5], 16),
            int(color[5:7], 16),
            round(max(0.0, min(1.0, alpha)) * 255),
        )

    def qss_rgba(self, role: str, opacity: float | None = None) -> str:
        return "rgba({}, {}, {}, {})".format(*self.rgba(role, opacity))


def _load_skin(filename: str) -> Skin:
    raw = json.loads(resource_path(filename).read_text(encoding="utf-8"))
    base = raw["base"]
    accent = raw["accent"]
    skin = Skin(
        id=str(raw["id"]),
        name=str(raw["name"]),
        base_color=str(base["color"]).upper(),
        base_opacity=float(base["opacity"]),
        accent_color=str(accent["color"]).upper(),
        accent_opacity=float(accent["opacity"]),
    )
    if not skin.id or not skin.name:
        raise ValueError(f"Skin metadata is incomplete: {filename}")
    if not _HEX_COLOR.fullmatch(skin.base_color):
        raise ValueError(f"Invalid base color in {filename}")
    if not _HEX_COLOR.fullmatch(skin.accent_color):
        raise ValueError(f"Invalid accent color in {filename}")
    if not 0.0 <= skin.base_opacity <= 1.0:
        raise ValueError(f"Invalid base opacity in {filename}")
    if not 0.0 <= skin.accent_opacity <= 1.0:
        raise ValueError(f"Invalid accent opacity in {filename}")
    return skin


def available_skins() -> tuple[Skin, ...]:
    return tuple(_load_skin(filename) for _skin_id, filename in SKIN_FILES)


def get_skin(skin_id: str) -> Skin:
    for expected_id, filename in SKIN_FILES:
        if skin_id == expected_id:
            skin = _load_skin(filename)
            if skin.id != expected_id:
                raise ValueError(f"Skin id does not match its filename: {filename}")
            return skin
    return _load_skin(dict(SKIN_FILES)[DEFAULT_SKIN_ID])


_active_skin = get_skin(DEFAULT_SKIN_ID)


def activate_skin(skin_id: str) -> Skin:
    global _active_skin
    _active_skin = get_skin(skin_id)
    return _active_skin


def active_skin() -> Skin:
    return _active_skin
