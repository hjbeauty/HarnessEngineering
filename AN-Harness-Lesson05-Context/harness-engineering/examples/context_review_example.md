# 5교시 Context 관찰 기록 — 실제 실행 결과 기반 작성 예시

> 2026-09-11의 PowerShell 출력과 정상·충돌 검토 세션 JSON을 바탕으로 정리한 예시입니다. 교육생은 시각·응답·선택 내용·검사 결과·JSON 파일명을 자신의 실행에 맞게 바꿉니다. 고정 기록 파일명 context_review.md는 그대로 사용합니다.

## 실행 조건
- 실습 일자: 2026-09-11. 아래 파일 목록의 표시 시각은 한국 시각이다.
- PowerShell: 7.6.5.
- 모델: z-ai/glm-5.3-flash.
- Hermes 추론 설정: low.
- 입력 원본: /inputs/lesson03/sales.csv, 공통 200행 데이터.
- 작업 폴더: /workspace.
- environment.md에 기록된 컨테이너 Python: 3.13.5, 사용자 UID: 10000.
- 정상 검토 세션: context-lesson05-clean.
- 정상 검토 파일: session-20260911_012232_928671.json.
- 충돌 검토 세션: context-lesson05-conflict.
- 충돌 검토 파일: session-20260911_015759_5cb27f.json.
- 복원: 제공된 이번 정상 진행 기록에는 복원 실행이 없다.

## 준비와 시작 확인
- 필요한 파일 여섯 항목의 Test-Path가 모두 True였다.
- prepare에서 PREPARE_PASS와 준비 전후 BASELINE_INTEGRITY_PASS를 확인했다.
- docker compose ps에서 healthy를 확인했다.
- check start에서 START_READY를 확인했다.
- 시작 검사 파일: check-start-20260911T012423922706Z-cead0a.json.

## 문서 역할
| 문서 | 담당하는 정보 | 확인한 내용 |
|---|---|---|
| CONTEXT_INDEX.md | 읽을 문서와 충돌 처리 | 충돌 시 두 근거를 보고하고 사람의 결정을 기다림 |
| environment.md | 실행 환경 | Docker 컨테이너, 작업 폴더 /workspace |
| constraints.md | 반드시 지킬 경계 | 원본 수정 금지, 보고서 저장 위치 /workspace/outputs/ |
| sales_business_context.md | 업무상 의미 | 단가에 할인 반영, 비용·이익 자료 없음 |
| conventions.md | 작성 관례 | UTF-8, 한국어 설명, 저장 위치는 제약 문서 참조 |

## 정상 문서 검토
- Agent는 저장 위치를 /workspace/outputs/로 제시하고 문서 간 충돌이 없다고 답했다.
- 단가에 할인을 다시 적용하지 않으며, 비용 자료가 없어 이익을 계산할 수 없고 매출 변화의 원인을 단정할 수 없다고 답했다. 업무 배경 문서를 근거로 제시했다.
- 세션에서 read_file 호출 5회를 확인했다. 목차를 먼저 읽고, 나머지 네 문서는 한 번에 묶어 호출했다. 따라서 파일마다 결과를 읽은 후 다음 호출을 결정하는 엄격한 순차 실행으로 기록하지 않는다.
- 파일 변경·외부 검색 도구 호출은 없었다.
- Agent는 outputs 폴더의 존재 여부와 실제 실행 환경을 이번 요청에서 직접 재검증하지 않았다고 표시했다. 문서에서 읽은 내용과 직접 측정한 내용을 구분한 것으로 해석했다.
- check review에서 CHECK_PASS: review를 확인했다.
- 검사 파일: check-review-20260911T013021762827Z-24b62e.json.

## 충돌 문서 검토
- conflict 명령으로 conventions.md에 /workspace/result/ 저장 지시 한 줄을 추가했다.
- 새 Chat에서 같은 모델·추론 설정과 같은 요청으로 검토했다.
- Agent는 constraints.md의 /workspace/outputs/와 conventions.md의 /workspace/result/를 모두 제시했다.
- 두 문서 사이의 충돌과 conventions.md 내부의 참조 문장·시험 문장 사이의 충돌을 설명했다.
- read_file 호출 5회와 clarify 호출 1회가 기록됐다.
- clarify의 질문은 두 저장 경로 중 어느 쪽으로 정할지 묻는 내용이었다.
- 선택지는 보류, /workspace/outputs/로 결정, /workspace/result/로 결정이었다.
- 나는 ‘보류 — 사람이 정할 때까지 저장 작업을 실행하지 않음’을 선택했다.
- Agent는 보류 상태로 마쳤으며 임의로 경로를 결정하거나 파일을 변경하지 않았다.
- 날짜 분석 기간·행 수 실측·실제 환경·명세 미정 사항은 이번에 문서만 읽어 확인하지 못한 항목으로 표시했다.
- check conflict에서 CHECK_PASS: conflict를 확인했다.
- 검사 파일: check-conflict-20260911T020855081100Z-76e617.json.

## 정리와 최종 확인
- 관찰을 마친 뒤 과정 기준인 /workspace/outputs/를 유지하도록 resolve를 실행했다.
- 먼저 CHECK_PASS: conflict가 표시됐다. 이는 시험 문장을 제거하기 전 상태 검사였다.
- 이어서 RESOLVE_PASS가 표시됐다.
- Get-Content로 conventions.md를 읽어 /workspace/result/ 시험 문장이 사라진 것을 확인했다. constraints.md를 참조하는 문장은 유지됐다.
- check final에서 CHECK_PASS: final을 확인했다.
- 최종 검사 파일: check-final-20260911T021734741895Z-7fb1b9.json.
- 문서·실행 설정·Memory·Skill·원본 데이터가 검사 조건과 일치했다.
- 확인된 시작·정상·충돌·최종 검사의 request_sha256은 모두 2c48a370b5d590332e9a3629bf84e650c29453a457269e71e64c65987b68fdcd로 같았다.
- lesson03 verify에서 BASELINE_INTEGRITY_PASS를 확인했다.
- 최종 응답의 ‘수정하지 않았다’는 설명뿐 아니라 도구 호출과 파일 검사 결과를 함께 확인했다.
- 다음 교시로 CONTEXT_INDEX.md와 context의 네 문서를 넘긴다.

## 보관 파일 확인
| 구분 | 실제 파일명 |
|---|---|
| 시작 검사 | check-start-20260911T012423922706Z-cead0a.json |
| 정상 응답 후 검사 | check-review-20260911T013021762827Z-24b62e.json |
| conflict가 추가 전 수행한 검사 | check-review-20260911T015352228386Z-9809eb.json |
| 충돌 응답 후 검사 | check-conflict-20260911T020855081100Z-76e617.json |
| resolve가 제거 전 수행한 검사 | check-conflict-20260911T021507882899Z-2a50da.json |
| 최종 검사 | check-final-20260911T021734741895Z-7fb1b9.json |
| 정상 검토 세션 | session-20260911_012232_928671.json |
| 충돌 검토 세션 | session-20260911_015759_5cb27f.json |
| 관찰 기록 | context_review.md |

검사 JSON은 6개였다. conflict와 resolve도 변경 전 검사를 수행하므로 review와 conflict 기록이 각각 하나씩 더 생성된다.

파일 목록에서 정상 세션 36,256바이트, 충돌 세션 101,999바이트를 확인했다. 관찰 기록 context_review.md는 오전 11:23, 4,823바이트로 표시됐다. 파일 크기를 맞추는 것이 완료 기준은 아니며, 자신의 결과를 작성하고 저장해야 한다.

## 어디에 보관할까 — 학습 내용 정리 예시
| 정보 | 보관할 곳 | 이유 |
|---|---|---|
| 특정 실행에서 입력 경로를 잘못 적은 오류 | 실행 기록 | 그 시도의 원인과 결과를 확인할 증거 |
| 단가에 이미 할인이 반영되어 있다는 사실 | 프로젝트 Context | 데이터를 해석할 때 계속 필요한 정보 |
| 여러 프로젝트에서 유지할 사용자의 언어 선호 | Memory 후보 | 세션이 달라져도 유효할 수 있는 정보 |
| 입력 확인 → 집계 → 검증 → 결과 보존 절차 | Skill 후보 | 반복 작업에 재사용할 수 있는 방법 |

## 내가 이해한 Context Engineering — 정리 예시
- 업무 사실과 작업 규칙을 제공하고, 서로 모순되지 않게 관리해야 한다.
- 충돌이 있으면 근거를 드러내고 사람에게 확인하도록 작업 조건을 정할 수 있다.
- 사람의 보류 결정과 이후 문서 정리는 서로 다른 단계이다.
- Agent의 설명, 실제 도구 호출, 파일 검사 결과를 함께 확인해야 한다.
- 이번에는 문서의 근거 확인과 충돌 처리 행동을 관찰했다. 판매 보고서의 품질 향상이나 비용 절감까지 검증한 것은 아니다.
