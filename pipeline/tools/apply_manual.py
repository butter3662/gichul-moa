"""수동 판정(인덱스→코드)을 data/units_manual.json 에 누적한다.
사용: python3 tools/apply_manual.py <정규식> <a> <b> "i:코드 i:코드 ..." """
import json, re, sys, os
CODE = {"P": ("공통수학1", "다항식"), "E": ("공통수학1", "방정식과 부등식"), "C": ("공통수학1", "경우의 수"), "M": ("공통수학1", "행렬"),
        "G": ("공통수학2", "도형의 방정식"), "S": ("공통수학2", "집합과 명제"), "F": ("공통수학2", "함수와 그래프"),
        "EL": ("대수", "지수함수와 로그함수"), "T": ("대수", "삼각함수"), "Q": ("대수", "수열"),
        "L": ("미적분Ⅰ", "함수의 극한과 연속"), "D": ("미적분Ⅰ", "미분"), "I": ("미적분Ⅰ", "적분"),
        "PC": ("확률과 통계", "경우의 수"), "PP": ("확률과 통계", "확률"), "PS": ("확률과 통계", "통계"),
        "XL": ("미적분Ⅱ", "수열의 극한"), "XD": ("미적분Ⅱ", "미분법"), "XI": ("미적분Ⅱ", "적분법"),
        "GC": ("기하", "이차곡선"), "GS": ("기하", "공간도형과 공간좌표"), "GV": ("기하", "벡터")}
sys.path.insert(0, "tools")
from taxonomy import UNITS
u = json.load(open("data/units.json"))
P = "data/units_manual.json"
man = json.load(open(P)) if os.path.exists(P) else {}
ks = json.load(open("/tmp/list.json"))
for tok in sys.argv[-1].split():
    i, c = tok.split(":", 1)
    k = ks[int(i)] if ks else i
    if c in CODE:
        s, un = CODE[c]
    else:
        s, ui = c.replace("_", " ").split("#"); un = UNITS[s][int(ui)]
    man[k] = [s, un]
json.dump(man, open(P, "w"), ensure_ascii=False, indent=0)
print(len(man))
