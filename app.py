import ctypes
import json
import sys
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, QTimer, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QGuiApplication, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QSlider,
    QStyle,
)


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "settings.json"
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")

DEFAULT_CONFIG = {
    "last_file": "",
    "font_family": "Microsoft YaHei UI",
    "font_size": 18,
    "foreground": "#cfd8dc",
    "text_opacity": 1.0,
    "background": "#101418",
    "background_opacity": 0.72,
    "always_on_top": True,
    "toolbar_visible": True,
    "wrap": True,
    "geometry": "760x520+160+120",
    "hotkeys": {
        "open": "Ctrl+O",
        "hide_toolbar": "Ctrl+H",
        "settings": "Ctrl+,",
        "minimize": "Ctrl+Alt+M",
    },
    "files": {},
}

VK_CODES = {
    "BACKSPACE": 0x08,
    "TAB": 0x09,
    "ENTER": 0x0D,
    "ESC": 0x1B,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "PAGEUP": 0x21,
    "PAGEDOWN": 0x22,
    "END": 0x23,
    "HOME": 0x24,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    ";": 0xBA,
    "'": 0xDE,
    "[": 0xDB,
    "]": 0xDD,
    "\\": 0xDC,
    "-": 0xBD,
    "=": 0xBB,
}
for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=0x41):
    VK_CODES[letter] = index
for index, digit in enumerate("0123456789", start=0x30):
    VK_CODES[digit] = index
for number in range(1, 25):
    VK_CODES[f"F{number}"] = 0x70 + number - 1


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_size_t),
        ("time", ctypes.c_uint32),
        ("pt", POINT),
    ]


def deep_update(base, updates):
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = value


def load_config():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    saved = {}
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            deep_update(config, saved)
        except (OSError, json.JSONDecodeError):
            pass
    if "background_opacity" not in saved and "opacity" in saved:
        config["background_opacity"] = saved["opacity"]
    config["background_opacity"] = clamp(float(config.get("background_opacity", 0.72)), 0, 1)
    config["text_opacity"] = clamp(float(config.get("text_opacity", 1.0)), 0, 1)
    return config


def save_config(config):
    temp_path = CONFIG_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(CONFIG_PATH)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def read_text_file(path):
    raw = Path(path).read_bytes()
    last_error = None
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("unknown", raw, 0, len(raw), str(last_error))


def parse_geometry(value):
    try:
        size, x, y = value.replace("+", "x", 1).replace("+", "x", 1).split("x")
    except ValueError:
        return 760, 520, 160, 120
    parts = value.replace("+", "x").split("x")
    try:
        width, height, left, top = [int(part) for part in parts[:4]]
        return width, height, left, top
    except (ValueError, TypeError):
        return 760, 520, 160, 120


def normalize_hotkey(value):
    parts = [part.strip() for part in value.replace("-", "+").split("+") if part.strip()]
    if not parts:
        return ""
    aliases = {
        "CONTROL": "Ctrl",
        "CTRL": "Ctrl",
        "COMMAND": "Win",
        "CMD": "Win",
        "WINDOWS": "Win",
        "WIN": "Win",
        "OPTION": "Alt",
        "ALT": "Alt",
        "SHIFT": "Shift",
    }
    normalized = []
    key = ""
    for part in parts:
        upper = part.upper()
        if upper in aliases:
            label = aliases[upper]
            if label not in normalized:
                normalized.append(label)
        else:
            key = part.upper() if len(part) > 1 else part
    return "+".join(normalized + [key]) if key else ""


def parse_hotkey(value):
    normalized = normalize_hotkey(value)
    if not normalized:
        raise ValueError("快捷键不能为空")
    parts = normalized.split("+")
    key = parts[-1].upper()
    modifiers = set(parts[:-1])
    if key not in VK_CODES:
        raise ValueError(f"不支持的按键: {parts[-1]}")
    return normalized, modifiers, key


def qcolor_to_rgba(color, opacity):
    qcolor = QColor(color)
    if not qcolor.isValid():
        qcolor = QColor("#cfd8dc")
    alpha = round(clamp(opacity, 0, 1) * 255)
    return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha})"


def qcolor_to_hex(color):
    qcolor = QColor(color)
    return qcolor.name() if qcolor.isValid() else "#cfd8dc"


class NovelReader(QMainWindow):
    HOTKEY_ID_MINIMIZE = 1001
    WM_HOTKEY = 0x0312
    PM_REMOVE = 0x0001
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008

    RESIZE_MARGIN = 10
    TITLE_DRAG_HEIGHT = 38

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.current_file = ""
        self.current_encoding = ""
        self.drag_start = None
        self.resize_state = None
        self.global_hotkey_registered = False
        self.is_windows = sys.platform.startswith("win")

        self.setWindowTitle("摸鱼阅读器")
        self.compact_toolbar = None
        self.setMinimumSize(180, 140)
        self.apply_window_flags(force=True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        width, height, left, top = parse_geometry(self.config.get("geometry", "760x520+160+120"))
        self.setGeometry(left, top, width, height)

        self.build_ui()
        self.apply_style()
        self.update_toolbar_mode()
        self.rebind_hotkeys()
        self.register_global_minimize_hotkey()
        self.start_hotkey_timer()

        last_file = self.config.get("last_file", "")
        if last_file and Path(last_file).exists():
            self.open_file(last_file, restore_progress=True)
        else:
            self.show_welcome()

    def build_ui(self):
        self.shell = QWidget(self)
        self.shell.setObjectName("shell")
        self.setCentralWidget(self.shell)

        self.main_layout = QVBoxLayout(self.shell)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.toolbar = QWidget(self.shell)
        self.toolbar_layout = QHBoxLayout(self.toolbar)
        self.toolbar_layout.setContentsMargins(6, 5, 6, 5)
        self.toolbar_layout.setSpacing(4)

        style = self.style()
        self.open_button = self.tool_button("打开 TXT", style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), self.choose_file)
        self.font_down_button = self.tool_button("字号减小", None, lambda: self.change_font_size(-1), "A-")
        self.font_up_button = self.tool_button("字号增大", None, lambda: self.change_font_size(1), "A+")
        self.bg_down_button = self.tool_button("背景更透明", None, lambda: self.change_background_opacity(-0.05), "B-")
        self.bg_up_button = self.tool_button("背景更实", None, lambda: self.change_background_opacity(0.05), "B+")
        self.text_down_button = self.tool_button("文字更透明", None, lambda: self.change_text_opacity(-0.05), "T-")
        self.text_up_button = self.tool_button("文字更实", None, lambda: self.change_text_opacity(0.05), "T+")
        self.more_button = self.tool_button("更多操作", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton), self.show_more_menu)

        self.progress_label = QLabel("0.00%")
        self.progress_label.setFixedWidth(62)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.jump_entry = QLineEdit()
        self.jump_entry.setPlaceholderText("%")
        self.jump_entry.setFixedWidth(58)
        self.jump_entry.returnPressed.connect(self.jump_to_progress)
        self.jump_button = self.tool_button("跳转到进度", style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward), self.jump_to_progress)
        self.hide_button = self.tool_button("隐藏工具栏", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarShadeButton), self.toggle_toolbar)
        self.settings_button = self.tool_button("设置", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), self.open_settings)
        self.minimize_button = self.tool_button("最小化", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton), self.minimize_to_taskbar)
        self.close_button = self.tool_button("关闭", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton), self.close)

        for widget in (
            self.open_button,
            self.font_down_button,
            self.font_up_button,
            self.bg_down_button,
            self.bg_up_button,
            self.text_down_button,
            self.text_up_button,
            self.more_button,
            self.progress_label,
            self.jump_entry,
            self.jump_button,
            self.hide_button,
            self.settings_button,
            self.minimize_button,
            self.close_button,
        ):
            self.toolbar_layout.addWidget(widget)
        self.toolbar_layout.addStretch(1)

        self.restore_toolbar_button = self.tool_button("显示工具栏", style.standardIcon(QStyle.StandardPixmap.SP_TitleBarUnshadeButton), self.toggle_toolbar)
        self.restore_toolbar_button.setParent(self.shell)
        self.restore_toolbar_button.setFixedSize(28, 24)
        self.restore_toolbar_button.hide()

        self.reader = QTextEdit(self.shell)
        self.reader.setReadOnly(True)
        self.reader.setFrameShape(QTextEdit.Shape.NoFrame)
        self.reader.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.reader.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.reader.viewport().installEventFilter(self)
        self.reader.viewport().setMouseTracking(True)
        self.reader.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.status = QLabel("未打开文件", self.shell)
        self.status.setFixedHeight(24)
        self.status.setContentsMargins(8, 0, 8, 0)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.reader, 1)
        self.main_layout.addWidget(self.status)
        self.apply_toolbar_visibility(bool(self.config.get("toolbar_visible", True)))

        for widget in (self.shell, self.reader, self.reader.viewport(), self.status):
            widget.installEventFilter(self)
            widget.setMouseTracking(True)

    def tool_button(self, tooltip, icon, callback, text=""):
        button = QToolButton(self)
        if icon is not None:
            button.setIcon(icon)
        if text:
            button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setFixedSize(28, 26)
        button.clicked.connect(lambda checked=False, cb=callback: cb())
        return button

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.restore_toolbar_button.move(max(0, self.width() - 34), 4)
        self.restore_toolbar_button.raise_()
        self.update_toolbar_mode()

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_toolbar_visibility(bool(self.config.get("toolbar_visible", True)))

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ContextMenu:
            self.show_context_menu(event.globalPos())
            return True

        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapFromGlobal(event.globalPosition().toPoint())
            edge = self.edge_at(pos)
            if edge:
                self.start_resize(event.globalPosition().toPoint(), edge)
                return True
            if watched in (self.reader.viewport(), self.shell, self.status) and pos.y() <= self.height() - 18:
                self.start_move(event.globalPosition().toPoint())
                return True

        if event.type() == QEvent.Type.MouseMove:
            global_pos = event.globalPosition().toPoint()
            if self.resize_state:
                self.resize_window(global_pos)
                return True
            if self.drag_start:
                self.move_window(global_pos)
                return True
            local_pos = self.mapFromGlobal(global_pos)
            self.update_cursor(local_pos)

        if event.type() == QEvent.Type.MouseButtonRelease:
            if self.drag_start or self.resize_state:
                self.drag_start = None
                self.resize_state = None
                self.unsetCursor()
                self.save_current_progress()
                return True
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self.edge_at(event.position().toPoint())
            if edge:
                self.start_resize(event.globalPosition().toPoint(), edge)
            elif event.position().y() <= self.TITLE_DRAG_HEIGHT:
                self.start_move(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resize_state:
            self.resize_window(event.globalPosition().toPoint())
        elif self.drag_start:
            self.move_window(event.globalPosition().toPoint())
        else:
            self.update_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start = None
        self.resize_state = None
        self.unsetCursor()
        self.save_current_progress()
        super().mouseReleaseEvent(event)

    def edge_at(self, pos):
        margin = self.RESIZE_MARGIN
        left = pos.x() <= margin
        right = pos.x() >= self.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= self.height() - margin
        if top and left:
            return "top_left"
        if top and right:
            return "top_right"
        if bottom and left:
            return "bottom_left"
        if bottom and right:
            return "bottom_right"
        if left:
            return "left"
        if right:
            return "right"
        if top:
            return "top"
        if bottom:
            return "bottom"
        return ""

    def update_cursor(self, pos):
        edge = self.edge_at(pos)
        if edge in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif edge in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        else:
            self.unsetCursor()

    def start_move(self, global_pos):
        self.drag_start = (global_pos, self.frameGeometry().topLeft())

    def move_window(self, global_pos):
        if not self.drag_start:
            return
        start_pos, start_top_left = self.drag_start
        self.move(start_top_left + (global_pos - start_pos))

    def start_resize(self, global_pos, edge):
        self.resize_state = (global_pos, self.geometry(), edge)

    def resize_window(self, global_pos):
        if not self.resize_state:
            return
        start_pos, start_geometry, edge = self.resize_state
        delta = global_pos - start_pos
        geometry = start_geometry
        left, top, right, bottom = geometry.left(), geometry.top(), geometry.right(), geometry.bottom()
        if "left" in edge:
            left += delta.x()
        if "right" in edge:
            right += delta.x()
        if "top" in edge:
            top += delta.y()
        if "bottom" in edge:
            bottom += delta.y()

        min_width, min_height = self.minimumWidth(), self.minimumHeight()
        if right - left + 1 < min_width:
            if "left" in edge:
                left = right - min_width + 1
            else:
                right = left + min_width - 1
        if bottom - top + 1 < min_height:
            if "top" in edge:
                top = bottom - min_height + 1
            else:
                bottom = top + min_height - 1
        self.setGeometry(left, top, right - left + 1, bottom - top + 1)

    def show_welcome(self):
        hotkey = self.config["hotkeys"]["minimize"]
        self.reader.setPlainText(
            "打开 TXT 小说开始阅读。\n\n"
            "拖动文字区域可移动窗口，拖动任意边缘可缩放。\n"
            f"默认老板键: {hotkey}（Windows 下全局最小化）\n"
            "Ctrl+H: 显示/隐藏工具栏\n"
            "进度框输入 50.01 可跳到 50.01%\n"
            "右键: 打开菜单"
        )

    def choose_file(self):
        initial_dir = str(Path(self.current_file).parent) if self.current_file else str(APP_DIR)
        path, _ = QFileDialog.getOpenFileName(self, "选择小说 TXT", initial_dir, "Text files (*.txt);;All files (*.*)")
        if path:
            self.open_file(path, restore_progress=True)

    def open_file(self, path, restore_progress=False):
        try:
            content, encoding = read_text_file(path)
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(self, "打开失败", f"无法读取文件：\n{exc}")
            return

        self.save_current_progress()
        self.current_file = str(Path(path).resolve())
        self.current_encoding = encoding
        self.config["last_file"] = self.current_file
        self.reader.setPlainText(content)
        self.setWindowTitle(Path(path).name)

        if restore_progress:
            ratio = float(self.config.get("files", {}).get(self.current_file, {}).get("yview", 0.0))
            QTimer.singleShot(80, lambda: self.set_scroll_ratio(ratio))
        QTimer.singleShot(120, self.update_status)
        self.schedule_save()

    def set_scroll_ratio(self, ratio):
        scrollbar = self.reader.verticalScrollBar()
        scrollbar.setValue(round(scrollbar.maximum() * clamp(ratio, 0, 1)))

    def current_scroll_ratio(self):
        scrollbar = self.reader.verticalScrollBar()
        maximum = scrollbar.maximum()
        return 0.0 if maximum <= 0 else scrollbar.value() / maximum

    def jump_to_progress(self):
        raw = self.jump_entry.text().strip().replace("%", "")
        if not raw:
            return
        try:
            percent = float(raw)
        except ValueError:
            QMessageBox.warning(self, "进度无效", "请输入 0 到 100 之间的百分比，例如 50.01")
            return
        percent = clamp(percent, 0, 100)
        self.set_scroll_ratio(percent / 100)
        self.jump_entry.setText(f"{percent:.2f}")
        self.update_status()
        self.save_current_progress()

    def change_font_size(self, delta):
        self.config["font_size"] = int(clamp(int(self.config["font_size"]) + delta, 8, 72))
        self.apply_style()
        self.update_status()
        self.schedule_save()

    def change_background_opacity(self, delta):
        self.config["background_opacity"] = round(clamp(float(self.config["background_opacity"]) + delta, 0, 1), 2)
        self.apply_style()
        self.update_status()
        self.schedule_save()

    def change_text_opacity(self, delta):
        self.config["text_opacity"] = round(clamp(float(self.config["text_opacity"]) + delta, 0, 1), 2)
        self.apply_style()
        self.update_status()
        self.schedule_save()

    def toggle_toolbar(self):
        visible = self.toolbar.isVisible()
        self.apply_toolbar_visibility(not visible)
        self.config["toolbar_visible"] = not visible
        self.schedule_save()

    def apply_toolbar_visibility(self, visible):
        self.toolbar.setVisible(visible)
        self.status.setVisible(visible)
        self.restore_toolbar_button.setVisible(not visible)
        if not visible:
            self.restore_toolbar_button.raise_()
        else:
            self.update_toolbar_mode()

    def update_toolbar_mode(self):
        compact = self.width() < 430
        mode_changed = compact != self.compact_toolbar
        self.compact_toolbar = compact
        if mode_changed:
            for widget in (
                self.font_down_button,
                self.font_up_button,
                self.bg_down_button,
                self.bg_up_button,
                self.text_down_button,
                self.text_up_button,
                self.settings_button,
            ):
                widget.setVisible(not compact)
        self.more_button.setVisible(compact)
        self.progress_label.setVisible(self.width() >= 250)
        self.jump_entry.setVisible(self.width() >= 300)
        self.jump_button.setVisible(self.width() >= 300)
        self.hide_button.setVisible(self.width() >= 230)
        self.toolbar_layout.invalidate()

    def show_more_menu(self):
        menu = QMenu(self)
        menu.addAction("字号减小", lambda: self.change_font_size(-1))
        menu.addAction("字号增大", lambda: self.change_font_size(1))
        menu.addSeparator()
        menu.addAction("背景更透明", lambda: self.change_background_opacity(-0.05))
        menu.addAction("背景更实", lambda: self.change_background_opacity(0.05))
        menu.addAction("文字更透明", lambda: self.change_text_opacity(-0.05))
        menu.addAction("文字更实", lambda: self.change_text_opacity(0.05))
        menu.addSeparator()
        menu.addAction("设置", self.open_settings)
        menu.addAction("显示/隐藏工具栏", self.toggle_toolbar)
        menu.exec(self.more_button.mapToGlobal(QPoint(0, self.more_button.height())))

    def minimize_to_taskbar(self):
        self.save_current_progress()
        self.showMinimized()

    def apply_style(self):
        font = QFont(self.config["font_family"], int(self.config["font_size"]))
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.reader.setFont(font)

        background = qcolor_to_rgba(self.config["background"], float(self.config["background_opacity"]))
        foreground = qcolor_to_rgba(self.config["foreground"], float(self.config["text_opacity"]))
        solid_foreground = qcolor_to_hex(self.config["foreground"])

        self.shell.setStyleSheet(
            f"""
            QWidget#shell {{
                background-color: {background};
                border-radius: 6px;
            }}
            QTextEdit {{
                background: transparent;
                color: {foreground};
                border: 0;
                selection-background-color: rgba(80, 130, 160, 160);
                padding: 16px 20px;
            }}
            QLabel {{
                color: {solid_foreground};
                background: transparent;
            }}
            QToolButton {{
                color: {solid_foreground};
                background: rgba(255, 255, 255, 18);
                border: 0;
                border-radius: 4px;
                font-size: 11px;
            }}
            QToolButton:hover {{
                background: rgba(255, 255, 255, 42);
            }}
            QLineEdit {{
                color: {solid_foreground};
                background: rgba(255, 255, 255, 30);
                border: 0;
                border-radius: 4px;
                padding: 2px 4px;
            }}
            """
        )
        self.apply_window_flags()

    def apply_window_flags(self, force=False):
        flags = Qt.WindowType.FramelessWindowHint
        if self.config.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        current = self.windowFlags()
        current_top = bool(current & Qt.WindowType.WindowStaysOnTopHint)
        current_frameless = bool(current & Qt.WindowType.FramelessWindowHint)
        desired_top = bool(flags & Qt.WindowType.WindowStaysOnTopHint)
        desired_frameless = True
        if force or current_top != desired_top or current_frameless != desired_frameless:
            geometry = self.geometry()
            visible = self.isVisible()
            self.setWindowFlags(flags)
            self.setGeometry(geometry)
            if visible:
                self.show()

    def on_scroll(self):
        self.update_status()
        self.schedule_save()

    def update_status(self):
        percent = self.current_scroll_ratio() * 100
        self.progress_label.setText(f"{percent:.2f}%")
        if not self.current_file:
            return
        name = Path(self.current_file).name
        self.status.setText(
            f"{name} | {percent:.2f}% | {self.current_encoding} | 字号 {self.config['font_size']} | "
            f"背景 {self.config['background_opacity']:.2f} | 文字 {self.config['text_opacity']:.2f}"
        )

    def schedule_save(self):
        if hasattr(self, "save_timer"):
            self.save_timer.stop()
        else:
            self.save_timer = QTimer(self)
            self.save_timer.setSingleShot(True)
            self.save_timer.timeout.connect(self.save_current_progress)
        self.save_timer.start(600)

    def save_current_progress(self):
        if self.current_file:
            self.config.setdefault("files", {}).setdefault(self.current_file, {})["yview"] = self.current_scroll_ratio()
        geometry = self.geometry()
        self.config["geometry"] = f"{geometry.width()}x{geometry.height()}+{geometry.x()}+{geometry.y()}"
        try:
            save_config(self.config)
        except OSError:
            pass

    def rebind_hotkeys(self):
        for action in self.findChildren(QAction):
            if action.property("hotkey_action"):
                self.removeAction(action)

        mappings = {
            "open": self.choose_file,
            "hide_toolbar": self.toggle_toolbar,
            "settings": self.open_settings,
            "minimize": self.minimize_to_taskbar,
        }
        for name, callback in mappings.items():
            action = QAction(self)
            action.setProperty("hotkey_action", True)
            action.setShortcut(QKeySequence(self.config["hotkeys"].get(name, "")))
            action.triggered.connect(callback)
            self.addAction(action)

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        menu.addAction("打开 TXT", self.choose_file)
        menu.addAction("显示/隐藏工具栏", self.toggle_toolbar)
        menu.addAction("设置", self.open_settings)
        menu.addSeparator()
        menu.addAction("最小化", self.minimize_to_taskbar)
        menu.addAction("退出", self.close)
        menu.exec(global_pos)

    def open_settings(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        layout = QVBoxLayout(dialog)

        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("字体"))
        font_box = QFontComboBox()
        font_box.setCurrentFont(QFont(self.config["font_family"]))
        font_row.addWidget(font_box)
        layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("字号"))
        size_box = QSpinBox()
        size_box.setRange(8, 72)
        size_box.setValue(int(self.config["font_size"]))
        size_row.addWidget(size_box)
        layout.addLayout(size_row)

        fg_row = QHBoxLayout()
        fg_row.addWidget(QLabel("文字颜色"))
        fg_input = QLineEdit(self.config["foreground"])
        fg_button = QPushButton("选择")
        fg_button.clicked.connect(lambda: self.pick_color(fg_input))
        fg_row.addWidget(fg_input)
        fg_row.addWidget(fg_button)
        layout.addLayout(fg_row)

        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("背景颜色"))
        bg_input = QLineEdit(self.config["background"])
        bg_button = QPushButton("选择")
        bg_button.clicked.connect(lambda: self.pick_color(bg_input))
        bg_row.addWidget(bg_input)
        bg_row.addWidget(bg_button)
        layout.addLayout(bg_row)

        bg_opacity = self.opacity_row(layout, "背景透明度", float(self.config["background_opacity"]))
        text_opacity = self.opacity_row(layout, "文字透明度", float(self.config["text_opacity"]))

        always_top = QCheckBox("窗口置顶")
        always_top.setChecked(bool(self.config["always_on_top"]))
        layout.addWidget(always_top)

        wrap = QCheckBox("自动换行")
        wrap.setChecked(bool(self.config["wrap"]))
        layout.addWidget(wrap)

        hotkey_inputs = {}
        for label, name in (
            ("打开文件", "open"),
            ("显示/隐藏工具栏", "hide_toolbar"),
            ("打开设置", "settings"),
            ("一键最小化", "minimize"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            edit = QLineEdit(self.config["hotkeys"].get(name, ""))
            row.addWidget(edit)
            layout.addLayout(row)
            hotkey_inputs[name] = edit

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        cancel = QPushButton("取消")
        save = QPushButton("保存")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        action_row.addWidget(cancel)
        action_row.addWidget(save)
        layout.addLayout(action_row)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            normalized_hotkeys = {name: parse_hotkey(edit.text())[0] for name, edit in hotkey_inputs.items()}
        except ValueError as exc:
            QMessageBox.warning(self, "快捷键无效", str(exc))
            return

        self.config["font_family"] = font_box.currentFont().family()
        self.config["font_size"] = size_box.value()
        self.config["foreground"] = qcolor_to_hex(fg_input.text())
        self.config["background"] = qcolor_to_hex(bg_input.text())
        self.config["background_opacity"] = round(bg_opacity.value(), 2)
        self.config["text_opacity"] = round(text_opacity.value(), 2)
        self.config["always_on_top"] = always_top.isChecked()
        self.config["wrap"] = wrap.isChecked()
        self.config["hotkeys"].update(normalized_hotkeys)
        self.reader.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth if self.config["wrap"] else QTextEdit.LineWrapMode.NoWrap)
        self.apply_style()
        self.rebind_hotkeys()
        self.register_global_minimize_hotkey()
        self.save_current_progress()

    def opacity_row(self, layout, label, value):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(round(value * 100))
        spin = QDoubleSpinBox()
        spin.setRange(0, 1)
        spin.setDecimals(2)
        spin.setSingleStep(0.05)
        spin.setValue(value)
        slider.valueChanged.connect(lambda number: spin.setValue(number / 100))
        spin.valueChanged.connect(lambda number: slider.setValue(round(number * 100)))
        row.addWidget(slider, 1)
        row.addWidget(spin)
        layout.addLayout(row)
        return spin

    def pick_color(self, target):
        color = QColorDialog.getColor(QColor(target.text()), self)
        if color.isValid():
            target.setText(color.name())

    def register_global_minimize_hotkey(self):
        self.unregister_global_minimize_hotkey()
        if not self.is_windows:
            return
        try:
            normalized, modifiers, key = parse_hotkey(self.config["hotkeys"].get("minimize", "Ctrl+Alt+M"))
        except ValueError:
            return
        modifier_flags = 0
        if "Alt" in modifiers:
            modifier_flags |= self.MOD_ALT
        if "Ctrl" in modifiers:
            modifier_flags |= self.MOD_CONTROL
        if "Shift" in modifiers:
            modifier_flags |= self.MOD_SHIFT
        if "Win" in modifiers:
            modifier_flags |= self.MOD_WIN
        result = ctypes.windll.user32.RegisterHotKey(None, self.HOTKEY_ID_MINIMIZE, modifier_flags, VK_CODES[key])
        self.global_hotkey_registered = bool(result)
        if not result:
            self.status.setText(f"全局快捷键 {normalized} 注册失败，可能已被其他程序占用")

    def unregister_global_minimize_hotkey(self):
        if self.is_windows and self.global_hotkey_registered:
            ctypes.windll.user32.UnregisterHotKey(None, self.HOTKEY_ID_MINIMIZE)
        self.global_hotkey_registered = False

    def start_hotkey_timer(self):
        self.hotkey_timer = QTimer(self)
        self.hotkey_timer.timeout.connect(self.poll_global_hotkeys)
        self.hotkey_timer.start(100)

    def poll_global_hotkeys(self):
        if not self.is_windows:
            return
        msg = MSG()
        while ctypes.windll.user32.PeekMessageW(
            ctypes.byref(msg),
            None,
            self.WM_HOTKEY,
            self.WM_HOTKEY,
            self.PM_REMOVE,
        ):
            if msg.wParam == self.HOTKEY_ID_MINIMIZE:
                self.minimize_to_taskbar()

    def closeEvent(self, event):
        self.save_current_progress()
        self.unregister_global_minimize_hotkey()
        super().closeEvent(event)


def main():
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    reader = NovelReader()
    reader.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
