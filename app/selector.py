"""문항 고르기 규칙 (작업기와 옵션 생성기가 같이 쓴다)."""

SUBJECT_ORDER = ["국어", "공통수학1", "공통수학2", "대수", "미적분Ⅰ", "확률과 통계", "미적분Ⅱ", "기하", "영어",
                 "통합사회", "통합과학", "물리학", "화학", "생명과학", "지구과학",
                 "역학과 에너지", "전자기와 양자", "화학 반응의 세계", "물질과 에너지",
                 "세포와 물질대사", "생물의 유전", "지구시스템과학", "행성우주과학"]
TYPE_NAME = {"학평": "학력평가(교육청)", "모평": "모의평가(평가원)", "수능": "수능", "예시": "수능 예시문항"}
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
    if it["type"] == "예시":
        return 2028
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
        ex = it["type"] == "예시"          # 수능 예시문항은 2028학년도를 골랐을 때만
        if ex and 2028 not in Y:
            continue
        if Y and hak_year(it) not in Y:
            continue
        if M and not ex and it["month"] not in M:
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
        out.sort(key=lambda it: (-hak_year(it), it["type"] != "예시", -it["year"], -it["month"], it["grade"], it["subj15"], it["section"] or "", it["no"]))
    return out


def random_pick(items, q, sent):
    """랜덤 한 문제: q = {mode:'random', area:'국어'|'수학'|'영어', subjects, grades}
    - 2022학년도 이후 문항에서 먼저 고르고, 다 쓰면 그 전 문항에서 고른다
    - 수학은 4점 문항만, 국어는 지문 단위(같은 지문의 문항 전부)
    - sent: 이미 보낸 문항 id 집합. 반환: (문항 목록, 2022학년도 이전에서 골랐는지) / 없으면 ([], None)"""
    import random
    area = q.get("area")
    S = set(q.get("subjects") or [])
    G = set(q.get("grades") or [])
    groups = {}
    for it in items:
        if it["type"] == "예시":
            continue
        if area == "국어":
            if it["subj15"] != "국어" or (S and it.get("genre") not in S):
                continue
        elif area == "수학":
            if it["subj15"] != "수학" or it.get("pts") != 4 or (S and it["subject"] not in S):
                continue
        elif area == "영어":
            if it["subj15"] != "영어":
                continue
        else:
            continue
        if G and it["grade"] not in G:
            continue
        key = ((it.get("passage") or {}).get("key") or it["id"]) if area == "국어" else it["id"]
        groups.setdefault(key, []).append(it)
    new, old = [], []
    for g in groups.values():
        if any(it["id"] in sent for it in g):
            continue
        (new if hak_year(g[0]) >= 2022 else old).append(g)
    for pool, is_old in ((new, False), (old, True)):
        if pool:
            g = random.choice(pool)
            return sorted(g, key=lambda it: it["no"]), is_old
    return [], None
