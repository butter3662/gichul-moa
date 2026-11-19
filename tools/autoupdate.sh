#!/bin/bash
# GitHub에 새 버전이 있으면 받아서 반영한다 (gichul-update.timer 가 10분마다 root로 실행)
# 사용: autoupdate.sh <저장소 폴더> <사용자>
REPO="$1"; OWNER="$2"
cd "$REPO" || exit 1
as_owner() { runuser -u "$OWNER" -- "$@"; }
OLD=$(as_owner git rev-parse HEAD)
as_owner git pull --ff-only -q origin main || { echo "git pull 실패 (로컬에서 바뀐 파일이 있으면 생김)"; exit 1; }
NEW=$(as_owner git rev-parse HEAD)
[ "$OLD" = "$NEW" ] && exit 0
echo "업데이트: ${OLD:0:7} -> ${NEW:0:7}"
# 새로 추가된 원본 PDF 받기 (이미 받은 파일은 건너뜀) + 깨진 PDF 복구
as_owner mkdir -p data/raw data/fixed
as_owner .venv/bin/python -I tools/fetch.py sources.txt data/raw || true
[ -f extra_sources.json ] && as_owner .venv/bin/python -I tools/fetch_extra.py extra_sources.json data/raw || true
while read -r f; do
  [ -z "$f" ] && continue
  [ -f "data/fixed/$f" ] || as_owner pdftocairo -pdf "data/raw/$f" "data/fixed/$f" 2>/dev/null || true
done < fixed_list.txt
# 자동 업데이트 설정 파일이 바뀌었을 수도 있으니 다시 설치
bash tools/install_autoupdate.sh "$REPO" "$OWNER" >/dev/null
systemctl restart gichul-worker
echo "작업기 재시작 완료"
