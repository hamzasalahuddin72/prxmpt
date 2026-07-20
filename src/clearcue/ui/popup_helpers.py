from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from clearcue.storage.database import SessionSummary


TOP_BAR_SIZE = (720, 58)
PROMPT_SCREEN_SIZE = (720, 35)
FEEDBACK_WINDOW_SIZE = (720, 261)
HISTORY_POPUP_SIZE = (720, 164)
HISTORY_ROW_HEIGHT = 34
HISTORY_ROW_GAP = 4
HISTORY_VERTICAL_PADDING = 16
HISTORY_MAX_VISIBLE_ROWS = 4

TOP_TO_PROMPT_GAP = 6
PROMPT_TO_CONTENT_GAP = 6
POPUP_CORNER_RADIUS = 10


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
        + TOP_TO_PROMPT_GAP
        + PROMPT_SCREEN_SIZE[1]
        + PROMPT_TO_CONTENT_GAP
        + FEEDBACK_WINDOW_SIZE[1]
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
    """Calculate the shared anchors for the four independently hosted popups."""

    top_height = round(TOP_BAR_SIZE[1] * scale)
    prompt_height = round(PROMPT_SCREEN_SIZE[1] * scale)
    top_to_prompt = round(TOP_TO_PROMPT_GAP * scale)
    prompt_to_content = round(PROMPT_TO_CONTENT_GAP * scale)

    prompt_y = top_y + top_height + top_to_prompt
    content_y = prompt_y + prompt_height + prompt_to_content
    return {
        "top": (top_x, top_y),
        "prompt": (top_x, prompt_y),
        "feedback": (top_x, content_y),
        "history": (top_x, content_y),
    }


def popup_cluster_size(state: PopupState, scale: float) -> tuple[int, int]:
    """Return the visible cluster bounds for screen-edge clamping."""

    width = round(TOP_BAR_SIZE[0] * scale)
    positions = popup_cluster_positions(0, 0, scale)
    if state is PopupState.TOP_ONLY:
        return width, round(TOP_BAR_SIZE[1] * scale)
    if state is PopupState.PLOT:
        height = positions["feedback"][1] + round(FEEDBACK_WINDOW_SIZE[1] * scale)
    elif state is PopupState.HISTORY:
        height = positions["history"][1] + round(HISTORY_POPUP_SIZE[1] * scale)
    else:
        height = positions["prompt"][1] + round(PROMPT_SCREEN_SIZE[1] * scale)
    return width, height


def popup_size_for_screen(
    available_width: int,
    available_height: int,
    preferred_width: int = 720,
    preferred_height: int = 366,
) -> tuple[int, int]:
    """Scale the reference popup down so it remains inside the work area."""
    scale = min(
        1.0,
        max(0.1, (available_width - 24) / preferred_width),
        max(0.1, (available_height - 24) / preferred_height),
    )
    return max(1, round(preferred_width * scale)), max(1, round(preferred_height * scale))


def popup_corner_radius(
    width: int,
    height: int,
    reference_width: int = 720,
    reference_radius: int = POPUP_CORNER_RADIUS,
) -> int:
    """Return a scaled radius that always fits the current popup height."""
    scaled = round(reference_radius * max(1, width) / reference_width)
    return max(1, min(scaled, max(1, height // 2 - 1)))


def history_popup_height(session_count: int) -> int:
    """Return the adaptive one-to-four-row history-popup height."""

    rows = max(1, min(HISTORY_MAX_VISIBLE_ROWS, int(session_count)))
    return (
        HISTORY_VERTICAL_PADDING
        + rows * HISTORY_ROW_HEIGHT
        + (rows - 1) * HISTORY_ROW_GAP
    )


def history_content_height(session_count: int) -> int:
    """Return the scroll contents height for every stored meeting row."""

    rows = max(1, int(session_count))
    return rows * HISTORY_ROW_HEIGHT + (rows - 1) * HISTORY_ROW_GAP


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


def session_display_datetime(started_at: str) -> str:
    """Format a stored UTC start time using the computer's local timezone."""

    try:
        parsed = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone()
        return f"{parsed.day} {parsed.strftime('%B %Y at %H:%M')}"
    except ValueError:
        return started_at.replace("T", " ")[:16] or "Unknown date"


def session_display_duration(started_at: str, ended_at: str | None) -> str:
    """Return an elapsed meeting duration as MM:SS or H:MM:SS."""

    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        if ended_at:
            ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            if ended.tzinfo is None:
                ended = ended.replace(tzinfo=UTC)
        else:
            ended = datetime.now(UTC)
        seconds = max(0, round((ended - started).total_seconds()))
    except ValueError:
        return "--:--"
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def session_display_model(model_used: str) -> str:
    cleaned = model_used.strip()
    if not cleaned:
        return "local"
    lowered = cleaned.lower()
    if "gemini" in lowered:
        if "lite" in lowered:
            return "gem-lite"
        if "3.5" in lowered:
            return "gem-3.5"
    return cleaned[:14]
