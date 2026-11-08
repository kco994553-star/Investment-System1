# Main 공통 합성 입력
정상: expanded-index.json 2발행사→expanded-detail/{2자리}.json의 같은 issuer 상세. A는 다중 티커·Q0·관문 입력 있음/실제관문UNKNOWN, B는 미분류. 기존 원래 비교집단3/보유2를 구분.
상세 파일 없음: 전체 배치 검증 거부/이전 정상 묶음 유지; 조회 시 해당 상세만 오류 표시.
색인 중복/상세 issuer누락/다른 scope 또는 날짜/판/summarySHA: 거부. 고정 manifestSHA는 인증된 인계에서 받아야 하며 자체 해시만으로 진위를 보장하지 않는다.
조회 part=expanded_index 또는 expanded_detail&shard=55 등의 고정2자리 패턴만 사용한다. 임의 path를 받지 않는다.
source-summary.json은 별도 출처 합성 자료이며 투영 manifest의 파일 목록에 속하지 않는다.
