import sys
from collections import Counter

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QPixmap, QKeyEvent
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, \
    QDesktopWidget, QFileDialog
from skimage import img_as_ubyte
from skimage.io import imread, imsave

from CV.exceptions import CutException
from CV.scan import cut_by_external_contour, cut_by_internal_contour
from ML.exceptions import ClfNotFoundException, ScNotFoundException, \
    DimRedNotFoundException
from ML.letter_recognition import image_to_board
from assistant.hint import get_board_with_hints, get_hint_value_coord
from assistant.scrabble_assistant import LETTERS_AMOUNT
from assistant.scrabble_assistant import get_used_letters, get_n_hints
# from assistant.scrabble_assistant import is_board_letters_amount_right
from assistant.postprocessing import full_postprocessing
from preprocessing.model import CLASSIFIER_DUMP_PATH, DIMRED_DUMP_PATH, \
    SCALER_DUMP_PATH


# authors: Pavel, Mikhail
class ScrabbleApplication(QWidget):
    """
    Application of scrabble-assistant
    Using PyQT5 version 5.14.2
    """

    # настраиваемые параметры
    _hints_amount = 3  # сколько подсказок выдавать
    _asterisk_active = False  # возможность выбрать кроме букв еще и *
    _console_output = True  # возможность выводить данные в консоль

    _chips_varieties = 0  # кол-во разновидностей фишек

    # доска в виде двумерного символьного массива
    _board = None

    _width = 0  # 450 px для 1920
    _height = 0  # 805 px для 1080

    _chip_size = 0  # размер кнопки с буквой в px
    _row_size = 0  # длина линии кнопок в px

    # css цвета для вывода ценностей подсказок
    _colors = ['rgba(25, 114, 32, 200)',   # зелёный
               'rgba(20, 140, 150, 200)',  # голубой
               'rgba(129, 125, 0, 200)',  # жёлтый
               'rgba(49, 30, 100, 200)',  # фиолетовый
               'rgba(200, 30, 140, 200)']  # розовый

    # пути к папкам с фишками разных цветов
    # фишки используются для вывода подсказок на доске
    _chips_folders_paths = [
        'resources/app_images/chips/green/',
        'resources/app_images/chips/light_blue/',
        'resources/app_images/chips/yellow/',
        'resources/app_images/chips/violet/',
        'resources/app_images/chips/pink/'
    ]

    # путь к css
    _stylesheet_path = 'resources/stylesheet/app.css'

    # пути к иконкам
    _app_icon_path = 'resources/app_images/icon.png'  # иконка приложения
    _upload_img_icon_path = 'resources/app_images/button_icons/upload.png'
    _drop_img_icon_path = 'resources/app_images/button_icons/refresh.png'
    _start_icon_path = 'resources/app_images/button_icons/search.png'

    # словари с буквами
    _used_letters = dict()  # словарь с кол-вом букв, которые уже есть на доске
    _chosen_letters = dict()  # словарь с буквами, которые выбрал юзер

    # кнопки
    _letters_buttons = []  # массив кнопок с буквами 'А'-'Я' и '*'
    _letters_on_buttons = []  # массив букв к кнопкам
    _chosen_chips_buttons = []  # массив кнопок выбранных букв
    _empty_buttons = []  # Кнопки-заглушки
    _drop_button = None  # кнопка 'сбросить счетчик букв'
    _upload_img_button = None  # кнопка 'сделать фото' / 'загрузить картинку'
    _start_button = None  # кнопка по нажатии запускает весь алгоритм

    # labels
    _msg_label = None
    _msg_start = 'Загрузите изображение'
    _msg_image_uploaded = 'Выберите фишки'
    _msg_got_hint = 'Подсказки отображены на доске'
    _msg_no_hints = 'Ни одной подсказки не найдено'
    _msg_too_many_letters_error = 'Кол-во букв на доске превышает допустимое'
    _msg_max_chips_error = 'Вы набрали максимум фишек'
    _msg_max_chip_error = 'В игре больше нет фишек с буквой '
    _msg_max_chip_aster_error = 'В игре больше нет фишек со звёздочкой'
    _msg_no_chips_error = 'Вы не выбрали ни одной фишки'
    _msg_no_img_error = 'Вы не загрузили изображение'
    _msg_scan_error = 'Доска не распознана, попробуйте другое фото'
    _msg_clf_dump_error = 'Не найден дамп классификатора ' + \
                          f'в {CLASSIFIER_DUMP_PATH}'
    _msg_clf_error = 'Ошибка классификатора'
    _msg_dec_dump_error = f'Не найден дамп декомпозера в {DIMRED_DUMP_PATH}'
    _msg_sc_dump_error = f'Не найден дамп шкалировщика в {SCALER_DUMP_PATH}'
    _msg_unknown_recognition_error = 'Неизвестная ошибка распознавания'

    _img_label = None  # label для изображения доски
    _board_img = None  # обрезанное изображение доски

    _hints_labels = []  # фишки подсказок, отображаемые на экране
    _got_hints = False  # получена ли подсказка

    def __init__(self):
        """
        Инициализация приложения
        """
        # Считывание файла разметки и внешнего шрифта
        super().__init__(flags=Qt.Widget)
        f = open(self._stylesheet_path, 'r')
        self.styleData = f.read()
        f.close()
        self.init_buttons()
        self.init_labels()
        self.init_ui()
        self.draw_widgets()

    def init_ui(self):
        """
        Инициализация интерфейса
        """

        # Подгрузка файла разметки
        self.setStyleSheet(self.styleData)
        # Параметры окна
        size = QDesktopWidget().screenGeometry(-1)
        width = size.width()
        height = size.height()

        # если ширина экрана менее 1920, то уменьшаем окно
        k = 0.8 if width < 1920 else 1

        # размеры окна
        self._width = 450 * k  # 450 px для 1920
        self._height = 805 * k  # 805 px для 1080
        # размер кнопки с буквой в px
        self._chip_size = self._width // 9
        # длина линии кнопок в px
        self._row_size = self._chip_size * (self._width // self._chip_size)

        self.setGeometry((width - self._width) // 2,
                         (height - self._height) // 2,
                         self._width, self._height)
        self.setMaximumSize(self._width, self._height)
        self.setMinimumSize(self._width, self._height)
        self.setWindowTitle('Эрудит')
        self.setWindowIcon(QIcon(self._app_icon_path))
        self.show()

    def init_dicts(self):
        """
        Инициализация словарей
        """

        # словарь с выбранными буквами
        self._chosen_letters = {'а': 0, 'б': 0, 'в': 0, 'г': 0, 'д': 0, 'е': 0,
                                'ж': 0, 'з': 0, 'и': 0, 'й': 0, 'к': 0, 'л': 0,
                                'м': 0, 'н': 0, 'о': 0, 'п': 0, 'р': 0, 'с': 0,
                                'т': 0, 'у': 0, 'ф': 0, 'х': 0, 'ц': 0, 'ч': 0,
                                'ш': 0, 'щ': 0, 'ъ': 0, 'ы': 0, 'ь': 0, 'э': 0,
                                'ю': 0, 'я': 0, '*': 0}
        # словарь с буквами, которые уже есть на доске
        self._used_letters = get_used_letters(self._board)

    def init_buttons(self):
        """
        Инициализация кнопок
        """

        # кнопка загрузки изображения
        btn = QPushButton(self)
        btn.setText(' Открыть')
        btn.setIcon(QIcon(self._upload_img_icon_path))
        btn.setIconSize(QSize(20, 20))
        btn.clicked.connect(self.image_uploaded)
        self._upload_img_button = btn

        # кнопка старта алгоритма
        start_btn = QPushButton(self)
        start_btn.setDisabled(True)
        start_btn.setIcon(QIcon(self._start_icon_path))
        start_btn.setIconSize(QSize(20, 20))
        start_btn.setText(' Найти')
        start_btn.clicked.connect(self.start_btn_pressed)
        self._start_button = start_btn

        # кнопки выбранных фишек
        self._chosen_chips_buttons = []
        for i in range(7):
            btn = QPushButton(self)
            btn.setObjectName("chosen_letters")
            btn.setDisabled(True)
            self._chosen_chips_buttons.append(btn)

        # расчет кол-ва разновидностей фишек
        # со звездочкой 33, без нее 32
        if self._asterisk_active:
            self._chips_varieties = 33
        else:
            self._chips_varieties = 32

        # кнопки с фишками-буквами
        self._letters_buttons = []
        self._letters_on_buttons = []
        for i in range(self._chips_varieties):
            if i == 32:
                letter_on_button = '*'
            else:
                letter_on_button = chr(1072 + i)
            self._letters_on_buttons.append(letter_on_button)
            btn = QPushButton(self)
            btn.setObjectName("letters")
            btn.setText(self._letters_on_buttons[i].upper())
            btn.setDisabled(True)
            btn.clicked.connect(self.letter_btn_pressed)
            self._letters_buttons.append(btn)

        # пустые кнопки в конце клавиатуры
        for i in range(36 - self._chips_varieties):
            btn = QPushButton(self)
            btn.setObjectName("letters")
            btn.setDisabled(True)
            self._empty_buttons.append(btn)

        # кнопка сброса счетчика
        drop_button = QPushButton(self)
        drop_button.setDisabled(True)
        drop_button.setIcon(QIcon(self._drop_img_icon_path))
        drop_button.setIconSize(QSize(20, 20))
        drop_button.setObjectName("drop")
        drop_button.clicked.connect(self.drop_btn_pressed)
        self._drop_button = drop_button

    def init_labels(self):
        """
        Инициализация labels
        """

        # img label
        label = QLabel(self)
        self._img_label = label

        # hint labels
        for i in range(225):
            label = QLabel(self)
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName('image')
            label.setText('')
            self._hints_labels.append(label)

        # msg label
        label = QLabel(self)
        label.setText(self._msg_start)
        label.setAlignment(Qt.AlignCenter)  # выровнять текст по центру
        self._msg_label = label

    def image_uploaded(self):
        """
        Проверка загруженного изображения и его показ на экране
        """

        fd = QFileDialog()  # диалоговое окно для выбора файла
        option = fd.Options()  # стандартный выбор файла
        img_path = fd.getOpenFileName(self, caption="Выбор изображения",
                                      filter="Image files (*.jpg)",
                                      options=option)[0]

        # если изображение так и не было выбрано - выходим из функции
        if not img_path:
            return

        # обработка изображения
        try:
            img = img_as_ubyte(imread(img_path))  # считывание
            # обрезка по внешнему контуру
            img = img_as_ubyte(cut_by_external_contour(img))
            # обрезка по внутреннему контуру
            img_squared = img_as_ubyte(cut_by_internal_contour(img))

        except (CutException, AttributeError, ValueError):
            self._img_label.setPixmap(QPixmap())  # убираем изображение доски
            self.clear_hint()
            self._msg_label.setText(self._msg_scan_error)  # error msg
            # блокировка кнопок
            for i in range(self._chips_varieties):
                self._letters_buttons[i].setDisabled(True)
            self._drop_button.setDisabled(True)
            self._start_button.setDisabled(True)
            return

        # распознавание символов на доске
        try:
            board = image_to_board(img_squared, CLASSIFIER_DUMP_PATH)

            if self._console_output:
                print('Результат: ')
                for row in board:
                    print('|', end='')
                    for i in range(len(row)):
                        if row[i] == '':
                            print(' ', end='|')
                        else:
                            print(row[i], end='|')
                    print()
                print()

        except ClfNotFoundException:
            self._msg_label.setText(self._msg_clf_dump_error)
            return

        except DimRedNotFoundException:
            self._msg_label.setText(self._msg_dec_dump_error)
            return

        except ScNotFoundException:
            self._msg_label.setText(self._msg_sc_dump_error)
            return

        except ValueError:
            self._msg_label.setText(self._msg_clf_error)
            return

        except TypeError:
            self._msg_label.setText(self._msg_unknown_recognition_error)
            return

        # постобработка доски
        board = full_postprocessing(board)

        self._board = board

        if self._console_output:
            print('Постобработка: ')
            for row in board:
                print('|', end='')
                for i in range(len(row)):
                    if row[i] == '':
                        print(' ', end='|')
                    else:
                        print(row[i], end='|')
                print()

        # записываем изображение
        imsave('resources/app_images/user_image.jpg', img_squared)

        # считываем изображение
        img = QPixmap('resources/app_images/user_image.jpg')
        # уменьшаем до размеров экрана
        img = img.scaled(self._width, self._width)

        # сохраняем
        self._board_img = img
        self._img_label.setPixmap(self._board_img)

        # если кол-во всех букв на доске не больше допустимого
        # if is_board_letters_amount_right(self._board):

        # Разблокировка кнопок
        self._start_button.setDisabled(False)
        for i in range(self._chips_varieties):
            self._letters_buttons[i].setDisabled(False)
        self._drop_button.setDisabled(False)

        self.init_dicts()  # инициализируем словари
        self._msg_label.setText(self._msg_image_uploaded)
        self.clear_widgets()
        # else:
        #     # если превышено кол-во хоть одной из букв
        #     self._msg_label.setText(self._msg_too_many_letters_error)

    def clear_widgets(self):
        """
        Обновление всех виджетов
        """

        # повторная инициализация словарей
        self.init_dicts()
        # обновляем кнопки
        self.update_buttons()
        # сбрасываем msg
        self._msg_label.setText(self._msg_image_uploaded)

        # сбрасываем все выбранные фишки
        for i in range(7):
            btn = self._chosen_chips_buttons[i]
            btn.setText("")
            self._chosen_chips_buttons[i] = btn
        # сбрасываем фон номеров подсказок
        for i in range(225):
            self._hints_labels[i].setStyleSheet('background-color: None;')

        # очистка подсказки
        self.clear_hint()

    def clear_hint(self):
        """
        Удаление подсказки с экрана
        """

        for label in self._hints_labels:
            label.setPixmap(QPixmap())
            label.setText('')

    def update_buttons(self):
        """
        Обновляет все кнопки-фишки, при необходимости меняя их цвет
        """
        # идем по всем кнопкам с буквами
        for i in range(len(self._letters_buttons)):
            # получаем букву, расположенную на кнопке
            letter = self._letters_on_buttons[i]

            # если фишку можно взять, то она синяя, если нельзя - красная
            # далее проверяем. можно ли взять еще одну фишку
            # проверка на наличие 7 фишек
            if sum(self._chosen_letters.values()) < 7:
                # проверка на наличие в игре достаточного количества таких фишек
                if self._chosen_letters[letter] + self._used_letters[letter] < \
                        LETTERS_AMOUNT[letter]:
                    self._letters_buttons[i].setDisabled(False)
                else:
                    self._letters_buttons[i].setDisabled(True)
            else:
                self._letters_buttons[i].setDisabled(True)

    def draw_widgets(self):
        """
        Прорисовка всех виджетов на экране
        """

        # текущая глубина для расположения виджетов друг за другом
        current_height = 0

        # прорисовка img label
        height = self._width
        self._img_label.resize(self._width, height)
        self._img_label.move(0, current_height)

        index = 0  # суммарная длина всех прошлых labels
        label_size = self._width // 15
        for label in self._hints_labels:
            label.resize(label_size - 2, label_size - 2)
            x_pos = index % self._width
            y_pos = index // self._width * label_size
            index += label_size
            label.move(x_pos + 2, y_pos + current_height + 2)
        current_height += height

        # прорисовка msg label
        height = self._chip_size - 5
        self._msg_label.resize(self._width, height)
        self._msg_label.move(0, current_height)
        current_height += height

        height = self._chip_size
        # прорисовка выбранных букв
        for i in range(len(self._chosen_chips_buttons)):
            self._chosen_chips_buttons[i].resize(self._chip_size,
                                                 self._chip_size)
            self._chosen_chips_buttons[i].move(i * self._chip_size,
                                               current_height)

        # прорисовка кнопки "сброс"
        self._drop_button.resize(self._chip_size * 2, self._chip_size)
        self._drop_button.move(7 * self._chip_size, current_height)

        current_height += height

        # разрыв в 5 пикселей
        current_height += 5

        # прорисовка кнопок с буквами для выбора
        index = 0  # суммарная длина всех прошлых кнопок
        for btn in self._letters_buttons:
            btn.resize(self._chip_size, self._chip_size)
            x_pos = index % self._row_size
            y_pos = index // self._row_size * self._chip_size
            index += self._chip_size
            btn.move(x_pos, y_pos + current_height)

        # три кнопки в конце клавиатуры
        for btn in self._empty_buttons:
            btn.resize(self._chip_size, self._chip_size)
            x_pos = index % self._row_size
            y_pos = index // self._row_size * self._chip_size
            index += self._chip_size
            btn.move(x_pos, y_pos + current_height)

        current_height += 4 * height

        # разрыв в 5 пикселей
        current_height += 5

        # прорисовка кнопки для выбора фото
        height = self._chip_size
        self._upload_img_button.resize(self._width // 2, height)
        self._upload_img_button.move(0, current_height)

        # прорисовка кнопки старта
        self._start_button.resize(self._width // 2, height)
        self._start_button.move(self._width // 2, current_height)
        current_height += height

    def letter_btn_pressed(self, letter: str = None):
        """
        Добавление фишки к выбранным фишкам, если это возможно
        """
        # если кнопка была активирована нажатием на нее, а не клавиатурой
        if not letter:
            # определяем какая именно кнопка вызвала функцию
            # и записываем ее букву
            for i in range(len(self._letters_buttons)):
                if self._letters_buttons[i] == self.sender():
                    letter = self._letters_on_buttons[i]
                    break

        # проверка на наличие 7 фишек
        if sum(self._chosen_letters.values()) < 7:
            # проверка на наличие в игре достаточного количества фишек
            if self._chosen_letters[letter] + self._used_letters[letter] < \
                    LETTERS_AMOUNT[letter]:
                # определяем букву кнопки
                # отдельный случай со звездочкой
                if letter == '*':
                    chosen_chip_index = 32
                else:
                    chosen_chip_index = ord(letter) - 1072

                # находим фишку в выбранных фишках, которую будем отображать
                chosen_chip_position = sum(self._chosen_letters.values())
                btn = self._chosen_chips_buttons[chosen_chip_position]

                btn.setText(str(
                    self._letters_on_buttons[chosen_chip_index].upper()))

                # добавляем фишку в словарь выбранных фишек
                self._chosen_letters[letter] += 1
                # обновляем цвет фишек
                self.update_buttons()

    def keyPressEvent(self, event: QKeyEvent):
        """
        Обработка нажатий на кнопки клавиатуры
        """

        key = event.key()  # ключ нажатой кнопки
        text = event.text().lower()  # текст нажатой кнопки

        # замена вводимых латинских букв на кириллицу и Ё на Е
        # комментарий ниже указывает PyCharm не проверять строки на опечатки
        # noinspection SpellCheckingInspection
        _eng_chars = u"`qwertyuiop[]asdfghjkl;'zxcvbnm,." \
                     u"QWERTYUIOP{}ASDFGHJKL:\"|ZXCVBNM<>"
        _rus_chars = u"ёйцукенгшщзхъфывапролджэячсмитьбю" \
                     u"ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭ/ЯЧСМИТЬБЮ"
        _trans_table = dict(zip(_eng_chars, _rus_chars))
        text = text.join([_trans_table.get(c, c) for c in text])
        if text == 'ё':
            text = 'е'

        # выход из программы по нажатию Escape
        if key == Qt.Key_Escape:
            self.close()
        # запуск алгоритма по нажатию Enter
        elif key == Qt.Key_Return:
            self._start_button.animateClick()
        # сброс по нажатию Backspace
        elif key == Qt.Key_Backspace:
            self._drop_button.animateClick()

        # если нажатая кнопка - один символ
        elif len(text) == 1:
            # если это "а"-"я"
            if 1072 <= ord(text) <= 1103:
                # если кнопка выключена, приложение не на начальном экране
                # и строка выбранных фишек не заполнена,
                # выводим сообщение, что кончились фишки с такой буквой
                if not self._letters_buttons[ord(text) - 1072].isEnabled() \
                        and self._start_button.isEnabled():
                    if sum(self._chosen_letters.values()) != 7:
                        self._msg_label.setText(self._msg_max_chip_error
                                                + text.upper())
                    # если 7 фишек уже выбрано, выводим об этом сообщение
                    else:
                        self._msg_label.setText(self._msg_max_chips_error)
                # иначе производим нажатие нужной кнопки
                else:
                    self._letters_buttons[ord(text) - 1072].animateClick()
            # аналогично, обработка звездочки
            elif text == '*' and self._asterisk_active:
                if not self._letters_buttons[32].isEnabled() \
                        and self._start_button.isEnabled():
                    if sum(self._chosen_letters.values()) != 7:
                        self._msg_label.setText(self._msg_max_chip_aster_error)
                    else:
                        self._msg_label.setText(self._msg_max_chips_error)
                else:
                    self._letters_buttons[32].animateClick()

    def drop_btn_pressed(self):
        """
        Сброс виджетов
        """

        self.clear_widgets()
        self._start_button.setDisabled(False)

    def start_btn_pressed(self):
        """
        Запуск алгоритма
        """
        # очистка подсказки, если запуск идет не в первый раз
        if self._got_hints:
            self.clear_hint()

        if sum(self._chosen_letters.values()) == 0:
            self._msg_label.setText(self._msg_no_chips_error)
        elif self._board_img is None:
            self._msg_label.setText(self._msg_no_img_error)
        else:
            # время начала
            # t = time.time()

            # запуск алгоритма
            hints, values = get_n_hints(self._board,
                                        Counter(self._chosen_letters),
                                        self._hints_amount)
            # время окончания
            # print(time.time() - t)

            if len(hints) != 0:
                # отрисовка подсказки на экране
                self.draw_hint(hints, values)
                # выводим стоимость подсказки
                self._msg_label.setText(self._msg_got_hint)
                self._got_hints = True
            else:
                self._msg_label.setText(self._msg_no_hints)

            # блокировака кнопок
            for i in range(self._chips_varieties):
                self._letters_buttons[i].setDisabled(True)
            self._start_button.setDisabled(True)

    def draw_hint(self, hints: [[[str]]], values: [int]):
        """
        Отрисовка подсказок на экране
        """

        # объединение доски с подсказками и их ценностями
        combined_board = get_board_with_hints(self._board, hints)

        # идем по всем полученным подсказкам
        for i in range(len(hints)):

            # определяем цвет подсказки
            # если цвета закончились - идем по новому кругу
            color_index = i % len(self._colors)

            # идем по доске подсказок
            for y in range(len(hints[i])):
                for x in range(len(hints[i][y])):
                    # отрисовываем букву если:
                    # на подсказке эта буква есть
                    # а на доске этой буквы еще нет
                    if hints[i][y][x] != '' and self._board[y][x] == '':
                        # поиск индекса буквы в алфавите
                        # отдельная обработка звездочки
                        if hints[i][y][x] == '*':
                            chip_index = 32
                        else:
                            chip_index = ord(hints[i][y][x]) - 1072

                        img_folder = self._chips_folders_paths[color_index]
                        img_filename = 'letter' + str(chip_index + 1) + '.jpg'

                        # размер одной фишки на изображении,
                        # масштабирование изображения под фишку
                        size = self._width // 15 - 2  # 28px
                        pix = QPixmap(img_folder + img_filename).\
                            scaled(size, size)

                        # находим нужный label в массиве
                        hint_label = self._hints_labels[y * 15 + x]
                        # установка изображения
                        hint_label.setPixmap(pix)

            # отрисовка ценности подсказки
            # определяем слово как гориз. или верт.
            # по приоритетам находим лучшую точку
            # рисуем
            y, x = get_hint_value_coord(hints[i], combined_board)
            combined_board[y][x] = '$'
            label = self._hints_labels[y * 15 + x]
            label.setText(str(values[i]))
            label.setStyleSheet('color: white; '
                                'background-color: '
                                + self._colors[color_index])


if __name__ == '__main__':
    app = QApplication(sys.argv)  # создание объекта приложения
    scrabble = ScrabbleApplication()  # создание объекта главного виджета
    sys.exit(app.exec_())  # выход из приложения по закрытию окна
