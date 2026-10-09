/* Global presentation preference. Source identifiers and raw data are never translated. */
(function(root,factory) {
  const api=factory();
  if(typeof module==="object" && module.exports) module.exports=api;
  else root.AppLanguage=api;
})(typeof globalThis!=="undefined"?globalThis:this,function() {
  "use strict";
  const LOCALES=Object.freeze(["ko-KR","en-US"]), KEY="investment.web.v1.settings";
  const UI={"본문으로":{"ko-KR":"본문으로","en-US":"Skip to content"},"데이터를 불러오는 중…":{"ko-KR":"데이터를 불러오는 중…","en-US":"Loading data…"},"주요 화면":{"ko-KR":"주요 화면","en-US":"Main navigation"},"오늘":{"ko-KR":"오늘","en-US":"Today"},"기업":{"ko-KR":"기업","en-US":"Companies"},"보유":{"ko-KR":"보유","en-US":"Holdings"},"순위":{"ko-KR":"순위","en-US":"Rankings"},"뉴스·관계":{"ko-KR":"뉴스·관계","en-US":"News / Network"},"리서치":{"ko-KR":"리서치","en-US":"Research"},"설정":{"ko-KR":"설정","en-US":"Settings"},"전체 검색":{"ko-KR":"전체 검색","en-US":"Global Search"},"표시 언어":{"ko-KR":"표시 언어","en-US":"Display language"},"뉴스 원문 언어":{"ko-KR":"뉴스 원문 언어","en-US":"News source language"},"전체 언어":{"ko-KR":"전체 언어","en-US":"All source languages"},"한국어 원문":{"ko-KR":"한국어 원문","en-US":"Korean sources"},"영어 원문":{"ko-KR":"영어 원문","en-US":"English sources"},"표시 언어는 계산 결과에 영향을 주지 않습니다.":{"ko-KR":"표시 언어는 계산 결과에 영향을 주지 않습니다.","en-US":"Display language does not affect calculation results."},"원문 언어는 뉴스 필터만 변경합니다.":{"ko-KR":"원문 언어는 뉴스 필터만 변경합니다.","en-US":"Source language changes only the news filter."},"미제공":{"ko-KR":"미제공","en-US":"Not provided"},"시점 미제공":{"ko-KR":"시점 미제공","en-US":"As-of not provided"},"출처 미제공":{"ko-KR":"출처 미제공","en-US":"Source not provided"},"저장되었습니다.":{"ko-KR":"저장되었습니다.","en-US":"Saved."},"이 브라우저에 저장할 수 없습니다. 내보내기로 보관하세요.":{"ko-KR":"이 브라우저에 저장할 수 없습니다. 내보내기로 보관하세요.","en-US":"Cannot save in this browser. Export a backup."},"기존 설정 손상: 원본을 보존했습니다. 현재 변경은 내보내기로 보관하세요.":{"ko-KR":"기존 설정 손상: 원본을 보존했습니다. 현재 변경은 내보내기로 보관하세요.","en-US":"Existing preferences are corrupt and have been preserved. Export current changes."},"저장된 설정을 읽을 수 없습니다. 원본을 덮어쓰지 않고 임시로 시작합니다.":{"ko-KR":"저장된 설정을 읽을 수 없습니다. 원본을 덮어쓰지 않고 임시로 시작합니다.","en-US":"Cannot read saved preferences. Temporary preferences are in use; the original is preserved."},"관심기업 파일 형식 오류":{"ko-KR":"관심기업 파일 형식 오류","en-US":"Invalid interests file"},"관심기업":{"ko-KR":"관심기업","en-US":"Interests"},"Evidence(근거) · 원본 보기":{"ko-KR":"Evidence(근거) · 원본 보기","en-US":"Evidence · View original"},"운영 Snapshot이 연결되지 않았습니다.":{"ko-KR":"운영 Snapshot이 연결되지 않았습니다.","en-US":"Operating snapshots are not connected."},"이 기업의 Snapshot 미제공":{"ko-KR":"이 기업의 Snapshot 미제공","en-US":"No snapshot provided for this company"},"오늘의 투자 화면":{"ko-KR":"오늘의 투자 화면","en-US":"Today's investment view"},"중요한 변화부터 확인하고, 근거까지 따라가세요.":{"ko-KR":"중요한 변화부터 확인하고, 근거까지 따라가세요.","en-US":"Review key changes and follow the evidence."},"Portfolio(포트폴리오)":{"ko-KR":"Portfolio(포트폴리오)","en-US":"Portfolio"},"자세히 →":{"ko-KR":"자세히 →","en-US":"Details →"},"연결 대기":{"ko-KR":"연결 대기","en-US":"Awaiting data"},"제공된 Snapshot":{"ko-KR":"제공된 Snapshot","en-US":"Provided snapshot"},"실제 보유·평가금액·수익률을 연결하면 여기서 확인합니다.":{"ko-KR":"실제 보유·평가금액·수익률을 연결하면 여기서 확인합니다.","en-US":"Connect actual holdings, valuation and returns to view them here."},"오늘 / 최근 주요 변화":{"ko-KR":"오늘 / 최근 주요 변화","en-US":"Recent key changes"},"Macro(거시환경)":{"ko-KR":"Macro(거시환경)","en-US":"Macro"},"Technical(기술적 분석)":{"ko-KR":"Technical(기술적 분석)","en-US":"Technical"},"Attention(확인 필요)":{"ko-KR":"Attention(확인 필요)","en-US":"Attention"},"기업 목록은":{"ko-KR":"기업 목록은","en-US":"Company list as of"},"과거 스냅샷입니다. 최신 시세·분석이 아닙니다.":{"ko-KR":"과거 스냅샷입니다. 최신 시세·분석이 아닙니다.","en-US":"is a historical snapshot. Current prices and analysis are not connected."},"출처와 데이터 시점을 확인하세요.":{"ko-KR":"출처와 데이터 시점을 확인하세요.","en-US":"Check the source and as-of date."},"분석 · 뉴스 · 관계 변화 더보기":{"ko-KR":"분석 · 뉴스 · 관계 변화 더보기","en-US":"More analysis, news and relationship changes"},"QGV 변화":{"ko-KR":"QGV 변화","en-US":"QGV changes"},"변화량은 upstream changes가 제공할 때만 표시합니다.":{"ko-KR":"변화량은 upstream changes가 제공할 때만 표시합니다.","en-US":"Changes are displayed only when supplied by the producer."},"Technical 변화":{"ko-KR":"Technical 변화","en-US":"Technical changes"},"최근 신호는 기업 상세에서 확인하세요.":{"ko-KR":"최근 신호는 기업 상세에서 확인하세요.","en-US":"See company details for recent signals."},"관심기업 뉴스":{"ko-KR":"관심기업 뉴스","en-US":"Interest news"},"뉴스 열기 →":{"ko-KR":"뉴스 열기 →","en-US":"Open news →"},"Relationship changes(관계 변화)":{"ko-KR":"Relationship changes(관계 변화)","en-US":"Relationship changes"},"관계망 열기 →":{"ko-KR":"관계망 열기 →","en-US":"Open network →"},"기업 탐색":{"ko-KR":"기업 탐색","en-US":"Explore companies"},"기업 검색":{"ko-KR":"기업 검색","en-US":"Search companies"},"티커 또는 기업명 검색":{"ko-KR":"티커 또는 기업명 검색","en-US":"Search ticker or company name"},"관심기업만":{"ko-KR":"관심기업만","en-US":"Interests only"},"그룹 필터":{"ko-KR":"그룹 필터","en-US":"Group filter"},"모든 그룹":{"ko-KR":"모든 그룹","en-US":"All groups"},"더보기":{"ko-KR":"더보기","en-US":"More"},"관심기업 · Groups(그룹) 관리":{"ko-KR":"관심기업 · Groups(그룹) 관리","en-US":"Manage interests and groups"},"이 기기의 브라우저에 저장됩니다. 즐겨찾기와 관심기업은 같은 목록입니다.":{"ko-KR":"이 기기의 브라우저에 저장됩니다. 즐겨찾기와 관심기업은 같은 목록입니다.","en-US":"Saved in this browser. Favorites and interests share one list."},"새 그룹 이름":{"ko-KR":"새 그룹 이름","en-US":"New group name"},"예: 반도체":{"ko-KR":"예: 반도체","en-US":"Example: Semiconductor"},"그룹 만들기":{"ko-KR":"그룹 만들기","en-US":"Create group"},"개":{"ko-KR":"개","en-US":"items"},"그룹 이름":{"ko-KR":"그룹 이름","en-US":"Group name"},"이름 변경":{"ko-KR":"이름 변경","en-US":"Rename"},"그룹 삭제":{"ko-KR":"그룹 삭제","en-US":"Delete group"},"내보내기":{"ko-KR":"내보내기","en-US":"Export"},"설정 병합 가져오기":{"ko-KR":"설정 병합 가져오기","en-US":"Import and merge preferences"},"기업을 찾을 수 없습니다.":{"ko-KR":"기업을 찾을 수 없습니다.","en-US":"Company not found."},"기업 목록 →":{"ko-KR":"기업 목록 →","en-US":"Company list →"},"← 기업 목록":{"ko-KR":"← 기업 목록","en-US":"← Company list"},"Macro exposure / context(거시 노출)":{"ko-KR":"Macro exposure / context(거시 노출)","en-US":"Macro exposure / context"},"기업 노출:":{"ko-KR":"기업 노출:","en-US":"Company exposure:"},"Portfolio status(보유 상태)":{"ko-KR":"Portfolio status(보유 상태)","en-US":"Portfolio status"},"Snapshot에 포함 · 비중":{"ko-KR":"Snapshot에 포함 · 비중","en-US":"Included in snapshot · Weight"},"제공된 Snapshot에 없음":{"ko-KR":"제공된 Snapshot에 없음","en-US":"Absent from provided snapshot"},"실제 보유 상태 미제공":{"ko-KR":"실제 보유 상태 미제공","en-US":"Actual holdings not provided"},"이 기업의 뉴스·관계망 확인 →":{"ko-KR":"이 기업의 뉴스·관계망 확인 →","en-US":"View this company's news and network →"},"내 포트폴리오":{"ko-KR":"내 포트폴리오","en-US":"My portfolio"},"보유 현황":{"ko-KR":"보유 현황","en-US":"Holdings"},"수익률":{"ko-KR":"수익률","en-US":"Return"},"평가금액":{"ko-KR":"평가금액","en-US":"Market value"},"Exposure(노출)":{"ko-KR":"Exposure(노출)","en-US":"Exposure"},"모델 비중":{"ko-KR":"모델 비중","en-US":"Model weight"},"실제 비중":{"ko-KR":"실제 비중","en-US":"Actual weight"},"기업별 분석 →":{"ko-KR":"기업별 분석 →","en-US":"Company analysis →"},"기업별 신호 →":{"ko-KR":"기업별 신호 →","en-US":"Company signals →"},"중요 뉴스·관계 변화 →":{"ko-KR":"중요 뉴스·관계 변화 →","en-US":"Key news and relationship changes →"},"기업 순위":{"ko-KR":"기업 순위","en-US":"Company rankings"},"QGV 순위와 시가총액 순위는 각각 upstream 값을 표시합니다.":{"ko-KR":"QGV 순위와 시가총액 순위는 각각 upstream 값을 표시합니다.","en-US":"QGV and market-cap ranks are separate producer values."},"제공된 Leaderboard":{"ko-KR":"제공된 Leaderboard","en-US":"Provided leaderboard"},"시총 순위":{"ko-KR":"시총 순위","en-US":"Market-cap rank"},"시총 #":{"ko-KR":"시총 #","en-US":"Market cap #"},"Daily move(전일 등락)":{"ko-KR":"Daily move(전일 등락)","en-US":"Daily move"},"Consensus(컨센서스)":{"ko-KR":"Consensus(컨센서스)","en-US":"Consensus"},"Scenario(시나리오)":{"ko-KR":"Scenario(시나리오)","en-US":"Scenario"},"Reevaluation(재평가 기준)":{"ko-KR":"Reevaluation(재평가 기준)","en-US":"Reevaluation trigger"},"뉴스와 연결":{"ko-KR":"뉴스와 연결","en-US":"News and connections"},"기업 문맥":{"ko-KR":"기업 문맥","en-US":"Company context"},"Portfolio · 관심기업 · 기타 중요뉴스":{"ko-KR":"Portfolio · 관심기업 · 기타 중요뉴스","en-US":"Portfolio · Interests · Other key news"},"콘텐츠 전환":{"ko-KR":"콘텐츠 전환","en-US":"Content view"},"뉴스":{"ko-KR":"뉴스","en-US":"News"},"관계망":{"ko-KR":"관계망","en-US":"Network"},"뉴스 범위":{"ko-KR":"뉴스 범위","en-US":"News scope"},"전체 중요뉴스":{"ko-KR":"전체 중요뉴스","en-US":"All key news"},"Fact = 확인된 관계 · Impact = 잠재 영향 경로":{"ko-KR":"Fact = 확인된 관계 · Impact = 잠재 영향 경로","en-US":"Fact = confirmed relationship · Impact = potential pathway"},"Track D 운영 관계망 미연결":{"ko-KR":"Track D 운영 관계망 미연결","en-US":"Track D operating network not connected"},"질문에서 근거로":{"ko-KR":"질문에서 근거로","en-US":"From questions to evidence"},"일치하는 기업이 없습니다.":{"ko-KR":"일치하는 기업이 없습니다.","en-US":"No matching companies."},"상태 미제공":{"ko-KR":"상태 미제공","en-US":"Status not provided"},"이 범위에 제공된 뉴스가 없습니다.":{"ko-KR":"이 범위에 제공된 뉴스가 없습니다.","en-US":"No news provided for this scope."},"DEMO 포함 · 합성 데이터는 투자 판단용이 아닙니다.":{"ko-KR":"DEMO 포함 · 합성 데이터는 투자 판단용이 아닙니다.","en-US":"Includes DEMO · Synthetic data is not for investment decisions."},"개인 설정 저장을 사용할 수 없습니다. 내보내기를 이용하세요.":{"ko-KR":"개인 설정 저장을 사용할 수 없습니다. 내보내기를 이용하세요.","en-US":"Preference storage is unavailable. Use export."},"1MB 이하 JSON을 선택하세요.":{"ko-KR":"1MB 이하 JSON을 선택하세요.","en-US":"Select a JSON file of 1 MB or less."},"가져오기 실패:":{"ko-KR":"가져오기 실패:","en-US":"Import failed:"},"데이터를 열 수 없습니다.":{"ko-KR":"데이터를 열 수 없습니다.","en-US":"Cannot open data."},"연결 상태를 확인한 뒤 다시 시도하세요.":{"ko-KR":"연결 상태를 확인한 뒤 다시 시도하세요.","en-US":"Check the connection and retry."},"다시 시도":{"ko-KR":"다시 시도","en-US":"Retry"},"기업·산업·투자자·거시지표 검색":{"ko-KR":"기업·산업·투자자·거시지표 검색","en-US":"Search companies, industries, investors and macro indicators"},"검색 순서는 투자 추천 순위가 아닙니다.":{"ko-KR":"검색 순서는 투자 추천 순위가 아닙니다.","en-US":"Search order does not represent investment recommendations."},"일치하는 항목이 없습니다.":{"ko-KR":"일치하는 항목이 없습니다.","en-US":"No matching entities."},"검색어를 입력하세요.":{"ko-KR":"검색어를 입력하세요.","en-US":"Enter a query."},"산업":{"ko-KR":"산업","en-US":"Industry"},"투자자":{"ko-KR":"투자자","en-US":"Investor"},"거시지표":{"ko-KR":"거시지표","en-US":"Macro indicator"},"등록된 항목":{"ko-KR":"등록된 항목","en-US":"Registered entity"},"분석 미연결":{"ko-KR":"분석 미연결","en-US":"Analysis unavailable"},"QGV 제공":{"ko-KR":"QGV 제공","en-US":"QGV available"},"Snapshot 보유":{"ko-KR":"Snapshot 보유","en-US":"Held in snapshot"},"원문":{"ko-KR":"원문","en-US":"Original source"},"관련 기업":{"ko-KR":"관련 기업","en-US":"Related companies"},"산업 분류가 제공된 기업만 표시합니다.":{"ko-KR":"산업 분류가 제공된 기업만 표시합니다.","en-US":"Only companies with a supplied industry classification are shown."},"Investor-QGV 미연결":{"ko-KR":"Investor-QGV 미연결","en-US":"Investor-QGV not connected"},"표시 메타데이터만 등록되어 있습니다.":{"ko-KR":"표시 메타데이터만 등록되어 있습니다.","en-US":"Only presentation metadata is registered."},"금융 용어":{"ko-KR":"금융 용어","en-US":"Financial terminology"},"검증 상태":{"ko-KR":"검증 상태","en-US":"Validation status"},"정상":{"ko-KR":"정상","en-US":"Normal"},"경고":{"ko-KR":"경고","en-US":"Warning"},"비상":{"ko-KR":"비상","en-US":"Emergency"},"제공되지 않음":{"ko-KR":"제공되지 않음","en-US":"Not available"},"검증됨":{"ko-KR":"검증됨","en-US":"Validated"},"검증 대기":{"ko-KR":"검증 대기","en-US":"Awaiting validation"},"설정을 읽을 수 없습니다. 저장된 원본은 보존합니다.":{"ko-KR":"설정을 읽을 수 없습니다. 저장된 원본은 보존합니다.","en-US":"Cannot read settings. Saved original is preserved."},"설정을 저장할 수 없습니다.":{"ko-KR":"설정을 저장할 수 없습니다.","en-US":"Cannot save settings."},"확대":{"ko-KR":"확대","en-US":"Zoom in"},"축소":{"ko-KR":"축소","en-US":"Zoom out"},"관계 필터":{"ko-KR":"관계 필터","en-US":"Relationship filter"},"모든 관계":{"ko-KR":"모든 관계","en-US":"All relationships"},"Fact만":{"ko-KR":"Fact만","en-US":"Facts only"},"추론만":{"ko-KR":"추론만","en-US":"Inferences only"},"선택 기업 집중":{"ko-KR":"선택 기업 집중","en-US":"Focus selected company"},"콘텐츠 버전 · 사용법":{"ko-KR":"콘텐츠 버전 · 사용법","en-US":"Content version / Help"},"Filters(필터) · Starter · Bundle":{"ko-KR":"Filters(필터) · Starter · Bundle","en-US":"Filters · Starter · Bundle"},"Variables (변수)":{"ko-KR":"Variables (변수)","en-US":"Variables"},"Preview (미리보기)":{"ko-KR":"Preview (미리보기)","en-US":"Preview"},"Copy (복사)":{"ko-KR":"Copy (복사)","en-US":"Copy"},"Copied":{"ko-KR":"Copied","en-US":"Copied"},"All domains (전체)":{"ko-KR":"All domains (전체)","en-US":"All domains"},"All roles (전체)":{"ko-KR":"All roles (전체)","en-US":"All roles"},"All scopes (전체)":{"ko-KR":"All scopes (전체)","en-US":"All scopes"},"No bundle (번들 없음)":{"ko-KR":"No bundle (번들 없음)","en-US":"No bundle"}};
  Object.assign(UI,{"보고서":{"ko-KR":"보고서","en-US":"Reports"},"알림":{"ko-KR":"알림","en-US":"Alerts"},"Ready to copy (복사 가능)":{"ko-KR":"Ready to copy (복사 가능)","en-US":"Ready to copy"},"Missing required (필수 누락)":{"ko-KR":"Missing required (필수 누락)","en-US":"Missing required"},"Invalid (오류)":{"ko-KR":"Invalid (오류)","en-US":"Invalid"},"Copied (복사됨)":{"ko-KR":"Copied (복사됨)","en-US":"Copied"},"준비됨":{"ko-KR":"준비됨","en-US":"Ready"},"일부 제공":{"ko-KR":"일부 제공","en-US":"Partial"},"차단됨":{"ko-KR":"차단됨","en-US":"Blocked"},"합성 데이터":{"ko-KR":"합성 데이터","en-US":"Synthetic"},"상승 추세":{"ko-KR":"상승 추세","en-US":"Uptrend"},"하락 추세":{"ko-KR":"하락 추세","en-US":"Downtrend"},"횡보":{"ko-KR":"횡보","en-US":"Range"},"높은 변동성":{"ko-KR":"높은 변동성","en-US":"High volatility"},"알 수 없음":{"ko-KR":"알 수 없음","en-US":"Unknown"},"진입 구간":{"ko-KR":"진입 구간","en-US":"Entry"},"추가 구간":{"ko-KR":"추가 구간","en-US":"Add"},"대기":{"ko-KR":"대기","en-US":"Wait"},"위험 축소":{"ko-KR":"위험 축소","en-US":"Risk reduction"},"데이터 누락":{"ko-KR":"데이터 누락","en-US":"Missing data"},"오래된 데이터":{"ko-KR":"오래된 데이터","en-US":"Stale data"},"추정 데이터":{"ko-KR":"추정 데이터","en-US":"Estimated data"},"출처 충돌":{"ko-KR":"출처 충돌","en-US":"Conflicting sources"},"PIT 데이터 없음":{"ko-KR":"PIT 데이터 없음","en-US":"PIT unavailable"},"버전 불일치":{"ko-KR":"버전 불일치","en-US":"Version mismatch"},"식별자 변경":{"ko-KR":"식별자 변경","en-US":"Identifier changed"},"계산 오류":{"ko-KR":"계산 오류","en-US":"Calculation error"},"의존성 차단":{"ko-KR":"의존성 차단","en-US":"Blocked dependency"},"해당 없음":{"ko-KR":"해당 없음","en-US":"Not applicable"},"식별자 모호성":{"ko-KR":"식별자 모호성","en-US":"Ambiguous identifier"}});
  Object.assign(UI,{"생산자 검증(validation)이 PASS가 아니라 표시하지 않습니다.":{"ko-KR":"생산자 검증(validation)이 PASS가 아니라 표시하지 않습니다.","en-US":"Withheld: producer validation is not PASS."}});
  Object.assign(UI,{"게시 승인이 없는 연구·잠정 결과라 표시하지 않습니다.":{"ko-KR":"게시 승인이 없는 연구·잠정 결과라 표시하지 않습니다.","en-US":"Withheld: research or provisional output without publication approval."}});
  // Production-shaped state presentation: freshness labels, persisted producer metadata, remaining UI strings.
  Object.assign(UI,{"만료 전":{"ko-KR":"만료 전","en-US":"Before expiry"},"만료 후, 최신 아님":{"ko-KR":"만료 후, 최신 아님","en-US":"Past expiry, not current"},"사용 기한 경과, 표시 보류":{"ko-KR":"사용 기한 경과, 표시 보류","en-US":"Past usable-until, withheld"},"사용 기한(usable_until)이 지난 데이터라 표시하지 않습니다.":{"ko-KR":"사용 기한(usable_until)이 지난 데이터라 표시하지 않습니다.","en-US":"Withheld: past the producer-declared usable_until."},"사유 코드":{"ko-KR":"사유 코드","en-US":"Reason code"},"생산자 데이터 시점":{"ko-KR":"생산자 데이터 시점","en-US":"Producer as-of"},"방법론":{"ko-KR":"방법론","en-US":"Methodology"},"신선도":{"ko-KR":"신선도","en-US":"Freshness"},"커버리지 집계":{"ko-KR":"커버리지 집계","en-US":"Coverage counts"},"종목 보유":{"ko-KR":"종목 보유","en-US":"holdings"},"News / Relationships(뉴스·관계)":{"ko-KR":"News / Relationships(뉴스·관계)","en-US":"News / Relationships"},"QGV context(QGV 맥락)":{"ko-KR":"QGV context(QGV 맥락)","en-US":"QGV context"},"Technical context(기술적 분석 맥락)":{"ko-KR":"Technical context(기술적 분석 맥락)","en-US":"Technical context"},"Macro context(거시 맥락)":{"ko-KR":"Macro context(거시 맥락)","en-US":"Macro context"},"News Network(뉴스 관계망)":{"ko-KR":"News Network(뉴스 관계망)","en-US":"News Network"},"Prompt Library(프롬프트 라이브러리)":{"ko-KR":"Prompt Library(프롬프트 라이브러리)","en-US":"Prompt Library"},"Prompt → Context / Variables → Preview → Copy":{"ko-KR":"프롬프트 → 맥락·변수 → 미리보기 → 복사","en-US":"Prompt → Context / Variables → Preview → Copy"}});
  Object.assign(UI,{"개인 참고용입니다. 투자 권유나 자문이 아닙니다.":{"ko-KR":"개인 참고용입니다. 투자 권유나 자문이 아닙니다.","en-US":"For personal reference only. Not investment advice."}});
  // Cockpit IA v1 navigation and availability. No source data or calculations are translated.
  Object.assign(UI, {
    "기술":{"ko-KR":"기술","en-US":"Technical"},
    "매크로":{"ko-KR":"매크로","en-US":"Macro"},
    "검증":{"ko-KR":"검증","en-US":"Validation"},
    "내 투자":{"ko-KR":"내 투자","en-US":"My investments"},
    "종목 찾기·분석":{"ko-KR":"종목 찾기·분석","en-US":"Find / analyze companies"},
    "시장 정보":{"ko-KR":"시장 정보","en-US":"Market information"},
    "성과":{"ko-KR":"성과","en-US":"Performance"},
    "QGV 허브":{"ko-KR":"QGV 허브","en-US":"QGV hub"},
    "기존 화면과 각 기능의 준비 상태를 확인합니다.":{"ko-KR":"기존 화면과 각 기능의 준비 상태를 확인합니다.","en-US":"Open existing screens and check feature availability."},
    "사용 가능":{"ko-KR":"사용 가능","en-US":"Available"},
    "부분":{"ko-KR":"부분","en-US":"Partial"},
    "준비 중":{"ko-KR":"준비 중","en-US":"Coming soon"},
    "포트폴리오":{"ko-KR":"포트폴리오","en-US":"Portfolio"},
    "실제 보유":{"ko-KR":"실제 보유","en-US":"Actual holdings"},
    "전략 프로필":{"ko-KR":"전략 프로필","en-US":"Strategy profile"},
    "모델 포트폴리오":{"ko-KR":"모델 포트폴리오","en-US":"Model portfolio"},
    "전체 기업":{"ko-KR":"전체 기업","en-US":"All companies"},
    "리더보드":{"ko-KR":"리더보드","en-US":"Leaderboard"},
    "관심 기업":{"ko-KR":"관심 기업","en-US":"Watchlist"},
    "뉴스·관계망":{"ko-KR":"뉴스·관계망","en-US":"News / Network"},
    "투자자 13F":{"ko-KR":"투자자 13F","en-US":"Investor 13F"},
    "Track Record":{"ko-KR":"Track Record","en-US":"Track Record"},
    "기기 보유 요약을 확인합니다. 운영 포트폴리오 Snapshot은 미연결입니다.":{"ko-KR":"기기 보유 요약을 확인합니다. 운영 포트폴리오 Snapshot은 미연결입니다.","en-US":"View local holdings. Operating portfolio snapshots are not connected."},
    "이 기기에 보유와 수동 시세를 입력·관리합니다.":{"ko-KR":"이 기기에 보유와 수동 시세를 입력·관리합니다.","en-US":"Enter and manage holdings and manual quotes on this device."},
    "전략 프로필 상세 화면은 준비 중입니다.":{"ko-KR":"전략 프로필 상세 화면은 준비 중입니다.","en-US":"The strategy profile screen is coming soon."},
    "모델 포트폴리오 상세 화면은 준비 중입니다.":{"ko-KR":"모델 포트폴리오 상세 화면은 준비 중입니다.","en-US":"The model portfolio screen is coming soon."},
    "과거 기업 목록을 탐색합니다. 운영 기업 분석은 미연결입니다.":{"ko-KR":"과거 기업 목록을 탐색합니다. 운영 기업 분석은 미연결입니다.","en-US":"Browse the historical company list. Operating company analysis is not connected."},
    "순위 화면은 열 수 있습니다. 운영 순위 데이터는 미연결입니다.":{"ko-KR":"순위 화면은 열 수 있습니다. 운영 순위 데이터는 미연결입니다.","en-US":"Open the rankings screen. Operating rankings are not connected."},
    "관심 기업 전용 화면은 준비 중입니다. 기존 기업 화면의 관심 목록 관리는 유지됩니다.":{"ko-KR":"관심 기업 전용 화면은 준비 중입니다. 기존 기업 화면의 관심 목록 관리는 유지됩니다.","en-US":"A dedicated watchlist screen is coming soon. Manage existing interests in the companies screen."},
    "뉴스·관계망 화면은 열 수 있습니다. 운영 데이터는 미연결입니다.":{"ko-KR":"뉴스·관계망 화면은 열 수 있습니다. 운영 데이터는 미연결입니다.","en-US":"Open the news and network screen. Operating data is not connected."},
    "투자자 13F 상세 화면은 준비 중입니다.":{"ko-KR":"투자자 13F 상세 화면은 준비 중입니다.","en-US":"The investor 13F screen is coming soon."},
    "검증 허브에서 준비 상태를 확인합니다. 성과 기록은 미연결입니다.":{"ko-KR":"검증 허브에서 준비 상태를 확인합니다. 성과 기록은 미연결입니다.","en-US":"Check availability in the validation hub. Performance records are not connected."},
    "기술적 분석":{"ko-KR":"기술적 분석","en-US":"Technical analysis"},
    "기존 기록의 연결 상태를 확인합니다.":{"ko-KR":"기존 기록의 연결 상태를 확인합니다.","en-US":"Check the connection status of existing records."},
    "기술적 분석 엔진":{"ko-KR":"기술적 분석 엔진","en-US":"Technical analysis engine"},
    "기존 종목 화면에서 제공된 기술적 분석 기록을 확인합니다.":{"ko-KR":"기존 종목 화면에서 제공된 기술적 분석 기록을 확인합니다.","en-US":"View supplied technical records in the existing company screen."},
    "가격·거래량 차트":{"ko-KR":"가격·거래량 차트","en-US":"Price / volume charts"},
    "실제 가격·거래량 차트가 이 앱에 연결되지 않았습니다.":{"ko-KR":"실제 가격·거래량 차트가 이 앱에 연결되지 않았습니다.","en-US":"Actual price and volume charts are not connected to this app."},
    "공식 축별 상태를 확인합니다.":{"ko-KR":"공식 축별 상태를 확인합니다.","en-US":"Check the states of the official macro axes."},
    "매크로 엔진 버전":{"ko-KR":"매크로 엔진 버전","en-US":"Macro engine versions"},
    "확정":{"ko-KR":"확정","en-US":"Confirmed"},
    "후보":{"ko-KR":"후보","en-US":"Candidate"},
    "후보 버전은 운영 엔진 승격을 뜻하지 않습니다.":{"ko-KR":"후보 버전은 운영 엔진 승격을 뜻하지 않습니다.","en-US":"Candidate status does not promote the operating engine."},
    "축별 운영 상태가 이 앱에 연결되지 않았습니다.":{"ko-KR":"축별 운영 상태가 이 앱에 연결되지 않았습니다.","en-US":"Operating states for each axis are not connected to this app."},
    "Growth":{"ko-KR":"Growth · 성장","en-US":"Growth"},
    "Inflation":{"ko-KR":"Inflation · 물가","en-US":"Inflation"},
    "Liquidity":{"ko-KR":"Liquidity · 유동성","en-US":"Liquidity"},
    "Monetary Policy":{"ko-KR":"Monetary Policy · 통화정책","en-US":"Monetary Policy"},
    "Credit":{"ko-KR":"Credit · 신용","en-US":"Credit"},
    "Labor":{"ko-KR":"Labor · 노동","en-US":"Labor"},
    "Fiscal":{"ko-KR":"Fiscal · 재정","en-US":"Fiscal"},
    "FX":{"ko-KR":"FX · 외환","en-US":"FX"},
    "Level":{"ko-KR":"Level · 수준","en-US":"Level"},
    "Direction":{"ko-KR":"Direction · 방향","en-US":"Direction"},
    "Momentum":{"ko-KR":"Momentum · 모멘텀","en-US":"Momentum"},
    "Surprise":{"ko-KR":"Surprise · 예상 대비","en-US":"Surprise"},
    "Stress":{"ko-KR":"Stress · 스트레스","en-US":"Stress"},
    "Confidence":{"ko-KR":"Confidence · 신뢰도","en-US":"Confidence"},
    "검증·연구":{"ko-KR":"검증·연구","en-US":"Validation / Research"},
    "리서치와 검증 기록의 준비 상태를 확인합니다.":{"ko-KR":"리서치와 검증 기록의 준비 상태를 확인합니다.","en-US":"Check the availability of research and validation records."},
    "기존 프롬프트 라이브러리를 엽니다.":{"ko-KR":"기존 프롬프트 라이브러리를 엽니다.","en-US":"Open the existing prompt library."},
    "백테스트":{"ko-KR":"백테스트","en-US":"Backtesting"},
    "전진검증":{"ko-KR":"전진검증","en-US":"Forward validation"},
    "공개 앱에 연결된 백테스트 결과가 없습니다.":{"ko-KR":"공개 앱에 연결된 백테스트 결과가 없습니다.","en-US":"No backtest results are connected to the public app."},
    "공개 앱에 연결된 전진검증 결과가 없습니다.":{"ko-KR":"공개 앱에 연결된 전진검증 결과가 없습니다.","en-US":"No forward validation results are connected to the public app."},
    "공개 앱에 연결된 성과 기록이 없습니다.":{"ko-KR":"공개 앱에 연결된 성과 기록이 없습니다.","en-US":"No performance records are connected to the public app."},
    "← QGV":{"ko-KR":"← QGV","en-US":"← QGV"},
    "← 검증":{"ko-KR":"← 검증","en-US":"← Validation"}
  });
  const TERMS=Object.freeze({
    free_cash_flow:["Free Cash Flow","잉여현금흐름"], drawdown:["Drawdown","낙폭"],
    operating_margin:["Operating Margin","영업이익률"], Q_score:["Quality","품질"],
    G_score:["Growth","성장"], V_score:["Valuation","가치평가"], total_score:["Total score","종합 점수"],
    confidence:["Confidence","신뢰도"], coverage_state:["Coverage","커버리지"],
    regime:["Regime","레짐"], execution_zone:["Execution zone","실행 구간"],
    invalidation:["Invalidation","무효화 조건"]
  });
  function fallback(labels,locale,canonical="") {
    for(const l of [...new Set([locale,"ko-KR","en-US"])]) {
      if(typeof labels?.[l]==="string" && labels[l].trim()) return labels[l];
    }
    return canonical;
  }
  function text(key,locale="ko-KR") { return fallback(UI[key],locale,key); }
  function term(key,locale="ko-KR", bilingual=true) {
    const pair=TERMS[key]; if(!pair) return key;
    return locale==="ko-KR" ? (bilingual?pair[0]+"("+pair[1]+")":pair[1]) : pair[0];
  }
  function status(code,locale) {
    const map={NORMAL:"정상",WARNING:"경고",EMERGENCY:"비상",NOT_AVAILABLE:"제공되지 않음",
      VALIDATED:"검증됨",PASS:"검증됨",PENDING:"검증 대기",
      READY:"준비됨",PARTIAL:"일부 제공",BLOCKED:"차단됨",SYNTHETIC:"합성 데이터",
      TREND_UP:"상승 추세",TREND_DOWN:"하락 추세",RANGE:"횡보",HIGH_VOL:"높은 변동성",UNKNOWN:"알 수 없음",
      ENTRY:"진입 구간",ADD:"추가 구간",WAIT:"대기",RISK_REDUCTION:"위험 축소",
      MISSING_DATA:"데이터 누락",STALE_DATA:"오래된 데이터",ESTIMATED_DATA:"추정 데이터",CONFLICTING_SOURCE:"출처 충돌",
      PIT_UNAVAILABLE:"PIT 데이터 없음",VERSION_MISMATCH:"버전 불일치",IDENTIFIER_CHANGED:"식별자 변경",
      CALCULATION_ERROR:"계산 오류",BLOCKED_DEPENDENCY:"의존성 차단",NOT_APPLICABLE:"해당 없음",IDENTIFIER_AMBIGUOUS:"식별자 모호성"};
    return text(map[code] || code,locale);
  }
  function settings(value={}) {
    if(value===null || typeof value!=="object" || Array.isArray(value)) throw Error("Invalid AppSettings");
    if(value.version!==undefined && value.version!==1) throw Error("Unsupported AppSettings version");
    const display_locale=value.display_locale ?? "ko-KR", source_language=value.source_language ?? "all";
    if(!LOCALES.includes(display_locale) || !["all","ko","en"].includes(source_language))
      throw Error("Invalid language preference");
    return Object.freeze({version:1,display_locale,source_language});
  }
  function read(storage) {
    try {const raw=storage.getItem(KEY); return {value:settings(raw?JSON.parse(raw):{}),writable:true};}
    catch(e) {return {value:settings(),writable:false};}
  }
  function write(storage,value) { storage.setItem(KEY,JSON.stringify(settings(value))); }
  function localized(value,locale,canonical="") { return fallback(value,locale,canonical); }
  return Object.freeze({LOCALES,KEY,UI,TERMS,fallback,text,term,status,settings,read,write,localized});
});
