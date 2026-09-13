# Harness Engineering 공통 데이터

이 데이터는 3~12교시에서 함께 사용합니다. 처음 한 번 준비한 파일을 계속 사용하며, 교시가 바뀌어도 원본을 다시 생성하거나 교체하지 않습니다.

## 준비

1. 공통 데이터 ZIP을 임시 폴더에 압축 해제합니다.
2. 안에 있는 `harness-engineering` 폴더의 내용을 `C:\AI-Native\harness-engineering`에 합칩니다.
3. 이미 `inputs\lesson03\sales.csv`가 있으면 그대로 둡니다. 이 패키지의 해당 파일은 3교시 패키지와 바이트까지 같습니다.
4. CSV는 읽기 전용 원본으로 보관합니다. 가이드북에서 지정한 입력을 작업용 폴더에 준비해 실행합니다.

기존 Compose 설정으로 `inputs` 아래 파일은 컨테이너의 `/inputs`에서 읽을 수 있습니다. 모든 CSV가 처음부터 이 위치에 있으므로 모델이 한 번도 보지 않은 비공개 시험이라고 가정하지 않습니다. `context`와 `spec` 문서는 가이드북에서 지정할 때 작업 폴더에 제공하며, 루트 폴더에 있는 것만으로 Agent가 읽었다고 판단하지 않습니다.

## 공통 파일의 역할

| 경로 | 용도 |
|---|---|
| inputs/lesson03/sales.csv | 기존 200행 공통 과제. 최초 Baseline과 이후 같은 입력 비교에 사용 |
| inputs/sales/sales_micro.csv | 10행. 계산을 직접 확인 |
| inputs/sales/sales_practice.csv | 72행. 프로그램 개발·반복 검증 |
| inputs/sales/sales_transfer.csv | 52행. 13종 제품을 포함한 재사용 확인 |
| inputs/sales/boundaries/ | 주문 1건, 제품 2종, 큰 금액의 정상 입력 |
| inputs/sales/relations/ | 행·열 순서, BOM, 줄바꿈, 단가 두 배, 분할 입력 관계 확인 |
| inputs/sales/errors/ | 한 종류의 오류가 있는 입력과 빈 파일 |
| inputs/sales/sales_mixed_errors.csv | 여러 오류가 섞인 입력. 첫 오류 보고가 기본 정책 |
| inputs/sales/comparison/ | GLM·Qwen에 똑같이 제공할 고정 비교 입력 |
| context/sales_business_context.md | 업무 배경과 열의 의미 |
| spec/SALES_SPEC.md | 입력 규칙, 계산, 출력, 오류 처리 기준 |

`comparison`은 용도를 구분한 이름입니다. 다른 데이터와 함께 제공하는 공통 시험 파일이며 비공개 데이터가 아닙니다. 정답 수치를 프로그램에 직접 넣지 않고 입력에서 계산합니다.

## 교시별 사용

| 교시 | 공통 데이터 활용 |
|---|---|
| 3 | sales.csv로 최초 결과 기록. 상세 명세·정답은 먼저 제공하지 않음 |
| 4 | 판매 데이터 보존. 실행 경계는 별도 시험용 파일·빈 폴더로 확인 |
| 5 | 같은 sales.csv에 업무 설명 제공 전후 비교 |
| 6 | 명세를 제공하고 sales_micro.csv로 계산 확인, sales.csv에 적용 |
| 7 | 같은 프로그램의 작업 계획을 세우고 sales_practice.csv로 실행 |
| 8 | 같은 과제에서 도구·접근 경로·원본 보호 확인 |
| 9 | sales_transfer.csv를 동일하게 사용해 Skill 적용 전후 비교 |
| 10 | boundaries·relations·errors로 검증 |
| 11 | 오류 파일과 sales_mixed_errors.csv로 복구·재검증 |
| 12 | comparison의 동일 파일 목록으로 GLM·Qwen 비교 |

각 비교에서 모델·요청·데이터·시작 코드를 같게 맞추고, 확인하려는 조건만 바꿉니다. 새 실행은 이전 실행의 수정 코드와 결과를 물려받지 않도록 같은 시작 상태에서 진행합니다. 다른 파일의 점수 차이를 Harness 개선 효과로 계산하지 않습니다.

## 결과 기록

입력 파일명·해시, 모델·설정, 요청, 시작 코드, 도구 실행, 종료 코드와 출력 파일을 남깁니다. 데이터가 달라졌다면 별도의 시험으로 표시합니다. 오류 입력에서는 정상 출력이 덮어써지지 않았는지 확인합니다. 기존 Baseline은 보존합니다.
