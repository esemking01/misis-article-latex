"""Сравнение вариантов критерия на тестовой базе clients.csv.

Для каждой пары записей считаем схожесть трёх полей и смотрим, совпадает ли
решение «дубликат / не дубликат» с эталоном (entity_id).
Чтобы не сравнивать одни и те же строки миллионы раз, схожесть считается
по уникальным значениям поля, а потом раскладывается по парам через numpy.
"""
import json
import time
from itertools import combinations

import numpy as np
import pandas as pd

from matcher import dates_compatible, gender, normalize, token_sort_ratio, ratio

FIELDS = ["Фамилия", "Имя", "Отчество"]
THRESHOLDS = list(range(50, 100, 5))

df = pd.read_csv("clients.csv", dtype=str, keep_default_na=False)
n = len(df)
I, J = np.triu_indices(n, k=1)
ent = df["entity_id"].to_numpy()
fam = df["family_id"].to_numpy()
same_entity = ent[I] == ent[J]
same_family = fam[I] == fam[J]
total_true = int(same_entity.sum())
print(f"записей {n}, пар {len(I):,}, настоящих пар-дубликатов {total_true}")


def field_min_sim(prep, sim):
    """min по трём полям схожести для всех пар, через матрицы по уникальным значениям"""
    res = np.full(len(I), 100, dtype=np.int16)
    for f in FIELDS:
        vals = df[f].map(prep)
        uniq, idx = np.unique(vals.to_numpy(), return_inverse=True)
        m = len(uniq)
        S = np.zeros((m, m), dtype=np.int16)
        for a in range(m):
            S[a, a] = sim(uniq[a], uniq[a])
            for b in range(a + 1, m):
                S[a, b] = S[b, a] = sim(uniq[a], uniq[b])
        res = np.minimum(res, S[idx[I], idx[J]])
    return res


def metrics(pred):
    tp = int((pred & same_entity).sum())
    fp = int((pred & ~same_entity).sum())
    fn = total_true - tp
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / total_true
    f1 = 2 * p * r / (p + r) if p + r else 0
    fp_family = int((pred & ~same_entity & same_family).sum())
    return dict(tp=tp, fp=fp, fn=fn, precision=round(p, 3), recall=round(r, 3),
                f1=round(f1, 3), fp_family=fp_family, fp_other=fp - fp_family)


t0 = time.time()
sim_raw = field_min_sim(lambda s: s, token_sort_ratio)            # как в исходной программе
sim_norm = field_min_sim(normalize, ratio)                        # с нормализацией
print(f"матрицы схожести: {time.time() - t0:.1f} c")

g = np.array([gender(s, p) for s, p in zip(df["Фамилия"], df["Отчество"])], dtype=object)
gender_ok = ~((g[I] != None) & (g[J] != None) & (g[I] != g[J]))  # noqa: E711
print("пол не определился у", int(sum(x is None for x in g)), "записей")

dates = df["Дата рождения"].to_numpy()
# совместимость дат считаем только для кандидатов, иначе долго
variants = {
    "V0 исходный": lambda T: sim_raw > T,
    "V1 + нормализация": lambda T: sim_norm > T,
    "V2 + проверка пола": lambda T: (sim_norm > T) & gender_ok,
}
results = {k: {} for k in list(variants) + ["V3 + дата рождения"]}
for T in THRESHOLDS:
    for k, fn in variants.items():
        results[k][T] = metrics(fn(T))
    cand = (sim_norm > T) & gender_ok
    ci = np.nonzero(cand)[0]
    ok = np.array([dates_compatible(dates[I[c]], dates[J[c]]) for c in ci], dtype=bool)
    pred = np.zeros(len(I), dtype=bool)
    pred[ci[ok]] = True
    results["V3 + дата рождения"][T] = metrics(pred)

for k, r in results.items():
    best = max(r, key=lambda T: r[T]["f1"])
    print(f"\n{k}: лучший порог {best} -> {r[best]}")
    print("  при 70:", r[70])

# что именно ловит исходный вариант при 70 %: разбор ложных срабатываний
pred0 = sim_raw > 70
fp_idx = np.nonzero(pred0 & ~same_entity)[0]
examples = [(df.iloc[I[c]][FIELDS].tolist(), df.iloc[J[c]][FIELDS].tolist()) for c in fp_idx[:15]]
print("\nпримеры ложных срабатываний V0@70:")
for a, b in examples:
    print("  ", " ".join(a), "|", " ".join(b))

# пропуски финального варианта
predF = np.zeros(len(I), dtype=bool)
cand = (sim_norm > 70) & gender_ok
ci = np.nonzero(cand)[0]
ok = np.array([dates_compatible(dates[I[c]], dates[J[c]]) for c in ci], dtype=bool)
predF[ci[ok]] = True
fn_idx = np.nonzero(~predF & same_entity)[0]
print(f"\nпропуски V3@70 ({len(fn_idx)}):")
for c in fn_idx[:15]:
    a, b = df.iloc[I[c]], df.iloc[J[c]]
    print("  ", " ".join(a[FIELDS]), a["Дата рождения"], "|", " ".join(b[FIELDS]), b["Дата рождения"],
          int(sim_norm[c]))
fpF = np.nonzero(predF & ~same_entity)[0]
print(f"\nложные V3@70 ({len(fpF)}):")
for c in fpF[:15]:
    a, b = df.iloc[I[c]], df.iloc[J[c]]
    print("  ", " ".join(a[FIELDS]), a["Дата рождения"], "|", " ".join(b[FIELDS]), b["Дата рождения"])

# ---------- блокировка ----------
first = df["Фамилия"].map(lambda s: normalize(s)[:1]).to_numpy()
block = first[I] == first[J]
predB = predF & block
mB = metrics(predB)
print(f"\nблокировка по первой букве фамилии: сравнений {int(block.sum()):,} из {len(I):,} "
      f"({block.mean():.1%}), {mB}")

json.dump({"results": {k: {str(t): v for t, v in r.items()} for k, r in results.items()},
           "pairs": int(len(I)), "records": n, "true_pairs": total_true,
           "blocking": {"compared": int(block.sum()), **mB}},
          open("results.json", "w"), ensure_ascii=False, indent=1)

# ---------- три исхода, как у Феллеги и Сантера ----------
has_both = (dates[I] != "") & (dates[J] != "")
sure = predF & has_both
review = predF & ~has_both
ms = metrics(sure)
print(f"\nуверенные (обе даты есть): {int(sure.sum())}, из них верных {ms['tp']}, точность {ms['precision']}")
print(f"на ручную проверку (даты нет): {int(review.sum())}, из них настоящих дубликатов "
      f"{int((review & same_entity).sum())}")
