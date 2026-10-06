이번 사용자 관찰 세션에 한해 AUTONOMY_MODE를 READ_ONLY → RUN으로 전환하는 것을 승인한다.
범위는 최신 Global과 Chart #41에서 확인된 현재 6개 OPEN gate를 줄이기 위한 Main 통합 조정에 한정한다.
수행 범위:
Portfolio·Identity·Theme 책임 owner, branch, write-set 확정
authoritative TARGET 반환 확보
19개 Security mapping 반환 확보
versioned Theme 입력 반환 확보
P01의 TARGET visualization 적용 여부 확인
Web/Integration의 최소 write-set 수용 확보
FPIA governance / independent verifier / launcher / runtime / GIE 상태 확인 및 가능한 범위 처리
owner routing, dependency reconciliation, 검증, evidence 및 handoff 게시
CDR-024 / Autonomous Execution & Decision Authority SSoT v1.1을 적용한다.
D1/D2/D3-A는 승인 범위 안에서 자동 진행하고, D3-R만 중지·보고하라.
다음은 금지한다:
canonical merge
Official/LIVE 승격
Holdout 사용
PIT/no-lookahead 완화
Frozen/history/evidence 파괴적 변경
금융 credential/권한 확대
유료 자원 사용
실제 매매·주문·자금이동
실행 제약:
cycle 최대 5 tasks
lease TTL 2시간
동일 failure repair 최대 3회
stale lease 자동 탈취 금지
publish 직전 AUTONOMY_MODE 재확인
이번 bounded cycle이 끝나거나 WAIT_DEPENDENCY / D3-R / 실제 tool blocker에 도달하면 AUTONOMY_MODE를 다시 READ_ONLY로 복귀시키고 결과를 보고하라.
최신 Global과 Main/Chart scoped handoff를 fresh-read한 뒤 계속 진행해.
