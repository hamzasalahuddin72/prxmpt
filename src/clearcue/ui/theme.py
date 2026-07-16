"""Flat high-contrast theme used by the performance build."""


APP_STYLESHEET = """
QWidget {
    background: #000000;
    color: #ffffff;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QFrame#Card {
    border: 2px solid #ffffff;
}
QFrame#UpdateBanner {
    background: #002b12;
    border: 2px solid #00ff66;
}
QLabel#UpdateText {
    background: #002b12;
    color: #ffffff;
    font-weight: 700;
}
QLabel#Title {
    font-size: 18pt;
    font-weight: 800;
    color: #ffffff;
}
QLabel#ModeBadge {
    background: #ffff00;
    color: #000000;
    border: 1px solid #ffff00;
    padding: 3px 7px;
    font-weight: 800;
}
QLabel#Muted {
    color: #c8c8c8;
}
QLabel#SectionTitle {
    color: #00ffff;
    font-size: 10pt;
    font-weight: 800;
}
QLabel#StatusText {
    color: #ffff00;
    font-weight: 800;
}
QLabel#SourceOn {
    color: #00ff66;
    font-weight: 800;
}
QLabel#SourceRetry {
    color: #ffff00;
    font-weight: 800;
}
QLabel#SourceOff {
    color: #9a9a9a;
    font-weight: 800;
}
QLabel#ErrorBanner {
    background: #ffff00;
    color: #000000;
    border: 2px solid #ffffff;
    padding: 6px;
    font-weight: 700;
}
QPushButton {
    background: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 6px 10px;
    font-weight: 650;
}
QPushButton:hover, QPushButton:focus {
    background: #ffffff;
    color: #000000;
}
QPushButton:pressed {
    background: #c8c8c8;
    color: #000000;
}
QPushButton:disabled {
    border-color: #666666;
    color: #777777;
}
QPushButton#Primary {
    background: #00ff66;
    color: #000000;
    border-color: #00ff66;
    font-weight: 800;
}
QPushButton#Primary:hover { background: #ffffff; border-color: #ffffff; }
QPushButton#Danger {
    background: #ff3030;
    color: #ffffff;
    border-color: #ff3030;
    font-weight: 800;
}
QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser, QComboBox, QListWidget {
    background: #000000;
    color: #ffffff;
    border: 2px solid #ffffff;
    padding: 5px;
    selection-background-color: #ffff00;
    selection-color: #000000;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QListWidget:focus {
    border-color: #00ffff;
}
QComboBox::drop-down {
    border-left: 1px solid #ffffff;
    width: 22px;
}
QComboBox QAbstractItemView {
    background: #000000;
    color: #ffffff;
    selection-background-color: #ffff00;
    selection-color: #000000;
}
QCheckBox { spacing: 7px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 2px solid #ffffff;
    background: #000000;
}
QCheckBox::indicator:checked { background: #00ff66; }
QProgressBar {
    border: 1px solid #ffffff;
    background: #000000;
    height: 12px;
}
QProgressBar::chunk { background: #00ff66; }
QTabWidget::pane { border: 2px solid #ffffff; }
QTabBar::tab {
    background: #000000;
    color: #ffffff;
    border: 1px solid #ffffff;
    padding: 7px 11px;
}
QTabBar::tab:selected {
    background: #ffff00;
    color: #000000;
}
QSplitter::handle { background: #ffffff; }
QStatusBar { color: #ffffff; border-top: 1px solid #ffffff; }
QToolTip {
    background: #ffff00;
    color: #000000;
    border: 1px solid #ffffff;
}
"""
