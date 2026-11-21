#!/bin/bash
# 새 기출 반영: 글 추가 → 분리 → 정답 → 합치기 → 텍스트 → 과목·단원·소단원 분류 → 선택지 갱신
# 사용(작업 환경 /home/claude 에서): bash gichul-moa/pipeline/update.sh <호랭이 글번호> [...]
set -e
cd /home/claude
python3 -I tools/add_post.py "$@" | tee /tmp/add.log
python3 tools/catalog.py | tail -2
POSTS=$(grep '^POSTS' /tmp/add.log | cut -d' ' -f2)
ONLY=$(python3 -c "
import json,sys; p=set('$POSTS'.split(',')); print(','.join(e['id'] for e in json.load(open('data/catalog.json')) if e['post'] in p))")
echo "시험: $ONLY"
export ONLY
python3 tools/split_all.py 문제 | tail -3
python3 tools/split_all.py 해설 | tail -3
python3 tools/answers_all.py | tail -3
python3 tools/headed_answers.py | tail -3
python3 tools/merge.py | head -3
cp data/items.json gichul-moa/data/items.json
unset ONLY
python3 tools/extract_text.py
python3 tools/ocr_texts.py | head -1
python3 tools/classify.py | head -1
python3 tools/genre.py
python3 tools/apply_units.py >/dev/null
python3 tools/classify_sub.py | head -1
python3 tools/apply_units.py
(cd gichul-moa && python3 tools/make_options.py)
# 작업 자료를 저장소에 보관 (다음 세션에서 이어서 쓰기 위함)
bash gichul-moa/pipeline/save.sh
echo "완료. 확인 후 gichul-moa 에서 git add -A; git commit; git push"
