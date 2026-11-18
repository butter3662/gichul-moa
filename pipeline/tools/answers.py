"""정답표(해설 첫머리 또는 정답 PDF)에서 문항별 정답을 뽑는다.
사용: python3 -I answers.py <pdf> [과목키]
출력: JSON {"<영역 또는 ->": {"번호": "정답"}}"""
import sys, os, re, json, collections, pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split as S

pymupdf.TOOLS.mupdf_display_errors(False)
CIRC = "①②③④⑤"
MOJI = {"檾": "①", "檿": "②", "櫀": "③", "櫁": "④", "櫂": "⑤"}  # 일부 해설 PDF의 깨진 원문자
SEC_ORDER = {"수학": ["확률과 통계", "미적분", "기하"], "국어": ["화법과 작문", "언어와 매체"]}
SEC_FROM = {"수학": 23, "국어": 35}


def is_pua(t):
    return any(0xE000 <= ord(c) <= 0xF8FF for c in t)


def ocr_cell(page, bbox):
    import pytesseract
    from PIL import Image
    r = pymupdf.Rect(bbox) + (-0.5, -3, 0.5, 3)
    pix = page.get_pixmap(dpi=400, clip=r, colorspace=pymupdf.csGRAY)
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    im = im.resize((im.width * 2, im.height * 2))
    for psm in (7, 8, 10):
        t = pytesseract.image_to_string(im, lang="eng", config=f"--psm {psm} -c tessedit_char_whitelist=0123456789").strip()
        if t:
            return t
    return "?"


def token_ok(t):
    return (t.isascii() and t.isdigit()) or (len(t) == 1 and (t in CIRC or t in MOJI)) or is_pua(t)


def parse(path, subject=None):
    d = pymupdf.open(path)
    whole = "".join(p.get_text() for p in d[:1])
    triple = ("배점" in whole.replace(" ", "")) or ("배 점" in whole)
    S.COLS = [(0, d[0].rect.width)] if triple else S.detect_cols(d)
    events = []
    for pi, p in enumerate(d):
        S._LC.clear()
        for (bb, sz, t) in S.lines_of(p):
            tt = t.replace(" ", "").strip("■□◆◇●○<>〈〉[]()•")
            for s in S.SECTIONS[:5]:
                if tt == s.replace(" ", "") or tt == s.replace(" ", "") + "]":
                    events.append((pi, S.col_index(bb[0]), bb[1], "sec", s))
        ws = [w for w in p.get_text("words") if token_ok(w[4])]
        ws.sort(key=lambda w: (S.col_index(w[0]), (w[1] + w[3]) / 2))
        groups = []
        for w in ws:
            c, cy = S.col_index(w[0]), (w[1] + w[3]) / 2
            if groups and groups[-1][0] == c and abs(groups[-1][1] - cy) < 4:
                groups[-1][2].append((w[0], w[4], tuple(w[:4])))
            else:
                groups.append([c, cy, [(w[0], w[4], tuple(w[:4]))]])
        for c, cy, toks in groups:
            toks.sort()
            events.append((pi, c, cy, "row", toks))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    out = collections.defaultdict(dict)
    sec = None
    step = 3 if triple else 2
    for pi, c, y, kind, val in events:
        if kind == "sec":
            if not triple:
                sec = val
            continue
        toks = val
        if len(toks) < 2:
            continue
        i, k_by_no = 0, collections.Counter()
        pairs = []
        while i + 1 < len(toks):
            n, a = toks[i][1], toks[i + 1]
            if not (n.isascii() and n.isdigit()) or not (1 <= int(n) <= 50):
                i += 1
                continue
            ans = MOJI.get(a[1], a[1])
            if is_pua(ans):
                ans = ocr_cell(d[pi], a[2])
            pairs.append((int(n), ans))
            i += step
        prev = out.get(sec or "-", {})
        if len(pairs) < 2 and not (pairs and str(pairs[0][0] - 1) in prev):
            continue
        for n, ans in pairs:
            s = sec
            if triple and subject in SEC_FROM and n >= SEC_FROM[subject]:
                k = k_by_no[n]
                k_by_no[n] += 1
                s = SEC_ORDER[subject][k] if k < len(SEC_ORDER[subject]) else None
            key = s or "-"
            if str(n) not in out[key]:
                out[key][str(n)] = ans
    return dict(out)


if __name__ == "__main__":
    print(json.dumps(parse(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), ensure_ascii=False))
