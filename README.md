# Mate It — Dormitory Roommate Matching Service

> 기숙사 룸메이트를 **자동으로 정해주는 서비스가 아니라, 사용자가 자신의 기준으로 비교하고 선택할 수 있도록 돕는 탐색·매칭 서비스**입니다.

[Notion Portfolio ↗](https://lush-echo-8d0.notion.site/Service-Business-Planning-Portfolio-3dde2258cda6804b8c96fcae751252b9)

**Project** 2025 HUFS Engineering Academic Festival  
**Period** 2025.04–2025.12  
**Role** PM · Service Planning · Development  
**Result** Beta launch · Academic Festival Excellence Award

---

## Why this project

기숙사 룸메이트를 구할 때 생활패턴과 선호조건을 충분히 비교하기 어렵다는 문제에서 시작했습니다. 초기에는 생활패턴을 기반으로 상대를 자동 추천하는 매칭 알고리즘을 핵심으로 설계했습니다.

하지만 데모 영상을 본 약 **100명**을 대상으로 설문한 결과, 약 **70%**가 자동매칭보다 **원하는 조건을 직접 확인하고 후보를 비교·선택하는 방식**을 선호했습니다.

이 결과를 바탕으로 서비스의 중심을 `자동 결정`에서 `사용자 선택 지원`으로 전환했습니다.

## Product Decision

| Before | After |
| --- | --- |
| 알고리즘 중심 자동매칭 | 조건별 직접 탐색 중심 |
| 추천 결과가 최종 선택을 주도 | 알고리즘은 후보 추천을 보조 |
| 매칭 결과 중심 | 프로필 · 찜 · 1:1 채팅을 통한 비교와 선택 |

서비스를 만든 뒤 사용자를 설득하는 것이 아니라, **사용자의 실제 선택 기준을 확인한 뒤 구조를 수정한 경험**에 가장 큰 의미가 있습니다.

## Key Features

- 생활패턴·선호조건 기반 사용자 프로필
- 조건을 확인하며 룸메이트 후보 탐색
- 관심 프로필 저장(찜)
- 사용자 간 1:1 채팅
- 룸메이트 요청 및 수락/거절
- 학생 인증 및 계정 관리
- 후보 추천을 위한 매칭 로직

## My Contribution

PM으로 프로젝트 방향과 서비스 구조를 정리하고, 사용자 흐름과 주요 기능을 기획했습니다.

- 약 100명 대상 사용자 평가 설문 설계 및 결과 해석
- 설문 결과를 바탕으로 자동매칭 중심 구조를 직접 탐색 중심으로 재설계
- 프로필·찜·채팅·룸메이트 요청 등 핵심 사용자 흐름 설계
- 팀 역할 및 개발 일정 조율
- Django 기반 기능 개발 및 배포 과정 참여
- 약 1주간 베타 서비스 운영 및 추가 피드백 수집

## Validation & Result

베타 운영 과정에서는 다음과 같은 후속 요구를 확인했습니다.

- 매칭 기능을 더 강화했으면 좋겠다는 의견
- 학교 공식 기숙사 시스템과 연계되면 좋겠다는 의견
- 별도 시스템에서 기본정보를 다시 입력하는 과정이 번거롭다는 의견

프로젝트는 **제14회 한국외대 총장배 이공계 학술제 우수상**을 수상했습니다.

## Tech Stack

| Area | Stack |
| --- | --- |
| Backend | Django, Python |
| Database | Django ORM |
| Frontend | Django Templates, HTML, CSS, JavaScript |
| Auth | Django Authentication, student verification |
| Deployment | Procfile based deployment |
| Collaboration | Git, GitHub |

## Repository Structure

```text
mateit-roommate-matching-service/
├── config/                 # Django project settings and URL configuration
├── mateit/                 # Core domain models, forms, views, matching logic
├── templates/              # Main user-facing templates
├── utils/                  # Label / matching support modules
├── manage.py
├── requirements.txt
└── .env.example
```

> 이 저장소는 포트폴리오용 공개본입니다. 개인정보, 운영 DB, 실제 인증정보 및 배포 비밀값은 포함하지 않습니다.

## Getting Started

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

환경변수는 `.env.example`을 참고해 설정합니다.

## What I Learned

이 프로젝트를 통해 서비스기획에서 중요한 것은 처음 정한 기능을 끝까지 지키는 것이 아니라, **사용자가 실제로 무엇을 기준으로 선택하는지 검증하고 그 결과를 제품 구조에 반영하는 것**이라는 기준을 갖게 됐습니다.
