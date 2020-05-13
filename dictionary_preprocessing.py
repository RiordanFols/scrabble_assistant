import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
import scrabble_assistant as sa


def is_word_correct(word: str) -> bool:
    """
    Проверяет слово на корректность - не содержит ли оно неожиданных символов,
    не содержит ли оно больше букв, чем есть в игре.
    :param word: слово
    :return: true = переданное слово не содержит неожиданных символов
    """

    word = word.lower()
    alphabet = set(sa.read_json(sa.LETTERS_AMOUNT_FILENAME).keys())
    # множество букв, для которых указана стоимость

    for letter in word:
        if letter not in alphabet:
            return False

    letters_amount = sa.read_json(sa.LETTERS_AMOUNT_FILENAME)
    word_letters = Counter(word)

    for letter in word:
        if word_letters[letter] > letters_amount[letter]:
            return False
    return True


# не удалять пока
'''def is_word_fits_in_pattern(sharped_row: [str], word: str) -> bool:
    result = []
    patterns = get_regex_patterns(sharped_row)

    for pattern in patterns:
        found = pattern.findall(word)
        if pattern.findall(word):
            # if pattern.findall(word).pop() == word:
            result.append(pattern.findall(word))
    return bool(result)'''


def is_word_available(letters: Counter, word: str) -> bool:
    """
    Проверяет возможность составить слово из переданных букв
    :param letters: счетчик букв игрока
    :param word: слово
    :return: можно ли составить из переданных букв переданое слово
    """

    word_letters = Counter(word)  # счетчик букв
    for letter in word_letters.keys():
        if letters[letter] < word_letters[letter]:
            return False
    return True


def drop_incorrect_words():
    """
    Выполняется 1 раз, для  предобработки словаря.
    Выкидывает из словаря слова, содержащие более 15 букв. И слова с неожиданными символами.
    Перезаписывает предобработанный словарь на место исходного.
    :return:
    """
    dictionary_data = pd.read_csv(sa.DICTIONARY_FILENAME, header=None, names=['word'])
    # Считываем словарь в датафрейм

    dictionary_data['length'] = dictionary_data.word.apply(lambda x: len(x))
    # Добавляем колонку с длиной слова

    dictionary_data = dictionary_data.query('length <= 15')
    # Убираем слова длинее 15 букв

    dictionary_data['is_correct'] = dictionary_data.word.apply(lambda x: is_word_correct(x))
    dictionary_data = dictionary_data.query('is_correct == True')
    dictionary_data = dictionary_data.drop('is_correct', axis=1)  # больше не нужна
    # Убираем слова с неожиданными символами и содержащие больше букв, чем есть в игре.
    # fixme: Выполняется долго! Можно переписать.

    np.savetxt(fname=sa.DICTIONARY_FILENAME, X=dictionary_data.word, fmt='%s',
               encoding='utf-8')  # Перезаписываем почищенный словарь


def make_sub_dictionaries():
    """
    Выполняется 1 раз, для  получения под-словарей, содержащих определенную букву.
    Считывает алфавит. Разбивает исходный словарь на N словарей,
    где N - количество букв в алфавите. Записывает подсловари в папку sub-dictionaries
    :return:
    """
    dictionary_data = pd.read_csv(sa.DICTIONARY_FILENAME, header=None, names=['word'])
    # Считываем словарь в датафрейм

    alphabet = sa.read_json(sa.LETTERS_AMOUNT_FILENAME)
    alphabet.pop('*')
    alphabet = list(alphabet.keys())
    # Считываем буквы, по которым будем разбивать словари

    for letter in alphabet:
        dictionary_data['contains_letter'] = dictionary_data.word.str.contains(letter)
        # Ставим флаг - содержит ли слово искомую букву

        words_contains_letter = dictionary_data.query("contains_letter == True")
        # Создаем датафрейм из слов, которые содержат искомую букву

        np.savetxt(fname=(
            Path(Path.cwd() / 'sub-dictionaries' / (letter + '-containing-sub-dict.txt'))),
            X=words_contains_letter.word, fmt='%s', encoding='utf-8')
        # Записываем подсловарь