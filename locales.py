TRANSLATIONS = {
    "ru": {
        "tab_room": "Комната",
        "tab_soundpad": "Саундпад",
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
        "btn_join_action": "Подключиться",
        "btn_joining": "Вход...",
        "btn_server_setup": "Настройка сервера",
        "btn_leave": "Выйти",
        "btn_sleep": "Сон",
        "btn_wake": "Войти в комнату",
        "btn_pin_on": "Закрепить: ВКЛ",
        "btn_pin_off": "Закрепить: ВЫКЛ",
        "reserved_lobby_title": "Комната: {room}",
        "reserved_status_active": "В сети: {count}",
        "lobby_title": "Комната: {room}",
        "chat_placeholder": "Сообщение...",
        "btn_on": "ВКЛ",
        "btn_off": "ВЫКЛ",
        "btn_self_listen_on": "Слышать себя: ВКЛ",
        "btn_self_listen_off": "Слышать себя: ВЫКЛ",
        "soundpad_select_placeholder": "Саундпад",
        "you_suffix": " (Вы)",
        
        # Participant Modal
        "modal_user_title": "Участник: {user}",
        "lbl_user_vol": "Громкость участника:",
        "lbl_ducking_pct": "Приоритетное заглушение:",
        
        # Soundpad Interface
        "soundpad_title": "Саундпад",
        "soundpad_tx_vol": "Громкость в эфир:",
        "soundpad_local_vol": "Громкость у себя:",
        "soundpad_stop_hotkey": "Клавиша остановки звуков:",
        "soundpad_interrupt_switch": "Прерывать звук при запуске нового:",
        "btn_stop_sound": "Стоп",
        "btn_add_sound": "Добавить звук",
        "sound_play_btn": "Воспроизвести",
        "sound_del_btn": "Удалить",
        
        # Server Setup Modal
        "modal_server_title": "Настройка сервера",
        "modal_server_lbl": "Адрес WebSocket сервера:",
        "modal_server_inst_title": "Развёртывание:",
        "modal_server_inst": (
            "1. Скопируйте server.py на ваш VPS.\n"
            "2. pip install websockets\n"
            "3. nohup python3 server.py > server.log 2>&1 &\n"
            "4. Введите адрес подключения."
        ),
        "btn_save": "Сохранить",
        "btn_cancel": "Отмена",
        "server_saved": "Адрес сохранён. Подключение обновлено.",
        "server_prefix_err": "Адрес должен начинаться с ws:// или wss://",
        "server_not_configured": "Укажите адрес сервера.",
        "input_fill_err": "Заполните все поля!",

        # Settings Interface
        "settings_title": "Настройки звука и оверлея",
        "group_io": "Устройства ввода и вывода:",
        "lbl_mic": "Микрофон:",
        "lbl_spk": "Динамики:",
        "lbl_mic_boost": "Усиление микрофона:",
        "lbl_vad_gate": "Порог активации микрофона:",
        "group_dsp": "Обработка звука:",
        "switch_echo_on": "Эхоподавление: ВКЛ",
        "switch_echo_off": "Эхоподавление: ВЫКЛ",
        "switch_noise_on": "Шумоподавление: ВКЛ",
        "switch_noise_off": "Шумоподавление: ВЫКЛ",
        "switch_agc_on": "Автоусиление (AGC): ВКЛ",
        "switch_agc_off": "Автоусиление (AGC): ВЫКЛ",
        "group_dev": "Режим разработчика:",
        "switch_dev_on": "Режим разработчика: ВКЛ",
        "switch_dev_off": "Режим разработчика: ВЫКЛ",
        
        # EQ Presets
        "group_eq": "Эквалайзер:",
        "lbl_eq_desc": "Профиль обработки входящего голоса",
        "eq_flat": "Стандартный (Flat)",
        "eq_crisp": "Голосовой баланс (Discord Crisp)",
        "eq_warm": "Теплый радио-голос (Warm Broadcast)",
        "eq_clarity": "Игровой фокус (Gamer Clarity)",
        "eq_bass": "Бас-буст (Deep Bass)",

        # Overlay Options
        "group_overlay": "Оверлей:",
        "switch_overlay_on": "Поверх всех окон: ВКЛ",
        "switch_overlay_off": "Поверх всех окон: ВЫКЛ",
        "lbl_overlay_mode": "Режим отображения:",
        "overlay_mode_none": "Без своей панели",
        "overlay_mode_self": "Со своей панелью",
        "overlay_mode_separate": "С отдельными панелями Мик/Звук",
        "lbl_overlay_icons": "Иконки оверлея:",
        "switch_ov_mic": "Микрофон",
        "switch_ov_spk": "Наушники",
        "lbl_overlay_scale": "Масштаб:",
        "lbl_overlay_x": "Позиция X (% ширины экрана):",
        "lbl_overlay_y": "Позиция Y (% высоты экрана):",

        # Hotkeys
        "group_hotkeys": "Горячие клавиши (клик для очистки):",
        "lbl_hk_mic": "Заглушить микрофон:",
        "lbl_hk_spk": "Заглушить звук:",
        "lbl_hk_tray": "Свернуть в трей:",
        "lbl_hk_overlay": "Вкл/Выкл оверлей:",

        # Language
        "group_lang": "Язык интерфейса / Language:",
        "lang_restart_title": "Смена языка",
        "lang_restart_msg": "Перезапустите Wave для применения языка.",

        # Logs Interface
        "logs_title": "Сетевые логи и диагностика",
        "btn_clear_logs": "Очистить логи",

        # Info Interface
        "info_title": "О программе",
        "app_full_title": "Wave V1.4 Pro by yunscryy",
        "app_desc": (
            "Минималистичный голосовой клиент прямого подключения с интерфейсом Windows 11 Fluent Design.\n\n"
            "Архитектура и стек технологий:\n"
            "• Среда выполнения: Python 3.14 x64\n"
            "• Графический интерфейс: PyQt6, QFluentWidgets (Fluent Design Win11)\n"
            "• Аудио-движок: SoundDevice, NumPy (PCM16 16кГц, IIR DSP фильтры, VAD Engine, Soundpad Direct Stream)\n"
            "• Сетевой транспорт: WebSockets (Дуплексный бинарный стриминг данных)\n"
            "• Системный уровень: Win32 API Hooking (User32 / Shell32)"
        ),
        "app_version": "Версия: 1.4.8 Pro",
        "btn_github": "GitHub репозиторий"
    },
    "en": {
        "tab_room": "Room",
        "tab_soundpad": "Soundpad",
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
        "placeholder_nickname": "Nickname",
        "placeholder_room": "Room ID (e.g.: squad)",
        "placeholder_pwd": "Room Password",
        "status_enter_room": "Enter room name to check status",
        "status_room_len_err": "ID must be at least 3 characters",
        "status_checking": "Checking...",
        "status_need_server": "Please configure server address first",
        "status_room_exists": "Room exists. Enter password:",
        "status_room_free": "Room available. Set password:",
        "btn_enter_room": "Join Room",
        "btn_create_room": "Create Room",
        "btn_join_action": "Connect",
        "btn_joining": "Connecting...",
        "btn_server_setup": "Server Setup",
        "btn_leave": "Leave",
        "btn_sleep": "Sleep",
        "btn_wake": "Enter Room",
        "btn_pin_on": "Pinned: ON",
        "btn_pin_off": "Pinned: OFF",
        "reserved_lobby_title": "Room: {room}",
        "reserved_status_active": "Online: {count}",
        "lobby_title": "Room: {room}",
        "chat_placeholder": "Message...",
        "btn_on": "ON",
        "btn_off": "OFF",
        "btn_self_listen_on": "Self-listen: ON",
        "btn_self_listen_off": "Self-listen: OFF",
        "soundpad_select_placeholder": "Soundpad",
        "you_suffix": " (You)",
        
        # Participant Modal
        "modal_user_title": "Member: {user}",
        "lbl_user_vol": "Voice Volume:",
        "lbl_ducking_pct": "Priority Ducking:",
        
        # Soundpad Interface
        "soundpad_title": "Soundpad",
        "soundpad_tx_vol": "Broadcast Volume:",
        "soundpad_local_vol": "Local Volume:",
        "soundpad_stop_hotkey": "Stop sounds hotkey:",
        "soundpad_interrupt_switch": "Interrupt previous sound on new play:",
        "btn_stop_sound": "Stop",
        "btn_add_sound": "Add Sound",
        "sound_play_btn": "Play",
        "sound_del_btn": "Delete",

        # Server Setup Modal
        "modal_server_title": "Server Configuration",
        "modal_server_lbl": "WebSocket Server Address:",
        "modal_server_inst_title": "Deployment Instructions:",
        "modal_server_inst": (
            "1. Upload server.py to your VPS.\n"
            "2. pip install websockets\n"
            "3. nohup python3 server.py > server.log 2>&1 &\n"
            "4. Enter connection URL."
        ),
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "server_saved": "Server address saved.",
        "server_prefix_err": "URL must start with ws:// or wss://",
        "server_not_configured": "Specify server address.",
        "input_fill_err": "Please fill all fields!",

        # Settings Interface
        "settings_title": "Audio & Overlay Settings",
        "group_io": "Audio Devices:",
        "lbl_mic": "Microphone:",
        "lbl_spk": "Speakers:",
        "lbl_mic_boost": "Microphone Boost:",
        "lbl_vad_gate": "Activation Threshold:",
        "group_dsp": "Audio Processing:",
        "switch_echo_on": "Echo Cancellation: ON",
        "switch_echo_off": "Echo Cancellation: OFF",
        "switch_noise_on": "Noise Suppression: ON",
        "switch_noise_off": "Noise Suppression: OFF",
        "switch_agc_on": "Auto Gain Control: ON",
        "switch_agc_off": "Auto Gain Control: OFF",
        "group_dev": "Developer Mode:",
        "switch_dev_on": "Developer Mode: ON",
        "switch_dev_off": "Developer Mode: OFF",
        
        # EQ Presets
        "group_eq": "Equalizer:",
        "lbl_eq_desc": "Voice incoming processing profile",
        "eq_flat": "Standard (Flat)",
        "eq_crisp": "Voice Balance (Discord Crisp)",
        "eq_warm": "Warm Radio (Warm Broadcast)",
        "eq_clarity": "Gaming Focus (Gamer Clarity)",
        "eq_bass": "Bass Boost (Deep Bass)",

        # Overlay Options
        "group_overlay": "Overlay:",
        "switch_overlay_on": "Always-on-top: ON",
        "switch_overlay_off": "Always-on-top: OFF",
        "lbl_overlay_mode": "Display Mode:",
        "overlay_mode_none": "Without self panel",
        "overlay_mode_self": "With self panel",
        "overlay_mode_separate": "With separate Mic/Audio",
        "lbl_overlay_icons": "Overlay Icons:",
        "switch_ov_mic": "Microphone",
        "switch_ov_spk": "Headphones",
        "lbl_overlay_scale": "Scale:",
        "lbl_overlay_x": "Position X (% screen width):",
        "lbl_overlay_y": "Position Y (% screen height):",

        # Hotkeys
        "group_hotkeys": "Global Hotkeys (Click to clear):",
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
        "app_full_title": "Wave V1.4 Pro by yunscryy",
        "app_desc": (
            "Windows 11 Fluent Design voice client.\n\n"
            "Architecture & Technology Stack:\n"
            "• Runtime Environment: Python 3.14 x64\n"
            "• UI Framework: PyQt6, QFluentWidgets (Fluent Design Win11)\n"
            "• Audio DSP Engine: SoundDevice, NumPy (PCM16 16kHz, IIR DSP processing, VAD Engine, Soundpad Direct Stream)\n"
            "• Transport: WebSockets (Full-duplex binary streaming)\n"
            "• System Level: Win32 API Hooking (User32 / Shell32)"
        ),
        "app_version": "Version: 1.4.8 Pro",
        "btn_github": "GitHub Repository"
    }
}