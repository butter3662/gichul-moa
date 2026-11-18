"""PDF마다 쪽수, 텍스트 레이어 여부, 쪽당 이미지 수를 조사한다. 사용: python3 -I survey.py <폴더> <출력.tsv>"""
import sys, os, pymupdf

src, out = sys.argv[1], sys.argv[2]
rows = []
for name in sorted(os.listdir(src)):
    if not name.endswith(".pdf"):
        continue
    try:
        d = pymupdf.open(os.path.join(src, name))
        chars = sum(len(p.get_text("text").strip()) for p in d)
        imgs = sum(len(p.get_images()) for p in d)
        w, h = d[0].rect.width, d[0].rect.height
        rows.append((name, d.page_count, chars, imgs, f"{w:.0f}x{h:.0f}"))
    except Exception as e:
        rows.append((name, -1, -1, -1, str(e)[:40]))
with open(out, "w", encoding="utf-8") as f:
    f.write("name\tpages\tchars\timages\tsize\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")
print(len(rows))
