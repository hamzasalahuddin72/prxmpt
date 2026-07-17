import xml.etree.ElementTree as ET

from clearcue.resources import resource_path


FORMS = {
    "prxmpt-top-bar.ui": ("TopBarRoot", (720, 58)),
    "prxmpt-prompt-screen.ui": ("PromptScreenRoot", (720, 35)),
    "prxmpt-feedback-window.ui": ("FeedbackWindowRoot", (720, 261)),
    "prxmpt-history-popup.ui": ("HistoryPopupRoot", (720, 164)),
}


def _widget(root: ET.Element, name: str) -> ET.Element:
    for widget in root.iter("widget"):
        if widget.attrib.get("name") == name:
            return widget
    raise AssertionError(f"missing Designer widget: {name}")


def _geometry(widget: ET.Element) -> tuple[int, int, int, int]:
    geometry = widget.find("./property[@name='geometry']/rect")
    assert geometry is not None, widget.attrib.get("name")
    return tuple(
        int(geometry.findtext(part, "0"))
        for part in ("x", "y", "width", "height")
    )


def test_four_designer_forms_use_approved_fixed_geometry() -> None:
    for filename, (root_name, size) in FORMS.items():
        root = ET.parse(resource_path(filename)).getroot()
        root_widget = _widget(root, root_name)
        assert _geometry(root_widget) == (0, 0, *size)
        minimum = root_widget.find("./property[@name='minimumSize']/size")
        maximum = root_widget.find("./property[@name='maximumSize']/size")
        assert minimum is not None and maximum is not None
        min_size = (
            int(minimum.findtext("width", "0")),
            int(minimum.findtext("height", "0")),
        )
        max_size = (
            int(maximum.findtext("width", "0")),
            int(maximum.findtext("height", "0")),
        )
        assert min_size == max_size == size


def test_top_bar_matches_supplied_svg_control_coordinates() -> None:
    root = ET.parse(resource_path("prxmpt-top-bar.ui")).getroot()
    assert _geometry(_widget(root, "PopupHeader")) == (0, 0, 720, 58)
    assert _geometry(_widget(root, "DragIcon")) == (16, 20, 25, 25)
    assert _geometry(_widget(root, "MicrophoneButton")) == (87, 20, 25, 25)
    assert _geometry(_widget(root, "MicrophoneLevelLamp")) == (110, 23, 18, 18)
    assert _geometry(_widget(root, "SpeakerButton")) == (145, 20, 25, 25)
    assert _geometry(_widget(root, "SpeakerLevelLamp")) == (168, 23, 18, 18)
    assert _geometry(_widget(root, "LiveIndicator")) == (244, 26, 17, 15)
    assert _geometry(_widget(root, "PopupBrand")) == (308, 8, 104, 56)
    assert _geometry(_widget(root, "SettingsIcon")) == (603, 20, 25, 25)
    assert _geometry(_widget(root, "OpacityButton")) == (640, 20, 25, 25)
    assert _geometry(_widget(root, "PopupClose")) == (677, 20, 25, 25)
    names = {
        widget.attrib.get("name")
        for widget in root.iter("widget")
    }
    assert "PrivacyIcon" not in names
    assert "ProfileButton" not in names
    assert _widget(root, "PopupBrand").attrib["class"] == "LogoToggleButton"


def test_prompt_screen_matches_supplied_svg_sections() -> None:
    root = ET.parse(resource_path("prxmpt-prompt-screen.ui")).getroot()
    assert _geometry(_widget(root, "PromptCard")) == (0, 0, 720, 35)
    assert _geometry(_widget(root, "HistoryToggleButton")) == (15, 4, 25, 27)
    assert _geometry(_widget(root, "PlotToggleButton")) == (42, 4, 25, 27)
    assert _geometry(_widget(root, "QuestionInput")) == (70, 7, 580, 20)
    assert _geometry(_widget(root, "TranscriptionIndicator")) == (618, 8, 26, 18)
    assert _geometry(_widget(root, "ClearButton")) == (650, 4, 24, 27)
    assert _geometry(_widget(root, "AnswerButton")) == (676, 4, 29, 27)


def test_feedback_window_matches_supplied_svg_sections() -> None:
    root = ET.parse(resource_path("prxmpt-feedback-window.ui")).getroot()
    assert _geometry(_widget(root, "AnswerView")) == (6, 7, 708, 215)
    assert _geometry(_widget(root, "AnswerLoadingSpinner")) == (349, 104, 22, 22)
    assert _geometry(_widget(root, "ModelBadge")) == (14, 227, 100, 25)
    assert _geometry(_widget(root, "PreviousAnswerButton")) == (326, 228, 25, 25)
    assert _geometry(_widget(root, "NextAnswerButton")) == (369, 228, 25, 25)
    assert _geometry(_widget(root, "AutoAnswerSwitch")) == (607, 227, 25, 25)
    assert _geometry(_widget(root, "StealthSwitch")) == (677, 227, 25, 25)


def test_forms_contain_every_required_interactive_control() -> None:
    names = set()
    for filename in FORMS:
        root = ET.parse(resource_path(filename)).getroot()
        names.update(widget.attrib.get("name") for widget in root.iter("widget"))
    required = {
        "SettingsIcon",
        "OpacityButton",
        "DragIcon",
        "PopupClose",
        "MicrophoneButton",
        "MicrophoneLevelLamp",
        "SpeakerButton",
        "SpeakerLevelLamp",
        "LiveButton",
        "QuestionInput",
        "AnswerButton",
        "TranscriptionIndicator",
        "ClearButton",
        "PlotToggleButton",
        "HistoryToggleButton",
        "AnswerView",
        "AnswerLoadingSpinner",
        "ModelBadge",
        "PreviousAnswerButton",
        "NextAnswerButton",
        "AutoAnswerSwitch",
        "StealthSwitch",
        "HistoryScroll",
    }
    assert required <= names
