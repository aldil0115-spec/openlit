# Observability Stack

OpenLit + Elasticsearch + Kibana + Prometheus + Grafana 통합 관측성 스택

---

## 아키텍처

```
앱 (OTLP)
    │
    ▼
외부 OTel Collector  :4317 (gRPC) / :4318 (HTTP)
    ├── OTLP ──► OpenLit :3000  ──► ClickHouse   (LLM 트레이스/메트릭)
    ├── ──────► Elasticsearch :9200 ◄── Kibana :5601  (로그/트레이스 탐색)
    └── :8889 ◄── Prometheus :9090 ◄── Grafana :3001  (메트릭 대시보드)
```

---

## 서비스 포트

| 서비스 | 호스트 포트 | 접속 URL |
|---|---|---|
| OpenLit UI | 3000 | http://localhost:3000 |
| OTel Collector (gRPC) | 4317 | — |
| OTel Collector (HTTP) | 4318 | — |
| Elasticsearch | 9200 | http://localhost:9200 |
| Kibana | 5601 | http://localhost:5601 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3001 | http://localhost:3001 |
| ClickHouse HTTP | 8123 | http://localhost:8123 |

---

## 기본 계정 정보

| 서비스 | ID | PW |
|---|---|---|
| OpenLit | user@openlit.io | openlituser |
| Grafana | admin | admin |
| ClickHouse | default | OPENLIT |

---

## 파일 구조

```
workspace/
├── docker-compose.yml
├── .env                             ← (선택) 환경변수 오버라이드
├── assets/                          ← OpenLit 공식 설정
│   ├── clickhouse-config.xml        ← ClickHouse 로그/성능 튜닝
│   ├── clickhouse-init.sh           ← OTel 테이블 초기화 스크립트
│   └── otel-collector-config.yaml   ← OpenLit 내장 collector (ClickHouse 전용)
├── otel-collector/
│   └── config.yaml                  ← 외부 collector (ES + Prometheus 팬아웃)
├── prometheus/
│   └── prometheus.yml               ← 스크레이프 설정
└── grafana/
    └── provisioning/datasources/
        └── datasources.yml          ← Prometheus + ES 데이터소스 자동 등록
```

---

## 실행

### 1. 전체 시작

```bash
docker compose up -d
```

> ClickHouse 초기화에 약 30~60초 소요됩니다. OpenLit 은 ClickHouse 헬스체크 통과 후 자동 시작됩니다.

### 2. 상태 확인

```bash
docker compose ps
```

모든 서비스가 `running (healthy)` 상태여야 합니다.

### 3. 로그 확인

```bash
# 전체 로그
docker compose logs -f

# 서비스별 로그
docker compose logs -f clickhouse
docker compose logs -f openlit
docker compose logs -f otel-collector
docker compose logs -f elasticsearch
```

### 4. 전체 종료

```bash
docker compose down
```

### 5. 데이터 포함 완전 초기화 (볼륨 삭제)

```bash
docker compose down -v
```

---

## 환경변수 커스터마이징

루트에 `.env` 파일을 생성하면 기본값을 덮어쓸 수 있습니다.

```dotenv
# .env 예시
OPENLIT_DB_PASSWORD=mypassword
OPENLIT_DB_NAME=openlit
OPENLIT_DB_USER=default
PORT=3000
```

---

## 앱 연동 방법

애플리케이션의 OTLP exporter 엔드포인트를 외부 OTel Collector 로 지정합니다.

**gRPC (권장)**
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

**HTTP**
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

### Python 예시 (openlit SDK)

```python
import openlit

openlit.init(
    otlp_endpoint="http://localhost:4318",
    application="my-app",
    environment="production"
)
```

---

## 각 서비스 활용 가이드

### OpenLit (http://localhost:3000)
- LLM 호출 트레이스, 토큰 사용량, 비용 분석
- OpenAI / Anthropic / Bedrock 등 자동 계측 지원

### Kibana (http://localhost:5601)
- 인덱스 패턴 등록: `otel-traces`, `otel-logs`
- **Stack Management → Index Patterns → Create** 에서 등록 후 Discover 에서 탐색

### Grafana (http://localhost:3001)
- Prometheus, Elasticsearch 데이터소스 자동 등록됨
- **Connections → Data sources** 에서 확인 가능

### Prometheus (http://localhost:9090)
- OTel Collector 메트릭 스크레이프 (`otel-collector:8889`)
- **Status → Targets** 에서 수집 상태 확인

---

## 예제 앱 — AI 마피아 게임

LangGraph 2-Agent 기반 마피아 게임으로 토큰 모니터링을 체험할 수 있습니다.

### 구조

```
Marcus (마피아 Agent A)  ←── LangGraph ──►  Diana (탐정 Agent B)
      거짓 진술 생성                              발언 분석 + 마피아 추리
            │                                          │
            └──────────► OpenLit 토큰 추적 ◄───────────┘
```

### 실행

```bash
cd mafia_game

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 에 OPENAI_API_KEY 입력

# 게임 실행
python main.py
```

### 토큰 모니터링 포인트

| 확인 항목 | 확인 위치 |
|---|---|
| 라운드별 Agent 토큰 소비량 | OpenLit → Traces |
| Marcus vs Diana 토큰 비교 | OpenLit → Dashboard |
| 누적 토큰 시계열 그래프 | Grafana → Prometheus |
| 전체 대화 로그 | Kibana → otel-logs |

---

## 문제 해결

### ClickHouse 연결 실패
```bash
docker compose logs clickhouse | grep -i "error\|init"
```
볼륨에 구버전 데이터가 남아 있는 경우:
```bash
docker compose down -v && docker compose up -d
```

### OpenLit 로그인 불가
```bash
docker compose logs openlit | grep -i "error\|db\|clickhouse"
```

### Elasticsearch 기동 지연
메모리 부족 시 `ES_JAVA_OPTS` 조정 (`docker-compose.yml` > elasticsearch):
```yaml
ES_JAVA_OPTS=-Xms256m -Xmx256m
```

### OTel Collector 헬스체크
```bash
curl http://localhost:13133/
```
