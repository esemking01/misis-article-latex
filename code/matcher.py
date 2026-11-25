"""Сравнение строк и правила отнесения пары записей к дубликатам.

ratio() считает то же, что fuzz.ratio из fuzzywuzzy с установленным
python-Levenshtein: 2 * НОП / (|a| + |b|), где НОП — длина наибольшей общей
подпоследовательности (то есть расстояние, где замена = 2 операции).
НОП считается бит-параллельным алгоритмом, чтобы не ждать вечность на чистом Python.
"""
import re

LAT2CYR = str.maketrans("aeopcxyk", "аеорсхук")


def lcs_len(a: str, b: str) -> int:
    if not a or not b:
        return 0
    masks = {}
    for i, ch in enumerate(a):
        masks[ch] = masks.get(ch, 0) | (1 << i)
    full = (1 << len(a)) - 1
    v = full
    for ch in b:
        u = v & masks.get(ch, 0)
        v = ((v + u) | (v - u)) & full
    return len(a) - bin(v).count("1")


def ratio(a: str, b: str) -> int:
    if not a and not b:
        return 0
    return int(round(100 * 2 * lcs_len(a, b) / (len(a) + len(b))))


def full_process(s: str) -> str:
    # как в fuzzywuzzy: нижний регистр, всё кроме букв и цифр -> пробел
    return re.sub(r"(?ui)\W", " ", str(s)).lower().strip()


def token_sort_ratio(a: str, b: str) -> int:
    a = " ".join(sorted(full_process(a).split()))
    b = " ".join(sorted(full_process(b).split()))
    return ratio(a, b)


# ---------- улучшения ----------
def normalize(s: str) -> str:
    """нижний регистр, ё -> е, латиница-двойник -> кириллица, без пробелов"""
    s = str(s).lower().replace("ё", "е").translate(LAT2CYR)
    return re.sub(r"\s+", "", s)


def gender(surname: str, patronymic: str):
    """Пол по окончанию отчества, а если не вышло — по фамилии. None = не понять."""
    p, s = normalize(patronymic), normalize(surname)
    if p.endswith("ич"):
        return "М"
    if p.endswith("на"):
        return "Ж"
    if s.endswith(("ова", "ева", "ина", "ая")):
        return "Ж"
    if s.endswith(("ов", "ев", "ин", "ий")):
        return "М"
    return None


def dates_compatible(d1: str, d2: str) -> bool:
    """Пустая дата ничего не запрещает; одна неверная цифра или перепутанные
    день и месяц считаются опечаткой."""
    if not d1 or not d2 or d1 == d2:
        return True
    a, b = d1.replace(".", ""), d2.replace(".", "")
    if sum(x != y for x, y in zip(a, b)) <= 1:
        return True
    return a[2:4] + a[0:2] + a[4:] == b
