# IoT MLOps Lab

IoT 환경에서 발생하는 데이터를 수집, 처리, 추론, 관찰, 배포까지 실습하는 MLOps 프로젝트입니다.

## 구성 요소

- **simulator/** : IoT 데이터 시뮬레이터
- **iot-subscriber/** : IoT 데이터 수신 및 처리
- **inference-client/** : 모델 추론 요청 클라이언트
- **tritron-server/** : 모델 서빙 서버 (예정)
- **model/** : 머신러닝 모델 및 학습 코드
- **observability/** : 모니터링, 트레이싱, 로깅, 프로파일링 등 관찰성(Observability) 설정
- **data-pipeline/** : 데이터 파이프라인 구성 (예정)
- **compose.yaml** : 전체 서비스 Docker Compose 오케스트레이션

## 실행 방법

1. Docker 및 Docker Compose 설치
2. `docker compose up` 명령어로 전체 서비스 실행

## 목적

- IoT 데이터의 end-to-end MLOps 파이프라인 실습
- 데이터 생성 → 수집 → 추론 → 관찰(모니터링, 트레이싱, 로깅, 프로파일링 등) → 배포 자동화 경험

```bash
docker compose up --build;
```

## 서비스 접속 안내

docker compose로 실행 후 아래 사이트들에서 각종 관찰성(Observability) 및 관리 UI에 접속할 수 있습니다:

- **Grafana (관찰성 대시보드: 모니터링, 트레이싱 등):** [http://localhost:3000](http://localhost:3000)
    - 기본 계정: admin / admin
- **Prometheus (메트릭 수집):** [http://localhost:9090](http://localhost:9090)
- **Simulator (FastAPI 기반 센서 시뮬레이터):** [http://localhost:8000/docs](http://localhost:8000/docs)
    - FastAPI의 Swagger UI에서 API 테스트 및 확인 가능
- **기타 서비스**
    - 필요에 따라 inference-client 등에서 별도 웹 UI가 열릴 수 있습니다.

각 서비스의 포트는 compose.yaml에서 변경될 수 있으니, 실제 포트와 URL을 확인하세요.
