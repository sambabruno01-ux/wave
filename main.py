import sys
import os
import ctypes
from ctypes import wintypes
import getpass
import json
import threading
import time
import asyncio
import websockets
import sounddevice as sd
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

try:
    myappid = 'yunscryy.wave.voiceclient.1.4.9'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QObject, QMimeData
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QFrame, QStackedWidget, QTextBrowser, QTextEdit, QGridLayout,
    QSystemTrayIcon, QMenu, QLabel, QFileDialog
)
from PyQt6.QtGui import (
    QFont, QKeySequence, QIcon, QKeyEvent, QColor, 
    QMouseEvent, QPainter, QPen, QDesktopServices, QDrag, QFontMetrics
)

from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon, 
    SubtitleLabel, TitleLabel, BodyLabel, CaptionLabel, StrongBodyLabel,
    LineEdit, PasswordLineEdit, PrimaryPushButton, PushButton,
    SwitchButton, Slider, ComboBox, InfoBar, InfoBarPosition, 
    setTheme, Theme, setThemeColor, PillPushButton, SimpleCardWidget, 
    ScrollArea, IconWidget, PrimaryToolButton, MessageBoxBase, ToolButton
)

from locales import TRANSLATIONS

DEFAULT_SERVER_URL = ""

APPDATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "WaveVoice")
CACHE_DIR = os.path.join(APPDATA_DIR, "sound_cache")
os.makedirs(APPDATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(APPDATA_DIR, "settings.json")
SOUNDPAD_CONFIG_PATH = os.path.join(APPDATA_DIR, "soundpad.json")

if getattr(sys, 'frozen', False):
    BUNDLE_DIR = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
ICON_PATH_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PATH_PNG = os.path.join(ASSETS_DIR, "icon.png")

SAMPLE_RATE = 16000
BLOCK_SIZE = 640

EQ_PRESETS = {
    "eq_flat": (1.0, 1.0, 1.0),
    "eq_crisp": (0.85, 1.25, 1.15),
    "eq_warm": (1.25, 1.10, 0.85),
    "eq_clarity": (0.75, 1.30, 1.25),
    "eq_bass": (1.40, 0.95, 0.85)
}

OVERLAY_MODES = [
    "overlay_mode_none",
    "overlay_mode_self",
    "overlay_mode_separate"
]

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

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

def convert_and_cache_audio(src_path):
    try:
        import wave
        cache_name = f"snd_{abs(hash(src_path))}.wav"
        dest_wav = os.path.join(CACHE_DIR, cache_name)

        if os.path.exists(dest_wav) and os.path.getsize(dest_wav) > 100:
            return dest_wav

        data = None
        sr = SAMPLE_RATE

        if sf is not None:
            try:
                data, sr = sf.read(src_path, dtype='float32')
                if data.ndim > 1:
                    data = data.mean(axis=1)
            except Exception:
                data = None

        if data is None and src_path.lower().endswith(".wav"):
            try:
                with wave.open(src_path, 'rb') as wf:
                    sr = wf.getframerate()
                    ch = wf.getnchannels()
                    sw = wf.getsampwidth()
                    raw = wf.readframes(wf.getnframes())
                    if sw == 2:
                        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    elif sw == 1:
                        data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
                    if ch > 1 and data is not None:
                        data = data.reshape(-1, ch).mean(axis=1)
            except Exception:
                data = None

        if data is None:
            return None

        if sr != SAMPLE_RATE:
            data = np.interp(
                np.linspace(0, len(data), int(len(data) * SAMPLE_RATE / sr)),
                np.arange(len(data)),
                data
            ).astype(np.float32)

        data = np.clip(data, -1.0, 1.0)
        pcm16_bytes = (data * 32767).astype(np.int16).tobytes()

        with wave.open(dest_wav, 'wb') as out_wf:
            out_wf.setnchannels(1)
            out_wf.setsampwidth(2)
            out_wf.setframerate(SAMPLE_RATE)
            out_wf.writeframes(pcm16_bytes)

        return dest_wav
    except Exception as e:
        print(f"[Convert Error] {e}")
        return None

def read_pcm_from_cached_wav(wav_path):
    try:
        import wave
        with wave.open(wav_path, 'rb') as wf:
            raw = wf.readframes(wf.getnframes())
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception:
        return None

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
                if combo:
                    mod, vk = parse_hotkey_string(combo)
                    if mod is not None and vk is not None:
                        self.current_hotkeys[hid] = (action, mod, vk)
                        hid += 1
        if self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_UPDATE_HOTKEYS, 0, 0)

    def _msg_loop(self):
        self.thread_id = kernel32.GetCurrentThreadId()
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
        "server_url": DEFAULT_SERVER_URL,
        "language": "ru",
        "dev_mode": False,
        "mic_device": None,
        "speaker_device": None,
        "mic_boost": 1.0,
        "vad_threshold": 0.0,
        "echo_cancellation": False,
        "noise_suppression": False,
        "auto_gain_control": False,
        "equalizer_preset": "eq_flat",
        "overlay_enabled": False,
        "overlay_mode": "overlay_mode_none",
        "ov_icon_mic": True,
        "ov_icon_spk": True,
        "overlay_x_pct": 3.0,
        "overlay_y_pct": 3.0,
        "overlay_scale": 100,
        "bind_mute_mic": "",
        "bind_deafen": "",
        "bind_tray": "",
        "bind_overlay": "",
        "bind_soundpad_stop": "",
        "soundpad_interrupt": True,
        "pinned_room": None,
        "pinned_pwd": "",
        "soundpad_tx_vol": 1.0,
        "soundpad_local_vol": 1.0,
        "peer_settings": {}
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for k, v in loaded.items():
                    cfg[k] = v
        except Exception:
            pass

    if not cfg.get("user_name"):
        cfg["user_name"] = get_windows_user()
        
    return cfg

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def load_soundpad():
    if os.path.exists(SOUNDPAD_CONFIG_PATH):
        try:
            with open(SOUNDPAD_CONFIG_PATH, "r", encoding="utf-8") as f:
                items = json.load(f)
                valid = []
                for it in items:
                    p = it.get("cached_path") or it.get("path") or it.get("orig_path")
                    if p:
                        it["cached_path"] = p
                        valid.append(it)
                return valid
        except Exception:
            pass
    return []

def save_soundpad(data):
    try:
        with open(SOUNDPAD_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
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
    if not inputs: inputs = [{"index": None, "name": "Default Microphone"}]
    if not outputs: outputs = [{"index": None, "name": "Default Speakers"}]
    return inputs, outputs

def apply_equalizer_filter(audio_array, preset_key):
    g_low, g_mid, g_high = EQ_PRESETS.get(preset_key, (1.0, 1.0, 1.0))
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

class KeyRecorderEdit(LineEdit):
    keySequenceRecorded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("...")

    def mousePressEvent(self, event: QMouseEvent):
        self.clear()
        self.keySequenceRecorded.emit("")
        event.accept()

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

class UserSettingsModal(MessageBoxBase):
    def __init__(self, username, main_window, parent=None):
        super().__init__(parent)
        self.username = username
        self.main_window = main_window

        user_cfg = self.main_window.cfg["peer_settings"].get(username, {"vol": 1.0, "ducking": 0})
        
        self.titleLabel = SubtitleLabel(self.main_window.tr("modal_user_title").format(user=username), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(BodyLabel(self.main_window.tr("lbl_user_vol"), self))
        self.vol_lbl = CaptionLabel(f"{int(user_cfg.get('vol', 1.0) * 100)}%", self)
        self.vol_slider = Slider(Qt.Orientation.Horizontal, self)
        self.vol_slider.setRange(0, 200)
        self.vol_slider.setValue(int(user_cfg.get('vol', 1.0) * 100))
        self.vol_slider.valueChanged.connect(lambda v: self.vol_lbl.setText(f"{v}%"))
        
        v_box = QHBoxLayout()
        v_box.addWidget(self.vol_slider)
        v_box.addWidget(self.vol_lbl)
        self.viewLayout.addLayout(v_box)

        self.viewLayout.addWidget(BodyLabel(self.main_window.tr("lbl_ducking_pct"), self))
        self.duck_lbl = CaptionLabel(f"{user_cfg.get('ducking', 0)}%", self)
        self.duck_slider = Slider(Qt.Orientation.Horizontal, self)
        self.duck_slider.setRange(0, 75)
        self.duck_slider.setValue(user_cfg.get('ducking', 0))
        self.duck_slider.valueChanged.connect(lambda v: self.duck_lbl.setText(f"{v}%"))

        d_box = QHBoxLayout()
        d_box.addWidget(self.duck_slider)
        d_box.addWidget(self.duck_lbl)
        self.viewLayout.addLayout(d_box)

        self.yesButton.setText(self.main_window.tr("btn_save"))
        self.cancelButton.setText(self.main_window.tr("btn_cancel"))
        self.widget.setMinimumWidth(380)

    def apply_settings(self):
        self.main_window.cfg["peer_settings"][self.username] = {
            "vol": self.vol_slider.value() / 100.0,
            "ducking": self.duck_slider.value()
        }
        save_config(self.main_window.cfg)

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
        self.mic_lbl = QLabel(self.main_window.tr("btn_on"), self.mic_card)
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
        self.spk_lbl = QLabel(self.main_window.tr("btn_on"), self.spk_card)
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

        overlay_mode = self.main_window.cfg.get("overlay_mode", "overlay_mode_none")
        show_bottom_controls = (overlay_mode == "overlay_mode_separate")
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

        overlay_mode = self.main_window.cfg.get("overlay_mode", "overlay_mode_none")
        include_self = (overlay_mode == "overlay_mode_self")

        show_mic = self.main_window.cfg.get("ov_icon_mic", True)
        show_spk = self.main_window.cfg.get("ov_icon_spk", True)

        ordered_users = self.main_window.user_order if self.main_window.user_order else list(users_dict.keys())
        users_items = [(u, users_dict[u]) for u in ordered_users if u in users_dict]

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

            full_name = f"{user}{self.main_window.tr('you_suffix')}" if is_me else user
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

            mic_muted = self.main_window.state["mic_muted"] if is_me else udata.get("mic_muted", False)
            deafened = self.main_window.state["deafened"] if is_me else udata.get("deafened", False)

            mic_icon = None
            spk_icon = None

            if show_mic:
                mic_icon = StatusIconWidget(FluentIcon.MICROPHONE, card, is_slashed=mic_muted, slash_color="#FFFFFF")
                mic_icon.setFixedSize(14, 14)
                r_layout.addWidget(mic_icon)

            if show_spk:
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
                border_a = min(1.0, 0.40 + 0.60 * alpha)
                border_width = 1.5 + (0.8 * alpha)
                card.setStyleSheet(f"""
                    QFrame.OverlayUserCard {{
                        background-color: rgba(26, 26, 26, 0.86);
                        border: {border_width:.1f}px solid rgba({r}, {g}, {b}, {border_a:.2f});
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

        self.mic_lbl.setText(self.main_window.tr("btn_off") if mic_off else self.main_window.tr("btn_on"))
        self.mic_icon.set_slashed(mic_off)

        self.spk_lbl.setText(self.main_window.tr("btn_off") if deaf_on else self.main_window.tr("btn_on"))
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

class ServerSettingsModalDialog(MessageBoxBase):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        self.titleLabel = SubtitleLabel(self.main_window.tr("modal_server_title"), self)
        self.viewLayout.addWidget(self.titleLabel)

        self.urlLabel = BodyLabel(self.main_window.tr("modal_server_lbl"), self)
        self.viewLayout.addWidget(self.urlLabel)

        self.url_input = LineEdit(self)
        self.url_input.setText(self.main_window.cfg.get("server_url", ""))
        self.url_input.setPlaceholderText("ws://IP:8765")
        self.viewLayout.addWidget(self.url_input)

        inst_card = SimpleCardWidget(self)
        inst_l = QVBoxLayout(inst_card)
        inst_l.setContentsMargins(12, 10, 12, 10)
        inst_l.setSpacing(4)
        inst_l.addWidget(StrongBodyLabel(self.main_window.tr("modal_server_inst_title"), inst_card))
        
        info_lbl = CaptionLabel(self.main_window.tr("modal_server_inst"), inst_card)
        info_lbl.setWordWrap(True)
        inst_l.addWidget(info_lbl)
        self.viewLayout.addWidget(inst_card)

        self.yesButton.setText(self.main_window.tr("btn_save"))
        self.cancelButton.setText(self.main_window.tr("btn_cancel"))
        self.widget.setMinimumWidth(440)

    def validate_and_apply(self):
        new_url = self.url_input.text().strip()
        if new_url and not (new_url.startswith("ws://") or new_url.startswith("wss://")):
            InfoBar.error("Error", self.main_window.tr("server_prefix_err"), duration=3500, parent=self.main_window)
            return False

        self.main_window.cfg["server_url"] = new_url
        save_config(self.main_window.cfg)
        self.main_window.reconnect_websocket()
        InfoBar.success("Server", self.main_window.tr("server_saved"), duration=3000, parent=self.main_window)
        return True

class DraggableUserCard(SimpleCardWidget):
    def __init__(self, username, room_interface, parent=None):
        super().__init__(parent)
        self.username = username
        self.room_interface = room_interface
        self.setObjectName(f"user_card_{username}")
        self.setStyleSheet("SimpleCardWidget { border: 2px solid transparent; border-radius: 8px; background-color: rgba(255, 255, 255, 0.04); }")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drag_start_pos = None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drag_start_pos and (event.pos() - self.drag_start_pos).manhattanLength() > 8:
            if self.username != self.room_interface.main_window.state["user"]:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(self.username)
                drag.setMimeData(mime)
                drag.exec(Qt.DropAction.MoveAction)
                self.drag_start_pos = None
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.drag_start_pos is not None:
            if self.username != self.room_interface.main_window.state["user"]:
                modal = UserSettingsModal(self.username, self.room_interface.main_window, self.room_interface.main_window)
                if modal.exec():
                    modal.apply_settings()
        self.drag_start_pos = None
        event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() != self.room_interface.main_window.state["user"]:
            event.acceptProposedAction()

    def dropEvent(self, event):
        src_user = event.mimeData().text()
        dest_user = self.username
        if src_user != dest_user:
            self.room_interface.reorder_users_drag(src_user, dest_user)
        event.acceptProposedAction()

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
        self.layout.addWidget(self.stack, 1)

        self.init_auth_view()
        self.init_reserved_lobby_view()
        self.init_room_view()
        self.init_permanent_control_bar()

        if self.main_window.cfg.get("pinned_room"):
            self.show_reserved_lobby(self.main_window.cfg.get("pinned_room"), {})
        else:
            self.stack.setCurrentIndex(0)

    def init_auth_view(self):
        self.auth_page = QWidget()
        layout = QVBoxLayout(self.auth_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = TitleLabel(self.main_window.tr("auth_title"), self.auth_page)
        layout.addWidget(title)

        card = SimpleCardWidget(self.auth_page)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)

        header = BodyLabel(self.main_window.tr("auth_subtitle"), card)
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        card_layout.addWidget(header)

        self.name_input = LineEdit(card)
        self.name_input.setPlaceholderText(self.main_window.tr("placeholder_nickname"))
        self.name_input.setText(self.main_window.state["user"])
        card_layout.addWidget(self.name_input)

        self.room_input = LineEdit(card)
        self.room_input.setPlaceholderText(self.main_window.tr("placeholder_room"))
        self.room_input.textChanged.connect(self.check_room_status)
        card_layout.addWidget(self.room_input)

        self.status_lbl = CaptionLabel(self.main_window.tr("status_enter_room"), card)
        card_layout.addWidget(self.status_lbl)

        self.pwd_input = PasswordLineEdit(card)
        self.pwd_input.setPlaceholderText(self.main_window.tr("placeholder_pwd"))
        card_layout.addWidget(self.pwd_input)

        self.action_btn = PrimaryPushButton(self.main_window.tr("btn_join_action"), card)
        self.action_btn.setIcon(FluentIcon.MESSAGE)
        self.action_btn.clicked.connect(self.join_or_create_room)
        self.action_btn.setEnabled(False)
        card_layout.addWidget(self.action_btn)

        layout.addWidget(card)
        layout.addStretch()

        self.server_cfg_btn = PushButton(self.main_window.tr("btn_server_setup"), self.auth_page)
        self.server_cfg_btn.setIcon(FluentIcon.GLOBE)
        self.server_cfg_btn.clicked.connect(self.open_server_settings)
        layout.addWidget(self.server_cfg_btn)

        self.stack.addWidget(self.auth_page)

    def init_reserved_lobby_view(self):
        self.reserved_page = QWidget()
        layout = QVBoxLayout(self.reserved_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self.res_title = SubtitleLabel("", self.reserved_page)
        self.wake_btn = PrimaryPushButton(self.main_window.tr("btn_wake"), self.reserved_page)
        self.wake_btn.setIcon(FluentIcon.MESSAGE)
        self.wake_btn.clicked.connect(self.wake_from_sleep)
        top.addWidget(self.res_title)
        top.addStretch()
        top.addWidget(self.wake_btn)
        layout.addLayout(top)

        self.res_scroll = ScrollArea(self.reserved_page)
        self.res_scroll.setWidgetResizable(True)
        self.res_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.res_scroll.setStyleSheet("background: transparent;")
        
        self.res_content = QWidget()
        self.res_layout = QVBoxLayout(self.res_content)
        self.res_layout.setContentsMargins(0, 0, 0, 0)
        self.res_layout.setSpacing(8)
        self.res_layout.addStretch()
        
        self.res_scroll.setWidget(self.res_content)
        layout.addWidget(self.res_scroll)

        self.stack.addWidget(self.reserved_page)

    def init_room_view(self):
        self.room_page = QWidget()
        layout = QVBoxLayout(self.room_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        self.room_heading = SubtitleLabel(self.main_window.tr("lobby_title").format(room=""), self.room_page)

        self.reserve_toggle_btn = PillPushButton(self.main_window.tr("btn_pin_off"), self.room_page)
        self.reserve_toggle_btn.setCheckable(True)
        self.reserve_toggle_btn.clicked.connect(self.toggle_room_reserve)

        self.leave_btn = PushButton(self.main_window.tr("btn_leave"), self.room_page)
        self.leave_btn.setIcon(FluentIcon.POWER_BUTTON)
        self.leave_btn.clicked.connect(self.leave_or_sleep_room)

        top_row.addWidget(self.room_heading)
        top_row.addStretch()
        top_row.addWidget(self.reserve_toggle_btn)
        top_row.addWidget(self.leave_btn)
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
        self.chat_input.setPlaceholderText(self.main_window.tr("chat_placeholder"))
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

        self.stack.addWidget(self.room_page)

    def init_permanent_control_bar(self):
        self.ctrl_card = SimpleCardWidget(self)
        ctrl_layout = QHBoxLayout(self.ctrl_card)
        ctrl_layout.setContentsMargins(16, 10, 16, 10)
        ctrl_layout.setSpacing(10)

        self.mute_btn = PillPushButton(self.main_window.tr("btn_on"), self.ctrl_card)
        self.mute_btn.setIcon(FluentIcon.MICROPHONE)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setChecked(self.main_window.state["mic_muted"])
        self.mute_btn.clicked.connect(self.toggle_mic)

        self.deaf_btn = PillPushButton(self.main_window.tr("btn_on"), self.ctrl_card)
        self.deaf_btn.setIcon(FluentIcon.HEADPHONE)
        self.deaf_btn.setCheckable(True)
        self.deaf_btn.setChecked(self.main_window.state["deafened"])
        self.deaf_btn.clicked.connect(self.toggle_deaf)

        self.self_listen_btn = PillPushButton(self.main_window.tr("btn_self_listen_off"), self.ctrl_card)
        self.self_listen_btn.setIcon(FluentIcon.VOLUME)
        self.self_listen_btn.setCheckable(True)
        self.self_listen_btn.setChecked(self.main_window.state["self_listen"])
        self.self_listen_btn.clicked.connect(self.toggle_self_listen)
        self.self_listen_btn.setVisible(self.main_window.cfg.get("dev_mode", False))

        self.quick_soundpad_combo = ComboBox(self.ctrl_card)
        self.quick_soundpad_combo.setPlaceholderText(self.main_window.tr("soundpad_select_placeholder"))
        self.quick_soundpad_combo.currentIndexChanged.connect(self.on_quick_soundpad_selected)

        ctrl_layout.addWidget(self.mute_btn)
        ctrl_layout.addWidget(self.deaf_btn)
        ctrl_layout.addWidget(self.self_listen_btn)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.quick_soundpad_combo)

        self.layout.addWidget(self.ctrl_card)
        self.refresh_quick_soundpad()

    def refresh_quick_soundpad(self):
        self.quick_soundpad_combo.blockSignals(True)
        self.quick_soundpad_combo.clear()
        self.quick_soundpad_combo.addItem(self.main_window.tr("soundpad_select_placeholder"), userData=None)
        sp_items = load_soundpad()
        for it in sp_items:
            path_val = it.get("cached_path") or it.get("path") or it.get("orig_path")
            if path_val:
                raw_name = it["name"]
                display_name = (raw_name[:18] + '...') if len(raw_name) > 20 else raw_name
                self.quick_soundpad_combo.addItem(display_name, userData=path_val)
        self.quick_soundpad_combo.setCurrentIndex(0)
        self.quick_soundpad_combo.blockSignals(False)

    def on_quick_soundpad_selected(self, idx):
        if idx > 0:
            path = self.quick_soundpad_combo.itemData(idx)
            if path and os.path.exists(path):
                self.main_window.soundpad_interface.play_sound(path)
            self.quick_soundpad_combo.setCurrentIndex(0)

    def open_server_settings(self):
        modal = ServerSettingsModalDialog(self.main_window, self.main_window)
        if modal.exec():
            modal.validate_and_apply()
            self.check_room_status(self.room_input.text())

    def check_room_status(self, text=None):
        if text is None:
            text = self.room_input.text()

        if not self.main_window.cfg.get("server_url"):
            self.status_lbl.setText(self.main_window.tr("status_need_server"))
            self.status_lbl.setStyleSheet("color: #FFA000;")
            self.action_btn.setEnabled(False)
            return

        r_id = text.strip()
        if len(r_id) < 3:
            self.status_lbl.setText(self.main_window.tr("status_room_len_err"))
            self.status_lbl.setStyleSheet("color: #888888;")
            self.action_btn.setEnabled(False)
            return
        
        self.status_lbl.setText(self.main_window.tr("status_checking"))
        self.status_lbl.setStyleSheet("color: #888888;")
        self.action_btn.setEnabled(False)

        self.main_window.send_json_msg({
            "type": "CHECK_ROOM",
            "room": r_id
        })

    def set_room_status_ui(self, exists, reserved=False, users=None):
        r_id = self.room_input.text().strip()
        if len(r_id) < 3:
            self.action_btn.setEnabled(False)
            return

        if exists:
            self.status_lbl.setText(self.main_window.tr("status_room_exists"))
            self.status_lbl.setStyleSheet("color: #4CAF50;")
            self.action_btn.setText(self.main_window.tr("btn_enter_room"))
        else:
            self.status_lbl.setText(self.main_window.tr("status_room_free"))
            self.status_lbl.setStyleSheet("color: #888888;")
            self.action_btn.setText(self.main_window.tr("btn_create_room"))

        self.action_btn.setEnabled(True)

    def join_or_create_room(self):
        if not self.main_window.cfg.get("server_url"):
            InfoBar.warning("Warning", self.main_window.tr("server_not_configured"), duration=3500, parent=self)
            return

        name = self.name_input.text().strip()
        r_id = self.room_input.text().strip()
        pwd = self.pwd_input.text().strip()

        if not name or not r_id or not pwd:
            InfoBar.error(
                title="Error",
                content=self.main_window.tr("input_fill_err"),
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        self.action_btn.setEnabled(False)
        self.action_btn.setText(self.main_window.tr("btn_joining"))

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
            "self_listen": self.main_window.state["self_listen"],
            "reserve": (self.main_window.cfg.get("pinned_room") == r_id)
        })

    def show_active_room(self, reserved=False):
        self.action_btn.setEnabled(True)
        self.action_btn.setText(self.main_window.tr("btn_join_action"))
        self.room_heading.setText(self.main_window.tr("lobby_title").format(room=self.main_window.state['room']))
        self.chat_view.clear()
        self.known_users = {self.main_window.state["user"]}
        
        is_pinned = (self.main_window.cfg.get("pinned_room") == self.main_window.state["room"])
        self.reserve_toggle_btn.setChecked(is_pinned)
        self.reserve_toggle_btn.setText(self.main_window.tr("btn_pin_on") if is_pinned else self.main_window.tr("btn_pin_off"))
        self.leave_btn.setText(self.main_window.tr("btn_sleep") if is_pinned else self.main_window.tr("btn_leave"))

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
        self.stack.setCurrentIndex(2)
        self.refresh_quick_soundpad()
        self.main_window.notify_event("user_joined")

    def show_reserved_lobby(self, room_id, users_dict):
        self.res_title.setText(self.main_window.tr("reserved_lobby_title").format(room=room_id))
        
        while self.res_layout.count() > 1:
            item = self.res_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for u, udata in users_dict.items():
            card = SimpleCardWidget(self.res_content)
            card.setStyleSheet("background-color: rgba(255, 255, 255, 0.04); border-radius: 6px;")
            l = QHBoxLayout(card)
            l.setContentsMargins(10, 6, 10, 6)
            
            ping_val = udata.get("ping", 0)
            p_color = "#4CAF50" if ping_val < 90 else ("#FFA000" if ping_val < 180 else "#F44336")
            
            dot = CaptionLabel("●", card)
            dot.setStyleSheet(f"color: {p_color};")
            l.addWidget(dot)
            
            p_lbl = CaptionLabel(f"{ping_val}ms" if ping_val > 0 else "--ms", card)
            p_lbl.setStyleSheet(f"color: {p_color}; font-weight: bold;")
            l.addWidget(p_lbl)

            n_lbl = StrongBodyLabel(u, card)
            l.addWidget(n_lbl)
            l.addStretch()
            self.res_layout.insertWidget(self.res_layout.count() - 1, card)

        self.stack.setCurrentIndex(1)
        self.refresh_quick_soundpad()

    def wake_from_sleep(self):
        res_room = self.main_window.cfg.get("pinned_room")
        res_pwd = self.main_window.cfg.get("pinned_pwd", "")
        if res_room:
            self.name_input.setText(self.main_window.state["user"])
            self.room_input.setText(res_room)
            self.pwd_input.setText(res_pwd)
            self.join_or_create_room()

    def toggle_room_reserve(self):
        is_pinned = self.reserve_toggle_btn.isChecked()
        self.reserve_toggle_btn.setText(self.main_window.tr("btn_pin_on") if is_pinned else self.main_window.tr("btn_pin_off"))
        self.leave_btn.setText(self.main_window.tr("btn_sleep") if is_pinned else self.main_window.tr("btn_leave"))
        
        self.main_window.cfg["pinned_room"] = self.main_window.state["room"] if is_pinned else None
        self.main_window.cfg["pinned_pwd"] = self.main_window.state["password"] if is_pinned else ""
        save_config(self.main_window.cfg)

        self.main_window.send_json_msg({
            "type": "TOGGLE_RESERVE",
            "reserve": is_pinned
        })

    def toggle_mic(self):
        self.main_window.state["mic_muted"] = not self.main_window.state["mic_muted"]
        is_muted = self.main_window.state["mic_muted"]
        self.mute_btn.setChecked(is_muted)
        self.mute_btn.setText(self.main_window.tr("btn_off") if is_muted else self.main_window.tr("btn_on"))
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
        self.deaf_btn.setText(self.main_window.tr("btn_off") if is_deaf else self.main_window.tr("btn_on"))
        
        self.main_window.send_json_msg({
            "type": "UPDATE_STATE",
            "deafened": is_deaf
        })
        self.main_window.overlay.update_controls_status()
        self.update_user_state_icon(self.main_window.state["user"], self.main_window.state["mic_muted"], is_deaf)

    def toggle_self_listen(self):
        self.main_window.state["self_listen"] = not self.main_window.state["self_listen"]
        is_on = self.main_window.state["self_listen"]
        self.self_listen_btn.setText(self.main_window.tr("btn_self_listen_on") if is_on else self.main_window.tr("btn_self_listen_off"))
        
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

    def reorder_users_drag(self, src_user, dest_user):
        if src_user in self.main_window.user_order and dest_user in self.main_window.user_order:
            self.main_window.user_order.remove(src_user)
            idx = self.main_window.user_order.index(dest_user)
            self.main_window.user_order.insert(idx, src_user)
            self.update_users_list(self.main_window.last_received_users)

    def update_users_list(self, users_dict):
        self.main_window.last_received_users = users_dict
        current_users = set(users_dict.keys())
        new_comers = current_users - self.known_users
        left_users = self.known_users - current_users

        if new_comers and len(self.known_users) > 0:
            for new_u in new_comers:
                if new_u != self.main_window.state["user"]:
                    self.main_window.notify_event("user_joined")
                    self.main_window.log(f"[Room] User {new_u} joined")

        if left_users and len(self.known_users) > 0:
            for left_u in left_users:
                if left_u != self.main_window.state["user"]:
                    self.main_window.notify_event("user_left")
                    self.main_window.log(f"[Room] User {left_u} left")

        self.known_users = current_users

        ordered = [self.main_window.state["user"]]
        for u in self.main_window.user_order:
            if u in users_dict and u != self.main_window.state["user"]:
                ordered.append(u)
        for u in users_dict:
            if u not in ordered:
                ordered.append(u)
        self.main_window.user_order = ordered

        while self.users_layout.count() > 1:
            item = self.users_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.user_cards.clear()
        self.user_ping_labels.clear()
        self.user_state_icons.clear()

        for u in self.main_window.user_order:
            if u not in users_dict:
                continue
            udata = users_dict[u]
            is_me = (u == self.main_window.state["user"])
            
            user_card = DraggableUserCard(u, self, self.users_content)
            user_card.setAcceptDrops(not is_me)
            
            uc_layout = QHBoxLayout(user_card)
            uc_layout.setContentsMargins(10, 8, 12, 8)
            uc_layout.setSpacing(8)

            if not is_me:
                handle = QLabel("≡", user_card)
                handle.setFixedWidth(14)
                handle.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 16px; font-weight: bold;")
                handle.setCursor(Qt.CursorShape.SizeVerCursor)
                uc_layout.addWidget(handle)
            else:
                uc_layout.addSpacing(6)

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

            name_text = f"{u}{self.main_window.tr('you_suffix')}" if is_me else u
            name_lbl = StrongBodyLabel(name_text, user_card)
            uc_layout.addWidget(name_lbl)
            uc_layout.addStretch()

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
                b_alpha = min(1.0, 0.40 + 0.60 * alpha)
                card.setStyleSheet(f"""
                    SimpleCardWidget {{
                        border: 2px solid rgba({r}, {g}, {b}, {b_alpha:.2f});
                        border-radius: 8px;
                        background-color: rgba(255, 255, 255, 0.04);
                    }}
                """)
            else:
                card.setStyleSheet("SimpleCardWidget { border: 2px solid transparent; border-radius: 8px; background-color: rgba(255, 255, 255, 0.04); }")

    def update_user_ping_ui(self, user, ping_ms):
        if user in self.user_ping_labels:
            dot, lbl = self.user_ping_labels[user]
            color = "#4CAF50" if ping_ms < 90 else ("#FFA000" if ping_ms < 180 else "#F44336")
            dot.setStyleSheet(f"color: {color}; font-size: 13px;")
            lbl.setText(f"{ping_ms}ms")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")

    def leave_or_sleep_room(self):
        is_pinned = (self.main_window.cfg.get("pinned_room") == self.main_window.state["room"])
        self.main_window.notify_event("user_left")
        self.main_window.leave_and_cleanup()
        
        if is_pinned:
            self.show_reserved_lobby(self.main_window.cfg.get("pinned_room"), {})
        else:
            self.stack.setCurrentIndex(0)
            self.check_room_status()

class SoundpadCard(SimpleCardWidget):
    def __init__(self, idx, sound_data, soundpad_interface, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.sound_data = sound_data
        self.soundpad_interface = soundpad_interface
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        icon = IconWidget(FluentIcon.MUSIC, self)
        icon.setFixedSize(18, 18)
        layout.addWidget(icon)

        self.name_lbl = StrongBodyLabel(sound_data["name"], self)
        self.name_lbl.setMinimumWidth(80)
        layout.addWidget(self.name_lbl, 1)

        self.key_edit = KeyRecorderEdit(self)
        self.key_edit.setFixedWidth(105)
        self.key_edit.setText(sound_data.get("hotkey", ""))
        self.key_edit.keySequenceRecorded.connect(lambda k: self.soundpad_interface.on_hotkey_changed(self.idx, k))
        layout.addWidget(self.key_edit)

        cached_p = sound_data.get("cached_path") or sound_data.get("path")
        play_btn = PrimaryPushButton(self.soundpad_interface.main_window.tr("sound_play_btn"), self)
        play_btn.setIcon(FluentIcon.PLAY)
        play_btn.clicked.connect(lambda: self.soundpad_interface.play_sound(cached_p))
        layout.addWidget(play_btn)

        del_btn = ToolButton(FluentIcon.DELETE, self)
        del_btn.clicked.connect(lambda: self.soundpad_interface.delete_sound(self.idx))
        layout.addWidget(del_btn)

class SoundpadInterface(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("SoundpadInterface")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(32, 24, 32, 24)
        self.layout.setSpacing(14)
        
        self.current_playback_id = 0
        self.sounds = load_soundpad()
        self.init_ui()

    def init_ui(self):
        top = QHBoxLayout()
        self.title = SubtitleLabel(self.main_window.tr("soundpad_title"), self)
        add_btn = PrimaryPushButton(self.main_window.tr("btn_add_sound"), self)
        add_btn.setIcon(FluentIcon.ADD)
        add_btn.clicked.connect(self.add_sound_file)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(add_btn)
        self.layout.addLayout(top)

        # 1. Панель настроек громкости
        vol_card = SimpleCardWidget(self)
        v_layout = QVBoxLayout(vol_card)
        v_layout.setContentsMargins(18, 14, 18, 14)
        v_layout.setSpacing(12)

        tx_row = QHBoxLayout()
        tx_row.addWidget(BodyLabel(self.main_window.tr("soundpad_tx_vol"), vol_card))
        self.tx_vol_lbl = CaptionLabel(f"{int(self.main_window.cfg.get('soundpad_tx_vol', 1.0) * 100)}%", vol_card)
        self.tx_vol_slider = Slider(Qt.Orientation.Horizontal, vol_card)
        self.tx_vol_slider.setRange(0, 150)
        self.tx_vol_slider.setValue(int(self.main_window.cfg.get("soundpad_tx_vol", 1.0) * 100))
        self.tx_vol_slider.valueChanged.connect(self.on_tx_volume_changed)
        tx_row.addWidget(self.tx_vol_slider)
        tx_row.addWidget(self.tx_vol_lbl)
        v_layout.addLayout(tx_row)

        loc_row = QHBoxLayout()
        loc_row.addWidget(BodyLabel(self.main_window.tr("soundpad_local_vol"), vol_card))
        self.local_vol_lbl = CaptionLabel(f"{int(self.main_window.cfg.get('soundpad_local_vol', 1.0) * 100)}%", vol_card)
        self.local_vol_slider = Slider(Qt.Orientation.Horizontal, vol_card)
        self.local_vol_slider.setRange(0, 150)
        self.local_vol_slider.setValue(int(self.main_window.cfg.get("soundpad_local_vol", 1.0) * 100))
        self.local_vol_slider.valueChanged.connect(self.on_local_volume_changed)
        loc_row.addWidget(self.local_vol_slider)
        loc_row.addWidget(self.local_vol_lbl)
        v_layout.addLayout(loc_row)

        self.layout.addWidget(vol_card)

        # 2. Панель опций остановки и прерывания
        opt_card = SimpleCardWidget(self)
        opt_l = QVBoxLayout(opt_card)
        opt_l.setContentsMargins(18, 12, 18, 12)
        opt_l.setSpacing(10)

        stop_row = QHBoxLayout()
        stop_row.addWidget(BodyLabel(self.main_window.tr("soundpad_stop_hotkey"), opt_card))
        self.stop_key_edit = KeyRecorderEdit(opt_card)
        self.stop_key_edit.setText(self.main_window.cfg.get("bind_soundpad_stop", ""))
        self.stop_key_edit.keySequenceRecorded.connect(self.on_stop_hotkey_changed)
        stop_row.addWidget(self.stop_key_edit)
        
        stop_btn = PushButton(self.main_window.tr("btn_stop_sound"), opt_card)
        stop_btn.setIcon(FluentIcon.CANCEL)
        stop_btn.clicked.connect(self.stop_all_sounds)
        stop_row.addWidget(stop_btn)
        opt_l.addLayout(stop_row)

        self.interrupt_switch = SwitchButton(opt_card)
        self.interrupt_switch.setOnText(self.main_window.tr("btn_on"))
        self.interrupt_switch.setOffText(self.main_window.tr("btn_off"))
        self.interrupt_switch.setChecked(self.main_window.cfg.get("soundpad_interrupt", True))
        self.interrupt_switch.checkedChanged.connect(self.on_interrupt_toggled)
        
        sw_row = QHBoxLayout()
        sw_row.addWidget(BodyLabel(self.main_window.tr("soundpad_interrupt_switch"), opt_card))
        sw_row.addStretch()
        sw_row.addWidget(self.interrupt_switch)
        opt_l.addLayout(sw_row)

        self.layout.addWidget(opt_card)

        # 3. Список звуков
        self.scroll = ScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.cards_content = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.cards_content)
        self.layout.addWidget(self.scroll, 1)

        self.refresh_list()

    def on_tx_volume_changed(self, v):
        self.tx_vol_lbl.setText(f"{v}%")
        self.main_window.cfg["soundpad_tx_vol"] = v / 100.0
        save_config(self.main_window.cfg)

    def on_local_volume_changed(self, v):
        self.local_vol_lbl.setText(f"{v}%")
        self.main_window.cfg["soundpad_local_vol"] = v / 100.0
        save_config(self.main_window.cfg)

    def on_stop_hotkey_changed(self, combo):
        self.main_window.cfg["bind_soundpad_stop"] = combo
        save_config(self.main_window.cfg)
        self.update_soundpad_hotkeys()

    def on_interrupt_toggled(self, is_checked):
        self.main_window.cfg["soundpad_interrupt"] = is_checked
        save_config(self.main_window.cfg)

    def stop_all_sounds(self):
        self.current_playback_id += 1
        with self.main_window.audio_lock:
            self.main_window.local_soundpad_active_tracks.clear()

    def refresh_list(self):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, s in enumerate(self.sounds):
            card = SoundpadCard(i, s, self, self.cards_content)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        self.update_soundpad_hotkeys()
        self.main_window.room_interface.refresh_quick_soundpad()

    def add_sound_file(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Open Audio", "", "Audio Files (*.mp3 *.wav)")
        if not fpath:
            return

        if not (fpath.lower().endswith(".mp3") or fpath.lower().endswith(".wav")):
            InfoBar.warning("Format", "Поддерживаются только .mp3 и .wav файлы", duration=3000, parent=self)
            return

        def _bg_convert():
            cached = convert_and_cache_audio(fpath)
            if cached and os.path.exists(cached):
                name = os.path.splitext(os.path.basename(fpath))[0]
                self.sounds.append({"name": name, "orig_path": fpath, "cached_path": cached, "hotkey": ""})
                save_soundpad(self.sounds)
                QTimer.singleShot(0, self.refresh_list)
                QTimer.singleShot(0, lambda: InfoBar.success("Soundpad", f"Звук '{name}' добавлен", duration=2500, parent=self))
            else:
                QTimer.singleShot(0, lambda: InfoBar.error("Error", "Не удалось обработать аудиофайл", duration=3500, parent=self))

        threading.Thread(target=_bg_convert, daemon=True).start()

    def on_hotkey_changed(self, idx, combo):
        if idx < len(self.sounds):
            self.sounds[idx]["hotkey"] = combo
            save_soundpad(self.sounds)
            self.update_soundpad_hotkeys()

    def delete_sound(self, idx):
        if idx < len(self.sounds):
            item = self.sounds.pop(idx)
            p = item.get("cached_path")
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
            save_soundpad(self.sounds)
            self.refresh_list()

    def update_soundpad_hotkeys(self):
        sp_map = {}
        for s in self.sounds:
            p = s.get("cached_path") or s.get("path")
            if s.get("hotkey") and p:
                sp_map[f"soundpad_{p}"] = s["hotkey"]
        
        stop_key = self.main_window.cfg.get("bind_soundpad_stop", "")
        if stop_key:
            sp_map["soundpad_stop_all"] = stop_key

        self.main_window.hotkey_mgr.set_hotkeys({**self.main_window.get_system_hotkeys(), **sp_map})

    def play_sound(self, cached_wav_path):
        if not cached_wav_path or not os.path.exists(cached_wav_path):
            return
        
        if self.main_window.cfg.get("soundpad_interrupt", True):
            self.stop_all_sounds()

        self.current_playback_id += 1
        play_id = self.current_playback_id
        
        def _streamer():
            try:
                pcm_arr = read_pcm_from_cached_wav(cached_wav_path)
                if pcm_arr is None:
                    return

                tx_vol = float(self.main_window.cfg.get("soundpad_tx_vol", 1.0))
                local_vol = float(self.main_window.cfg.get("soundpad_local_vol", 1.0))

                tx_pcm = pcm_arr * tx_vol
                loc_pcm = pcm_arr * local_vol

                # 1. Загрузка в прямой локальный PortAudio / SoundDevice буфер
                chunks_to_add = []
                for j in range(0, len(loc_pcm), BLOCK_SIZE):
                    c = loc_pcm[j:j+BLOCK_SIZE]
                    if len(c) < BLOCK_SIZE:
                        c = np.pad(c, (0, BLOCK_SIZE - len(c)))
                    chunks_to_add.append(c)

                with self.main_window.audio_lock:
                    if self.main_window.cfg.get("soundpad_interrupt", True):
                        self.main_window.local_soundpad_active_tracks = [chunks_to_add]
                    else:
                        self.main_window.local_soundpad_active_tracks.append(chunks_to_add)

                # 2. Сетевая отправка PCM чанками на сервер
                if self.main_window.state["in_room"]:
                    u_bytes = self.main_window.state["user"].encode('utf-8')
                    header = bytearray([2, len(u_bytes)]) + u_bytes

                    for i in range(0, len(tx_pcm), BLOCK_SIZE):
                        if play_id != self.current_playback_id:
                            break

                        chunk = tx_pcm[i:i+BLOCK_SIZE]
                        if len(chunk) < BLOCK_SIZE:
                            chunk = np.pad(chunk, (0, BLOCK_SIZE - len(chunk)))
                        
                        self.main_window.speaker_activity[self.main_window.state["user"]] = time.time() + 0.35

                        clipped = np.clip(chunk, -1.0, 1.0)
                        pcm16 = (clipped * 32767).astype(np.int16)
                        packet = bytes(header + pcm16.tobytes())
                        
                        if self.main_window.ws_loop and self.main_window.ws_loop.is_running():
                            self.main_window.ws_loop.call_soon_threadsafe(self.main_window.out_queue.put_nowait, packet)
                        
                        time.sleep(BLOCK_SIZE / SAMPLE_RATE)
            except Exception as e:
                self.main_window.log(f"[Soundpad Streamer] {e}")

        threading.Thread(target=_streamer, daemon=True).start()

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
        self.title = SubtitleLabel(self.main_window.tr("settings_title"), self)
        self.layout.addWidget(self.title)

        self.scroll = ScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.verticalScrollBar().setSingleStep(25)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 10, 0)
        container_layout.setSpacing(16)

        # Выбор языка
        card_lang = SimpleCardWidget(container)
        clang_layout = QVBoxLayout(card_lang)
        clang_layout.setContentsMargins(20, 18, 20, 18)
        clang_layout.setSpacing(12)
        clang_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_lang"), card_lang))
        
        self.lang_combo = ComboBox(card_lang)
        self.lang_combo.addItem("Русский", userData="ru")
        self.lang_combo.addItem("English", userData="en")
        
        cur_lang = self.main_window.cfg.get("language", "ru")
        idx = 0 if cur_lang == "ru" else 1
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self.on_lang_changed)
        clang_layout.addWidget(self.lang_combo)
        container_layout.addWidget(card_lang)

        # Устройства
        card1 = SimpleCardWidget(container)
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(20, 18, 20, 18)
        c1_layout.setSpacing(12)

        c1_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_io"), card1))
        
        c1_layout.addWidget(BodyLabel(self.main_window.tr("lbl_mic"), card1))
        self.mic_combo = ComboBox(card1)
        self.mic_combo.currentTextChanged.connect(self.trigger_delayed_save)
        c1_layout.addWidget(self.mic_combo)

        c1_layout.addWidget(BodyLabel(self.main_window.tr("lbl_spk"), card1))
        self.spk_combo = ComboBox(card1)
        self.spk_combo.currentTextChanged.connect(self.trigger_delayed_save)
        c1_layout.addWidget(self.spk_combo)

        c1_layout.addWidget(BodyLabel(self.main_window.tr("lbl_mic_boost"), card1))
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

        c1_layout.addWidget(BodyLabel(self.main_window.tr("lbl_vad_gate"), card1))
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

        # Обработка звука (DSP)
        card2 = SimpleCardWidget(container)
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(20, 18, 20, 18)
        c2_layout.setSpacing(12)

        c2_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_dsp"), card2))

        self.echo_switch = SwitchButton(card2)
        self.echo_switch.setOnText(self.main_window.tr("switch_echo_on"))
        self.echo_switch.setOffText(self.main_window.tr("switch_echo_off"))
        self.echo_switch.setChecked(self.main_window.cfg.get("echo_cancellation", False))
        self.echo_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.echo_switch)

        self.noise_switch = SwitchButton(card2)
        self.noise_switch.setOnText(self.main_window.tr("switch_noise_on"))
        self.noise_switch.setOffText(self.main_window.tr("switch_noise_off"))
        self.noise_switch.setChecked(self.main_window.cfg.get("noise_suppression", False))
        self.noise_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.noise_switch)

        self.agc_switch = SwitchButton(card2)
        self.agc_switch.setOnText(self.main_window.tr("switch_agc_on"))
        self.agc_switch.setOffText(self.main_window.tr("switch_agc_off"))
        self.agc_switch.setChecked(self.main_window.cfg.get("auto_gain_control", False))
        self.agc_switch.checkedChanged.connect(self.trigger_delayed_save)
        c2_layout.addWidget(self.agc_switch)

        container_layout.addWidget(card2)

        # Эквалайзер
        card3 = SimpleCardWidget(container)
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(20, 18, 20, 18)
        c3_layout.setSpacing(12)

        c3_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_eq"), card3))
        c3_layout.addWidget(CaptionLabel(self.main_window.tr("lbl_eq_desc"), card3))
        
        self.eq_combo = ComboBox(card3)
        for preset_key in EQ_PRESETS.keys():
            self.eq_combo.addItem(self.main_window.tr(preset_key), userData=preset_key)
        
        cur_eq_key = self.main_window.cfg.get("equalizer_preset", "eq_flat")
        for i in range(self.eq_combo.count()):
            if self.eq_combo.itemData(i) == cur_eq_key:
                self.eq_combo.setCurrentIndex(i)
                break
        self.eq_combo.currentIndexChanged.connect(self.trigger_delayed_save)
        c3_layout.addWidget(self.eq_combo)

        container_layout.addWidget(card3)

        # Оверлей
        card4 = SimpleCardWidget(container)
        c4_layout = QVBoxLayout(card4)
        c4_layout.setContentsMargins(20, 18, 20, 18)
        c4_layout.setSpacing(12)

        c4_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_overlay"), card4))

        self.overlay_switch = SwitchButton(card4)
        self.overlay_switch.setOnText(self.main_window.tr("switch_overlay_on"))
        self.overlay_switch.setOffText(self.main_window.tr("switch_overlay_off"))
        self.overlay_switch.setChecked(self.main_window.cfg.get("overlay_enabled", False))
        self.overlay_switch.checkedChanged.connect(self.on_overlay_toggled)
        c4_layout.addWidget(self.overlay_switch)

        c4_layout.addWidget(BodyLabel(self.main_window.tr("lbl_overlay_mode"), card4))
        self.overlay_mode_combo = ComboBox(card4)
        for mode_key in OVERLAY_MODES:
            self.overlay_mode_combo.addItem(self.main_window.tr(mode_key), userData=mode_key)
        
        cur_mode_key = self.main_window.cfg.get("overlay_mode", "overlay_mode_none")
        for i in range(self.overlay_mode_combo.count()):
            if self.overlay_mode_combo.itemData(i) == cur_mode_key:
                self.overlay_mode_combo.setCurrentIndex(i)
                break
        self.overlay_mode_combo.currentIndexChanged.connect(self.on_overlay_mode_changed)
        c4_layout.addWidget(self.overlay_mode_combo)

        c4_layout.addWidget(BodyLabel(self.main_window.tr("lbl_overlay_icons"), card4))
        self.ov_mic_sw = SwitchButton(card4)
        self.ov_mic_sw.setOnText(self.main_window.tr("switch_ov_mic"))
        self.ov_mic_sw.setChecked(self.main_window.cfg.get("ov_icon_mic", True))
        self.ov_mic_sw.checkedChanged.connect(self.on_ov_icons_changed)
        c4_layout.addWidget(self.ov_mic_sw)

        self.ov_spk_sw = SwitchButton(card4)
        self.ov_spk_sw.setOnText(self.main_window.tr("switch_ov_spk"))
        self.ov_spk_sw.setChecked(self.main_window.cfg.get("ov_icon_spk", True))
        self.ov_spk_sw.checkedChanged.connect(self.on_ov_icons_changed)
        c4_layout.addWidget(self.ov_spk_sw)

        self.overlay_pos_container = QWidget(card4)
        pos_layout = QGridLayout(self.overlay_pos_container)
        pos_layout.setContentsMargins(0, 4, 0, 0)
        pos_layout.setSpacing(10)
        
        pos_layout.addWidget(BodyLabel(self.main_window.tr("lbl_overlay_scale")), 0, 0)
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

        pos_layout.addWidget(BodyLabel(self.main_window.tr("lbl_overlay_x")), 1, 0)
        self.overlay_x_slider = Slider(Qt.Orientation.Horizontal, self.overlay_pos_container)
        self.overlay_x_slider.setRange(0, 100)
        self.overlay_x_slider.setValue(int(self.main_window.cfg.get("overlay_x_pct", 3.0)))
        self.overlay_x_slider.valueChanged.connect(self.update_overlay_pos_live)
        self.overlay_x_slider.sliderReleased.connect(self.execute_save_settings)
        pos_layout.addWidget(self.overlay_x_slider, 1, 1)

        pos_layout.addWidget(BodyLabel(self.main_window.tr("lbl_overlay_y")), 2, 0)
        self.overlay_y_slider = Slider(Qt.Orientation.Horizontal, self.overlay_pos_container)
        self.overlay_y_slider.setRange(0, 100)
        self.overlay_y_slider.setValue(int(self.main_window.cfg.get("overlay_y_pct", 3.0)))
        self.overlay_y_slider.valueChanged.connect(self.update_overlay_pos_live)
        self.overlay_y_slider.sliderReleased.connect(self.execute_save_settings)
        pos_layout.addWidget(self.overlay_y_slider, 2, 1)

        c4_layout.addWidget(self.overlay_pos_container)
        self.overlay_pos_container.setVisible(self.overlay_switch.isChecked())

        container_layout.addWidget(card4)

        # Горячие клавиши
        card5 = SimpleCardWidget(container)
        c5_layout = QVBoxLayout(card5)
        c5_layout.setContentsMargins(20, 18, 20, 18)
        c5_layout.setSpacing(12)

        c5_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_hotkeys"), card5))

        bind_grid = QGridLayout()
        bind_grid.addWidget(BodyLabel(self.main_window.tr("lbl_hk_mic")), 0, 0)
        self.mute_bind_input = KeyRecorderEdit(card5)
        self.mute_bind_input.setText(self.main_window.cfg.get("bind_mute_mic", ""))
        self.mute_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.mute_bind_input, 0, 1)

        bind_grid.addWidget(BodyLabel(self.main_window.tr("lbl_hk_spk")), 1, 0)
        self.deaf_bind_input = KeyRecorderEdit(card5)
        self.deaf_bind_input.setText(self.main_window.cfg.get("bind_deafen", ""))
        self.deaf_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.deaf_bind_input, 1, 1)

        bind_grid.addWidget(BodyLabel(self.main_window.tr("lbl_hk_tray")), 2, 0)
        self.tray_bind_input = KeyRecorderEdit(card5)
        self.tray_bind_input.setText(self.main_window.cfg.get("bind_tray", ""))
        self.tray_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.tray_bind_input, 2, 1)

        bind_grid.addWidget(BodyLabel(self.main_window.tr("lbl_hk_overlay")), 3, 0)
        self.overlay_bind_input = KeyRecorderEdit(card5)
        self.overlay_bind_input.setText(self.main_window.cfg.get("bind_overlay", ""))
        self.overlay_bind_input.keySequenceRecorded.connect(lambda _: self.execute_save_settings())
        bind_grid.addWidget(self.overlay_bind_input, 3, 1)

        c5_layout.addLayout(bind_grid)
        container_layout.addWidget(card5)

        # Режим разработчика в самом конце
        card_dev = SimpleCardWidget(container)
        c_dev_layout = QVBoxLayout(card_dev)
        c_dev_layout.setContentsMargins(20, 18, 20, 18)
        c_dev_layout.setSpacing(12)
        c_dev_layout.addWidget(StrongBodyLabel(self.main_window.tr("group_dev"), card_dev))

        self.dev_switch = SwitchButton(card_dev)
        self.dev_switch.setOnText(self.main_window.tr("switch_dev_on"))
        self.dev_switch.setOffText(self.main_window.tr("switch_dev_off"))
        self.dev_switch.setChecked(self.main_window.cfg.get("dev_mode", False))
        self.dev_switch.checkedChanged.connect(self.on_dev_switch_toggled)
        c_dev_layout.addWidget(self.dev_switch)

        container_layout.addWidget(card_dev)

        self.scroll.setWidget(container)
        self.layout.addWidget(self.scroll)
        self.refresh_devices()

    def on_dev_switch_toggled(self, is_dev):
        self.main_window.cfg["dev_mode"] = is_dev
        save_config(self.main_window.cfg)
        self.main_window.toggle_dev_mode(is_dev)

    def on_lang_changed(self):
        selected_lang = self.lang_combo.currentData()
        if selected_lang and selected_lang != self.main_window.cfg.get("language"):
            self.main_window.cfg["language"] = selected_lang
            save_config(self.main_window.cfg)
            
            title = TRANSLATIONS.get(selected_lang, {}).get("lang_restart_title", "Language Changed")
            msg = TRANSLATIONS.get(selected_lang, {}).get("lang_restart_msg", "Please restart Wave to apply the changes.")
            
            InfoBar.info(
                title=title,
                content=msg,
                duration=4000,
                parent=self
            )

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

    def on_overlay_mode_changed(self):
        mode = self.overlay_mode_combo.currentData()
        if mode:
            self.main_window.cfg["overlay_mode"] = mode
            self.main_window.overlay.rebuild_layout_order()
            self.main_window.overlay.apply_scale_and_styles()
            self.trigger_delayed_save()

    def on_ov_icons_changed(self):
        self.main_window.cfg["ov_icon_mic"] = self.ov_mic_sw.isChecked()
        self.main_window.cfg["ov_icon_spk"] = self.ov_spk_sw.isChecked()
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

        found_mic = False
        if self.main_window.cfg.get("mic_device"):
            for i in range(self.mic_combo.count()):
                if self.mic_combo.itemText(i) == self.main_window.cfg.get("mic_device"):
                    self.mic_combo.setCurrentIndex(i)
                    found_mic = True
                    break
        if not found_mic and self.mic_combo.count() > 0:
            self.mic_combo.setCurrentIndex(0)
            self.main_window.cfg["mic_device"] = self.mic_combo.currentText()

        found_spk = False
        if self.main_window.cfg.get("speaker_device"):
            for i in range(self.spk_combo.count()):
                if self.spk_combo.itemText(i) == self.main_window.cfg.get("speaker_device"):
                    self.spk_combo.setCurrentIndex(i)
                    found_spk = True
                    break
        if not found_spk and self.spk_combo.count() > 0:
            self.spk_combo.setCurrentIndex(0)
            self.main_window.cfg["speaker_device"] = self.spk_combo.currentText()

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
        
        eq_data = self.eq_combo.currentData()
        if eq_data:
            self.main_window.cfg["equalizer_preset"] = eq_data
        
        self.main_window.cfg["overlay_enabled"] = self.overlay_switch.isChecked()
        
        mode_data = self.overlay_mode_combo.currentData()
        if mode_data:
            self.main_window.cfg["overlay_mode"] = mode_data

        self.main_window.cfg["ov_icon_mic"] = self.ov_mic_sw.isChecked()
        self.main_window.cfg["ov_icon_spk"] = self.ov_spk_sw.isChecked()

        self.main_window.cfg["overlay_scale"] = self.overlay_scale_slider.value()
        self.main_window.cfg["overlay_x_pct"] = float(self.overlay_x_slider.value())
        self.main_window.cfg["overlay_y_pct"] = float(self.overlay_y_slider.value())

        self.main_window.cfg["bind_mute_mic"] = self.mute_bind_input.text().strip()
        self.main_window.cfg["bind_deafen"] = self.deaf_bind_input.text().strip()
        self.main_window.cfg["bind_tray"] = self.tray_bind_input.text().strip()
        self.main_window.cfg["bind_overlay"] = self.overlay_bind_input.text().strip()

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
        self.title = SubtitleLabel(self.main_window.tr("logs_title"), self)
        clear_btn = PushButton(self.main_window.tr("btn_clear_logs"), self)
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
        self.title = SubtitleLabel(self.main_window.tr("info_title"), self)
        self.layout.addWidget(self.title)

        card = SimpleCardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        app_title = TitleLabel(self.main_window.tr("app_full_title"), card)
        card_layout.addWidget(app_title)

        desc = BodyLabel(self.main_window.tr("app_desc"), card)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        self.ver_lbl = CaptionLabel(self.main_window.tr("app_version"), card)
        card_layout.addWidget(self.ver_lbl)
        card_layout.addSpacing(4)

        gh_btn = PushButton(self.main_window.tr("btn_github"), card)
        gh_btn.setIcon(FluentIcon.GITHUB)
        gh_btn.clicked.connect(self.on_github_click)
        card_layout.addWidget(gh_btn)

        self.layout.addWidget(card)
        self.layout.addStretch()

    def on_github_click(self):
        QDesktopServices.openUrl(QUrl("https://github.com/yunscryy/wave"))

class MainWindow(FluentWindow):
    show_error_signal = pyqtSignal(str)
    enter_room_signal = pyqtSignal(bool)
    update_users_signal = pyqtSignal(dict)
    log_signal = pyqtSignal(str)
    chat_message_signal = pyqtSignal(str, str)
    smooth_glow_signal = pyqtSignal(str, float)
    user_ping_signal = pyqtSignal(str, int)
    room_status_signal = pyqtSignal(bool, bool, dict)

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
        self.ping_start_time = 0
        self.current_ping = 0
        self.user_order = []
        self.last_received_users = {}
        
        self.incoming_audio_queue = {}
        self.local_soundpad_active_tracks = []
        self.speaker_activity = {}
        self.speaker_glow_levels = {}
        self.last_played_audio_sample = np.zeros(BLOCK_SIZE, dtype=np.float32)
        self.noise_profile = 0.005
        self.agc_gain = 1.0
        self.vad_hold_counter = 0
        self.audio_lock = threading.Lock()

        self.input_stream = None
        self.output_stream = None
        self.stream_lock = threading.Lock()

        self.hotkey_mgr = GlobalHotkeyManager()
        self.hotkey_mgr.hotkey_triggered.connect(self.on_global_hotkey_triggered)

        self.init_window()
        self.init_tray_icon()
        self.init_overlay()
        self.init_audio_engine()
        self.init_signals()
        self.update_global_hotkeys()
        
        self.glow_timer = QTimer(self)
        self.glow_timer.timeout.connect(self.update_speaking_glow_smooth)
        self.glow_timer.start(7)

        self.ping_timer = QTimer(self)
        self.ping_timer.timeout.connect(self.send_ping_request)
        self.ping_timer.start(5000)

        self.log(f"[System] Wave Voice Client started. User: {default_user}")
        self.start_persistent_server_connection()

    def tr(self, key):
        lang = self.cfg.get("language", "ru")
        return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)

    def init_window(self):
        self.setWindowTitle("Wave")
        self.resize(760, 680)
        self.setMinimumSize(760, 680)

        setTheme(Theme.DARK)
        setThemeColor(self.accent_color)

        self.room_interface = RoomInterface(self)
        self.soundpad_interface = SoundpadInterface(self)
        self.settings_interface = SettingsInterface(self)
        self.logs_interface = LogsInterface(self)
        self.info_interface = InfoInterface(self)

        self.addSubInterface(self.room_interface, FluentIcon.CHAT, self.tr("tab_room"))
        self.addSubInterface(self.soundpad_interface, FluentIcon.MUSIC, self.tr("tab_soundpad"))
        self.addSubInterface(self.settings_interface, FluentIcon.SETTING, self.tr("tab_settings"))
        self.addSubInterface(self.logs_interface, FluentIcon.DOCUMENT, self.tr("tab_logs"))
        self.addSubInterface(self.info_interface, FluentIcon.INFO, self.tr("tab_info"))

        self.toggle_dev_mode(self.cfg.get("dev_mode", False))

        self.navigationInterface.addItem(
            routeKey="minimize_tray_action",
            icon=FluentIcon.MINIMIZE,
            text=self.tr("tray_minimize"),
            onClick=self.toggle_tray_minimize,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

    def toggle_dev_mode(self, is_dev):
        try:
            r_key = self.logs_interface.objectName()
            w = self.navigationInterface.panel.widget(r_key)
            if w:
                w.setVisible(is_dev)
        except Exception:
            pass
        if hasattr(self, "room_interface"):
            self.room_interface.self_listen_btn.setVisible(is_dev)

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
        show_action = tray_menu.addAction(self.tr("tray_show"))
        show_action.triggered.connect(self.show_from_tray)
        
        mute_action = tray_menu.addAction(self.tr("tray_toggle_mic"))
        mute_action.triggered.connect(self.room_interface.toggle_mic)

        overlay_action = tray_menu.addAction(self.tr("tray_toggle_overlay"))
        overlay_action.triggered.connect(self.toggle_overlay)

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction(self.tr("tray_quit"))
        quit_action.triggered.connect(self.close)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def toggle_tray_minimize(self):
        if self.isVisible():
            self.hide()
            self.tray_icon.showMessage(self.tr("tray_minimized_title"), self.tr("tray_minimized_msg"), QSystemTrayIcon.MessageIcon.Information, 1500)
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
        self.room_interface.action_btn.setText(self.tr("btn_join_action"))
        InfoBar.error(
            title="Error",
            content=err_msg,
            position=InfoBarPosition.TOP,
            duration=4000,
            parent=self.room_interface
        )

    def on_enter_room(self, reserved):
        self.room_interface.show_active_room(reserved=reserved)
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
                    p_arr = read_pcm_from_cached_wav(sound_file) or convert_and_cache_audio(sound_file)
                    if p_arr is not None:
                        if isinstance(p_arr, str):
                            p_arr = read_pcm_from_cached_wav(p_arr)
                        if p_arr is not None:
                            chunks = []
                            for j in range(0, len(p_arr), BLOCK_SIZE):
                                c = p_arr[j:j+BLOCK_SIZE]
                                if len(c) < BLOCK_SIZE:
                                    c = np.pad(c, (0, BLOCK_SIZE - len(c)))
                                chunks.append(c * 0.8)
                            with self.audio_lock:
                                self.local_soundpad_active_tracks.append(chunks)
                except Exception:
                    pass

        threading.Thread(target=_play, daemon=True).start()

    def get_system_hotkeys(self):
        return {
            "mute": self.cfg.get("bind_mute_mic", ""),
            "deafen": self.cfg.get("bind_deafen", ""),
            "tray": self.cfg.get("bind_tray", ""),
            "overlay": self.cfg.get("bind_overlay", "")
        }

    def update_global_hotkeys(self):
        hotkeys = self.get_system_hotkeys()
        self.hotkey_mgr.set_hotkeys(hotkeys)
        self.soundpad_interface.update_soundpad_hotkeys()

    def on_global_hotkey_triggered(self, action):
        if action == "mute":
            self.room_interface.toggle_mic()
        elif action == "deafen":
            self.room_interface.toggle_deaf()
        elif action == "tray":
            self.toggle_tray_minimize()
        elif action == "overlay":
            self.toggle_overlay()
        elif action == "soundpad_stop_all":
            self.soundpad_interface.stop_all_sounds()
        elif action.startswith("soundpad_"):
            p = action.replace("soundpad_", "")
            self.soundpad_interface.play_sound(p)

    def update_speaking_glow_smooth(self):
        now = time.time()
        active_users = set(self.speaker_activity.keys()) | set(self.speaker_glow_levels.keys())
        if not active_users:
            return

        for user in active_users:
            last_t = self.speaker_activity.get(user, 0)
            
            if user == self.state["user"] and self.state["mic_muted"]:
                is_active = False
            else:
                is_active = (now - last_t) < 0.35

            target = 1.0 if is_active else 0.0
            cur = self.speaker_glow_levels.get(user, 0.0)

            if cur < target:
                cur = min(1.0, cur + 0.08)
            elif cur > target:
                cur = max(0.0, cur - 0.04)

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

    def reconnect_websocket(self):
        if self.ws_client and self.ws_loop:
            try:
                asyncio.run_coroutine_threadsafe(self.ws_client.close(), self.ws_loop)
            except Exception:
                pass

    def start_persistent_server_connection(self):
        def _runner():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            self.out_queue = asyncio.Queue(maxsize=100)
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
                            reserved = data.get("reserved", False)
                            users = data.get("users", {})
                            self.room_status_signal.emit(exists, reserved, users)

                        elif mtype == "JOIN_OK":
                            self.state["in_room"] = True
                            reserved = data.get("reserved", False)
                            self.enter_room_signal.emit(reserved)
                            self.log(f"[Server] Authorization success in room '{data.get('room')}'")

                        elif mtype == "AUTH_ERROR":
                            self.show_error_signal.emit(data.get("msg", "Auth Error"))

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
                    if rms > 0.003:
                        self.speaker_activity[sender_name] = time.time()

                    is_me = (sender_name == self.state["user"])
                    
                    peer_cfg = self.cfg["peer_settings"].get(sender_name, {"vol": 1.0, "ducking": 0})
                    user_vol = 1.0 if is_me else peer_cfg.get("vol", 1.0)
                    if user_vol != 1.0:
                        audio_array = audio_array * user_vol

                    eq_preset_key = self.cfg.get("equalizer_preset", "eq_flat")
                    audio_array = apply_equalizer_filter(audio_array, eq_preset_key)

                    with self.audio_lock:
                        if sender_name not in self.incoming_audio_queue:
                            self.incoming_audio_queue[sender_name] = []
                        if len(self.incoming_audio_queue[sender_name]) < 8:
                            self.incoming_audio_queue[sender_name].append(audio_array)

        except websockets.exceptions.ConnectionClosed:
            pass

    async def _persistent_ws_handler(self):
        while True:
            current_target_url = self.cfg.get("server_url", DEFAULT_SERVER_URL).strip()
            if not current_target_url:
                await asyncio.sleep(2)
                continue

            try:
                self.log(f"[Server] Connecting to {current_target_url}...")
                async with websockets.connect(
                    current_target_url, 
                    open_timeout=45,
                    ping_interval=10,
                    ping_timeout=10,
                    max_size=10*1024*1024
                ) as ws:
                    self.ws_client = ws
                    self.log("[Server] Connection active!")
                    
                    self.send_ping_request()

                    res_room = self.cfg.get("pinned_room")
                    if res_room and not self.state["in_room"]:
                        self.send_json_msg({
                            "type": "CHECK_ROOM",
                            "room": res_room
                        })
                    elif self.state["in_room"] and self.state["room"]:
                        join_req = json.dumps({
                            "type": "JOIN",
                            "room": self.state["room"],
                            "user": self.state["user"],
                            "password": self.state.get("password", ""),
                            "mic_muted": self.state["mic_muted"],
                            "deafened": self.state["deafened"],
                            "self_listen": self.state["self_listen"],
                            "reserve": (res_room == self.state["room"])
                        })
                        await ws.send(join_req)

                    self.room_interface.check_room_status()

                    await asyncio.gather(
                        self._sender_task(ws),
                        self._receiver_task(ws)
                    )

            except Exception as e:
                self.ws_client = None
                self.log(f"[Server Reconnect] Retry in 3s: {e}")
                await asyncio.sleep(3)

    def leave_and_cleanup(self):
        if not self.state["room"]:
            return
        r_id = self.state["room"]
        self.state["in_room"] = False
        self.state["room"] = ""
        self.state["password"] = ""
        self.log(f"[Room] Left room {r_id}")
        
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

    def mic_audio_callback(self, indata, frames, time_info, status):
        raw_mic = indata[:, 0]
        processed_mic = self.process_microphone(raw_mic)

        rms = np.sqrt(np.mean(processed_mic**2))
        vad_gate = float(self.cfg.get("vad_threshold", 0.0))
        
        if vad_gate <= 0.001:
            is_speaking = (rms > 0.0015) and (not self.state["mic_muted"])
        else:
            if rms > vad_gate and not self.state["mic_muted"]:
                self.vad_hold_counter = 12
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

    def spk_audio_callback(self, outdata, frames, time_info, status):
        mixed_audio = np.zeros(frames, dtype=np.float32)

        # 1. Голоса участников из комнаты
        if not self.state["deafened"]:
            now = time.time()
            active_ducking_factor = 1.0
            
            for u in self.user_order:
                if u != self.state["user"] and (now - self.speaker_activity.get(u, 0)) < 0.35:
                    duck_val = self.cfg["peer_settings"].get(u, {}).get("ducking", 0)
                    if duck_val > 0:
                        active_ducking_factor = max(0.25, 1.0 - (duck_val / 100.0))
                        break

            with self.audio_lock:
                for sender, chunks in list(self.incoming_audio_queue.items()):
                    if chunks:
                        chunk = chunks.pop(0)
                        
                        is_higher = False
                        for u in self.user_order:
                            if u == sender:
                                break
                            if (now - self.speaker_activity.get(u, 0)) < 0.35 and self.cfg["peer_settings"].get(u, {}).get("ducking", 0) > 0:
                                is_higher = True
                                break

                        factor = active_ducking_factor if is_higher else 1.0
                        chunk = chunk * factor

                        if len(chunk) == frames:
                            mixed_audio += chunk
                        elif len(chunk) > frames:
                            mixed_audio += chunk[:frames]
                        else:
                            mixed_audio[:len(chunk)] += chunk

        # 2. Прямое подмешивание твоего саундпада в наушники
        with self.audio_lock:
            for track in list(self.local_soundpad_active_tracks):
                if track:
                    sp_chunk = track.pop(0)
                    if len(sp_chunk) == frames:
                        mixed_audio += sp_chunk
                    elif len(sp_chunk) > frames:
                        mixed_audio += sp_chunk[:frames]
                    else:
                        mixed_audio[:len(sp_chunk)] += sp_chunk
                else:
                    self.local_soundpad_active_tracks.remove(track)

        mixed_audio = np.clip(mixed_audio, -1.0, 1.0)
        self.last_played_audio_sample = mixed_audio.copy()
        outdata[:, 0] = mixed_audio

    def start_audio_stream(self):
        with self.stream_lock:
            if self.input_stream is not None:
                try:
                    self.input_stream.stop()
                    self.input_stream.close()
                except Exception:
                    pass
                self.input_stream = None

            if self.output_stream is not None:
                try:
                    self.output_stream.stop()
                    self.output_stream.close()
                except Exception:
                    pass
                self.output_stream = None

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

            try:
                self.input_stream = sd.InputStream(
                    device=in_idx,
                    channels=1,
                    samplerate=SAMPLE_RATE,
                    blocksize=BLOCK_SIZE,
                    callback=self.mic_audio_callback
                )
                self.input_stream.start()
                self.log(f"[Audio In] Microphone active ({SAMPLE_RATE} Hz).")
            except Exception as e:
                self.log(f"[Audio In Fallback] Re-trying default mic: {e}")
                try:
                    self.input_stream = sd.InputStream(
                        device=None,
                        channels=1,
                        samplerate=SAMPLE_RATE,
                        blocksize=BLOCK_SIZE,
                        callback=self.mic_audio_callback
                    )
                    self.input_stream.start()
                    self.log("[Audio In] Default Microphone active.")
                except Exception as ex_in:
                    self.log(f"[Audio In Critical] {ex_in}")

            try:
                self.output_stream = sd.OutputStream(
                    device=out_idx,
                    channels=1,
                    samplerate=SAMPLE_RATE,
                    blocksize=BLOCK_SIZE,
                    callback=self.spk_audio_callback
                )
                self.output_stream.start()
                self.log(f"[Audio Out] Speakers active ({SAMPLE_RATE} Hz).")
            except Exception as e:
                self.log(f"[Audio Out Fallback] Re-trying default speakers: {e}")
                try:
                    self.output_stream = sd.OutputStream(
                        device=None,
                        channels=1,
                        samplerate=SAMPLE_RATE,
                        blocksize=BLOCK_SIZE,
                        callback=self.spk_audio_callback
                    )
                    self.output_stream.start()
                    self.log("[Audio Out] Default Speakers active.")
                except Exception as ex_out:
                    self.log(f"[Audio Out Critical] {ex_out}")

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
    
    exit_code = app.exec()
    
    try:
        ctypes.windll.winmm.timeEndPeriod(1)
    except Exception:
        pass
        
    sys.exit(exit_code)