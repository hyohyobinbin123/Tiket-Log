# Ticket Log | 티켓로그

두 수업 노트북을 통합한 Streamlit 공연 예매 일정 관리 웹앱입니다. 실제 예매 및 결제는 공식 예매처에서 하고, 이 앱은 예매 일정과 구매 상태를 기록합니다. QR 입장권이나 결제 기능은 없습니다.

## 수업 코드와의 연결
- 첫 번째 노트북: KOPIS 공연목록 → 공연 상세 → 예매처별 URL 수집, Pandas 표, 수동 오픈일시 입력, D-Day, 카드/표, 수정/삭제 유지.
- 두 번째 노트북: `calendar.Calendar(firstweekday=6)`의 월별 날짜 그리드와 일정 개수, 날짜 클릭 필터링을 Streamlit 버튼으로 이식.
- 추가: Supabase 이메일 인증, 계정별 일정 저장 및 RLS, 구매 상태 관리, 가상 시연 데이터 분리. API에서 받아온 공연/예매처를 선택하는 방식으로 입력 오류 방지.
- Gemini의 미검증 예매일 생성은 채택하지 않았습니다. KOPIS의 공연 기간은 예매 오픈 날짜와 다르므로 공식 링크에서 사용자가 확인한 시간을 직접 입력합니다.

## 1. GitHub 업로드
1. https://github.com/new 에서 새 저장소(예: `ticketlog-integrated`)를 Public으로 생성합니다. 기존 캠퍼스패스 저장소를 덮어쓰지 마세요.
2. ZIP을 압축 해제합니다. `app.py`가 있는 폴더 **안의 내용**을 저장소 루트에 업로드하세요. `Add file → Upload files` 또는 빈 저장소의 `uploading an existing file`을 이용합니다. `.streamlit/config.toml`도 포함하세요(숨김 폴더라면 수동으로 추가해도 됩니다).
3. Commit changes를 누릅니다. `app.py`, `requirements.txt`, `catalog.py`, `schedule.py`, `db.py`, `schema.sql`이 루트에 있는지 확인하세요.

## 2. Supabase 준비 (로그인 및 영구 저장)
1. https://supabase.com/dashboard 에서 새 프로젝트를 생성합니다.
2. SQL Editor → New query에서 `schema.sql` 전체를 붙여넣고 Run 합니다.
3. Table Editor에서 `ticketlog_schedules`가 생성됐는지 확인합니다. RLS 정책은 자신의 계정 행만 읽기/쓰기 허용합니다.
4. 프로젝트 Connect 또는 Settings의 API Keys에서 Project URL과 publishable key(기존 anon key도 가능)를 확인합니다. **service_role/secret key는 사용하지 마세요.** Authentication의 Email provider와 신규 가입을 활성화합니다. 이메일 확인은 유지할 것을 권장합니다.
5. 배포 후 Authentication → URL Configuration에서 실제 Streamlit 공개 URL을 Site URL에 지정합니다. 확인 메일이 필요한 계정은 이메일 확인 뒤 앱에서 로그인합니다. 메일 발송 제한이 있을 수 있습니다.

## 3. KOPIS 인증키
https://www.kopis.or.kr/ 에서 Open API 신청/발급을 이용합니다. 발급된 키는 Streamlit Secrets에만 보관합니다. 키가 없으면 시연 모드에서 시작합니다. 원본 노트북에 노출된 키와 터널링 토큰은 재발급을 권장합니다. 이 ZIP에는 실제 키가 없습니다.

## 4. Streamlit 공개 배포
1. https://share.streamlit.io/ 에 GitHub로 로그인합니다.
2. Create app → GitHub 저장소에서 배포 → Repository, Branch `main`, Main file path `app.py`를 지정합니다.
3. Advanced settings의 Secrets에 `secrets.example.toml` 내용을 복사하여 자신의 값으로 교체합니다. Python 버전을 선택할 수 있다면 3.11 또는 3.12를 사용합니다.
4. Deploy. 생성된 `https://...streamlit.app` 주소를 교수님과 조원들에게 전달하세요. 공개 저장소 및 앱 공개 접근 설정을 확인하세요. 설정 전에는 시연 모드만으로 배포할 수 있습니다. 이후 앱 Manage/Settings에서 Secrets를 수정할 수 있습니다.
5. 시크릿 모드에서 주소를 열어 로그인 전 공연 탐색이 되는지 확인하세요. 무료 플랜은 휴면 및 사용량 제한이 있을 수 있습니다.

## 5. 사용 및 테스트
- 실제 모드: 공연 탐색 → KOPIS 공연 불러오기 → 공식 예매처에서 오픈 일시 확인 → 로그인 → 일정 등록.
- 달력: 날짜를 선택 → 그 날짜의 기존 일정 확인 및 추가. 실제 모드에서 등록 전 공연 탐색 메뉴에서 조회가 필요합니다.
- 내 티켓: 수정/삭제/구매 상태 변경 및 CSV 내보내기.
- 시연 모드: 가상 공연 4개로 로그인 없이 동작 체험. 시연 기록은 세션에만 남고 실제 DB에는 저장되지 않습니다.
- 서로 다른 두 테스트 계정으로 가입해 A의 일정이 B에 표시되지 않는지 확인하세요. 새 브라우저에서 재로그인해 일정이 유지되는지, 동일 공연/예매처/시간 중복 추가가 차단되는지 확인하세요.
- 약한 비밀번호 등 가입 오류는 화면에 안내됩니다. 일부 이메일 가입 오류는 계정 존재 여부 보호를 위해 일반 메시지가 나올 수 있습니다.

## 로컬 실행 (선택)
`python -m pip install -r requirements.txt` → `.streamlit/secrets.toml`을 로컬에서 생성(깃허브 업로드 금지) → `streamlit run app.py`.

## 검증 범위
Python 문법 검사와 모의 KOPIS 응답, 달력, 필터, 오류 안내 등 단위 테스트를 수행했습니다. 실제 Streamlit/Supabase 패키지 설치가 이 작업 환경에서 불가능했으므로 브라우저 화면, 실서버 API 및 인증/DB 통합 테스트는 배포 후 확인해야 합니다.
