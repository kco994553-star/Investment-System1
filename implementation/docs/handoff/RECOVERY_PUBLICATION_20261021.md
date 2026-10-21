# 10/20 수집 자료 복구·게시 증거

확인: 2026-10-21T08:51:13.485267+00:00 UTC / 2026-10-21T17:51:13.485267+09:00 KST.

**배포 성공 · 게시 138/138 파일 일치 · 고정 데이터 25/25 해시 일치.** 실사이트 PC·모바일/라이트·다크 조작도 236 assertions, 실패 0으로 확인했다.

- canonical/실제 게시: `ae34eb9035200fd47991dbb5878330ac4ca32db6`.
- [복구 run 39567157784](https://github.com/kco994553-star/Investment-System1/actions/runs/39567157784): 2026-10-21 08:09:27 UTC / 17:09:27 KST 시작, 08:49:17 UTC / 17:49:17 KST 성공 완료. [deploy job 119128557647](https://github.com/kco994553-star/Investment-System1/actions/runs/39567157784/job/119128557647)은 08:49:16 UTC / 17:49:16 KST 완료.
- [게시 사이트](https://kco994553-star.github.io/Investment-System1/). 배포 artifact `12332900631`, GitHub metadata ZIP digest `fb171b3a49596a51bde32d33e7dc4bf49b94425ad74047cb6825bb6b106c3876`(1,866,494 bytes). 이 digest는 metadata 값이며 로컬 ZIP 다운로드로 재계산했다고 주장하지 않는다. 실제 게시 내용은 아래 별도 138개 파일 바이트 비교로 확인했다.
- PR #371 최종 HEAD `9066c67eb15990013e0002fc9138dd0939a3941b`의 필수 6개 job 성공 후 최신 canonical `87bdc1c3`에 병합. 복구 실행의 전체 Python 3,622 PASS / 1 skipped / 298 subtests, 브라우저 단계 성공, 실제 macro evidence 10단계 PASS, 공개 가드138 PASS.

## 고정 원본·승인 범위

원본 run **39522288311**, artifact **12311543375**, commit `8c671ae4859bc509be228ec59b4d923f1bb2af43`만 사용했다. 복구 전용 source job의 저장소 `actions: read`만 추가했으며 일반 PR/build에는 추가하지 않았다. 권한 자체는 저장소 Actions 읽기이고, 특정 artifact 한정은 코드상의 제한이다. 다른 실행/산출물에 이 승인을 확장하지 않았다.

- ZIP SHA-256: `16a0af04725323edc624bc0ce503ab3700224c38d7df55cd604a9e42b22d0826`.
- TAR SHA-256: `e1ba05bf5ff43d5bf76e46a4525884e6a886b2c86e33f1b82f7e2f8cfc7b5912`.
- GitHub source job은 08:09:35 UTC / 17:09:35 KST에 실제 ZIP/TAR 검증을 통과했다. unprivileged build는 저장소·원본 실행 SHA·artifact metadata·만료·안전한 TAR 구조·고정 JSON 해시를 확인하고 25개 파일만 복원했다.
- 새 빌드 코드/manifest는 #370 수정이 포함된 ae34eb90 기준이다. 87bdc1c3 이후 ae34eb90의 변경은 workflow/helper/tests/docs이며 게시 소스/build 생성기에는 차이가 없다. 별도 새 코드 위 복구 후보와 실제 사이트 138개 전체를 바이트로 비교했다.
- 재수집·비공개 원장 쓰기·새 관측 추가 없음. 원본의 오래된 JS/HTML을 재게시하지 않았다. 로컬 새 ZIP GET의 이전 `Forbidden`을 우회하지 않았고, 승인된 GitHub job의 실제 성공과 구분했다.

## 배포 직전 최신 자료·원장 검사

기존 `checked-cockpit-pages` deploy 잠금 안에서 08:49:02 UTC / 17:49:02 KST에 freshness 검사 **10개 PASS**, refused=0, live_invalid=0, SEC rows_compared=1537/rows_regressed=0, records_compared=2/records_regressed=0을 확인했다. 이어 08:49:06 UTC / 17:49:06 KST에 최신 게시 **25개**가 감사한 기존본 또는 동일 고정 원본인지 다시 검사해 통과한 뒤 배포했다. 오래된 산출물로 더 최신 기록을 덮지 않았다.

| 버전 | 이전 게시 | 복구 게시 | 보존 | 누락/변경/순서 이동 | 날짜 |
| --- | ---: | ---: | ---: | --- | --- |
| forward_validation/v1 | 1 | 2 | 1 | 0 / 0 / 0 | 10/19, 10/20 각각 한 번 |
| forward_validation/v2 | 1 | 2 | 1 | 0 / 0 / 0 | 10/19, 10/20 각각 한 번 |
| forward_validation/v1+dcf_v1_default | 0 | 0 | 0 | 0 / 0 / 0 | 추가 없음 |

원장 전체 17,858 bytes, SHA-256 `1f355c259277f855d961ad4b7d653bf2ab61bc46c2ad423f8ab638fc2b4eeb72`는 원본 수집 산출물과 게시본이 같다. 비교 로그의 `appended=1`은 **이전 게시본 대비** 원본에 이미 있던 10/20 기록이 한 건 더 있다는 뜻이다. 복구 실행에서 만든 새 관측 수는 **0**이다. 원본 정기 실행은 RAW 사본 읽기와 같은 원장 hash의 private upload 성공 로그가 있지만, private 업로드 사본의 별도 재다운로드/다음 정기 실행 재사용은 아직 확인하지 않았다.

## 25개 데이터의 실제 게시 SHA-256

모든 행은 고정 원본 SHA와 실제 사이트에서 읽은 SHA가 동일하다.

| 파일 | 원본 = 실제 게시 SHA-256 |
| --- | --- |
| actual-catalog.json | `fb10ebc8506de85ac7b210ead9a47d0f7fe69c69e4ba86f17bc3b3eea3b93b49` |
| company-classification.json | `872f7fd78bf5dd735dfcfd2209a6b079f62ab21a34ad53212f58e87641d4a391` |
| company-logos.json | `656cd7a076923ce2498c97b6775b481045125214333d11002ffee79bbe26da5d` |
| company-names-ko.json | `74489ef7d67073a1cea3d60d019581e91f79df8164c2ed29cdb566072a301e4b` |
| company-types-pricefree.json | `52c4eb141c7614f47fc61fe328d8aa99743108be4be5c8b8ab383ce8b2649c5e` |
| dart-disclosures.json | `0d4ead442e3e04f90b94b7d81a64799bc394625f055c54bc9c697f90c94b87f4` |
| dart-financials.json | `b4e954fb350a8884260f92be8d58594704fe969f171f8aaa3afb2bb35d499809` |
| data.json | `c3365b11e217760e2f3a008aaf660baade4494f01b5a255be3cfb6405a451cf9` |
| entities.json | `b085478e6f45797bed32fd9204dc9e8f72c9a452f621a4d3338b99c89ccdc78f` |
| forward-validation-ledger.json | `1f355c259277f855d961ad4b7d653bf2ab61bc46c2ad423f8ab638fc2b4eeb72` |
| macro-evidence.json | `e9a3869d7f4996fc211fe5b230c9eb0ae3b16bb37d1c31d41589ca06ea5d3e51` |
| macro-screen.json | `e936c295ddc76cf7de68b8608ec174b24f5bbb19eb408b60d7e80cea506e5618` |
| news-signals.json | `ddebde7a2d5c0dcbcf5f12f8f40e97ed7a2476e4d04a81a71ea771271e3b61ae` |
| sec-13f-changes.json | `a698593a86db348e35a87d9399c2390057acb58e9ccbd3870e7e9263d65e4bdb` |
| sec-disclosures.json | `374124876829cdaa4d1a0f9b8c5bf5bd8e8fda7244005ac4589ab4a937b1dd67` |
| sec-filing-windows.json | `d5f7bb87e11df2d83fd1dbaa28c9f5d49bc2bd7d64b8198fa8a56bd43a336781` |
| sec-m2-candidates.json | `64108ed836970fbbe09e08624fbd92469ce49168d7d875530f156306ed32f649` |
| sec-public-inputs.json | `08a4753e0f5eac1c721370b4d306bc88b9ec37f5b9b75e5f1f0f0051ae8ea57f` |
| sec-qg-factors.json | `6102d99a0bb69a9ed580496e0a4e787cece5be2d6dd291d2fdcefe9cff12288f` |
| sec-qgv2.json | `322b3206d36df15305edf8bf459a715d02229822fcbef935c663c80e2b15a3bf` |
| sec-universe-qg.json | `2efc5007a07002aae4431f076406825c62ed88729d422e336800b73f48ba4b37` |
| sec-universe-shares.json | `65190b248eda82f129dcd76d6d69ebf337b232757834096185d85445e080df7b` |
| sec-valuation-inputs.json | `f1d6a305d84b0f7814f92ac23f85fe08e3dc674ca2346f397a7f5b78862a5d30` |
| universe-codes.json | `b4a06c40e702bfb376dc06973cffccb0ff636cd86935905a9cd7ce57f28bf45a` |
| universe-domains.json | `33cb0add559efe23ec8d75c3df8419016b2c635bb11ed1d7dc9b09529bac9562` |

## 수집 상태의 해석

배포 성공이 모든 수집 성공을 뜻하지 않는다. P1 매크로 13지표/14계열 중 10지표/11계열 LIVE, E14는 TERMS_UNVERIFIED, E21/E26은 SOURCE_KEY_NOT_CONFIGURED이고 세 지표에는 관측값이 없다. 기존 macro-v0 H15 HTTP404 및 H41/H8 빈 응답으로 해당 통화/유동성/신용은 NA다. XOM은 shares LIVE이지만 BASIS/COVER 미확인이고 QG는 NO_ANNUAL_SEC_FINANCIALS여서 완전 복구가 아니다. replay_events 137개는 현재 빈티지 근사 재구성이며 실제 당시 발표 이벤트가 아니다(events/releases=0).

합성 fixture·브라우저 조작 시험, 실제 10/20 수집 산출물의 바이트 확인, 운영 run/배포 로그를 구분했다. 공식 국면·확률·매크로 gate·가격 공급원 권리를 새로 승인하거나 활성화하지 않았다. #372 및 TARGET/#262 후속 준비 코드는 이 ae34eb90 게시에 포함되지 않는다.

## 실사이트 브라우저 검사

2026-10-21 08:54:35–08:57:26 UTC / 17:54:35–17:57:26 KST에 실제 게시 URL의 recovery 프로필로 390/1280 × light/dark, 236 assertions / 실패 0을 확인했다. 결과 28 PASS, 후속 #372 기능 12 NOT_EXPECTED. 검색→5카드→동일 기업 상세, 기존 메뉴, 공개 새로고침 UNCHANGED와 필터 보존, 승인된 자체 호스팅 글꼴 2개, 페이지 오류·외부/쓰기/redirect/WS 요청 0을 확인했다. 합성 기기 노트·시나리오의 생성/저장/복귀/reload/수정/삭제 및 개인 매크로 추정 추가/삭제·공식 이력 불변도 확인했다. 실제 투자 가격·개인 계정 없이 임시 컨텍스트에서 검사했고 합성 저장 항목을 삭제했다. 캡처 8장 실제 열람. APPLIED 새 자료 세대나 #372 새 기능, 모든 내부 표 가독성을 이 결과로 검증했다고 세지 않는다.

첫 실행은 앱 접속 전 직접 TCP ECONNREFUSED로 assertions=0이었다. 환경에 이미 설정된 프록시를 Chromium에 전달한 재실행이 성공했다. TLS 검증·네트워크 정책·요청 경계를 유지했으며 앱 소스나 단언을 바꾸지 않았다.

## 로컬 증거

- `recovery-live-all-assets-20261021.json`: UTC/KST·138개 파일의 기대/게시 SHA와 바이트.
- `recovery-operational-proof-20261021.json`: run/job/step 상태·최종 metadata·검사 로그 발췌(토큰 없음).
- `recovery-final-ci-9066c67e.json`: 병합 전 정확한 HEAD 6 job 성공.
- `investment-daily-20261020/replay-validation-87bdc1c3.json`: 고정 원본25해시·원장 날짜/prefix.
