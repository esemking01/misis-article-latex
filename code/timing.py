"""Сколько времени занимает полный поиск всех пар без блокировки и с ней (чистый Python)."""
import time
from itertools import combinations
import pandas as pd
from matcher import normalize, ratio, gender, dates_compatible

df = pd.read_csv("clients.csv", dtype=str, keep_default_na=False)
rows = [(normalize(r.Фамилия), normalize(r.Имя), normalize(r.Отчество), gender(r.Фамилия, r.Отчество),
         r._5) for r in df.itertuples()]

def is_dup(a, b, T=70):
    if a[3] and b[3] and a[3] != b[3]:
        return False
    if not all(ratio(x, y) > T for x, y in zip(a[:3], b[:3])):
        return False
    return dates_compatible(a[4], b[4])

t = time.time()
full = sum(is_dup(a, b) for a, b in combinations(rows, 2))
t_full = time.time() - t

blocks = {}
for r in rows:
    blocks.setdefault(r[0][:1], []).append(r)
t = time.time()
blk = sum(is_dup(a, b) for g in blocks.values() for a, b in combinations(g, 2))
t_blk = time.time() - t
print(f"без блокировки: {full} пар, {t_full:.1f} c; с блокировкой: {blk} пар, {t_blk:.1f} c")
