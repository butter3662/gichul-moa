"""문항 고르기 규칙 (작업기와 옵션 생성기가 같이 쓴다)."""

SUBJECT_ORDER = ["국어", "공통수학1", "공통수학2", "대수", "미적분Ⅰ", "확률과 통계", "미적분Ⅱ", "기하", "영어",
                 "통합사회", "통합과학", "물리학", "화학", "생명과학", "지구과학",
                 "역학과 에너지", "전자기와 양자", "화학 반응의 세계", "물질과 에너지",
                 "세포와 물질대사", "생물의 유전", "지구시스템과학", "행성우주과학"]
TYPE_NAME = {"학평": "학력평가(교육청)", "모평": "모의평가(평가원)", "수능": "수능"}
MAX_ITEMS = 1500
_ORDER = {s: i for i, s in enumerate(SUBJECT_ORDER)}
import os as _os, json as _json
try:
    UNIT_ORDER = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "data", "unit_order.json"), encoding="utf-8"))
except OSError:
    UNIT_ORDER = {}
SUB_ORDER = UNIT_ORDER.pop("_subs", {})


def sub_key(it):
    ss = SUB_ORDER.get(f"{subjects_of(it)[0]}/{it.get('unit')}", [])
    return ss.index(it["sub"]) if it.get("sub") in ss else 99


def unit_key(it):
    us = UNIT_ORDER.get(subjects_of(it)[0], [])
    return us.index(it["unit"]) if it.get("unit") in us else 99


def subjects_of(it):
    s = it["subject"]
    return s if isinstance(s, list) else [s]


def subj_key(it):
    return min(_ORDER.get(s, 99) for s in subjects_of(it))


def sub_ok(it, B):
    """B: {"과목/단원/소단원"}. 소단원을 하나라도 고른 대단원만 소단원으로 거른다."""
    if not B:
        return True
    pre = f"{subjects_of(it)[0]}/{it.get('unit')}/"
    mine = {x for x in B if x.startswith(pre)}
    return not mine or pre + str(it.get("sub")) in mine


def unit_ok(it, U):
    """U: {"과목/단원"}. 단원을 하나라도 고른 과목만 단원으로 거른다 (예전 형식 "단원"도 허용)."""
    for s in subjects_of(it):
        mine = {x for x in U if x.startswith(s + "/")}
        if mine:
            return f"{s}/{it.get('unit')}" in mine
    return not any("/" not in x for x in U) or it.get("unit") in U


def hak_year(it):
    """시험지에 적힌 학년도: 모평·수능은 시행 연도+1, 학평은 시행 연도"""
    return it["year"] + 1 if it["type"] in ("모평", "수능") else it["year"]


def select(items, q):
    """q: {subjects, grades, years, months, types, units, sort}. 빈 목록은 '전체'."""
    S = set(q.get("subjects") or [])
    G = set(q.get("grades") or [])
    Y = set(int(y) for y in (q.get("years") or []))
    M = set(int(m) for m in (q.get("months") or []))
    T = set(q.get("types") or [])
    U = set(q.get("units") or [])
    B = set(q.get("subs") or [])
    P = set(int(x) for x in (q.get("pts") or []))
    out = []
    for it in items:
        if S and not (S & set(subjects_of(it))):
            continue
        if G and it["grade"] not in G:
            continue
        if Y and hak_year(it) not in Y:
            continue
        if M and it["month"] not in M:
            continue
        if T and it["type"] not in T:
            continue
        if U and not unit_ok(it, U):
            continue
        if B and not sub_ok(it, B):
            continue
        if P and it.get("pts") is not None and it["pts"] not in P:
            continue
        out.append(it)
    if q.get("sort") == "unit":
        out.sort(key=lambda it: (subj_key(it), unit_key(it), sub_key(it), -it["year"], -it["month"], it["no"]))
    else:
        out.sort(key=lambda it: (subj_key(it), -it["year"], -it["month"], it["grade"], it["section"] or "", it["no"]))
    return out
