# Eve's Apple — 제출용 소개문

## 서비스 명

**Eve's Apple**
EVE — Evidence Verification Engine
*Take a bite. Know what's real.*

## Problem Definition

정치·광고 콘텐츠의 문제는 단순한 거짓말만이 아니다. 숫자는 존재하지만 적용 대상과 기간이 빠져 있거나, 연구는 존재하지만 광고 제품과 정확히 일치하지 않거나, 2차 출처가 원 연구의 한정 조건을 반복 과정에서 잃어버리는 경우가 많다. 사용자는 긴 출처 목록보다 “어떤 부분이 직접 검증됐고, 무엇이 아직 불명확한가”를 알고 싶다. 그러나 이를 매번 원출처까지 추적하고 반대·제한 근거를 함께 읽기는 어렵다.

## Solution

EVE는 사용자의 정치 또는 광고 텍스트에서 검증 가능한 factual claim을 추출하고, 이를 Evidence Requirement로 분해하는 증거 조사 에이전트다. Nemotron이 claim과 필요한 검증 조건을 구조화하고, Evidence Memory가 중요 수치·기간이 호환되는 기존 조사를 보수적으로 재사용한다. 캐시가 없으면 AI-Q shallow research가 원 연구·공식 자료·제한 근거를 탐색하며, Evidence Synthesizer가 출처와 provenance를 정리한다. 이어 Nemotron Evidence Judge가 각 requirement의 직접 근거 여부를 평가한다. Python state machine은 최대 두 번의 AI-Q job과 한 번의 targeted retry만 허용하고, 근거가 충분하거나 예산이 소진되면 종료한다. 결과는 TRUE/FALSE가 아니라 CONFIRMED, MISSING_CONTEXT, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE, UNVERIFIED로 표현한다.

## Tech Stack / NVIDIA technologies actually used

- FastAPI + React/Vite + SQLite Evidence Memory
- NVIDIA Nemotron hosted API: claim extraction, evidence requirement planning, evidence judgment
- NVIDIA AI-Q / Agent Skills: `shallow_researcher` 기반 source research
- NVIDIA OpenShell: Evidence Hunter의 least-privilege runtime boundary
- Cloudflare Tunnel: loopback-only EVE public entry

NemoClaw은 active runtime으로 사용하지 않는다. 설치 호환성 검토 중 validated OpenShell 0.1.1과 요구 버전이 달라, 동작 중인 보안 runtime을 다운그레이드하지 않기로 결정했다.

## Demo URL

https://evesapple.kr

## GitHub URL

https://github.com/modelerSy/evesapple
