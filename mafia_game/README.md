# AI 마피아 게임

LangGraph 기반 5인 마피아 게임 — 각 플레이어가 서로 다른 LLM 으로 구동됩니다.

---

## 에이전트 구성

| Agent | 이름 | 역할 | 모델 | 제공사 |
|---|---|---|---|---|
| A | Marcus | 마피아 | `mistral:latest` | Ollama (로컬) |
| B | Diana | 탐정 | `deepseek-r1:7b` | Ollama (로컬) |
| C | Alice | 시민 | `deepseek-r1:7b` | Ollama (로컬) |
| D | Bob | 시민 | `deepseek-r1:7b` | Ollama (로컬) |
| E | Charlie | 시민 | `mistral:latest` | Ollama (로컬) |

---

## 게임 규칙

- **시민 팀 승리** : 투표로 마피아(Marcus)를 탈락시키면 승리
- **마피아 승리** : 생존 마피아 수 ≥ 생존 시민 수가 되면 승리
- **최대 6라운드** 진행 후 자동 종료

### 라운드 진행 순서

```
① 낮 — 토론
   각 플레이어 LLM 이 순서대로 발언 생성 (이전 발언 누적 컨텍스트 참고)

② 낮 — 투표
   각 플레이어 LLM 이 가장 의심되는 플레이어 투표
   최다 득표자 탈락

③ 승리 판정
   → 마피아 탈락 시 시민 승리 / 마피아 수 ≥ 시민 수 이면 마피아 승리

④ 밤 — 마피아 제거
   Marcus(mistral) 가 탐정(Diana) 우선 타깃 선택

⑤ 승리 판정 후 ① 로 반복
```

---

## 사전 준비

### 1. 관측성 스택 실행 (토큰 모니터링용)

```bat
cd D:\devops\workspace
docker compose up -d
```

### 2. Ollama 모델 확인

```bat
ollama list
```

목록에 없으면 다운로드:

```bat
ollama pull mistral:latest
ollama pull deepseek-r1:7b
```

---

## 설치 및 실행

### 1. 가상환경 생성

```bat
cd D:\devops\workspace\mafia_game
python -m venv .venv
```

> `python` 명령이 없으면 `py -m venv .venv` 로 시도

### 2. 가상환경 활성화

```bat
.venv\Scripts\activate
```

성공 시 터미널 앞에 `(.venv)` 가 표시됩니다:

```
(.venv) D:\devops\workspace\mafia_game>
```

### 3. 패키지 설치

```bat
pip install -r requirements.txt
```

### 4. 게임 실행

```bat
python main.py
```

---

## 환경변수

`.env` 파일에 아래 항목이 설정되어 있어야 합니다:

```dotenv
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
GOOGLE_API_KEY=your-google-api-key-here
```

`.env.example` 을 복사해서 사용:

```bat
copy .env.example .env
```

---

## 토큰 모니터링

게임 실행 중/후 아래 대시보드에서 토큰 사용량을 확인할 수 있습니다.

| 확인 항목 | URL | 계정 |
|---|---|---|
| LLM 트레이스 · 토큰 상세 | http://localhost:3000 | user@openlit.io / openlituser |
| 메트릭 대시보드 (Grafana) | http://localhost:3001 | admin / admin |
| 로그 탐색 (Kibana) | http://localhost:5601 | — |

### 라운드당 LLM 호출 횟수

| 단계 | 호출 수 |
|---|---|
| 낮 발언 | 최대 5회 (생존자 수) |
| 투표 결정 | 최대 5회 |
| 야간 타깃 선택 | 1회 |
| **합계** | **최대 11회 / 라운드** |

라운드가 쌓일수록 대화 컨텍스트가 누적되어 토큰이 점진적으로 증가하는 패턴을 OpenLit 에서 확인할 수 있습니다.

---

## 파일 구조

```
mafia_game/
├── main.py                  ← 실행 진입점
├── requirements.txt
├── .env                     ← API 키 (git 커밋 금지)
├── .env.example             ← 환경변수 샘플
└── game/
    ├── state.py             ← GameState 정의
    ├── agents.py            ← LLM 에이전트 (발언·투표·야간)
    ├── nodes.py             ← 게임 로직 노드
    └── graph.py             ← LangGraph 그래프 조립
```
