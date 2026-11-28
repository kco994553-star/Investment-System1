# 전국 신규 실업수당 청구의 출처와 11월 종합 CPI의 분모

## 전국 계절조정 신규 실업수당 청구

**출처와 계산 주체를 확인했다.** 대상은 미국 일반 주 실업보험 프로그램의 주간 전국 계절조정 신규 청구 건수다. ETA 공개 목록은 OUI의 전국 계절조정·비조정 보도자료 이력과 주에서 제출한 ETA-539 원보고서를 서로 다른 데이터셋으로 관리한다. 전국 이력의 식별자는 `ETA-5-012:013-463`, ETA-539의 식별자는 `ETA-5-012:013-464`다. 전국 이력은 1967년부터의 자료로 주간·연간 개정을 포함한다고 명시한다. [ETA 자료 목록](https://www.dol.gov/agencies/eta/datahub/datainventory) · [전국 발표 이력의 연방 카탈로그](https://catalog.data.gov/dataset/historical-unemployment-insurance-seasonally-adjusted-and-unadjusted-weekly-claims-data) · [ETA-539 카탈로그](https://catalog.data.gov/dataset/unemployment-insurance-weekly-claims-extended-benefits-trigger-data-eta-539)

| 항목 | 확인 결과 및 기록 방법 |
|---|---|
| 작성·가공 | 주 실업보험 기관이 청구를 보고한다. BLS가 계절요인을 제공하고 ETA가 비조정 건수에 적용해 전국 계절조정 계열을 공표한다. 최초치는 지급책임 주 기준 ETA-538, 다음 주 개정치는 거주 주 기준 ETA-539다. 현재 주의 속보를 `ETA539` 단일 출처로 기록하면 빈티지가 섞인다. [DOL 주간 보도자료 Technical Notes A·C](https://www.dol.gov/sites/dolgov/files/OPA/newsreleases/ui-claims/20250439.pdf) · [ETA 보고서 539 작성지침](https://oui.doleta.gov/dmstree/handbooks/401/i_1.pdf) |
| 발표·개정 | 통상 목요일 오전 8시 30분 미국 동부 시간에 공개하고 공휴일에는 일정이 바뀐다. 보도자료별 발표 일시, 기준 주 종료일, 최초·전주 개정·연간 개정 구분과 원문을 별도 보존해야 당시 신호를 재생할 수 있다. 계절요인 개정과 비조정 자료의 갱신이 연간 이력에 반영된다. [ETA 보도자료 보관·일정](https://oui.doleta.gov/unemploy/claims_arch.asp) · [DOL Technical Notes](https://www.dol.gov/sites/dolgov/files/OPA/newsreleases/ui-claims/20250439.pdf) |
| 이용조건 | 각 연방 카탈로그의 작성기관은 ETA, 접근 등급은 `public`, 권리 필드는 `TRUE`이다. 해당 항목에 이름 붙은 별도 라이선스나 필드별 재배포 조건은 없다. DOL 일반 규정은 연방정부가 작성한 공개영역 자료의 사용·복제·배포를 허용하고, DOL의 추천·제휴 암시를 금하며, 제3자 저작물이 포함될 수 있다고 밝힌다. 전국 계절조정 숫자의 집계·공표 주체는 확인됐고 해당 필드에 제3자 권리 표시는 확인되지 않았다. `TRUE` 자체를 개별 라이선스로 번역할 수는 없다. [DOL 저작권 정책](https://www.dol.gov/general/aboutdol/copyright) · [전국 이력 메타데이터](https://catalog.data.gov/dataset/historical-unemployment-insurance-seasonally-adjusted-and-unadjusted-weekly-claims-data) |
| 적용 제안 | 개별 주 보고서·그림·로고·개인 청구자료를 제외하고 전국 SA 숫자와 자체 계산한 변화만을 대상으로 이용범위를 명시한다. “U.S. Department of Labor, Employment and Training Administration, Unemployment Insurance Weekly Claims, national seasonally adjusted initial claims”와 기준 주·발표일·빈티지를 표시한다. 소유자 결정과 승인된 PR·커밋 이후에만 해당 범위로 자료 도입을 진행한다. [ETA 전국 조회](https://oui.doleta.gov/unemploy/claims.asp) |

보관 자료에는 해당 세 저점의 주별 시계열이 없어 실업수당 추가 시 개선되는 개월 수는 미측정이다. 이번 확인은 기관 문서·메타데이터 대조이며, 운영 E14의 이용조건 판정이나 관측 취득으로 이어지지 않았다.

## 2026년 11월 종합 CPI 전년동월비

**2025년 11월 전국 종합 CPI-U 비계절조정 지수는 324.122(1982~84=100)이다.** BLS가 2025-12-18 오전 8시 30분 미국 동부 시간에 발표한 USDL-25-1584 본문과 표 1의 전 품목 행을, 보관된 공식 CUUR0000SA0 2025 M11 행과 대조했다. 같은 파일에서 2025 M10은 대시와 예산 공백 각주 X이며 2026 M10까지 있다. 2025년 10월 지수 결측은 2026년 10월 전년동월비의 분모에만 해당한다. [BLS 2025년 11월 발표·표 1](https://www.bls.gov/news.release/archives/cpi_12182025.htm) · [BLS 예산 공백 FAQ](https://www.bls.gov/cpi/additional-resources/2025-federal-government-shutdown-impact-cpi-faq.htm) · [BLS 공식 종합지수 원문](https://download.bls.gov/pub/time.series/cu/cu.data.1.AllItems)

BLS 2026년 10월 보도자료가 안내한 다음 발표 예정일은 **2026-12-10 목요일 오전 8시 30분 미국 동부 시간**이다. 2026-11-22 현재 11월 분자는 발표 전이다. BLS가 2026년 11월 같은 계열의 지수를 실제 공표하면 **100 × (2026년 11월 지수 ÷ 324.122 − 1)**로 계산한 뒤 BLS 표의 공식 전년동월비와 표시 자릿수를 대조할 수 있다. 지수가 공표되지 않으면 그때의 결측 사유를 기록한다. [BLS 2026년 10월 발표 원문](https://www.bls.gov/news.release/archives/cpi_11102026.htm) · [BLS 다음 발표 안내가 실린 PDF](https://www.bls.gov/news.release/pdf/cpi.pdf)
