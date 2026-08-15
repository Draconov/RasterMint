# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

APP_STYLE = r"""
QMainWindow, QWidget {
    background: #20242C;
    color: #E8ECF2;
    font-size: 12px;
}
QMenuBar, QMenu, QStatusBar {
    background: #191D24;
    color: #E8ECF2;
}
QMenuBar {
    padding: 2px 4px;
}
QMenuBar::item {
    padding: 5px 10px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: #315C46;
    color: #FFFFFF;
}
QMenu {
    border: 1px solid #353B47;
    padding: 4px;
}
QMenu::item {
    padding: 7px 30px 7px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #3D7658;
    color: #FFFFFF;
}
QMenu::separator {
    height: 1px;
    background: #353B47;
    margin: 4px 8px;
}
QGroupBox {
    border: 1px solid #353B47;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background: #2A303A;
    border: 1px solid #3C4553;
    border-radius: 4px;
    padding: 5px 7px;
    color: #F2F5F8;
}
QPushButton:hover, QToolButton:hover, QComboBox:hover, QSpinBox:hover,
QDoubleSpinBox:hover, QLineEdit:hover {
    border-color: #6BA982;
    background: #303943;
}
QPushButton:pressed, QToolButton:pressed {
    background: #385143;
}
QPushButton#resetSettingsButton {
    margin-top: 8px;
    background: #3A292D;
    border-color: #6C454D;
}
QPushButton#resetSettingsButton:hover {
    background: #53343B;
    border-color: #A56572;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #3A414D;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 13px;
    margin: -5px 0;
    background: #D8DEE8;
    border-radius: 6px;
}
QScrollArea { border: 0; }
QSplitter::handle { background: #15181E; width: 2px; height: 2px; }
QLabel#viewTitle {
    background: #191D24;
    color: #C8D0DB;
    padding: 5px 8px;
    font-weight: 600;
}
QLabel#inspectorTitle, QLabel#dialogTitle {
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    padding: 2px 0 6px 0;
}
QLabel#sectionHint {
    color: #AAB3C0;
}
QListWidget#inspectorNav {
    background: #181C22;
    border: 0;
    border-right: 1px solid #303641;
    padding: 8px 5px;
    outline: 0;
}
QListWidget#inspectorNav::item {
    min-height: 34px;
    padding: 4px 9px;
    margin: 1px 2px;
    border-radius: 5px;
    color: #C9D0DA;
}
QListWidget#inspectorNav::item:hover {
    background: #29372F;
    color: #FFFFFF;
}
QListWidget#inspectorNav::item:selected {
    background: #315C46;
    color: #FFFFFF;
    font-weight: 600;
}
QStackedWidget#inspectorDetails {
    background: #20242C;
    border: 0;
}
"""
