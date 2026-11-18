"""호랭이닷컴 파일을 천천히 내려받는다. 사용: python3 -I fetch.py <url목록> <저장폴더>"""
import sys, os, time, urllib.parse, urllib.request

urls_file, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)
urls = [u.strip() for u in open(urls_file, encoding="utf-8") if u.strip()]
ok = skip = fail = 0
for i, u in enumerate(urls, 1):
    name = urllib.parse.unquote(u.rsplit("/", 1)[1])
    dst = os.path.join(out_dir, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        skip += 1
        continue
    enc = urllib.parse.quote(u, safe=":/")
    for attempt in range(3):
        try:
            req = urllib.request.Request(enc, headers={"User-Agent": "Mozilla/5.0 (personal study archive)"})
            with urllib.request.urlopen(req, timeout=60) as r, open(dst + ".part", "wb") as f:
                f.write(r.read())
            os.replace(dst + ".part", dst)
            ok += 1
            break
        except Exception as e:
            time.sleep(3)
            if attempt == 2:
                fail += 1
                print("FAIL", name, e, flush=True)
    time.sleep(0.1)
    if i % 100 == 0:
        print(f"{i}/{len(urls)} ok={ok} skip={skip} fail={fail}", flush=True)
print(f"done ok={ok} skip={skip} fail={fail}")
