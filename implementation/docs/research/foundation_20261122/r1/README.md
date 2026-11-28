# 기존 경기 규칙 R1을 재생하는 방법

design.txt는 첫 비교 전 고정한 원래 규칙이다. sources.json에는 9개 원기관 계열의 URL, 자료 요청 기준과 최초 연구 입력의 SHA-256이 있다. 기관 입력과 NBER 원표의 새로운 취득은 실행 승인 범위를 별도로 확인한다. 보관 observations.csv(SHA-256 de3cd21bc1ae09c3bd003108b3dee62a1bf8c5851f45bf2580298ca5ba7068fc)와 nber.csv(76754a3e94be666491e95f94a3406abc030b6bd65a1745e04cffa48b1aed7a32)를 이 디렉터리의 작업 사본에 놓는다. 두 파일은 개인 보관 경로의 regime 디렉터리에 있다. NBER는 점수 계산 후의 기준일 비교에만 사용한다.

    python replay.py
    python ../recovery/recovery_replay.py . ./recovery-output

months-lag1/2.csv는 두 발표 지연 가정의 연구자 계산 월별 근거표, summary-lag1/2.json은 대응한 전환과 오경보의 집계다. 회복 규칙을 바꿔 본 계산이 원래 R1의 월별 구간·득표·전환 및 집계와 일치하는지 대조한 뒤 비교 결과를 낸다. 공개 경고등의 원래 성적은 상위 디렉터리의 warnings-metrics.json에 있다.
