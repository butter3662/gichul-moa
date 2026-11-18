#!/bin/bash
# 자동 업데이트(10분마다 git pull → 바뀌었으면 PDF 받고 작업기 재시작) 설치
# 사용: sudo bash tools/install_autoupdate.sh   (저장소 폴더 안에서)
REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
OWNER="${2:-${SUDO_USER:-$USER}}"
cat > /etc/systemd/system/gichul-update.service <<UNIT
[Unit]
Description=기출모아 자동 업데이트
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash $REPO/tools/autoupdate.sh $REPO $OWNER
UNIT
cat > /etc/systemd/system/gichul-update.timer <<UNIT
[Unit]
Description=기출모아 자동 업데이트 (10분마다)

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now gichul-update.timer
echo "자동 업데이트 켜짐. 기록 보기: journalctl -u gichul-update -n 20"
