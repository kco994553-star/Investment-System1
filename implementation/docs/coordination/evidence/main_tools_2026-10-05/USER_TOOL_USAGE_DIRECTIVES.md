# Main tool usage directives — user wording preserved

These directives supplement CDR-018 at the existing checkpoint. They do not restart completed design, change owners or expand write sets/approval boundaries.

## User message — 2026-10-05 14:12 KST

> 이 지시는 기존 작업을 보완하는 도구 활용 지침이다. 현재 진행 중인 구현·테스트·게시 작업을 중단하거나 처음부터 재시작하지 마라. 현재 실행의 안전한 체크포인트 또는 다음 재개 시점부터 적용하라. 이미 완료된 작업은 도구 적용을 이유로 반복하지 말고, 필요한 도구만 선택해 사용하라. 기존 owner·write-set·D1/D2 자동진행·D3 승인 경계를 유지하라.
>
> Investment-System1의 기존 Main 통합 작업을 계속한다. 시작 시 최신 GitHub와 Global/Scoped Handoff, owner lease, 승인 범위를 확인하라.
>
> 연결된 도구는 필요한 경우에만 활용한다.
>
> - Context7: 저장소의 실제 의존성 버전에 맞는 개발 문서 확인
> - Superpowers: 현재 작업에 필요한 디버깅·검증·리뷰 절차
> - Linear: 기존 프로젝트와 이슈를 확인한 뒤 미완료 작업·담당자·dependency를 중복 없이 정리
>
> GitHub를 코드·계약·승인·검증 증거의 기준으로 유지한다. Linear 상태만으로 구현 완료나 gate 해제를 선언하지 마라. 새 도구 도입 때문에 기존 작업을 처음부터 계획하거나 재구현하지 마라.
>
> D1/D2 작업은 기존 권한대로 진행하고 실제 D3에서만 승인 요청하라. 결과는 변경사항, exact HEAD, 검증 결과, 남은 blocker, 다음 단계로 보고하라.

## User message — 2026-10-05 14:18 KST

> 추가 지침 — 도구 최초 사용
>
> 나는 GitHub 외의 도구를 이 프로젝트에서 사용한 적이 없다. 플러그인이 연결돼 있다는 이유로 해당 서비스의 프로젝트·DB·디자인·환경설정이 준비돼 있다고 가정하지 마라.
>
> 1. 현재 작업과 기존 구현을 유지하면서, 이 Work에서 실제 호출 가능한 도구와 필요한 접근 권한을 먼저 확인하라.
> 2. Context7은 저장소의 실제 라이브러리 버전에 맞는 문서 조회부터 사용하고, Superpowers는 현재 단계에 필요한 절차만 적용하라. 이미 승인·완료된 설계를 다시 시작하지 마라.
> 3. 다른 도구는 구체적인 작업에 도움이 될 때만 사용하라. 연결된 서비스의 기존 프로젝트를 최소한으로 조회하고, 대상이 불명확하면 임의로 선택하지 마라.
> 4. 최초 사용 시 ‘사용 목적·대상·읽기 또는 변경 범위’를 짧게 설명하라. 기존 D1/D2 권한으로 가능한 작업은 불필요한 재승인 없이 진행하라.
> 5. Figma와 MagicPath는 같은 화면의 중복 관리를 피하도록 하나를 주 도구로 선택하라. Linear를 사용하더라도 GitHub를 코드·계약·검증 증거의 기준으로 유지하라.
> 6. Supabase 연결을 백엔드 교체 승인으로, Vercel 연결을 배포 승인으로 해석하지 마라. 유료 자원·실제 credential·production auth·tenant 정책 변경·배포 등 기존 D3 경계를 유지하라.
> 7. 계정이나 대상 지정 때문에 막히면 필요한 사용자 행동을 한 번에 구체적으로 알려주고, 그 도구 없이 가능한 독립 작업은 계속하라.
> 8. 결과에는 실제 사용한 도구, 생성·변경한 항목의 링크, 검증 결과를 기록하라. 연결만 된 상태를 구현 완료로 보고하지 마라.

## Applied at the continuing checkpoint

- GitHub is the source of truth. Current connected repository read/write was confirmed; each ref publication uses a fresh exact parent and non-force update.
- Superpowers was applied to the existing finite PIW-D002 implementation, TDD, independent review and verification; no redesign or restart.
- Context7 resolved `/python/cpython/v3.11.14` for the existing workflow's Python 3.11 runtime. Retrieved results mixed version-pinned docs with `main` snippets; `main` snippets were not used. The exact v3.11.14 official `Doc/library/json.rst` was read through GitHub to confirm `object_pairs_hook` and `parse_constant` behavior. Local verification runtime is separately recorded as Python 3.12.14 / pytest 9.1.1; it is not reported as the CI interpreter.
- Linear read-only discovery succeeded: no projects, including archived; no Investment-System1 matching issues. The four default onboarding issues are outside this repository's scope. No project, issue, assignment or dependency graph was invented or modified. Later use requires an actual repository-associated target.
- No current Main task requires Figma/MagicPath, Supabase or Vercel, so no service project/database/design/settings target was guessed or changed. When a later scoped task needs them, discover the exact existing target and select only one design authority per screen; backend replacement/deployment remain outside this directive.
- Tool connection, configuration readback and identity consistency do not establish implementation, runtime trust, gate closure or end-to-end automatic continuation.
