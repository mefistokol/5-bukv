"""
Игра «5 букв» (Bukv5) на русском языке с графическим интерфейсом (tkinter).

Правила:
  - Компьютер загадывает случайное русское слово из 5 букв.
  - У игрока 6 попыток угадать слово.
  - После каждой попытки буквы подсвечиваются:
      * жёлтый — буква стоит на своём месте (correct);
      * белый  — буква есть в слове, но не на этом месте (present);
      * серый  — буквы нет в слове (absent).
  - Введённое слово должно присутствовать в словаре (файл words_5.txt).

Зависимости: только стандартная библиотека Python (tkinter, random, os, sys).
"""

import os
import random
import sys
import tkinter as tk

# Множество допустимых русских строчных букв (без «ё» — она приводится к «е»).
_RU_LOWER = set("абвгдежзийклмнопрстуфхцчшщъыьэюя")

# Путь к файлу со словарём — рядом с самим .py-файлом, чтобы игра
# работала независимо от текущей рабочей директории, из которой её запускают.
WORDS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "words_5.txt",
)


# ---------------------------------------------------------------------------
# Загрузка словаря
# ---------------------------------------------------------------------------


def _load_words(path):
    """Загружает словарь из текстового файла.

    Формат файла: одно слово на строку, любая раскладка регистра,
    допускается буква «ё» (приводится к «е»).

    Берутся только слова, которые после нормализации:
      - имеют ровно 5 букв;
      - состоят только из русских строчных букв (см. _RU_LOWER).

    Дубликаты удаляются, результат сортируется для воспроизводимости.

    Args:
        path: путь к .txt-файлу со словами.

    Returns:
        Отсортированный список валидных слов (str, нижний регистр).

    Raises:
        SystemExit: если файл не найден или после фильтрации пуст.
    """
    try:
        # utf-8-sig корректно отбрасывает возможный BOM в начале файла.
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        sys.exit(f"Не найден файл словаря: {path}")
    except OSError as e:
        sys.exit(f"Не удалось открыть файл словаря {path}: {e}")

    words = set()
    for line in raw_lines:
        # Чистим пробелы/переводы строк, приводим к нижнему регистру, ё → е.
        w = line.strip().lower().replace("ё", "е")
        # Пропускаем слова неподходящей длины.
        if len(w) != 5:
            continue
        # Пропускаем слова с символами, не входящими в русский алфавит.
        if any(ch not in _RU_LOWER for ch in w):
            continue
        words.add(w)

    if not words:
        sys.exit(f"Файл словаря {path} пуст или не содержит подходящих слов.")

    return sorted(words)


# Загружаем словарь один раз при импорте модуля.
WORDS = _load_words(WORDS_FILE)

# Множество для O(1) проверки «есть ли такое слово в словаре».
WORDS_SET = set(WORDS)


# ---------------------------------------------------------------------------
# Цветовая палитра в стиле Т-Банка
# ---------------------------------------------------------------------------
BG = "#1B1B1B"  # основной фон приложения
CARD_BG = "#2C2C2C"  # фон карточек (оверлей результата)
CELL_EMPTY_BG = "#1B1B1B"  # фон пустой ячейки
CELL_EMPTY_BORDER = "#FFDD2D"  # обводка пустой ячейки (жёлтая)
CELL_FILLED_BORDER = "#FFE96B"  # обводка ячейки с введённой буквой
CELL_CORRECT_BG = "#FFDD2D"  # фон ячейки — буква на верном месте
CELL_PRESENT_BG = "#FFFFFF"  # фон ячейки — буква есть, но не на месте
CELL_ABSENT_BG = "#5A5A5A"  # фон ячейки — буквы нет в слове
TEXT_ON_YELLOW = "#000000"  # цвет текста на жёлтом фоне
TEXT_ON_WHITE = "#000000"  # цвет текста на белом фоне
TEXT_ON_GREY = "#FFFFFF"  # цвет текста на сером фоне
TEXT_PRIMARY = "#FFFFFF"  # основной цвет текста
TEXT_MUTED = "#9A9A9A"  # приглушённый цвет текста
KEY_BG = "#3F3F3F"  # фон клавиш по умолчанию
KEY_FG = "#FFFFFF"  # цвет букв на клавишах
KEY_ABSENT = "#2A2A2A"  # фон клавиши с отсутствующей буквой
KEY_ABSENT_FG = "#6A6A6A"  # цвет буквы на «отсутствующей» клавише
BRAND_YELLOW = "#FFDD2D"  # фирменный жёлтый цвет
BRAND_YELLOW_HOVER = "#FFE85C"  # жёлтый при наведении курсора
ACCENT_BLUE = "#428BF9"  # акцентный синий (пока не используется)
ERROR_RED = "#E74C3C"  # красный цвет для ошибок/встряски

# ---------------------------------------------------------------------------
# Состояния ячеек и клавиш
# ---------------------------------------------------------------------------
STATE_EMPTY = "empty"  # ячейка пуста / клавиша не использована
STATE_FILLED = "filled"  # ячейка заполнена (до проверки)
STATE_CORRECT = "correct"  # буква на правильном месте (жёлтый)
STATE_PRESENT = "present"  # буква есть, но не на месте (белый)
STATE_ABSENT = "absent"  # буквы нет в слове (серый)

# Приоритет состояний для клавиатуры: более высокий приоритет не может быть
# понижен (correct побеждает present, present побеждает absent и т.д.).
PRIORITY = {
    STATE_EMPTY: 0,
    STATE_ABSENT: 1,
    STATE_PRESENT: 2,
    STATE_CORRECT: 3,
}

# ---------------------------------------------------------------------------
# Раскладка экранной клавиатуры (ЙЦУКЕН), три ряда
# ---------------------------------------------------------------------------
KEYBOARD_ROWS = [
    list("йцукенгшщзхъ"),  # 12 обычных клавиш
    list("фывапролджэ"),  # 11 обычных клавиш
    ["ENTER"] + list("ячсмитьбю") + ["BACK"],  # 2 широких + 9 обычных
]

ROWS = 6  # количество попыток (строк сетки)
COLS = 5  # длина слова (столбцов)

# ---------------------------------------------------------------------------
# Геометрия: размеры ячеек, клавиш, отступы
# ---------------------------------------------------------------------------
CELL_SIZE = 60  # сторона ячейки сетки (px)
CELL_GAP = 6  # промежуток между ячейками (px)
CELL_RADIUS = 8  # радиус скругления углов ячейки (px)
GRID_PAD_X = 24  # горизонтальный отступ сетки от края Canvas
GRID_PAD_Y = 12  # вертикальный отступ сетки от края Canvas

KEY_W = 32  # ширина обычной клавиши (px)
KEY_H = 46  # высота клавиши (px)
KEY_GAP = 5  # промежуток между клавишами (px)
KEY_RADIUS = 6  # радиус скругления клавиши (px)
KEY_WIDE_W = 56  # ширина широкой клавиши (Ввод / ⌫) (px)

# ---------------------------------------------------------------------------
# Шрифты
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT_CELL = (FONT_FAMILY, 24, "bold")  # буква в ячейке
FONT_KEY = (FONT_FAMILY, 12, "bold")  # буква на клавише
FONT_KEY_WIDE = (FONT_FAMILY, 11, "bold")  # текст на широкой клавише
FONT_TITLE = (FONT_FAMILY, 14, "bold")  # заголовок (резерв)
FONT_LOGO = (FONT_FAMILY, 13, "bold")  # символы логотипа «5БУКВ»
FONT_MUTED = (FONT_FAMILY, 10)  # приглушённый текст
FONT_DIALOG_TITLE = (FONT_FAMILY, 18, "bold")  # заголовок оверлея результата
FONT_DIALOG_TEXT = (FONT_FAMILY, 12)  # текст оверлея результата
FONT_BUTTON = (FONT_FAMILY, 12, "bold")  # текст кнопки


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def _calc_keyboard_width():
    """Вычисляет ширину самого широкого ряда экранной клавиатуры (в пикселях).

    Учитывает, что клавиши ENTER и BACK имеют увеличенную ширину KEY_WIDE_W,
    а остальные — стандартную KEY_W. Между клавишами — промежуток KEY_GAP.

    Returns:
        int: максимальная ширина ряда в пикселях.
    """
    max_w = 0
    for row in KEYBOARD_ROWS:
        row_w = 0
        for k in row:
            # Широкие клавиши (Ввод / Backspace) шире обычных.
            row_w += KEY_WIDE_W if k in ("ENTER", "BACK") else KEY_W
        # Промежутки между клавишами: на 1 меньше, чем самих клавиш.
        row_w += (len(row) - 1) * KEY_GAP
        if row_w > max_w:
            max_w = row_w
    return max_w


def _decline_attempts(n):
    """Возвращает слово «попытка» в правильном падеже для числа *n*.

    Используется винительный падеж (угадано «за N попытку/попытки/попыток»).

    Правила склонения:
      - 1            → «попытку»
      - 2, 3, 4      → «попытки»
      - 5, 6, ...    → «попыток»
      (В Bukv5 n ∈ [1..6], поэтому числа вроде 11-14 не встречаются.)

    Args:
        n: число попыток (1–6).

    Returns:
        str: склонённое слово.
    """
    if n == 1:
        return "попытку"
    elif 2 <= n <= 4:
        return "попытки"
    else:
        return "попыток"


def rounded_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    """Рисует скруглённый прямоугольник на Canvas в виде сглаженного полигона.

    Координаты (x1, y1) — верхний левый угол, (x2, y2) — нижний правый.
    Параметр *r* задаёт радиус скругления.

    Дополнительные именованные аргументы (**kwargs) передаются напрямую
    в canvas.create_polygon (fill, outline, width и т.д.).

    Args:
        canvas: объект tk.Canvas.
        x1, y1, x2, y2: координаты ограничивающего прямоугольника.
        r: радиус скругления углов.
        **kwargs: параметры стиля для create_polygon.

    Returns:
        int: идентификатор созданного элемента Canvas.
    """
    # Определяем контрольные точки для кубической кривой Безье, которую
    # tkinter аппроксимирует через smooth=True. Точки перечислены по часовой
    # стрелке, начиная от верхнего левого угла.
    points = [
        x1 + r,
        y1,  # верхняя сторона (начало)
        x2 - r,
        y1,  # верхняя сторона (конец)
        x2,
        y1,  # верхний правый угол (контр. точка)
        x2,
        y1 + r,  # правая сторона (начало)
        x2,
        y2 - r,  # правая сторона (конец)
        x2,
        y2,  # нижний правый угол (контр. точка)
        x2 - r,
        y2,  # нижняя сторона (начало)
        x1 + r,
        y2,  # нижняя сторона (конец)
        x1,
        y2,  # нижний левый угол (контр. точка)
        x1,
        y2 - r,  # левая сторона (начало)
        x1,
        y1 + r,  # левая сторона (конец)
        x1,
        y1,  # верхний левый угол (контр. точка)
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


# ---------------------------------------------------------------------------
# Основной класс игры
# ---------------------------------------------------------------------------


class Bukv5Game:
    """Реализует логику и графический интерфейс игры «5 букв» (Bukv5).

    При создании экземпляра:
      1. Строит весь UI (заголовок, сетку, клавиатуру, кнопку «Играть ещё»).
      2. Привязывает обработчики клавиш.
      3. Запускает новую игру (выбирает случайное слово).
    """

    def __init__(self, root):
        """Инициализирует игру и отрисовывает интерфейс.

        Args:
            root: корневое окно tk.Tk.
        """
        self.root = root
        self.root.title("5 букв")  # заголовок окна
        self.root.configure(bg=BG)  # фон окна
        self.root.geometry("480x780")  # фиксированный размер окна
        self.root.resizable(False, False)

        # --- Состояние игры ---
        self.secret = ""  # загаданное слово (нижний регистр)
        self.current_row = 0  # текущая строка (номер попытки, 0-based)
        self.current_col = 0  # текущий столбец (позиция курсора в строке)
        self.game_over = False  # флаг завершения игры (победа или поражение)

        # Двумерный массив букв: letters[r][c] — символ в ячейке (r, c).
        self.letters = [["" for _ in range(COLS)] for _ in range(ROWS)]

        # Двумерный массив состояний ячеек: cell_states[r][c] — STATE_*.
        self.cell_states = [[STATE_EMPTY for _ in range(COLS)] for _ in range(ROWS)]

        # Canvas-идентификаторы элементов ячеек:
        #   cell_items[r][c] = (rect_id, text_id)
        # где rect_id — скруглённый прямоугольник, text_id — текст буквы.
        self.cell_items = [[None for _ in range(COLS)] for _ in range(ROWS)]

        # Словарь клавиш экранной клавиатуры:
        #   keys[key_label] = {"rect": int, "text": int, "kind": str,
        #                      "state": str, "bbox": tuple}
        # key_label — строчная буква или "ENTER"/"BACK".
        self.keys = {}

        # Ссылка на виджет-оверлей результата (победа/поражение).
        self.overlay = None

        # Строим интерфейс, привязываем клавиши, запускаем первую игру.
        self._build_ui()
        self._bind_keys()
        self.new_game()

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        """Создаёт все визуальные элементы: логотип, сетку, тост, клавиатуру, кнопку."""

        # ---- Заголовок-логотип «5БУКВ» (5 жёлтых плиток) ----
        header = tk.Frame(self.root, bg=BG, height=80)
        header.pack(fill="x", pady=(18, 4))
        header.pack_propagate(False)  # запрещаем сжатие фрейма

        # Символы логотипа, каждый рисуется на отдельной плитке.
        logo_chars = ["5", "Б", "У", "К", "В"]
        logo_tile = 30  # сторона плитки логотипа (px)
        logo_gap = 4  # промежуток между плитками (px)
        logo_w = logo_tile * 5 + logo_gap * 4  # общая ширина логотипа
        logo_canvas = tk.Canvas(
            header,
            width=logo_w,
            height=logo_tile,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        logo_canvas.pack()

        # Рисуем каждую плитку логотипа.
        for i, ch in enumerate(logo_chars):
            x = i * (logo_tile + logo_gap)
            rounded_rect(
                logo_canvas,
                x,
                0,
                x + logo_tile,
                logo_tile,
                6,
                fill=BRAND_YELLOW,
                outline=BRAND_YELLOW,
            )
            logo_canvas.create_text(
                x + logo_tile / 2,
                logo_tile / 2,
                text=ch,
                font=FONT_LOGO,
                fill="#000000",
            )

        # ---- Подпись-индикатор попыток (под логотипом) ----
        self.attempts_var = tk.StringVar(value="Попытка 1 из 6")
        self.attempts_label = tk.Label(
            self.root,
            textvariable=self.attempts_var,
            bg=BG,
            fg=TEXT_MUTED,
            font=FONT_MUTED,
        )
        self.attempts_label.pack(pady=(8, 0))

        # ---- Сетка ячеек (6 строк × 5 столбцов) ----
        grid_w = COLS * CELL_SIZE + (COLS - 1) * CELL_GAP + GRID_PAD_X * 2
        grid_h = ROWS * CELL_SIZE + (ROWS - 1) * CELL_GAP + GRID_PAD_Y * 2
        self.grid_canvas = tk.Canvas(
            self.root,
            width=grid_w,
            height=grid_h,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.grid_canvas.pack(pady=(8, 6))

        # Рисуем пустые ячейки сетки.
        for r in range(ROWS):
            for c in range(COLS):
                # Координаты ячейки.
                x1 = GRID_PAD_X + c * (CELL_SIZE + CELL_GAP)
                y1 = GRID_PAD_Y + r * (CELL_SIZE + CELL_GAP)
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                # Скруглённый прямоугольник (фон ячейки).
                rect_id = rounded_rect(
                    self.grid_canvas,
                    x1,
                    y1,
                    x2,
                    y2,
                    CELL_RADIUS,
                    fill=CELL_EMPTY_BG,
                    outline=CELL_EMPTY_BORDER,
                    width=2,
                )
                # Текстовый элемент для отображения буквы.
                text_id = self.grid_canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text="",
                    font=FONT_CELL,
                    fill=TEXT_PRIMARY,
                )
                self.cell_items[r][c] = (rect_id, text_id)

        # ---- Область для всплывающих сообщений-«тостов» ----
        self.message_frame = tk.Frame(self.root, bg=BG, height=28)
        self.message_frame.pack(fill="x", pady=(0, 4))
        self.message_frame.pack_propagate(False)

        self.message_canvas = tk.Canvas(
            self.message_frame,
            height=28,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.message_canvas.pack()
        self._message_items = None  # (rect_id, text_id) текущего тоста

        # ---- Экранная клавиатура ----
        # Рассчитываем ширину самого широкого ряда, чтобы Canvas
        # вместил все клавиши и корректно центрировал каждый ряд.
        kb_total_w = _calc_keyboard_width()
        kb_h = 3 * KEY_H + 2 * KEY_GAP + 8  # высота трёх рядов + зазоры
        self.kb_canvas = tk.Canvas(
            self.root,
            width=kb_total_w + 16,  # +16 px запас по бокам
            height=kb_h,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.kb_canvas.pack(pady=(4, 6))

        # Отрисовка клавиш; передаём полную ширину Canvas для центрирования.
        self._draw_keyboard(kb_total_w + 16)

        # ---- Кнопка «Играть ещё» (внизу окна) ----
        self.button_frame = tk.Frame(self.root, bg=BG, height=64)
        self.button_frame.pack(fill="x", pady=(4, 12))
        self.button_frame.pack_propagate(False)

        self.button_canvas = tk.Canvas(
            self.button_frame,
            width=240,
            height=52,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        self.button_canvas.pack()
        self._draw_new_game_button()

    # ------------------------------------------------------------------
    # Отрисовка клавиатуры
    # ------------------------------------------------------------------

    def _draw_keyboard(self, total_w):
        """Отрисовывает все клавиши экранной клавиатуры на kb_canvas.

        Каждый ряд центрируется горизонтально по ширине total_w.
        Для каждой клавиши создаётся скруглённый прямоугольник и текст,
        а также привязывается обработчик клика.

        Args:
            total_w: полная ширина Canvas (для центрирования рядов).
        """
        self.keys.clear()
        y = 4  # начальная вертикальная позиция первого ряда

        for row in KEYBOARD_ROWS:
            # Вычисляем ширину текущего ряда (клавиши + промежутки).
            row_w = 0
            for k in row:
                row_w += KEY_WIDE_W if k in ("ENTER", "BACK") else KEY_W
            row_w += (len(row) - 1) * KEY_GAP

            # Начальная горизонтальная позиция для центрирования ряда.
            x = (total_w - row_w) / 2

            for k in row:
                # Определяем ширину, подпись и тип клавиши.
                w = KEY_WIDE_W if k in ("ENTER", "BACK") else KEY_W
                x1, y1, x2, y2 = x, y, x + w, y + KEY_H

                if k == "ENTER":
                    label = "Ввод"  # подпись для клавиши Enter
                    font = FONT_KEY_WIDE
                    kind = "enter"
                elif k == "BACK":
                    label = "\u232b"  # символ ⌫ для Backspace
                    font = (FONT_FAMILY, 16, "bold")
                    kind = "back"
                else:
                    label = k.upper()  # русская буква в верхнем регистре
                    font = FONT_KEY
                    kind = "letter"

                # Фон клавиши (скруглённый прямоугольник).
                rect_id = rounded_rect(
                    self.kb_canvas,
                    x1,
                    y1,
                    x2,
                    y2,
                    KEY_RADIUS,
                    fill=KEY_BG,
                    outline=KEY_BG,
                )
                # Текст на клавише.
                text_id = self.kb_canvas.create_text(
                    (x1 + x2) / 2,
                    (y1 + y2) / 2,
                    text=label,
                    font=font,
                    fill=KEY_FG,
                )

                # Сохраняем описание клавиши для будущего обновления состояния.
                self.keys[k] = {
                    "rect": rect_id,
                    "text": text_id,
                    "kind": kind,
                    "state": STATE_EMPTY,
                    "bbox": (x1, y1, x2, y2),
                }

                # Привязываем обработчик клика (мышь) к клавише.
                if kind == "letter":
                    cb = lambda ch=k: self.add_letter(ch)
                elif kind == "enter":
                    cb = self.submit_guess
                else:
                    cb = self.backspace

                # Привязка ко всем графическим элементам клавиши
                # (и к прямоугольнику, и к тексту), чтобы клик работал
                # при попадании в любую часть клавиши.
                for item in (rect_id, text_id):
                    self.kb_canvas.tag_bind(
                        item,
                        "<Button-1>",
                        lambda e, f=cb: f(),
                    )

                x += w + KEY_GAP  # смещаем позицию для следующей клавиши

            y += KEY_H + KEY_GAP  # смещаем позицию для следующего ряда

    # ------------------------------------------------------------------
    # Кнопка «Играть ещё»
    # ------------------------------------------------------------------

    def _draw_new_game_button(self):
        """Рисует кнопку «Играть ещё» на button_canvas с эффектами hover."""
        c = self.button_canvas
        c.delete("all")  # очищаем Canvas перед перерисовкой
        w, h = 240, 52

        # Фон кнопки.
        self._btn_rect = rounded_rect(
            c,
            2,
            2,
            w - 2,
            h - 2,
            20,
            fill=BRAND_YELLOW,
            outline=BRAND_YELLOW,
        )
        # Текст кнопки.
        self._btn_text = c.create_text(
            w / 2,
            h / 2,
            text="Играть ещё",
            font=FONT_BUTTON,
            fill="#000000",
        )

        # Привязка клика и hover-эффектов для обоих элементов кнопки.
        for item in (self._btn_rect, self._btn_text):
            c.tag_bind(item, "<Button-1>", lambda e: self.new_game())
            # При наведении — чуть более светлый жёлтый.
            c.tag_bind(
                item,
                "<Enter>",
                lambda e: c.itemconfig(
                    self._btn_rect,
                    fill=BRAND_YELLOW_HOVER,
                    outline=BRAND_YELLOW_HOVER,
                ),
            )
            # При уходе — возвращаем стандартный жёлтый.
            c.tag_bind(
                item,
                "<Leave>",
                lambda e: c.itemconfig(
                    self._btn_rect,
                    fill=BRAND_YELLOW,
                    outline=BRAND_YELLOW,
                ),
            )

    # ------------------------------------------------------------------
    # Управление внешним видом ячейки
    # ------------------------------------------------------------------

    def _set_cell(self, r, c, letter, state, border_override=None):
        """Обновляет внешний вид ячейки (r, c): фон, обводку, текст, цвет.

        Args:
            r: номер строки (0-based).
            c: номер столбца (0-based).
            letter: символ для отображения (или "" для пустой ячейки).
            state: одно из значений STATE_* (определяет цветовую схему).
            border_override: если задан, принудительно заменяет цвет обводки
                             (используется при эффекте «встряски»).
        """
        rect_id, text_id = self.cell_items[r][c]
        self.cell_states[r][c] = state

        # Выбираем цвета в зависимости от состояния.
        if state == STATE_EMPTY:
            fill = CELL_EMPTY_BG
            border = CELL_EMPTY_BORDER
            fg = TEXT_PRIMARY
            width = 2
        elif state == STATE_FILLED:
            fill = CELL_EMPTY_BG
            border = CELL_FILLED_BORDER
            fg = TEXT_PRIMARY
            width = 3  # чуть толще обводка для заполненной ячейки
        elif state == STATE_CORRECT:
            fill = CELL_CORRECT_BG
            border = CELL_CORRECT_BG
            fg = TEXT_ON_YELLOW
            width = 1
        elif state == STATE_PRESENT:
            fill = CELL_PRESENT_BG
            border = CELL_PRESENT_BG
            fg = TEXT_ON_WHITE
            width = 1
        elif state == STATE_ABSENT:
            fill = CELL_ABSENT_BG
            border = CELL_ABSENT_BG
            fg = TEXT_ON_GREY
            width = 1
        else:
            # Неизвестное состояние — рисуем как пустую ячейку (запасной вариант).
            fill = CELL_EMPTY_BG
            border = CELL_EMPTY_BORDER
            fg = TEXT_PRIMARY
            width = 2

        # Принудительная обводка (например, красная при встряске).
        if border_override is not None:
            border = border_override

        # Обновляем фон и обводку прямоугольника.
        self.grid_canvas.itemconfig(
            rect_id,
            fill=fill,
            outline=border,
            width=width,
        )
        # Обновляем букву и её цвет.
        self.grid_canvas.itemconfig(
            text_id,
            text=letter.upper() if letter else "",
            fill=fg,
        )

    # ------------------------------------------------------------------
    # Управление состоянием клавиш экранной клавиатуры
    # ------------------------------------------------------------------

    def _set_key_state(self, key, state):
        """Обновляет визуальное состояние клавиши, если новое состояние
        имеет более высокий приоритет (correct > present > absent > empty).

        Args:
            key: строчная буква (ключ в self.keys).
            state: новое состояние STATE_*.
        """
        info = self.keys.get(key)
        if info is None:
            return
        cur = info["state"]
        # Не понижаем приоритет: если буква уже была «correct», не перекрашиваем.
        if PRIORITY.get(state, 0) <= PRIORITY.get(cur, 0):
            return
        info["state"] = state

        # Определяем цвета фона и текста по состоянию.
        if state == STATE_CORRECT:
            fill = CELL_CORRECT_BG
            fg = TEXT_ON_YELLOW
        elif state == STATE_PRESENT:
            fill = CELL_PRESENT_BG
            fg = TEXT_ON_WHITE
        elif state == STATE_ABSENT:
            fill = KEY_ABSENT
            fg = KEY_ABSENT_FG
        else:
            fill = KEY_BG
            fg = KEY_FG

        self.kb_canvas.itemconfig(info["rect"], fill=fill, outline=fill)
        self.kb_canvas.itemconfig(info["text"], fill=fg)

    def _reset_key(self, key):
        """Сбрасывает клавишу к исходному виду (серый фон, белый текст).

        Используется при начале новой игры.

        Args:
            key: строчная буква (ключ в self.keys).
        """
        info = self.keys.get(key)
        if info is None:
            return
        info["state"] = STATE_EMPTY
        self.kb_canvas.itemconfig(info["rect"], fill=KEY_BG, outline=KEY_BG)
        self.kb_canvas.itemconfig(info["text"], fill=KEY_FG)

    # ------------------------------------------------------------------
    # Сообщения / тост
    # ------------------------------------------------------------------

    def show_message(self, text, color=TEXT_PRIMARY, bg=CARD_BG):
        """Показывает всплывающее сообщение-«тост» под сеткой.

        Рисуется как скруглённый прямоугольник с текстом внутри.

        Args:
            text: текст сообщения.
            color: цвет текста.
            bg: цвет фона плашки.
        """
        c = self.message_canvas
        c.delete("all")  # убираем предыдущее сообщение
        if not text:
            return
        # Приблизительная ширина плашки: 12 px на символ + 40 px запас.
        width = max(120, 12 * len(text) + 40)
        height = 24
        c.configure(width=width, height=height)
        rounded_rect(c, 0, 0, width, height, 10, fill=bg, outline=bg)
        c.create_text(
            width / 2,
            height / 2,
            text=text,
            font=(FONT_FAMILY, 11, "bold"),
            fill=color,
        )

    def clear_message(self):
        """Убирает текущее всплывающее сообщение."""
        self.message_canvas.delete("all")

    # ------------------------------------------------------------------
    # Привязки физической клавиатуры
    # ------------------------------------------------------------------

    def _bind_keys(self):
        """Привязывает обработчики нажатий физической клавиатуры.

        - Любая русская буква → add_letter.
        - Enter → submit_guess.
        - Backspace → backspace.
        """
        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Return>", lambda e: self.submit_guess())
        self.root.bind("<BackSpace>", lambda e: self.backspace())

    def _on_key(self, event):
        """Обработчик нажатия произвольной клавиши.

        Фильтрует только русские буквы; Enter и Backspace обрабатываются
        отдельными привязками выше.
        """
        if self.game_over:
            return
        ch = event.char
        if not ch:
            return
        ch = ch.lower()
        # Буква «ё» приводится к «е» для единообразия.
        if ch == "ё":
            ch = "е"
        if ch in _RU_LOWER:
            self.add_letter(ch)

    # ------------------------------------------------------------------
    # Игровая логика
    # ------------------------------------------------------------------

    def new_game(self):
        """Запускает новую игру: выбирает случайное слово и сбрасывает состояние."""
        self.secret = random.choice(WORDS)  # загаданное слово
        self.current_row = 0
        self.current_col = 0
        self.game_over = False
        self.clear_message()
        self._hide_overlay()  # убираем оверлей результата, если был

        # Сбрасываем все ячейки сетки.
        for r in range(ROWS):
            for c in range(COLS):
                self.letters[r][c] = ""
                self._set_cell(r, c, "", STATE_EMPTY)

        # Сбрасываем все буквенные клавиши клавиатуры.
        for k in self.keys:
            if self.keys[k]["kind"] == "letter":
                self._reset_key(k)

        self._update_attempts()

    def _update_attempts(self):
        """Обновляет надпись с номером текущей попытки."""
        if self.game_over:
            return
        self.attempts_var.set(f"Попытка {self.current_row + 1} из {ROWS}")

    def add_letter(self, ch):
        """Добавляет букву в текущую позицию.

        Если строка уже заполнена (5 букв), нажатие игнорируется.

        Args:
            ch: строчная русская буква.
        """
        if self.game_over:
            return
        if self.current_col >= COLS:
            return  # строка заполнена, больше букв не вмещается
        ch = ch.lower()
        if ch == "ё":
            ch = "е"
        if ch not in _RU_LOWER:
            return
        # Записываем букву в модель и обновляем ячейку.
        self.letters[self.current_row][self.current_col] = ch
        self._set_cell(self.current_row, self.current_col, ch, STATE_FILLED)
        self.current_col += 1
        self.clear_message()

    def backspace(self):
        """Удаляет последнюю введённую букву в текущей строке."""
        if self.game_over:
            return
        if self.current_col == 0:
            return  # нечего удалять
        self.current_col -= 1
        self.letters[self.current_row][self.current_col] = ""
        self._set_cell(self.current_row, self.current_col, "", STATE_EMPTY)
        self.clear_message()

    def submit_guess(self):
        """Проверяет введённое слово и применяет раскраску.

        Порядок проверок:
          1. Всё ли 5 букв введены?
          2. Есть ли слово в словаре?
          3. Раскрашиваем ячейки и клавиши.
          4. Проверяем, угадано ли слово (победа) или попытки закончились
             (поражение).
        """
        if self.game_over:
            return

        # --- Проверка 1: введены ли все 5 букв ---
        if self.current_col != COLS:
            self.shake_row(self.current_row)
            self.show_message("Нужно ровно 5 букв", color="#FFFFFF", bg="#3A2222")
            return

        guess = "".join(self.letters[self.current_row])

        # --- Проверка 2: есть ли слово в словаре ---
        # Если слова нет — попытка НЕ засчитывается: ячейки остаются
        # заполненными, игрок может стереть буквы и попробовать другое слово.
        if guess not in WORDS_SET:
            self.shake_row(self.current_row)
            self.show_message(
                "Нет такого слова в словаре",
                color="#FFFFFF",
                bg="#3A2222",
            )
            return

        # --- Проверка 3: раскраска букв ---
        self.color_row(self.current_row, guess)

        # --- Проверка 4: победа? ---
        if guess == self.secret:
            self.game_over = True
            attempts = self.current_row + 1
            word_form = _decline_attempts(attempts)
            self.attempts_var.set(f"Угадано за {attempts} {word_form}")
            # Показываем оверлей победы с небольшой задержкой (280 мс),
            # чтобы игрок успел увидеть раскраску последней строки.
            self.root.after(
                280,
                lambda: self._show_result_overlay(
                    title="Победа!",
                    subtitle=f"Слово «{self.secret.upper()}» угадано "
                    f"за {attempts} {word_form}",
                    accent=BRAND_YELLOW,
                ),
            )
            return

        # --- Переход к следующей попытке ---
        self.current_row += 1
        self.current_col = 0

        # --- Проверка 5: попытки кончились — поражение ---
        if self.current_row >= ROWS:
            self.game_over = True
            self.attempts_var.set("Игра окончена")
            self.root.after(
                280,
                lambda: self._show_result_overlay(
                    title="Поражение",
                    subtitle=f"Загаданное слово: «{self.secret.upper()}»",
                    accent=ERROR_RED,
                ),
            )
        else:
            self._update_attempts()

    # ------------------------------------------------------------------
    # Раскраска строки (двухпроходный алгоритм Bukv5)
    # ------------------------------------------------------------------

    def color_row(self, row, guess):
        """Раскрашивает ячейки строки и обновляет клавиатуру.

        Алгоритм Bukv5 с корректной обработкой повторяющихся букв:
          Проход 1 — помечаем точные совпадения (correct), «расходуя» букву
                     из загаданного слова (ставим None).
          Проход 2 — для оставшихся ячеек ищем неиспользованные совпадения
                     (present), тоже «расходуя» букву.

        Args:
            row: номер строки (0-based).
            guess: введённое слово (5 символов, нижний регистр).
        """
        # Копируем буквы загаданного слова, чтобы «расходовать» их.
        secret_chars = list(self.secret)
        result = [STATE_ABSENT] * COLS  # по умолчанию все — absent

        # Проход 1: точные совпадения (correct).
        for i in range(COLS):
            if guess[i] == secret_chars[i]:
                result[i] = STATE_CORRECT
                secret_chars[i] = None  # буква использована

        # Проход 2: присутствующие, но не на своём месте (present).
        for i in range(COLS):
            if result[i] == STATE_CORRECT:
                continue  # эта позиция уже обработана
            ch = guess[i]
            if ch in secret_chars:
                result[i] = STATE_PRESENT
                # Расходуем первое вхождение этой буквы.
                secret_chars[secret_chars.index(ch)] = None

        # Применяем результат к ячейкам и клавиатуре.
        for i in range(COLS):
            self._set_cell(row, i, guess[i], result[i])
            self._set_key_state(guess[i], result[i])

    # ------------------------------------------------------------------
    # Эффект «встряски» — мерцание красной обводкой
    # ------------------------------------------------------------------

    def shake_row(self, row):
        """Визуальный эффект ошибки: кратковременная красная обводка ячеек.

        Обводка возвращается к нормальной через 260 мс.

        Args:
            row: номер строки.
        """
        for c in range(COLS):
            letter = self.letters[row][c]
            state = self.cell_states[row][c]
            # Устанавливаем красную обводку поверх текущего состояния.
            self._set_cell(row, c, letter, state, border_override=ERROR_RED)
        # Через 260 мс убираем красную обводку.
        self.root.after(260, lambda: self._reset_shake(row))

    def _reset_shake(self, row):
        """Возвращает обводку ячеек строки к нормальному виду после shake.

        Args:
            row: номер строки.
        """
        for c in range(COLS):
            letter = self.letters[row][c]
            state = self.cell_states[row][c]
            self._set_cell(row, c, letter, state)

    # ------------------------------------------------------------------
    # Оверлей результата (победа / поражение)
    # ------------------------------------------------------------------

    def _show_result_overlay(self, title, subtitle, accent=BRAND_YELLOW):
        """Показывает карточку с результатом игры поверх основного UI.

        Содержит заголовок, подзаголовок и кнопку «Играть ещё».

        Args:
            title: текст заголовка («Победа!» / «Поражение»).
            subtitle: дополнительный текст (слово, количество попыток).
            accent: цвет акцентной полоски сверху карточки.
        """
        self._hide_overlay()  # на случай, если предыдущий оверлей остался

        # Полупрозрачную подложку tkinter не поддерживает нативно,
        # поэтому рисуем плотную карточку по центру окна.
        overlay = tk.Frame(self.root, bg=BG)
        overlay.place(relx=0.5, rely=0.5, anchor="center", width=380, height=240)

        card = tk.Canvas(
            overlay,
            width=380,
            height=240,
            bg=BG,
            highlightthickness=0,
            bd=0,
        )
        card.pack()

        # Фон карточки.
        rounded_rect(card, 4, 4, 376, 236, 16, fill=CARD_BG, outline=CARD_BG)
        # Акцентная полоска сверху (жёлтая при победе, красная при поражении).
        rounded_rect(card, 4, 4, 376, 14, 8, fill=accent, outline=accent)

        # Текст заголовка и подзаголовка.
        card.create_text(190, 70, text=title, font=FONT_DIALOG_TITLE, fill=TEXT_PRIMARY)
        card.create_text(
            190, 110, text=subtitle, font=FONT_DIALOG_TEXT, fill=TEXT_MUTED
        )

        # ---- Кнопка «Играть ещё» внутри карточки ----
        btn_w, btn_h = 220, 48
        bx1 = (380 - btn_w) / 2
        by1 = 165
        bx2 = bx1 + btn_w
        by2 = by1 + btn_h
        btn_rect = rounded_rect(
            card,
            bx1,
            by1,
            bx2,
            by2,
            20,
            fill=BRAND_YELLOW,
            outline=BRAND_YELLOW,
        )
        btn_text = card.create_text(
            (bx1 + bx2) / 2,
            (by1 + by2) / 2,
            text="Играть ещё",
            font=FONT_BUTTON,
            fill="#000000",
        )

        # Привязка клика и hover-эффекта к кнопке карточки.
        for item in (btn_rect, btn_text):
            card.tag_bind(item, "<Button-1>", lambda e: self.new_game())
            card.tag_bind(
                item,
                "<Enter>",
                lambda e: card.itemconfig(
                    btn_rect,
                    fill=BRAND_YELLOW_HOVER,
                    outline=BRAND_YELLOW_HOVER,
                ),
            )
            card.tag_bind(
                item,
                "<Leave>",
                lambda e: card.itemconfig(
                    btn_rect,
                    fill=BRAND_YELLOW,
                    outline=BRAND_YELLOW,
                ),
            )

        self.overlay = overlay

    def _hide_overlay(self):
        """Уничтожает оверлей результата, если он существует."""
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------


def main():
    """Создаёт главное окно Tk и запускает игровой цикл."""
    root = tk.Tk()
    Bukv5Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()
