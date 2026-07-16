"""prxmpt popup and supporting-dialog theme."""


APP_STYLESHEET = """
QWidget {
    background: #000000;
    color: #f7f7f8;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QWidget#TransparentRoot, QWidget#TransparentPanel, QMainWindow {
    background: transparent;
}
QFrame#PopupRoot {
    background: #000000;
    border: 1px solid #81817a;
    border-radius: 58px;
}
QFrame#PopupHeader {
    background: rgba(63, 92, 114, 77);
    border: 1px solid #000000;
    border-radius: 32px;
}
QLabel#PopupBrand {
    background: transparent;
}
QPushButton#SettingsIcon,
QPushButton#HeaderIcon,
QPushButton#DragIcon,
QPushButton#PrivacyIcon,
QPushButton#PopupClose {
    padding: 0;
    margin: 0;
    background: transparent;
    border: 0;
}
QPushButton#SettingsIcon:hover,
QPushButton#DragIcon:hover,
QPushButton#PrivacyIcon:hover,
QPushButton#PopupClose:hover { border: 1px solid #ffffff; border-radius: 6px; }
QPushButton#SettingsIcon[updateAvailable="true"] {
    border: 2px solid #ffff42;
    border-radius: 17px;
}

QFrame#AudioCard,
QFrame#QuestionCard,
QFrame#AnswerCard {
    background: #1f1f20;
    border: 0;
    border-radius: 58px;
}
QFrame#AudioCard { background: rgba(255, 255, 255, 31); }
QPushButton#AudioSourceButton {
    padding: 0;
    margin: 0;
    background: transparent;
    border: 2px solid transparent;
    border-radius: 10px;
}
QPushButton#AudioSourceButton[active="true"][signal="true"] {
    border-color: #ffffff;
}
QPushButton#AudioSourceButton[sourceState="retrying"] {
    border-color: #ffcf42;
}
QPushButton#AudioSourceButton:hover { border-color: #ffffff; }
QPushButton#ModelBadge {
    background: #000000;
    color: #f1f1f4;
    border: 1px solid #4b3726;
    border-radius: 14px;
    padding: 0 8px;
    font-size: 8.5pt;
}
QPushButton#ModelBadge:hover { border-color: #25cfff; }
QPushButton#LiveButton {
    padding: 0;
    background: #67696d;
    color: #ffffff;
    border: 0;
    border-radius: 14px;
    font-size: 9pt;
    font-weight: 700;
}
QPushButton#LiveButton[running="true"] { background: #34c759; }
QPushButton#LiveButton:hover { border: 1px solid #ffffff; }

QPlainTextEdit#QuestionInput {
    background: transparent;
    color: #f8f8f9;
    border: 0;
    padding: 4px 6px;
    font-size: 15pt;
    selection-background-color: #0a9fe8;
}
QPushButton#AnswerButton,
QPushButton#ClearButton,
QLabel#TranscriptionIndicator {
    background: transparent;
    border: 0;
}
QPushButton#SessionPill {
    min-height: 29px;
    max-height: 29px;
    border: 0;
    padding: 0 15px;
    color: #ffffff;
}
QPushButton#AnswerButton {
    background: #069ee7;
    border-radius: 15px;
}
QPushButton#AnswerButton:hover { background: #25cfff; color: #071016; }
QPushButton#ClearButton {
    background: #9b9ca1;
    border-radius: 15px;
}
QPushButton#ClearButton:hover { background: #c8c9cd; color: #111111; }
QPushButton#SessionPill {
    min-width: 46px;
    max-width: 64px;
    padding: 0 8px;
    background: #a7afbd;
    border-radius: 15px;
    font-weight: 800;
    font-size: 8pt;
}
QPushButton#SessionPill[running="true"] {
    background: #18c96e;
    color: #07120b;
}

QPlainTextEdit#AnswerView {
    background: #252527;
    color: #f8f8f9;
    border: 1px solid #9b9ca1;
    border-radius: 58px;
    padding: 18px 20px;
    font-size: 15.5pt;
    selection-background-color: #0a9fe8;
}
QLabel#PopupError {
    background: #ffff00;
    color: #000000;
    border-radius: 8px;
    padding: 5px 8px;
    font-weight: 700;
}
QLabel#ToggleLabel {
    background: transparent;
    color: #ffffff;
    font-size: 9.5pt;
}

QFrame#HistoryCard {
    background: rgba(0, 26, 53, 51);
    border: 0;
    border-radius: 58px;
}
QFrame#MeetingRow {
    background: transparent;
    border: 0;
    border-bottom: 1px solid #4b5962;
    min-height: 25px;
    max-height: 29px;
}
QFrame#MeetingRow[last="true"] { border-bottom: 0; }
QLabel#MeetingTitle,
QLabel#MeetingTime,
QLabel#EmptyHistory {
    background: transparent;
    color: #f4f5f7;
}
QLabel#MeetingTitle { font-size: 10pt; }
QLabel#MeetingTime { font-size: 10pt; }
QLabel#EmptyHistory { padding: 18px; color: #9ea7ad; }
QPushButton#MeetingTranscript,
QPushButton#MeetingNotes,
QPushButton#MeetingDelete {
    padding: 0;
    margin: 0;
    background: transparent;
    border: 0;
    font-size: 14pt;
    font-weight: 800;
}
QPushButton#MeetingTranscript { color: #22dbff; }
QPushButton#MeetingNotes { color: #8b5cff; }
QPushButton#MeetingDelete { color: #ff5264; }
QPushButton#MeetingTranscript:hover,
QPushButton#MeetingNotes:hover,
QPushButton#MeetingDelete:hover { color: #ffffff; }

QMenu {
    background: #111a1f;
    color: #ffffff;
    border: 1px solid #65717a;
    padding: 5px;
}
QMenu::item { padding: 7px 28px 7px 12px; }
QMenu::item:selected { background: #0a9fe8; }
QMenu::item:disabled { color: #8b9398; }

/* Supporting dialogs retain simple high-contrast controls. */
QDialog { background: #111315; color: #ffffff; }
QFrame#Card { border: 1px solid #777777; }
QLabel#Title { font-size: 18pt; font-weight: 800; }
QLabel#Muted { color: #c8c8c8; }
QLabel#SectionTitle { color: #25cfff; font-weight: 800; }
QLabel#StatusText { color: #ffff8b; font-weight: 800; }
QLabel#SourceOn { color: #20e47b; font-weight: 800; }
QLabel#SourceRetry { color: #ffcf42; font-weight: 800; }
QLabel#SourceOff { color: #9a9a9a; font-weight: 800; }
QPushButton {
    background: #191c1f;
    color: #ffffff;
    border: 1px solid #c5c8ca;
    border-radius: 5px;
    padding: 6px 10px;
}
QPushButton:hover { background: #ffffff; color: #111111; }
QPushButton#Primary { background: #18c96e; color: #06110a; border-color: #18c96e; }
QPushButton#Danger { background: #d94050; border-color: #d94050; }
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QComboBox, QListWidget {
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
