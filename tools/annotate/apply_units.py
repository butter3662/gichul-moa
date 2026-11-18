"""분류 결과(data/units.json)와 수동 판정(data/units_manual.json)을 items.json 에 반영한다.
subject: 22개정 과목 하나로 확정, unit: 22개정 단원. 단원 순서는 gichul-moa/data/unit_order.json 에 저장."""
import json, sys, collections
sys.path.insert(0, "tools")
from taxonomy import UNITS
items = json.load(open("data/items.json"))
u = json.load(open("data/units.json")); m = json.load(open("data/units_manual.json"))
miss = collections.Counter()
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
    assert it.get("unit") is None or it["unit"] in UNITS[it["subject"]], it["id"]
json.dump(items, open("data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(items, open("gichul-moa/data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
json.dump(UNITS, open("gichul-moa/data/unit_order.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("missing", dict(miss))
print(collections.Counter(type(it["subject"]).__name__ for it in items))
