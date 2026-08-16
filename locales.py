TRANSLATIONS = {
    "ru": {
        "tab_room": "Комната",
        "tab_settings": "Настройки",
        "tab_logs": "Логи",
        "tab_info": "Информация",
        "tray_minimize": "Свернуть в трей",
        "tray_show": "Показать Wave",
        "tray_toggle_mic": "Вкл/Выкл микрофон",
        "tray_toggle_overlay": "Вкл/Выкл оверлей",
        "tray_quit": "Закрыть Wave",
        "tray_minimized_title": "Wave",
        "tray_minimized_msg": "Приложение свернуто в трей",
        
        # Room Interface
        "auth_title": "Wave Voice",
        "auth_subtitle": "Подключение к голосовому каналу",
        "placeholder_nickname": "Ваш никнейм",
        "placeholder_room": "ID Комнаты (например: squad)",
        "placeholder_pwd": "Пароль комнаты",
        "status_enter_room": "Введите название комнаты для проверки",
        "status_room_len_err": "ID должен содержать от 3 символов",
        "status_checking": "Проверка...",
        "status_need_server": "Сначала укажите адрес сервера",
        "status_room_exists": "Комната существует. Введите пароль:",
        "status_room_free": "Комната свободна. Задайте пароль:",
        "btn_enter_room": "Войти в комнату",
        "btn_create_room": "Создать комнату",
        "btn_join_action": "Создать / Войти",
        "btn_joining": "Вход...",
        "btn_server_setup": "Настройка сервера",
        "btn_leave": "Выйти",
        "lobby_title": "Лобби: {room}",
        "chat_placeholder": "Написать сообщение...",
        "btn_on": "ВКЛ",
        "btn_off": "ВЫКЛ",
        "btn_self_listen_on": "Слышать себя: ВКЛ",
        "btn_self_listen_off": "Слышать себя: ВЫКЛ",
        "you_suffix": " (Вы)",
        
        # Server Setup Modal
        "modal_server_title": "Настройка сервера",
        "modal_server_lbl": "Адрес WebSocket сервера:",
        "modal_server_inst_title": "Инструкция по развёртыванию:",
        "modal_server_inst": (
            "1. Сохраните файл server.py на целевой сервер.\n"
            "2. Установите зависимость: pip install websockets\n"
            "3. Запустите: python server.py\n"
            "4. Введите полученный адрес подключения."
        ),
        "btn_export_server": "Экспорт server.py",
        "btn_save": "Сохранить",
        "btn_cancel": "Отмена",
        "export_success": "Файл server.py сохранён!",
        "export_error": "Не удалось сохранить: {err}",
        "server_saved": "Адрес сохранён. Подключение обновлено.",
        "server_prefix_err": "Адрес должен начинаться с ws:// или wss://",
        "server_not_configured": "Укажите адрес сервера внизу страницы.",
        "input_fill_err": "Заполните все поля!",

        # Settings Interface
        "settings_title": "Настройки звука, эквалайзера и оверлея",
        "group_io": "Устройства вывода и ввода:",
        "lbl_mic": "Микрофон:",
        "lbl_spk": "Динамики:",
        "lbl_mic_boost": "Усиление микрофона:",
        "lbl_vad_gate": "Порог срабатывания микрофона (VAD Gate):",
        "group_dsp": "Улучшенная обработка звука:",
        "switch_echo_on": "Эхоподавление (Acoustic Echo Reduction): ВКЛ",
        "switch_echo_off": "Эхоподавление: ВЫКЛ",
        "switch_noise_on": "Шумоподавление (Noise Suppression): ВКЛ",
        "switch_noise_off": "Шумоподавление: ВЫКЛ",
        "switch_agc_on": "Автоматическая регулировка усиления (Auto Gain Control): ВКЛ",
        "switch_agc_off": "Автоматическая регулировка усиления: ВЫКЛ",
        
        # EQ Presets
        "group_eq": "Встроенный эквалайзер голоса:",
        "lbl_eq_desc": "Применяется к собеседникам и при проверке своего звука",
        "eq_flat": "Стандартный (Flat)",
        "eq_crisp": "Голосовой баланс (Discord Crisp)",
        "eq_warm": "Теплый радио-голос (Warm Broadcast)",
        "eq_clarity": "Игровой фокус (Gamer Clarity)",
        "eq_bass": "Бас-буст (Deep Bass)",

        # Overlay Options
        "group_overlay": "Игровой оверлей участников:",
        "switch_overlay_on": "Показывать оверлей поверх всех окон: ВКЛ",
        "switch_overlay_off": "Оверлей: ВЫКЛ",
        "lbl_overlay_mode": "Режим отображения оверлея:",
        "overlay_mode_none": "Без своей панели",
        "overlay_mode_self": "Со своей панелью",
        "overlay_mode_separate": "С отдельными панелями Мик/Звук",
        "lbl_overlay_icons": "Иконки статуса в оверлее:",
        "overlay_icons_hide": "Скрыть иконки статуса",
        "overlay_icons_mic": "Только микрофон",
        "overlay_icons_both": "Микрофон + Звук",
        "lbl_overlay_scale": "Масштаб оверлея (%):",
        "lbl_overlay_x": "Позиция X (% ширины экрана):",
        "lbl_overlay_y": "Позиция Y (% высоты экрана):",

        # Hotkeys
        "group_hotkeys": "Глобальные горячие клавиши (Работают везде):",
        "lbl_hk_mic": "Микрофон (Mute):",
        "lbl_hk_spk": "Звук (Deafen):",
        "lbl_hk_tray": "Свернуть в трей:",
        "lbl_hk_overlay": "Вкл/Выкл оверлей:",

        # Language
        "group_lang": "Язык интерфейса / Interface Language:",
        "lang_restart_title": "Смена языка",
        "lang_restart_msg": "Перезапустите Wave для применения языка.",

        # Logs Interface
        "logs_title": "Сетевые логи и статус",
        "btn_clear_logs": "Очистить логи",

        # Info Interface
        "info_title": "О программе",
        "app_full_title": "Wave V1.3 by yunscryy",
        "app_desc": (
	    "Windows 11-style voice chat room application built\n\n"
            "Архитектура и стек технологий:\n"
            "• Клиентская среда: Python 3.14 x64\n"
            "• Графический стек: PyQt6, QFluentWidgets (Fluent Design System Win11)\n"
            "• Аудио ядро: SoundDevice, NumPy (PCM16 16kHz, IIR DSP processing, VAD Gate Engine)\n"
            "• Транспортный протокол: WebSockets (двунаправленный бинарный стриминг)\n"
            "• Системный уровень: Win32 API Hooking (User32 / Shell32)"
        ),
        "app_version": "Версия: 1.3.0 Pro Suite",
        "btn_github": "Репозиторий GitHub"
    },
    "en": {
        "tab_room": "Room",
        "tab_settings": "Settings",
        "tab_logs": "Logs",
        "tab_info": "About",
        "tray_minimize": "Minimize to tray",
        "tray_show": "Show Wave",
        "tray_toggle_mic": "Toggle Microphone",
        "tray_toggle_overlay": "Toggle Overlay",
        "tray_quit": "Exit Wave",
        "tray_minimized_title": "Wave",
        "tray_minimized_msg": "Application minimized to system tray",
        
        # Room Interface
        "auth_title": "Wave Voice",
        "auth_subtitle": "Connect to Voice Channel",
        "placeholder_nickname": "Your nickname",
        "placeholder_room": "Room ID (e.g. squad)",
        "placeholder_pwd": "Room password",
        "status_enter_room": "Enter room name to check status",
        "status_room_len_err": "ID must be at least 3 characters",
        "status_checking": "Checking...",
        "status_need_server": "Please configure server address first",
        "status_room_exists": "Room exists. Enter password:",
        "status_room_free": "Room available. Set password:",
        "btn_enter_room": "Join Room",
        "btn_create_room": "Create Room",
        "btn_join_action": "Create / Join",
        "btn_joining": "Connecting...",
        "btn_server_setup": "Server Setup",
        "btn_leave": "Leave",
        "lobby_title": "Lobby: {room}",
        "chat_placeholder": "Type a message...",
        "btn_on": "ON",
        "btn_off": "OFF",
        "btn_self_listen_on": "Self-listen: ON",
        "btn_self_listen_off": "Self-listen: OFF",
        "you_suffix": " (You)",
        
        # Server Setup Modal
        "modal_server_title": "Server Configuration",
        "modal_server_lbl": "WebSocket Server Address:",
        "modal_server_inst_title": "Deployment Instructions:",
        "modal_server_inst": (
            "1. Save server.py to your target server.\n"
            "2. Install dependency: pip install websockets\n"
            "3. Run: python server.py\n"
            "4. Enter your connection URL above."
        ),
        "btn_export_server": "Export server.py",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "export_success": "server.py saved successfully!",
        "export_error": "Save failed: {err}",
        "server_saved": "Server address saved. Connection updated.",
        "server_prefix_err": "URL must start with ws:// or wss://",
        "server_not_configured": "Specify server address at the bottom first.",
        "input_fill_err": "Please fill in all fields!",

        # Settings Interface
        "settings_title": "Audio, Equalizer & Overlay Settings",
        "group_io": "Input & Output Audio Devices:",
        "lbl_mic": "Microphone:",
        "lbl_spk": "Speakers:",
        "lbl_mic_boost": "Microphone Boost:",
        "lbl_vad_gate": "Noise Gate Threshold (VAD Gate):",
        "group_dsp": "Advanced DSP Audio Processing:",
        "switch_echo_on": "Echo Cancellation (Acoustic Echo Reduction): ON",
        "switch_echo_off": "Echo Cancellation: OFF",
        "switch_noise_on": "Noise Suppression: ON",
        "switch_noise_off": "Noise Suppression: OFF",
        "switch_agc_on": "Auto Gain Control (AGC): ON",
        "switch_agc_off": "Auto Gain Control: OFF",
        
        # EQ Presets
        "group_eq": "Integrated Voice Equalizer:",
        "lbl_eq_desc": "Applies to incoming peers and self-listening loopback",
        "eq_flat": "Standard (Flat)",
        "eq_crisp": "Voice Balance (Discord Crisp)",
        "eq_warm": "Warm Radio (Warm Broadcast)",
        "eq_clarity": "Gaming Focus (Gamer Clarity)",
        "eq_bass": "Bass Boost (Deep Bass)",

        # Overlay Options
        "group_overlay": "In-Game Participants Overlay:",
        "switch_overlay_on": "Always-on-top Overlay: ON",
        "switch_overlay_off": "Overlay: OFF",
        "lbl_overlay_mode": "Overlay Layout Mode:",
        "overlay_mode_none": "Without personal panel",
        "overlay_mode_self": "With personal panel",
        "overlay_mode_separate": "With separate Mic/Audio panels",
        "lbl_overlay_icons": "Status Icons in Overlay:",
        "overlay_icons_hide": "Hide status icons",
        "overlay_icons_mic": "Microphone only",
        "overlay_icons_both": "Microphone + Audio",
        "lbl_overlay_scale": "Overlay Scale (%):",
        "lbl_overlay_x": "Position X (% screen width):",
        "lbl_overlay_y": "Position Y (% screen height):",

        # Hotkeys
        "group_hotkeys": "Global Hotkeys (Win32 Hook):",
        "lbl_hk_mic": "Mute Microphone:",
        "lbl_hk_spk": "Deafen Audio:",
        "lbl_hk_tray": "Minimize to Tray:",
        "lbl_hk_overlay": "Toggle Overlay:",

        # Language
        "group_lang": "Interface Language / Язык интерфейса:",
        "lang_restart_title": "Language Changed",
        "lang_restart_msg": "Please restart Wave to apply the changes.",

        # Logs Interface
        "logs_title": "Network Logs & Diagnostics",
        "btn_clear_logs": "Clear Logs",

        # Info Interface
        "info_title": "About Wave",
        "app_full_title": "Wave V1.3 by yunscryy",
        "app_desc": (
	    "Windows 11-style voice chat room application built\n\n"
            "Architecture & Technology Stack:\n"
            "• Runtime Environment: Python 3.14 x64\n"
            "• UI Framework: PyQt6, QFluentWidgets (Fluent Design Win11)\n"
            "• Audio DSP Engine: SoundDevice, NumPy (PCM16 16kHz, IIR DSP processing, VAD Gate Engine)\n"
            "• Transport: WebSockets (Full-duplex binary streaming)\n"
            "• System Level: Win32 API Hooking (User32 / Shell32)"
        ),
        "app_version": "Version: 1.3.0 Pro Suite",
        "btn_github": "GitHub Repository"
    }
}