# -*- coding: utf-8 -*-
"""
Файл конфигурации для парсера Avito.
Здесь хранятся все настройки, которые можно менять без редактирования основного скрипта.
"""

# Ссылка на страницу поиска (можно заменить на любую другую категорию)
BASE_URL = "https://www.avito.ru/all/noutbuki/b_u-ASgBAgICAUTwvA2I0jQ?cd=1&d=1&f=ASgBAgECAUTwvA2I0jQCRcaaDBl7ImZyb20iOjE1MDAwLCJ0byI6MzUwMDB9nKEUFXsiZnJvbSI6MzIsInRvIjpudWxsfQ"

# Максимальное количество страниц для сбора (None = все доступные)
MAX_PAGES = None  # или, например, 5, чтобы ограничить

# Режим работы браузера: True - без окна, False - с окном (удобно для отладки)
HEADLESS = False

# User-Agent для браузера
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Размер окна браузера
VIEWPORT = {"width": 1280, "height": 800}

# Тайм-аут загрузки страницы (в миллисекундах)
TIMEOUT = 60000

# Имя выходного файла
OUTPUT_FILE = "avito_all_pages.json"

# Максимальное количество попыток решения капчи
CAPTCHA_MAX_ATTEMPTS = 5

# Задержка между страницами (в секундах) – можно задать диапазон
DELAY_BETWEEN_PAGES = (3, 6)