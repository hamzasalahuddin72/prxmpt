import json

from clearcue.resources import resource_path
from clearcue.ui.skins import (
    DEFAULT_SKIN_ID,
    activate_skin,
    active_skin,
    available_skins,
    get_skin,
)
from clearcue.ui.theme import APP_STYLESHEET, stylesheet_for_skin


def test_skin_files_are_separate_and_use_the_approved_colors() -> None:
    midnight_file = resource_path("skins/midnight.json")
    azure_file = resource_path("skins/azure-knight.json")
    rose_file = resource_path("skins/rose-quartz.json")
    assert midnight_file.is_file()
    assert azure_file.is_file()
    assert rose_file.is_file()

    midnight = json.loads(midnight_file.read_text(encoding="utf-8"))
    azure = json.loads(azure_file.read_text(encoding="utf-8"))
    rose = json.loads(rose_file.read_text(encoding="utf-8"))
    assert midnight["base"] == {"color": "#000000", "opacity": 1.0}
    assert midnight["accent"] == {"color": "#D0BCFF", "opacity": 0.16}
    assert azure["base"] == {"color": "#1C4345", "opacity": 1.0}
    assert azure["accent"] == {"color": "#85F7FF", "opacity": 0.34}
    assert rose["base"] == {"color": "#EAC9C2", "opacity": 1.0}
    assert rose["accent"] == {"color": "#BE818D", "opacity": 1.0}


def test_skin_catalog_and_fallback_are_stable() -> None:
    assert [(skin.id, skin.name) for skin in available_skins()] == [
        ("midnight", "Midnight"),
        ("azure_knight", "Azure Knight"),
        ("rose_quartz", "Rose Quartz"),
    ]
    assert DEFAULT_SKIN_ID == "midnight"
    assert get_skin("missing").id == "midnight"


def test_stylesheet_uses_exact_skin_opacity_tokens() -> None:
    assert "rgba(0, 0, 0, 255)" in APP_STYLESHEET
    assert "rgba(208, 188, 255, 41)" in APP_STYLESHEET
    azure = stylesheet_for_skin("azure_knight")
    assert "rgba(28, 67, 69, 255)" in azure
    assert "rgba(133, 247, 255, 87)" in azure
    assert "__POPUP_" not in azure
    rose = stylesheet_for_skin("rose_quartz")
    assert "rgba(234, 201, 194, 255)" in rose
    assert "rgba(190, 129, 141, 255)" in rose
    assert "__POPUP_" not in rose


def test_active_skin_can_be_selected_for_custom_painters() -> None:
    try:
        activate_skin("azure_knight")
        assert active_skin().name == "Azure Knight"
        assert active_skin().rgba("base") == (28, 67, 69, 255)
    finally:
        activate_skin("midnight")


def test_rose_quartz_can_be_selected_for_custom_painters() -> None:
    try:
        activate_skin("rose_quartz")
        assert active_skin().name == "Rose Quartz"
        assert active_skin().rgba("base") == (234, 201, 194, 255)
        assert active_skin().rgba("accent") == (190, 129, 141, 255)
    finally:
        activate_skin("midnight")
