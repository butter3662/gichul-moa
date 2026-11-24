"""선택된 문항으로 문제 PDF와 해설 PDF 두 개를 만든다.
원본 PDF의 해당 영역을 벡터 그대로 옮겨 붙이므로(show_pdf_page) 화질이 떨어지지 않는다."""
import os, re, pymupdf

pymupdf.TOOLS.mupdf_display_errors(False)

PAGE_W, PAGE_H = 841.0, 1190.0          # 원본 시험지와 같은 판형(A3 비율, A4로 인쇄하면 원본과 같은 크기)
MARGIN_X, MARGIN_TOP, MARGIN_BOT = 50.0, 80.0, 60.0
GAP = 24.0
COL_W = (PAGE_W - 2 * MARGIN_X - GAP) / 2
MAX_SCALE = 1.25
SOLVE_SPACE = {"default": 40.0, "국어": 30.0, "영어": 30.0}
FLOW_SUBJECTS = {"국어", "영어"}   # 지문 흐름대로 이어 붙이는 과목. 나머지는 모의고사처럼 한 단에 위아래 2칸
FONT = "nsk"
_FONT_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "NanumGothic-Regular.ttf"),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]
FONTFILE = next((f for f in _FONT_CANDIDATES if os.path.exists(f)), None)
_FONTOBJ = pymupdf.Font(fontfile=FONTFILE) if FONTFILE else pymupdf.Font("korea")


def put(page, xy, text, size, color=(0, 0, 0)):
    if FONTFILE:
        page.insert_text(xy, text, fontname=FONT, fontfile=FONTFILE, fontsize=size, color=color)
    else:
        page.insert_text(xy, text, fontname="korea", fontsize=size, color=color)


def tlen(text, size):
    return _FONTOBJ.text_length(text, fontsize=size)


CIRC = "①②③④⑤"


def ans_width(a, size):
    return size * 1.15 if a in CIRC else tlen(a, size)


def put_answer(page, xy, a, size):
    """정답 쓰기. 원문자(①~⑤)는 글꼴에 없을 수 있어 원과 숫자를 직접 그린다."""
    x, y = xy
    if a in CIRC:
        r = size * 0.55
        c = pymupdf.Point(x + r, y - size * 0.36)
        page.draw_circle(c, r, color=(0, 0, 0), width=0.7)
        d = str(CIRC.index(a) + 1)
        page.insert_text((c.x - tlen(d, size * 0.8) / 2, c.y + size * 0.28), d, fontname="helv", fontsize=size * 0.8)
    else:
        put(page, (x, y), a, size)


class Docs:
    """원본 PDF 열기 캐시"""

    def __init__(self, raw_dir, fixed_dir):
        self.raw, self.fixed, self.cache = raw_dir, fixed_dir, {}

    def get(self, name, src):
        key = (name, src)
        if key not in self.cache:
            base = self.fixed if src == "fixed" else self.raw
            self.cache[key] = pymupdf.open(os.path.join(base, name))
        return self.cache[key]


class Writer:
    """2단 레이아웃으로 조각을 차례로 붙인다."""

    def __init__(self, title):
        self.doc = pymupdf.open()
        self.title = title
        self.page = None
        self.col = 0
        self.y = 0
        self.pno = 0
        self.new_page()

    def new_page(self):
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.pno += 1
        self.col, self.y = 0, MARGIN_TOP
        p = self.page
        put(p, (MARGIN_X, 48), self.title, 15)
        p.draw_line((MARGIN_X, 60), (PAGE_W - MARGIN_X, 60), width=1.2)
        p.draw_line((PAGE_W / 2, MARGIN_TOP - 6), (PAGE_W / 2, PAGE_H - MARGIN_BOT + 6), width=0.6)
        put(p, (PAGE_W / 2 - tlen(str(self.pno), 11) / 2, PAGE_H - 28), str(self.pno), 11)

    def next_col(self):
        if self.col == 0:
            self.col, self.y = 1, MARGIN_TOP
        else:
            self.new_page()

    def x0(self):
        return MARGIN_X + self.col * (COL_W + GAP)

    def room(self):
        return PAGE_H - MARGIN_BOT - self.y

    def text(self, s, size=11, bold=False, h=None):
        h = h or size * 1.6
        if self.room() < h:
            self.next_col()
        put(self.page, (self.x0(), self.y + size), s, size)
        self.y += h

    def answer_table(self, answers, per_row=5):
        """빠른 정답: 5문항씩 한 줄, 번호 칸과 정답 칸으로 된 표"""
        cell_w = COL_W / per_row
        num_w = cell_w * 0.42
        rh = 20
        for start in range(0, len(answers), per_row):
            if self.room() < rh:
                self.next_col()
            y = self.y
            for j, a in enumerate(answers[start:start + per_row]):
                x = self.x0() + j * cell_w
                self.page.draw_rect(pymupdf.Rect(x, y, x + num_w, y + rh), color=(0.55, 0.55, 0.55), fill=(0.93, 0.93, 0.93), width=0.6)
                self.page.draw_rect(pymupdf.Rect(x + num_w, y, x + cell_w, y + rh), color=(0.55, 0.55, 0.55), width=0.6)
                n = str(start + j + 1)
                put(self.page, (x + (num_w - tlen(n, 10)) / 2, y + 14), n, 10)
                a = a or "?"
                fs = 11 if len(a) <= 3 else 9
                put_answer(self.page, (x + num_w + (cell_w - num_w - ans_width(a, fs)) / 2, y + 14.5), a, fs)
            self.y += rh

    def clip(self, src_doc, pno, rect, cover=None, label=None):
        """원본의 rect 영역을 현재 단에 붙인다. cover: 원본 번호를 가릴 사각형, label: 새 번호.
        한 단보다 긴 조각은 단 경계에서 나눠 붙인다."""
        r = content_bounds(src_doc[pno], rect)
        scale = min(MAX_SCALE, COL_W / r.width)
        first = True
        while r.height > 0.5:
            h = r.height * scale
            if h > self.room() + 0.5 and self.y > MARGIN_TOP + 1:
                self.next_col()
                continue
            part = pymupdf.Rect(r)
            if h > self.room() + 0.5:
                part.y1 = r.y0 + self.room() / scale
            ph = part.height * scale
            target = pymupdf.Rect(self.x0(), self.y, self.x0() + part.width * scale, self.y + ph)
            self.page.show_pdf_page(target, src_doc, pno, clip=part)
            if first and cover is not None:
                c = pymupdf.Rect(cover)
                cr = pymupdf.Rect(target.x0 + (c.x0 - part.x0) * scale - 1, target.y0 + (c.y0 - part.y0) * scale - 1,
                                  target.x0 + (c.x1 - part.x0) * scale + 1, target.y0 + (c.y1 - part.y0) * scale + 1)
                self.page.draw_rect(cr, color=(1, 1, 1), fill=(1, 1, 1))
                if label.startswith("["):
                    put(self.page, (cr.x0 + 1, cr.y1 - 1.5), label, max(9, 11 * scale))
                else:
                    self.page.insert_text((cr.x0 + 1, cr.y1 - 1.5), label, fontname="hebo", fontsize=max(9, 11.5 * scale))
            first = False
            self.y += ph + 4
            r = pymupdf.Rect(r.x0, part.y1, r.x1, r.y1)
            if r.height > 0.5:
                self.next_col()

    def slot_h(self):
        return (PAGE_H - MARGIN_BOT - MARGIN_TOP) / 2

    def begin_slot(self, h):
        """모의고사처럼 한 단을 위·아래 두 칸으로 나눠, 문항을 칸의 맨 위에서 시작한다."""
        top, mid = MARGIN_TOP, MARGIN_TOP + self.slot_h()
        if self.y <= top + 1:
            return
        if self.y <= mid + 1 and h <= self.slot_h() - 10:
            self.y = mid
            return
        self.next_col()

    def end_slot(self, h):
        top, mid = MARGIN_TOP, MARGIN_TOP + self.slot_h()
        if h > self.slot_h() - 10 or self.y > mid + 1:
            if self.y > MARGIN_TOP + 1:
                self.next_col()
        else:
            self.y = mid

    def space(self, h):
        if self.room() < h:
            self.next_col()
        else:
            self.y += h


NUMRX = re.compile(r"^\d{1,2}\.?$")


def number_box(src_doc, seg):
    """문항 첫 조각에서 원래 번호('12.')의 위치를 찾는다 (텍스트 없는 스캔본이면 None)."""
    page = src_doc[seg["page"]]
    r = pymupdf.Rect(seg["rect"])
    words = page.get_text("words", clip=r)
    cands = [w for w in words if NUMRX.match(w[4]) and w[1] < r.y0 + 40]
    if not cands:
        return None
    w = min(cands, key=lambda w: (round(w[1] / 8), w[0]))
    x1 = w[2]
    for v in words:  # 숫자 바로 뒤에 따로 떨어진 '.'
        if v[4] == "." and 0 <= v[0] - w[2] < 8 and abs(v[1] - w[1]) < 6:
            x1 = max(x1, v[2])
    return (w[0], w[1], x1, w[3])


def set_box(src_doc, seg):
    """지문 첫 줄의 '[1~3]' 위치"""
    page = src_doc[seg["page"]]
    r = pymupdf.Rect(seg["rect"])
    words = sorted([w for w in page.get_text("words", clip=r) if w[1] < r.y0 + 30], key=lambda w: (round(w[1] / 8), w[0]))
    start = next((i for i, w in enumerate(words) if w[4].startswith("[")), None)
    if start is None:
        return None
    for w in words[start:start + 5]:
        if "]" in w[4]:
            a = words[start]
            return (a[0], min(a[1], w[1]), w[2], max(a[3], w[3]))
    return None


def content_bounds(page, rect):
    """조각 안 실제 내용의 좌우 범위로 좁힌다 (원본 여백 제거).
    조각 가장자리에 걸친 이웃 단의 선(단 구분선, 옆 문항 상자 테두리)은 넣지 않는다."""
    r = pymupdf.Rect(rect)
    tx = []
    for w in page.get_text("words", clip=r):
        if w[4].strip():
            tx += [w[0], w[2]]
    xs = list(tx)
    t0, t1 = (min(tx), max(tx)) if tx else (None, None)
    for dr in page.get_drawings():
        b = dr["rect"]
        if not r.contains(b) or (b.width < 3 and b.height > 60):
            continue
        if tx and (b.x1 < t0 - 2 and b.x1 - r.x0 < 20 or b.x0 > t1 + 2 and r.x1 - b.x0 < 20):
            continue   # 글자 범위 밖, 조각 가장자리에 붙은 선 = 이웃 단의 것
        xs += [b.x0, b.x1]
    for im in page.get_image_info():
        b = pymupdf.Rect(im["bbox"]) & r
        if not b.is_empty:
            xs += [b.x0, b.x1]
    if not xs:
        return r
    return pymupdf.Rect(max(r.x0, min(xs) - 3), r.y0, min(r.x1, max(xs) + 3), r.y1)


def source_label(it):
    """출처: 시험지에 적힌 학년도 기준. 모평·수능은 시행 연도+1학년도, 학평은 시행 연도와 같은 학년도."""
    if it["type"] == "예시":
        return f"2028학년도 수능 예시문항 {it['no']}번"
    t = {"학평": "학력평가", "모평": "모의평가", "수능": "수능"}[it["type"]]
    sec = f" {it['section']}" if it.get("section") and it["subj15"] == "수학" else ""
    if it["type"] == "수능":
        return f"{it['year'] + 1}학년도 수능{sec} {it['no']}번"
    if it["type"] == "모평":
        return f"{it['year'] + 1}학년도 {it['month']}월 {it['grade']} 모의평가{sec} {it['no']}번"
    return f"{it['year']}학년도 {it['month']}월 {it['grade']} 학력평가{sec} {it['no']}번"


def build(items, docs, out_q, out_e, title="기출 문제집"):
    """items: 순서대로 정렬된 문항 목록. 반환: (문항 수, 해설 없는 문항 수)"""
    wq = Writer(title)
    printed_passages = set()
    for i, it in enumerate(items, 1):
        q = it["q"]
        sd = docs.get(q["file"], q["src"])
        p = it.get("passage")
        if p and p["key"] not in printed_passages:
            printed_passages.add(p["key"])
            members = [j for j, x in enumerate(items, 1) if (x.get("passage") or {}).get("key") == p["key"]]
            label = f"[{members[0]}~{members[-1]}]" if len(members) > 1 else f"[{members[0]}]"
            pd_ = docs.get(p["file"], p["src"])
            for k, s in enumerate(p["segs"]):
                cover = set_box(pd_, s) if k == 0 else None
                wq.clip(pd_, s["page"], s["rect"], cover=cover, label=label if cover else None)
            wq.space(16)
        flow = it["subj15"] in FLOW_SUBJECTS
        if not flow:
            est = 0
            for s in q["segs"]:
                r = content_bounds(sd[s["page"]], s["rect"])
                est += r.height * min(MAX_SCALE, COL_W / r.width) + 4
            wq.begin_slot(est + 14)
        src = source_label(it)
        r0 = content_bounds(sd[q["segs"][0]["page"]], q["segs"][0]["rect"])
        h0 = r0.height * min(MAX_SCALE, COL_W / r0.width)
        if wq.room() < h0 + 16 and wq.y > MARGIN_TOP + 1:
            wq.next_col()
        put(wq.page, (wq.x0() + COL_W - tlen(src, 8.5), wq.y + 8), src, 8.5, color=(0.42, 0.45, 0.56))
        wq.y += 12
        for k, s in enumerate(q["segs"]):
            cover = number_box(sd, s) if k == 0 else None
            wq.clip(sd, s["page"], s["rect"], cover=cover, label=f"{i}." if cover else None)
        if flow:
            wq.space(SOLVE_SPACE.get(it["subj15"], SOLVE_SPACE["default"]))
        else:
            wq.end_slot(est + 14)
    if wq.doc.page_count > 1 and wq.page.get_images() == [] and wq.y <= MARGIN_TOP + 1 and wq.col == 0:
        wq.doc.delete_page(wq.doc.page_count - 1)   # 마지막에 생긴 빈 쪽
    wq.doc.subset_fonts()
    wq.doc.save(out_q, garbage=3, deflate=True)

    # 해설: 맨 앞 빠른 정답(5문항씩), 이어서 문항별 해설
    we = Writer(title + " — 정답과 해설")
    we.text("빠른 정답", size=14, h=26)
    we.answer_table([x.get("answer") for x in items])
    we.space(24)
    noexp = 0
    for i, it in enumerate(items, 1):
        head = f"{i}.  정답 "
        src = source_label(it)
        if we.room() < 60:
            we.next_col()
        we.page.draw_rect(pymupdf.Rect(we.x0(), we.y, we.x0() + COL_W, we.y + 22), color=None, fill=(0.94, 0.95, 0.98))
        put(we.page, (we.x0() + 6, we.y + 15.5), head, 11)
        put_answer(we.page, (we.x0() + 6 + tlen(head, 11) + 2, we.y + 15.5), it.get("answer") or "?", 11)
        put(we.page, (we.x0() + COL_W - tlen(src, 8.5) - 6, we.y + 15), src, 8.5)
        we.y += 28
        e = it.get("e")
        if e:
            ed = docs.get(e["file"], e["src"])
            for k, s_ in enumerate(e["segs"]):
                cover = number_box(ed, s_) if k == 0 else None
                we.clip(ed, s_["page"], s_["rect"], cover=cover, label=f"{i}." if cover else None)
        else:
            noexp += 1
            we.text("해설 없음", size=9.5)
        we.space(12)
    we.doc.subset_fonts()
    we.doc.save(out_e, garbage=3, deflate=True)
    return len(items), noexp
