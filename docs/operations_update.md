# MCP Core 업데이트 정리

## 작업 범위
- `/plans` 예측 파이프라인의 컨텍스트 처리, 예측기 초기화, 이상 탐지 알림 전송 경로를 점검하고 개선했습니다.
- Discord 웹훅을 이용한 모니터링 알림을 MCP-dangerous 봇으로 통합했습니다.
- 모델 메타데이터(lookback 24h)와 관련된 문서를 최신화했습니다.

---

## 주요 코드 변경
### 컨텍스트 처리
- `app/core/context_extractor.py`
  - `MCPContext(**raw_context)`로 수정하여 요청 컨텍스트가 정상적으로 검증·로딩되도록 함.

### 예측기 초기화 로그
- `app/core/predictor/baseline_predictor.py`
- `app/core/predictor/lstm_predictor.py`
  - Windows 콘솔 인코딩 오류를 유발하던 이모지를 제거하고 `[info]/[warn]/[debug]/[error]` 포맷으로 로그 정리.

### Discord 웹훅 확장
- `app/core/alerts/discord_alert.py`
  - `send_discord_alert`에 `username`, `avatar_url` 파라미터 추가.
  - 웹훅 URL이 없을 때는 페이로드를 콘솔에 로깅하고 종료.
- `app/core/policy.py`
  - 이상 탐지 시 MCP-dangerous 톤의 메시지를 전송하도록 페이로드 구성.
  - `DISCORD_BOT_NAME`, `DISCORD_BOT_AVATAR` 환경변수로 봇 프로필 커스터마이징 가능.
  - 알림 스레드는 비동기이므로 테스트 스크립트에서는 `sleep` 등을 통해 전송 완료를 보장해야 함.

### 문서 업데이트
- `read1.md`
  - 메타데이터 `sequence_length = 24`, 82개 피처 등 현행 설정을 명시.
  - lookback 변경 시 재학습·재배포 필요성을 안내.
- 데이터 소스 전환 문서화: `DATA_SOURCE_BACKEND`(csv/mysql)과 `MYSQL_*` 환경 변수 세팅 방법 추가.

---

## 테스트 & 검증
1. `PYTHONPATH`를 `c:/Users/wjdwl/mcp_core`로 지정 후 `tests/discord_test.py` 실행 → HTTP 204 응답 확인.
2. `postprocess_predictions`에 고정된 고부하 시퀀스를 입력해 이상 탐지 → MCP-dangerous 봇이 채널에 메시지 전송.  
   - 단발성 스크립트 실행 시에는 `time.sleep(3)` 정도로 스레드 완료를 기다려야 알림이 누락되지 않음.

---

## 운영 시 참고 사항
- 필수 환경변수  
  - `DISCORD_WEBHOOK_URL`: 배포 환경의 Discord 채널 웹훅  
  - `ANOMALY_Z`: 이상 탐지 z-score 임계값 (기본 3.0)
- 데이터 백엔드  
  - `DATA_SOURCE_BACKEND`: `csv`(기본) 또는 `mysql`  
  - MySQL 선택 시 `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_TABLE`, `MYSQL_SSL_CA`(선택) 필요
- 의존성  
  - CSV 경로만 사용할 경우 기본 requirements로 충분  
  - MySQL 경로를 사용할 경우 `PyMySQL`과 `SQLAlchemy`가 사전 설치되어 있어야 하며, 커넥션 문자열은 `mysql+pymysql://` 스킴을 따른다
- 선택 환경변수  
  - `DISCORD_BOT_NAME`(기본 `MCP-dangerous`)  
  - `DISCORD_BOT_AVATAR`(기본 `https://i.imgur.com/9kY5F5k.png`)
- 모델 재학습 시에는 `models/*.h5`, `models/mcp_model_metadata.pkl`, `data/lstm_ready_cluster_data.csv`를 동일 시점으로 유지해야 서빙과 일관성 확보.

---

## 후속 제안
1. 테스트 스크립트(`tests/anomaly_check.py`)에 전송 대기 로직을 추가하여 자동 테스트 안정성 확보.
2. Discord 응답 상태를 로그/모니터링 시스템에 통합해 알림 실패 시 추적 가능하도록 개선.
3. lookback 168h 요건이 재도입될 경우, demoMCP 노트북에서 재학습 후 산출물 전체를 갱신.
