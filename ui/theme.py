from PyQt6.QtGui import QFont


LIGHT_PALETTE = {
    "BG_PRIMARY": "#d8dee6",
    "BG_SECONDARY": "#e3e8ef",
    "BG_SURFACE": "#ebeff4",
    "BG_ELEVATED": "#f2f4f8",
    "BG_HOVER": "#cfd6e1",
    "ACCENT": "#2563eb",
    "ACCENT_HOVER": "#1d4ed8",
    "ACCENT_DIM": "#3b82f6",
    "ACCENT_WARM": "#d97706",
    "TEXT": "#1e293b",
    "TEXT_DIM": "#4e5d73",
    "TEXT_BRIGHT": "#0f172a",
    "BORDER": "#c0c8d6",
    "BORDER_LIGHT": "#a8b2c4",
    "BORDER_FOCUS": "#2563eb",
    "VISITED": "#93c5fd",
    "FRONTIER": "#f59e0b",
    "PATH": "#2563eb",
    "WALL": "#334155",
    "START": "#16a34a",
    "GOAL": "#e11d48",
    "PRUNED": "#fda4af",
    "WEIGHT_LOW": "#fde68a",
    "WEIGHT_HIGH": "#fca5a5",
    "ERROR": "#e11d48",
    "WARNING": "#d97706",
    "SUCCESS": "#16a34a",
}

DARK_PALETTE = {
    "BG_PRIMARY": "#111217",
    "BG_SECONDARY": "#171920",
    "BG_SURFACE": "#1e212b",
    "BG_ELEVATED": "#252936",
    "BG_HOVER": "#2e3344",
    "ACCENT": "#7c83ff",
    "ACCENT_HOVER": "#949aff",
    "ACCENT_DIM": "#5a62e6",
    "ACCENT_WARM": "#f59e0b",
    "TEXT": "#e4e6ef",
    "TEXT_DIM": "#8b90a5",
    "TEXT_BRIGHT": "#ffffff",
    "BORDER": "#2a2e3d",
    "BORDER_LIGHT": "#3a4054",
    "BORDER_FOCUS": "#7c83ff",
    "VISITED": "#1e3a4c",
    "FRONTIER": "#f59e0b",
    "PATH": "#22d3ee",
    "WALL": "#2c303d",
    "START": "#10b981",
    "GOAL": "#f43f5e",
    "PRUNED": "#3b2638",
    "WEIGHT_LOW": "#1c3329",
    "WEIGHT_HIGH": "#451e29",
    "ERROR": "#f43f5e",
    "WARNING": "#f59e0b",
    "SUCCESS": "#10b981",
}


class Colors:
    MODE = "light"
    BG_PRIMARY = LIGHT_PALETTE["BG_PRIMARY"]
    BG_SECONDARY = LIGHT_PALETTE["BG_SECONDARY"]
    BG_SURFACE = LIGHT_PALETTE["BG_SURFACE"]
    BG_ELEVATED = LIGHT_PALETTE["BG_ELEVATED"]
    BG_HOVER = LIGHT_PALETTE["BG_HOVER"]
    ACCENT = LIGHT_PALETTE["ACCENT"]
    ACCENT_HOVER = LIGHT_PALETTE["ACCENT_HOVER"]
    ACCENT_DIM = LIGHT_PALETTE["ACCENT_DIM"]
    ACCENT_WARM = LIGHT_PALETTE["ACCENT_WARM"]
    TEXT = LIGHT_PALETTE["TEXT"]
    TEXT_DIM = LIGHT_PALETTE["TEXT_DIM"]
    TEXT_BRIGHT = LIGHT_PALETTE["TEXT_BRIGHT"]
    BORDER = LIGHT_PALETTE["BORDER"]
    BORDER_LIGHT = LIGHT_PALETTE["BORDER_LIGHT"]
    BORDER_FOCUS = LIGHT_PALETTE["BORDER_FOCUS"]
    VISITED = LIGHT_PALETTE["VISITED"]
    FRONTIER = LIGHT_PALETTE["FRONTIER"]
    PATH = LIGHT_PALETTE["PATH"]
    WALL = LIGHT_PALETTE["WALL"]
    START = LIGHT_PALETTE["START"]
    GOAL = LIGHT_PALETTE["GOAL"]
    PRUNED = LIGHT_PALETTE["PRUNED"]
    WEIGHT_LOW = LIGHT_PALETTE["WEIGHT_LOW"]
    WEIGHT_HIGH = LIGHT_PALETTE["WEIGHT_HIGH"]
    ERROR = LIGHT_PALETTE["ERROR"]
    WARNING = LIGHT_PALETTE["WARNING"]
    SUCCESS = LIGHT_PALETTE["SUCCESS"]


def set_theme(mode: str):
    palette = DARK_PALETTE if mode == "dark" else LIGHT_PALETTE
    Colors.MODE = "dark" if mode == "dark" else "light"
    for key, val in palette.items():
        setattr(Colors, key, val)


def current_theme() -> str:
    return Colors.MODE


class Fonts:
    FAMILY = "Segoe UI"
    FAMILY_MONO = "Cascadia Code"
    SIZE_XS = 10
    SIZE_S = 11
    SIZE_M = 12
    SIZE_L = 14
    SIZE_XL = 17
    SIZE_TITLE = 20

    @staticmethod
    def body() -> QFont:
        return QFont(Fonts.FAMILY, Fonts.SIZE_M)

    @staticmethod
    def mono() -> QFont:
        f = QFont(Fonts.FAMILY_MONO, Fonts.SIZE_S)
        f.setStyleHint(QFont.StyleHint.Monospace)
        return f

    @staticmethod
    def heading() -> QFont:
        return QFont(Fonts.FAMILY, Fonts.SIZE_XL, QFont.Weight.DemiBold)


SPACING = 10
RADIUS = 8


def build_stylesheet() -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {Colors.BG_PRIMARY};
        color: {Colors.TEXT};
        font-family: "{Fonts.FAMILY}";
        font-size: {Fonts.SIZE_M}px;
    }}

    QFrame#sidebar {{
        background-color: {Colors.BG_SECONDARY};
        border-right: 1px solid {Colors.BORDER};
    }}

    QFrame#inspector-dock {{
        background-color: {Colors.BG_SECONDARY};
        border-left: 1px solid {Colors.BORDER};
    }}

    QFrame#card {{
        background-color: {Colors.BG_SURFACE};
        border: 1px solid {Colors.BORDER};
        border-radius: {RADIUS}px;
    }}

    QFrame#kpi-card {{
        background-color: {Colors.BG_SURFACE};
        border: 1px solid {Colors.BORDER};
        border-radius: {RADIUS}px;
    }}
    QFrame#kpi-card:hover {{
        border-color: {Colors.BORDER_LIGHT};
        background-color: {Colors.BG_ELEVATED};
    }}

    QFrame#playback-bar {{
        background-color: {Colors.BG_SECONDARY};
        border-top: 1px solid {Colors.BORDER};
    }}

    QFrame#empty-canvas {{
        background-color: {Colors.BG_SECONDARY};
        border: 1px dashed {Colors.BORDER_LIGHT};
        border-radius: 12px;
    }}

    QLabel {{
        color: {Colors.TEXT};
        background: transparent;
    }}
    QLabel#dim {{
        color: {Colors.TEXT_DIM};
        font-size: {Fonts.SIZE_S}px;
    }}
    QLabel#section-title {{
        color: {Colors.TEXT_DIM};
        font-size: {Fonts.SIZE_XS}px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    QLabel#accent {{
        color: {Colors.ACCENT};
    }}
    QLabel#kpi-value {{
        color: {Colors.TEXT_BRIGHT};
        font-size: {Fonts.SIZE_XL}px;
        font-weight: 700;
        font-family: "{Fonts.FAMILY_MONO}";
    }}
    QLabel#kpi-label {{
        color: {Colors.TEXT_DIM};
        font-size: {Fonts.SIZE_XS}px;
        font-weight: 600;
    }}
    QLabel#mono-badge {{
        color: {Colors.ACCENT};
        background-color: {Colors.BG_ELEVATED};
        border: 1px solid {Colors.BORDER};
        border-radius: 4px;
        padding: 2px 6px;
        font-family: "{Fonts.FAMILY_MONO}";
        font-size: {Fonts.SIZE_XS}px;
    }}

    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
        background-color: {Colors.BG_ELEVATED};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 5px 10px;
        min-height: 22px;
        color: {Colors.TEXT_BRIGHT};
    }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{
        border-color: {Colors.BORDER_LIGHT};
        background-color: {Colors.BG_HOVER};
    }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
        border-color: {Colors.BORDER_FOCUS};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid {Colors.BORDER};
        border-bottom: 1px solid {Colors.BORDER};
        border-top-right-radius: 5px;
        background-color: {Colors.BG_SURFACE};
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid {Colors.BORDER};
        border-bottom-right-radius: 5px;
        background-color: {Colors.BG_SURFACE};
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {Colors.BG_HOVER};
    }}
    QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
    QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
        background-color: {Colors.BORDER};
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: none;
        width: 0;
        height: 0;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.BG_ELEVATED};
        border: 1px solid {Colors.BORDER_LIGHT};
        selection-background-color: {Colors.BG_HOVER};
        selection-color: {Colors.ACCENT};
        color: {Colors.TEXT};
        outline: 0;
    }}

    QCheckBox {{
        color: {Colors.TEXT};
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 15px;
        height: 15px;
        border-radius: 4px;
        border: 1px solid {Colors.BORDER_LIGHT};
        background-color: {Colors.BG_ELEVATED};
    }}
    QCheckBox::indicator:checked {{
        background-color: {Colors.ACCENT};
        border-color: {Colors.ACCENT};
    }}

    QPushButton {{
        background-color: {Colors.BG_ELEVATED};
        border: 1px solid {Colors.BORDER};
        border-radius: 6px;
        padding: 7px 14px;
        color: {Colors.TEXT};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {Colors.BG_HOVER};
        border-color: {Colors.BORDER_LIGHT};
        color: {Colors.TEXT_BRIGHT};
    }}
    QPushButton:pressed {{
        background-color: {Colors.BG_SURFACE};
    }}
    QPushButton:disabled {{
        color: {Colors.TEXT_DIM};
        background-color: {Colors.BG_SURFACE};
        border-color: {Colors.BORDER};
    }}
    QPushButton#primary {{
        background-color: {Colors.ACCENT};
        color: #ffffff;
        border: none;
        font-weight: 700;
        padding: 8px 16px;
    }}
    QPushButton#primary:hover {{
        background-color: {Colors.ACCENT_HOVER};
        color: #ffffff;
    }}
    QPushButton#primary:pressed {{
        background-color: {Colors.ACCENT_DIM};
    }}
    QPushButton#icon-btn, QPushButton#icon-btn:hover, QPushButton#icon-btn:pressed {{
        background-color: transparent;
        border: none;
        padding: 0;
    }}
    QPushButton#zoom-btn {{
        padding: 0 6px;
        font-size: 11px;
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {Colors.BORDER};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {Colors.ACCENT};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
        border: 2px solid {Colors.BG_SECONDARY};
    }}
    QSlider::handle:horizontal:hover {{
        background: {Colors.ACCENT_HOVER};
    }}
    QSlider::sub-page:horizontal {{
        background: {Colors.ACCENT_DIM};
        border-radius: 2px;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 7px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {Colors.BORDER_LIGHT};
        border-radius: 3px;
        min-height: 28px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QSplitter::handle {{
        background: {Colors.BORDER};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}

    QStatusBar {{
        background-color: {Colors.BG_SECONDARY};
        color: {Colors.TEXT_DIM};
        border-top: 1px solid {Colors.BORDER};
        font-size: {Fonts.SIZE_S}px;
        padding: 2px 8px;
    }}

    QToolTip {{
        background-color: {Colors.BG_ELEVATED};
        color: {Colors.TEXT_BRIGHT};
        border: 1px solid {Colors.BORDER_LIGHT};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    """
