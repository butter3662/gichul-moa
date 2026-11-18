"""분류 결과(data/units.json)와 수동 판정(data/units_manual.json)을 items.json 에 반영한다.
subject: 22개정 과목 하나로 확정, unit: 22개정 단원. 단원 순서는 gichul-moa/data/unit_order.json 에 저장."""
import json, sys, collections
sys.path.insert(0, "tools")
from taxonomy import UNITS
from subtaxonomy import S as SUB
import os
items = json.load(open("data/items.json"))
u = json.load(open("data/units.json")); m = json.load(open("data/units_manual.json"))
miss = collections.Counter()
subs = json.load(open("data/subs.json")) if os.path.exists("data/subs.json") else {}
msub = json.load(open("data/subs_manual.json")) if os.path.exists("data/subs_manual.json") else {}
for it in items:
    if it["subj15"] in ("국어", "영어"):
        continue
    v = u.get(it["id"])
    if it["id"] in m:
        it["subject"], it["unit"] = m[it["id"]]
    elif v:
        it["subject"], it["unit"] = v["subject"], v["unit"]
    else:
        miss[it["subj15"]] += 1
    sv = subs.get(it["id"])
    it["sub"] = sv["sub"] if sv and (it["subject"], it.get("unit")) in SUB and sv["sub"] in [n for n, _ in SUB[(it["subject"], it["unit"])]] else None
    if it["id"] in msub:
        it["sub"] = msub[it["id"]]
    assert it.get("unit") is None or it["unit"] in UNITS[it["subject"]], it["id"]
json.dump(items, open("data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
# 사이트용: 영어 듣기(1~17번)는 문제집에 넣지 않는다
site = [it for it in items if not (it["subj15"] == "영어" and it["no"] <= 17)]
json.dump(site, open("gichul-moa/data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
order = {s: UNITS[s] for s in UNITS}
order["_subs"] = {f"{a}/{b}": [n for n, _ in v] for (a, b), v in SUB.items()}
json.dump(order, open("gichul-moa/data/unit_order.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("missing", dict(miss))
print(collections.Counter(type(it["subject"]).__name__ for it in items))
