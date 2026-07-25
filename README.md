# Spring Boot 학습 가이드 (Kotlin)

[![Live Site](https://img.shields.io/badge/Live-namja.github.io-6DB33F?style=flat-square&logo=githubpages&logoColor=white)](https://namja.github.io/Spring-Boot-Learning-Guide/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.1.0-6DB33F?style=flat-square&logo=springboot&logoColor=white)](https://docs.spring.io/spring-boot/index.html)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.3.21-7F52FF?style=flat-square&logo=kotlin&logoColor=white)](https://kotlinlang.org/)

Kotlin 개발자를 위한 Spring Boot 4 실습형 입문 가이드입니다. **문서는 아래 사이트에서 읽어 주세요.**

👉 **<https://namja.github.io/Spring-Boot-Learning-Guide/>**

이 저장소는 그 사이트의 소스입니다.

## 저장소 구조

| 경로 | 설명 |
| --- | --- |
| `src/**/*.html` | **편집 대상.** 페이지 본문 HTML 조각 (`<h1>`부터 시작, 셸·내비게이션 없음) |
| `src/_nav.html` | 사이드바 내비게이션 트리 (루트 기준 링크) |
| `tools/build_site.py` | 생성기 — 셸 래핑 + 코드 하이라이팅 + 목차 생성 → `docs/` |
| `tools/verify_site.py` | 링크·앵커·CSS 클래스·JS 훅 검증기 |
| `tools/assets/` | `base.css`(레이아웃) · `diagrams.css`(도식 컴포넌트) · `app.js`(인터랙션) |
| `docs/` | **생성물.** GitHub Pages가 이 폴더를 그대로 서빙합니다. 직접 수정하지 마세요 |

마크다운은 2026-07에 은퇴했습니다. ASCII 아트로는 도식 표현에 한계가 있어, 본문·도식 모두 HTML/CSS로 직접 조립하는 방식으로 옮겼습니다.

## 빌드

```bash
python3 -m venv .venv && . .venv/bin/activate   # 처음 한 번
pip install pygments                            # 처음 한 번

python tools/build_site.py     # src/ → docs/ (68페이지 + assets)
python tools/verify_site.py    # 링크·기능 검증 (실패 시 exit 1)

python3 -m http.server 3000 --directory docs    # 로컬 확인
```

작성 규칙(코드블록·콜아웃·도식 컴포넌트·탭)은 [`CLAUDE.md`](CLAUDE.md)에 정리해 두었습니다.

## 라이선스

문서와 예제 코드는 학습 목적으로 자유롭게 참고하셔도 됩니다.
