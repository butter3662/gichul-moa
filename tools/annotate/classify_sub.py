"""items.json 의 (과목, 대단원)에 맞춰 소단원을 정한다. 출력: data/subs.json {id: {sub, score, margin, conf}}"""
import json, re, sys
sys.path.insert(0, "tools")
from subtaxonomy import S
src = open("tools/classify.py").read(); ns = {}
exec("import re\n" + src[src.index("PUA = {}"):src.index("# 수식 패턴")], ns)
norm = ns["norm"]
items = json.load(open("data/items.json")); texts = json.load(open("data/texts.json"))
def intent(e):
    m = re.search(r"\[?출제\s*의도\]?\s*:?(.{0,80})", e or "")
    return m.group(1) if m else ""
out = {}
for it in items:
    key = (it["subject"], it.get("unit"))
    if key not in S:
        continue
    subs = S[key]
    if len(subs) == 1:
        out[it["id"]] = dict(sub=subs[0][0], score=9, margin=1, conf="high"); continue
    t = texts.get(it["id"], {})
    q = norm(t.get("q")); ie = norm(intent(t.get("e")))
    sc = []
    for name, kws in subs:
        v = 0.0
        for kw in kws:
            try:
                v += min(len(re.findall(kw, q)), 4) + 3 * min(len(re.findall(kw, ie)), 2)
            except re.error:
                v += min(q.count(kw), 4) + 3 * min(ie.count(kw), 2)
        sc.append((v, name))
    best = max(sc, key=lambda x: x[0])
    rest = sorted((v for v, n in sc if n != best[1]), reverse=True)
    second = rest[0] if rest else 0
    margin = (best[0] - second) / (best[0] + 1e-9)
    conf = "high" if best[0] >= 3 and margin >= 0.3 else ("mid" if best[0] >= 1 and margin > 0 else "low")
    out[it["id"]] = dict(sub=best[1], score=round(best[0], 1), margin=round(margin, 2), conf=conf,
                         alt=[f"{n}:{v}" for v, n in sorted(sc, reverse=True)[1:3]])
json.dump(out, open("data/subs.json", "w"), ensure_ascii=False)
import collections
print(len(out), collections.Counter(v["conf"] for v in out.values()))
c = collections.Counter((it["subject"], v["conf"]) for it in items for v in [out.get(it["id"])] if v)
for k in sorted(c): print(k, c[k])
