# 원자료 비공개 보관 절차 (2026-10-11 사용자 결정)

대상: Track A 원자료 archive `c21-raw-store-36305927245.zip` — Actions artifact 10927496280, 451,439,890 bytes, sha256 `712e43bcc1fcd137e5e99ccdda2440850eda56015e02037293d8eac8db399f94`, **2026-12-26T08:21:15Z 만료**. 같은 비공개 저장소를 SEC 504 다일 raw에도 쓴다.

## 1. 사용자가 할 일 (한 번)

1. 새 저장소 만들기: GitHub → New repository
   - Owner `kco994553-star`, 이름 **`investment-system1-raw`**
   - **Private**
   - "Add a README file" 체크(릴리스 태그를 달 첫 커밋이 필요)
   - .gitignore·license 없음
2. 토큰 만들기: Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate
   - Token name `investment-system1-raw-writer`, Expiration 1년(만료 전 갱신)
   - Resource owner `kco994553-star`, Repository access **Only select repositories → `investment-system1-raw`만**
   - Permissions → Repository permissions → **Contents: Read and write** (Metadata: Read는 자동)
   - 그 외 권한 없음
3. 토큰 등록: `Investment-System1` 저장소 → Settings → Secrets and variables → Actions → New repository secret
   - Name **`RAW_REPO_TOKEN`**, Value = 위 토큰. 다른 곳에 붙여 넣지 않는다.
4. 알려 주기: "저장소·토큰 등록 완료"라고만 알려 주면 된다(값은 보내지 않는다).

## 2. 실행 (개발자, 알림 후)

`raw-store-private-release` 워크플로를 `upload=true`로 수동 실행한다.

1. 원본 artifact 다운로드 → sha256 대조 → 압축 해제 → `raw_artifact_restore_check.py`(verify_blobs, manifest_set_sha256) PASS 확인
2. 비공개 저장소 릴리스 `raw-c21-store-36305927245`에 zip과 `.sha256` 업로드(이미 있으면 덮어쓰지 않음, 크기가 다르면 중단)
3. 릴리스에서 다시 다운로드 → sha256 대조 → 압축 해제 → verify_blobs **6808/6808 PASS** 재확인
4. 실행 요약에 출력된 `storage_locations` 항목을 `implementation/reports/raw_persistence/storage_locations_<date>.json`에 기록하는 PR → retention 판정이 `DURABLE_COPY_PRESENT`가 되는지 확인

로그에는 개수·크기·sha256만 남고 토큰·원자료 내용·가격은 출력하지 않는다. 기존 Actions artifact는 만료까지 그대로 둔다(삭제는 별도 결정).

## 3. 복원 방법

비공개 릴리스에서 zip을 받아 sha256을 위 값과 대조 → 압축 해제 → `python implementation/tools/raw_artifact_restore_check.py --archive <zip> --expected-sha <sha> --restored <dir> --out check.json` → `blob_verification.status == PASS`, 6808/6808.
