# MCP Core Orchestrator

FastAPI 기반 MCP Core는 사용자가 업로드한 GitHub 레포지토리의 실행 정보를 분석해 `/plans` 응답으로 서비스별 CPU·Memory 사용량을 예측해 전달한다. 컨텍스트 구조화 → 서비스 라우팅 → 예측 엔진(LSTM/Baseline) 실행 → 정책 후처리 → 이상 알림 순으로 파이프라인이 구성된다.

---

## 1. 전체 처리 흐름
1. 클라이언트가 `/plans` 엔드포인트로 예측 요청을 전송한다.  
2. `context_extractor`가 `context` JSON을 `MCPContext` 모델로 검증한다.  
3. `router`가 서비스 타입·런타임 환경을 기준으로 모델 버전을 선택한다.  
4. `predictor`가 선택된 엔진(LSTM 또는 Baseline)으로 24시간 시계열을 생성한다.  
5. `policy`가 가중치·클램프·이상 탐지·Discord 알림을 적용한다.  
6. `/plans` 응답으로 예측 결과, 권장 플래이버, 예상 비용을 반환한다.  

> `/plans` 응답 스키마는 배포 파이프라인과의 계약으로 간주되므로 임의 변경을 지양한다.

---

## 2. 데이터 파이프라인 및 메타데이터
- 원본 CSV: `data/lstm_ready_cluster_data.csv` (1,439행 × 84컬럼)  
- 모델: `models/best_mcp_lstm_model.h5`  
- 메타데이터: `models/mcp_model_metadata.pkl`  
  * `sequence_length = 24` (24시간 윈도우)  
  * `feature_names` 82개, `scaler`, `target_scaler`, `use_log_transform` 플래그 포함  
- lookback 길이를 변경할 경우 노트북/스크립트에서 재학습하여 모델·메타데이터·CSV를 동시에 업데이트해야 한다.

---

## 3. 데이터 전처리 규칙
### 3.1 결측치 처리 대응
- **Feature 컬럼**: forward-fill 후 남은 값은 0으로 채운다.  
- **Target 컬럼**: 음수 값은 0으로 클리핑하고, 로그 변환(`log1p`) 적용 시 결측 처리 규칙을 동일하게 따른다.

### 3.2 이상치 처리 규칙
- 학습 스크립트(`train_from_notebook.py`)에서 **IQR 기반 Winsorize** 적용:  
  * 1사분위(Q1)와 3사분위(Q3)를 이용해 IQR을 계산  
  * 하한 = Q1 - 3×IQR, 상한 = Q3 + 3×IQR  
  * 범위를 벗어난 값은 하한/상한으로 클램프  
- 서빙 단계에서는 `policy`에서 예측값을 0~1 사이로 clamp(정규화된 지표 기준)하고, 이상 탐지는 Z-score 기반으로 수행한다.

### 3.3 평균 보간 및 Winsorize
- 일부 보조 지표(예: 평균 CPU)에서 짧은 구간이 비어 있을 경우 forward-fill과 0 보간을 조합한다.  
- 극단값 처리를 위해 상·하한을 이동 평균 기반으로 다듬는 경우 추가 Winsorize(5%/95%)를 선택적으로 적용한다. 이는 노트북 실험 시 파라미터로 조정 가능하다.

---

## 4. 디렉터리 구조 (요약)
```
app/
  core/
    context_extractor.py   # 컨텍스트 → MCPContext 변환
    router.py              # 서비스 라우팅
    policy.py              # 가중치/클램프/이상 탐지/Discord 알림
    predictor/
      base.py              # Predictor 추상 클래스
      baseline_predictor.py# 통계 기반 + 폴백
      lstm_predictor.py    # LSTM 예측 엔진
      data_sources/
        base.py            # 데이터 소스 추상화
        csv_source.py      # CSV 데이터 소스
        mysql_source.py    # SQLAlchemy 기반 MySQL 데이터 소스
        factory.py         # 환경 변수로 데이터 소스 선택
  routes/plans.py          # /plans 라우터
models/                    # 학습된 모델 및 메타데이터
data/                      # 예측 입력 CSV
docs/operations_update.md  # 작업 이력 및 운영 가이드
```

---

## 5. 데이터 소스 전환
### CSV (기본값)
```
DATA_SOURCE_BACKEND=csv
CSV_DATA_PATH=data/lstm_ready_cluster_data.csv
```

### MySQL (SQLAlchemy + PyMySQL)
```
DATA_SOURCE_BACKEND=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=mcp_user
MYSQL_PASSWORD=secret
MYSQL_DATABASE=mcp_core
MYSQL_TABLE=metric_history
# MYSQL_SSL_CA=/path/to/ca.pem
```
- `mysql+pymysql://` 스킴을 사용하며 `PyMySQL`, `SQLAlchemy` 설치가 필요하다.  
- `metric_history` 테이블 스키마는 다음과 같다.
  ```sql
  CREATE TABLE metric_history (
      service_id   VARCHAR(128),
      metric_name  VARCHAR(128),
      ts           DATETIME,
      value        DOUBLE,
      PRIMARY KEY (service_id, metric_name, ts)
  );
  ```
- 조회 결과가 부족하면 가장 오래된 값을 복제해 길이를 맞춘다.

---

## 6. 예측 엔진
| 엔진 | 위치 | 특징 |
|------|------|------|
| `LSTMPredictor` | `app/core/predictor/lstm_predictor.py` | TensorFlow 모델 로드, 메타데이터 기반 스케일링 |
| `BaselinePredictor` | `app/core/predictor/baseline_predictor.py` | 최근 24시간 통계 + 폴백 시나리오 |

`policy` 단계에서 두 엔진 모두 컨텍스트 가중치 및 이상 탐지 처리를 거친 뒤 `/plans` 응답으로 전달된다.

---

## 7. 이상 탐지 및 알림
- `app/core/anomaly.py`: 최근 168시간을 기준으로 z-score를 계산해 이상 여부를 판단한다.  
- `policy`가 이상을 감지하면 비동기 스레드로 Discord 알림을 전송한다.  
- 환경 변수:  
  * `DISCORD_WEBHOOK_URL` (필수)  
  * `DISCORD_BOT_NAME` (기본값 `MCP-dangerous`)  
  * `DISCORD_BOT_AVATAR` (기본값 `https://i.imgur.com/9kY5F5k.png`)  
- 스크립트 테스트 시 비동기 스레드가 완료될 수 있도록 `time.sleep()` 등으로 약간의 대기 시간을 준다.

---

## 8. 환경 변수 예시 (.env)
```bash
# 데이터 소스
DATA_SOURCE_BACKEND=csv
CSV_DATA_PATH=data/lstm_ready_cluster_data.csv
# MYSQL_HOST=...
# MYSQL_USER=...
# MYSQL_PASSWORD=...
# MYSQL_DATABASE=...
# MYSQL_TABLE=metric_history

# 모델 및 알림 설정
DISCORD_WEBHOOK_URL=...
DISCORD_BOT_NAME=MCP-dangerous
DISCORD_BOT_AVATAR=https://i.imgur.com/9kY5F5k.png
ANOMALY_Z=3.0
```

---

## 9. 모델 학습 스크립트 (`train_from_notebook.py`)
- 노트북을 스크립트화하며 다음을 반영했다.
  1. 스케일러를 train 데이터로만 학습시켜 데이터 누수를 방지.  
  2. 결측치는 forward-fill 후 0으로 채워 미래 데이터를 사용하지 않음.  
  3. 체크포인트와 모델, 메타데이터를 모두 `models/`에 저장.  
  4. CLI 인자를 통해 CSV 경로, 시퀀스 길이, 학습 epoch 등을 조정.  
- 실행 예시
  ```bash
  python app/core/predictor/train_from_notebook.py \
    --csv-path data/lstm_ready_cluster_data.csv \
    --sequence-length 24 \
    --epochs 80 \
    --batch-size 32
  ```
- 학습 후 `models/best_mcp_lstm_model.h5`와 `models/mcp_model_metadata.pkl`이 갱신되어 서빙과 바로 호환된다.

---

## 10. 테스트 및 검증
1. **Discord 연동 확인**  
   ```bash
   export PYTHONPATH=$PWD
   export DISCORD_WEBHOOK_URL=...
   python tests/discord_test.py
   ```
2. **이상 탐지 시뮬레이션**  
   - 예측 범위를 인위적으로 높여 `postprocess_predictions` 호출 시 알림이 도착하는지 확인.  
3. **데이터 소스 점검**  
   - CSV: 파일 경로와 권한 확인.  
   - MySQL: `MySQLDataSource.is_available()` 호출 또는 CLI로 접속 테스트.

---

## 11. 향후 개선 제안
1. `tests/anomaly_check.py`에 알림 전송 완료까지 대기하는 로직 추가.  
2. Discord 응답 로그를 중앙 모니터링 시스템(CloudWatch, Prometheus 등)과 연동.  
3. lookback을 168시간으로 확장할 필요가 생기면 노트북에서 재학습 후 산출물 일괄 갱신.

---

## 12. 사용자 인증 및 관리 (User Authentication)

MCP Core는 사용자 관리 및 클라우드 계정 통합을 위한 MySQL 기반 인증 시스템을 제공한다.

### 12.1 데이터베이스 스키마
- **위치**: `database/schemas/001_users_authentication.sql`
- **주요 테이블**:
  - `users`: 사용자 정보, 인증, 클라우드 계정 통합
  - `user_sessions`: 세션 관리
  - `password_reset_tokens`: 비밀번호 재설정
  - `email_verification_tokens`: 이메일 인증
  - `user_audit_log`: 감사 로그

### 12.2 지원 클라우드 제공자
- AWS, Azure, GCP, Alibaba Cloud, Oracle Cloud, IBM Cloud

### 12.3 초기 설정
```bash
# 환경 변수 설정
export MYSQL_HOST=localhost
export MYSQL_USER=mcp_user
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=mcp_core

# 스키마 초기화
python database/init_db.py
```

### 12.4 보안 기능
- 비밀번호 해싱 (bcrypt/argon2)
- API 키 관리
- 2단계 인증 (TOTP)
- 세션 관리
- 감사 로그

자세한 내용은 `database/README.md`를 참조한다.

---

## 13. 참고 문서
- `docs/operations_update.md`  
- `demoMCPproject.ipynb`
- `database/README.md` (사용자 관리)

---
