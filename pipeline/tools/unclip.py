"""잘린 글자(지수·분수 위 첨자 등)가 없도록 영역 위아래를 넓힌다.
영역 경계가 글자 하나를 가로지르면 그 글자가 다 들어가게 경계를 옮긴다 (같은 문항 안에서만)."""
import os, pymupdf

_cache = {}


def _chars(path, page):
    k = (path, page)
    if k not in _cache:
        if len(_cache) > 400:
            _cache.clear()
        d = pymupdf.open(path)
        boxes = []
        for b in d[page].get_text("rawdict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    for c in s["chars"]:
                        if c["c"].strip():
                            boxes.append(c["bbox"])
        _cache[k] = boxes
    return _cache[k]


def fix_seg(path, seg, pad=1.0, limit=14):
    x0, y0, x1, y1 = seg["rect"]
    top, bot = y0, y1
    for (a, b, c, e) in _chars(path, seg["page"]):
        if c < x0 or a > x1:
            continue
        if b < y0 < e and y0 - b <= limit:      # 위 경계를 가로지름
            top = min(top, b - pad)
        if b < y1 < e and e - y1 <= limit:      # 아래 경계를 가로지름
            bot = max(bot, e + pad)
    if top != y0 or bot != y1:
        seg["rect"] = [x0, round(top, 1), x1, round(bot, 1)]
        return True
    return False


def fix_items(items, raw, fixed):
    n = 0
    only = set(os.environ.get("ONLY", "").split(",")) - {""}
    for it in items:
        if only and it["exam"] not in only:
            continue
        for k in ("q", "e", "passage"):
            v = it.get(k)
            if not v or not v.get("segs"):
                continue
            path = os.path.join(raw if v.get("src", "raw") == "raw" else fixed, v["file"])
            if not os.path.exists(path):
                continue
            for s in v["segs"]:
                try:
                    n += fix_seg(path, s)
                except Exception:
                    pass
    return n
