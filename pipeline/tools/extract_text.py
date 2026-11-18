"""국어·영어를 뺀 문항의 문제 텍스트와 해설 텍스트를 뽑아 data/texts.json 에 저장한다.
{item_id: {"q": 문제 텍스트, "e": 해설 텍스트}}"""
import os, json, pymupdf
from concurrent.futures import ProcessPoolExecutor

pymupdf.TOOLS.mupdf_display_errors(False)
RAW, FIXED = "/home/claude/raw", "/home/claude/fixed"
items = json.load(open("/home/claude/gichul-moa/data/items.json", encoding="utf-8"))
items = [it for it in items if it["subj15"] not in ("국어", "영어")]


def txt(part):
    if not part:
        return ""
    d = pymupdf.open(os.path.join(FIXED if part["src"] == "fixed" else RAW, part["file"]))
    return " ".join(d[s["page"]].get_text(clip=pymupdf.Rect(s["rect"])) for s in part["segs"]).replace("\n", " ")


def work(chunk):
    out = {}
    for it in chunk:
        out[it["id"]] = {"q": txt(it["q"])[:3000], "e": txt(it.get("e"))[:3000]}
    return out


if __name__ == "__main__":
    OUT = "/home/claude/data/texts.json"
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    items = [it for it in items if it["id"] not in old]  # 새 문항만 뽑는다
    by_file = {}
    for it in items:
        by_file.setdefault(it["q"]["file"], []).append(it)
    chunks = list(by_file.values())
    res = dict(old)
    with ProcessPoolExecutor(2) as ex:
        for r in ex.map(work, chunks):
            res.update(r)
    json.dump(res, open("/home/claude/data/texts.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(len(res), "items;", sum(1 for v in res.values() if len(v["q"].strip()) < 20), "with little question text")
