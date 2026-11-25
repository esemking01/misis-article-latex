"""Генератор тестовой клиентской базы с дубликатами, опечатками и родственниками.

Запуск:  python generate.py            -> clients.csv
Колонки: id, Фамилия, Имя, Отчество, Дата рождения, Телефон, entity_id, family_id
entity_id — эталон: записи с одинаковым entity_id описывают одного человека.
"""
import csv
import random
from datetime import date, timedelta

from names import (FEMALE_NAMES, MALE_NAMES, PAIRED_NAMES, PATRONYMICS,
                   SURNAMES_GENDERED, SURNAMES_NEUTRAL, female_surname)

SEED = 2026
N_FAMILIES = 1300          # семей (у каждой 1–3 человека в базе)
DUP_SHARE = 0.25           # доля людей, у которых есть дубликаты
MISSING_DATE = 0.15        # доля дубликатов без даты рождения

rng = random.Random(SEED)

ROWS = ["йцукенгшщзхъ", "фывапролджэ", "ячсмитьбю"]
NEIGHBOURS = {}
for row in ROWS:
    for i, ch in enumerate(row):
        NEIGHBOURS[ch] = (row[i - 1] if i > 0 else "") + (row[i + 1] if i + 1 < len(row) else "")
# типичные «смысловые» замены из исследования опечаток: и-е, а-о и т.п.
CONFUSIONS = {"и": "е", "е": "и", "а": "о", "о": "а", "ё": "е", "я": "е", "ы": "и", "ш": "щ", "щ": "ш"}
LATIN = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "к": "k",
         "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C", "Х": "X", "К": "K", "М": "M", "Т": "T"}


def zipf_choice(items, a=1.1):
    """Частые фамилии и имена встречаются чаще — так появляются тёзки."""
    weights = [1 / (i + 1) ** a for i in range(len(items))]
    return rng.choices(items, weights=weights)[0]


def random_date():
    return date(1950, 1, 1) + timedelta(days=rng.randrange(0, 365 * 55))


def random_phone():
    return "+7 9{:02d} {:03d}-{:02d}-{:02d}".format(rng.randrange(100), rng.randrange(1000),
                                                    rng.randrange(100), rng.randrange(100))


def make_person(surname, father, gender, birth=None, name=None):
    if name is None:
        name = zipf_choice(MALE_NAMES if gender == "М" else FEMALE_NAMES)
    patr = PATRONYMICS[father][0 if gender == "М" else 1]
    sur = surname if gender == "М" else female_surname(surname)
    return {"Фамилия": sur, "Имя": name, "Отчество": patr, "gender": gender,
            "Дата рождения": birth or random_date(), "Телефон": random_phone()}


# ---------- опечатки ----------
def typo(word):
    if len(word) < 3:
        return word
    kind = rng.choices(["sub", "del", "ins", "swap", "conf"], weights=[3, 3, 2, 1, 3])[0]
    i = rng.randrange(1, len(word))  # первую букву люди путают реже
    ch = word[i].lower()
    if kind == "sub" and NEIGHBOURS.get(ch):
        return word[:i] + rng.choice(NEIGHBOURS[ch]) + word[i + 1:]
    if kind == "del":
        return word[:i] + word[i + 1:]
    if kind == "ins":
        return word[:i] + word[i] + word[i:]          # удвоение буквы
    if kind == "swap" and i + 1 < len(word):
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == "conf" and ch in CONFUSIONS:
        return word[:i] + CONFUSIONS[ch] + word[i + 1:]
    return word[:i] + word[i + 1:]


def latinize(word):
    pos = [i for i, c in enumerate(word) if c in LATIN]
    if not pos:
        return word
    i = rng.choice(pos)
    return word[:i] + LATIN[word[i]] + word[i + 1:]


def corrupt(rec):
    """Портим копию записи 1–2 ошибками ручного ввода."""
    r = dict(rec)
    fields = ["Фамилия", "Имя", "Отчество"]
    for _ in range(rng.choice([1, 1, 2])):
        f = rng.choice(fields)
        kind = rng.choices(["typo", "case", "latin", "yo", "space"], weights=[6, 2, 1.5, 1, 1])[0]
        if kind == "typo":
            r[f] = typo(r[f])
        elif kind == "case":
            for g in fields:
                r[g] = r[g].lower() if rng.random() < 0.7 else r[g].upper()
        elif kind == "latin":
            r[f] = latinize(r[f])
        elif kind == "yo":
            r[f] = r[f].replace("ё", "е").replace("Ё", "Е") if "ё" in r[f].lower() else typo(r[f])
        else:
            r[f] = " " + r[f] + "  " if rng.random() < 0.5 else r[f].replace(r[f][1], r[f][1] + " ", 1)
    d = r["Дата рождения"]
    u = rng.random()
    if u < MISSING_DATE:
        r["Дата рождения"] = None
    elif u < MISSING_DATE + 0.03 and d.day <= 12 and d.day != d.month:
        r["Дата рождения"] = date(d.year, d.day, d.month)   # перепутали день и месяц
    if rng.random() < 0.5:
        r["Телефон"] = "" if rng.random() < 0.5 else random_phone()  # новый номер или пусто
    return r


def main():
    people = []  # (entity_id, family_id, record)
    eid = 0
    for fam in range(N_FAMILIES):
        surname = zipf_choice(SURNAMES_GENDERED + SURNAMES_NEUTRAL, a=0.8)
        father = zipf_choice(list(PATRONYMICS), a=0.7)
        g = rng.choice("МЖ")
        first = make_person(surname, father, g)
        members = [first]
        u = rng.random()
        if u < 0.25:
            # брат и сестра: одна фамилия и отчество, иногда парные имена
            g2 = "Ж" if g == "М" else "М"
            name2 = None
            if g == "М" and first["Имя"] in PAIRED_NAMES and rng.random() < 0.6:
                name2 = PAIRED_NAMES[first["Имя"]]
            members.append(make_person(surname, father, g2, name=name2))
        elif u < 0.40:
            # супруги: одна фамилия, разные имена и отчества
            g2 = "Ж" if g == "М" else "М"
            other_father = zipf_choice(list(PATRONYMICS), a=0.7)
            members.append(make_person(surname, other_father, g2))
        for m in members:
            people.append((eid, fam, m))
            eid += 1

    records = []
    for e, fam, p in people:
        records.append((e, fam, p))
        if rng.random() < DUP_SHARE:
            for _ in range(rng.choice([1, 1, 1, 2, 3])):
                records.append((e, fam, corrupt(p)))
    rng.shuffle(records)

    with open("clients.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "Фамилия", "Имя", "Отчество", "Дата рождения", "Телефон", "entity_id", "family_id"])
        for i, (e, fam, r) in enumerate(records):
            d = r["Дата рождения"].strftime("%d.%m.%Y") if r["Дата рождения"] else ""
            w.writerow([i, r["Фамилия"], r["Имя"], r["Отчество"], d, r["Телефон"], e, fam])
    print(f"людей: {len(people)}, записей: {len(records)}, дубликатов: {len(records) - len(people)}")


if __name__ == "__main__":
    main()
