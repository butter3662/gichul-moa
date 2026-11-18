"""문제지 PDF에서 문항·지문 세트의 영역을 계산한다.
영역은 여러 조각(segments)으로 이루어질 수 있다: [{page, rect:[x0,y0,x1,y1]}].
사용: python3 -I split.py <문제.pdf> [<미리보기폴더>]"""
import sys, os, re, json, statistics, pymupdf

pymupdf.TOOLS.mupdf_display_errors(False)
NUM = re.compile(r"^(\d{1,2})\s?\.\s*")
SET = re.compile(r"^\[\s*(\d{1,2})\s*[~∼～\-–]\s*(\d{1,2})\s*\]")
SECTIONS = ["확률과 통계", "미적분", "기하", "화법과 작문", "언어와 매체",
            "물리학Ⅰ", "화학Ⅰ", "생명과학Ⅰ", "지구과학Ⅰ", "물리학Ⅱ", "화학Ⅱ", "생명과학Ⅱ", "지구과학Ⅱ"]
TOP, BOT = 0.12, 0.905  # 쪽 머리·꼬리 제외 비율


_LC, _DC = {}, {}


def drawings_of(page):
    k = (page.parent.name, page.number)
    if k not in _DC:
        _DC[k] = [dr["rect"] for dr in page.get_drawings()]
    return _DC[k]


OCR = False


def readable(d):
    txt = "".join(p.get_text() for p in d)
    if len(txt.strip()) < 200 * d.page_count:
        return False
    bad = sum(1 for ch in txt if ord(ch) < 32 and ch not in "\n\r\t")
    return bad < len(txt) * 0.05


def ocr_lines(page):
    import pytesseract
    from PIL import Image
    z = 200 / 72
    pix = page.get_pixmap(dpi=200)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    data = pytesseract.image_to_data(im, lang="kor+eng", config="--psm 3", output_type=pytesseract.Output.DICT)
    groups = {}
    for i, w in enumerate(data["text"]):
        if not w.strip():
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        groups.setdefault(key, []).append(i)
    out = []
    for idx in groups.values():
        x0 = min(data["left"][i] for i in idx) / z
        y0 = min(data["top"][i] for i in idx) / z
        x1 = max(data["left"][i] + data["width"][i] for i in idx) / z
        y1 = max(data["top"][i] + data["height"][i] for i in idx) / z
        t = " ".join(data["text"][i] for i in idx)
        out.append(((x0, y0, x1, y1), (y1 - y0) * 0.75, t))
    return out


def _gray(page, dpi):
    import numpy as np
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]


def ocr_find_starts(d):
    """스캔본: 각 단 왼쪽 끝 좁은 띠만 숫자 인식해 문항 번호 위치를 찾는다."""
    import pytesseract, re as _re
    from PIL import Image
    dpi = 300
    z = dpi / 72
    W, H = d[0].rect.width, d[0].rect.height
    found = []
    for pi, p in enumerate(d):
        g = _gray(p, dpi)
        y0, y1 = int(H * TOP * z), int(H * BOT * z)
        for c, (cx0, cx1) in enumerate([(0, W / 2), (W / 2, W)]):
            a, b = int(cx0 * z), int(cx1 * z)
            region = (g[y0:y1, a:b] < 128)
            dark = region.sum(axis=0)
            import numpy as _np
            linecols = dark > (y1 - y0) * 0.3   # 단 구분선 같은 세로줄
            linecols = _np.convolve(linecols.astype(int), _np.ones(9, dtype=int), "same") > 0
            ys0 = int(H * 0.2 * z) - y0
            xs = [i for i, v in enumerate(region[ys0:].sum(axis=0)) if v > 20 and not linecols[i]]
            if not xs:
                continue
            left = a + xs[0]
            strip = g[y0:y1, max(0, left - 6): left + int(30 * z)].copy()
            lc = linecols[max(0, left - 6 - a): left + int(30 * z) - a]
            strip[:, :len(lc)][:, lc] = 255
            ink = (strip < 128)
            rows = ink.sum(axis=1) > 0
            # 줄 단위로 나누기
            runs, start = [], None
            for yy, r in enumerate(rows):
                if r and start is None:
                    start = yy
                elif not r and start is not None:
                    runs.append((start, yy)); start = None
            if start is not None:
                runs.append((start, len(rows)))
            for (r0, r1) in runs:
                if not (8 * z * 0.6 < r1 - r0 < 20 * z):
                    continue
                cols_ink = ink[r0:r1].sum(axis=0)
                first = next((i for i, v in enumerate(cols_ink) if v), 99)
                if first > 6 + 3 * z:   # 왼쪽 끝에서 시작하지 않으면 번호 아님
                    continue
                crop = strip[max(0, r0 - 4): r1 + 4]
                txt = pytesseract.image_to_string(Image.fromarray(crop), lang="eng",
                                                  config="--psm 7 -c tessedit_char_whitelist=0123456789.").strip()
                m = _re.match(r"^(\d{1,2})", txt)
                found.append(dict(kind="q", no=int(m.group(1)) if m else None, txt=txt, page=pi, col=c,
                                  y=(y0 + r0) / z, x=cx0, h=(r1 - r0) / z, first=first))
    found.sort(key=lambda a: (a["page"], a["col"], a["y"]))
    if os.environ.get("OCRDEBUG"):
        for f in found:
            print(f["page"], f["col"], round(f["y"]), round(f["h"], 1), f["first"], repr(f["txt"]), file=sys.stderr)
    if len(found) > 20:
        found = [f for f in found if f["txt"].strip()]
    # 후보를 읽는 순서대로 1번부터 번호를 붙이고, 인식된 숫자와 얼마나 맞는지 확인
    agree = sum(1 for i, f in enumerate(found) if f["no"] == i + 1 or str(i + 1) in f["txt"].replace(".", " ").split())
    for i, f in enumerate(found):
        f["no"] = i + 1
        f["section"] = None
        f["kind"] = "q"
    if found:
        found[0]["agree"] = round(agree / len(found), 2)
    return found


def trim_pixels(page, rect):
    import numpy as np
    z = 150 / 72
    g = _gray(page, 150)
    x0, y0, x1, y1 = [int(v * z) for v in rect]
    sub = g[y0:y1, x0 + 6:x1 - 6]
    rows = np.where((sub < 140).sum(axis=1) > 2)[0]
    if len(rows) == 0:
        return None
    # 아래쪽 쪽번호·안내문 띠를 피하려고 큰 빈 줄 간격 뒤 작은 덩어리는 버림
    return [rect[0], rect[1], rect[2], round(rect[1] + (rows[-1] + 6) / z, 1)]


def lines_of(page):
    k = (page.parent.name, page.number)
    if k in _LC:
        return _LC[k]
    if OCR:
        _LC[k] = ocr_lines(page)
        return _LC[k]
    out = []
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = "".join(s["text"] for s in l["spans"]).strip()
            if t:
                sp = next((x for x in l["spans"] if x["text"].strip()), l["spans"][0])
                bb = list(l["bbox"])
                bb[0] = sp["bbox"][0]
                bb[1] = max(bb[1], sp["bbox"][1])
                out.append((tuple(bb), sp["size"], t))
    _LC[k] = out
    return out


COLS = None


def detect_cols(d):
    """본문 줄의 왼쪽 x 분포로 단 경계를 찾는다 (1~3단)."""
    import collections
    W, H = d[0].rect.width, d[0].rect.height
    xs = collections.Counter()
    n = 0
    for p in d:
        for (bb, sz, t) in lines_of(p):
            if H * TOP < bb[1] < H * BOT and len(t) > 6:
                xs[int(bb[0] // 8)] += 1
                n += 1
    peaks = sorted(x * 8 for x, v in xs.items() if n and v > n * 0.08)
    starts = []
    for x in peaks:
        if not starts or x - starts[-1] > W * 0.15:
            starts.append(x)
    starts = starts[:3] if starts else [0]
    if len(starts) == 1:
        right = sum(v for x, v in xs.items() if x * 8 > W * 0.5)
        if n and right > n * 0.2:
            starts = [starts[0], W * 0.5 + 15]
    bounds = [0] + [x - 15 for x in starts[1:]] + [W]
    return [(bounds[i], bounds[i + 1]) for i in range(len(starts))]


def cols_of(W):
    return COLS


def col_index(x):
    for i, (a, b) in enumerate(COLS):
        if a - 10 <= x < b - 10 or (i == len(COLS) - 1 and x >= a - 10):
            return i
    return 0


def find_starts(d, body, mode="q"):
    W, H = d[0].rect.width, d[0].rect.height
    starts, section = [], None
    first = "".join(d[i].get_text() for i in range(min(2, d.page_count))).replace(" ", "")
    allowed = list(SECTIONS[5:])
    if "수학" in first[:400] or "확률과통계" in first:
        allowed += SECTIONS[:3]
    if "국어" in first[:400] or "화법과작문" in first or "언어와매체" in first:
        allowed += SECTIONS[3:5]
    for pi, p in enumerate(d):
        ls = lines_of(p)
        head = "".join(t for (bb, sz, t) in ls if bb[1] < H * 0.2 and sz > body * 1.3).replace(" ", "")
        for s in allowed:
            if s.replace(" ", "") in head:
                section = s
        if mode == "expl":
            ls = sorted(ls, key=lambda l: (col_index(l[0][0]), l[0][1]))
        for (bb, sz, t) in ls:
            if mode == "expl":
                tt = t.replace(" ", "").strip("■□◆◇●○<>〈〉[]()•")
                mh = re.match(r"(물리학|화학|생명과학|지구과학)(Ⅰ|Ⅱ)정답", tt)
                if mh:
                    section = mh.group(1) + mh.group(2)
                elif re.match(r"(사회ㆍ문화|사회·문화|생활과윤리|윤리와사상|한국지리|세계지리|동아시아사|세계사|경제|정치와법)정답", tt):
                    section = "기타"
                for s in allowed[:]:
                    if s in SECTIONS[5:]:
                        continue
                    if s.replace(" ", "") in tt and len(tt) <= 22 and not NUM.match(t):
                        section = s
            if not (H * TOP < bb[1] < H * BOT):
                continue
            col = col_index(bb[0])
            m = SET.match(t)
            if m:
                starts.append(dict(kind="set", no=f"{int(m.group(1))}~{int(m.group(2))}", section=section,
                                   page=pi, col=col, y=bb[1], x=bb[0]))
                continue
            m = NUM.match(t)
            if mode == "q":
                ok = OCR or sz >= body * 1.08
            else:
                rest = NUM.sub("", t, count=1).strip()
                ok = (os.environ.get("_RELAX") or "출제" in t or "[정답" in t or "정답" in t[:12] or rest == "" or rest.startswith("[") or sz >= body * 1.08) \
                    and not (rest[:1] in "①②③④⑤" and rest != "") and not re.match(r"^\d{1,3}\s", rest)
            if m and ok and 1 <= int(m.group(1)) <= 50:
                starts.append(dict(kind="q", no=int(m.group(1)), section=section,
                                   page=pi, col=col, y=bb[1], x=bb[0]))
    if mode == "expl" and not os.environ.get("_RELAX") and len([s for s in starts if s["kind"] == "q"]) < 15:
        os.environ["_RELAX"] = "1"
        try:
            return find_starts(d, body, mode)
        finally:
            os.environ.pop("_RELAX", None)
    by = {}
    for s in starts:
        by.setdefault((s["page"], s["col"]), []).append(s)
    keep = []
    for arr in by.values():
        xmin = min(a["x"] for a in arr)
        keep += [a for a in arr if a["x"] - xmin < 25]
    keep.sort(key=lambda a: (a["page"], a["col"], a["y"]))
    # 같은 (영역, 번호)가 다시 나오면 두 번째 판(홀·짝수형 등)으로 보고 잘라냄
    seen, out, last_sec = set(), [], "∅"
    for a in keep:
        if a["kind"] == "q":
            key = (a["section"], a["no"])
            if key in seen or (a["no"] == 1 and seen and a["section"] == last_sec):
                break
            seen.add(key)
            last_sec = a["section"]
        out.append(a)
    while out and out[-1]["kind"] == "set":
        out.pop()
    return out


def body_lines(p, x0, x1, y0, y1, body):
    return [l for l in lines_of(p) if x0 <= l[0][0] < x1 and y0 <= l[0][1] < y1
            and abs(l[1] - body) < 1.6 and len(l[2]) > 3]


def trim(p, rect):
    """조각 안 실제 내용 아래 끝으로 자른다. 안내문(확인 사항) 이하 제외."""
    R = pymupdf.Rect(rect)
    stop = R.y1
    ls = lines_of(p)
    for (bb, sz, t) in ls:
        if R.intersects(pymupdf.Rect(bb)) and ("확인 사항" in t or "확인사항" in t):
            stop = min(stop, bb[1] - 40)
    ymax = None
    for (bb, sz, t) in ls:
        b = pymupdf.Rect(bb)
        if R.intersects(b) and b.y1 < stop and b.y0 >= R.y0 - 2:
            ymax = max(ymax or 0, b.y1)
    for b in ([] if OCR else drawings_of(p)):
        if R.contains(b) and b.y1 < stop and not (b.width < 3 and b.height > 60) and b.height < R.height * 0.95:
            ymax = max(ymax or 0, b.y1)
    for img in ([] if OCR else p.get_image_info()):
        b = pymupdf.Rect(img["bbox"])
        if R.intersects(b) and b.y0 < stop:
            ymax = max(ymax or 0, min(b.y1, stop))
    if ymax is None:
        return None
    return [round(R.x0, 1), round(R.y0, 1), round(R.x1, 1), round(min(R.y1, ymax + 8), 1)]


def split(path, mode="q"):
    global OCR
    _LC.clear(); _DC.clear()
    d = pymupdf.open(path)
    src = "raw"
    if not readable(d):
        fixed = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), "fixed", os.path.basename(path))
        if not os.path.exists(fixed):
            import subprocess
            os.makedirs(os.path.dirname(fixed), exist_ok=True)
            subprocess.run(["pdftocairo", "-pdf", path, fixed], capture_output=True, timeout=300)
        if os.path.exists(fixed):
            d2 = pymupdf.open(fixed)
            if readable(d2):
                d, src = d2, "fixed"
    OCR = not readable(d)
    W, H = d[0].rect.width, d[0].rect.height
    sizes = [sz for p in d for (_, sz, t) in lines_of(p) if len(t) > 8]
    body = statistics.median(sizes) if sizes else 11
    global COLS
    COLS = detect_cols(d)
    if OCR:
        COLS = [(0, W / 2), (W / 2, W)]
        keep = ocr_find_starts(d)
        items = []
        for i, a in enumerate(keep):
            nxt = keep[i + 1] if i + 1 < len(keep) else None
            x0, x1 = COLS[a["col"]]
            y1 = nxt["y"] - 6 if nxt and (nxt["page"], nxt["col"]) == (a["page"], a["col"]) else H * BOT
            t = trim_pixels(d[a["page"]], [x0, a["y"] - 8, x1, y1])
            items.append(dict(kind="q", no=a["no"], section=None,
                              segments=[dict(page=a["page"], rect=t)] if t else [], src=src, ocr=True))
        return items
    keep = find_starts(d, body, mode)
    colseq = [(pi, c) for pi in range(d.page_count) for c in range(len(COLS))]
    items = []
    for i, a in enumerate(keep):
        nxt = keep[i + 1] if i + 1 < len(keep) else None
        segs = []
        k = colseq.index((a["page"], a["col"]))
        while True:
            pi, c = colseq[k]
            x0, x1 = cols_of(W)[c]
            if (pi, c) == (a["page"], a["col"]):
                y0 = a["y"] - 6
            else:
                ys = [l[0][1] for l in lines_of(d[pi]) if x0 <= l[0][0] < x1 and H * TOP < l[0][1] < H * BOT and l[1] < body * 1.6]
                y0 = (min(ys) - 4) if ys else H * TOP
            if nxt and (pi, c) == (nxt["page"], nxt["col"]):
                y1 = nxt["y"] - 6
                # 다음 시작점 위쪽에 본문이 이어지면 포함
                if (pi, c) == (a["page"], a["col"]) or len(body_lines(d[pi], x0, x1, y0, y1, body)) >= 2:
                    segs.append((pi, [x0, y0, x1, y1]))
                break
            if (pi, c) != (a["page"], a["col"]):
                # 시작점 없는 단: 세트이거나 본문이 이어질 때만 포함
                if not (a["kind"] == "set" or len(body_lines(d[pi], x0, x1, y0, H * BOT, body)) >= 2):
                    break
            segs.append((pi, [x0, y0, x1, H * BOT]))
            k += 1
            if k >= len(colseq) or (nxt is None and a["kind"] == "q"):
                break
            if a["kind"] == "q" and k - colseq.index((a["page"], a["col"])) > (2 if mode == "q" else 4):
                break
        out = []
        for pi, r in segs:
            t = trim(d[pi], r)
            if t and t[3] - t[1] > 12:
                out.append(dict(page=pi, rect=t))
        items.append(dict(kind=a["kind"], no=a["no"], section=a["section"], segments=out))
    for it in items:
        it["src"] = src
        if OCR:
            it["ocr"] = True
    return items


def render(path, items, outdir, dpi=110):
    os.makedirs(outdir, exist_ok=True)
    if items and items[0].get("src") == "fixed":
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))), "fixed", os.path.basename(path))
    d = pymupdf.open(path)
    from PIL import Image
    for i, it in enumerate(items):
        ims = []
        for s in it["segments"]:
            pix = d[s["page"]].get_pixmap(clip=pymupdf.Rect(s["rect"]), dpi=dpi)
            ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        if not ims:
            continue
        w = max(im.width for im in ims)
        canvas = Image.new("RGB", (w, sum(im.height for im in ims) + 6 * (len(ims) - 1)), "white")
        y = 0
        for im in ims:
            canvas.paste(im, (0, y))
            y += im.height + 6
        canvas.save(os.path.join(outdir, f"{i:03d}_{it['section'] or ''}_{it['no']}.png"))


if __name__ == "__main__":
    mode = os.environ.get("MODE", "q")
    items = split(sys.argv[1], mode)
    print(json.dumps(items, ensure_ascii=False))
    if len(sys.argv) > 2:
        render(sys.argv[1], items, sys.argv[2])
