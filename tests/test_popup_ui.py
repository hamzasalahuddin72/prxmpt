from clearcue.storage.database import SessionSummary
from clearcue.ui.popup_helpers import (
    PopupState,
    controls_toggle_target,
    history_toggle_target,
    popup_corner_radius,
    popup_cluster_positions,
    popup_cluster_size,
    popup_scale_for_screen,
    popup_size_for_screen,
    plot_toggle_target,
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


def test_popup_corner_radius_is_clamped_when_collapsed() -> None:
    assert popup_corner_radius(551, 827) == 58
    assert popup_corner_radius(551, 80) == 39
    assert popup_corner_radius(406, 626) == 43


def test_five_popup_cluster_uses_fixed_approved_anchors() -> None:
    positions = popup_cluster_positions(100, 12, 1.0)
    assert positions == {
        "top": (100, 12),
        "audio": (100, 66),
        "activity": (262, 233),
        "plot": (100, 261),
        "history": (100, 261),
    }
    assert popup_cluster_size(PopupState.TOP_ONLY, 1.0) == (516, 46)
    assert popup_cluster_size(PopupState.CONTROLS, 1.0) == (516, 243)
    assert popup_cluster_size(PopupState.PLOT, 1.0) == (516, 642)
    assert popup_cluster_size(PopupState.HISTORY, 1.0) == (516, 639)


def test_popup_cluster_scales_uniformly_on_smaller_screens() -> None:
    scale = popup_scale_for_screen(430, 650)
    assert round(scale, 3) == round(406 / 516, 3)
    width, height = popup_cluster_size(PopupState.PLOT, scale)
    assert width <= 406
    assert height <= 626


def test_popup_visibility_transitions_are_mutually_exclusive() -> None:
    assert controls_toggle_target(PopupState.TOP_ONLY) is PopupState.CONTROLS
    assert controls_toggle_target(PopupState.PLOT) is PopupState.TOP_ONLY
    assert plot_toggle_target(PopupState.CONTROLS) is PopupState.PLOT
    assert plot_toggle_target(PopupState.HISTORY) is PopupState.PLOT
    assert plot_toggle_target(PopupState.PLOT) is PopupState.CONTROLS
    assert history_toggle_target(PopupState.CONTROLS) is PopupState.HISTORY
    assert history_toggle_target(PopupState.PLOT) is PopupState.HISTORY
    assert history_toggle_target(PopupState.HISTORY) is PopupState.CONTROLS


def test_meeting_display_helpers() -> None:
    session = SessionSummary(7, 1, "2026-07-16T14:14:00+00:00", None, "Practice session")
    assert session_display_title(session) == "Meeting 7"
    assert len(session_display_time(session.started_at)) == 5
