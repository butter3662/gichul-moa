"""카탈로그의 모든 문제지를 분리해 data/regions/<파일명>.json 에 저장하고 요약을 출력한다."""
import sys, os, json, collections
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/home/claude/tools")
import split as S

RAW = "/home/claude/raw"
OUT = "/home/claude/data/regions"
os.makedirs(OUT, exist_ok=True)


def work(arg):
    name, mode = arg
    out = OUT if mode == "q" else OUT + "_expl"
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, name + ".json")
    try:
        items = S.split(os.path.join(RAW, name), mode)
        json.dump(items, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
        with open("/home/claude/data/progress.txt", "a") as f:
            f.write(name + "\n")
        return name, items, None
    except Exception as e:
        return name, None, repr(e)[:100]


if __name__ == "__main__":
    cat = json.load(open("/home/claude/data/catalog.json", encoding="utf-8"))
    KIND = sys.argv[1] if len(sys.argv) > 1 else "문제"
    MODE = "q" if KIND == "문제" else "expl"
    ONLY = set(os.environ.get("ONLY", "").split(",")) - {""}
    jobs = [(e, f) for e in cat for f in e["files"] if f["kind"] == KIND and (not ONLY or e["id"] in ONLY)]
    names = [f["name"] for e, f in jobs]
    meta = {f["name"]: (e["id"], f["subject"]) for e, f in jobs}
    res = {}
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for name, items, err in ex.map(work, [(n, MODE) for n in names]):
            res[name] = (items, err)
    rows = []
    for name in names:
        items, err = res[name]
        eid, subj = meta[name]
        if err:
            rows.append((eid, subj, name, "ERR", err))
            continue
        q = [it for it in items if it["kind"] == "q"]
        by = collections.defaultdict(list)
        for it in q:
            by[it["section"]].append(it["no"])
        desc = "; ".join(f"{k or '-'}:{len(v)}({min(v)}-{max(v)})" for k, v in by.items()) if q else "0"
        bad = []
        for k, v in by.items():
            exp = list(range(min(v), max(v) + 1))
            if sorted(v) != exp:
                bad.append(k or "-")
        rows.append((eid, subj, name, "BAD" if (bad or not q) else "ok", desc))
    with open(f"/home/claude/data/split_summary_{MODE}.tsv", "w", encoding="utf-8") as f:
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    c = collections.Counter(r[3] for r in rows)
    print(c)
