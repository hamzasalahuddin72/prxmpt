from __future__ import annotations

from datetime import datetime
from enum import Enum

from clearcue.storage.database import SessionSummary


TOP_BAR_SIZE = (516, 46)
AUDIO_HANDLER_SIZE = (516, 161)
ACTIVITY_BUTTONS_SIZE = (191, 22)
PLOT_POPUP_SIZE = (516, 393)
HISTORY_POPUP_SIZE = (516, 390)

TOP_TO_AUDIO_GAP = 8
AUDIO_TO_ACTIVITY_GAP = 6
ACTIVITY_TO_CONTENT_GAP = 6


class PopupState(str, Enum):
    """The four valid visibility configurations for the popup cluster."""

    TOP_ONLY = "top_only"
    CONTROLS = "controls"
    PLOT = "plot"
    HISTORY = "history"


def controls_toggle_target(state: PopupState) -> PopupState:
    return PopupState.CONTROLS if state is PopupState.TOP_ONLY else PopupState.TOP_ONLY


def plot_toggle_target(state: PopupState) -> PopupState:
    return PopupState.CONTROLS if state is PopupState.PLOT else PopupState.PLOT


def history_toggle_target(state: PopupState) -> PopupState:
    return PopupState.CONTROLS if state is PopupState.HISTORY else PopupState.HISTORY


def popup_scale_for_screen(available_width: int, available_height: int) -> float:
    """Return one uniform scale that keeps the largest cluster on screen."""

    maximum_height = (
        TOP_BAR_SIZE[1]
        + TOP_TO_AUDIO_GAP
        + AUDIO_HANDLER_SIZE[1]
        + AUDIO_TO_ACTIVITY_GAP
        + ACTIVITY_BUTTONS_SIZE[1]
        + ACTIVITY_TO_CONTENT_GAP
        + PLOT_POPUP_SIZE[1]
    )
    return min(
        1.0,
        max(0.1, (available_width - 24) / TOP_BAR_SIZE[0]),
        max(0.1, (available_height - 24) / maximum_height),
    )


def popup_cluster_positions(
    top_x: int,
    top_y: int,
    scale: float,
) -> dict[str, tuple[int, int]]:
    """Calculate the shared anchors for all five independently hosted popups."""

    top_width = round(TOP_BAR_SIZE[0] * scale)
    top_height = round(TOP_BAR_SIZE[1] * scale)
    audio_height = round(AUDIO_HANDLER_SIZE[1] * scale)
    activity_width = round(ACTIVITY_BUTTONS_SIZE[0] * scale)
    activity_height = round(ACTIVITY_BUTTONS_SIZE[1] * scale)
    top_to_audio = round(TOP_TO_AUDIO_GAP * scale)
    audio_to_activity = round(AUDIO_TO_ACTIVITY_GAP * scale)
    activity_to_content = round(ACTIVITY_TO_CONTENT_GAP * scale)

    audio_y = top_y + top_height + top_to_audio
    activity_y = audio_y + audio_height + audio_to_activity
    content_y = activity_y + activity_height + activity_to_content
    return {
        "top": (top_x, top_y),
        "audio": (top_x, audio_y),
        "activity": (top_x + (top_width - activity_width) // 2, activity_y),
        "plot": (top_x, content_y),
        "history": (top_x, content_y),
    }


def popup_cluster_size(state: PopupState, scale: float) -> tuple[int, int]:
    """Return the visible cluster bounds for screen-edge clamping."""

    width = round(TOP_BAR_SIZE[0] * scale)
    positions = popup_cluster_positions(0, 0, scale)
    if state is PopupState.TOP_ONLY:
        return width, round(TOP_BAR_SIZE[1] * scale)
    if state is PopupState.PLOT:
        height = positions["plot"][1] + round(PLOT_POPUP_SIZE[1] * scale)
    elif state is PopupState.HISTORY:
        height = positions["history"][1] + round(HISTORY_POPUP_SIZE[1] * scale)
    else:
        height = positions["activity"][1] + round(ACTIVITY_BUTTONS_SIZE[1] * scale)
    return width, height


def popup_size_for_screen(
    available_width: int,
    available_height: int,
    preferred_width: int = 551,
    preferred_height: int = 827,
) -> tuple[int, int]:
    """Scale the reference popup down so it remains inside the work area."""
    scale = min(
        1.0,
        max(0.1, (available_width - 24) / preferred_width),
        max(0.1, (available_height - 24) / preferred_height),
    )
    return max(300, round(preferred_width * scale)), max(438, round(preferred_height * scale))


def popup_corner_radius(
    width: int,
    height: int,
    reference_width: int = 551,
    reference_radius: int = 58,
) -> int:
    """Return a scaled radius that always fits the current popup height."""
    scaled = round(reference_radius * max(1, width) / reference_width)
    return max(1, min(scaled, max(1, height // 2 - 1)))


def session_display_title(session: SessionSummary) -> str:
    title = session.title.strip()
    if not title or title.lower() == "practice session":
        return f"Meeting {session.id}"
    return title


def session_display_time(started_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return parsed.strftime("%H:%M")
    except ValueError:
        return started_at.replace("T", " ")[11:16] or "--:--"
