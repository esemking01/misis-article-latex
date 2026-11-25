"""Графики для статьи по results.json"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

r = json.load(open("results.json"))["results"]
names = list(r)
labels = ["исходный", "+ нормализация", "+ проверка пола", "+ дата рождения"]
colors = ["#9e9e9e", "#5b8def", "#f0a030", "#2a9d5c"]

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
for k, lab, c in zip(names, labels, colors):
    ts = [int(t) for t in r[k]]
    ax.plot(ts, [r[k][str(t)]["f1"] for t in ts], marker="o", label=lab, color=c, lw=2)
ax.set_xlabel("порог схожести T, %")
ax.set_ylabel("F1")
ax.set_ylim(0, 1)
ax.grid(alpha=0.3)
ax.legend(frameon=False, loc="lower center", ncol=2)
ax.set_title("Качество поиска дубликатов в зависимости от порога")
fig.tight_layout()
fig.savefig("../f1_by_threshold.png")

fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
fp = [r[k]["70"]["fp"] for k in names]
fn = [r[k]["70"]["fn"] for k in names]
x = range(len(names))
b1 = ax.bar([i - 0.2 for i in x], fp, 0.4, label="ложные срабатывания", color="#e07a5f")
b2 = ax.bar([i + 0.2 for i in x], fn, 0.4, label="пропущенные дубликаты", color="#3d5a80")
ax.bar_label(b1, padding=2)
ax.bar_label(b2, padding=2)
ax.set_xticks(list(x), labels)
ax.set_ylabel("число пар")
ax.legend(frameon=False)
ax.set_title("Ошибки при пороге 70 %")
fig.tight_layout()
fig.savefig("../errors_at_70.png")
print("ok")
