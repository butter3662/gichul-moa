#!/bin/bash
# 라즈베리파이 설치·업데이트 스크립트 — 이 폴더(gichul-moa)에서 실행: bash setup.sh
# 1) 프로그램 설치  2) 원본 PDF 내려받기  3) 깨진 PDF 복구  4) 작업기(worker) 서비스 등록
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "[1/4] 프로그램 설치"
sudo apt-get update -y
sudo apt-get install -y python3-venv poppler-utils
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pymupdf

echo "[2/4] 원본 PDF 내려받기 (이미 받은 파일은 건너뜀)"
mkdir -p data/raw data/fixed
.venv/bin/python -I tools/fetch.py sources.txt data/raw

echo "[3/4] 깨진 PDF 복구"
while read -r f; do
  [ -z "$f" ] && continue
  [ -f "data/fixed/$f" ] || pdftocairo -pdf "data/raw/$f" "data/fixed/$f" 2>/dev/null || true
done < fixed_list.txt

echo "[4/4] 작업기 서비스 등록"
# 예전 웹서버 방식(gichul.service)은 끈다
if systemctl list-unit-files | grep -q '^gichul.service'; then
  sudo systemctl disable --now gichul.service || true
fi
if [ ! -f /etc/gichul.env ]; then
  sudo tee /etc/gichul.env > /dev/null <<'EOF'
SUPABASE_URL=https://ictjkqbbcaigdvlysdaw.supabase.co
SUPABASE_SERVICE_KEY=여기에_서비스키
GMAIL_USER=magilab.co@gmail.com
GMAIL_APP_PASSWORD=여기에_앱비밀번호
EOF
  sudo chmod 600 /etc/gichul.env
  echo ">>> /etc/gichul.env 를 만들었다. 서비스 키와 앱 비밀번호를 넣어야 작동한다:  sudo nano /etc/gichul.env"
fi
sudo tee /etc/systemd/system/gichul-worker.service > /dev/null <<EOF
[Unit]
Description=gichul-moa worker (기출모아 메일 작업기)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=$HERE/app
EnvironmentFile=/etc/gichul.env
Environment=DATA_DIR=$HERE/data
ExecStart=$HERE/.venv/bin/python -u worker.py
Restart=always
RestartSec=10
User=$USER

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable gichul-worker
sudo systemctl restart gichul-worker
sudo bash tools/install_autoupdate.sh "$HERE" "$USER"
echo "완료. 상태 확인: sudo systemctl status gichul-worker   /   기록 보기: journalctl -u gichul-worker -f"
