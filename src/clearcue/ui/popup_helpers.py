from __future__ import annotations

from datetime import datetime

from clearcue.storage.database import SessionSummary


def popup_size_for_screen(
    available_width: int,
    available_height: int,
    preferred_width: int = 520,
    preferred_height: int = 760,
) -> tuple[int, int]:
    """Scale the reference popup down so it remains inside the work area."""
    scale = min(
        1.0,
        max(0.1, (available_width - 24) / preferred_width),
        max(0.1, (available_height - 24) / preferred_height),
    )
    return max(300, round(preferred_width * scale)), max(438, round(preferred_height * scale))


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
