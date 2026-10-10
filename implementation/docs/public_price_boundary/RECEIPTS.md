# GSQ-010 메타데이터 receipt

사용자 결정 [GSQ-010](../pages_cockpit_owner/GOOGLE_SHEET_QUOTES_DECISION_REGISTER.md)에 따른 **문서 PR / 병합 대기** 기록이다. 기준 canonical은 `a8b275e6f509838b3edd516c2d0dfdde6c50ae14`이며 #92 병합 직후다. 가격 원자료·가격 기반 파생값·토큰·Secret 값·원문 발췌는 이 receipt에 복사하지 않는다. 해시는 값을 제거하기 전 원본을 식별하는 메타데이터이며 원본 보존 또는 공개 재배포 허가가 아니다.

기존 Markdown 7개의 실제 가격·가격 파생값 재인용은 이 PR에서 지정 문구로 대체한다. 아래 source hash/bytes는 값 제거 전 기준 파일, 정리본 hash/bytes는 이 PR의 제안 파일을 가리킨다. 기준 파일은 감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 #92 병합 후 동일 bytes임을 확인했다. 기준일은 시장 자료의 기준일 또는 문서에 명시된 날짜이며 실제 조회 성공이나 자료 정확성을 재인증하지 않는다.

Frozen 3개의 receipt는 코덱1 후속 정리에 사용할 **메타데이터 준비**다. 이 문서 PR에서 Frozen JSON 값의 삭제·교체·이동은 실행하지 않는다. 원본의 사용자 개인 저장소 보관도 사용자가 별도로 처리하며 이번 작업에서 복사·업로드하지 않았다.

**과거 Git 이력·기존 Pages/Actions 사본은 재작성하지 않는다.** 사용자가 GSQ-010에서 잔여 노출을 수용했으며 force push 금지는 유지한다. 아래 원본 hash가 식별하는 값은 이전 공개 커밋 등에 남을 수 있고, 새 HEAD의 문구 대체가 이전 사본의 소거를 의미하지 않는다.

## 문서 정리 receipt 목록

| receipt | 문서 경로 | 원본 bytes | 정리본 bytes | 제거 값 개수 |
| --- | --- | ---: | ---: | ---: |
| [doc-01](#doc-01) | [Investment-System1 · Artifact Evidence Register 2026-09-23.md](../../../Investment-System1%20%C2%B7%20Artifact%20Evidence%20Register%202026-09-23.md) | 20,536 | 21,102 | 17 |
| [doc-02](#doc-02) | [Investment-System1 · Contract Conflict Register 2026-09-23.md](../../../Investment-System1%20%C2%B7%20Contract%20Conflict%20Register%202026-09-23.md) | 46,078 | 46,438 | 8 |
| [doc-03](#doc-03) | [Investment-System1 · HANDOFF_HISTORY.md](../../../Investment-System1%20%C2%B7%20HANDOFF_HISTORY.md) | 142,566 | 143,999 | 44 |
| [doc-04](#doc-04) | [Investment-System1 · TRACK_A_REAL_DATA_STATUS.md](../../../Investment-System1%20%C2%B7%20TRACK_A_REAL_DATA_STATUS.md) | 3,576 | 3,835 | 5 |
| [doc-05](#doc-05) | [implementation/CHANGELOG.md](../../CHANGELOG.md) | 42,420 | 42,738 | 7 |
| [doc-06](#doc-06) | [implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md](../../reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md) | 7,148 | 7,352 | 4 |
| [doc-07](#doc-07) | [implementation/experiments/chart-contract-v0.1/p0-prerequisites/contract/CHARTDOCUMENT_V01_ADEQUACY_AND_V02_PROPOSAL.md](../../experiments/chart-contract-v0.1/p0-prerequisites/contract/CHARTDOCUMENT_V01_ADEQUACY_AND_V02_PROPOSAL.md) | 26,896 | 27,244 | 8 |

합계: **7문서 / 93개 값 / 60개 원본 줄**. 비가격 주식수·기준일·판정·출처·해시와 명시된 합성 probe는 보존했다. src·tests·tools·web_assets, 실자료 JSON·HTML·gzip, workflow와 운영 설정은 변경하지 않았다.

## doc-01

- 경로: `Investment-System1 · Artifact Evidence Register 2026-09-23.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `4e26469af2d77215e394f82c6ab3b03f6e2895e3`
- 원본 SHA-256: `6cb1289a4b524fe82ac2656548ae41a520674e1997034ca0bb5f2f9a07a075a7`
- 원본 크기: **20,536 bytes**.
- 기존 출처 표시: Yahoo Finance / Yahoo chart / SEC NPORT / SEC.
- 기존 문서에 표시된 날짜: 2021-10-06 / 2021-10-18 / 2024-06-30 / 2024-09-30 / 2024-12-31 / 2025-01-01 / 2026-09-23 / 2026-09-24 / 2026-09-25 / 2026-09-26 / 2026-09-27 / 2026-09-28.
- 제거 범위(원본 줄): 129, 145, 147–148, 162–163, 171–173, 178, 185–186.
- 제거 종류·개수: actual_market_price_or_value 10개, actual_issuer_rank 5개, actual_outcome_return 2개.
- 정리본 크기: **21,102 bytes**.
- 정리본 Git blob SHA-1: `884b1447a9607a13dcf9bde5376f7ec102bcbd49`
- 정리본 SHA-256: `e2736129fd89a820cc874ac0596ae21227171b018e11fef85dd503d57c6296d7`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-02

- 경로: `Investment-System1 · Contract Conflict Register 2026-09-23.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `506694f867d451ffaca4f37e858715a9cac9b60d`
- 원본 SHA-256: `8e1da679a1d1a1a663e69f9a7e51ca99a2bb9d2c3df8d5d498d627b847f1a5ec`
- 원본 크기: **46,078 bytes**.
- 기존 출처 표시: Yahoo Finance / Yahoo chart / SEC NPORT / SEC / Tiingo / Stooq.
- 기존 문서에 표시된 날짜: 2021-10-06 / 2021-10-18 / 2024-06-03 / 2024-06-13 / 2024-06-24 / 2024-06-28 / 2024-06-30 / 2024-07-05 / 2024-08-13 / 2024-08-26 / 2024-09-30 / 2024-12-23 / 2024-12-31 / 2026-09-22 / 2026-09-23 / 2026-09-24 / 2026-09-25 / 2026-09-26 / 2026-09-27 / 2026-10-08.
- 제거 범위(원본 줄): 399, 439, 443, 448, 467.
- 제거 종류·개수: nport_market_value 1개, nport_implied_price 1개, actual_market_price_or_value 4개, actual_issuer_rank 2개.
- 정리본 크기: **46,438 bytes**.
- 정리본 Git blob SHA-1: `ed6f43aca75f3618dbfde5c0ba520cb069dffdad`
- 정리본 SHA-256: `e894d64a3d477619c45bb5f20e4d2b6200a92c03765aac41b836ec9a3584f56d`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-03

- 경로: `Investment-System1 · HANDOFF_HISTORY.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `488b1eeae7581051315511fd95a63e9b651d830c`
- 원본 SHA-256: `9f1038af4be69e465c719061690aa57f01d6f4aee918b7f8aa96bc4a02668d03`
- 원본 크기: **142,566 bytes**.
- 기존 출처 표시: Yahoo historical bars/chart / Tiingo historical price fallback / SEC NPORT holding valuations.
- 기존 문서에 표시된 날짜: 2024-06-24 / 2024-06-30 / 2024-09-27 / 2024-09-30 / 2024-11-13 / 2024-12-23 / 2024-12-31 / 2025-01-01 / 2025-03-05 / 2026-09-22 / 2026-09-23 / 2026-09-24 / 2026-09-25 / 2026-09-26 / 2026-09-27 / 2026-12-24.
- 제거 범위(원본 줄): 257, 1294, 1328, 1331, 1333, 1347–1348, 1387, 1409, 1414, 1434, 1444, 1480, 1491, 1503–1504, 1513, 1527, 1604–1606, 1610, 1612, 1620–1621, 1626–1628, 1630.
- 제거 종류·개수: market_cap 26개, market_value 2개, price 1개, price_adjustment_ratio 1개, realized_return 3개, market_cap_rank 11개.
- 정리본 크기: **143,999 bytes**.
- 정리본 Git blob SHA-1: `23d25a478a2f1c387a032ab126786d57586b8943`
- 정리본 SHA-256: `896672f82aff9d8e88ee0ca1ccd1bdc2b482e9080bdc2b214c03dd494693276c`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-04

- 경로: `Investment-System1 · TRACK_A_REAL_DATA_STATUS.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `14ffa5e6f3b65be0f42aaa73a7a5d94195742c52`
- 원본 SHA-256: `7dd2c7767fc4baaeca4f0da16097708a411345a58d990b61ea92c600f21893ee`
- 원본 크기: **3,576 bytes**.
- 기존 출처 표시: SEC NPORT / SEC.
- 기존 문서에 표시된 날짜: 2026-09-27.
- 제거 범위(원본 줄): 22, 24.
- 제거 종류·개수: actual_outcome_return 3개, actual_return_delta 2개.
- 정리본 크기: **3,835 bytes**.
- 정리본 Git blob SHA-1: `fb83923451cfd98282682303df62891ccb0816d5`
- 정리본 SHA-256: `2072ad58aa4474a1f3630193e42b8165c9e111a3978a48b56952b53cb91ea088`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-05

- 경로: `implementation/CHANGELOG.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `6294e0c2123533ca4a656a2baa594e3f8dc324b9`
- 원본 SHA-256: `944545a84bbf21526ccd5b91ff280fb89b9adff7d01ea608797c8d7ba9b5653e`
- 원본 크기: **42,420 bytes**.
- 기존 출처 표시: Yahoo Finance / Yahoo chart / SEC NPORT / SEC / Tiingo / Stooq.
- 기존 문서에 표시된 날짜: 2024-06-30 / 2024-09-30 / 2024-12-23 / 2024-12-31 / 2025-01-01 / 2026-09-14 / 2026-09-23 / 2026-09-24 / 2026-09-25 / 2026-09-26 / 2026-09-27 / 2026-09-28.
- 제거 범위(원본 줄): 583, 590, 598, 607, 618, 624.
- 제거 종류·개수: actual_market_price_or_value 5개, actual_issuer_rank 2개.
- 정리본 크기: **42,738 bytes**.
- 정리본 Git blob SHA-1: `baf4c71b5b14ee01f133a4c5d09a93d7169802f3`
- 정리본 SHA-256: `48dc4c6665862f9ecc659335339d789e9201008422d8893b835b5a40aef4c9f4`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-06

- 경로: `implementation/reports/gate_evidence/track_a_share_unit_policy_proposal_2026-09-27.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `3c0bf586d4b81afc7c392f943a47f484df336034`
- 원본 SHA-256: `6ef4755b2dcfb8cb76c5f942499f3cef2647d8fd18d688d6887aa726017e6d7d`
- 원본 크기: **7,148 bytes**.
- 기존 출처 표시: Yahoo Finance / Yahoo chart / SEC NPORT / SEC.
- 기존 문서에 표시된 날짜: 2024-05-22 / 2024-05-29 / 2024-06-10 / 2024-06-24 / 2024-06-28 / 2024-06-30 / 2024-09-10 / 2024-09-30 / 2024-12-31 / 2026-09-27.
- 제거 범위(원본 줄): 11, 38.
- 제거 종류·개수: actual_market_price_or_value 3개, actual_issuer_rank 1개.
- 정리본 크기: **7,352 bytes**.
- 정리본 Git blob SHA-1: `2438d01403fb706f05c003538868bdc72accc038`
- 정리본 SHA-256: `7b1905cacd24e030888d2c85cc1d0b0c8d873eabed41c6546fa2fcd0253132c4`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## doc-07

- 경로: `implementation/experiments/chart-contract-v0.1/p0-prerequisites/contract/CHARTDOCUMENT_V01_ADEQUACY_AND_V02_PROPOSAL.md`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14` (감사 당시 `3877f9a1eab3d511a58bcb7c49c1a833965737d3`와 동일 파일 bytes).
- 원본 Git blob SHA-1: `29807e03cd8e121aeeeb57200e7fc7f76efc8b6b`
- 원본 SHA-256: `09ec22ad7b5ced46ac29128e22de57713bd18d6b79b0e7133d49738ae6dd413a`
- 원본 크기: **26,896 bytes**.
- 기존 출처 표시: Yahoo Finance / Yahoo chart.
- 기존 문서에 표시된 날짜: 2022-05-17 / 2024-01-15 / 2024-10-14 / 2024-11-05 / 2025-04-09 / 2025-09-19 / 2026-10-04.
- 제거 범위(원본 줄): 128–131.
- 제거 종류·개수: actual_ohlc_price 8개.
- 정리본 크기: **27,244 bytes**.
- 정리본 Git blob SHA-1: `ac51fc323dad97bc43ebe656d9bd091074b8d9d1`
- 정리본 SHA-256: `9b5cb092adab26ce173aaf361399fb040feda420f34266fceac1b76db74a782e`
- 처리: 실제 값만 “값 제거됨(GSQ-010), receipt 참조”로 대체하고 해당 receipt 링크를 남겼다. 문서 PR 제안의 처리이며 canonical 반영은 병합 후다.
- 이력: 원본 값은 과거 공개 Git/Pages/Actions 사본에 남을 수 있으며 이력 재작성·소거를 하지 않았다.

## Frozen 메타데이터 receipt 목록

배열·종목별 순위·시총·cutoff·가격과 그 재구성 조합은 복사하지 않는다. 원본 파일 식별에 필요한 path/hash/bytes/as_of/kind/출처 경로만 남긴다. 코덱1은 후속 구현에서 실제 값 삭제와 공개 소비 경로 차단을 수행해야 하며, 이 목록 자체는 값 제거 완료 또는 새로운 Frozen 검증 PASS가 아니다.

## frozen-01

- 원본 경로: `implementation/reports/gate_evidence/official_snapshot_2024-06-30.json`
- 기준일: **2024-06-30**.
- 원본 종류: `OFFICIAL_US_MCAP_TOP500_PIT`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14`
- Git blob SHA-1: `da6d5adbff1b0083c52f5ebe4f343f66c5c30a60`
- SHA-256: `1bbc039885ae7606a36f954aedcf955b17834e8a10a5547e59c150e53d788f8d`
- 원본 크기: **180,625 bytes**.
- 출처/증거 경로: `implementation/reports/gate_evidence/gate_chain_2024-06-30_real_gha.json`
- 출처 범위: 기존 official_snapshot과 gate_chain real_gha 결과; SEC 재무/주식수·공시와 가격 기반 Frozen 구성. 외부 원응답을 새 조회하지 않음.
- 값 제거 상태: **코덱1 후속 작업 대기; 이번 문서 PR에서는 미실행**. 원본에 값이 남아 있는 현 상태를 공개 허용으로 판정하지 않는다.
- 원본 개인 보관: **사용자 별도 처리; 이번 작업에서는 미실행**. 공개 branch/폴더로 옮기는 방식은 비공개 보관이 아니다.
- 과거 사본: GSQ-010에 따라 재작성하지 않으며 잔여 노출 수용과 force push 금지를 유지한다.

## frozen-02

- 원본 경로: `implementation/reports/gate_evidence/official_snapshot_2024-09-30.json`
- 기준일: **2024-09-30**.
- 원본 종류: `OFFICIAL_US_MCAP_TOP500_PIT`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14`
- Git blob SHA-1: `5e33aec98c495696cb8c3ea01b1288654a261d64`
- SHA-256: `367b8dba1a00c0b9293a9242d29255c1a9342201684bd5bb1a0168384b21e9e4`
- 원본 크기: **180,565 bytes**.
- 출처/증거 경로: `implementation/reports/gate_evidence/gate_chain_2024-09-30_real_gha.json`
- 출처 범위: 기존 official_snapshot과 gate_chain real_gha 결과; SEC 재무/주식수·공시와 가격 기반 Frozen 구성. 외부 원응답을 새 조회하지 않음.
- 값 제거 상태: **코덱1 후속 작업 대기; 이번 문서 PR에서는 미실행**. 원본에 값이 남아 있는 현 상태를 공개 허용으로 판정하지 않는다.
- 원본 개인 보관: **사용자 별도 처리; 이번 작업에서는 미실행**. 공개 branch/폴더로 옮기는 방식은 비공개 보관이 아니다.
- 과거 사본: GSQ-010에 따라 재작성하지 않으며 잔여 노출 수용과 force push 금지를 유지한다.

## frozen-03

- 원본 경로: `implementation/reports/gate_evidence/official_snapshot_2024-12-31.json`
- 기준일: **2024-12-31**.
- 원본 종류: `OFFICIAL_US_MCAP_TOP500_PIT`
- 원본 확인 커밋: `a8b275e6f509838b3edd516c2d0dfdde6c50ae14`
- Git blob SHA-1: `0277ec47f77ef2b0bfbab714352b2e0a76bdd7d6`
- SHA-256: `75f795f838a608a6554e9a3fa3aa8e9e56e72fdfad4e5f8f74623aa00c7a47c9`
- 원본 크기: **180,645 bytes**.
- 출처/증거 경로: `implementation/reports/gate_evidence/gate_chain_2024-12-31_real_gha.json`
- 출처 범위: 기존 official_snapshot과 gate_chain real_gha 결과; SEC 재무/주식수·공시와 가격 기반 Frozen 구성. 외부 원응답을 새 조회하지 않음.
- 값 제거 상태: **코덱1 후속 작업 대기; 이번 문서 PR에서는 미실행**. 원본에 값이 남아 있는 현 상태를 공개 허용으로 판정하지 않는다.
- 원본 개인 보관: **사용자 별도 처리; 이번 작업에서는 미실행**. 공개 branch/폴더로 옮기는 방식은 비공개 보관이 아니다.
- 과거 사본: GSQ-010에 따라 재작성하지 않으며 잔여 노출 수용과 force push 금지를 유지한다.

## receipt의 범위

이 문서는 metadata-only 수령/처리 기록이다. 원 자료의 진위를 hash만으로 증명하거나 삭제 완료를 재검증하는 계약이 아니다. 원본을 새로 조회해 hash를 만들지 않았고 Secret API·개인 저장소·공급자·기존 배포·로그/아티팩트 본문은 조회하지 않았다. 보류 51개의 출처 재검토와 추가 정리 대상은 [감사 후속 절](AUDIT.md#gsq-010-followup)에 기록한다.
