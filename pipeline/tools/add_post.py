"""호랭이닷컴 글(번호)을 목록에 추가하고 PDF를 내려받는다.
사용: python3 -I tools/add_post.py <글번호 또는 주소> [...]
결과: horaeng/titles.tsv, horaeng/links.txt, gichul-moa/sources.txt 에 추가, raw/ 에 PDF 저장
출력 마지막 줄: 처리할 시험 글번호 목록"""
import sys, re, html, urllib.request, urllib.parse, os, subprocess
H, RAW, SRC = "/home/claude/horaeng", "/home/claude/raw", "/home/claude/gichul-moa/sources.txt"
UA = {"User-Agent": "Mozilla/5.0 (personal study archive)"}
titles = {l.split("\t")[2] for l in open(f"{H}/titles.tsv", encoding="utf-8") if l.strip()}
srcs = {l.strip() for l in open(SRC, encoding="utf-8") if l.strip()}
done = []
for arg in sys.argv[1:]:
    pid = re.search(r"(\d+)\s*$", arg.rstrip("/")).group(1)
    page = urllib.request.urlopen(urllib.request.Request(f"https://horaeng.com/{pid}", headers=UA), timeout=60).read().decode("utf-8", "ignore")
    t = html.unescape(re.search(r"<title>([^<]*)", page).group(1)).replace(" - 호랭이닷컴", "").strip()
    g = re.search(r"고([123])", t)
    grade = f"고{g.group(1)}" if g else "고3"            # 모의평가·수능은 고3
    m = re.search(r"(\d{4})학년도", t)
    year = int(m.group(1)) - 1 if m else int(re.search(r"(\d{4})년", t).group(1))  # 학년도 → 시행년
    links = sorted(set(re.findall(r'href="(https://horaeng\.com/wp-content/uploads/[^"]+\.pdf)"', page)))
    # 기출모아에서 쓰는 과목만 (한국사·사회탐구 선택과목·제2외국어·듣기 등은 뺀다. 고1 통합사회는 포함)
    SKIP = r"한국사|경제|정치|법과|사회문화|사회ㆍ문화|사회·문화|윤리|지리|세계사|동아시아|직업|독일|일본|중국|프랑스|스페인|러시아|아랍|베트남|한문|듣기|대본|사회탐구"
    def keep(u):
        n = urllib.parse.unquote(u.rsplit("/", 1)[1])
        if grade == "고1" and re.search(r"사회|통합사회", n) and not re.search(r"한국사", n):
            return True
        return not re.search(SKIP, n)
    links = [u for u in links if keep(u)]
    print(pid, grade, year, t, len(links), "files")
    if pid not in titles:
        open(f"{H}/titles.tsv", "a", encoding="utf-8").write(f"{grade}\t{year}\t{pid}\t{t}\n")
        with open(f"{H}/links.txt", "a", encoding="utf-8") as f:
            for u in links:
                f.write(f'{pid} href="{u}"\n')
    with open(SRC, "a", encoding="utf-8") as f:
        for u in links:
            if u not in srcs:
                f.write(u + "\n"); srcs.add(u)
    lst = "/tmp/new_urls.txt"
    open(lst, "w").write("\n".join(links) + "\n")
    subprocess.run([sys.executable, "-I", "/home/claude/tools/fetch.py", lst, RAW], check=True)
    done.append(pid)
print("POSTS", ",".join(done))
