"""국어 문항을 독서/문학/화법과 작문/언어와 매체/화작·문법으로 나눠 data/genre.json 에 저장한다.
- 선택 과목(section)이 있으면 그대로
- 공통+선택 체제(2022학년도 이후) 고3: 공통 1~17 독서, 18~34 문학
- 그 밖(고1·고2, 옛 체제 고3): 2015 교육과정 학평은 1~15 화작·문법,
  나머지는 지문 끝의 '작가, 「작품」'·줄거리·작자 미상이 있으면 문학, 발표·토론·초고 등이면 화작·문법, 아니면 독서
새로 생긴 문항만 계산한다."""
import os, re, json, pymupdf
pymupdf.TOOLS.mupdf_display_errors(False)
items = json.load(open("data/items.json", encoding="utf-8"))
OUT = "data/genre.json"
G = json.load(open(OUT)) if os.path.exists(OUT) else {}
LIT = re.compile(r"[가-힣]{2,5}(\s*원작)?(,\s*[가-힣]{2,4}\s*각색)?,\s*[｢「『][^｣」』]{1,40}[｣」』]|(앞부분|중략|뒷부분|전체)\s*(부분\s*)?(의\s*)?줄거리|작자\s*미상|\[아니리\]|\[중모리\]|\[자진모리\]")
HW = re.compile(r"\[초고\]|\[발표|\[토론|발표자|사회자|청중|면담|작문 상황|글쓰기 (계획|과정)|학생\s?[1-3]|\[대화\]|강연|협상|\[자료\]")
docs = {}


def txt(part):
    if not part:
        return ""
    f = ("fixed/" if part.get("src") == "fixed" else "raw/") + part["file"]
    if not os.path.exists(f):
        return ""
    d = docs.setdefault(f, pymupdf.open(f))
    return re.sub(r"\s+", " ", " ".join(d[s["page"]].get_text(clip=pymupdf.Rect(s["rect"])) for s in part["segs"]))


def hak(it):
    return 2028 if it["type"] == "예시" else it["year"] + (1 if it["type"] in ("모평", "수능") else 0)


def era22(it):
    return it["year"] >= {"고1": 2025, "고2": 2026, "고3": 2028}[it["grade"]] or it["type"] == "예시"


cache = {}
n = 0
for it in items:
    if it["subj15"] != "국어" or it["id"] in G:
        continue
    if it.get("section"):
        g = it["section"]
    elif it["grade"] == "고3" and 2022 <= hak(it) < 2028 and it["type"] != "예시":
        g = "독서" if it["no"] <= 17 else "문학"
    elif not era22(it) and it["no"] <= 15:
        g = "화작·문법"
    else:
        key = (it.get("passage") or {}).get("key") or it["id"]
        if key not in cache:
            t = txt(it.get("passage")) or txt(it["q"])
            cache[key] = "문학" if LIT.search(t) else ("화작·문법" if HW.search(t) or not it.get("passage") else "독서")
        g = cache[key]
    G[it["id"]] = g
    n += 1
json.dump(G, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("genre", n, "new;", len(G), "total")
