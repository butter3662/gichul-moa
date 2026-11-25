"""기출모아 작업기 (라즈베리파이에서 상시 실행).
Supabase의 gichul_requests 표에서 '대기' 요청을 하나씩 가져와
문제 PDF·해설 PDF를 만들고, Gmail로 요청자가 적은 이메일에 보낸다.

환경변수 (/etc/gichul.env 에 사용자가 직접 넣는다):
  SUPABASE_URL          예: https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY  Supabase 대시보드 → Project Settings → API Keys 의 secret(service_role) 키
  GMAIL_USER            보내는 Gmail 주소
  GMAIL_APP_PASSWORD    그 계정의 16자리 앱 비밀번호
  DATA_DIR              (선택) 기본 ../data"""
import os, sys, json, time, ssl, smtplib, tempfile, traceback
import urllib.request, urllib.error, urllib.parse
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pdf
import pymupdf
import selector

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", os.path.join(BASE, "..", "data"))
URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_SERVICE_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_PW = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
MAX_MAIL_BYTES = 18 * 1024 * 1024   # Gmail 첨부 25MB 한도(인코딩 증가분 고려)
POLL = 5

ITEMS = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))
docs = build_pdf.Docs(os.path.join(DATA, "raw"), os.path.join(DATA, "fixed"))


def api(method, path, body=None, extra=None):
    h = {"apikey": KEY, "Content-Type": "application/json", "Prefer": "return=representation"}
    if not KEY.startswith("sb_"):  # 예전 형식(JWT) service_role 키만 Authorization 헤더에도 넣는다
        h["Authorization"] = f"Bearer {KEY}"
    h.update(extra or {})
    req = urllib.request.Request(f"{URL}/rest/v1/{path}", method=method, headers=h,
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read()
        return json.loads(t) if t else None


BUCKET = "gichul-pdf"


def storage(method, path, data=None, ctype="application/json", extra=None):
    h = {"apikey": KEY, "Content-Type": ctype}
    if not KEY.startswith("sb_"):
        h["Authorization"] = f"Bearer {KEY}"
    h.update(extra or {})
    if ctype == "application/json" and data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(f"{URL}/storage/v1/{urllib.parse.quote(path)}", method=method, headers=h, data=data)
    with urllib.request.urlopen(req, timeout=120) as r:
        t = r.read()
        return json.loads(t) if t else None


def upload(r, files):
    """사이트에서 바로 열 수 있게 PDF를 비공개 저장소에 올린다: 시각(YYYYMMDDHH)/사용자/요청/번호.pdf"""
    stamp = time.strftime("%Y%m%d%H", time.gmtime())
    out = []
    for i, (path, name, _) in enumerate(files):
        key = f"{stamp}/{r['user_id']}/{r['id']}/{i + 1}.pdf"
        with open(path, "rb") as f:
            storage("POST", f"object/{BUCKET}/{key}", f.read(), "application/pdf", {"x-upsert": "true"})
        out.append({"name": name, "path": key})
    set_status(r["id"], files=out)


def cleanup_storage():
    """24시간 지난 PDF 지우기"""
    cut = time.strftime("%Y%m%d%H", time.gmtime(time.time() - 25 * 3600))
    def ls(prefix):
        return storage("POST", f"object/list/{BUCKET}", {"prefix": prefix, "limit": 1000, "offset": 0}) or []
    for d in ls(""):
        if d.get("id") is None and d["name"] < cut:
            names = []
            for u in ls(d["name"]):
                for q in ls(f"{d['name']}/{u['name']}"):
                    names += [f"{d['name']}/{u['name']}/{q['name']}/{f['name']}" for f in ls(f"{d['name']}/{u['name']}/{q['name']}")]
            if names:
                storage("DELETE", f"object/{BUCKET}", {"prefixes": names})


def deliver(r, q, title, files, n, noexp, mail_limit=None):
    try:
        upload(r, files)
    except Exception:
        traceback.print_exc()
        if q.get("no_mail"):   # 메일 없이 받는 요청은 올리기에 실패하면 받을 방법이 없다
            raise
    if q.get("no_mail"):
        return 0
    mails = pack(files, mail_limit or MAX_MAIL_BYTES)
    for i, fs in enumerate(mails):
        send(r["email"], title, fs, q, n, noexp, i + 1, len(mails))
        if len(mails) > 1:
            set_status(r["id"], message=f"메일 {i + 1}/{len(mails)}통 보냈어요.")
    return len(mails)


def set_status(rid, **fields):
    fields["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    api("PATCH", f"gichul_requests?id=eq.{rid}", fields)


def claim():
    rows = api("GET", "gichul_requests?status=eq.queued&order=created_at.asc&limit=1")
    if not rows:
        return None
    r = rows[0]
    got = api("PATCH", f"gichul_requests?id=eq.{r['id']}&status=eq.queued",
              {"status": "working", "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
    return got[0] if got else None


def describe(q):
    parts = []
    names = {"subjects": "과목", "grades": "학년", "years": "연도", "months": "월", "types": "시험", "units": "범위", "subs": "소단원", "pts": "배점"}
    for k, n in names.items():
        v = q.get(k) or []
        if v:
            vv = [x.split("/", 1)[-1].replace("/", " › ") if k in ("units", "subs") else f"{x}학년도" if k == "years" else f"{x}월" if k == "months" else f"{x}점" if k == "pts" else selector.TYPE_NAME.get(x, x) if k == "types" else str(x) for x in v]
            parts.append(f"{n}: {', '.join(vv)}")
        elif k not in ("units", "subs", "pts"):
            parts.append(f"{n}: 전체")
    return "\n".join(parts)


def split_pdf(path, limit, outdir, stem):
    """PDF를 쪽 단위로 나눠 각 조각이 limit 바이트 이하가 되게 한다. [(경로, 크기)] 반환."""
    size = os.path.getsize(path)
    if size <= limit:
        return [(path, size)]
    src = pymupdf.open(path)
    pages = src.page_count
    k = max(2, -(-size // int(limit * 0.9)))
    while True:
        k = min(k, pages)
        bounds = [round(i * pages / k) for i in range(k + 1)]
        parts = []
        for i in range(k):
            out = pymupdf.open()
            out.insert_pdf(src, from_page=bounds[i], to_page=bounds[i + 1] - 1)
            p = os.path.join(outdir, f"{stem}_{i + 1}.pdf")
            out.save(p, garbage=4, deflate=True)
            out.close()
            parts.append((p, os.path.getsize(p)))
        if all(sz <= limit for _, sz in parts) or k == pages:
            return parts
        k += 1


def pack(files, limit):
    """첨부 파일 목록 [(경로, 이름, 크기)]을 메일당 limit 이하로 묶는다."""
    mails, cur, tot = [], [], 0
    for f in files:
        if cur and tot + f[2] > limit:
            mails.append(cur)
            cur, tot = [], 0
        cur.append(f)
        tot += f[2]
    if cur:
        mails.append(cur)
    return mails


def send(to, title, files, q, n, noexp, idx=1, total=1):
    m = EmailMessage()
    m["From"] = f"기출모아 <{GMAIL_USER}>"
    m["To"] = to
    m["Subject"] = f"[기출모아] {title} ({n}문항)" + (f" ({idx}/{total})" if total > 1 else "")
    body = "안녕하세요, 기출모아입니다.\n"
    if total > 1:
        body += f"파일 첨부 한도 초과로 {idx}번째 메일 보내드립니다 (남은 메일 수 {total - idx}/{total})\n"
    if q.get("mode") == "random":
        body += f"요청하신 랜덤 문제를 보내드립니다.\n\n{title}\n\n문항 수: {n}개"
    else:
        body += f"요청하신 기출 문제집을 보내드립니다.\n\n{describe(q)}\n\n문항 수: {n}개"
    if noexp:
        body += f"\n해설이 없는 문항: {noexp}개 (해설 파일에는 '해설 없음'으로 표시되며, 정답은 확인하실 수 있습니다.)"
    body += "\n\n첨부 파일: " + ", ".join(name for _, name, _ in files)
    body += "\n이 메일은 자동으로 발송되었습니다. 감사합니다."
    m.set_content(body)
    for path, name, _ in files:
        with open(path, "rb") as f:
            m.add_attachment(f.read(), maintype="application", subtype="pdf", filename=name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=300) as s:
        s.login(GMAIL_USER, GMAIL_PW)
        s.send_message(m)


def sent_ids(uid):
    """이 사용자에게 랜덤으로 이미 보낸 문항 id"""
    out, off = set(), 0
    while True:
        rows = api("GET", f"gichul_sent?user_id=eq.{uid}&select=item_id&limit=1000&offset={off}")
        out |= {x["item_id"] for x in rows or []}
        if not rows or len(rows) < 1000:
            return out
        off += 1000


def handle_random(r, q):
    picked, is_old = selector.random_pick(ITEMS, q, sent_ids(r["user_id"]))
    if not picked:
        set_status(r["id"], status="failed", item_count=0, message="이 조건으로 보낼 수 있는 문제를 다 보냈어요. 다른 과목이나 학년을 골라 주세요.")
        return
    it = picked[0]
    src = build_pdf.source_label(it).rsplit(" ", 1)[0]
    nos = f"{picked[0]['no']}~{picked[-1]['no']}번" if len(picked) > 1 else f"{it['no']}번"
    title = f"랜덤 {q.get('area')} - {src} {nos}"
    with tempfile.TemporaryDirectory() as d:
        fq, fe = os.path.join(d, "문제.pdf"), os.path.join(d, "해설.pdf")
        n, noexp = build_pdf.build(picked, docs, fq, fe, title)
        safe = "".join(c for c in title if c not in '\\/:*?"<>|')
        # 랜덤 문제는 문제 뒤에 정답·해설을 붙여 한 파일로 보낸다
        both = pymupdf.open(fq)
        both.insert_pdf(pymupdf.open(fe))
        fb = os.path.join(d, "문제_해설.pdf")
        both.save(fb, garbage=3, deflate=True)
        files = [(fb, f"{safe}.pdf", os.path.getsize(fb))]
        deliver(r, q, title, files, n, noexp)
    api("POST", "gichul_sent", [{"user_id": r["user_id"], "item_id": x["id"]} for x in picked],
        {"Prefer": "resolution=ignore-duplicates,return=minimal"})
    msg = f"{src} {nos} 문제를 " + ("준비했어요." if q.get("no_mail") else "보냈어요.") + (" (2022학년도 이후 문제를 다 써서 그 전 문제에서 골랐어요.)" if is_old else "")
    set_status(r["id"], status="sent", item_count=n, message=msg, item_ids=[x["id"] for x in picked])


def handle(r):
    q = r["query"] or {}
    if q.get("mode") == "random":
        return handle_random(r, q)
    items = selector.select(ITEMS, q)
    if not items:
        set_status(r["id"], status="failed", message="조건에 맞는 문항이 없어요. 조건을 넓혀 주세요.", item_count=0)
        return
    if len(items) > selector.MAX_ITEMS:
        set_status(r["id"], status="failed", item_count=len(items),
                   message=f"문항이 {len(items)}개로 너무 많아요. 최대 {selector.MAX_ITEMS}개까지 만들 수 있어요.")
        return
    title = (q.get("title") or "기출 문제집").strip()[:40] or "기출 문제집"
    with tempfile.TemporaryDirectory() as d:
        fq, fe = os.path.join(d, "문제.pdf"), os.path.join(d, "해설.pdf")
        n, noexp = build_pdf.build(items, docs, fq, fe, title)
        safe = "".join(c for c in title if c not in '\\/:*?"<>|')
        files = []
        for path, label in ((fq, "문제"), (fe, "해설")):
            parts = split_pdf(path, MAX_MAIL_BYTES, d, label)
            for i, (p, sz) in enumerate(parts):
                name = f"{safe}_{label}.pdf" if len(parts) == 1 else f"{safe}_{label}_{i + 1}.pdf"
                files.append((p, name, sz))
        nm = deliver(r, q, title, files, n, noexp)
    msg = "준비했어요." if nm == 0 else f"{r['email']}(으)로 보냈어요." if nm == 1 else f"{r['email']}(으)로 메일 {nm}통에 나눠 보냈어요."
    set_status(r["id"], status="sent", item_count=n, message=msg)


def main():
    print("기출모아 작업기 시작", flush=True)
    # 호랭이닷컴 밖(EBSi·평가원)에서 온 원본이 없으면 먼저 받아 둔다
    spec = os.path.join(BASE, "..", "extra_sources.json")
    if os.path.exists(spec):
        import subprocess
        subprocess.run([sys.executable, "-I", os.path.join(BASE, "..", "tools", "fetch_extra.py"), spec, os.path.join(DATA, "raw")])
    # 이전에 하다가 멈춘 요청은 다시 대기로
    try:
        api("PATCH", "gichul_requests?status=eq.working", {"status": "queued"})
    except Exception:
        pass
    last_clean = 0
    while True:
        if time.time() - last_clean > 3600:
            last_clean = time.time()
            try:
                cleanup_storage()
            except Exception:
                traceback.print_exc()
        try:
            r = claim()
        except Exception as e:
            print("Supabase 연결 실패:", e, flush=True)
            time.sleep(30)
            continue
        if not r:
            time.sleep(POLL)
            continue
        print("요청", r["id"], r["email"], flush=True)
        try:
            handle(r)
        except smtplib.SMTPAuthenticationError:
            traceback.print_exc()
            set_status(r["id"], status="failed", message="메일을 보내지 못했어요 (운영자 설정 문제)")
        except Exception as e:
            traceback.print_exc()
            set_status(r["id"], status="failed", message=f"만드는 중에 오류가 났어요: {str(e)[:150]}")


if __name__ == "__main__":
    main()
