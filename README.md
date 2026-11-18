# 기출모아

과목·학년·연도·월·시험 종류·범위를 고르면 기출 문항을 모아 **문제 PDF**와 **해설 PDF**를 이메일로 보내 주는 개인 학습용 사이트다.

## 구조
```
[화면: GitHub Pages /docs] → [Supabase: gichul_requests 표] → [라즈베리파이 작업기] → [Gmail로 PDF 발송]
```
- 화면은 Supabase 로그인을 한 사람만 요청을 넣을 수 있다 (한 사람당 하루 20건).
- 라즈베리파이 작업기가 대기 중인 요청을 가져가 PDF를 만들고, 요청에 적힌 이메일로 보낸다.
- 원본 PDF와 문항 주석(data/items.json)은 라즈베리파이에만 있다. 화면에는 조건별 문항 수(docs/options.json)만 보낸다.
- 평가원 시험(수능·모의평가)은 해설이 공개되지 않아 해설 파일에 "해설 없음"으로 표시하고 정답만 넣는다.

## 라즈베리파이 설치 / 업데이트
```
cd ~/gichul-moa
git pull
bash setup.sh
```
처음 설치하면 `/etc/gichul.env`가 생긴다. 다음 두 값을 직접 넣는다.
- `SUPABASE_SERVICE_KEY` — Supabase 대시보드 → Project Settings → API Keys 의 secret(service_role) 키
- `GMAIL_APP_PASSWORD` — magilab.co@gmail.com 의 16자리 앱 비밀번호 (Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호)

```
sudo nano /etc/gichul.env
sudo systemctl restart gichul-worker
```

## 관리
- 상태: `sudo systemctl status gichul-worker`
- 실시간 기록: `journalctl -u gichul-worker -f`
- 주석 DB를 바꾼 뒤: `python3 tools/make_options.py` → 커밋·푸시 → 라즈베리파이에서 `git pull && sudo systemctl restart gichul-worker`

## 파일
- `app/worker.py` — 작업기, `app/build_pdf.py` — PDF 만들기, `app/selector.py` — 문항 고르기 규칙
- `docs/index.html`, `docs/options.json` — 화면
- `sources.txt` — 원본 PDF 주소, `fixed_list.txt` — 복구가 필요한 PDF

폰트: 나눔고딕 (SIL Open Font License).
