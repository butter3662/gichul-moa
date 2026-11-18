# 기출 모음 (라즈베리파이용)

과목·학년·연도·월·시험 종류·단원을 골라 기출 문항을 모으면 **문제 PDF**와 **해설 PDF** 두 개를 만들어 주는 개인 학습용 사이트다.

## 설치
1. 이 폴더를 통째로 라즈베리파이에 복사한다 (예: `scp -r gichul pi@<IP>:~/`).
2. 라즈베리파이에서 실행한다.
   ```
   cd ~/gichul
   bash setup.sh
   ```
   중간에 사이트 접속 비밀번호를 묻는다. 원본 PDF 약 1,200개(약 1GB)를 호랭이닷컴에서 받으므로 시간이 걸린다.
3. 같은 와이파이에서 `http://<라즈베리파이 IP>:8080` 으로 접속한다. 아이디는 아무거나, 비밀번호는 설치할 때 정한 것.

## 구성
- `app/server.py` — 서버. 주석 DB는 서버 안에서만 쓰고 브라우저로 보내지 않는다.
- `app/build_pdf.py` — 문항 영역을 원본 PDF에서 벡터 그대로 잘라 붙여 PDF를 만든다.
- `app/static/index.html` — 선택 화면.
- `data/items.json` — 문항 주석 DB (원본 시험, 과목, 번호, 해설 위치, 정답, 단원). **비공개로 보관할 것.**
- `sources.txt` — 원본 PDF 주소 목록, `fixed_list.txt` — 복구가 필요한 PDF 목록.

## 관리
- 상태 확인: `sudo systemctl status gichul`
- 다시 시작(주석 DB를 바꾼 뒤): `sudo systemctl restart gichul`
- 만든 PDF는 6시간 뒤 자동 삭제된다.

폰트: 나눔고딕 (SIL Open Font License).
