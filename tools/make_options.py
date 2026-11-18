"""data/items.json 으로 화면용 선택지·문항 수 표(docs/options.json)를 만든다.
주석 자체(파일 위치·정답 등)는 넣지 않고, 조건별 문항 수만 넣는다.
사용: python3 tools/make_options.py"""
import os, sys, json, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import selector

items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
combo = collections.Counter()
subj = collections.Counter()
units = collections.defaultdict(set)
subu = collections.defaultdict(set)
years, months = set(), set()
for it in items:
    subs = selector.subjects_of(it)
    for s in subs:
        subj[s] += 1
        if it.get("unit") and len(subs) == 1:
            units[s].add(it["unit"])
    combo[("|".join(subs), it["grade"], it["year"], it["month"], it["type"], it.get("unit") or "", it.get("sub") or "", it.get("pts") or 0)] += 1
    if it.get("sub"):
        subu[f"{subs[0]}/{it['unit']}"].add(it["sub"])
    years.add(it["year"])
    months.add(it["month"])
order = {s: i for i, s in enumerate(selector.SUBJECT_ORDER)}
out = dict(
    subjects=sorted(subj, key=lambda s: order.get(s, 99)),
    units={s: sorted(v, key=lambda u: selector.UNIT_ORDER.get(s, []).index(u) if u in selector.UNIT_ORDER.get(s, []) else 99)
           for s, v in units.items()},
    subs={k: sorted(v, key=lambda x: selector.SUB_ORDER.get(k, []).index(x) if x in selector.SUB_ORDER.get(k, []) else 99)
          for k, v in subu.items()},
    grades=["고1", "고2", "고3"],
    years=sorted(years, reverse=True),
    months=sorted(months),
    types=[dict(key=k, name=v) for k, v in selector.TYPE_NAME.items()],
    max_items=selector.MAX_ITEMS,
    combos=[list(k) + [v] for k, v in combo.items()],
)
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "docs", "options.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("subjects", len(out["subjects"]), "combos", len(out["combos"]))
