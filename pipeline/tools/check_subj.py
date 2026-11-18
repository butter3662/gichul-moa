"""과탐·통합 문항 묶음(시험×과목)의 문제 텍스트가 실제로 그 과목인지 확인한다."""
import json, re, sys, collections
sys.path.insert(0, "tools")
from taxonomy import K
exec(open("tools/classify.py").read().split("# 수식 패턴")[0].split("items = json")[1].split("\n", 1)[1].split("# 키워드 정리")[0]) if False else None
texts = json.load(open("data/texts.json")); items = json.load(open("data/items.json"))
S15 = {"물리학1": ["물리학"], "화학1": ["화학"], "생명과학1": ["생명과학"], "지구과학1": ["지구과학"],
       "물리학2": ["역학과 에너지", "전자기와 양자"], "화학2": ["물질과 에너지", "화학 반응의 세계"],
       "생명과학2": ["세포와 물질대사", "생물의 유전"], "지구과학2": ["지구시스템과학", "행성우주과학"]}
FAM = {}
for s15, subs in S15.items():
    fam = re.sub(r"[12]$", "", s15)
    FAM.setdefault(fam, set()).update(w for (s, u), ws in K.items() if s in subs for w in ws if len(w) >= 2)
# 다른 계열과 겹치는 낱말 제거
cnt = collections.Counter(w for ws in FAM.values() for w in ws)
FAM = {f: {w for w in ws if cnt[w] == 1} for f, ws in FAM.items()}
g = collections.defaultdict(collections.Counter)
for it in items:
    if it["subj15"] not in S15:
        continue
    q = re.sub(r"\s+", "", texts.get(it["id"], {}).get("q", ""))
    for f, ws in FAM.items():
        g[(it["exam"], it["subj15"], it["q"]["file"])][f] += sum(q.count(w) for w in ws)
for (ex, s, fn), c in sorted(g.items()):
    tot = sum(c.values())
    best = c.most_common(1)[0][0] if tot else "-"
    if tot and best != re.sub(r"[12]$", "", s):
        print(ex, s, fn, dict(c))
