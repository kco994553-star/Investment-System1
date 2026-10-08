[TARGET v0 채택 + #63 병합 — v1.1 범위, READ_ONLY 유지]

사용자 결정 (2026-10-08, Decision Register에 원문과 함께 append-only 기록)
- 첨부한 TARGET_v0.yaml을 Portfolio TARGET(A-S1)과 Strategy Theme(A-S3)의 v0으로 채택한다.
  내용은 QGV Portfolio Specification v1.1 §2를 수정 없이 옮긴 것이다.
- 이 파일의 소스 담당자는 사용자 본인이다(#54의 OWNER_UNASSIGNED 해소).
- 상장 시장: Tokyo Electron = [도쿄 8035 / ADR TOELY], 한미반도체 = [KRX 042700], Alphabet = [GOOGL / GOOG]
- PR #63 병합을 승인한다. 단, base가 기준 브랜치이면 병합하지 말고 보고한다.

1. TARGET 파일 반영
- 첨부 파일을 그대로 implementation/docs/portfolio_target_owner/TARGET_v0.yaml에 추가한다(PR로).
- 비중·테마·종목·시점 값을 바꾸지 않는다. 위 상장 시장 결정만 listing 칸에 반영한다.
- 파일 안의 검증 규칙(테마 합계, 전체 10000, 종목 중복 없음)을 테스트로 고정한다.
- 이후 TARGET 변경은 사용자가 이 파일을 수정할 때만 일어난다. 에이전트는 값을 제안·추정·보정하지 않는다.

2. 종목 식별 (A-S2)
- 19개 종목을 기존에 승인된 식별 계약으로 security_id에 매핑한다. ticker_hint는 참고값일 뿐이다.
- 매핑할 수 없는 종목은 지어내지 말고 UNRESOLVED로 남겨 목록으로 보고한다.

3. Chart 게이트 재평가
- TARGET v0과 A-S2 결과로 Chart P0 게이트 6개를 다시 판정하고, 닫힌 게이트를 evidence와 함께 보고한다.
- TARGET 화면을 기존 SAMPLE 대신 TARGET v0에 연결한다. ACTUAL은 NOT_AVAILABLE 유지.
- 표시만 연결한다. 새 계산법, QGV 재계산, 비중 재정규화는 하지 않는다.

4. #63
- base 확인 후 병합하고, PPA-F08을 닫힌 blocker로 기록한다(Platform 1/9).

5. 보고
- 닫힌 blocker와 게이트(병합 기준), A-S2 매핑 결과(매핑/미해결 수), 남은 사용자 결정.

포함하지 않는 것: 기준 브랜치 병합, 새 투자 계산법, Holdout, AUTONOMY_MODE 변경, 자동화 확장.
