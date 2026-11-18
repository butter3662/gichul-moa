#!/bin/bash
# 새 작업 환경에서 저장소의 도구·중간 자료를 /home/claude 로 풀어 놓는다
# 사용: git clone 후  bash gichul-moa/pipeline/restore.sh
set -e
cd /home/claude
P=gichul-moa/pipeline
mkdir -p tools data raw fixed horaeng
cp $P/tools/*.py tools/
cp $P/data/*.json data/
tar xzf $P/data/regions.tgz -C data
gunzip -c $P/data/texts.json.gz > data/texts.json
cp $P/horaeng/* horaeng/
cp gichul-moa/data/items.json data/items.json
pip install --break-system-packages -q pymupdf pytesseract pillow 2>/dev/null || true
which tesseract >/dev/null || echo "※ tesseract(kor)가 없으면 스캔본 OCR이 안 됨: apt-get install tesseract-ocr tesseract-ocr-kor"
which pdftocairo >/dev/null || echo "※ pdftocairo 없음: apt-get install poppler-utils"
echo "restored"
