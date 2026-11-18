"""기출 모음 사이트 서버 (라즈베리파이용, Flask).
- 주석 DB(items.json)는 서버 안에서만 쓰고 브라우저로 보내지 않는다.
- 브라우저에는 고를 수 있는 선택지(과목·학년·연도·월·시험 종류·단원)만 보낸다.
- 선택하면 문제 PDF와 해설 PDF 두 개를 만들어 내려준다.
설정: 환경변수 SITE_PASSWORD(접속 비밀번호), DATA_DIR(기본 ../data)"""
import os, json, uuid, time, threading, collections, hmac
from flask import Flask, request, jsonify, send_file, Response, abort

import build_pdf

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", os.path.join(BASE, "..", "data"))
RAW = os.path.join(DATA, "raw")
FIXED = os.path.join(DATA, "fixed")
OUT = os.path.join(DATA, "out")
os.makedirs(OUT, exist_ok=True)
PASSWORD = os.environ.get("SITE_PASSWORD", "")

ITEMS = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))
SUBJECT_ORDER = ["국어", "공통수학1", "공통수학2", "대수", "미적분Ⅰ", "확률과 통계", "미적분Ⅱ", "기하", "영어",
                 "통합사회", "통합과학", "물리학", "화학", "생명과학", "지구과학",
                 "역학과 에너지", "전자기와 양자", "화학 반응의 세계", "물질과 에너지",
                 "세포와 물질대사", "생물의 유전", "지구시스템과학", "행성우주과학"]
TYPE_NAME = {"학평": "학력평가(교육청)", "모평": "모의평가(평가원)", "수능": "수능"}

app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="/static")
docs = build_pdf.Docs(RAW, FIXED)
lock = threading.Lock()


def subjects_of(it):
    s = it["subject"]
    return s if isinstance(s, list) else [s]


@app.before_request
def auth():
    if not PASSWORD:
        return
    a = request.authorization
    if not a or not hmac.compare_digest(a.password or "", PASSWORD):
        return Response("로그인이 필요합니다", 401, {"WWW-Authenticate": 'Basic realm="gichul"'})


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/options")
def options():
    subj = collections.Counter()
    units = collections.defaultdict(collections.Counter)
    years, months = set(), set()
    for it in ITEMS:
        for s in subjects_of(it):
            subj[s] += 1
            if it.get("unit") and not isinstance(it["subject"], list):
                units[s][it["unit"]] += 1
        years.add(it["year"])
        months.add(it["month"])
    order = {s: i for i, s in enumerate(SUBJECT_ORDER)}
    return jsonify(
        subjects=[dict(name=s, count=c) for s, c in sorted(subj.items(), key=lambda x: order.get(x[0], 99))],
        units={s: [u for u, _ in sorted(c.items())] for s, c in units.items()},
        grades=["고1", "고2", "고3"],
        years=sorted(years, reverse=True),
        months=sorted(months),
        types=[dict(key=k, name=v) for k, v in TYPE_NAME.items()],
    )


def select(q):
    S = set(q.get("subjects") or [])
    G = set(q.get("grades") or [])
    Y = set(int(y) for y in (q.get("years") or []))
    M = set(int(m) for m in (q.get("months") or []))
    T = set(q.get("types") or [])
    U = set(q.get("units") or [])
    out = []
    for it in ITEMS:
        subs = subjects_of(it)
        if S and not (S & set(subs)):
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
    sort = q.get("sort", "exam")
    if sort == "unit":
        out.sort(key=lambda it: (subs_key(it), it.get("unit") or "", it["year"], it["month"], it["no"]))
    else:
        out.sort(key=lambda it: (subs_key(it), -it["year"], -it["month"], it["grade"], it["section"] or "", it["no"]))
    return out


def subs_key(it):
    order = {s: i for i, s in enumerate(SUBJECT_ORDER)}
    return min(order.get(s, 99) for s in subjects_of(it))


@app.post("/api/count")
def count():
    return jsonify(count=len(select(request.get_json(force=True))))


@app.post("/api/build")
def build():
    q = request.get_json(force=True)
    items = select(q)
    if not items:
        return jsonify(error="조건에 맞는 문항이 없습니다."), 400
    if len(items) > 1500:
        return jsonify(error=f"문항이 {len(items)}개로 너무 많습니다. 조건을 좁혀 주세요(최대 1500개)."), 400
    token = uuid.uuid4().hex
    d = os.path.join(OUT, token)
    os.makedirs(d)
    title = (q.get("title") or "기출 문제집").strip()[:40]
    with lock:
        n, noexp = build_pdf.build(items, docs, os.path.join(d, "문제.pdf"), os.path.join(d, "해설.pdf"), title)
    return jsonify(count=n, no_explanation=noexp,
                   problem=f"/dl/{token}/문제.pdf", solution=f"/dl/{token}/해설.pdf")


@app.get("/dl/<token>/<name>")
def dl(token, name):
    if not token.isalnum() or name not in ("문제.pdf", "해설.pdf"):
        abort(404)
    path = os.path.join(OUT, token, name)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True, download_name=name)


def cleanup():
    while True:
        now = time.time()
        for t in os.listdir(OUT):
            p = os.path.join(OUT, t)
            if os.path.isdir(p) and now - os.path.getmtime(p) > 6 * 3600:
                for f in os.listdir(p):
                    os.remove(os.path.join(p, f))
                os.rmdir(p)
        time.sleep(1800)


threading.Thread(target=cleanup, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
