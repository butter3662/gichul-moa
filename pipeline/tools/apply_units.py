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
# 배점: 문제 글의 [2점]/[3점]/[4점]. 수학과 선택 과학만(통합과학·통합사회·국어·영어 제외)
import re
T = json.load(open("data/texts.json")) if os.path.exists("data/texts.json") else {}
PUA_D = {0xE034 + i: str((i + 1) % 10) for i in range(10)}
SCI = ("물리학", "화학", "생명과학", "지구과학")
def pts_of(it):
    t = ((T.get(it["id"]) or {}).get("q") or "").translate(PUA_D)
    m = re.findall(r"\[\s*([234])\s*점\s*\]", t)
    return int(m[-1]) if m else None
guess = collections.defaultdict(collections.Counter)
def era(it):   # 수학 교육과정: 2022 개정은 고1 2025년, 고2 2026년, 고3 2028년 시행분부터
    start = {"고1": 2025, "고2": 2026, "고3": 2028}[it["grade"]]
    return 2022 if it["year"] >= start else 2015
def gkey(it):
    return (it["grade"], era(it), it.get("section") is not None, it["no"])
for it in items:
    it.pop("pts", None)
    if it["subj15"] == "수학" or it["subj15"].startswith(SCI):
        p = pts_of(it)
        if it["subj15"] != "수학":
            p = 3 if p == 3 else 2          # 과탐은 2점·3점뿐, 표시 없으면 2점
        it["pts"] = p
        if p and it["subj15"] == "수학":
            guess[gkey(it)][p] += 1
for it in items:   # 수학에서 배점 표시를 못 읽은 문항은 같은 교육과정·학년·번호의 배점 (같은 번호면 배점이 같음)
    if it["subj15"] == "수학" and not it.get("pts"):
        g = guess[gkey(it)]
        it["pts"] = g.most_common(1)[0][0] if g else 3
PM = json.load(open("data/pts_manual.json")) if os.path.exists("data/pts_manual.json") else {}
for it in items:
    if it["id"] in PM:
        it["pts"] = PM[it["id"]]
json.dump(items, open("data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
# 사이트용: 영어 듣기(1~17번)는 문제집에 넣지 않는다
site = [it for it in items if not (it["subj15"] == "영어" and it["no"] <= 17)]
json.dump(site, open("gichul-moa/data/items.json", "w", encoding="utf-8"), ensure_ascii=False)
order = {s: UNITS[s] for s in UNITS}
order["_subs"] = {f"{a}/{b}": [n for n, _ in v] for (a, b), v in SUB.items()}
json.dump(order, open("gichul-moa/data/unit_order.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("missing", dict(miss))
print("pts", collections.Counter((it["subj15"] == "수학", it.get("pts")) for it in items if "pts" in it))
print(collections.Counter(type(it["subject"]).__name__ for it in items))
