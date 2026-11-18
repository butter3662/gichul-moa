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
import urllib.request, urllib.error
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_pdf
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
    names = {"subjects": "과목", "grades": "학년", "years": "연도", "months": "월", "types": "시험", "units": "범위", "subs": "소단원"}
    for k, n in names.items():
        v = q.get(k) or []
        if v:
            vv = [x.split("/", 1)[-1].replace("/", " › ") if k in ("units", "subs") else f"{x}년" if k == "years" else f"{x}월" if k == "months" else selector.TYPE_NAME.get(x, x) if k == "types" else str(x) for x in v]
            parts.append(f"{n}: {', '.join(vv)}")
        elif k not in ("units", "subs"):
            parts.append(f"{n}: 전체")
    return "\n".join(parts)


def send(to, title, files, q, n, noexp, part=None):
    m = EmailMessage()
    m["From"] = f"기출모아 <{GMAIL_USER}>"
    m["To"] = to
    m["Subject"] = f"[기출모아] {title} ({n}문항)" + (f" — {part}" if part else "")
    body = f"요청한 기출 문제집이다.\n\n{describe(q)}\n\n문항 수: {n}"
    if noexp:
        body += f"\n해설 없는 문항: {noexp}개 (해설 파일에 '해설 없음'으로 표시, 정답은 있음)"
    body += "\n\n이 메일은 자동으로 보낸 것이다."
    m.set_content(body)
    for path, name in files:
        with open(path, "rb") as f:
            m.add_attachment(f.read(), maintype="application", subtype="pdf", filename=name)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=120) as s:
        s.login(GMAIL_USER, GMAIL_PW)
        s.send_message(m)


def handle(r):
    q = r["query"] or {}
    items = selector.select(ITEMS, q)
    if not items:
        set_status(r["id"], status="failed", message="조건에 맞는 문항이 없습니다.", item_count=0)
        return
    if len(items) > selector.MAX_ITEMS:
        set_status(r["id"], status="failed", item_count=len(items),
                   message=f"문항이 {len(items)}개라 너무 많습니다. 최대 {selector.MAX_ITEMS}개까지 됩니다.")
        return
    title = (q.get("title") or "기출 문제집").strip()[:40] or "기출 문제집"
    with tempfile.TemporaryDirectory() as d:
        fq, fe = os.path.join(d, "문제.pdf"), os.path.join(d, "해설.pdf")
        n, noexp = build_pdf.build(items, docs, fq, fe, title)
        sq, se = os.path.getsize(fq), os.path.getsize(fe)
        if max(sq, se) > MAX_MAIL_BYTES:
            set_status(r["id"], status="failed", item_count=n,
                       message="PDF가 메일 첨부 한도(약 18MB)를 넘습니다. 조건을 좁혀 주세요.")
            return
        safe = "".join(c for c in title if c not in '\\/:*?"<>|')
        if sq + se <= MAX_MAIL_BYTES:
            send(r["email"], title, [(fq, f"{safe}_문제.pdf"), (fe, f"{safe}_해설.pdf")], q, n, noexp)
        else:
            send(r["email"], title, [(fq, f"{safe}_문제.pdf")], q, n, noexp, part="1/2 문제")
            send(r["email"], title, [(fe, f"{safe}_해설.pdf")], q, n, noexp, part="2/2 해설")
    set_status(r["id"], status="sent", item_count=n, message=f"{r['email']}로 보냈습니다.")


def main():
    print("기출모아 작업기 시작", flush=True)
    # 이전에 하다가 멈춘 요청은 다시 대기로
    try:
        api("PATCH", "gichul_requests?status=eq.working", {"status": "queued"})
    except Exception:
        pass
    while True:
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
            set_status(r["id"], status="failed", message="메일 계정 로그인 실패 (운영자 설정 문제)")
        except Exception as e:
            traceback.print_exc()
            set_status(r["id"], status="failed", message=f"처리 중 오류: {str(e)[:150]}")


if __name__ == "__main__":
    main()
