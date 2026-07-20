"""prxmpt popup and supporting-dialog theme."""

from clearcue.ui.skins import DEFAULT_SKIN_ID, get_skin


APP_STYLESHEET_TEMPLATE = """
QWidget {
    background: #000000;
    color: #f7f7f8;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QWidget#TopBarRoot,
QWidget#PromptScreenRoot,
QWidget#FeedbackWindowRoot,
QWidget#HistoryPopupRoot,
QWidget#HistoryContents,
QGraphicsView#PopupGraphicsView,
QMainWindow {
    background: transparent;
}
QFrame#PopupHeader {
    background: transparent;
    border: 0;
}
QFrame#PromptCard,
QFrame#FeedbackCard,
QFrame#HistoryCard {
    background: __POPUP_BASE__;
    border: 0;
    border-radius: 10px;
}
QLabel#LiveLabel,
QLabel#LiveIndicator,
QLabel#ToggleLabel,
QLabel#MeetingTitle,
QLabel#MeetingTime,
QLabel#MeetingDuration,
QLabel#MeetingModel,
QLabel#EmptyHistory {
    background: transparent;
}

QPushButton#SettingsIcon,
QPushButton#DragIcon,
LogoToggleButton#PopupBrand,
AudioLevelLamp#MicrophoneLevelLamp,
AudioLevelLamp#SpeakerLevelLamp,
QPushButton#PopupClose,
QPushButton#OpacityButton,
QPushButton#SpeakerButton,
QPushButton#MicrophoneButton,
QPushButton#LiveButton,
QPushButton#AnswerButton,
QPushButton#ClearButton,
QPushButton#PlotToggleButton,
QPushButton#HistoryToggleButton,
QPushButton#PreviousAnswerButton,
QPushButton#NextAnswerButton,
QPushButton#MeetingTranscript,
QPushButton#MeetingNotes,
QPushButton#MeetingDelete {
    background: transparent;
    border: 0;
    padding: 0;
    margin: 0;
}
QLabel#LiveLabel {
    color: #ffffff;
    font-family: "Comic Sans MS";
    font-size: 10px;
    font-weight: 700;
}
QLabel#LiveLabel[running="false"] { color: #9b9b9e; }
QLabel#LiveIndicator {
    background: #55575c;
    border: 0;
    border-radius: 7px;
}
QLabel#LiveIndicator[running="true"] { background: #34c759; }
QLabel#LiveIndicator[error="true"] { background: #ff453a; }
QPushButton#SettingsIcon[updateAvailable="true"] {
    background: rgba(255, 255, 66, 28);
}

QTextEdit#QuestionInput {
    background: __POPUP_ACCENT__;
    color: #ffffff;
    border: 0;
    border-radius: 3px;
    padding: 1px 5px 0 5px;
    font-family: "Comic Sans MS";
    font-size: 13px;
    font-weight: 600;
    selection-background-color: #0080ff;
}
QWidget#AnswerLoadingSpinner { background: transparent; border: 0; }
QPlainTextEdit#AnswerView {
    background: __POPUP_ACCENT__;
    color: #ffffff;
    border: 0;
    border-radius: 10px;
    padding: 10px 12px;
    font-family: "Comic Sans MS";
    font-size: 14px;
    font-weight: 600;
    selection-background-color: #0080ff;
}
QPushButton#ModelBadge {
    background: transparent;
    border: 0;
    color: #ffffff;
    padding: 0;
    font-family: "Comic Sans MS";
    font-size: 11px;
    font-weight: 700;
}
QLabel#ToggleLabel {
    color: #ffffff;
    font-family: "Comic Sans MS";
    font-size: 10px;
    font-weight: 700;
}
QLabel#PopupError,
QLabel#PopupErrorMirror {
    background: #fff400;
    color: #000000;
    border: 0;
    border-radius: 4px;
    padding: 1px 5px;
    font-family: "Segoe UI";
    font-size: 10px;
    font-weight: 700;
}

QScrollArea#HistoryScroll,
QScrollArea#HistoryScroll QWidget#qt_scrollarea_viewport {
    background: transparent;
    border: 0;
}
QFrame#MeetingRow {
    background: __POPUP_ACCENT__;
    border: 0;
    border-radius: 10px;
    min-height: 34px;
    max-height: 34px;
}
QLabel#MeetingTitle,
QLabel#MeetingTime,
QLabel#MeetingDuration,
QLabel#MeetingModel {
    color: #ffffff;
    font-family: "Comic Sans MS";
    font-size: 13px;
    font-weight: 600;
}
QLabel#MeetingTime { font-weight: 700; }
QLabel#MeetingDuration,
QLabel#MeetingModel { font-size: 11px; }
QLabel#EmptyHistory {
    color: #a7a4ad;
    font-family: "Comic Sans MS";
    font-size: 13px;
}
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 10px 0;
}
QScrollBar::handle:vertical {
    background: __POPUP_SCROLL_ACCENT__;
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }

QMenu {
    background: #111014;
    color: #ffffff;
    border: 1px solid #6d6874;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item { padding: 7px 28px 7px 12px; border-radius: 5px; }
QMenu::item:selected { background: __POPUP_MENU_ACCENT__; }
QMenu::item:disabled { color: #8b9398; }
QMenu QSlider::groove:horizontal {
    background: #4b4b52;
    height: 6px;
    border-radius: 3px;
}
QMenu QSlider::sub-page:horizontal {
    background: #28cf72;
    border-radius: 3px;
}
QMenu QSlider::handle:horizontal {
    background: #27d4c6;
    border: 1px solid rgba(255, 255, 255, 130);
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

/* Supporting dialogs intentionally remain simple, native and high contrast. */
QDialog { background: #111315; color: #ffffff; }
QFrame#Card { border: 1px solid #777777; }
QLabel#Title { font-size: 18pt; font-weight: 800; }
QLabel#Muted { color: #c8c8c8; }
QLabel#SectionTitle { color: #25cfff; font-weight: 800; }
QLabel#StatusText { color: #ffff8b; font-weight: 800; }
QLabel#SourceOn { color: #20e47b; font-weight: 800; }
QLabel#SourceRetry { color: #ffcf42; font-weight: 800; }
QLabel#SourceOff { color: #9a9a9a; font-weight: 800; }
QDialog QPushButton {
    background: #191c1f;
    color: #ffffff;
    border: 0;
    border-radius: 5px;
    padding: 6px 10px;
}
QDialog QPushButton:hover { background: #2b2f33; color: #ffffff; }
QDialog QPushButton:pressed { background: #101214; padding-top: 7px; padding-bottom: 5px; }
QPushButton#Primary { background: #18c96e; color: #06110a; }
QPushButton#Primary:hover { background: #2bdc81; }
QPushButton#Primary:pressed { background: #12ae5e; }
QPushButton#Danger { background: #d94050; }
QPushButton#Danger:hover { background: #ea5362; }
QPushButton#Danger:pressed { background: #b93341; }
QDialog QLineEdit,
QDialog QTextEdit,
QDialog QPlainTextEdit,
QDialog QTextBrowser,
QDialog QComboBox,
QDialog QListWidget {
    background: #080a0c;
    color: #ffffff;
    border: 1px solid #aeb4b8;
    border-radius: 5px;
    padding: 5px;
    selection-background-color: #0a9fe8;
}
QComboBox QAbstractItemView { background: #080a0c; color: #ffffff; }
QCheckBox { spacing: 7px; }
QProgressBar { border: 1px solid #ffffff; background: #000000; height: 12px; }
QProgressBar::chunk { background: #18c96e; }
QTabWidget::pane { border: 1px solid #777777; }
QTabBar::tab { background: #101316; border: 1px solid #777777; padding: 7px 11px; }
QTabBar::tab:selected { background: #0a9fe8; color: #ffffff; }
QToolTip { background: #ffffa2; color: #000000; border: 1px solid #000000; }
"""


def stylesheet_for_skin(skin_id: str) -> str:
    skin = get_skin(skin_id)
    return (
        APP_STYLESHEET_TEMPLATE.replace("__POPUP_BASE__", skin.qss_rgba("base"))
        .replace("__POPUP_ACCENT__", skin.qss_rgba("accent"))
        .replace("__POPUP_SCROLL_ACCENT__", skin.qss_rgba("accent", 80 / 255))
        .replace("__POPUP_MENU_ACCENT__", skin.qss_rgba("accent", 62 / 255))
    )


# Kept as a public compatibility constant for supporting tools and tests.
APP_STYLESHEET = stylesheet_for_skin(DEFAULT_SKIN_ID)
