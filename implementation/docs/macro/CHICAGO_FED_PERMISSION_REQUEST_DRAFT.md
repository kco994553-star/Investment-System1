# Chicago Fed 자료 이용 허가 요청 초안 (MEV-5)

> **DRAFT · NOT SENT · 발송은 별도 사용자 승인 필요.**
> 이 문서는 문안 초안이다. 아직 아무에게도 보내지 않았다.
> **허용 범위가 서면으로 확인되기 전에는 비공개 Lab 이용도 자동으로 허용되지 않는다.** CFNAI·NFCI는 수집·저장·계산하지 않는다.
> 이름·이메일·연락처는 넣지 않았다. `[CONTACT]` 같은 자리 표시만 있다. 발송 때 사용자가 채운다.

근거: [MACRO_EVIDENCE_LINES_CATALOG_20261018](MACRO_EVIDENCE_LINES_CATALOG_20261018.md) §3 Chicago Fed 행, §12 MEV-5. 사용자 결정 원문: [USER_DECISIONS_PENDING](../USER_DECISIONS_PENDING.md) "결정됨 — 2026-10-18 저녁 (#313 …)" 4항.

같은 결정의 다른 항목(참고):
- MEV-6: 기존 가격·기기 경계 안에서 승인됨. 이 요청과 무관하다.
- MEV-7: 보류. 이 요청에 넣지 않았다.

## 한국어 요약

- 대상: 시카고 연은의 CFNAI(전국 활동 지수, 3개월 평균 포함)와 NFCI(전국 금융 여건 지수, 하위 지수 포함).
- 이유: 시카고 연은 법적 고지는 비영리·출처 표기 조건의 서면물 복제만 허용하고, 재게시·배포는 서면 허가를 요구한다(https://www.chicagofed.org/utilities/legal-notices, 2026-10-18 확인).
- 요청하는 범위(항목별로 허가 여부를 따로 묻는다):
  1. 공개 페이지에 **사건선**만 표시: 날짜와 "CFNAI-MA3가 −0.70 아래로 내려감" 같은 사실 문장. 지수 값 자체는 표시하지 않음.
  2. 공개 페이지에 지수 값과 차트 표시(출처 표기).
  3. 비공개 저장소에 원자료 파일 보관(공개 재배포 없음).
  4. 비공개 연구(과거 사건 재구성·검증)에 사용.
  5. AI 기반 분석 도구로 처리하는 것.
  6. 과거 발표본(빈티지) 파일 이용 가능 여부와 조건.
- 조건 제안: 비상업 개인 연구, 출처 표기, 원자료 재배포 없음, 보증·제휴 암시 없음, 요청 시 삭제.
- 답이 오기 전 동작: 이용하지 않는다. 답이 오면 허가 범위를 결정 기록에 옮기고, 그 범위만 쓴다.

## 발송 전 확인 목록

- [ ] 사용자 발송 승인.
- [ ] 받는 곳(시카고 연은 공식 문의 경로) 확인: `[RECIPIENT]`.
- [ ] 보내는 사람 정보 `[CONTACT]`, `[NAME]`은 사용자가 직접 채움. 저장소에 기록하지 않음.
- [ ] 프로젝트 설명 문구 최종 확인(공개 저장소·공개 페이지가 있다는 사실을 숨기지 않음).
- [ ] 보낸 뒤 사본은 비공개 위치에만. 공개 저장소에는 "발송함/날짜/답변 요지"만.

## 영문 초안

Subject: Permission request — use of CFNAI and NFCI in a non-commercial personal research tool

To: [RECIPIENT], Federal Reserve Bank of Chicago

Dear [RECIPIENT],

I am writing to ask for written permission to use two data products published by the Federal Reserve Bank of Chicago: the Chicago Fed National Activity Index (CFNAI, including the CFNAI-MA3 and the diffusion index) and the National Financial Conditions Index (NFCI, including the ANFCI and its subindexes).

**About the project.** [PROJECT_NAME] is a non-commercial, personal investment research tool maintained by one individual. It has no customers, advertising or paid features. Its source code is kept in a public software repository, and it publishes a small public web page. Personal data and market prices are not published there. The tool shows dated "evidence events" on an economic-cycle chart. Each event is a date plus a short factual statement about an official indicator (for example, "the three-month average crossed a published reference level"). The events are recorded from the information available at the time of each release. Past events are never rewritten.

**Why we are asking.** Your Legal Notices allow reproduction of written materials when it is not for private or commercial gain and the materials are credited to the Bank, and ask that other uses, such as republication or distribution, receive written permission. Some of our uses may fall outside that grant, so we would rather ask first. We have not collected, stored or displayed CFNAI or NFCI data, and will not do so until we hear from you.

**What we would like to do.** Please let us know which of the following you would permit, and on what conditions:

1. **Event lines on the public page (no index values).** Show a date and a factual statement derived from CFNAI or NFCI. For example: "CFNAI-MA3 fell below −0.70 (Federal Reserve Bank of Chicago)". The statement would use the reference levels described on your website. The index values themselves would not be shown.
2. **Index values on the public page.** Show the published index values or a chart of them, credited to the Federal Reserve Bank of Chicago, with a link to your release page.
3. **Private storage.** Keep copies of the published data files in a private, access-controlled store, so that each event can be traced to the release it came from. These copies would not be redistributed.
4. **Private research use.** Use the stored releases, privately, to reconstruct past events and to test how well such evidence lines line up with later business-cycle dates. Results would only be described in summary form.
5. **Automated and AI-assisted processing.** Process the data with automated scripts, including AI-based coding and analysis assistants, for items 1–4 only. The data would not be used to train machine-learning models.
6. **Historical releases.** If you publish or can provide past releases ("vintages") of CFNAI or NFCI, tell us whether they may be used for item 4, and on what terms.

**Conditions we propose.**

- Non-commercial, personal research use only.
- Clear credit on every display: "Source: Federal Reserve Bank of Chicago", with a link to the relevant release page.
- No redistribution of raw data files.
- No suggestion of endorsement or affiliation. The Bank's name, seal or logo would not be used beyond the source credit.
- A note that values may be revised, and that our derived statements are our own and not the Bank's.
- We will stop using the data and delete stored copies if you ask.

If only some items can be permitted, a partial permission is still very helpful. We will keep a record of the permitted scope and limit our use to it.

Thank you for your time and for making these indexes available.

Sincerely,
[NAME]
[CONTACT]
[DATE]

## 회신 처리 (발송·회신 뒤)

- 회신 원문은 비공개로 보관한다. 공개 저장소에는 허가 항목 번호, 조건 요지, 날짜만 적는다.
- 허가된 항목만 목록 문서 §3 Chicago Fed 행과 E24·E37 라이선스·표시 칸에 반영한다(별도 PR).
- 거절·무응답이면 E24·E37은 P3 그대로 두고 사용하지 않는다.
