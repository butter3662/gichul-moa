#!/bin/bash
# 라즈베리파이 설치 스크립트 — 이 폴더(gichul)에서 실행: bash setup.sh
# 1) 필요한 프로그램 설치  2) 원본 PDF 내려받기  3) 깨진 PDF 복구  4) 서비스 등록
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "[1/4] 프로그램 설치"
sudo apt-get update -y
sudo apt-get install -y python3-venv poppler-utils
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install flask pymupdf gunicorn

echo "[2/4] 원본 PDF 내려받기 (약 1,200개)"
mkdir -p data/raw data/fixed data/out
.venv/bin/python -I tools/fetch.py sources.txt data/raw

echo "[3/4] 깨진 PDF 복구"
while read -r f; do
  [ -z "$f" ] && continue
  [ -f "data/fixed/$f" ] || pdftocairo -pdf "data/raw/$f" "data/fixed/$f" || true
done < fixed_list.txt

echo "[4/4] 서비스 등록"
if [ -z "$SITE_PASSWORD" ]; then
  read -r -s -p "사이트 접속 비밀번호를 정하세요: " SITE_PASSWORD; echo
fi
sudo tee /etc/systemd/system/gichul.service > /dev/null <<EOF
[Unit]
Description=gichul (기출 모음 사이트)
After=network-online.target

[Service]
WorkingDirectory=$HERE/app
Environment=DATA_DIR=$HERE/data
Environment=SITE_PASSWORD=$SITE_PASSWORD
ExecStart=$HERE/.venv/bin/gunicorn -w 2 -t 300 -b 0.0.0.0:8080 server:app
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now gichul
echo "완료: 같은 와이파이에서 http://$(hostname -I | awk '{print $1}'):8080 으로 접속"
