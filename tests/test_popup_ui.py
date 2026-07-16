from clearcue.storage.database import SessionSummary
from clearcue.ui.popup_helpers import (
    popup_size_for_screen,
    session_display_time,
    session_display_title,
)


def test_popup_uses_reference_size_when_screen_has_room() -> None:
    assert popup_size_for_screen(1920, 1080) == (551, 827)


def test_popup_scales_down_inside_small_work_area() -> None:
    width, height = popup_size_for_screen(430, 650)
    assert width <= 406
    assert height <= 626
    assert round(width / height, 2) == round(551 / 827, 2)


def test_meeting_display_helpers() -> None:
    session = SessionSummary(7, 1, "2026-07-16T14:14:00+00:00", None, "Practice session")
    assert session_display_title(session) == "Meeting 7"
    assert len(session_display_time(session.started_at)) == 5
