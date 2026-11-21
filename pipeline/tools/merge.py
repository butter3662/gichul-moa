"""문항 영역·해설 영역·정답을 합쳐 data/items.json (문항 주석 DB)을 만든다.
문항 1개 = 레코드 1개:
  id, exam(시험 id), grade, year(시행년), month, type, title,
  subj15(원 과목), subject(22개정 표시 과목, 미정이면 후보 목록), section, no,
  q:{file, src, segs}, passage:{key, file, src, segs} | None,
  e:{file, src, segs} | None, answer, unit(단원, 나중에 채움)"""
import os, re, json, collections, pymupdf

pymupdf.TOOLS.mupdf_display_errors(False)
D = "/home/claude/data"
RAW = "/home/claude/raw"
cat = json.load(open(f"{D}/catalog.json", encoding="utf-8"))
manual = json.load(open(f"{D}/answers_manual.json", encoding="utf-8"))

SCI = {"물리학Ⅰ": "물리학1", "화학Ⅰ": "화학1", "생명과학Ⅰ": "생명과학1", "지구과학Ⅰ": "지구과학1",
       "물리학Ⅱ": "물리학2", "화학Ⅱ": "화학2", "생명과학Ⅱ": "생명과학2", "지구과학Ⅱ": "지구과학2"}
FIXED22 = {"국어": "국어", "영어": "영어", "통합과학": "통합과학", "통합사회": "통합사회",
           "물리학1": "물리학", "화학1": "화학", "생명과학1": "생명과학", "지구과학1": "지구과학",
           "확률과통계": "확률과 통계", "미적분": "미적분Ⅱ", "기하": "기하"}
SPLIT22 = {"물리학2": ["역학과 에너지", "전자기와 양자"], "화학2": ["화학 반응의 세계", "물질과 에너지"],
           "생명과학2": ["세포와 물질대사", "생물의 유전"], "지구과학2": ["지구시스템과학", "행성우주과학"]}
MATH_SEC = {"확률과 통계": "확률과 통계", "미적분": "미적분Ⅱ", "기하": "기하"}


def subject22(subj15, section, grade):
    if subj15 == "수학":
        if section in MATH_SEC:
            return MATH_SEC[section]
        return ["공통수학1", "공통수학2"] if grade == "고1" else ["대수", "미적분Ⅰ"]
    if subj15 in FIXED22:
        return FIXED22[subj15]
    return SPLIT22.get(subj15, subj15)


def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return None


def seg_h(segs):
    return sum(s["rect"][3] - s["rect"][1] for s in segs)


def set_range(no):
    a, b = no.split("~")
    return int(a), int(b)


def text_of(name, src, segs):
    path = os.path.join(RAW if src == "raw" else RAW.replace("raw", "fixed"), name)
    d = pymupdf.open(path)
    return "".join(d[s["page"]].get_text(clip=pymupdf.Rect(s["rect"])) for s in segs)


items = []
seen_ids = set()
stats = collections.Counter()
BAD_Q = {"2023학년도-6월-모의평가-지구과학2-문제.pdf"}  # 실제 내용은 생명과학Ⅱ
SKIP_EXPL = {"2024_10-고3-물리학Ⅱ-정답-및-해설.pdf"}  # 다른 과목(지구과학Ⅰ) 쪽이 잘못 들어 있음
ONLY = set(os.environ.get("ONLY", "").split(",")) - {""}  # 일부 시험만 다시 만들기
headed = json.load(open(f"{D}/headed_answers.json"))
for e in cat:
    if ONLY and e["id"] not in ONLY:
        continue
    files = e["files"]
    # 과목별 파일 묶기 (국어·수학은 선택과목이 별도 파일인 경우가 있음)
    qfiles = [f for f in files if f["kind"] == "문제"]
    efiles = [f for f in files if f["kind"] == "해설"]
    afiles = [f for f in files if f["kind"] == "정답"]
    # 정답표: 과목별 → {section: {no: ans}}
    answers = collections.defaultdict(lambda: collections.defaultdict(dict))

    def add_ans(subj, res, override=False):
        for sec, dd in res.items():
            if not isinstance(dd, dict):
                continue
            s15 = SCI.get(sec, subj)
            sec2 = None if (sec == "-" or sec in SCI) else sec
            for no, a in dd.items():
                if override or no not in answers[(s15, sec2)]:
                    answers[(s15, sec2)][no] = a

    for f in efiles + afiles:  # 정답 파일이 뒤에 오므로 덮어쓰기 우선
        r = load(f"{D}/answers/{f['name']}.json") or {}
        add_ans(f["subject"], r, override=(f["kind"] == "정답"))
    for s15h, tab in headed.get(e["id"], {}).items():  # 해설 속 'X 정답' 표 (파일 과목명이 틀린 경우 대비)
        add_ans(s15h, {"-": tab}, override=True)
    for f in files:
        if f["name"] in manual:
            add_ans(f["subject"], manual[f["name"]], override=True)
    for k, v in manual.items():
        if k.startswith(f"EXAM:{e['id']}:"):
            add_ans(k.split(":")[-1], v, override=True)

    # 해설 영역: (과목, section, no) → (file, src, segs)
    expl = {}
    for f in efiles:
        regs = [] if f["name"] in SKIP_EXPL else (load(f"{D}/regions_expl/{f['name']}.json") or [])
        has_head = any(it.get("section") in SCI for it in regs)
        for it in regs:
            if it["kind"] != "q" or not it["segments"]:
                continue
            if it.get("section") == "기타" or (has_head and it.get("section") is None and f["subject"] not in ("국어", "수학", "영어")):
                continue
            s15 = SCI.get(it["section"], f["subject"])
            sec = None if it["section"] in SCI else it["section"]
            if f["subject"] == "국어" and sec is None and it["no"] >= 35 and re.search(r"화법|작문", f["name"]):
                sec = "화법과 작문"
            if f["subject"] == "국어" and sec is None and it["no"] >= 35 and re.search(r"언어|매체", f["name"]):
                sec = "언어와 매체"
            key = (s15, sec, it["no"])
            if key not in expl:
                expl[key] = dict(file=f["name"], src=it.get("src", "raw"), segs=it["segments"])

    for f in qfiles:
        regs = load(f"{D}/regions/{f['name']}.json") or []
        subj_file = f["subject"]
        sets = [it for it in regs if it["kind"] == "set" and it["segments"] and seg_h(it["segments"]) > 80]
        for it in regs:
            if it["kind"] != "q":
                continue
            s15 = SCI.get(it["section"], subj_file)
            if s15 == "과학탐구":
                continue
            sec = None if it["section"] in SCI else it["section"]
            if subj_file in ("확률과통계", "미적분", "기하"):
                sec = {"확률과통계": "확률과 통계", "미적분": "미적분", "기하": "기하"}[subj_file] if it["no"] >= 23 else None
                s15 = "수학"
            if s15 == "국어" and sec is None and it["no"] >= 35:
                if re.search(r"화법|작문", f["name"]):
                    sec = "화법과 작문"
                elif re.search(r"언어|매체", f["name"]):
                    sec = "언어와 매체"
            passage = None
            for st in sets:
                a, b = set_range(st["no"])
                if a <= it["no"] <= b and st["section"] == it["section"]:
                    passage = dict(key=f"{f['name']}#{st['no']}#{st['section']}", file=f["name"],
                                   src=st.get("src", "raw"), segs=st["segments"])
            ek = (s15 if subj_file not in ("확률과통계", "미적분", "기하") else subj_file, sec, it["no"])
            ex = expl.get((s15, sec, it["no"])) or expl.get(ek)
            akeys = [(s15, sec), (subj_file, sec), (subj_file, None)]
            ans = None
            for k in akeys:
                if k in answers and str(it["no"]) in answers[k]:
                    ans = answers[k][str(it["no"])]
                    break
            if ans is None and ex:
                tx = text_of(ex["file"], ex["src"], ex["segs"])
                m = re.search(r"정답\s*[:：]?\s*([①②③④⑤]|\d{1,3})(?!\d)", tx)
                if m:
                    ans = m.group(1)
                else:
                    ms = re.findall(r"([①②③④⑤])\s*(?:이다|입니다|가 정답|이 정답)", tx)
                    if ms:
                        ans = ms[-1]
            s22 = subject22(s15, sec, e["grade"])
            if e["grade"] == "고1" and e["month"] == 3 and s15 == "수학":
                continue  # 고1 3월 수학은 중학 범위라 제외 (사용자 결정)
            if f["name"] in BAD_Q:
                continue  # 원본 사이트에 다른 과목 시험지가 잘못 올라가 있음
            rid = f"{e['id']}|{s15}|{sec or '-'}|{it['no']}"
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            rec = dict(id=rid, exam=e["id"], grade=e["grade"],
                       year=e["year"], month=e["month"], type=e["type"], title=e["title"],
                       subj15=s15, subject=s22, section=sec, no=it["no"],
                       q=dict(file=f["name"], src=it.get("src", "raw"), segs=it["segments"]),
                       passage=passage, e=ex, answer=ans, unit=None)
            items.append(rec)
            stats["q"] += 1
            stats["has_e"] += ex is not None
            stats["has_ans"] += ans is not None
            stats["has_passage"] += passage is not None

if ONLY:
    items = [r for r in json.load(open(f"{D}/items.json", encoding="utf-8")) if r["exam"] not in ONLY] + items
ids = collections.Counter(r["id"] for r in items)
dups = [k for k, v in ids.items() if v > 1]
# 손으로 만든 문항(예: 2028 수능 예시문항, 이미지 시험지)
if os.path.exists(f"{D}/extra_items.json"):
    have = {it["id"] for it in items}
    items += [it for it in json.load(open(f"{D}/extra_items.json", encoding="utf-8")) if it["id"] not in have]
import unclip
print("unclipped", unclip.fix_items(items, RAW, RAW.replace("raw", "fixed")))
json.dump(items, open(f"{D}/items.json", "w", encoding="utf-8"), ensure_ascii=False)
print(dict(stats), "dup ids", len(dups), dups[:5])
by = collections.Counter((r["subj15"]) for r in items)
print(by)
noans = collections.Counter(r["exam"] + " " + r["subj15"] for r in items if r["answer"] is None)
print("no answer:", noans.most_common(30))
