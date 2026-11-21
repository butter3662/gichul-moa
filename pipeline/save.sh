#!/bin/bash
# 작업 도구·중간 자료를 저장소(pipeline/)에 복사
set -e
cd /home/claude
P=gichul-moa/pipeline
mkdir -p $P/tools $P/data $P/horaeng
cp tools/*.py $P/tools/
cp data/catalog.json data/answers_manual.json data/headed_answers.json data/units_manual.json $P/data/
[ -f data/subs_manual.json ] && cp data/subs_manual.json $P/data/ || true
[ -f data/extra_items.json ] && cp data/extra_items.json $P/data/ || true
[ -f data/pts_manual.json ] && cp data/pts_manual.json $P/data/ || true
tar czf $P/data/regions.tgz -C data regions regions_expl answers
gzip -c data/texts.json > $P/data/texts.json.gz
cp horaeng/titles.tsv horaeng/links.txt $P/horaeng/
echo "saved"
