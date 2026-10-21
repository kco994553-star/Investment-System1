# 현재 인수인계 — 2026-10-21 (Codex Main)

확인 시각: **2026-10-21 09:12 UTC / 18:12 KST**. 이 시점 이후 PR·Actions·게시 증거는 다시 확인한다. 구현 / 시험 / 병합 / 게시 / 실사이트 확인을 구분한다.

먼저 읽기: [WORKING_RULES.md](WORKING_RULES.md) → 이 파일 → [사용자 결정](implementation/docs/USER_DECISIONS_PENDING.md) → [기존 분담](implementation/docs/PARALLEL_LANES_20261020.md) → [제품 IA](implementation/docs/PRODUCT_IA_DIRECTIVE_20261018.md) → [자료 계약](implementation/docs/FRONTEND_DATA_CONTRACT.md) → 작업 영역 계약·시험. 이전 원문은 [10/20 기록](implementation/docs/handoff/HANDOFF_HISTORY_20261020.md)에 보존했다. 과거 “다음 실행/병합 대기”보다 아래 실제 증거를 따른다. 사용자 결정은 구현과 다르다는 이유로 폐기하지 않는다.

## 1. 기준·인수 범위

- 실제 기본·canonical: **claude/investment-system-top500-validation-alrugm**, HEAD **ae34eb9035200fd47991dbb5878330ac4ca32db6** (#371). #371의 최종 9066c67e 필수 6 CI 성공과 직전 canonical 87bdc1c3 일치를 확인하고 병합했다. #370 최종 HEAD e967cbd3의 필수 6 CI가 모두 성공했고, 병합 직전 base=8c671ae4와 원격 canonical 일치를 확인했다.
- **실제 게시: ae34eb9035200fd47991dbb5878330ac4ca32db6**. [복구 run 39567157784](https://github.com/kco994553-star/Investment-System1/actions/runs/39567157784)은 **2026-10-21 08:49:17 UTC / 17:49:17 KST 성공**. 사이트 138/138파일·고정 데이터25/25 SHA 일치. 이전 afb06868 게시 상태는 대체됐다. [25개 해시·원장·배포 직전 최신자료 검사·실사이트 증거](implementation/docs/handoff/RECOVERY_PUBLICATION_20261021.md).
- 실사이트 recovery 프로필: 390/1280 × light/dark **236 assertions / 실패0**, 28 PASS / 후속 #372 기능12 NOT_EXPECTED. 검색→5카드→동일기업상세·기존메뉴·새로고침 UNCHANGED/필터보존·승인폰트2개 확인. 합성 기기 노트/시나리오 저장·복귀·reload·수정·삭제와 개인추정 추가/삭제·공식이력 불변 확인. 실가격·#372 새 기능 통과로 확대하지 않는다.
- 원격 400개 브랜치 이름·SHA 전수 대조. 기술 #350/#354/#355/#357/#359, 매크로 #351/#352/#353/#356/#358은 병합되어 게시 커밋에 포함된다. 별도의 후속 기술·매크로 배치 브랜치는 발견하지 못했다. Claude 미푸시 작업이 없다는 뜻은 아니다.
- 새 checkout이며 Claude worktree·미커밋 변경·예약 작업이 이전됐다고 가정하지 않는다. AGENTS.md와 사용자 기능 계층 원본 Investment_System_Function_Hierarchy_v1.0.md는 저장소에서 발견하지 못했다.
- Git clone·조회·수정·시험·실제 push 성공. #370 작업 브랜치의 로컬·원격 HEAD e967cbd3 일치를 확인했다. GitHub API 커밋 게시 경로는 사용하지 않았다.
- 시안은 [Drive의 6쪽 원본](https://drive.google.com/file/d/1T5ErGHdFPKDO2-Q9aF5pGtKcxCTzChVW/view)을 전 페이지 이미지로 렌더링·열람했다. **요청한 18쪽 (1).pdf는 미확보**. 새 배치 중 시안이 필요한 부분만 보류한다. 18쪽 PC·모바일 전체 대조 완료가 아니다. 제공된 ChatGPT library share의 공개 GET은 2026-10-21 08:40 UTC / 17:40 KST HTTP403 Forbidden이었고 다른 인증/경로로 우회하지 않았다.
- 추가 인수 자료: 18쪽 PDF 링크, 마지막 기술/매크로 작업자의 브랜치·기준 SHA·HEAD·git status --short·미푸시 diff. 사용자는 “진행”이라 답했지만 이 자료는 아직 제공되지 않았다.

## 2. 10/20 관측일 운영 결과

[정기 run 39522288311](https://github.com/kco994553-star/Investment-System1/actions/runs/39522288311), SHA 8c671ae4: **collect 성공 / verify 실패 / deploy 건너뜀**. 실제 시작 **2026-10-21 00:36:01 UTC / 09:36:01 KST**. 과거 “오늘 밤”은 이미 끝났다.

- 실패는 macro_evidence_browser_test.js가 실제 수집 파일에서도 미수집 배너를 기다리는 EMPTY 390 timeout. 동일 기준 코드의 빈 fixture는 통과하고 수집 파일에서는 실패하는 것을 재현했다.
- 원장 비공개 사본 읽기: source=RAW, raw=FOUND, recovered_records=0. v1/v2 각각 **10/19 보존 + 10/20 정확히 한 번 추가**, 각각 총 2개. 기록 시각 **2026-10-21 00:48:06 UTC / 09:48:06 KST**. 버전별 한 건을 중복으로 세지 않는다.
- 비공개 업로드 성공 로그: forward-ledger-2026-10-20, 17,858 bytes, SHA-256 **1f355c259277f855d961ad4b7d653bf2ab61bc46c2ad423f8ab638fc2b4eeb72**. artifact 원장과 일치·append-only 검사 통과. 업로드 사본 재다운로드와 배포 실패 다음 날의 실제 복구는 아직 확인하지 않았다.
- 현재 게시 원장은 복구로 10/19+10/20을 포함하며 원본과 같은 1f355c25… 해시다. 복구 생성 관측0, 재수집0. 정기 실행 두 번째 연속 성공 또는 다음 날 private RAW 재사용은 아직 확인하지 않았다.
- Q 486/504, G 494/504, 양쪽 478/504. 502 LIVE / 2 NA, 샤드 2/7의 77개 수집·전체 7/7 샤드. 기존 SEC 행 1,537개 보존. 데이터 JSON 25개 중 18개 변경·7개 동일.
- **XOM 완전 복구 아님**: 발행주식 LIVE이나 COVER_UNCONFIRMED/BASIS_UNCONFIRMED. QG는 NO_ANNUAL_SEC_FINANCIALS로 NOT_AVAILABLE.
- 매크로 P1 13지표/14계열 중 **10지표/11계열 LIVE**. E14 TERMS_UNVERIFIED, E21·E26 SOURCE_KEY_NOT_CONFIGURED이며 관측값 없음. SOURCE/PARSE 실패는 없고 이전 파일은 빈 초기 상태였다. 실패 후 이전 성공 관측 보존의 운영 사례는 아니다.
- 기존 macro-v0는 별도: H15 HTTP 404, H41/H8 빈 응답으로 통화·유동성·신용 NA. FX는 공개 제외. P1 성공을 전체 매크로 성공으로 부르지 않는다.
- events=0, releases=0, replay_events=137. 재생 사건은 현재 빈티지의 과거 재구성이며 당시 실시간 기록이 아니다. 공식 국면·확률·매크로 gate는 활성화하지 않았다.

공개 원본 artifact **12311543375**, github-pages 138파일. ZIP SHA-256 **16a0af04725323edc624bc0ce503ab3700224c38d7df55cd604a9e42b22d0826**, tar SHA-256 **e1ba05bf5ff43d5bf76e46a4525884e6a886b2c86e33f1b82f7e2f8cfc7b5912**. 만료 **2026-10-22 00:50:43 UTC / 09:50:43 KST**. Main 환경에 원본·추출본·출처 기록 보관. 재수집 없음.

## 3. 현재 구현·검증·병렬 담당

| 담당 | 소유 범위 | 상태·의존성 |
| --- | --- | --- |
| Main | codex/frontend-links-20261021; app/style/guard/CI/handoff 통합 | #372 f013440d 필수5 CI 성공, cockpit 노트 문구2검사 실패. 모바일 QGV 기존3열 줄바꿈 보완16캡처/독립리뷰/필터60/정렬564 PASS. 노트 문구44 PASS/독립 APPROVE. UI로고 보존 보완114 PASS·실제25해시보존. 최종HEAD6CI·병합·게시 잔여 |
| Darwin | 별도 worktree의 chart_user_objects_browser_test.js만 | 승인 저장문구 변경과 기존 시험 비교 완료, red42/2·기준44·green44 PASS. app/style 수정 없음. 로컬9영역49캡처 실제 시각감사 완료 |
| Kierkegaard | recovery/최종 실사이트 브라우저 검사 | recovery236 assertions PASS. #262 가설 통합/리뷰 완료. 최종 frontend 실제배포 신호 대기 |
| Lovelace | TARGET·공용 변경 독립 리뷰 | #248 원본ancestry/15파일 PASS, #263/공용app APPROVE. 좁은 모바일 CSS 독립 APPROVE |

기존 PR 재사용 준비 브랜치는 모두 원격에 보존·로컬/원격 SHA 동일 확인했다. 원본 PR 브랜치 자체는 아직 갱신 전이다.

- #248: 원본 claude/target-v1-builder 8c6990e2 → codex/target248-sync-20261021 **e1248fd1**, f013 포함·원본 ancestry/owned11파일 유지·총15파일, build136 PASS. 중간 배포 금지.
- #263: 원본 claude/target-v1-followups 194148f5 → codex/target263-sync-20261021 **48b91213**, #248+f013 포함. 실제 통합 build141·TARGET390/1280·build/config/font12 PASS. 최종 재조회/coverage/안전/같은calc/실제사용자응답 조건 유지, number_check.result null/false/null/0.
- #262: 원본 claude/macro-rule-c-clean b7db9b60 → codex/macro262-sync-20261021 **5ad6d000**, #263+f013 포함. Python44/Node302/화면64·최종 통합macro6 PASS. C는 HYPOTHESIS/UNCALIBRATED, gate_active=false/automatic=false, report/owner승인 요구 유지.
- 실제 #372 canonical 병합 커밋에 다시 동기화한 뒤 **#248→#263→#262 각각 최종HEAD 필수6체크 후 순차 병합**한다. 원본 PR 재사용, force push 없음. 준비 단계 성공을 최종 HEAD CI로 세지 않는다.

Main #370 검증: macro 브라우저 390/1280 **10단계 통과**(초기 읽기·빈 상태·실제 제공 artifact·합성 새로고침·상세). 실제 10/20 artifact에 수정된 두 JS만 적용해 확인했다. 리뷰 지적 초기 읽기 경합·404·필수 labels/summary/관측 누락을 회귀에 추가했고 수정 전 실패를 확인했다. 최종 공통 새로고침 **159 checks**, 화면 보존 **20 screens**, 실제 artifact 경계 가드 **138파일** 통과. 관련 Python **73 passed/150 subtests**는 JS 리뷰 보완 전 실행 결과이며 Python 코드는 변경하지 않았다. 최종 HEAD e967cbd3의 원격 필수 **6/6 CI 성공**: cockpit-pages 39555638059, web-mvp-validation 39555637884, autonomy-gate-a 39555637886, web-research-guard 39555638018, web-state-presentation 39555637868, c21-real-data 39555637896. #370 병합·복구 배포 완료. 수집기·공식 계산·저장 정책·공개 범위는 변경하지 않는다.

기존 수동 화면 배포는 **현재 게시 데이터**를 보존하므로 10/20 미게시 데이터를 복구하지 않는다. 실패 run 재실행은 원래 SHA의 시험을 쓰므로 해결책이 아니다. [10/21 복구 승인](implementation/docs/USER_DECISIONS_PENDING.md)을 적용한다. 권한은 이 저장소 Actions 읽기이며 artifact 제한은 코드상의 제한이다. 기존 deploy 잠금·SEC/원장 freshness·공개 경계 가드·전체 검증을 유지하고, 최종 배포 직전에 25개 게시 파일이 감사한 기존본 또는 고정 원본인지 비교한다. 알려지지 않은 새 데이터·404·망 오류이면 중단한다. 복구 후보 25개는 모두 고정 원본 해시여야 한다. 재수집·원장 추가 없음.

복구 로컬 검증: 실제 ZIP/TAR 해시·25/25 JSON 바이트 일치, 새 코드/manifest 113개 불변, 공개 가드 138파일 PASS. 기존 게시본 대비 원장 v1/v2 각각 10/19 보존·원본 10/20 1건, 누락/변경/이동 0. 복구 전용 시험 130 PASS(실제 다운로드와 구분); 기존 workflow 경계 5개와 최종 freshness 형태 2개를 합쳐 **137 PASS**. #371 첫 CI의 5개 workflow는 같은 `test_affected_workflows_have_no_publication_sinks`의 업로드 수 1개 가정 때문에 실패했다. 승인된 복구 전용 upload의 job·조건·정확한 3경로를 검사하며 기존 Pages upload 앞의 공개 가드·브라우저 검사는 유지하도록 수정했다. 이어 기존 freshness 시험이 마지막 직전 단계만 가정해 실패했다. 기존 무조건 SEC/원장 검사와 추가 복구 전용 25파일 검사가 모두 deploy 잠금 안에서 배포보다 앞서는 정확한 구조를 검사하도록 정정했다. 독립 리뷰 통과. 최종 9066c67e의 필수 6개 job이 모두 성공: build 39563380368, guard 39563380409, repository-guard 39563380427, ingest-and-gate 39563380389, presentation 39563380373, validate 39563380383. #371은 ae34eb90으로 병합했다.

전송 확인의 제한: 로컬 `gh` ZIP GET은 `Forbidden`/exit 1/0 bytes로 실패했고 다른 경로로 우회하지 않았다. 같은 principal의 artifact metadata는 200이지만 ZIP 거부가 API 권한 또는 전송 계층인지 미분류이며 실제 scope를 단정하지 않는다. 앞서 보관한 공식 ZIP의 정확한 바이트 검증과 GitHub 복구 job의 실제 전송 성공은 별개다. 승인된 GitHub 복구 run 39567157784(HEAD ae34eb90)은 2026-10-21 08:09:27 UTC / 17:09:27 KST에 시작했다. source job 119112084667은 성공했고 08:09:35 UTC / 17:09:35 KST에 ZIP_VERIFIED를 기록했다. build/복구/최종 검사/배포가 모두 성공했다. 전체 Python 3622 PASS/1 skipped/298 subtests, 공개가드138 PASS. 배포 직전 SEC1537행 후퇴0·기존원장2기록 누락/변경/이동0, 고정25파일 최신 게시 재비교 PASS. 실사이트도 위 별도 프로필로 통과했다. 최신 게시 25파일의 production CLI는 한 차례 읽기 실패 후 코드 변경 없이 재확인해 exit 0으로 통과했다. 복구 dispatch 직전에도 최신 게시 25파일 검사 PASS, in_progress/queued 실행 0을 확인했다. 배포 시 잠금 안의 검사 자체가 다시 성공해야 한다.

프런트엔드 연결 검증: navigation 40 PASS(light/dark × 390/1280), private-history 60 PASS, IA 1530 checks·16개 빈 기기 캡처 PASS, macro 10단계 PASS. 마지막 같은 기업 2.1 복귀 유지 보완은 navigation 40 및 독립 6개 lifecycle 확인에 포함한다. 실제 10/20 공개 파일 위의 자산 가드 138파일 PASS. 합성 봉으로 RAM 보존을 확인했으며 실가격/기업행사 검증 완료가 아니다. 기존 다른 기업·화면 이탈·로그아웃 정리 동작 유지. PC 라이트/모바일 다크 캡처를 실제 열람했지만 18쪽 PDF 전체 대조는 미완료다. 필수 CI 최종 HEAD와 배포는 별도로 확인한다.

추가 #372 통합 검증: QGV 표시 필터 Node 24 PASS(전체 Universe/공식 모델 불변 포함), 실제 통합 브라우저 60 PASS. 검색 복귀·홈 갱신 12시나리오/120단언 PASS 및 독립 리뷰 70단언 PASS. 선택 기업 프롬프트 projection 15·통합 브라우저 152단언/4폭·언어 조합 PASS, 관련 Python 41 PASS. 새 정확한 자산 해시를 고정했고 고정 10/20 데이터 위 공개 가드 138파일 PASS. G6 최종 실제 통합 build에서도 3/3·48 snapshots·564 checks PASS, guard138 PASS. 원격 cb593bbd의 font fixture 실패는 원인/최종 집중 검사/독립 재리뷰를 상세 기록했다. 실가격 검증이나 실사이트 실행을 뜻하지 않는다. [상세 통합 기록](implementation/docs/handoff/FRONTEND_WIRING_20261021.md).

## 4. 기능 1.1 계층별 상태

기능 번호는 기존 handoff/PR을 따른다. **기능 1 기업검색 ↔ 메뉴 0, 2 QGV ↔ 메뉴 1, 3 기술 ↔ 메뉴 2, 4 매크로 ↔ 메뉴 3, 5 뉴스 ↔ 메뉴 4, 6 포트폴리오 ↔ 메뉴 5, 7 프롬프트 ↔ 메뉴 6, 8 트리 ↔ 메뉴 n, 9 Lab ↔ 메뉴 n+1**. 18쪽 PDF 페이지 대응은 미확인이다. 원본 없는 하위 번호를 새로 확정하지 않는다. 기존 CI 기록을 이번 재실행으로 표시하지 않는다.

| 기능 | 구현 / 시험 | 병합 | 게시 | 실사이트 확인·잔여 |
| --- | --- | --- | --- | --- |
| 1.1 기업검색 | 기존5요약·상세 + #372 연속성 시험 완료 | #362; #372 대기 | 기존 ae34 | 기존검색 PASS; 확장기능 미게시 |
| 2.1 리더보드 | Universe504·공식/QG참고/개인 분리; #372 표시필터·단일정렬 시험 완료 | #364; #372 대기 | 기존 ae34 | 기존메뉴 PASS; 모바일 표 보완 중 |
| 2.2 가중치 | 2단계·개인 프로필 / 기존CI | #300 | ae34 | 공식과 개인 분리; 미승인 수치 생성 금지 |
| 2.3 13F 연구 | 공개 과거보유 조회 / 기존CI | 기존 | ae34 | 가중치 학습·채택 미구현; 기관 실제공식 아님 |
| 2.4 상세·레이더 | 가치·비교·후보3축/NA / 기존CI | #311/#344/#364 | ae34 | 실제가격·권리 경계 유지 |
| 2.5 QGV 트리 | 기존 설명·경로 | 기존 | ae34 | 18쪽 시안 미확보 |
| 3.1 차트·시나리오 | 기존 + #372 기업ID/RAM 유지 / 합성시험 | #354/#359; #372 대기 | 기존 ae34 | 합성저장·reload PASS, 실제연속성 미확인 |
| 3.2 패턴 | 감지·이력·설정 / 합성시험 | #355/#357 | ae34 | 노트/공식이력 분리 PASS; 실가격검증 아님 |
| 3.3 노트 | 저장·편집·삭제·교환 / 기존CI | #359/#363 | ae34 | 실사이트 합성생성/수정/삭제/reload PASS; 계정동기화 아님 |
| 4.1 국면·근거 | P1수집/링·#370 수정 / 최종6CI | #351/#352/#353/#356/#370 | ae34+10/20자료 | 국면·확률 미산출; 새로고침 UNCHANGED PASS |
| 4.2~4.6 기존매크로 | 산업·개인·트리; #372 연결 / 로컬시험 | #358/#363; #372 대기 | 기존 ae34 | 개인추정 추가/삭제/reload PASS; C가설 #262 준비 |
| 5.1 관계망 | 틀·검색안내 / 기존CI | #367 | ae34 | 생산자 미연결, 임의관계 없음 |
| 5.2 공시·뉴스 | SEC/DART·schema2/필터 / 기존CI | #346/#367 | ae34 | NEWS LIVE/필터보존 PASS, 영향·가격반영 미산출 |
| 6.1 포트폴리오 | 모델/실제/모의 분리; TARGET 준비 | #366; #248/#263 대기 | 기존 ae34 | 기존메뉴 PASS; TARGET 확정 미실행 |
| 6.2~6.3 보고 | 일일·누락입력·실행프롬프트·답변검토 | 기존/#366 | ae34 | 주간집계 미결 |
| 7.1 프롬프트 | 라이브러리·개인복사본; #372 기업가져오기 시험 완료 | #368; #372 대기 | 기존 ae34 | 기간의미 미정→수동, 자동공식적용 없음 |
| 8 구조트리 | 기존전체연결 / 로컬시각 확인 | 기존 | ae34 | 18쪽·원본없는 하위번호 미확인 |
| 9.1 백테스트 | 화면·설명·연구어댑터 | #368 | ae34 | 운영 실험등록/결과 미구현 |
| 9.2 전진검증 | 가격없는 원장·기기계산 / 운영보존 확인 | 기존/#368 | 10/19+10/20 ae34 | v1/v2 날짜각1건·hash일치; 실제이후성과 별도 |

최종 준비본 9영역 PC1440/모바일390 라이트 및 QGV/매크로 다크49캡처 실제열람. 확보6쪽과 비교 가능한 부분만 대조했다. 모바일 QGV 초기 숨는 점수열은 기존3열 줄바꿈으로 보완해4폭/2테마·독립리뷰를 통과했다. Lab 넓은 원장표는 내부 가로스크롤 가능하지만 날짜/지표 동시읽기 제약이 남는다. 전체 시안 일치나 모든 개인입력 상태 검증은 아니다.

## 5. 열린 PR·승인 경계

인수 시 열린 PR 7개: **#361, #305(draft), #281(draft), #267, #263, #262, #248**, 할당자 없음. 작성 계정이 같아도 Claude 로컬 작업 소유권을 넘겨받았다고 단정하지 않는다.

- **#248→#263**: 최신 결정상 구현 통합 승인. 최신 canonical 동기화·필수 검사 후 순서대로 통합 대상. TARGET 확정은 같은 calc_version 숫자 검증·coverage·실제 사용자 응답 등 별도 조건 유지.
- **#262**: 규칙 C는 승인된 가설. 재생·동기화 잔여. M-REENABLE은 기존 조건 및 별도 승인 필요, 참고 모드 유지.
- **#361**: Yahoo 권리 미해결로 Worker 배포 명시적 보류. 분할 블록 누락은 미확인이고 확인된 빈 배열과 다름. #365 공급원 비교는 병합된 문서.
- #305/#281 이전 디자인은 후속 방향으로 대체되어 참고용 보존. #267 합성 스튜디오 명시적 보류. claude/fe-doodle-map 통째 병합 금지.
- #369/#365/#362/#364/#366/#367/#368/#363/#360은 이미 병합. **#366/#367/#368/#363/#360은 현재 ae34 게시에 모두 포함**된다.
- 공통 V 공급원·금융 V·경기 모델·공식 매크로 gate 등 미승인 방법론을 연구 결과만으로 활성화하지 않는다. D1/D2/D3-A·기존 승인 구현은 재승인 없이 진행한다.

## 6. 다음 실행·예약·보존

다음 할 일은 순서대로 (1) 완료된 복구 증거 보존, (2) #372 노트 안내문 시험 실패 원인 확인과 모바일 QGV 줄바꿈 보완·최신 canonical 동기화·최종 6 CI·병합, (3) 기존 #248→#263 최신 canonical 동기화·각 6 CI·순차 병합(중간 확정 화면 배포 금지), (4) 기존 #262 가설 동기화·최종 6 CI·참고 모드 유지, (5) 최종 화면 배포에서 최신 데이터/원장 보존·실사이트 확인, (6) 18쪽 시안·미푸시 작업 확보 후 남은 배치 대조다. CI 대기 중에는 독립적인 승인 작업을 계속한다.

- 정기 cron 22:17 UTC / 다음 날 07:17 KST. 점검 기준 23:15 UTC / 다음 날 08:15 KST, 지연 점검 다음 날 00:17 UTC / 09:17 KST. 10/20 실행은 2시간19분 지연됐으므로 과거 “보통 15~20분”을 보장으로 쓰지 않는다.
- **새 예약을 만들지 않았다.** 확인 가능한 자동화 목록에서 기존 Claude 결과/지연 점검의 계속 실행 증거를 찾지 못했다. Claude 세션 예약 상태 미확인. 현재 가능한 작업을 예약 시각까지 미루지 않는다.
- 다음 dispatch 직전 진행·대기 실행과 최신 게시 확인. 확인을 위한 504 재수집·추가 원장 관측 금지. 다음 정상 실행의 RAW_FIRST 복구와 HONA 샤드 3 결과는 운영 증거로 별도 확인.
- 정기 workflow 동시 실행 방지와 두 Pages deploy의 checked-cockpit-pages 잠금·최종 freshness 검사 유지. 수동 화면 배포의 데이터 보존과 정기 수집의 정상 데이터 변경 구분.
- 사용자 시나리오·노트의 직접 입력 좌표만 승인된 브라우저 저장 대상. 공급자 가격·파생값·개인 보유/거래·시트 ID·토큰을 저장소/Pages/Actions 로그에 넣지 않는다. NA를 0/평균으로 채우지 않는다. Frozen/history/PIT/no-lookahead/provenance 유지.
- 글꼴 예외는 승인된 두 파일의 정확한 경로·서명·크기·해시뿐. 가드 범위/파일 수 상한 확대 금지. 권한 거부 우회 금지, 원문 이유와 영향 보고.
- 다른 작업자의 worktree·scratchpad·원자료를 삭제하지 않는다. 정리 전 소유자·병합·미커밋·재현 가능성 확인.

일반 UI 배포의 로고만 재수집하던 경로를 --preserve-only로 보완했다. 로고/보존/공개경계114 PASS와 실제 게시25파일 바이트 동일·원장2건보존·가드138 PASS 확인. 정기 로고 수집과 권한은 유지한다. 노트 안내문 시험도 독립 APPROVE를 받았다. 최종 PR HEAD 변경 후 필수6CI를 새로 확인한다.
