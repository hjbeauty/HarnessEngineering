> 2026-09-10 실제 터미널 기록과 로그인 화면을 반영한 예시입니다. 자신의 관찰 결과로 작성하세요.

# 2교시 환경 점검

## 실제 확인

- 실습 날짜: 2026-09-10
- 작업 폴더: C:\AI-Native\harness-engineering
- PowerShell 버전: 7.6.5
- WSL 버전: 2.7.13.0
- Docker Desktop 버전: 4.90.0
- Docker Client / Server Engine 버전: 29.7.2 / 29.7.2
- Docker Client와 Server 연결: 두 항목 모두 출력되어 연결 확인
- Docker Context: desktop-linux
- Docker Compose 버전 / OSType: v5.5.1 / linux
- hello-world 결과 / 종료 코드: Hello from Docker! / 0
- compose.yaml 구문 확인: docker compose config --quiet 종료 코드 0
- Hermes 이미지 다운로드: 성공, 종료 코드 0
- Hermes 컨테이너 실행: 성공, 종료 코드 0
- Hermes 서비스 최종 상태: healthy

### 브라우저 로그인 확인

- 접속 주소: http://127.0.0.1:9119/sessions
- 로그인 결과: 성공
- 화면 왼쪽 아래 사용자 / 인증 방식: student / via basic
- auth_required / auth_providers: True / basic
- 열린 화면: Sessions
- 세션 현황: Total 0, Active in store 0, Archived 0, Messages 0
- 화면 중앙 안내: No sessions yet
- 화면에 표시된 Hermes 버전: v0.21.1
- Gateway Status 표시: Off
- 새 InPrivate/시크릿 창에서 로그인 요구 확인: 제공된 기록에서는 미확인

### 최초 환경 점검

- create 점검 결과 / 종료 코드: ENVIRONMENT_PASS / 0
- Linux 실행 환경과 점검 명령의 일반 사용자 실행: 통과
- Windows 파일을 컨테이너에서 읽기: 통과
- 입력 파일 읽기: 통과
- 입력 폴더 쓰기 차단: 통과, read-only filesystem 확인
- 작업 폴더와 상태 볼륨의 확인 파일: 통과
- Git 초기화와 사용자 이름·이메일 설정: 통과
- Windows에서 container_marker.txt 확인: created-in-container
- 결과 파일: probe-create-20260910T042939957345Z.json

### 컨테이너 재생성 후 점검

- 실행 명령: docker compose up -d --force-recreate hermes
- 재생성 전 컨테이너 ID:
  b77e43491d342e09bd9c9877065b3fe6f7c532c65b4cd859a864f51afbc7684a
- 재생성 후 컨테이너 ID:
  79f7cdf2a8184a40344f8e593fd715b552f43a242fca7662246d7bdd124c064f
- 전후 ID 비교: 다름, 새 컨테이너 생성 확인
- verify 점검 결과 / 종료 코드: ENVIRONMENT_PASS / 0
- 작업 폴더·상태 볼륨의 확인 파일 유지: 통과
- 입력 폴더 쓰기 차단 유지: 통과
- Git 사용자 설정 유지: 통과
- 결과 파일: probe-verify-20260910T043213014989Z.json

### 중지와 다시 실행

- docker compose stop 결과: 컨테이너 중지
- 중지 후 표시: Exited (137)
- docker compose up -d 결과: 다시 실행됨
- 다시 실행한 직후 상태: health: starting
- 잠시 후 최종 상태: healthy

## 내 말로 설명

- 이미지와 컨테이너의 차이:
  이미지는 프로그램과 실행에 필요한 파일을 담은 바탕이다.
  컨테이너는 그 이미지를 이용해 만든 실행 공간이다.

- compose.yaml의 역할:
  사용할 이미지, 연결할 폴더, 포트와 실행 설정을 담은 파일이다.
  Docker Compose는 이 파일을 읽어 컨테이너를 실행하고 관리한다.

- 입력 폴더 쓰기가 막힌 것이 성공인 이유:
  입력 폴더를 읽기 전용으로 연결했기 때문이다.
  읽기는 가능하고 쓰기는 차단되어 원본 보호 설정이 작동함을 확인했다.

- 컨테이너가 달라졌는데 파일이 남은 이유:
  Windows 작업 폴더와 Docker 볼륨에 데이터를 저장했기 때문이다.
  새 컨테이너에도 같은 저장 공간이 연결되어 파일과 설정이 유지됐다.

- Docker Desktop과 Hermes 웹 대시보드의 역할:
  Docker Desktop은 컨테이너를 실행하고 관리한다.
  Hermes 웹 대시보드는 브라우저에서 Hermes를 사용하는 화면이다.

- 로그인 성공을 판단한 근거:
  Sessions 화면이 열렸고, 왼쪽 아래에 student와 via basic이 표시됐다.

## 남은 문제

- 설정 버전 경고 원문:
  This config predates version 12 (~2 years old) and can no longer be auto-migrated.

- 경고에 대해 확인한 사실:
  설정 자동 변환 경고가 출력됐지만 Dashboard 기동과 로그인은 성공했다.
  설정 파일의 버전 정보와 수업 설정의 적용 상태는 추가 확인이 필요하다.

- 중지 시 종료 코드: Exited (137)
- 종료 코드의 원인: 아직 확인하지 않음
- 경고 해결을 위해 수정한 내용: 없음
- 중지 후 다시 실행한 결과: healthy 확인
- 경고와 종료 코드의 원인이 해결됐는지: 미확인
- 추가 확인: 새 InPrivate/시크릿 창에서 로그인이 요구되는지 확인
- 현재 상태:
  터미널 환경 점검, 컨테이너 재생성 후 데이터 유지와 브라우저 로그인을 확인했다.
  설정 버전 경고와 종료 코드 137의 원인은 추가 확인 항목으로 남긴다.
