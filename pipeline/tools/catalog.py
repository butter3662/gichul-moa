"""시험 목록(catalog.json)을 만든다.
입력: horaeng/titles.tsv, horaeng/links.txt, raw/ 폴더
출력: data/catalog.json — 시험별 {id, grade, year(시행년), month, type, title, files:[{name, subject, kind}]}"""
import re, json, os, urllib.parse, collections

H = "/home/claude/horaeng"
RAW = "/home/claude/raw"
titles = {}
for line in open(f"{H}/titles.tsv", encoding="utf-8"):
    g, y, i, t = (line.rstrip("\n").split("\t") + [""])[:4]
    titles[i] = (g, int(y), t.replace("&#8211;", "-").strip())

# 예전 목록: 원본 PDF가 이 컴퓨터에 없는 시험(이미 처리한 시험)은 예전 항목을 그대로 쓴다
OLDCAT = {}
if os.path.exists("/home/claude/data/catalog.json"):
    for e in json.load(open("/home/claude/data/catalog.json", encoding="utf-8")):
        OLDCAT[e["post"]] = e
KNOWN = {f["name"] for e in OLDCAT.values() for f in e["files"]}
files_by_post = collections.defaultdict(list)
for line in open(f"{H}/links.txt", encoding="utf-8"):
    m = re.match(r'(\d+) href="([^"]+)"', line.strip())
    if m:
        name = urllib.parse.unquote(m.group(2).rsplit("/", 1)[1])
        if os.path.exists(os.path.join(RAW, name)) or name in KNOWN:
            files_by_post[m.group(1)].append(name)

SUBJ = [  # (정규식, 내부 과목키) — 순서 중요
    (r"통합과학", "통합과학"), (r"통합사회", "통합사회"),
    (r"물리학?\s*-?\s*(2|Ⅱ|II)", "물리학2"), (r"물리학?\s*-?\s*(1|Ⅰ|I)", "물리학1"),
    (r"화학\s*-?\s*(2|Ⅱ|II)", "화학2"), (r"화학\s*-?\s*(1|Ⅰ|I)", "화학1"),
    (r"생명과학\s*-?\s*(2|Ⅱ|II)", "생명과학2"), (r"생명과학\s*-?\s*(1|Ⅰ|I)", "생명과학1"),
    (r"지구과학\s*-?\s*(2|Ⅱ|II)", "지구과학2"), (r"지구과학\s*-?\s*(1|Ⅰ|I)", "지구과학1"),
    (r"과학탐구", "과학탐구"), (r"사회탐구", "사회탐구"),
    (r"(^|[-_])과학([-_]|$)", "과학"), (r"(^|[-_])사회([-_]|$)", "사회"),
    (r"확률과\s*통계", "확률과통계"), (r"미적분", "미적분"), (r"기하", "기하"),
    (r"화법과\s*작문|언어와\s*매체", "국어"),
    (r"국어", "국어"), (r"수학", "수학"), (r"영어", "영어"),
]


def subject_of(name, grade):
    n = re.sub(r"\.(pdf|zip)$", "", name.replace(" ", "")).replace("대학수학능력시험", "").replace("대수능", "")
    for rx, key in SUBJ:
        if re.search(rx, n):
            if grade == "고1" and key in ("과학", "과학탐구"):
                return "통합과학"
            if grade == "고1" and key in ("사회", "사회탐구"):
                return "통합사회"
            return key
    return None


def kind_of(name):
    if name.endswith(".zip"):
        return "듣기파일"
    if "듣기" in name or "대본" in name:
        return "듣기대본"
    if "해설" in name:
        return "해설"
    if "정답" in name or "답지" in name or re.search(r"[-_]답([-_.]|$)", name):
        return "정답"
    if "문제" in name or "문항" in name or "문재" in name:
        return "문제"
    return "문제"


exams = []
for pid, (g, y, t) in titles.items():
    names = files_by_post.get(pid, [])
    if not names:
        continue
    blob = t + " " + " ".join(names)
    if "수능" in t or "대학수학능력" in blob:
        typ, month = "수능", 11
    elif "모의평가" in t or "모의평가" in blob:
        typ = "모평"
        month = int(re.search(r"(\d{1,2})월", t or blob).group(1))
    else:
        typ = "학평"
        mm = re.search(r"(\d{1,2})월", t) if t else None
        if mm:
            month = int(mm.group(1))
        else:
            c = collections.Counter(int(x) for n in names for x in re.findall(r"(\d{1,2})월", n))
            month = c.most_common(1)[0][0]
    if pid in OLDCAT and not any(os.path.exists(os.path.join(RAW, n)) for n in names):
        exams.append(OLDCAT[pid]); continue
    files = [dict(name=n, subject=subject_of(n, g), kind=kind_of(n)) for n in sorted(names)]
    # 문제/해설 파일이 뒤바뀐 경우 바로잡기
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    def txt(n):
        try:
            return "".join(p.get_text() for p in pymupdf.open(os.path.join(RAW, n)))
        except Exception:
            return ""
    for subj in {f["subject"] for f in files}:
        q = [f for f in files if f["subject"] == subj and f["kind"] == "문제"]
        e = [f for f in files if f["subject"] == subj and f["kind"] == "해설"]
        if len(q) == 1 and len(e) == 1:
            tq, te = txt(q[0]["name"]), txt(e[0]["name"])
            if "출제의도" in tq and "출제의도" not in te:
                q[0]["kind"], e[0]["kind"] = "해설", "문제"
                print("swapped", q[0]["name"], e[0]["name"])
    exams.append(dict(id=f"{y}-{month:02d}-{g}-{typ}", post=pid, grade=g, year=y, month=month,
                      type=typ, title=t, files=files))
exams.sort(key=lambda e: e["id"])
os.makedirs("/home/claude/data", exist_ok=True)
json.dump(exams, open("/home/claude/data/catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ids = collections.Counter(e["id"] for e in exams)
print("exams", len(exams), "dup ids", [k for k, v in ids.items() if v > 1])
unk = [(e["id"], f["name"]) for e in exams for f in e["files"] if not f["subject"] or f["kind"] == "문제?"]
print("unknown", len(unk))
for u in unk[:40]:
    print(*u)
