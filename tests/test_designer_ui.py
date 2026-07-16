import xml.etree.ElementTree as ET

from clearcue.resources import resource_path


FORMS = {
    "prxmpt-top-bar.ui": ("TopBarRoot", (516, 46)),
    "prxmpt-audio-handler.ui": ("AudioHandlerRoot", (516, 161)),
    "prxmpt-activity-buttons.ui": ("ActivityButtonsRoot", (191, 22)),
    "prxmpt-plot-popup.ui": ("PlotPopupRoot", (516, 393)),
    "prxmpt-history-popup.ui": ("HistoryPopupRoot", (516, 390)),
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


def test_five_designer_forms_use_approved_fixed_geometry() -> None:
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
    assert _geometry(_widget(root, "PopupHeader")) == (0, 0, 516, 46)
    assert _geometry(_widget(root, "SettingsIcon")) == (18, 11, 24, 24)
    assert _geometry(_widget(root, "PopupBrand")) == (209, 0, 102, 46)
    assert _geometry(_widget(root, "DragIcon")) == (388, 12, 22, 22)
    assert _geometry(_widget(root, "PrivacyIcon")) == (434, 12, 23, 22)
    assert _geometry(_widget(root, "PopupClose")) == (481, 15, 17, 17)


def test_audio_handler_matches_supplied_svg_sections() -> None:
    root = ET.parse(resource_path("prxmpt-audio-handler.ui")).getroot()
    assert _geometry(_widget(root, "AudioCard")) == (0, 22, 110, 118)
    assert _geometry(_widget(root, "QuestionCard")) == (118, 0, 398, 161)
    assert _geometry(_widget(root, "LiveButton")) == (79, 43, 15, 15)
    assert _geometry(_widget(root, "AnswerButton")) == (43, 129, 100, 21)
    assert _geometry(_widget(root, "TranscriptionIndicator")) == (
        183,
        114,
        45,
        45,
    )
    assert _geometry(_widget(root, "ClearButton")) == (265, 129, 100, 21)


def test_forms_contain_every_required_interactive_control() -> None:
    names = set()
    for filename in FORMS:
        root = ET.parse(resource_path(filename)).getroot()
        names.update(widget.attrib.get("name") for widget in root.iter("widget"))
    required = {
        "SettingsIcon",
        "DragIcon",
        "PrivacyIcon",
        "PopupClose",
        "MicrophoneButton",
        "SpeakerButton",
        "LiveButton",
        "QuestionInput",
        "AnswerButton",
        "TranscriptionIndicator",
        "ClearButton",
        "PlotToggleButton",
        "HistoryToggleButton",
        "AnswerView",
        "ModelBadge",
        "AutoAnswerSwitch",
        "StealthSwitch",
        "HistoryScroll",
    }
    assert required <= names
