import json
from collections import Counter
from pathlib import Path

import numpy as np

LETTERS_VALUES_FILENAME = "letters_values.json"
LETTERS_AMOUNT_FILENAME = "letters_amount.json"
BOARD_BONUSES_FILENAME = "board_bonuses.json"
DICTIONARY_FILENAME = "dictionary.txt"


def get_best_hint(board: [[str]], letters: Counter) -> [[str]]:
    """
    Дает лучшую подсказку слова на доске.
    :param board: символьный двумерный массив доски
    :param letters: набор букв игрока
    :return: символьный двумерный массив с буквами подсказки
    """

    best_hint = board.copy()  # Подсказка - отдельная доска

    best_hint = [[''] * len(best_hint) for _ in range(len(best_hint[0]))]
    # Очищаем доску-подсказку (заполняем ее пустыми строками)

    for row in get_marked_rows(board):
        # Идем по строкам
        pass

    for row in get_marked_rows(transpose_board(board)):
        # Идем по столбцам
        pass

    return best_hint


def is_word_composable(letters: Counter, word: str) -> bool:
    """
    Проверяет возможность составить слово из переданных букв.
    :param letters: счетчик букв игрока
    :param word: слово
    :return: можно ли составить из переданных букв переданое слово
    """
    # todo: Добавить передачу паттерна, чтобы искать с учетом буквы на доске

    word_letters = Counter(word)  # Счетчик букв для слова
    for letter in word_letters.keys():
        if letters[letter] < word_letters[letter]:
            # Если количество букв у игрока меньше, чем букв в слове
            return False
    return True


def arrange_long_word_to_empty_board(word: str) -> [str]:
    """Располагает слово, длиной от 5 до 7 на стартовой доске наилучшим образом,
    с учетом бонусов.
    :param word: слово, которое располагаем
    :return: самый ценный вариант расположения слова на пустой доске
    """
    most_expensive_letter = 0
    most_expensive_letter_index = None

    letters_values = read_json_to_dict(LETTERS_VALUES_FILENAME)
    # bonuses = read_json_to_list(BOARD_BONUSES_FILENAME)
    best_hint = get_empty_board()

    center_of_board_by_y = int(len(best_hint) / 2)
    center_of_board_by_x = int(len(best_hint[center_of_board_by_y]) / 2)
    row_with_arranged_word = best_hint[center_of_board_by_y]

    distance_to_bonus = 4  # Расстояние от стартового поля до бонуса x2
    # todo: calculate it for each board

    word_len = len(word)
    available_movement = word_len - distance_to_bonus
    # На сколько слово может двигаться, оставаясь на стартовом поле

    letters_available_to_bonus = list(word[:available_movement]) + \
                                 list(word[-available_movement:])
    # Буквы, которые могут быть на бонусе

    for i in range(len(letters_available_to_bonus)):
        if letters_values[letters_available_to_bonus[i]] > most_expensive_letter:
            most_expensive_letter = letters_values[letters_available_to_bonus[i]]
            most_expensive_letter_index = i
            # Находим самую ценную букву и ее индекс, среди доступных

    # Бонусная буква делит слово на 2 части (бонусная буква идет во 2-ю часть)
    first_part = word[:most_expensive_letter_index]
    first_part_len = len(first_part)
    second_part = word[most_expensive_letter_index:]
    second_part_len = len(second_part)

    if most_expensive_letter_index < int(word_len / 2):
        # Если самая ценная из доступных букв, находится в 1-й половине слова
        bonus_index = center_of_board_by_x - distance_to_bonus

    else:  # Если самая ценная из доступных букв, находится во 2-й половине слова
        bonus_index = center_of_board_by_x + distance_to_bonus

    row_with_arranged_word = row_with_arranged_word[:bonus_index - first_part_len] + \
                             list(first_part) + list(second_part) + \
                             row_with_arranged_word[bonus_index + second_part_len:]
    # Располагаем слово в ряду наилучшим образом

    return row_with_arranged_word


def get_best_hint_for_empty_board(letters: Counter) -> [[str]]:
    """
    Генерирует первый ход. Выдает расположение лучшего слова для 1-ого хода.
    :param letters: буквы, которые есть у игрока
    :return: доска с расположенным лучшим словом
    """
    # todo: Можно переписать оптимальнее часть с длинными словами.

    best_word = ''
    best_word_start_by_x = None
    best_word_value = 0

    best_hint = get_empty_board()  # Подсказка - отдельная доска

    center_of_board_by_y = int(len(best_hint) / 2)
    # center_of_board_by_x = int(len(best_hint[center_of_board_by_y]) / 2)

    with open(DICTIONARY_FILENAME, 'r', encoding='utf-8') as dict_file:
        for line in dict_file:  # Читаем строки из словаря
            word = line[:-1]  # Записываем слово без '\n'
            if is_word_composable(letters, word):
                # Если слово можно составить из букв игрока
                word_len = len(word)
                if word_len < 5:
                    word_value = calculate_letters_values(word)
                    if word_value > best_word_value:
                        best_word = word
                        best_word_value = word_value

                elif word_len < 8:  # Если слово состоит из 5-7 букв
                    row = arrange_long_word_to_empty_board(word)
                    # Располагаем слово наилучшим образом

                    word_start_by_x = [i for i in range(len(row)) if row[i]][0]
                    # Находим индекс начала слова в ряду

                    word_value = calculate_word_value(word, best_hint, center_of_board_by_y,
                                                      word_start_by_x)

                    if word_value > best_word_value:
                        # Если найдено новое лучшее слово
                        best_word = word
                        best_word_value = word_value
                        best_word_start_by_x = word_start_by_x

    # На этом этапе мы нашли лучшее слово. Теперь расположим его на доске.
    best_word_len = len(best_word)

    if best_word_len < 5:  # Все слова, которые короче 5-и букв, ставим в середину ряда
        word_start_index = int((len(best_hint[center_of_board_by_y]) -
                                best_word_len) / 2)
        # Рассчитываем индекс, откуда начинается слово

        best_hint[center_of_board_by_y] = \
            best_hint[center_of_board_by_y][:word_start_index] + \
            list(best_word) + \
            best_hint[center_of_board_by_y][word_start_index + best_word_len:]
        # Заменяем середину ряда на найденое слово

    else:  # Располагаем на доске слово, состоящее из 5-7 букв
        best_hint[center_of_board_by_y] = arrange_long_word_to_empty_board(best_word)

    return best_hint


def get_regex_patterns(sharped_row: [str]) -> [str]:
    """
    Получает строку, возвращает паттерны, соответствующие этой строке,
    для поиска подходящих слов в словаре по этому паттерну.
    :param sharped_row: размеченный '#' ряд
    :return: шаблон, по которому можно найти подходящие слова
    """
    prepared_row = []
    patterns = []
    # test_row = ['', '', '', 'а', '#', 'а', '#', '#', '#', '#', '', 'р', '', '', '']

    for cell in range(len(sharped_row)):
        if sharped_row[cell]:  # если в клетке есть символ
            prepared_row.append(sharped_row[cell])
        else:  # если клетка пустая
            prepared_row.append(' ')

    prepared_row = ''.join(prepared_row).split('#')
    # соединяем в строку и нарезаем на подстроки по '#'

    for i in range(len(prepared_row)):
        if len(prepared_row[i]) > 1:
            # отбираем подстроки длинее 1 символа
            patterns.append(prepared_row[i])

    for i in range(len(patterns)):
        patterns[i] = patterns[i].replace(' ', '[а-я]?')
    # в пустое место можно вписать любую букву букву а-я или не писать ничего
    # todo: Можно переписать регулярку c помощью одних фигурных скобок

    for i in range(len(patterns)):
        patterns[i] = '^(' + patterns[i] + ')$'
    # Чтобы регулярка не хватала слова, которые удовлетворяют,
    # но выходят за рамки.

    # for i in range(len(patterns)):
    #    patterns[i] = re.compile(patterns[i])
    # компилируем каждый паттерн в регулярное выражение
    # upd. компиляция не понадобится. Но пока не удалять

    return patterns


def calculate_letters_values(word: str) -> int:
    """
    Считает ценность слова, без учета бонусов.
    :param word: слово, ценность которого нужно посчитать
    :return: ценность слова, без учета бонусов
    """
    letters_values = read_json_to_dict(LETTERS_VALUES_FILENAME)
    # Считываем ценности букв

    return sum([letters_values[letter] for letter in word])


def calculate_word_value(word: str, board: [[str]],
                         line_index: int, start_index: int) -> int:
    """
    Считает ценность слова, расположенного на доске,
    с учетом бонусов на доске в любых кол-вах.
    Не учитывает бонусы, которые уже были использованы.
    Если игрок доложил 7 букв - добавляет 15 баллов.
    :param word: слово, ценность которого нужно посчитать
    :param board: доска с текущей позицией
    :param line_index: индекс строки, в которой стоит слово
    :param start_index: индекс начала слова в строке
    :return: ценность слова, с учетом бонусов
    """

    # Считываем ценность букв как словарь
    letters_values = read_json_to_dict(LETTERS_VALUES_FILENAME)

    # Считываем бонусы на доске как матрицу
    board_bonuses = read_json_to_list(BOARD_BONUSES_FILENAME)

    # Разметка бонусов на доске:
    # 00 - обычное поле
    # x2 - *2 за букву
    # x3 - *3 за букву
    # X2 - *2 за слово
    # X3 - *3 за слово
    # ST - стартовое поле

    value = 0
    new_letters_counter = 0
    word_bonuses_2x_counter = 0  # сколько бонусов x2 слово собрали
    word_bonuses_3x_counter = 0  # сколько бонусов x3 слово собрали

    for i in range(len(word)):  # идем по буквам слова
        letter = word[i]

        letter_value = letters_values[letter]  # Ценность буквы без бонусов

        bonus = board_bonuses[line_index][start_index + i]
        # Бонус на клетке, где стоит буква

        # Бонусы учитываются только в том случае, если они не были использованы ранее.
        # Бонус использован, если на его месте уже есть буква.

        if not board[line_index][start_index + i]:  # Если в клетке не было буквы
            new_letters_counter += 1
            if bonus == "x2":
                letter_value *= 2
            elif bonus == "x3":
                letter_value *= 3
            elif bonus == "X2":
                word_bonuses_2x_counter += 1
            elif bonus == "X3":
                word_bonuses_3x_counter += 1

        value += letter_value
    # считаем все собранные бонусы за слово
    value *= 2 ** word_bonuses_2x_counter
    value *= 3 ** word_bonuses_3x_counter

    # выложил разом 7 букв - получи 15 баллов
    if new_letters_counter == 7:
        value += 15

    return value


def get_marked_rows(board: [[str]]) -> [[str]]:
    """
    Меняет доску, помечая заблокированные клетки знаком #
    Если у клетки есть символы сверху или снизу, то клетка заблокирована
    Постобработка:
    Между двумя # пустое пространство - все клетки между ними #
    От начала до # пустое пространство - все клетки между ними #
    От # до конца пустое пространство - все клетки между ними #
    :param board: символьный двумерный массив доски
    :return: одномерный массив символов(строка) с заблокированными клетками
    """

    marked_board = []  # новая доска с метками
    for index in range(len(board)):  # идем по строкам
        row = board[index].copy()  # i-тая строка доски
        for symbol_index in range(len(row)):
            up_block = False  # заблокировано ли сверху
            down_block = False  # заблокировано ли снизу

            if not row[symbol_index]:  # если в клетке пусто
                if index > 0:  # если не самая верхняя строка
                    if board[index - 1][symbol_index]:  # если сверху буква
                        up_block = True
                if index < (len(board) - 1):  # если не самая нижняя строка
                    if board[index + 1][symbol_index]:  # если снизу буква
                        down_block = True
                if up_block or down_block:
                    row[symbol_index] = '#'

        # постобработка:
        # между двумя # пустое пространство - все клетки между ними #
        # от начала до # пустое пространство - все клетки между ними #
        # от # до конца пустое пространство - все клетки между ними #

        last_sharp_index = -2  # индекс последнего символа #
        # -2: символы # не встречались
        # -1: символы # встречались, но после них шли буквы

        for row_index in range(len(row)):  # идем по строкам
            if row[row_index] == '#':
                # если уже встречали #, просто перезаписываем
                if last_sharp_index == -1:
                    last_sharp_index = row_index
                # если это первая # и до этого символов не было, то все
                # клетки до этого места помечаем #
                elif last_sharp_index == -2:
                    for j in range(row_index):
                        row[j] = '#'
                    last_sharp_index = row_index
                # если уже встречали # и до этого между текущим #
                # и прошлым не было # символов, помечаем # все клетки между ними
                else:
                    for j in range(last_sharp_index + 1, row_index):
                        row[j] = '#'
                    last_sharp_index = row_index
            # если нашли какой-то символ, но не #, сбрасываем счетчик
            elif row[row_index] != '':
                last_sharp_index = -1

            # если дошли до конца и между последним # и концом нет символов,
            # все клетки между ними помечаем #
            if row_index == (len(row) - 1) and last_sharp_index != -1:
                for j in range(last_sharp_index + 1, row_index + 1):
                    row[j] = '#'

        marked_board.append(row)  # добавляем строку к новой доске

    return marked_board


def transpose_board(board: [[str]]) -> [[str]]:
    """
    Транспонирует двумерный массив
    :param board: символьный двумерный массив доски
    :return: транспонированный двумерный массив
    """
    return list(np.array(board).transpose())


def read_json_to_dict(json_filename: str) -> dict:
    """
    Считывает json-файл в dict
    :param json_filename: имя json-файла
    :return: считанный словарь
    """
    with open(file=Path(Path.cwd() / 'jsons' / json_filename), mode='r',
              encoding='utf-8') as file:
        return dict(json.load(file))


def read_json_to_list(json_filename: str) -> [[str]]:
    """
    Считывает json-файл в list
    :param json_filename: имя json-файла
    :return: считанный массив
    """
    with open(file=Path(Path.cwd() / 'jsons' / json_filename), mode='r',
              encoding='utf-8') as file:
        return list(json.load(file))


def get_empty_board() -> [[str]]:
    """
    Генерирует пустую доску, по размеру из файла.
    :return: доска, без букв
    """
    board = read_json_to_list(BOARD_BONUSES_FILENAME)
    return [[''] * len(board) for _ in range(len(board[0]))]


# ----- TESTS -----
if __name__ == '__main__':
    pass

    # test_board = [
    #     ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', 'т', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', 'о', '', '', '', '', ''],
    #     ['', '', '', 'п', 'о', 'c', 'е', 'л', 'о', 'к', '', '', '', '', ''],
    #     ['', '', '', 'а', '', 'а', '', '', '', '', '', 'р', '', '', ''],
    #     ['', '', '', 'п', '', 'д', 'о', 'м', '', 'я', '', 'е', '', '', ''],
    #     ['', '', '', 'а', '', '', '', 'а', 'з', 'б', 'у', 'к', 'а', '', ''],
    #     ['', '', '', '', '', 'с', 'о', 'м', '', 'л', '', 'а', '', '', ''],
    #     ['', '', '', 'я', 'м', 'а', '', 'а', '', 'о', '', '', '', '', ''],
    #     ['', '', '', '', '', 'л', '', '', '', 'к', 'и', 'т', '', '', ''],
    #     ['', '', '', '', 'с', 'о', 'л', 'ь', '', 'о', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    #     ['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
    # ]

    # print(20 == calculate_word_value('тотем', transpose_board(test_board), 11, 10))
    # print(8 == calculate_word_value('дуло', transpose_board(test_board), 4, 1))
    # передаем транспонированную доску, тк слово написано по вертикали
    # если доска транспонирована - координаты меняются местами

    # test_marked_board = get_marked_rows(test_board)
    # for iii in range(len(test_marked_board)):
    #     print(test_marked_board[iii])
    # print(get_marked_row(test_board, 12))

    # board = get_best_hint_for_empty_board(Counter('собака'))

    # print(arrange_long_word_to_empty_board('зоопарк'))
    # print(arrange_long_word_to_empty_board('щавель'))
    # print(arrange_long_word_to_empty_board('карандаш'))

    # print(get_best_hint_for_empty_board(Counter('салат'))[7])
    # print(get_best_hint_for_empty_board(Counter('шалаш'))[7])
    # print(get_best_hint_for_empty_board(Counter('суп'))[7])
    # print(get_best_hint_for_empty_board(Counter('абв'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвг'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвгд'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвгде'))[7])
    print(get_best_hint_for_empty_board(Counter('абвгдеж'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвгдежз'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвгдежзи'))[7])
    # print(get_best_hint_for_empty_board(Counter('абвгдежзи'))[7])
    print(get_best_hint_for_empty_board(Counter('уеаояижзфцшщъыьэю'))[7])
