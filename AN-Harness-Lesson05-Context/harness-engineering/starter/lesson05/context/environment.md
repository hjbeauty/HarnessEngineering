# 실행 환경

적용 범위: 이 프로젝트의 Hermes 실행 환경.
출처: 5교시 준비 스크립트가 확인한 컨테이너와 설정.
확인 시각(UTC): @UTC@

- 교육생은 Windows PowerShell에서 Docker 명령을 실행합니다.
- Agent는 Docker 컨테이너 안에서 실행됩니다. terminal.backend는 local입니다.
- Agent의 작업 폴더는 /workspace입니다.
- 컨테이너 운영체제: Linux. Python 버전: @PYTHON@. 실행 사용자 UID: @UID@.
- 공통 원본 데이터: /inputs/lesson03/sales.csv, 데이터 행 200개.
- 모델: z-ai/glm-5.3-flash. Hermes 추론 설정: low.
- Windows의 workspace 폴더가 컨테이너의 /workspace에 연결됩니다.
- /inputs와 /course-tools는 읽기 전용으로 연결됩니다.
- 실제 환경과 문서가 다르면 문서를 근거로 환경을 추측하지 말고 차이를 보고합니다.
