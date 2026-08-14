APP_STYLE = r"""
QMainWindow, QWidget {
    background: #20242C;
    color: #E8ECF2;
    font-size: 12px;
}
QMenuBar, QMenu, QToolBar, QStatusBar {
    background: #191D24;
    color: #E8ECF2;
}
QToolBar { border: 0; spacing: 6px; padding: 4px; }
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
QPushButton, QToolButton, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #2A303A;
    border: 1px solid #3C4553;
    border-radius: 4px;
    padding: 5px 7px;
    color: #F2F5F8;
}
QPushButton:hover, QToolButton:hover, QComboBox:hover {
    border-color: #738097;
}
QPushButton:pressed, QToolButton:pressed {
    background: #343C49;
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
"""
