"""텍스트가 없는(스캔본) 문항은 OCR로 문제 텍스트를 채운다."""
import json, pymupdf, pytesseract, io
from PIL import Image
pymupdf.TOOLS.mupdf_display_errors(False)
t = json.load(open("data/texts.json")); items = {i["id"]: i for i in json.load(open("data/items.json"))}
todo = [k for k, v in t.items() if k in items and len(v["q"].strip()) < 20 and not v.get("ocr")]
print(len(todo))
for n, k in enumerate(todo):
    q = items[k]["q"]
    d = pymupdf.open(("fixed/" if q["src"] == "fixed" else "raw/") + q["file"])
    parts = []
    for s in q["segs"]:
        pix = d[s["page"]].get_pixmap(dpi=300, clip=pymupdf.Rect(s["rect"]))
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
        parts.append(pytesseract.image_to_string(img, lang="kor", config="--psm 4"))
    t[k]["q"] = " ".join(parts).replace("\n", " ")[:3000]
    t[k]["ocr"] = True
json.dump(t, open("data/texts.json", "w"), ensure_ascii=False)
import collections
print(collections.Counter(k.rsplit("|", 2)[0] for k in todo))
