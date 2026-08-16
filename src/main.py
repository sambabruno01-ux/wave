import sys
import os
import ctypes
from ctypes import wintypes
import getpass
import json
import threading
import time
import re
import winsound
import asyncio
import websockets
import sounddevice as sd
import numpy as np

try:
    myappid = 'yunscryy.wave.voiceclient.7.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QPoint, QObject
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QFrame, QStackedWidget, QTextBrowser, QTextEdit, QGridLayout,
    QSystemTrayIcon, QMenu, QLabel, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QIcon, QKeyEvent, QFontMetrics, QColor, QMouseEvent, QWheelEvent, QPainter, QPen, QDesktopServices

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition,
    FluentIcon, SubtitleLabel, TitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    LineEdit, PasswordLineEdit, PrimaryPushButton, PushButton,
    SwitchButton, Slider, ComboBox, InfoBar,
    InfoBarPosition, setTheme, Theme, setThemeColor,
    PillPushButton, SimpleCardWidget, ScrollArea, IconWidget,
    PrimaryToolButton
)

from core.db_config import RELAY_SERVER_URL

# ==========================================================
# ПУТИ К ДАННЫМ И РЕСУРСАМ (AppData / Frozen Check)
# ==========================================================
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

APPDATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Wave")
os.makedirs(APPDATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(APPDATA_DIR, "settings.json")
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
ICON_PATH_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PATH_PNG = os.path.join(ASSETS_DIR, "icon.png")

SAMPLE_RATE = 16000
BLOCK_SIZE = 640

EQ_PRESETS = {
    "Стандартный (Flat)": (1.0, 1.0, 1.0),
    "Голосовой баланс (Discord Crisp)": (0.85, 1.25, 1.15),
    "Теплый радио-голос (Warm Broadcast)": (1.25, 1.10, 0.85),
    "Игровой фокус (Gamer Clarity)": (0.75, 1.30, 1.25),
    "Бас-буст (Deep Bass)": (1.40, 0.95, 0.85)
}

OVERLAY_MODES = [
    "Без своей панели",
    "Со своей панелью",
    "С отдельными панелями Мик/Звук"
]

OVERLAY_ICONS_MODES = [
    "Скрыть иконки статуса",
    "Только микрофон",
    "Микрофон + Звук"
]

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
WM_USER = 0x0400
WM_UPDATE_HOTKEYS = WM_USER + 1
WM_QUIT_HOTKEYS = WM_USER + 2

VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "SPACE": 0x20, "TAB": 0x09, "ESC": 0x1B, "ESCAPE": 0x1B,
    "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22, "UP": 0x26, "DOWN": 0x28,
    "LEFT": 0x25, "RIGHT": 0x27, "RETURN": 0x0D, "ENTER": 0x0D,
    "BACKSPACE": 0x08, "CAPSLOCK": 0x14, "PRINTSCREEN": 0x2C, "PAUSE": 0x13
}

def parse_hotkey_string(combo_str):
    if not combo_str or not combo_str.strip():
        return None, None
    parts = [p.strip().upper() for p in combo_str.split("+") if p.strip()]
    if not parts:
        return None, None
    
    mod = MOD_NOREPEAT
    key_code = None
    
    for part in parts:
        if part in ("CTRL", "CONTROL"):
            mod |= MOD_CONTROL
        elif part == "ALT":
            mod |= MOD_ALT
        elif part == "SHIFT":
            mod |= MOD_SHIFT
        elif part in ("WIN", "META"):
            mod |= MOD_WIN
        else:
            if part in VK_MAP:
                key_code = VK_MAP[part]
            elif len(part) == 1:
                vk = user32.VkKeyScanW(ord(part))
                if vk != -1:
                    key_code = vk & 0xFF
                else:
                    key_code = ord(part)
            else:
                key_code = ord(part[0])
    
    return mod, key_code

class GlobalHotkeyManager(QObject):
    hotkey_triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.thread_id = None
        self.lock = threading.Lock()
        self.current_hotkeys = {}
        self.running = True
        self.thread = threading.Thread(target=self._msg_loop, daemon=True)
        self.thread.start()

    def set_hotkeys(self, hotkeys_dict):
        with self.lock:
            self.current_hotkeys.clear()
            hid = 1
            for action, combo in hotkeys_dict.items():
                mod, vk = parse_hotkey_string(combo)
                if mod is not None and vk is not None:
                    self.current_hotkeys[hid] = (action, mod, vk)
                    hid += 1
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_UPDATE_HOTKEYS, 0, 0)

    def _msg_loop(self):
        self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        registered_ids = []

        def _unregister_all():
            nonlocal registered_ids
            for hid in registered_ids:
                user32.UnregisterHotKey(None, hid)
            registered_ids = []

        def _register_current():
            nonlocal registered_ids
            _unregister_all()
            with self.lock:
                for hid, (action, mod, vk) in self.current_hotkeys.items():
                    res = user32.RegisterHotKey(None, hid, mod, vk)
                    if res:
                        registered_ids.append(hid)

        _register_current()

        msg = wintypes.MSG()
        while self.running:
            bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if bRet == 0 or bRet == -1:
                break
            
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                action_to_trigger = None
                with self.lock:
                    if hid in self.current_hotkeys:
                        action_to_trigger = self.current_hotkeys[hid][0]
                if action_to_trigger:
                    self.hotkey_triggered.emit(action_to_trigger)
            elif msg.message == WM_UPDATE_HOTKEYS:
                _register_current()
            elif msg.message == WM_QUIT_HOTKEYS:
                break
            
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        _unregister_all()

    def stop(self):
        self.running = False
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT_HOTKEYS, 0, 0)

def get_windows_accent_color():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
        accent, _ = winreg.QueryValueEx(key, "AccentColor")
        winreg.CloseKey(key)
        r = accent & 0xFF
        g = (accent >> 8) & 0xFF
        b = (accent >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "#0078D4"

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 120, 212)

def get_windows_user():
    try:
        u = os.environ.get("USERNAME") or os.environ.get("USER") or getpass.getuser()
        if u and u.strip():
            return u.strip()
    except Exception:
        pass
    return "User"

def load_config():
    cfg = {
        "user_name": get_windows_user(),
        "mic_device": None,
        "speaker_device": None,
        "mic_boost": 1.0,
        "vad_threshold": 0.0,
        "echo_cancellation": False,
        "noise_suppression": False,
        "auto_gain_control": False,
        "equalizer_preset": "Стандартный (Flat)",
        "overlay_enabled": False,
        "overlay_mode": "Без своей панели",
        "overlay_icons_mode": "Только микрофон",
        "overlay_x_pct": 3.0,
        "overlay_y_pct": 3.0,
        "overlay_scale": 100,
        "theme": "Dark",
        "theme_color": None,
        "bind_mute_mic": "Ctrl+M",
        "bind_deafen": "Ctrl+D",
        "bind_tray": "Ctrl+H",
        "bind_overlay": "Ctrl+O"
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded.get("user_name"):
                    cfg["user_name"] = loaded["user_name"]
                for k, v in loaded.items():
                    if k != "user_name" or v is not None:
                        cfg[k] = v
        except Exception:
            pass
    if not cfg.get("user_name"):
        cfg["user_name"] = get_windows_user()
        
    if "overlay_x" in cfg and "overlay_x_pct" not in cfg:
        cfg["overlay_x_pct"] = min(100.0, max(0.0, (cfg["overlay_x"] / 1920.0) * 100.0))
    if "overlay_y" in cfg and "overlay_y_pct" not in cfg:
        cfg["overlay_y_pct"] = min(100.0, max(0.0, (cfg["overlay_y"] / 1080.0) * 100.0))

    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def get_audio_devices():
    inputs = []
    outputs = []
    try:
        devices = sd.query_devices()
        seen_in = set()
        seen_out = set()
        for i, d in enumerate(devices):
            name = d.get("name", f"Device {i}")
            if d.get("max_input_channels", 0) > 0 and name not in seen_in:
                seen_in.add(name)
                inputs.append({"index": i, "name": name})
            if d.get("max_output_channels", 0) > 0 and name not in seen_out:
                seen_out.add(name)
                outputs.append({"index": i, "name": name})
    except Exception:
        pass
    if not inputs: inputs = [{"index": None, "name": "Микрофон по умолчанию"}]
    if not outputs: outputs = [{"index": None, "name": "Динамики по умолчанию"}]
    return inputs, outputs

def apply_equalizer_filter(audio_array, preset_name):
    g_low, g_mid, g_high = EQ_PRESETS.get(preset_name, (1.0, 1.0, 1.0))
    if (g_low, g_mid, g_high) == (1.0, 1.0, 1.0):
        return audio_array
    
    out = audio_array.copy()
    if g_low != 1.0:
        low = np.convolve(audio_array, np.ones(5)/5.0, mode='same')
        out += (g_low - 1.0) * low
    if g_high != 1.0:
        high = audio_array - np.convolve(audio_array, np.ones(3)/3.0, mode='same')
        out += (g_high - 1.0) * high
    if g_mid != 1.0:
        out *= g_mid
        
    return np.clip(out, -1.0, 1.0)

class StatusIconWidget(QWidget):
    def __init__(self, icon, parent=None, is_slashed=False, slash_color="#FFFFFF"):
        super().__init__(parent)
        self.is_slashed = is_slashed
        self.slash_color = slash_color
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.icon_widget = IconWidget(icon, self)
        self.layout.addWidget(self.icon_widget)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def setFixedSize(self, w, h):
        super().setFixedSize(w, h)
        self.icon_widget.setFixedSize(w, h)

    def set_slashed(self, slashed):
        if self.is_slashed != slashed:
            self.is_slashed = slashed
            self.update()

    def setIcon(self, icon):
        self.icon_widget.setIcon(icon)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.is_slashed:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(self.slash_color), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            w = self.width()
            h = self.height()
            painter.drawLine(3, 3, w - 3, h - 3)

class DraggableVolumeIcon(IconWidget):
    volume_changed = pyqtSignal(float)

    def __init__(self, icon, parent=None, initial_vol=1.0):
        super().__init__(icon, parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self.current_vol = initial_vol
        self.dragging = False
        self.last_y = 0

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_y = event.globalPosition().y()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            cur_y = event.globalPosition().y()
            delta = self.last_y - cur_y
            self.last_y = cur_y
            step = delta * 0.015
            self.current_vol = max(0.0, min(2.0, self.current_vol + step))
            self.volume_changed.emit(self.current_vol)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        step = 0.05 if delta > 0 else -0.05
        self.current_vol = max(0.0, min(2.0, self.current_vol + step))
        self.volume_changed.emit(self.current_vol)
        event.accept()

class KeyRecorderEdit(LineEdit):
    keySequenceRecorded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Кликните и нажмите комбинацию...")

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        modifiers = event.modifiers()
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")

        key_text = QKeySequence(key).toString()
        if key_text:
            parts.append(key_text)

        if parts:
            combo = "+".join(parts)
            self.setText(combo)
            self.keySequenceRecorded.emit(combo)
        event.accept()

class VoiceOverlay(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(4)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)

        self.controls_container = QWidget(self)
        self.controls_container_layout = QHBoxLayout(self.controls_container)
        self.controls_container_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_container_layout.setSpacing(6)

        self.mic_card = QFrame(self.controls_container)
        self.mic_card.setObjectName("OverlayControlCardMic")
        self.mic_card.setProperty("class", "OverlayControlPill")
        mic_c_layout = QHBoxLayout(self.mic_card)
        mic_c_layout.setContentsMargins(10, 4, 10, 4)
        mic_c_layout.setSpacing(6)
        mic_c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.mic_icon = StatusIconWidget(FluentIcon.MICROPHONE, self.mic_card, slash_color="#FFFFFF")
        self.mic_lbl = QLabel("ВКЛ", self.mic_card)
        self.mic_lbl.setObjectName("ControlStatusLabel")
        mic_c_layout.addWidget(self.mic_icon)
        mic_c_layout.addWidget(self.mic_lbl)

        self.spk_card = QFrame(self.controls_container)
        self.spk_card.setObjectName("OverlayControlCardSpk")
        self.spk_card.setProperty("class", "OverlayControlPill")
        spk_c_layout = QHBoxLayout(self.spk_card)
        spk_c_layout.setContentsMargins(10, 4, 10, 4)
        spk_c_layout.setSpacing(6)
        spk_c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spk_icon = StatusIconWidget(FluentIcon.HEADPHONE, self.spk_card, slash_color="#FFFFFF")
        self.spk_lbl = QLabel("ВКЛ", self.spk_card)
        self.spk_lbl.setObjectName("ControlStatusLabel")
        spk_c_layout.addWidget(self.spk_icon)
        spk_c_layout.addWidget(self.spk_lbl)

        self.controls_container_layout.addWidget(self.mic_card)
        self.controls_container_layout.addWidget(self.spk_card)

        self.cards = {}
        self.raw_user_names = {}
        self.last_users_dict = {}

        self.base_card_width = 250
        self.base_card_height = 40
        self.base_font_size = 13

        self.apply_scale_and_styles()
        self.rebuild_layout_order()
        self.recalculate_position()

    def is_bottom_half(self):
        y_pct = float(self.main_window.cfg.get("overlay_y_pct", 3.0))
        return y_pct >= 50.0

    def rebuild_layout_order(self):
        while self.root_layout.count() > 0:
            self.root_layout.takeAt(0)

        overlay_mode = self.main_window.cfg.get("overlay_mode", "Без своей панели")
        show_bottom_controls = (overlay_mode == "С отдельными панелями Мик/Звук")
        self.controls_container.setVisible(show_bottom_controls)

        if self.is_bottom_half():
            if show_bottom_controls:
                self.root_layout.addWidget(self.controls_container)
            self.root_layout.addLayout(self.cards_layout)
        else:
            self.root_layout.addLayout(self.cards_layout)
            if show_bottom_controls:
                self.root_layout.addWidget(self.controls_container)

    def apply_scale_and_styles(self):
        scale = float(self.main_window.cfg.get("overlay_scale", 100)) / 100.0
        self.cur_width = int(self.base_card_width * scale)
        self.cur_height = int(self.base_card_height * scale)
        self.cur_font_size = max(10, int(self.base_font_size * scale))
        self.cur_dot_size = max(8, int(10 * scale))
        self.cur_icon_size = max(12, int(15 * scale))

        self.setFixedWidth(self.cur_width)
        self.controls_container.setFixedWidth(self.cur_width)
        ctrl_h = max(28, int(34 * scale))
        self.mic_card.setFixedHeight(ctrl_h)
        self.spk_card.setFixedHeight(ctrl_h)

        self.setStyleSheet(f"""
            QFrame.OverlayUserCard {{
                background-color: rgba(26, 26, 26, 0.86);
                border: 1.5px solid rgba(255, 255, 255, 0.12);
                border-radius: 9px;
            }}
            QFrame.OverlayControlPill {{
                background-color: rgba(22, 22, 22, 0.86);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui;
                font-size: {self.cur_font_size}px;
            }}
            QLabel#ControlStatusLabel {{
                color: #FFFFFF !important;
                font-weight: 700;
                font-size: {max(10, self.cur_font_size - 1)}px;
            }}
            QLabel.PingLabel {{
                font-size: {max(9, self.cur_font_size - 1)}px;
                font-weight: 700;
            }}
            QLabel.NameLabel {{
                font-weight: 750;
                color: #FFFFFF;
                font-size: {self.cur_font_size}px;
            }}
        """)

        self.mic_icon.setFixedSize(self.cur_icon_size, self.cur_icon_size)
        self.spk_icon.setFixedSize(self.cur_icon_size, self.cur_icon_size)

        self.update_controls_status()
        if self.last_users_dict:
            self.update_users(self.last_users_dict)

    def update_users(self, users_dict):
        self.last_users_dict = users_dict
        
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        self.raw_user_names.clear()

        overlay_mode = self.main_window.cfg.get("overlay_mode", "Без своей панели")
        icons_mode = self.main_window.cfg.get("overlay_icons_mode", "Только микрофон")
        include_self = (overlay_mode == "Со своей панелью")

        users_items = list(users_dict.items())
        if self.is_bottom_half():
            users_items = list(reversed(users_items))

        for user, udata in users_items:
            is_me = (user == self.main_window.state["user"])
            if is_me and not include_self:
                continue
            
            card = QFrame(self)
            card.setProperty("class", "OverlayUserCard")
            card.setFixedWidth(self.cur_width)
            card.setFixedHeight(self.cur_height)

            r_layout = QHBoxLayout(card)
            r_layout.setContentsMargins(12, 4, 12, 4)
            r_layout.setSpacing(6)

            full_name = f"{user} (Вы)" if is_me else user
            self.raw_user_names[user] = full_name

            name_lbl = QLabel(full_name, card)
            name_lbl.setProperty("class", "NameLabel")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            r_layout.addWidget(name_lbl, 1)

            ping_val = udata.get("ping", 0) if isinstance(udata, dict) else 0
            p_color = "#4CAF50" if ping_val < 90 else ("#FFA000" if ping_val < 180 else "#F44336")
            p_txt = f"{ping_val}ms" if ping_val > 0 else "--ms"

            ping_lbl = QLabel(p_txt, card)
            ping_lbl.setProperty("class", "PingLabel")
            ping_lbl.setStyleSheet(f"color: {p_color};")
            ping_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            r_layout.addWidget(ping_lbl)

            dot = QLabel("●", card)
            dot.setFixedSize(self.cur_dot_size + 4, self.cur_dot_size + 4)
            dot.setStyleSheet(f"color: {p_color}; font-size: {self.cur_dot_size}px;")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            r_layout.addWidget(dot)

            mic_icon = None
            spk_icon = None
            mic_muted = self.main_window.state["mic_muted"] if is_me else udata.get("mic_muted", False)
            deafened = self.main_window.state["deafened"] if is_me else udata.get("deafened", False)

            if icons_mode in ("Только микрофон", "Микрофон + Звук"):
                mic_icon = StatusIconWidget(FluentIcon.MICROPHONE, card, is_slashed=mic_muted, slash_color="#FFFFFF")
                mic_icon.setFixedSize(14, 14)
                r_layout.addWidget(mic_icon)

            if icons_mode == "Микрофон + Звук":
                spk_icon = StatusIconWidget(FluentIcon.HEADPHONE, card, is_slashed=deafened, slash_color="#FFFFFF")
                spk_icon.setFixedSize(14, 14)
                r_layout.addWidget(spk_icon)

            self.cards[user] = (card, dot, ping_lbl, name_lbl, mic_icon, spk_icon)
            self.cards_layout.addWidget(card)

        self.adjustSize()
        self.recalculate_position()

    def set_user_glow_smooth(self, user, alpha, rgb_tuple):
        if user in self.cards:
            card = self.cards[user][0]
            r, g, b = rgb_tuple
            
            if alpha > 0.01:
                b_r = int(255 * (1.0 - alpha) + r * alpha)
                b_g = int(255 * (1.0 - alpha) + g * alpha)
                b_b = int(255 * (1.0 - alpha) + b * alpha)
                border_a = 0.12 * (1.0 - alpha) + 1.0 * alpha
                border_width = 1.5 + (0.5 * alpha)
                card.setStyleSheet(f"""
                    QFrame.OverlayUserCard {{
                        background-color: rgba(26, 26, 26, 0.86);
                        border: {border_width:.1f}px solid rgba({b_r}, {b_g}, {b_b}, {border_a:.2f});
                        border-radius: 9px;
                    }}
                """)
            else:
                card.setStyleSheet("""
                    QFrame.OverlayUserCard {{
                        background-color: rgba(26, 26, 26, 0.86);
                        border: 1.5px solid rgba(255, 255, 255, 0.12);
                        border-radius: 9px;
                    }}
                """)

    def update_ping(self, user, ping_ms):
        if user in self.cards:
            _, dot, ping_lbl, _, _, _ = self.cards[user]
            p_color = "#4CAF50" if ping_ms < 90 else ("#FFA000" if ping_ms < 180 else "#F44336")
            dot.setStyleSheet(f"color: {p_color}; font-size: {self.cur_dot_size}px;")
            ping_lbl.setStyleSheet(f"color: {p_color};")
            ping_lbl.setText(f"{ping_ms}ms")

    def update_controls_status(self):
        mic_off = self.main_window.state.get("mic_muted", False)
        deaf_on = self.main_window.state.get("deafened", False)

        self.mic_lbl.setText("ВЫКЛ" if mic_off else "ВКЛ")
        self.mic_icon.set_slashed(mic_off)

        self.spk_lbl.setText("ВЫКЛ" if deaf_on else "ВКЛ")
        self.spk_icon.set_slashed(deaf_on)

        if self.last_users_dict:
            self.update_users(self.last_users_dict)

    def recalculate_position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()

        x_pct = float(self.main_window.cfg.get("overlay_x_pct", 3.0))
        y_pct = float(self.main_window.cfg.get("overlay_y_pct", 3.0))

        abs_x = int((geo.width() * x_pct) / 100.0)
        abs_y = int((geo.height() * y_pct) / 100.0)

        w = self.width()
        h = self.height()

        if self.is_bottom_half():
            target_y = abs_y - h
            if target_y < 10:
                target_y = 10
            self.move(abs_x, target_y)
        else:
            if abs_y + h > geo.height() - 10:
                abs_y = geo.height() - h - 10
            self.move(abs_x, abs_y)

class RoomInterface(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("RoomInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(12)
        
        self.user_cards = {}
        self.user_ping_labels = {}
        self.user_state_icons = {}
        self.known_users = set()

        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        self.init_auth_view()
        self.init_room_view()
        self.stack.setCurrentIndex(0)

    def init_auth_view(self):
        self.auth_page = QWidget()
        layout = QVBoxLayout(self.auth_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = TitleLabel("Wave Voice", self.auth_page)
        layout.addWidget(title)

        card = SimpleCardWidget(self.auth_page)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        header = BodyLabel("Подключение к голосовому каналу", card)
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        card_layout.addWidget(header)

        self.name_input = LineEdit(card)
        self.name_input.setPlaceholderText("Ваш никнейм")
        self.name_input.setText(self.main_window.state["user"])
        card_layout.addWidget(self.name_input)

        self.room_input = LineEdit(card)
        self.room_input.setPlaceholderText("ID Комнаты (например: squad)")
        self.room_input.textChanged.connect(self.check_room_status)
        card_layout.addWidget(self.room_input)

        self.status_lbl = CaptionLabel("Введите название комнаты для проверки", card)
        card_layout.addWidget(self.status_lbl)

        self.pwd_input = PasswordLineEdit(card)
        self.pwd_input.setPlaceholderText("Пароль комнаты")
        card_layout.addWidget(self.pwd_input)

        self.action_btn = PrimaryPushButton("Создать / Войти", card)
        self.action_btn.setIcon(FluentIcon.MESSAGE)
        self.action_btn.clicked.connect(self.join_or_create_room)
        card_layout.addWidget(self.action_btn)

        layout.addWidget(card)
        layout.addStretch()
        self.stack.addWidget(self.auth_page)

    def init_room_view(self):
        self.room_page = QWidget()
        layout = QVBoxLayout(self.room_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        self.room_heading = SubtitleLabel("Лобби", self.room_page)

        leave_btn = PushButton("Выйти", self.room_page)
        leave_btn.setIcon(FluentIcon.POWER_BUTTON)
        leave_btn.clicked.connect(self.leave_room)

        top_row.addWidget(self.room_heading)
        top_row.addStretch()
        top_row.addWidget(leave_btn)
        layout.addLayout(top_row)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)
        columns_layout.setContentsMargins(0, 0, 0, 0)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.users_scroll = ScrollArea(left_col)
        self.users_scroll.setWidgetResizable(True)
        self.users_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.users_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self.users_content = QWidget()
        self.users_content.setStyleSheet("background: transparent;")
        self.users_layout = QVBoxLayout(self.users_content)
        self.users_layout.setContentsMargins(0, 0, 0, 0)
        self.users_layout.setSpacing(8)
        self.users_layout.addStretch()
        
        self.users_scroll.setWidget(self.users_content)
        left_layout.addWidget(self.users_scroll)

        right_col = SimpleCardWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        self.chat_view = QTextBrowser(right_col)
        self.chat_view.setOpenExternalLinks(True)
        self.chat_view.setFont(QFont("Segoe UI", 10))
        self.chat_view.setStyleSheet(
            "QTextBrowser { background-color: rgba(255, 255, 255, 0.03); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 8px; }"
        )
        right_layout.addWidget(self.chat_view)

        chat_input_row = QHBoxLayout()
        chat_input_row.setSpacing(6)
        self.chat_input = LineEdit(right_col)
        self.chat_input.setPlaceholderText("Написать сообщение...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        
        send_btn = PrimaryToolButton(FluentIcon.SEND, right_col)
        send_btn.setFixedSize(36, 32)
        send_btn.clicked.connect(self.send_chat_message)

        chat_input_row.addWidget(self.chat_input)
        chat_input_row.addWidget(send_btn)
        right_layout.addLayout(chat_input_row)

        columns_layout.addWidget(left_col, 5)
        columns_layout.addWidget(right_col, 5)
        layout.addLayout(columns_layout)

        action_card = SimpleCardWidget(self.room_page)
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(16, 12, 16, 12)
        action_layout.setSpacing(12)

        self.mute_btn = PillPushButton("ВКЛ", action_card)
        self.mute_btn.setIcon(FluentIcon.MICROPHONE)
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self.toggle_mic)

        self.deaf_btn = PillPushButton("ВКЛ", action_card)
        self.deaf_btn.setIcon(FluentIcon.HEADPHONE)
        self.deaf_btn.setCheckable(True)
        self.deaf_btn.clicked.connect(self.toggle_deaf)

        self.self_listen_btn = PillPushButton("Слышать себя: ВЫКЛ", action_card)
        self.self_listen_btn.setIcon(FluentIcon.VOLUME)
        self.self_listen_btn.setCheckable(True)
        self.self_listen_btn.clicked.connect(self.toggle_self_listen)

        action_layout.addWidget(self.mute_btn)
        action_layout.addWidget(self.deaf_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.self_listen_btn)

        layout.addWidget(action_card)
        self.stack.addWidget(self.room_page)

    def check_room_status(self, text):
        r_id = text.strip()
        if len(r_id) < 3:
            self.status_lbl.setText("ID должен содержать от 3 символов")
            self.status_lbl.setStyleSheet("color: #888888;")
            return
        
        self.status_lbl.setText("Проверка...")
        self.main_window.send_json_msg({
            "type": "CHECK_ROOM",
            "room": r_id
        })

    def set_room_status_ui(self, exists):
        if exists:
            self.status_lbl.setText("Комната существует. Введите пароль:")
            self.status_lbl.setStyleSheet("color: #4CAF50;")
            self.action_btn.setText("Войти в комнату")
        else:
            self.status_lbl.setText("Комната свободна. Задайте пароль:")
            self.status_lbl.setStyleSheet("color: #888888;")
            self.action_btn.setText("Создать комнату")

    def join_or_create_room(self):
        name = self.name_input.text().strip()
        r_id = self.room_input.text().strip()
        pwd = self.pwd_input.text().strip()

        if not name or not r_id or not pwd:
            InfoBar.error(
                title="Ошибка ввода",
                content="Заполните все поля!",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        self.action_btn.setEnabled(False)
        self.action_btn.setText("Вход...")

        self.main_window.state["user"] = name
        self.main_window.state["room"] = r_id
        self.main_window.state["password"] = pwd
        
        self.main_window.send_json_msg({
            "type": "JOIN",
            "room": r_id,
            "user": name,
            "password": pwd,
            "mic_muted": self.main_window.state["mic_muted"],
            "deafened": self.main_window.state["deafened"],
            "self_listen": self.main_window.state["self_listen"]
        })

    def show_active_room(self):
        self.action_btn.setEnabled(True)
        self.action_btn.setText("Создать / Войти")
        self.room_heading.setText(f"Лобби: {self.main_window.state['room']}")
        self.chat_view.clear()
        self.known_users = {self.main_window.state["user"]}
        initial_users = {
            self.main_window.state["user"]: {
                "ping": 0,
                "status": "online",
                "mic_muted": self.main_window.state["mic_muted"],
                "deafened": self.main_window.state["deafened"]
            }
        }
        self.update_users_list(initial_users)
        self.main_window.overlay.update_users(initial_users)
        self.stack.setCurrentIndex(1)
        self.main_window.notify_event("user_joined")

    def toggle_mic(self):
        self.main_window.state["mic_muted"] = not self.main_window.state["mic_muted"]
        is_muted = self.main_window.state["mic_muted"]
        self.mute_btn.setChecked(is_muted)
        self.mute_btn.setText("ВЫКЛ" if is_muted else "ВКЛ")
        self.mute_btn.setIcon(FluentIcon.MICROPHONE)
        if is_muted:
            self.main_window.speaker_glow_levels[self.main_window.state["user"]] = 0.0
        
        self.main_window.send_json_msg({
            "type": "UPDATE_STATE",
            "mic_muted": is_muted
        })
        self.main_window.overlay.update_controls_status()
        self.update_user_state_icon(self.main_window.state["user"], is_muted, self.main_window.state["deafened"])

    def toggle_deaf(self):
        self.main_window.state["deafened"] = not self.main_window.state["deafened"]
        is_deaf = self.main_window.state["deafened"]
        self.deaf_btn.setChecked(is_deaf)
        self.deaf_btn.setText("ВЫКЛ" if is_deaf else "ВКЛ")
        
        self.main_window.send_json_msg({
            "type": "UPDATE_STATE",
            "deafened": is_deaf
        })
        self.main_window.overlay.update_controls_status()
        self.update_user_state_icon(self.main_window.state["user"], self.main_window.state["mic_muted"], is_deaf)

    def toggle_self_listen(self):
        self.main_window.state["self_listen"] = not self.main_window.state["self_listen"]
        is_on = self.main_window.state["self_listen"]
        self.self_listen_btn.setText("Слышать себя: ВКЛ" if is_on else "Слышать себя: ВЫКЛ")
        
        self.main_window.send_json_msg({
            "type": "UPDATE_STATE",
            "self_listen": is_on
        })

    def send_chat_message(self):
        txt = self.chat_input.text().strip()
        if not txt or not self.main_window.state["in_room"]:
            return
        
        self.chat_input.clear()
        self.main_window.send_json_msg({
            "type": "CHAT",
            "text": txt
        })

    def receive_chat_message(self, sender, text):
        t_str = time.strftime("%H:%M")
        is_me = (sender == self.main_window.state["user"])
        color = "#64B5F6" if is_me else "#81C784"
        formatted = f'<span style="color: #888888;">[{t_str}]</span> <b style="color: {color};">{sender}:</b> {text}'
        self.chat_view.append(formatted)

        if not is_me:
            self.main_window.notify_event("chat")

    def update_users_list(self, users_dict):
        current_users = set(users_dict.keys())
        new_comers = current_users - self.known_users
        left_users = self.known_users - current_users

        if new_comers and len(self.known_users) > 0:
            for new_u in new_comers:
                if new_u != self.main_window.state["user"]:
                    self.main_window.notify_event("user_joined")
                    self.main_window.log(f"[Room] Пользователь {new_u} вошел в комнату")

        if left_users and len(self.known_users) > 0:
            for left_u in left_users:
                if left_u != self.main_window.state["user"]:
                    self.main_window.notify_event("user_left")
                    self.main_window.log(f"[Room] Пользователь {left_u} покинул комнату")

        self.known_users = current_users

        while self.users_layout.count() > 1:
            item = self.users_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.user_cards.clear()
        self.user_ping_labels.clear()
        self.user_state_icons.clear()

        for u, udata in users_dict.items():
            is_me = (u == self.main_window.state["user"])
            user_card = SimpleCardWidget(self.users_content)
            user_card.setObjectName(f"user_card_{u}")
            user_card.setStyleSheet("SimpleCardWidget { border: 2px solid transparent; border-radius: 8px; background-color: transparent; }")
            
            uc_layout = QHBoxLayout(user_card)
            uc_layout.setContentsMargins(12, 8, 12, 8)
            uc_layout.setSpacing(8)

            ping_val = udata.get("ping", 0) if isinstance(udata, dict) else 0
            p_color = "#4CAF50" if ping_val < 90 else ("#FFA000" if ping_val < 180 else "#F44336")
            
            dot = CaptionLabel("●", user_card)
            dot.setStyleSheet(f"color: {p_color}; font-size: 13px;")
            uc_layout.addWidget(dot)

            p_txt = f"{ping_val}ms" if ping_val > 0 else (f"{self.main_window.current_ping}ms" if is_me and self.main_window.current_ping > 0 else "--ms")
            ping_lbl = CaptionLabel(p_txt, user_card)
            ping_lbl.setStyleSheet(f"color: {p_color}; font-weight: bold; font-size: 11px;")
            uc_layout.addWidget(ping_lbl)
            self.user_ping_labels[u] = (dot, ping_lbl)

            name_text = f"{u} (Вы)" if is_me else u
            name_lbl = StrongBodyLabel(name_text, user_card)
            uc_layout.addWidget(name_lbl)
            uc_layout.addStretch()

            if not is_me:
                if u not in self.main_window.peer_volumes:
                    self.main_window.peer_volumes[u] = 1.0

                current_vol = self.main_window.peer_volumes[u]
                vol_label = CaptionLabel(f"{int(current_vol * 100)}%", user_card)
                vol_label.setFixedWidth(38)
                vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                vol_icon = DraggableVolumeIcon(FluentIcon.VOLUME, user_card, current_vol)
                vol_icon.volume_changed.connect(lambda v, l=vol_label, usr=u: self.on_vol_change(usr, v, l))

                uc_layout.addWidget(vol_icon)
                uc_layout.addWidget(vol_label)

            u_mic_off = self.main_window.state["mic_muted"] if is_me else udata.get("mic_muted", False)
            u_deaf_on = self.main_window.state["deafened"] if is_me else udata.get("deafened", False)

            mic_status_icon = StatusIconWidget(FluentIcon.MICROPHONE, user_card, is_slashed=u_mic_off, slash_color="#FFFFFF")
            mic_status_icon.setFixedSize(16, 16)
            uc_layout.addWidget(mic_status_icon)

            spk_status_icon = StatusIconWidget(FluentIcon.HEADPHONE, user_card, is_slashed=u_deaf_on, slash_color="#FFFFFF")
            spk_status_icon.setFixedSize(16, 16)
            uc_layout.addWidget(spk_status_icon)

            self.user_state_icons[u] = (mic_status_icon, spk_status_icon)

            self.user_cards[u] = user_card
            self.users_layout.insertWidget(self.users_layout.count() - 1, user_card)

    def update_user_state_icon(self, user, mic_muted, deafened):
        if user in self.user_state_icons:
            mic_ico, spk_ico = self.user_state_icons[user]
            mic_ico.set_slashed(mic_muted)
            spk_ico.set_slashed(deafened)

    def set_speaker_glow_smooth(self, username, alpha, rgb_tuple):
        if username in self.user_cards:
            card = self.user_cards[username]
            r, g, b = rgb_tuple
            if alpha > 0.01:
                b_alpha = 0.95 * alpha
                card.setStyleSheet(f"""
                    SimpleCardWidget {{
                        border: 2px solid rgba({r}, {g}, {b}, {b_alpha:.2f});
                        border-radius: 8px;
                        background-color: transparent;
                    }}
                """)
            else:
                card.setStyleSheet("SimpleCardWidget { border: 2px solid transparent; border-radius: 8px; background-color: transparent; }")

    def update_user_ping_ui(self, user, ping_ms):
        if user in self.user_ping_labels:
            dot, lbl = self.user_ping_labels[user]
            color = "#4CAF50" if ping_ms < 90 else ("#FFA000" if ping_ms < 180 else "#F44336")
            dot.setStyleSheet(f"color: {color}; font-size: 13px;")
            lbl.setText(f"{ping_ms}ms")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def on_vol_change(self, user, val, label):
        label.setText(f"{int(val * 100)}%")
        self.main_window.peer_volumes[user] = float(val)

    def leave_room(self):
        self.main_window.notify_event("user_left")
        self.main_window.leave_and_cleanup()
        self.stack.setCurrentIndex(0)

class SettingsInterface(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("SettingsInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(16)
        
        self.save_debounce_timer = QTimer(self)
        self.save_debounce_timer.setSingleShot(True)
        self.save_debounce_timer.setInterval(1000)
        self.save_debounce_timer.timeout.connect(self.execute_save_settings)
        
        self.init_ui()

    def init_ui(self):
        self.title = SubtitleLabel("Настройки звука, эквалайзера и оверлея", self)
        self.layout.addWidget(self.title)

        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 10, 0)
        container_layout.setSpacing(16)

        card1 = SimpleCardWidget(container)
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(20, 18, 20, 18)
        c1_layout.setSpacing(12)

        c1_layout.addWidget(StrongBodyLabel("Устройства вывода и ввода:", card1))
        
        c1_layout.addWidget(BodyLabel("Микрофон:", card1))
        self.mic_combo = ComboBox(card1)
        self.mic_combo.currentTextChanged.connect(self.trigger_delayed_save)
        c1_layout.addWidget(self.mic_combo)

        c1_layout.addWidget(BodyLabel("Динамики:", card1))
        self.spk_combo = ComboBox(card1)
        self.spk_combo.currentTextChanged.connect(self.trigger_delayed_save)
        c1_layout.addWidget(self.spk_combo)

        c1_layout.addWidget(BodyLabel("Усиление микрофона:", card1))
        self.boost_label = CaptionLabel(f"{self.main_window.cfg.get('mic_boost', 1.0):.1f}x", card1)
        self.boost_slider = Slider(Qt.Orientation.Horizontal, card1)
        self.boost_slider.setRange(10, 50)
        self.boost_slider.setValue(int(self.main_window.cfg.get("mic_boost", 1.0) * 10))
        self.boost_slider.valueChanged.connect(self.on_boost_change)
        self.boost_slider.sliderReleased.connect(self.execute_save_settings)
        
        b_row = QHBoxLayout()
        b_row.addWidget(self.boost_slider)
        b_row.addWidget(self.boost_label)
        c1_layout.addLayout(b_row)

        c1_layout.addWidget(BodyLabel("Порог срабатывания микрофона (VAD Gate):", card1))
        self.vad_label = CaptionLabel(f"{int(self.main_window.cfg.get('vad_threshold', 0.0) * 1000)}", card1)
        self.vad_slider = Slider(Qt.Orientation.Horizontal, card1)
        self.vad_slider.setRange(0, 100)
        self.vad_slider.setValue(int(self.main_window.cfg.get("vad_threshold", 0.0) * 1000))
        self.vad_slider.valueChanged.connect(self.on_vad_change)
        self.vad_slider.sliderReleased.connect(self.execute_save_settings)

        v_row = QHBoxLayout()
        v_row.addWidget(self.vad_slider)
        v_row.addWidget(self.vad_label)
        c1_layout.addLayout(v_row)

        container_layout.addWidget(card1)

        card2 = SimpleCardWidget(container)
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(20, 18, 20, 18)
        c2_layout.setSpacing(12)

        c2_layout.addWidget(StrongBodyLabel("Улучшенная обработка звука:", card2))

        self.echo_switch = SwitchButton(card2)
        self.echo_switch.setOnText("Эхоподавление (Acoustic Echo Reduction): ВКЛ")
        self.echo_switch.setOffText("Эхоподавление: ВЫКЛ")
        self.echo_switch.setChecked(self.main_window.cfg.get("echo_cancellation", False))
        self.echo_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.echo_switch)

        self.noise_switch = SwitchButton(card2)
        self.noise_switch.setOnText("Шумоподавление (Noise Suppression): ВКЛ")
        self.noise_switch.setOffText("Шумоподавление: ВЫКЛ")
        self.noise_switch.setChecked(self.main_window.cfg.get("noise_suppression", False))
        self.noise_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.noise_switch)

        self.agc_switch = SwitchButton(card2)
        self.agc_switch.setOnText("Автоматическая регулировка усиления (Auto Gain Control): ВКЛ")
        self.agc_switch.setOffText("Автоматическая регулировка усиления: ВЫКЛ")
        self.agc_switch.setChecked(self.main_window.cfg.get("auto_gain_control", False))
        self.agc_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.agc_switch)

        container_layout.addWidget(card2)

        card3 = SimpleCardWidget(container)
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(20, 18, 20, 18)
        c3_layout.setSpacing(12)

        c3_layout.addWidget(StrongBodyLabel("Встроенный эквалайзер голоса:", card3))
        c3_layout.addWidget(CaptionLabel("Применяется к собеседникам и при проверке своего звука", card3))
        
        self.eq_combo = ComboBox(card3)
        for preset_name in EQ_PRESETS.keys():
            self.eq_combo.addItem(preset_name)
        current_eq = self.main_window.cfg.get("equalizer_preset", "Стандартный (Flat)")
        self.eq_combo.setCurrentText(current_eq)
        self.eq_combo.currentTextChanged.connect(self.trigger_delayed_save)
        c3_layout.addWidget(self.eq_combo)

        container_layout.addWidget(card3)

        card4 = SimpleCardWidget(container)
        c4_layout = QVBoxLayout(card4)
        c4_layout.setContentsMargins(20, 18, 20, 18)
        c4_layout.setSpacing(12)

        c4_layout.addWidget(StrongBodyLabel("Игровой оверлей участников:", card4))

        self.overlay_switch = SwitchButton(card4)
        self.overlay_switch.setOnText("Показывать оверлей поверх всех окон: ВКЛ")
        self.overlay_switch.setOffText("Оверлей: ВЫКЛ")
        self.overlay_switch.setChecked(self.main_window.cfg.get("overlay_enabled", False))
        self.overlay_switch.checkedChanged.connect(self.on_overlay_toggled)
        c4_layout.addWidget(self.overlay_switch)

        c4_layout.addWidget(BodyLabel("Режим отображения оверлея:", card4))
        self.overlay_mode_combo = ComboBox(card4)
        for mode in OVERLAY_MODES:
            self.overlay_mode_combo.addItem(mode)
        current_mode = self.main_window.cfg.get("overlay_mode", "Без своей панели")
        self.overlay_mode_combo.setCurrentText(current_mode)
        self.overlay_mode_combo.currentTextChanged.connect(self.on_overlay_mode_changed)
        c4_layout.addWidget(self.overlay_mode_combo)

        c4_layout.addWidget(BodyLabel("Иконки статуса в оверлее:", card4))
        self.overlay_icons_combo = ComboBox(card4)
        for imode in OVERLAY_ICONS_MODES:
            self.overlay_icons_combo.addItem(imode)
        current_imode = self.main_window.cfg.get("overlay_icons_mode", "Только микрофон")
        self.overlay_icons_combo.setCurrentText(current_imode)
        self.overlay_icons_combo.currentTextChanged.connect(self.on_overlay_icons_mode_changed)
        c4_layout.addWidget(self.overlay_icons_combo)

        self.overlay_pos_container = QWidget(card4)
        pos_layout = QGridLayout(self.overlay_pos_container)
        pos_layout.setContentsMargins(0, 4, 0, 0)
        pos_layout.setSpacing(10)
        
        pos_layout.addWidget(BodyLabel("Масштаб оверлея (%):"), 0, 0)
        self.scale_label = CaptionLabel(f"{self.main_window.cfg.get('overlay_scale', 100)}%", self.overlay_pos_container)
        self.overlay_scale_slider = Slider(Qt.Orientation.Horizontal, self.overlay_pos_container)
        self.overlay_scale_slider.setRange(60, 150)
        self.overlay_scale_slider.setValue(self.main_window.cfg.get("overlay_scale", 100))
        self.overlay_scale_slider.valueChanged.connect(self.on_scale_slider_changed)
        self.overlay_scale_slider.sliderReleased.connect(self.execute_save_settings)
        
        scale_h = QHBoxLayout()
        scale_h.addWidget(self.overlay_scale_slider)
        scale_h.addWidget(self.scale_label)
        pos_layout.addLayout(scale_h, 0, 1)

        pos_layout.addWidget(BodyLabel("Позиция X (% ширины экрана):"), 1, 0)
        self.overlay_x_slider = Slider(Qt.Orientation.Horizontal, self.overlay_pos_container)
        self.overlay_x_slider.setRange(0, 100)
        self.overlay_x_slider.setValue(int(self.main_window.cfg.get("overlay_x_pct", 3.0)))
        self.overlay_x_slider.valueChanged.connect(self.update_overlay_pos_live)
        self.overlay_x_slider.sliderReleased.connect(self.execute_save_settings)
        pos_layout.addWidget(self.overlay_x_slider, 1, 1)

        pos_layout.addWidget(BodyLabel("Позиция Y (% высоты экрана):"), 2, 0)
        self.overlay_y_slider = Slider(Qt.Orientation.Horizontal, self.overlay_pos_container)
        self.overlay_y_slider.setRange(0, 100)
        self.overlay_y_slider.setValue(int(self.main_window.cfg.get("overlay_y_pct", 3.0)))
        self.overlay_y_slider.valueChanged.connect(self.update_overlay_pos_live)
        self.overlay_y_slider.sliderReleased.connect(self.execute_save_settings)
        pos_layout.addWidget(self.overlay_y_slider, 2, 1)

        c4_layout.addWidget(self.overlay_pos_container)
        self.overlay_pos_container.setVisible(self.overlay_switch.isChecked())

        container_layout.addWidget(card4)

        card5 = SimpleCardWidget(container)
        c5_layout = QVBoxLayout(card5)
        c5_layout.setContentsMargins(20, 18, 20, 18)
        c5_layout.setSpacing(12)

        c5_layout.addWidget(StrongBodyLabel("Глобальные горячие клавиши (Работают везде):", card5))

        bind_grid = QGridLayout()
        bind_grid.addWidget(BodyLabel("Микрофон (Mute):"), 0, 0)
        self.mute_bind_input = KeyRecorderEdit(card5)
        self.mute_bind_input.setText(self.main_window.cfg.get("bind_mute_mic", "Ctrl+M"))
        self.mute_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.mute_bind_input, 0, 1)

        bind_grid.addWidget(BodyLabel("Звук (Deafen):"), 1, 0)
        self.deaf_bind_input = KeyRecorderEdit(card5)
        self.deaf_bind_input.setText(self.main_window.cfg.get("bind_deafen", "Ctrl+D"))
        self.deaf_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.deaf_bind_input, 1, 1)

        bind_grid.addWidget(BodyLabel("Свернуть в трей:"), 2, 0)
        self.tray_bind_input = KeyRecorderEdit(card5)
        self.tray_bind_input.setText(self.main_window.cfg.get("bind_tray", "Ctrl+H"))
        self.tray_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.tray_bind_input, 2, 1)

        bind_grid.addWidget(BodyLabel("Вкл/Выкл оверлей:"), 3, 0)
        self.overlay_bind_input = KeyRecorderEdit(card5)
        self.overlay_bind_input.setText(self.main_window.cfg.get("bind_overlay", "Ctrl+O"))
        self.overlay_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.overlay_bind_input, 3, 1)

        c5_layout.addLayout(bind_grid)
        container_layout.addWidget(card5)

        scroll.setWidget(container)
        self.layout.addWidget(scroll)
        self.refresh_devices()

    def on_boost_change(self, v):
        self.boost_label.setText(f"{v/10.0:.1f}x")
        self.main_window.cfg["mic_boost"] = v / 10.0
        self.trigger_delayed_save()

    def on_vad_change(self, v):
        self.vad_label.setText(f"{v}")
        self.main_window.cfg["vad_threshold"] = v / 1000.0
        self.trigger_delayed_save()

    def on_overlay_toggled(self, is_on):
        self.overlay_pos_container.setVisible(is_on)
        if is_on:
            self.main_window.overlay.show()
        else:
            self.main_window.overlay.hide()
        self.trigger_delayed_save()

    def on_overlay_mode_changed(self, mode):
        self.main_window.cfg["overlay_mode"] = mode
        self.main_window.overlay.rebuild_layout_order()
        self.main_window.overlay.apply_scale_and_styles()
        self.trigger_delayed_save()

    def on_overlay_icons_mode_changed(self, mode):
        self.main_window.cfg["overlay_icons_mode"] = mode
        self.main_window.overlay.rebuild_layout_order()
        self.main_window.overlay.apply_scale_and_styles()
        self.trigger_delayed_save()

    def on_scale_slider_changed(self, val):
        self.scale_label.setText(f"{val}%")
        self.main_window.cfg["overlay_scale"] = val
        self.main_window.overlay.apply_scale_and_styles()
        self.main_window.overlay.recalculate_position()
        self.trigger_delayed_save()

    def update_overlay_pos_live(self):
        self.main_window.cfg["overlay_x_pct"] = float(self.overlay_x_slider.value())
        self.main_window.cfg["overlay_y_pct"] = float(self.overlay_y_slider.value())
        self.main_window.overlay.rebuild_layout_order()
        self.main_window.overlay.apply_scale_and_styles()
        self.main_window.overlay.recalculate_position()
        self.trigger_delayed_save()

    def refresh_devices(self):
        in_devs, out_devs = get_audio_devices()
        self.main_window.in_devs = in_devs
        self.main_window.out_devs = out_devs

        self.mic_combo.blockSignals(True)
        self.spk_combo.blockSignals(True)

        self.mic_combo.clear()
        for d in in_devs:
            self.mic_combo.addItem(d["name"])
        
        self.spk_combo.clear()
        for d in out_devs:
            self.spk_combo.addItem(d["name"])

        if self.main_window.cfg.get("mic_device"):
            self.mic_combo.setCurrentText(self.main_window.cfg.get("mic_device"))
        if self.main_window.cfg.get("speaker_device"):
            self.spk_combo.setCurrentText(self.main_window.cfg.get("speaker_device"))

        self.mic_combo.blockSignals(False)
        self.spk_combo.blockSignals(False)

    def trigger_delayed_save(self):
        self.save_debounce_timer.start(1000)

    def execute_save_settings(self):
        if self.save_debounce_timer.isActive():
            self.save_debounce_timer.stop()

        self.main_window.cfg["mic_device"] = self.mic_combo.currentText()
        self.main_window.cfg["speaker_device"] = self.spk_combo.currentText()
        self.main_window.cfg["mic_boost"] = self.boost_slider.value() / 10.0
        self.main_window.cfg["vad_threshold"] = self.vad_slider.value() / 1000.0
        self.main_window.cfg["echo_cancellation"] = self.echo_switch.isChecked()
        self.main_window.cfg["noise_suppression"] = self.noise_switch.isChecked()
        self.main_window.cfg["auto_gain_control"] = self.agc_switch.isChecked()
        self.main_window.cfg["equalizer_preset"] = self.eq_combo.currentText()
        
        self.main_window.cfg["overlay_enabled"] = self.overlay_switch.isChecked()
        self.main_window.cfg["overlay_mode"] = self.overlay_mode_combo.currentText()
        self.main_window.cfg["overlay_icons_mode"] = self.overlay_icons_combo.currentText()
        self.main_window.cfg["overlay_scale"] = self.overlay_scale_slider.value()
        self.main_window.cfg["overlay_x_pct"] = float(self.overlay_x_slider.value())
        self.main_window.cfg["overlay_y_pct"] = float(self.overlay_y_slider.value())

        self.main_window.cfg["bind_mute_mic"] = self.mute_bind_input.text().strip() or "Ctrl+M"
        self.main_window.cfg["bind_deafen"] = self.deaf_bind_input.text().strip() or "Ctrl+D"
        self.main_window.cfg["bind_tray"] = self.tray_bind_input.text().strip() or "Ctrl+H"
        self.main_window.cfg["bind_overlay"] = self.overlay_bind_input.text().strip() or "Ctrl+O"

        save_config(self.main_window.cfg)
        self.main_window.start_audio_stream()
        self.main_window.update_global_hotkeys()

class LogsInterface(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("LogsInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(12)
        
        self.init_ui()

    def init_ui(self):
        top_row = QHBoxLayout()
        self.title = SubtitleLabel("Сетевые логи и статус", self)
        clear_btn = PushButton("Очистить логи", self)
        clear_btn.setIcon(FluentIcon.DELETE)
        clear_btn.clicked.connect(self.clear_logs)
        top_row.addWidget(self.title)
        top_row.addStretch()
        top_row.addWidget(clear_btn)
        self.layout.addLayout(top_row)

        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: rgba(255, 255, 255, 0.03); color: #64B5F6; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 10px; }"
        )
        self.layout.addWidget(self.log_text)

    def append_log(self, text):
        self.log_text.append(text)

    def clear_logs(self):
        self.log_text.clear()

class InfoInterface(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("InfoInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(16)
        
        self.init_ui()

    def init_ui(self):
        self.title = SubtitleLabel("О программе", self)
        self.layout.addWidget(self.title)

        card = SimpleCardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        app_title = TitleLabel("Wave V1.3 by yunscryy", card)
        card_layout.addWidget(app_title)

        info_text = (
            "Сервер основан на бесплатном хостинге render.com reley, если сервер лег - сорян я тут не причем\n\n"
            "Архитектура и стек технологий:\n"
            "• Клиентская среда: Python 3.14 x64\n"
            "• Графический стек: PyQt6, QFluentWidgets (Fluent Design System Win11)\n"
            "• Аудио ядро: SoundDevice, NumPy (PCM16 16kHz, IIR DSP processing, VAD Gate Engine)\n"
            "• Транспортный протокол: WebSockets (двунаправленный бинарный стриминг)\n"
            "• Системный уровень: Win32 API Hooking (User32 / Shell32)"
        )

        desc = BodyLabel(info_text, card)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        ver = CaptionLabel("Версия: 1.3.0 Pro Suite", card)
        card_layout.addWidget(ver)
        card_layout.addSpacing(4)

        gh_btn = PushButton("Репозиторий GitHub", card)
        gh_btn.setIcon(FluentIcon.GITHUB)
        gh_btn.clicked.connect(self.on_github_click)
        card_layout.addWidget(gh_btn)

        self.layout.addWidget(card)
        self.layout.addStretch()

    def on_github_click(self):
        QDesktopServices.openUrl(QUrl("https://github.com/sambabruno01-ux/wave"))

class MainWindow(FluentWindow):
    show_error_signal = pyqtSignal(str)
    enter_room_signal = pyqtSignal()
    update_users_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)
    chat_message_signal = pyqtSignal(str, str)
    smooth_glow_signal = pyqtSignal(str, float)
    user_ping_signal = pyqtSignal(str, int)
    room_status_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.in_devs, self.out_devs = get_audio_devices()

        default_user = self.cfg.get("user_name") or get_windows_user()
        self.accent_color = get_windows_accent_color()
        self.accent_rgb = hex_to_rgb(self.accent_color)

        self.state = {
            "user": default_user,
            "room": "",
            "password": "",
            "in_room": False,
            "mic_muted": False,
            "deafened": False,
            "self_listen": False,
        }

        self.ws_client = None
        self.ws_loop = None
        self.out_queue = None
        self.peer_volumes = {}
        self.ping_start_time = 0
        self.current_ping = 0
        
        self.incoming_audio_queue = {}
        self.speaker_activity = {}
        self.speaker_glow_levels = {}
        self.last_played_audio_sample = np.zeros(BLOCK_SIZE, dtype=np.float32)
        self.noise_profile = 0.005
        self.agc_gain = 1.0
        self.vad_hold_counter = 0
        self.audio_lock = threading.Lock()

        self.audio_stream = None
        self.stream_lock = threading.Lock()

        self.hotkey_mgr = GlobalHotkeyManager()
        self.hotkey_mgr.hotkey_triggered.connect(self.on_global_hotkey_triggered)

        self.init_window()
        self.init_tray_icon()
        self.init_overlay()
        self.init_audio_engine()
        self.init_signals()
        self.update_global_hotkeys()
        
        # 30 FPS таймер подсветки
        self.glow_timer = QTimer(self)
        self.glow_timer.timeout.connect(self.update_speaking_glow_smooth)
        self.glow_timer.start(33)

        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self.send_ping_request)
        self.ping_timer.start(25000)

        self.log(f"[System] Wave Voice Client запущен. Пользователь: {default_user}")
        self.start_persistent_server_connection()

    def init_window(self):
        self.setWindowTitle("Wave")
        self.resize(700, 780)
        self.setMinimumSize(580, 660)

        setTheme(Theme.DARK)
        setThemeColor(self.accent_color)

        self.room_interface = RoomInterface(self)
        self.settings_interface = SettingsInterface(self)
        self.logs_interface = LogsInterface(self)
        self.info_interface = InfoInterface(self)

        self.addSubInterface(self.room_interface, FluentIcon.CHAT, "Комната")
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, "Настройки")
        self.addSubInterface(self.logs_interface, FluentIcon.DOCUMENT, "Логи")
        self.addSubInterface(self.info_interface, FluentIcon.INFO, "Информация")

        self.navigationInterface.addItem(
            routeKey="minimize_tray_action",
            icon=FluentIcon.MINIMIZE,
            text="Свернуть в трей",
            onClick=self.toggle_tray_minimize,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

    def init_overlay(self):
        self.overlay = VoiceOverlay(self)
        if self.cfg.get("overlay_enabled", False):
            self.overlay.show()
        else:
            self.overlay.hide()

    def toggle_overlay(self):
        is_visible = self.overlay.isVisible()
        if is_visible:
            self.overlay.hide()
            self.cfg["overlay_enabled"] = False
        else:
            self.overlay.show()
            self.cfg["overlay_enabled"] = True
        self.settings_interface.overlay_switch.setChecked(not is_visible)
        save_config(self.cfg)

    def init_tray_icon(self):
        icon = QIcon(ICON_PATH_ICO) if os.path.exists(ICON_PATH_ICO) else (
            QIcon(ICON_PATH_PNG) if os.path.exists(ICON_PATH_PNG) else QIcon(self.style().standardIcon(QApplication.style().StandardPixmap.SP_DriveNetIcon))
        )

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Wave Voice Client")

        tray_menu = QMenu()
        show_action = tray_menu.addAction("Показать Wave")
        show_action.triggered.connect(self.show_from_tray)
        
        mute_action = tray_menu.addAction("Вкл/Выкл микрофон")
        mute_action.triggered.connect(self.room_interface.toggle_mic)

        overlay_action = tray_menu.addAction("Вкл/Выкл оверлей")
        overlay_action.triggered.connect(self.toggle_overlay)

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Закрыть Wave")
        quit_action.triggered.connect(self.close)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def toggle_tray_minimize(self):
        if self.isVisible():
            self.hide()
            self.tray_icon.showMessage("Wave", "Приложение свернуто в трей", QSystemTrayIcon.MessageIcon.Information, 1500)
        else:
            self.show_from_tray()

    def show_from_tray(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_tray_minimize()

    def init_signals(self):
        self.show_error_signal.connect(self.on_show_error)
        self.enter_room_signal.connect(self.on_enter_room)
        self.update_users_signal.connect(self.room_interface.update_users_list)
        self.update_users_signal.connect(self.overlay.update_users)
        self.log_signal.connect(self.logs_interface.append_log)
        self.chat_message_signal.connect(self.room_interface.receive_chat_message)
        self.smooth_glow_signal.connect(self.on_smooth_glow_update)
        self.user_ping_signal.connect(self.room_interface.update_user_ping_ui)
        self.user_ping_signal.connect(self.overlay.update_ping)
        self.room_status_signal.connect(self.room_interface.set_room_status_ui)

    def on_smooth_glow_update(self, user, alpha):
        self.room_interface.set_speaker_glow_smooth(user, alpha, self.accent_rgb)
        self.overlay.set_user_glow_smooth(user, alpha, self.accent_rgb)

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_signal.emit(f"[{timestamp}] {msg}")

    def on_show_error(self, err_msg):
        self.room_interface.action_btn.setEnabled(True)
        self.room_interface.action_btn.setText("Создать / Войти")
        InfoBar.error(
            title="Ошибка",
            content=err_msg,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self.room_interface
        )

    def on_enter_room(self):
        self.room_interface.show_active_room()
        self.send_ping_request()

    def notify_event(self, event_type):
        def _play():
            try:
                QApplication.alert(self, 1200)
            except Exception:
                pass

            sound_file = None
            if event_type == "chat":
                for name in ["notif.wav", "notif.mp3"]:
                    p = os.path.join(ASSETS_DIR, name)
                    if os.path.exists(p):
                        sound_file = p
                        break
            elif event_type == "user_joined":
                for name in ["user.wav", "user.mp3"]:
                    p = os.path.join(ASSETS_DIR, name)
                    if os.path.exists(p):
                        sound_file = p
                        break
            elif event_type == "user_left":
                for name in ["exit.wav", "exit.mp3"]:
                    p = os.path.join(ASSETS_DIR, name)
                    if os.path.exists(p):
                        sound_file = p
                        break

            if sound_file:
                try:
                    if sound_file.endswith(".wav"):
                        winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    else:
                        ctypes.windll.winmm.mciSendStringW(f'open "{sound_file}" type mpegvideo alias {event_type}_snd', None, 0, 0)
                        ctypes.windll.winmm.mciSendStringW(f'play {event_type}_snd from 0', None, 0, 0)
                    return
                except Exception:
                    pass

            try:
                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                try:
                    winsound.MessageBeep(winsound.MB_OK)
                except Exception:
                    pass

        threading.Thread(target=_play, daemon=True).start()

    def update_global_hotkeys(self):
        hotkeys = {
            "mute": self.cfg.get("bind_mute_mic", "Ctrl+M"),
            "deafen": self.cfg.get("bind_deafen", "Ctrl+D"),
            "tray": self.cfg.get("bind_tray", "Ctrl+H"),
            "overlay": self.cfg.get("bind_overlay", "Ctrl+O")
        }
        self.hotkey_mgr.set_hotkeys(hotkeys)
        self.log(f"[Global Hotkeys] Бинды активны: Мик={hotkeys['mute']}, Звук={hotkeys['deafen']}, Трей={hotkeys['tray']}, Оверлей={hotkeys['overlay']}")

    def on_global_hotkey_triggered(self, action):
        if action == "mute":
            self.room_interface.toggle_mic()
        elif action == "deafen":
            self.room_interface.toggle_deaf()
        elif action == "tray":
            self.toggle_tray_minimize()
        elif action == "overlay":
            self.toggle_overlay()

    def update_speaking_glow_smooth(self):
        now = time.time()
        active_users = set(self.speaker_activity.keys()) | set(self.speaker_glow_levels.keys())

        for user in active_users:
            last_t = self.speaker_activity.get(user, 0)
            
            if user == self.state["user"] and self.state["mic_muted"]:
                is_active = False
            else:
                is_active = (now - last_t) < 0.35

            target = 1.0 if is_active else 0.0
            cur = self.speaker_glow_levels.get(user, 0.0)

            if cur < target:
                cur = min(1.0, cur + 0.35)
            elif cur > target:
                cur = max(0.0, cur - 0.12)

            if abs(cur - self.speaker_glow_levels.get(user, -1.0)) > 0.005:
                self.speaker_glow_levels[user] = cur
                self.smooth_glow_signal.emit(user, cur)

    def send_ping_request(self):
        if self.ws_client:
            self.ping_start_time = time.time()
            self.send_json_msg({
                "type": "PING",
                "ts": self.ping_start_time
            })

    def send_json_msg(self, obj):
        if self.ws_loop and self.ws_loop.is_running() and self.out_queue:
            try:
                raw_str = json.dumps(obj)
                self.ws_loop.call_soon_threadsafe(self.out_queue.put_nowait, raw_str)
            except Exception:
                pass

    def start_persistent_server_connection(self):
        def _runner():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            self.out_queue = asyncio.Queue(maxsize=50)
            self.ws_loop.run_until_complete(self._persistent_ws_handler())

        threading.Thread(target=_runner, daemon=True).start()

    async def _sender_task(self, ws):
        while True:
            try:
                packet = await self.out_queue.get()
                await ws.send(packet)
                self.out_queue.task_done()
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception:
                await asyncio.sleep(0.01)

    async def _receiver_task(self, ws):
        try:
            async for msg in ws:
                if isinstance(msg, str):
                    try:
                        data = json.loads(msg)
                        mtype = data.get("type")

                        if mtype == "ROOM_STATUS":
                            exists = data.get("exists", False)
                            self.room_status_signal.emit(exists)

                        elif mtype == "JOIN_OK":
                            self.state["in_room"] = True
                            self.enter_room_signal.emit()
                            self.log(f"[Server] Авторизация успешна в комнате '{data.get('room')}'")

                        elif mtype == "AUTH_ERROR":
                            self.show_error_signal.emit(data.get("msg", "Ошибка входа"))

                        elif mtype == "USER_LIST":
                            users = data.get("users", {})
                            self.update_users_signal.emit(users)

                        elif mtype == "PONG":
                            if self.ping_start_time > 0:
                                rtt = int((time.time() - self.ping_start_time) * 1000)
                                self.current_ping = rtt
                                u_name = self.state["user"]
                                self.user_ping_signal.emit(u_name, rtt)
                                if self.state["in_room"]:
                                    self.send_json_msg({"type": "REPORT_PING", "ping": rtt})

                        elif mtype == "CHAT":
                            sender = data.get("sender")
                            text = data.get("text")
                            self.chat_message_signal.emit(sender, text)

                    except Exception:
                        pass

                elif isinstance(msg, bytes) and len(msg) >= 3:
                    name_len = msg[1]
                    sender_name = msg[2:2+name_len].decode('utf-8', errors='ignore')
                    audio_bytes = msg[2+name_len:]

                    pcm16_data = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_array = pcm16_data.astype(np.float32) / 32768.0

                    rms = np.sqrt(np.mean(audio_array**2))
                    if rms > 0.008:
                        self.speaker_activity[sender_name] = time.time()

                    is_me = (sender_name == self.state["user"])
                    user_vol = 1.0 if is_me else self.peer_volumes.get(sender_name, 1.0)
                    if user_vol != 1.0:
                        audio_array = audio_array * user_vol

                    eq_name = self.cfg.get("equalizer_preset", "Стандартный (Flat)")
                    audio_array = apply_equalizer_filter(audio_array, eq_name)

                    with self.audio_lock:
                        if sender_name not in self.incoming_audio_queue:
                            self.incoming_audio_queue[sender_name] = []
                        if len(self.incoming_audio_queue[sender_name]) < 4:
                            self.incoming_audio_queue[sender_name].append(audio_array)

        except websockets.exceptions.ConnectionClosed:
            pass

    async def _persistent_ws_handler(self):
        while True:
            try:
                self.log(f"[Server] Подключение к {RELAY_SERVER_URL}...")
                async with websockets.connect(
                    RELAY_SERVER_URL, 
                    open_timeout=45,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=10*1024*1024
                ) as ws:
                    self.ws_client = ws
                    self.log("[Server] Соединение с сервером активно!")
                    
                    self.send_ping_request()

                    if self.state["in_room"] and self.state["room"]:
                        join_req = json.dumps({
                            "type": "JOIN",
                            "room": self.state["room"],
                            "user": self.state["user"],
                            "password": self.state.get("password", ""),
                            "mic_muted": self.state["mic_muted"],
                            "deafened": self.state["deafened"],
                            "self_listen": self.state["self_listen"]
                        })
                        await ws.send(join_req)

                    await asyncio.gather(
                        self._sender_task(ws),
                        self._receiver_task(ws)
                    )

            except Exception as e:
                self.ws_client = None
                self.log(f"[Server Reconnect] Повтор через 3с: {e}")
                await asyncio.sleep(3)

    def leave_and_cleanup(self):
        if not self.state["room"]:
            return
        r_id = self.state["room"]
        self.state["in_room"] = False
        self.state["room"] = ""
        self.state["password"] = ""
        self.log(f"[Room] Выход из комнаты {r_id}")
        
        if self.ws_client and self.ws_loop:
            try:
                asyncio.run_coroutine_threadsafe(self.ws_client.close(), self.ws_loop)
            except Exception:
                pass

    def process_microphone(self, mic_chunk):
        boost = float(self.cfg.get("mic_boost", 1.0))
        signal = mic_chunk * boost

        if self.cfg.get("echo_cancellation", False):
            ref_rms = np.sqrt(np.mean(self.last_played_audio_sample**2))
            if ref_rms > 0.01:
                suppress_factor = np.clip(1.0 - (ref_rms * 1.5), 0.35, 1.0)
                signal = signal * suppress_factor

        if self.cfg.get("noise_suppression", False):
            rms_cur = np.sqrt(np.mean(signal**2))
            if rms_cur < 0.015:
                self.noise_profile = 0.92 * self.noise_profile + 0.08 * rms_cur
            snr = (rms_cur + 1e-6) / (self.noise_profile + 1e-6)
            noise_gain = np.clip((snr - 1.2) / 2.0, 0.0, 1.0)
            signal = signal * (0.15 + 0.85 * noise_gain)

        if self.cfg.get("auto_gain_control", False):
            rms = np.sqrt(np.mean(signal**2))
            if rms > 0.008:
                target_rms = 0.10
                desired_gain = np.clip(target_rms / (rms + 1e-5), 0.6, 2.5)
                self.agc_gain = 0.90 * self.agc_gain + 0.10 * desired_gain
                signal = signal * self.agc_gain

        return signal

    def audio_callback(self, indata, outdata, frames, time_info, status):
        raw_mic = indata[:, 0]
        processed_mic = self.process_microphone(raw_mic)

        rms = np.sqrt(np.mean(processed_mic**2))
        vad_gate = float(self.cfg.get("vad_threshold", 0.0))
        
        if vad_gate <= 0.001:
            is_speaking = (rms > 0.004) and (not self.state["mic_muted"])
        else:
            if rms > vad_gate and not self.state["mic_muted"]:
                self.vad_hold_counter = 9
            elif self.vad_hold_counter > 0:
                self.vad_hold_counter -= 1
            
            is_speaking = (self.vad_hold_counter > 0) and (not self.state["mic_muted"])

        if is_speaking:
            self.speaker_activity[self.state["user"]] = time.time()

        if self.state["in_room"] and self.out_queue and is_speaking:
            clipped = np.clip(processed_mic, -1.0, 1.0)
            pcm16_data = (clipped * 32767).astype(np.int16)

            u_bytes = self.state["user"].encode('utf-8')
            header = bytearray([2, len(u_bytes)]) + u_bytes
            packet = bytes(header + pcm16_data.tobytes())

            if self.ws_loop and self.ws_loop.is_running():
                try:
                    self.ws_loop.call_soon_threadsafe(self.out_queue.put_nowait, packet)
                except Exception:
                    pass

        mixed_audio = np.zeros(frames, dtype=np.float32)

        if not self.state["deafened"]:
            with self.audio_lock:
                for sender, chunks in list(self.incoming_audio_queue.items()):
                    if chunks:
                        chunk = chunks.pop(0)
                        if len(chunk) == frames:
                            mixed_audio += chunk
                        elif len(chunk) > frames:
                            mixed_audio += chunk[:frames]
                        else:
                            mixed_audio[:len(chunk)] += chunk

        mixed_audio = np.clip(mixed_audio, -1.0, 1.0)
        self.last_played_audio_sample = mixed_audio.copy()
        outdata[:, 0] = mixed_audio

    def start_audio_stream(self):
        with self.stream_lock:
            if self.audio_stream is not None:
                try:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                except Exception:
                    pass
                self.audio_stream = None

            try:
                in_idx = None
                out_idx = None
                for d in self.in_devs:
                    if d["name"] == self.cfg.get("mic_device"):
                        in_idx = d["index"]
                        break
                for d in self.out_devs:
                    if d["name"] == self.cfg.get("speaker_device"):
                        out_idx = d["index"]
                        break

                self.audio_stream = sd.Stream(
                    device=(in_idx, out_idx),
                    channels=1,
                    samplerate=SAMPLE_RATE,
                    blocksize=BLOCK_SIZE,
                    callback=self.audio_callback
                )
                self.audio_stream.start()
                self.log(f"[Audio Engine] Аудиопоток активен ({SAMPLE_RATE} Гц).")
            except Exception as e:
                self.log(f"[Audio Error] Ошибка запуска аудио: {e}")

    def init_audio_engine(self):
        self.start_audio_stream()

    def closeEvent(self, event):
        self.hotkey_mgr.stop()
        self.overlay.close()
        self.leave_and_cleanup()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if os.path.exists(ICON_PATH_ICO):
        app.setWindowIcon(QIcon(ICON_PATH_ICO))
    elif os.path.exists(ICON_PATH_PNG):
        app.setWindowIcon(QIcon(ICON_PATH_PNG))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())