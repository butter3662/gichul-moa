"""문항 텍스트(q+해설)로 22개정 과목·단원을 키워드 점수로 정한다.
출력: data/units.json {id: {subject, unit, score, margin, conf}}"""
import json, math, re, sys
sys.path.insert(0, "tools")
from taxonomy import UNITS, K, candidates

items = json.load(open("data/items.json"))
texts = json.load(open("data/texts.json"))

# 키워드 정리: 1글자 토큰은 오탐이 많아 버림(Σ, 몫 제외)
KW = {}
for key, ws in K.items():
    KW[key] = sorted({w for w in ws if len(w) >= 2 or w in ("Σ", "몫")})

# HyhwpEQ(한글 수식 글꼴) 사용자 영역 문자 → 실제 기호 (글리프를 렌더해 눈으로 대조함)
PUA = {}
for n, ch in enumerate("123456789"):
    PUA[0xE034 + n] = ch
PUA[0xE03D] = "0"
for n in range(26):
    PUA[0xE000 + n] = chr(65 + n)
    PUA[0xE0E5 + n] = chr(97 + n)
PUA.update({0xE044: "(", 0xE045: ")", 0xE047: "=", 0xE048: "+", 0xE046: "-", 0xE049: "[", 0xE04A: "]",
            0xE04B: "{", 0xE04C: "}", 0xE052: ",", 0xE055: "<", 0xE056: ">", 0xE04F: ":", 0xE053: ".",
            0xE101: "|", 0xE04D: "|", 0xE067: "Σ", 0xE05B: "∫", 0xE05C: "√", 0xE06D: "‾", 0xE06E: "⃗",
            0xE0AC: "π", 0xE0A4: "θ", 0xE09D: "α", 0xE09E: "β", 0xE0AE: "σ", 0xE0C8: "°", 0xE042: "%"})


def norm(s):
    s = "".join(PUA.get(ord(c), " " if 0xE000 <= ord(c) <= 0xF8FF else c) for c in (s or ""))
    return re.sub(r"\s+", "", s)


# 수식 패턴 특징 (과목, 단원) → 정규식
FEAT = [
    (("대수", "수열"), r"Σ|[aSb][0-9n](?![a-z])|an\+1|Sn|등차|등비", 2.5),
    (("대수", "삼각함수"), r"sin|cos|tan|π|θ|부채꼴", 2.5),
    (("대수", "지수함수와 로그함수"), r"log|√|\(‾\d+\)x|제곱근|\d‾\d+×", 2.5),
    (("미적분Ⅰ", "적분"), r"∫|속도|f′\(x\)=[^가-힣]*(이고|,)f\(-?\d\)=|부정적분", 3.0),
    (("미적분Ⅰ", "미분"), r"′|f'|접선|극[댓솟]?값|극[대소]|실근의개수|평균변화율|미분계수|limh→0|‾x-\d+f\(x\)-f\(\d+\)|미분가능", 2.5),
    (("미적분Ⅰ", "함수의 극한과 연속"), r"lim|연속", 2.0),
    (("미적분Ⅱ", "적분법"), r"∫", 2.5),
    (("미적분Ⅱ", "미분법"), r"′|ln|e[x\-]|sec|csc|cot|tan\(|limx→0|매개변수|역함수", 2.5),
    (("미적분Ⅱ", "수열의 극한"), r"limn→∞|Σn=1∞|∞‾|수렴|급수", 3.0),
    (("기하", "벡터"), r"⃗|방향벡터", 2.5),
    (("기하", "이차곡선"), r"타원|포물선|쌍곡선|초점", 2.5),
    (("확률과 통계", "경우의 수"), r"전개식|계수는|개수는|개수를|경우의수", 3.0),
    (("확률과 통계", "확률"), r"확률은|확률을|P\(A", 2.5),
    (("확률과 통계", "통계"), r"확률변수|E\(X|V\(X|σ\(X|정규분포|표본", 3.0),
    (("공통수학2", "도형의 방정식"), r"[xy]\^?2\+[xy]", 2.0),
    (("공통수학1", "방정식과 부등식"), r"i=√|허수|복소수|이차방정식|부등식", 2.5),
    (("화학", "역동적인 화학 반응"), r"산화수|산화환원|중화|적정|pH|pOH|H3O|산성|염기|액성|열출입|발열|흡열|H\+|OH-", 3.0),
    (("화학", "화학 평형"), r"동적평형|가역", 3.0),
    (("화학 반응의 세계", "산화⋅환원 반응"), r"산화수|전지|전극|전기분해", 3.0),
    (("화학 반응의 세계", "산 염기 평형"), r"Ka|Kb|이온화상수|완충", 3.0),
    (("화학 반응의 세계", "화학 평형"), r"평형상수|K=|르샤틀리에|평형이동", 3.0),
    (("공통수학1", "다항식"), r"나머지|나누었을|항등식|모든실수x에대하여", 2.5),
]

def intent(e):
    m = re.search(r"\[?출제\s*의도\]?\s*:?(.{0,80})", e or "")
    return m.group(1) if m else ""

cache_idf = {}
def idf_for(cands):
    key = tuple(cands)
    if key not in cache_idf:
        units = [(s, u) for s in cands for u in UNITS[s]]
        df = {}
        for su in units:
            for w in KW.get(su, []):
                df[w] = df.get(w, 0) + 1
        cache_idf[key] = (units, {w: math.log(1 + len(units) / d) for w, d in df.items()})
    return cache_idf[key]

out = {}
for it in items:
    if it["subj15"] in ("국어", "영어"):
        continue
    cands = candidates(it)
    t = texts.get(it["id"], {})
    q, e = norm(t.get("q")), norm(t.get("e"))
    ie = norm(intent(t.get("e")))
    units, idf = idf_for(cands)
    scores = []
    for su in units:
        sc = 0.0
        for w in KW.get(su, []):
            n = min(q.count(w), 3) + 0.6 * min(e.count(w), 3) + 2.0 * min(ie.count(w), 2)
            if n:
                sc += n * idf[w] * (1 + 0.15 * len(w))
        for fsu, rx, wt in FEAT:
            if fsu == su:
                sc += wt * min(len(re.findall(rx, q)), 4) + 2.0 * min(len(re.findall(rx, ie)), 2)
        scores.append((sc, su))
    scores.sort(reverse=True)
    best, (s2, _) = scores[0], (scores[1] if len(scores) > 1 else (0, None))
    margin = (best[0] - s2) / (best[0] + 1e-9)
    conf = "high" if best[0] >= 6 and margin >= 0.25 else ("mid" if best[0] >= 3 and margin >= 0.1 else "low")
    out[it["id"]] = {"subject": best[1][0], "unit": best[1][1], "score": round(best[0], 1),
                     "margin": round(margin, 2), "conf": conf,
                     "alt": [f"{s}/{u}:{round(v,1)}" for v, (s, u) in scores[1:3]]}

# 문제 텍스트에 결정적인 표현이 있으면 그 단원으로 정한다
RULES = [
    ("화학", r"산화환원반응|산화수|중화적정|혼합한용액|중화반응|혼합한수용액", "역동적인 화학 반응"),
    ("확률과 통계", r"전개식에서", "경우의 수"),
    ("미적분Ⅰ", r"f′\(x\)=[^가-힣]*(이고|,)f\(-?\d\)=", "적분"),
    ("지구과학", r"자전축|공전궤도이심률|기후변화|기온편차|황사|태풍|뇌우|엘니뇨|라니냐|온대저기압|해수의|수온", "대기와 해양의 상호작용"),
    ("지구과학", r"판의경계|해구|해령|고지자기|화성암|퇴적암|변성암|방사성|반감기|지질|화석|대멸종|초대륙|열점|플룸|건열|연흔", "지구의 역사와 한반도의 암석"),
    ("생명과학", r"병원체|백신|항원|항체|면역|방어작용", "항상성과 몸의 조절"),
    ("생명과학", r"개체수|개체군|군집|생태계|생물량|먹이사슬|천이|방형구|출생률", "생명 시스템의 구성"),
    ("물리학", r"관성계|우주선|특수상대성|핵반응|핵융합|핵분열|질량결손", "힘과 에너지"),
    ("물리학", r"물질파|이중성|광전|파동|굴절|간섭|전반사|광섬유", "빛과 물질"),
    ("물리학", r"자성체|점전하|도선|자기장|유도전류|다이오드|반도체|솔레노이드", "전기와 자기"),
]
for it in items:
    v = out.get(it["id"])
    if not v:
        continue
    q = norm(texts.get(it["id"], {}).get("q"))
    for subj, rx, unit in RULES:
        if v["subject"] == subj and re.search(rx, q):
            v.update(unit=unit, conf="high", note="규칙")
            break

# 15개정 Ⅱ과목: 결정적 표현으로 22개정 과목·단원을 함께 정한다 (먼저 맞는 것 적용)
RULES2 = {
    "물리학2": [
        (r"전기장|전위|축전기|점전하|자기장|유도기전력|코일|저항|전류|도선|전기용량", "전자기와 양자", "전자기적 상호작용"),
        (r"물질파|광전|광자|불확정|에너지준위|터널|오비탈|양자", "전자기와 양자", "양자와 미시세계"),
        (r"렌즈|거울|편광|이중슬릿|간섭무늬|전자기파|안테나|홀로그램|굴절", "전자기와 양자", "빛과 정보 통신"),
        (r"도플러|음파|소리|정상파|공명|맥놀이|현의|관의", "역학과 에너지", "탄성파와 소리"),
        (r"이상기체|열효율|열기관|내부에너지|단열|등압|등온|열역학|기체의", "역학과 에너지", "열과 에너지"),
        (r"포물선운동|원운동|구심|케플러|만유인력|인공위성|단진동|진자|돌림힘|평형|빗면|운동량|등가원리|궤도", "역학과 에너지", "시공간과 운동"),
    ],
    "화학2": [
        (r"평형상수|르샤틀리에|평형이동|반응지수", "화학 반응의 세계", "화학 평형"),
        (r"이온화상수|완충|가수분해|Ka|Kb", "화학 반응의 세계", "산 염기 평형"),
        (r"전지|전극|전기분해|표준환원", "화학 반응의 세계", "산화⋅환원 반응"),
        (r"반응속도|속도상수|반감기|활성화에너지|촉매|반응차수", "물질과 에너지", "반응 속도"),
        (r"엔탈피|반응열|결합에너지|헤스|자유에너지|엔트로피", "물질과 에너지", "화학 변화의 자발성"),
        (r"몰랄|삼투|어는점|끓는점오름|증기압력내림|퍼센트농도", "물질과 에너지", "용액의 성질"),
        (r"부분압력|분압|몰분율|증기압력|결정|단위세포|수소결합|분자간|기체", "물질과 에너지", "물질의 세 가지 상태"),
    ],
    "생명과학2": [
        (r"제한효소|PCR|재조합|플라스미드|전기영동|형질전환|줄기세포|단일클론|유전자치료|핵치환", "생물의 유전", "생명공학 기술"),
        (r"전사|번역|코돈|mRNA|tRNA|오페론|프로모터|전사인자|유전자발현|혹스|분화", "생물의 유전", "유전자의 발현"),
        (r"복제|프라이머|선도가닥|지연가닥|오카자키|뉴클레오솜|DNA중합|반보존|허시|그리피스|에이버리", "생물의 유전", "유전자와 유전물질"),
        (r"하디|유전자풀|대립유전자빈도|종분화|유전적부동|계통수|분류|진화|원시지구|밀러|역\(|3역", "생물의 유전", "진화와 다양성(22개정 범위 밖)"),
        (r"광합성|명반응|캘빈|엽록체|틸라코이드|스트로마|세포호흡|해당과정|TCA|전자전달|산화적인산화|발효|미토콘드리아|광계|NADH|NADPH|RuBP|3PG", "세포와 물질대사", "세포호흡과 광합성"),
        (r"효소|기질|저해제|활성부위|조효소|보조인자", "세포와 물질대사", "물질대사와 에너지"),
        (r"세포막|인지질|확산|삼투|능동수송|세포소기관|리보솜|소포체|골지체|리소좀|원핵|진핵|조직계|세포분획|내포|외포", "세포와 물질대사", "세포"),
    ],
    "지구과학2": [
        (r"은하|허블|후퇴속도|적색편이|우주배경|암흑|우주론|팽창", "행성우주과학", "은하와 우주"),
        (r"망원경|집광력|분해능|연주시차|쌍성|변광성|세페이드|성단|흑점|광도|등급|분광형|별의", "행성우주과학", "태양과 별의 관측"),
        (r"행성|위성|적경|적위|고도|방위각|천구|회합주기|최대이각|순행|역행|케플러|탐사", "행성우주과학", "우주탐사와 행성계"),
        (r"해파|심해파|천해파|조석|조차|해일|에크만|지형류|용승", "지구시스템과학", "해수의 운동"),
        (r"구름|강수|단열감률|안정|이슬점|응결|지균풍|경도풍|지상풍|기압경도력|전향력|편서풍|대기대순환|정역학", "지구시스템과학", "강수 과정과 대기의 운동"),
        (r"지진파|진앙|진원|암영대|모호|지각평형|중력이상|지자기|편각|복각|광물|결정|쪼개짐|암석|변성|지질도|한반도|자원|퇴적", "지구시스템과학", "지구 탄생과 생동하는 지구"),
    ],
}
for it in items:
    v = out.get(it["id"])
    if not v or it["subj15"] not in RULES2 or v["conf"] == "high":
        continue
    q = norm(texts.get(it["id"], {}).get("q")) + norm(intent(texts.get(it["id"], {}).get("e")))
    for rx, subj, unit in RULES2[it["subj15"]]:
        if re.search(rx, q):
            v.update(subject=subj, unit=unit, conf="mid", note="규칙2")
            break

# 근거가 거의 없는 문항: 같은 시험·과목에서 번호가 가까운 문항의 단원을 따른다 (과탐은 대체로 단원 순서로 출제)
groups = {}
for it in items:
    if it["id"] in out:
        groups.setdefault((it["exam"], it["subj15"], it.get("section")), []).append(it)
for g in groups.values():
    good = [(i["no"], out[i["id"]]) for i in g if out[i["id"]]["score"] >= 3]
    for i in g:
        v = out[i["id"]]
        if v["score"] >= 1.5 or not good:
            continue
        no, nb = min(good, key=lambda x: abs(x[0] - i["no"]))
        v.update(subject=nb["subject"], unit=nb["unit"], conf="low", note=f"이웃 {no}번 따름")

# 고1 3월 통합과학·통합사회는 중학교 범위로 출제됨
for it in items:
    if it["id"] in out and it["grade"] == "고1" and it["month"] == 3 and it["subj15"] in ("통합과학", "통합사회"):
        out[it["id"]].update(unit="중학 범위(고1 3월)", conf="high", note="고1 3월")

json.dump(out, open("data/units.json", "w"), ensure_ascii=False, indent=0)
import collections
c = collections.Counter(v["conf"] for v in out.values())
print(len(out), dict(c))
by = collections.Counter((v["subject"], v["unit"]) for v in out.values())
for k2, n in sorted(by.items()):
    print(k2, n)
