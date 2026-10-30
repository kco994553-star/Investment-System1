# 현재 인수인계 — 2026-10-29

기준 **2026-10-29 13:48 UTC / 22:48 KST**, canonical **`3f3ccd2f`** (#411). `origin/main`은 없으며 실제 기본 브랜치는 **`claude/investment-system-top500-validation-alrugm`**이다. git log·PR 메타데이터·Actions job 로그·공개 파일을 대조했다. 이후 실행은 다시 조회한다.

읽기: [START_HERE](START_HERE.md) → [방향 전환 대장](docs/SPEC/DIRECTION_CHANGES.md) → [WORKING_RULES](WORKING_RULES.md) → [기능 현황](docs/SPEC/FUNCTION_STATUS.md) → [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md). 오늘 이행은 10/29 오너 승인(중앙 V 첫 게시, 화면 PR 병합)과 같은 날 확장 모집단 지시(DC-27, 결정 기록은 #423)를 따른다.

## 0. 역할·지금 관리할 흐름 (최대 3개)

Main이 공용 파일·코드·병합·배포를 조정한다. Codex는 검증·리뷰와 허용된 문서만 맡는다(DC-09). 예외는 확장 모집단 E0/E1-A로, 10/29 지시에 한해 전용 브랜치·Draft PR까지만 허용된다(DC-27). 이 예외로 공용 파일·병합·배포 권한이 넓어지지 않는다.

| 흐름 / 기능번호 | Main 이행 | 현재 상태 |
| --- | --- | --- |
| **1 중앙 V / 2·6** | 첫 게시 완료. 다음: TARGET 숫자 재기록 #424 병합(승인 뒤), 정기 실행에서 매일 `attempt=OK` 확인 | **게시됨**(아래 4·6절). TARGET 확정은 #424 전까지 calc_version 불일치로 막힘 |
| **2 프론트엔드 / 1·2** | 화면 PR 4개 병합 완료(배포 안 됨, P3 전환 때). 다음 P2: 새 프론트엔드의 공식 V 판독기(`qgv.js` OFFICIAL_READER) → 2.2 → 2.4·2.3.1·2.5 → 6 → … | 병합됨, 다음 PR 준비 전 |
| **3 확장 모집단 / 공통** | #423 계획·DC-27·E1-B/E2 설계(병합 승인 대기). Codex #422(E0/E1-A) 인수 검토 | #422 인수 검토 완료 — 병합 준비, 오너 승인 대기([설계 문서 1절](implementation/docs/expanded_universe/MAIN_E1B_E2_DESIGN_20261029.md)) |

### 작업 중

| PR·작업 | 담당 | 시작 (UTC) |
| --- | --- | --- |
| #424 TARGET v1 숫자 검증 재기록(23.1): 승인 대기, 열린 항목 = EME·CMG 새 10-Q 칸 원문 대조 | Claude Code Main | 10/29 13:20 |
| #423 확장 모집단 Main 통합 계획·DC-27·10/29 결정 기록 + #422 인수 결과·E1-B/E2/백테스트 경계 설계 + 10/30 오너 결정 반영(확장 정의 4기준·ADR 포함·공급처 약관·역산 시험·결정표 정리, DC-28): 반영 끝, 승인 대기 | Claude Code Main | 10/29 11:30 · 14:30 · 10/30 09:20 |
| 이 문서 PR(10/29 인수인계·기능 현황·첫 게시 점검표 기록) | Claude Code Main | 10/29 13:40 |

## 1. 승인 이행·오너 결정

| 번호 | 실제 상태·남은 조건 |
| --- | --- |
| **0 시작 확인** | 10/28분 정기 실행 #28 성공, **연속 7/7**(#21·#22·#23·#25·#26·#27·#28; #24는 수동이라 집계 밖). Secret 이름 2개 확인(값은 보지 않음) |
| **1 화면 PR** | #415 리더보드에 기업 선택 UI가 없어 **#421 → #415 → #419 → #420** 순서. 병합마다 canonical 동기화, 마지막 병합 뒤 CI 1회(6체크 녹색). 처음 쓰는 기기 확인: 새 앱 `#/qgv`를 새 브라우저 2개(1440·390)와 새로 고침에서 열었고, 같은 행·기준 칩, 기기 저장 0, 외부 요청 0, 오류 0 |
| **2 중앙 V 첫 게시** | 사슬 #393 → #400 → #403 → #404 → #405 병합 → `all_shards` 1회 → 재기록 PR #424(열림, 승인 뒤 병합) → #411 동기화·병합 → [점검표 8절](implementation/docs/qgv_scoring_standard/CENTRAL_V_GO_LIVE_CHECKLIST_20261024.md) 기록 |
| **3 멈춤 조건** | 해당 없음. VALID·MATCH(`attempt=OK`), 공급률 357/357 = 100%, 공개 파일에 가격·보유 칸 0, 원장 PRIMARY 유지 |
| **4 마무리** | 공개 파일 게시와 처음 쓰는 기기의 공식 V 표시를 확인(4절). 이 문서 PR |
| 확장 모집단(DC-27) | #423에 계획·결정 기록. 승인 항목 `EXP-*`·`LAB-PUBLISH`(결정 표) |
| T-FRESH · MANUAL-QUOTE · TV0-* · CV-MONTHEND-RECENT · D5-UPDATE · LISTING-ENDED-CODE | [결정 원문](implementation/docs/USER_DECISIONS_PENDING.md#남아-있는-결정만) 그대로 |

## 2. 10/29 병합 (mergedAt UTC)

| PR | 내용 | UTC | merge SHA |
| --- | --- | --- | --- |
| [#421](https://github.com/kco994553-star/Investment-System1/pull/421) | 레이더 브라우저 시험 시계 고정 | 10:24:36 | `500f7847` |
| [#415](https://github.com/kco994553-star/Investment-System1/pull/415) | P2-2a 메뉴 1 QGV·리더보드(배포 안 됨) | 10:27:28 | `6ab756d6` |
| [#419](https://github.com/kco994553-star/Investment-System1/pull/419) | 공용 기업 검색 부품(DC-23, 배포 안 됨) | 10:28:24 | `d8553b58` |
| [#420](https://github.com/kco994553-star/Investment-System1/pull/420) | 영상 양식·색 규칙(DC-25·26, 배포 안 됨) | 10:29:03 | `282382a7` |
| [#393](https://github.com/kco994553-star/Investment-System1/pull/393) | F_k·calc_version `qgv2-calc/2026-10-23.1` | 11:58:24 | `a1f1b704` |
| [#400](https://github.com/kco994553-star/Investment-System1/pull/400) | 중앙 V 계산 코어 | 12:08:11 | `34487a9d` |
| [#403](https://github.com/kco994553-star/Investment-System1/pull/403) | 중앙 V 가드 | 12:12:47 | `7dd182f6` |
| [#404](https://github.com/kco994553-star/Investment-System1/pull/404) | 중앙 V 워크플로·점검표 | 12:12:53 | `f16dadd2` |
| [#405](https://github.com/kco994553-star/Investment-System1/pull/405) | 옛 화면 판독기(TARGET v1 공식 V) | 12:13:03 | `d149c91d` |
| [#411](https://github.com/kco994553-star/Investment-System1/pull/411) | TARGET 확정 차단 점검 | 13:39:07 | `3f3ccd2f` |

- 사슬 다섯 PR은 최신 canonical과 동기화했다(충돌 없음). 맨 위에서 전체 시험 1회를 돌렸다: 파이썬 4,025, 빌드·가드, 노드, Worker, 브라우저 817, M2.
- 독립 검토 1회 결과 막는 문제는 없었다. 각 HEAD의 필수 6체크가 녹색인 것을 보고 병합했다.
- 병합 뒤 canonical 트리는 시험한 사슬 맨 위 트리와 같다.
- #411은 사슬 위로 합치면서 충돌 9곳을 풀었다. 확정 차단 점검과 PR-D 공식 V 읽기를 둘 다 유지했다. TARGET 노드 41/41, 브라우저 390·1280, 가드 PASS, CI 6체크 녹색.

## 3. 열린 PR·CI·승인

| PR | 제목 요지 | 상태 | 오너 승인·조건 |
| --- | --- | --- | --- |
| [#424](https://github.com/kco994553-star/Investment-System1/pull/424) | TARGET 숫자 검증 재기록(23.1) | CI 진행 | **병합 승인 필요.** 열린 항목: EME·CMG 새 10-Q 칸 원문 대조(SEC 연락처 필요) |
| [#423](https://github.com/kco994553-star/Investment-System1/pull/423) | 확장 모집단 계획·DC-27·10/29 결정·#422 인수 결과·E1-B/E2 설계 | CI 확인 | 문서 병합 승인 필요 |
| [#422](https://github.com/kco994553-star/Investment-System1/pull/422) | Codex 확장 카탈로그 E0/E1-A(신규 10개, Draft) | `a30b54bb` CI 6 녹색(11:21 base 기준). Main이 canonical+#422로 전체 4,115·저장소 가드 PASS 확인 | **병합 승인 필요.** 병합 직전 canonical 동기화 뒤 CI 재확인 |
| [#418](https://github.com/kco994553-star/Investment-System1/pull/418) · [#417](https://github.com/kco994553-star/Investment-System1/pull/417) · [#416](https://github.com/kco994553-star/Investment-System1/pull/416) | 백테스트 연구·기준(연구 담당) | Draft·Open | #417은 calc_version 17.1·점수 원본 SHA를 고정해 둠 → #393 뒤 다시 고정 필요(`EXP-417-REPIN`) |
| [#392](https://github.com/kco994553-star/Investment-System1/pull/392) | TARGET v0 결합 해소 | DIRTY | 통합 검증·최종 승인 별도 |
| [#361](https://github.com/kco994553-star/Investment-System1/pull/361) | Worker 분할 이벤트 | DIRTY | 공급원 권리로 보류 |
| #305 · #281 · #267 | 옛 시안·스튜디오 | draft·보류 | 참고 |

조회 범위: repo ruleset 24499602 HG-02 — PR 필수, 리뷰 승인 수 0, 필수 check `repository-guard`, 최신 기준 강제 없음. GitHub 리뷰 0과 오너 승인(대화·결정 기록)은 별개다.

## 4. 실제 상태·게시 검증

| 대상 / 기능번호 | 구현 | 시험·검증 | 통합 | 배포 | LIVE |
| --- | --- | --- | --- | --- | --- |
| 중앙 V / 2·6 | 완료 | 전체 시험·CI 녹색, verify `QGV_OFFICIAL_CHECK publication=VALID status=VALID consistent=YES new=YES`(시험 311) | 완료 | **완료**(run 40871484448, 13:31) | **확인**: 공개 파일, 처음 쓰는 기기의 TARGET 빌더 공식 V |
| #411 / 2.1.7·6.1 | 완료 | CI 녹색 | 완료 | 다음 정기 배포 | 미확인(배포 뒤) |
| #415·#419·#420 / 1·2 | 완료 | CI 녹색, 새 앱 처음 쓰는 기기 확인(로컬 빌드 + 실공개 파일) | 완료 | 해당 없음(`web_app/`은 P3 전환 때) | 해당 없음 |
| #424 / 6.1.2~6.1.4 | 완료 | 로컬 TARGET 시험 통과, CI 진행 | 승인 대기 | — | — |

공개 파일 **13:33 UTC** 확인:

| 항목 | 실측 |
| --- | --- |
| `qgv-official.json` | 200, 1,110,701 B, sha256 앞 16자 `1ffb90e4596a107f`(비공개 이력 `qgv-official-2026-10-28` 자산과 같음). `qgv-official/1`, calc_version 23.1, 기준일 **2026-10-28**(요청 10-29), IEX 표시 문구. 행 523·순위 356·V 점수 373. 가격·EV·시가총액·수익률 칸 0 |
| `qgv-official-status.json` | `attempt_state OK`, 게시본 id 일치 |
| 처음 쓰는 기기 | 새 브라우저(로그인 없음, 390·1280) → 플레이북 TARGET v1 빌더 초안 만들기 → "공식 V · 중앙 게시 · IEX 마지막 체결가 기준(공식 종가 아님) · 가격 기준일 2026-10-28 · 게시본 qgvpub-fa5a7ab5e4ea", 통과 159·후보 30. 읽은 파일 `sec-qgv2.json`·`qgv-official.json`뿐, 외부 요청 0, 오류 0 |
| `sec-qgv2.json` | sha256 앞 16자 `4ee3a6e9a6ea1956`, as_of 12:46:36, 504행, 값 있는 501행 모두 23.1, 혼합 0, Q 485·G 493, 단면 498. F_k 실린 행 422 |
| 원장 | 원장 단계 `records=8 appended=0`(일회성 실행). deploy 신선도 v1·v2 8/8 보존. 새 파일에 `observation_basis` 적용: 10/29~11/05 세션 PRIMARY(사유 없음, 새 구간 23.1) |
| 화면의 V | 리더보드·상세·레이더 V축은 아직 기기 V("임시 V"). 공식 V를 읽는 화면은 옛 화면 TARGET 빌더뿐 |

## 5. 다음 우선순위·대기열

1. **오늘 밤 10/29분 정기 실행**(10/30 00:18~02:30 UTC 무렵, 새 코드로 처음). 확인할 것:
   - `QGV_OFFICIAL attempt=OK published=NEW`(기준일 10-29 예상)
   - 연속 집계: DC-13 기준 7/7 달성 뒤의 계속 성공 여부
   - #411 화면 배포
   - 원장 10/29 세션 PRIMARY
2. **#424 병합**(승인 뒤): TARGET 확정 창 11-09~11-15 전에. 열린 항목(EME·CMG 원문 대조)을 먼저 끝낼지는 오너 결정.
3. **확장 모집단**: #422 병합(승인 뒤) → 승인 없이 가능한 합성 단계 E1-B.1~.3·E2-a → Codex 후속(PIT-F1 등). dry-run·일정·가격·공개 범위는 `EXP-*` 결정 뒤. (정정: 이 문서 첫 판의 "Codex PR 없음(13:48)"은 다시 조회하지 않은 오기였다 — #422는 11:21에 열렸다.)
4. **프론트엔드 P2**: 새 앱 공식 V 판독기 → 2.2 → … P3 실사이트 전환·배포는 별도 승인.

## 6. 정기 실행·수동 실행·중앙 V 실측

| 대상 / 관측분 | run 번호 / ID | UTC 시작→종료 | 결과 |
| --- | --- | --- | --- |
| SEC 10/22분 | [#21 / 39879258841](https://github.com/kco994553-star/Investment-System1/actions/runs/39879258841) | 10-23 00:37→01:20 | 성공 1/7 |
| SEC 10/23분 | [#22 / 40045938631](https://github.com/kco994553-star/Investment-System1/actions/runs/40045938631) | 10-24 00:38→01:17 | 성공 2/7 |
| SEC 10/24분 | [#23 / 40146210895](https://github.com/kco994553-star/Investment-System1/actions/runs/40146210895) | 10-25 00:19→01:06 | 성공 3/7 |
| ALLSHARDS-1026 | [#24 / 40186520528](https://github.com/kco994553-star/Investment-System1/actions/runs/40186520528) | 10-25 10:52→12:03 | 성공(수동, 집계 밖) |
| SEC 10/25분 | [#25 / 40248709458](https://github.com/kco994553-star/Investment-System1/actions/runs/40248709458) | 10-26 00:18→00:56 | 성공 4/7 |
| SEC 10/26분 | [#26 / 40432704648](https://github.com/kco994553-star/Investment-System1/actions/runs/40432704648) | 10-27 01:27→02:13 | 성공 5/7 |
| SEC 10/27분 | [#27 / 40614210081](https://github.com/kco994553-star/Investment-System1/actions/runs/40614210081) | 10-28 01:18→02:02 | 성공 6/7 |
| SEC 10/28분 | [#28 / 40802503489](https://github.com/kco994553-star/Investment-System1/actions/runs/40802503489) | 10-29 01:47→02:28 | 성공 **7/7** |
| **중앙 V 첫 게시 all_shards** | [#29 / 40871484448](https://github.com/kco994553-star/Investment-System1/actions/runs/40871484448) | 10-29 12:13→13:31 | **성공**(수동, `d149c91d`). collect 39분(샤드 28.7·V 단계 6), verify 35분, deploy 1분. `attempt=OK published=NEW basis=2026-10-28 rows=523 ranked=356 supplied=357/357` |

## 7. 알려진 위험·관리자 노트

| 위험 | 영향·확인 |
| --- | --- |
| TARGET 확정 막힘 | #424 병합 전까지 `NUMBER_CHECK_CALC_VERSION_MISMATCH`(설계대로). 확정 창 11-09~11-15 |
| 규칙 변경 PR과 라이브 게시본 | 엔진·가중치·설정 버전을 바꾸는 PR이 병합되면 라이브 게시본이 새 검증기에서 무효가 되어 다음 성공 실행까지 빠진다(점검표 7절). 정기 실행 직후 병합 권장 |
| 독립 검토 비차단 메모 | ① 디스크가 일부만 찬 드문 경우 V 단계 임시 파일 잔존 가능 → 가드 거부 분기 `rm -f`에 `.qgv-official*` 추가 후보 ② 비밀값 `/proc` 노출은 같은 사용자 신뢰 프로세스만(강화 후보) ③ verify 35/60분 |
| telecom MIN_PEERS=8 경계 | 하나 빠지면 Q가 GENERAL `UNIVERSE_FALLBACK`. 매일 8 미만이면 즉시 보고 |
| PSKY 주식수 행 | `sec-universe-shares.json` PSKY 행(#409 설계상 보존)은 10-31 03:13 UTC에 STALE. TARGET 확정·원장·중앙 V 순위는 이 파일을 읽지 않음 |
| #417 calc_version 고정 | 연구 명세가 17.1·점수 원본 SHA를 고정 → canonical과 맞추면 설정 검사 실패. 연구 담당이 다시 고정 |

관리자 노트: 기능 구현 %·프론트엔드 %는 미산정. 문서·리뷰만으로 제품 진행률을 올리지 않는다.

## 8. 경계

- 모집단·V
  - Universe504 고정(DC-01). 확장 모집단은 별도 연구 모집단이다(DC-27).
  - 공식 V는 IEX HIST 서버 계산·공개(DC-02, 10-29 게시).
- 넣지 않는 것: 원시 가격·EV·배율·수익률·보유·Secret 값·키·토큰 값은 문서·로그·공개 산출물에 넣지 않는다. Secret은 이름(`QGV_OFFICIAL_HMAC_KEY`·`RAW_REPO_READ_TOKEN`)만 적는다.
- 지킬 것: NA를 0으로 채우지 않는다. 가격 요청은 버튼을 누를 때만 한다. Frozen·원장·SUPERSEDED·#412 이력은 보존한다.
- 임의로 바꾸지 않는 것: 계산·가중치·T-FRESH·공개 경계·보호규칙·AUTONOMY_MODE.
