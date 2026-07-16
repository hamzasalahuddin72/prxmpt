import xml.etree.ElementTree as ET

from clearcue.resources import resource_path


def _widget(root: ET.Element, name: str) -> ET.Element:
    for widget in root.iter("widget"):
        if widget.attrib.get("name") == name:
            return widget
    raise AssertionError(f"missing Designer widget: {name}")


def _geometry(widget: ET.Element) -> tuple[int, int, int, int]:
    geometry = widget.find("./property[@name='geometry']/rect")
    assert geometry is not None, widget.attrib.get("name")
    return tuple(int(geometry.findtext(part, "0")) for part in ("x", "y", "width", "height"))


def test_designer_form_uses_approved_fixed_geometry() -> None:
    root = ET.parse(resource_path("prxmpt-main.ui")).getroot()
    assert _geometry(_widget(root, "TransparentRoot")) == (0, 0, 551, 827)
    assert _geometry(_widget(root, "PopupHeader")) == (20, 12, 515, 64)
    assert _geometry(_widget(root, "AudioCard")) == (20, 12, 166, 178)
    assert _geometry(_widget(root, "QuestionCard")) == (192, 13, 350, 178)
    assert _geometry(_widget(root, "AnswerCard")) == (10, 203, 532, 393)
    assert _geometry(_widget(root, "HistoryCard")) == (8, 607, 537, 132)


def test_designer_form_keeps_section_minimum_and_maximum_sizes_equal() -> None:
    root = ET.parse(resource_path("prxmpt-main.ui")).getroot()
    for name in ("PopupHeader", "AudioCard", "QuestionCard", "AnswerCard", "HistoryCard"):
        widget = _widget(root, name)
        minimum = widget.find("./property[@name='minimumSize']/size")
        maximum = widget.find("./property[@name='maximumSize']/size")
        assert minimum is not None and maximum is not None
        min_size = (int(minimum.findtext("width", "0")), int(minimum.findtext("height", "0")))
        max_size = (int(maximum.findtext("width", "0")), int(maximum.findtext("height", "0")))
        assert min_size == max_size == _geometry(widget)[2:]


def test_designer_form_contains_required_interactive_controls() -> None:
    root = ET.parse(resource_path("prxmpt-main.ui")).getroot()
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
        "AnswerView",
        "ModelBadge",
        "AutoAnswerSwitch",
        "StealthSwitch",
        "HistoryCard",
    }
    names = {widget.attrib.get("name") for widget in root.iter("widget")}
    assert required <= names
