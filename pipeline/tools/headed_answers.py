"""해설 파일 안의 'X 정답 1 ① 2 ③ …' 표를 과목 이름 기준으로 읽는다 (파일 과목명과 무관).
출력: data/headed_answers.json {exam_id: {subj15: {no: ans}}}"""
import json, re, pymupdf, os
pymupdf.TOOLS.mupdf_display_errors(False)
G = {"檾": "①", "檿": "②", "櫀": "③", "櫁": "④", "櫂": "⑤"}
MAP = {"물리학Ⅰ": "물리학1", "화학Ⅰ": "화학1", "생명과학Ⅰ": "생명과학1", "지구과학Ⅰ": "지구과학1",
       "물리학Ⅱ": "물리학2", "화학Ⅱ": "화학2", "생명과학Ⅱ": "생명과학2", "지구과학Ⅱ": "지구과학2"}
cat = json.load(open("data/catalog.json"))
NEW = set(os.environ.get("ONLY", "").split(",")) - {""}
if NEW:
    cat = [e for e in cat if e["id"] in NEW]
out = json.load(open("data/headed_answers.json")) if os.path.exists("data/headed_answers.json") else {}
for e in cat:
    out[e["id"]] = {}  # 이번에 처리하는 시험은 새로 읽는다
    for f in e["files"]:
        if f["kind"] not in ("해설", "정답"):
            continue
        p = os.path.join("raw", f["name"])
        try:
            d = pymupdf.open(p)
        except Exception:
            continue
        tx = " ".join(pg.get_text() for pg in d)
        for a, b in G.items():
            tx = tx.replace(a, b)
        tx = re.sub(r"\s+", " ", tx)
        for m in re.finditer(r"(물리학|화학|생명\s?과학|지구\s?과학)\s?(Ⅰ|Ⅱ)\s?정답", tx):
            s = MAP[m.group(1).replace(" ", "") + m.group(2)]
            seg = tx[m.end(): m.end() + 260]
            pairs = re.findall(r"(\d{1,2})\s?([①②③④⑤])", seg)
            tab = {}
            for no, an in pairs:
                n = int(no)
                if n == len(tab) + 1:
                    tab[str(n)] = an
            if len(tab) >= 15:
                out.setdefault(e["id"], {}).setdefault(s, tab)
json.dump(out, open("data/headed_answers.json", "w"), ensure_ascii=False)
items = json.load(open("data/items.json"))
bad = {}
for it in items:
    t = out.get(it["exam"], {}).get(it["subj15"])
    if t and str(it["no"]) in t and it["section"] in (None, "-") and it["answer"] != t[str(it["no"])]:
        bad.setdefault(it["exam"] + "|" + it["subj15"], []).append(it["no"])
print(sum(len(v) for v in out.values()), "tables")
for k, v in sorted(bad.items()):
    print(k, len(v))
