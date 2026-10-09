# v1.1 A-S2 종목 식별 결과

**현재 TARGET 종목 식별은 19/19 성공, 미해결 0건입니다.** 이전 0/19는 실제 식별 시도 전의 내부 admission 조사값이었습니다. 이번에는 19행 모두 시도하고 검증했습니다.

미국17행은 Frozen Track A의 SEC CIK를 두 기존 association 파일에서 대조하고, source-native ISIN과 연결했습니다. 16행은 다시 받은 SEC NPORT 원본이 Frozen manifest의 SHA-256/968,291bytes와 정확히 일치하며, 원문의 ISIN/CUSIP/title/EC/currency와 기존 Frozen issuer-CUSIP association을 대조했습니다. ASML은 issuer의 NASDAQ ordinary-share 원본을 사용했습니다. Alphabet은 원문 `ALPHABET INC CLASS A`로 확정했습니다.

Tokyo Electron과 한미반도체는 사용자가 승인한 거래소+코드 pair를 그대로 유지했습니다. 이 두 pair를 가짜 ISIN이나 완성된 C-39 issuer/security/listing 객체로 표현하지 않았습니다. C-39는 opaque nonempty IDs를 허용하므로 미국17의 실제 CIK/ISIN 문자열을 기존 자료형에 바인딩할 수 있습니다. 기존에 승인된 ID registry를 발견했다고 주장하지 않으며, 새 외부 식별자를 발명하지 않았습니다.

| 종목 | issuer 근거 | 현재 security reference | 결과 |
|---|---|---|---|
| ASML Holding | 0000937966 | USN070592100 | 성공 |
| Lam Research | 0000707549 | US5128073062 | 성공 |
| KLA Corporation | 0000319201 | US4824801009 | 성공 |
| Tokyo Electron | 사용자 pair + issuer/DART 원본 | TSE + 8035 | 성공 |
| 한미반도체 | 사용자 pair + issuer/DART 원본 | KRX + 042700 | 성공 |
| NVIDIA | 0001045810 | US67066G1040 | 성공 |
| Advanced Micro Devices | 0000002488 | US0079031078 | 성공 |
| Broadcom | 0001730168 | US11135F1012 | 성공 |
| Qualcomm | 0000804328 | US7475251036 | 성공 |
| Intel | 0000050863 | US4581401001 | 성공 |
| Microsoft | 0000789019 | US5949181045 | 성공 |
| Alphabet | 0001652044 | US02079K3059 | 성공 |
| Amazon | 0001018724 | US0231351067 | 성공 |
| RTX Corporation | 0000101829 | US75513E1010 | 성공 |
| Stryker | 0000310764 | US8636671013 | 성공 |
| Eaton | 0001551182 | IE00B8KQN827 | 성공 |
| Hubbell | 0000048898 | US4435106079 | 성공 |
| GE Vernova | 0001996810 | US36828A1016 | 성공 |
| Rockwell Automation | 0001024478 | US7739031091 | 성공 |

**계층별 결과:** current TARGET reference19/19, 미국 C-39 issuer/security 객체 pair17/17, 사용자 승인 foreign reference2/2, full dated ListingIdentity0/19. ASML issuer country는 source에서 확인하지 못했으므로 `UNKNOWN`으로 명시했습니다. 이 값과 full historical listing은 현재 TARGET 식별의 새 선행조건이 아닙니다.

각 행의 `remaining_full_hierarchy_fields`에 부족한 필드와 획득 소스를 적었습니다. 19행의 exact MIC/listing_id/valid interval/historical availability는 issuer·exchange historical listing master/capture manifests가 필요합니다. Tokyo는 독립 issuer등록/LEI 및 JPXsecuritymaster, 한미는 DARTissuer등록+KRXsecuritymaster에서 full계층을 확장할 수 있습니다. 이들은 시장·세션·과거자료 admission에 관한 후속작업이며, 사용자 지정 현재 종목 선택을 다시 묻지 않습니다.

A-S3는 사용자4테마와19배정을 원본값 그대로 유지하고 map/rootSHA-256을 묶은 sidecar로 완료했습니다. Chart source gate는 A-S1·A-S2·A-S3총3/6해소입니다. A-G1은 원production Product/P01authority/route/invalidation, A-G2는 원production per-file/read-routeacceptance, A-G3는 최종 통합subjectCI/독립검증/FPIA결과가 없어 열려 있습니다. 자세한 다음근거는 `SIX_GATE_REJUDGMENT.json`에 있습니다.

새 mapping/assignment availability는 이번 생성시각부터 적용합니다. 2024NPORT의 security증거를 사용했다는 이유로 새 mapping을 2024년이나 TARGET최초채택시각으로 소급하지 않았습니다. 원TARGET YAML·Frozen data·기존0/19artifact·계산법·Holdout·READ_ONLY·기준브랜치는 바꾸지 않았습니다.

원문 HTML/XML/SEC JSON은 deterministic gzip으로 보존했습니다. 재현검사는 압축파일 해시와 해제한 원본 SHA-256/Git blob을 모두 검사합니다.

재현 명령:

```bash
python implementation/docs/security_map19_owner/v1_1_cycle_20261008/verify_mapping.py
python -m unittest discover -s implementation/docs/security_map19_owner/v1_1_cycle_20261008 -p 'test_evidence_rejections.py' -v
python implementation/docs/strategy_theme_owner/v1_1_cycle_20261008/verify_theme.py
```
