"""모든 해설·정답 PDF에서 정답표를 뽑아 data/answers/<파일명>.json 에 저장한다."""
import sys, os, json
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/home/claude/tools")
import answers as A

RAW = "/home/claude/raw"
OUT = "/home/claude/data/answers"
os.makedirs(OUT, exist_ok=True)


def work(arg):
    name, subj = arg
    try:
        res = A.parse(os.path.join(RAW, name), subj)
    except Exception as e:
        res = {"error": repr(e)[:100]}
    json.dump(res, open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    return name, sum(len(v) for k, v in res.items() if isinstance(v, dict))


if __name__ == "__main__":
    cat = json.load(open("/home/claude/data/catalog.json", encoding="utf-8"))
    ONLY = set(os.environ.get("ONLY", "").split(",")) - {""}
    jobs = [(f["name"], f["subject"]) for e in cat for f in e["files"] if f["kind"] in ("해설", "정답") and (not ONLY or e["id"] in ONLY)]
    with ProcessPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(work, jobs))
    zero = [n for n, c in res if c == 0]
    print("files", len(res), "zero", len(zero))
    for z in zero:
        print("ZERO", z)
