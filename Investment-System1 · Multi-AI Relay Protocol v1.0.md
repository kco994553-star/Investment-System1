Investment-System1 · Multi-AI Relay Protocol v1.0

목적  
GPT → Grok → Claude → GPT처럼 여러 AI가 역할 분담 없이 순차적으로 같은 프로젝트를 이어서 작업한다. Google Drive의 Investment-System1을 Single Source of Truth(SSoT)로 사용한다.

작업 시작 순서  
1\. 00\_Project-Index/Investment System · Project Index  
2\. 00\_Project-Index/Investment-System1 · Master Status Index  
3\. 00\_Project-Index/Investment-System1 · CURRENT\_HANDOFF  
4\. CURRENT\_HANDOFF가 지정한 관련 Latest/Official 문서

핵심 규칙  
\- 이전 AI와의 채팅을 알고 있다고 가정하지 않는다.  
\- Drive 최신 공식 기록이 개별 AI의 기억이나 추측보다 우선한다.  
\- 기존 Architecture/Interface/Version Rule을 임의로 재설계하지 않는다.  
\- 이전 Handoff의 Next Action부터 실제 작업을 진행한다.  
\- 이미 완료된 작업을 이유 없이 다시 구현하지 않는다.  
\- 변경 필요 시 Existing / Proposed / Reason / Impact / Compatibility / Validation Required를 기록하고 검증 전에는 PROPOSED 또는 PROVISIONAL로 둔다.  
\- 기존 PASS 영역을 수정하면 Regression Test를 수행한다.  
\- 실제 실행하지 않은 테스트를 PASS라고 기록하지 않는다.  
\- Unit / Integration / Historical / PIT / OOS / Calibration / Forward Validation / Live Operation을 구분한다.  
\- 하위 모듈 PASS를 전체 시스템 검증 완료로 확대하지 않는다.  
\- Point-in-Time 검증에서 미래정보를 사용하지 않는다.  
\- 완료된 과거 Snapshot/Prediction을 사후 결과로 덮어쓰지 않는다.

작업 종료  
CURRENT\_HANDOFF를 다음 형식으로 갱신한다.  
Timestamp / AI / Project Version / Module-Area  
Started From  
Completed  
Files Changed  
Tests  
Decisions  
Provisional  
Open Issues  
Next Action  
Do Not Repeat

Handoff 규칙  
CURRENT\_HANDOFF에는 다음 AI가 필요한 최신 상태만 유지한다. 과거 인계는 HANDOFF\_HISTORY에 append-only로 보존한다.

Conflict 우선순위  
Official/Latest → Master Status Index → Module Specification → Decision History → Validation Record → Previous Version → Archive.  
해결되지 않으면 CONFLICT로 남기고 중대한 Architecture 변경이면 사용자 확인을 받는다.

완료 원칙  
진행률을 채우기 위해 기능을 추가하지 않는다.  
Implementation → Integration Test → Regression Test → Inconsistency Check → Documentation → Release Candidate → Freeze.  
모두 완료되면 Forward Validation 또는 실제 운용 단계로 넘긴다.  
