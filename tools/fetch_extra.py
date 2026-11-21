"""호랭이닷컴 밖(EBSi·평가원)에서 받은 원본을 내려받아 작업용 PDF로 만든다.
extra_sources.json: [{name, url, zip_member?(파일 이름에 들어간 말), odd_only?(홀수형 쪽만), pages?(남길 쪽)}]
사용: python3 -I fetch_extra.py extra_sources.json data/raw"""
import sys, os, io, re, json, time, zipfile, urllib.request
import pymupdf

spec, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
cache = {}


def get(url):
    if url not in cache:
        for a in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (personal study archive)"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    cache[url] = r.read()
                break
            except Exception as e:
                if a == 2:
                    raise
                time.sleep(3)
    return cache[url]


def zname(info):
    try:
        return info.filename.encode("cp437").decode("cp949")
    except Exception:
        return info.filename


ok = skip = fail = 0
for s in json.load(open(spec, encoding="utf-8")):
    dst = os.path.join(out, s["name"])
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        skip += 1
        continue
    try:
        data = get(s["url"])
        if s.get("zip_member"):
            z = zipfile.ZipFile(io.BytesIO(data))
            m = [i for i in z.infolist() if i.filename.lower().endswith(".pdf") and s["zip_member"] in zname(i)]
            data = z.read(m[0])
        d = pymupdf.open(stream=data, filetype="pdf")
        keep = None
        if s.get("image_pages"):      # 이미지로 된 시험지 쪽 → 그림만 쪽 크기(270dpi 기준)로 다시 담는다
            o = pymupdf.open()
            for i in s["image_pages"]:
                pix = pymupdf.Pixmap(d, d[i].get_images()[0][0])
                if pix.n > 3:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                k = 72 / 270
                pg = o.new_page(width=pix.width * k, height=pix.height * k)
                pg.insert_image(pg.rect, pixmap=pix)
            o.save(dst + ".part", garbage=3, deflate=True)
            os.replace(dst + ".part", dst)
            ok += 1
            continue
        if s.get("odd_only"):
            keep = [i for i, p in enumerate(d) if re.search(r"홀\s*수", p.get_text())]
        elif s.get("pages"):
            keep = s["pages"]
        if keep is not None:
            o = pymupdf.open()
            for i in keep:
                o.insert_pdf(d, from_page=i, to_page=i)
            o.save(dst + ".part", garbage=3, deflate=True)
        else:
            open(dst + ".part", "wb").write(data)
        os.replace(dst + ".part", dst)
        ok += 1
    except Exception as e:
        fail += 1
        print("FAIL", s["name"], e, flush=True)
print(f"extra ok={ok} skip={skip} fail={fail}")
