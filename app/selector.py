"""문항 고르기 규칙 (작업기와 옵션 생성기가 같이 쓴다)."""

SUBJECT_ORDER = ["국어", "공통수학1", "공통수학2", "대수", "미적분Ⅰ", "확률과 통계", "미적분Ⅱ", "기하", "영어",
                 "통합사회", "통합과학", "물리학", "화학", "생명과학", "지구과학",
                 "역학과 에너지", "전자기와 양자", "화학 반응의 세계", "물질과 에너지",
                 "세포와 물질대사", "생물의 유전", "지구시스템과학", "행성우주과학"]
TYPE_NAME = {"학평": "학력평가(교육청)", "모평": "모의평가(평가원)", "수능": "수능"}
MAX_ITEMS = 1500
_ORDER = {s: i for i, s in enumerate(SUBJECT_ORDER)}


def subjects_of(it):
    s = it["subject"]
    return s if isinstance(s, list) else [s]


def subj_key(it):
    return min(_ORDER.get(s, 99) for s in subjects_of(it))


def select(items, q):
    """q: {subjects, grades, years, months, types, units, sort}. 빈 목록은 '전체'."""
    S = set(q.get("subjects") or [])
    G = set(q.get("grades") or [])
    Y = set(int(y) for y in (q.get("years") or []))
    M = set(int(m) for m in (q.get("months") or []))
    T = set(q.get("types") or [])
    U = set(q.get("units") or [])
    out = []
    for it in items:
        if S and not (S & set(subjects_of(it))):
            continue
        if G and it["grade"] not in G:
            continue
        if Y and it["year"] not in Y:
            continue
        if M and it["month"] not in M:
            continue
        if T and it["type"] not in T:
            continue
        if U and it.get("unit") not in U:
            continue
        out.append(it)
    if q.get("sort") == "unit":
        out.sort(key=lambda it: (subj_key(it), it.get("unit") or "", it["year"], it["month"], it["no"]))
    else:
        out.sort(key=lambda it: (subj_key(it), -it["year"], -it["month"], it["grade"], it["section"] or "", it["no"]))
    return out
