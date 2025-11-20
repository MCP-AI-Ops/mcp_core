# MCP Core 전체 데이터 흐름 문서

## 1. 전체 아키텍처 개요

```
[프론트엔드: mcp_web]
    ↓ (사용자 입력: GitHub URL, 요청사항)
[백엔드: mcp_core]
    ↓ (Context 추출, 모델 선택, 예측)
[MySQL/CSV: feature 데이터 소스]
    ↓ (LSTM feature_names 전체 시계열 조회)
[LSTM/Baseline Predictor]
    ↓ (24시간 예측 생성)
[Policy & Flavor 추천]
    ↓ (인스턴스 스펙, 비용 산출)
[응답: PlansResponse]
    ↓ (프론트엔드에 반환)
[CI/CD 배포 자동화]
```

## 2. 프론트엔드(mcp_web) → 백엔드(mcp_core) 데이터 흐름

### 2.1 프론트엔드 구조
- **기술 스택**: React 18 + TypeScript, Vite, Tailwind CSS, shadcn/ui
- **라우팅**: React Router v6
- **상태 관리**: Context API (AuthContext) + TanStack Query
- **배포**: Vercel

### 2.2 주요 페이지 및 컴포넌트
- **Login/Signup** (`src/pages/Login.tsx`, `src/pages/Signup.tsx`): 인증
- **Predict** (`src/pages/Predict.tsx`): 대시보드, 프로젝트 생성 다이얼로그
- **Projects** (`src/pages/Projects.tsx`): 프로젝트 목록, 상세, 삭제
- **Settings** (`src/pages/Settings.tsx`): 사용자 설정, 알림, API 키
- **CreateProjectDialog** (`src/components/CreateProjectDialog.tsx`): GitHub URL, 사용자 수, 요청사항 입력

### 2.3 API 클라이언트
- **authAPI.ts**: `/auth/login`, `/auth/signup`, `/auth/profile` 등 인증 API
- **mcpAPI.ts**: `/plans`, `/deploy`, `/destroy`, `/projects` 등 MCP Core API
- **config.ts**: `API_BASE_URL` (8000 포트), `DEPLOY_API_BASE_URL` (8001 포트)

### 2.4 사용자 입력 → 백엔드 전송 흐름

#### 단계 1: 프로젝트 생성 (프론트엔드)
사용자가 "Create New Project" 버튼 클릭 → `CreateProjectDialog` 표시
- **입력 필드**:
  - `github_repo_url`: GitHub 저장소 URL (필수)
  - `expected_users`: 예상 사용자 수 (기본값: 100)
  - `requirements`: 자연어 요청사항 (선택, 예: "피크 시간대 스케일 업 필요")

#### 단계 2: Context JSON 생성 (프론트엔드)
```typescript
// src/pages/Predict.tsx의 handleCreateProject()
const context = {
  github_url: projectData.github_repo_url, // 필수
  // 나머지 필드(timestamp, service_type, runtime_env, time_slot, weight 등)는 백엔드가 채움
}

const payload = {
  service_id: `svc-${Date.now()}`,
  metric_name: "cpu_usage", // 기본값: total_events, cpu_usage 등
  context: context,
  requirements: projectData.requirements, // 자연어 요청사항
}
```

#### 단계 3: 백엔드 API 호출 (프론트엔드)
```typescript
// src/lib/mcpAPI.ts의 sendContextToMCP()
const res = await fetch(`${API_BASE_URL}/plans`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(payload)
});
```

## 3. 백엔드(mcp_core) 데이터 처리 흐름

### 3.1 엔드포인트: POST /plans

#### 단계 1: 요청 수신 및 Context 추출
```python
# app/routes/plans.py
@router.post("", response_model=PlansResponse)
def make_plan(req: PlansRequest):
    # 1. Context 추출 및 검증
    ctx = extract_context(req.context.model_dump())
    # MCPContext로 변환: timestamp, service_type, runtime_env, time_slot, weight, expected_users 등
```

**Context 필드**:
- `github_url`: 서비스 식별자 (필수)
- `timestamp`: 요청 시각 (UTC)
- `service_type`: web, api, db 중 하나 (기본값: web)
- `runtime_env`: prod, dev 중 하나 (기본값: prod)
- `time_slot`: peak, normal, low, weekend 중 하나 (기본값: normal)
- `weight`: 가중치 (기본값: 1.0)
- `expected_users`: 예상 사용자 수 (기본값: 1000)
- `region`: 배포 지역 (선택)
- `curr_cpu`, `curr_mem`: 현재 리소스 사용량 (선택)

#### 단계 2: 모델 버전 선택 (Router)
```python
# app/core/router.py
model_version, path = select_route(ctx)
# 예: "web_normal_v1", "lstm_web_peak_v2" 등
```

**라우팅 규칙**:
- Context의 `service_type`, `time_slot`, `runtime_env` 등을 기반으로 모델 버전 결정
- "lstm"이 포함된 모델 → LSTM Predictor
- 그 외 → Baseline Predictor (평균, 이동평균 등)

#### 단계 3: 데이터 소스에서 feature 조회
```python
# app/core/predictor/lstm_predictor.py
# CSV 데이터 소스 (현재)
recent_df = self.df.tail(self.sequence_length)  # 최근 24시간 (sequence_length)
recent_data = recent_df[self.feature_names].values  # feature_names 전체 컬럼 추출

# MySQL 데이터 소스 (향후)
# app/core/predictor/data_sources/mysql_source.py
# SELECT ts, value FROM metric_history
# WHERE github_url = :github_url
#   AND metric_name = :metric_name
#   AND ts BETWEEN :start_ts AND :end_ts
# ORDER BY ts ASC
```

**필수 feature_names** (LSTM 모델):
- 원본 feature: `unique_machines`, `add_events`, `remove_events`, `update_events`, `avg_cpu`, `avg_memory`, `std_cpu`, `std_memory`, `min_cpu`, `max_cpu`, `min_memory`, `max_memory`, `unique_switches`, `unique_platforms`
- 시간 feature: `hour_of_day`, `day_of_week`, `day_of_month`, `hour_sin`, `hour_cos`, `day_sin`, `day_cos`
- Lag feature: `lag1_events`, `lag1_machines`, `lag1_cpu`, ..., `lag24_cpu`
- Moving Average: `ma3_events`, `ma3_machines`, `ma3_cpu`, ..., `ma48_cpu`
- Rolling Stats: `roll12_std`, `roll12_max`, `roll12_min`, `roll24_std`, `roll24_max`, `roll24_min`
- Change feature: `pct_change_1h`, `pct_change_6h`, `pct_change_24h`, `diff_1h`, `diff_6h`, `diff_24h`
- 파생 feature: `cpu_memory_ratio`, `resource_total`, `resource_efficiency`, `events_per_machine`, `events_quantile`, `cpu_quantile`, `memory_quantile`
- 범주형 feature: `is_high_load`, `is_low_load`, `load_category`, `is_business_hour`, `is_weekend`, `is_night`
- 상호작용 feature: `cpu_events_interaction`, `machines_events_ratio`, `switches_complexity`

**총 79개 feature** 모두 필요!

#### 단계 4: LSTM 예측 실행
```python
# app/core/predictor/lstm_predictor.py
def run(self, *, github_url, metric_name, ctx, model_version):
    # 1. Feature 스케일링
    features_scaled = self.feature_scaler.transform(recent_data)
    X = features_scaled.reshape(1, self.sequence_length, -1)
    
    # 2. LSTM 모델 예측 (24시간, autoregressive)
    raw_predictions = self._generate_predictions(X)
    
    # 3. Context 기반 스케일링 (사용자 수, 시간대 반영)
    scale_factor = self._compute_context_scale(ctx, metric_name)
    predictions = [pred * scale_factor for pred in raw_predictions]
    
    # 4. PredictionResult 생성
    return PredictionResult(
        github_url=github_url,
        metric_name=metric_name,
        model_version=model_version,
        generated_at=datetime.utcnow(),
        predictions=[
            PredictionPoint(time=now + timedelta(hours=i+1), value=float(value))
            for i, value in enumerate(predictions)
        ]
    )
```

#### 단계 5: Policy 후처리 (안정화)
```python
# app/core/policy.py
final_pred = postprocess_predictions(raw_pred, ctx)
# - 가중치 적용 (ctx.weight)
# - 클램핑 (음수 방지, 극단값 제한)
# - 평활화 (급격한 변화 억제)
```

#### 단계 6: Flavor 추천 및 비용 산출
```python
# app/routes/plans.py
expected_users = ctx.expected_users or 100
time_slot = ctx.time_slot or "normal"

# 1단계: 사용자 수 기반
if expected_users <= 500:
    base_flavor = "small"
elif expected_users <= 5000:
    base_flavor = "medium"
else:
    base_flavor = "large"

# 2단계: 시간대 고려
if time_slot == "peak":
    recommended_flavor = upgrade(base_flavor)  # small → medium → large
elif time_slot == "low":
    recommended_flavor = downgrade(base_flavor)

# 3단계: 예측값 기반 안전장치
max_val = max(p.value for p in final_pred.predictions)
if max_val > 1000 or avg_val > 500:
    recommended_flavor = "large"

# 비용 산출
expected_cost_per_day = {"small": 1.2, "medium": 2.8, "large": 5.5}[recommended_flavor]
```

#### 단계 7: 이상 탐지 및 Discord 알림 (비차단)
```python
# app/core/anomaly.py
anomaly = detect_anomaly(final_pred, ctx, z_thresh=5.0)
if anomaly["anomaly_detected"]:
    send_discord_dev_alert(...)  # 중복 방지 적용
```

#### 단계 8: 응답 생성
```python
# app/routes/plans.py
return PlansResponse(
    prediction=final_pred,
    recommended_flavor=recommended_flavor,
    min_instances=1,
    max_instances=3,
    expected_cost_per_day=expected_cost_per_day,
    generated_at=datetime.utcnow(),
)
```

### 3.2 응답 스키마 (PlansResponse)
```json
{
  "prediction": {
    "github_url": "https://github.com/user/repo",
    "metric_name": "total_events",
    "model_version": "lstm_web_peak_v2",
    "generated_at": "2025-11-20T12:00:00Z",
    "predictions": [
      {"time": "2025-11-20T13:00:00Z", "value": 120.5},
      {"time": "2025-11-20T14:00:00Z", "value": 135.2},
      ...  // 24시간
    ]
  },
  "recommended_flavor": "medium",
  "min_instances": 1,
  "max_instances": 3,
  "expected_cost_per_day": 2.8,
  "generated_at": "2025-11-20T12:00:00Z"
}
```

## 4. 프론트엔드 응답 처리 및 표시

### 4.1 응답 수신 및 상태 업데이트
```typescript
// src/pages/Predict.tsx
const planResponse = await mcpApi.sendContextToMCP(payload, state.token);
// PlansResponse 객체 수신

toast({
  title: "예측 완료",
  description: `24시간 예측이 생성되었습니다. 권장 스펙: ${planResponse.recommended_flavor}`,
});
```

### 4.2 차트 표시 (ResultChart)
```typescript
// src/components/ResultChart.tsx
const chartData = result.prediction.predictions.map(p => ({
  time: new Date(p.time).toLocaleTimeString(),
  value: p.value,
}));

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={chartData}>
    <CartesianGrid strokeDasharray="3 3" />
    <XAxis dataKey="time" />
    <YAxis />
    <Tooltip />
    <Line type="monotone" dataKey="value" stroke="#8884d8" />
  </LineChart>
</ResponsiveContainer>
```

### 4.3 프로젝트 상태 업데이트
```typescript
// src/pages/Projects.tsx
// 프로젝트 목록에 새 프로젝트 추가
const newProject = {
  id: Date.now(),
  name: projectData.github_repo_url.split('/').pop(),
  repository: projectData.github_repo_url,
  status: "building",
  lastDeployment: null,
  url: null,
};
setProjects([...projects, newProject]);
```

## 5. CI/CD 배포 자동화 (배포 엔드포인트)

### 5.1 배포 요청 (프론트엔드 → 백엔드)
```typescript
// src/lib/mcpAPI.ts
const deployData = {
  service_id: serviceId,
  repo_id: projectData.github_repo_url,
  image_tag: "latest",
  env_config: {},
};

const deployResponse = await mcpApi.deploy(deployData, state.token);
// { instance_id: "inst-xxx", status: "deploying", ... }
```

### 5.2 배포 엔드포인트 (백엔드)
```python
# app/routes/deploy.py (8001 포트)
@router.post("/deploy")
def deploy_service(req: DeployRequest):
    # 1. Docker 이미지 빌드/푸시
    # 2. Kubernetes/VM 배포
    # 3. 상태 모니터링
    return DeployResponse(
        instance_id="inst-xxx",
        status="deploying",
        ...
    )
```

## 6. MySQL 데이터 소스 연동 (향후)

### 6.1 테이블 구조: metric_history
```sql
CREATE TABLE metric_history (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  github_url VARCHAR(200) NOT NULL,
  ts DATETIME NOT NULL,
  metric_name VARCHAR(100) NOT NULL,
  value DOUBLE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_metric (github_url, ts, metric_name),
  INDEX idx_github_url (github_url),
  INDEX idx_metric_name (metric_name),
  INDEX idx_ts (ts)
) ENGINE=InnoDB;
```

### 6.2 데이터 적재 (ETL 파이프라인 필요)
- **원본 데이터**: 서비스 모니터링 시스템(Prometheus, CloudWatch 등)
- **파생 feature 계산**: lag, ma, roll, pct_change, diff, ratio 등
- **적재**: metric_history 테이블에 feature_names 전체 저장 (세로형 구조)

### 6.3 예측 시 데이터 조회
```python
# app/core/predictor/data_sources/mysql_source.py
def fetch_historical_data(self, github_url, metric_name, hours=24):
    # feature_names 전체를 반복 조회하여 DataFrame 생성
    df = pd.DataFrame()
    for feature in feature_names:
        stmt = "SELECT ts, value FROM metric_history WHERE github_url = :url AND metric_name = :metric AND ts >= :start ORDER BY ts ASC"
        rows = conn.execute(stmt, {"url": github_url, "metric": feature, "start": start_ts})
        df[feature] = [row.value for row in rows]
    return df
```

### 6.4 주의사항
- feature_names에 있는 모든 feature가 DB에 저장되어 있어야 LSTM 예측 가능
- 일부 feature 누락 시 → Baseline Predictor로 자동 fallback
- 파생 feature는 ETL 단계에서 미리 계산하거나, 예측 직전에 실시간 계산

## 7. 데이터 흐름 요약

1. **프론트엔드**: 사용자가 GitHub URL, 예상 사용자 수, 요청사항 입력
2. **API 호출**: `POST /plans`로 Context JSON 전송
3. **백엔드**: Context 추출, 모델 선택, 데이터 조회, 예측 실행
4. **데이터 소스**: CSV/MySQL에서 feature_names 전체(79개) 조회
5. **LSTM 예측**: 24시간 시계열 예측 생성, Context 기반 스케일링
6. **Policy 후처리**: 가중치, 클램핑, 평활화
7. **Flavor 추천**: 사용자 수, 시간대, 예측값 기반으로 인스턴스 스펙 결정
8. **응답**: PlansResponse (예측, 권장 스펙, 비용) 반환
9. **프론트엔드**: 차트 표시, 프로젝트 상태 업데이트
10. **CI/CD**: 배포 엔드포인트로 자동 배포 (선택)

## 8. 연동 체크리스트

### 프론트엔드 (mcp_web)
- [x] GitHub URL 입력 필드
- [x] 예상 사용자 수 입력 필드
- [x] 자연어 요청사항 입력 필드 (선택)
- [x] `POST /plans` API 호출
- [x] PlansResponse 응답 수신 및 차트 표시
- [x] 프로젝트 목록 관리 (생성, 조회, 삭제)
- [x] 인증 (JWT 토큰)
- [ ] 배포 상태 실시간 업데이트 (WebSocket/Polling)

### 백엔드 (mcp_core)
- [x] `POST /plans` 엔드포인트
- [x] Context 추출 및 검증
- [x] Router (모델 선택)
- [x] LSTM Predictor (CSV 데이터 소스)
- [x] Baseline Predictor (fallback)
- [x] Policy 후처리
- [x] Flavor 추천 및 비용 산출
- [x] PlansResponse 응답 생성
- [x] 이상 탐지 및 Discord 알림
- [ ] MySQL 데이터 소스 연동
- [ ] feature engineering 자동화 (ETL)
- [ ] 배포 엔드포인트 구현 (`POST /deploy`, `POST /destroy`)
- [ ] 프로젝트 관리 API (`GET /projects`, `POST /projects`, `DELETE /projects/{id}`)

### 데이터베이스 (MySQL)
- [x] metric_history 테이블 DDL
- [x] SQLAlchemy ORM 모델
- [ ] feature_names 전체 적재 파이프라인
- [ ] 파생 feature 계산 스크립트
- [ ] 데이터 품질 검증 (누락, 이상치 처리)

### 배포 및 운영
- [ ] Vercel 배포 (프론트엔드)
- [ ] EC2/Docker 배포 (백엔드)
- [ ] MySQL 운영 (RDS, Aurora 등)
- [ ] 환경 변수 설정 (API URL, DB 연결 정보, Discord Webhook 등)
- [ ] 모니터링 (로그, 메트릭, 알림)
- [ ] CI/CD 파이프라인 (GitHub Actions, Jenkins 등)

## 9. 다음 단계

1. **MySQL 데이터 소스 전환**
   - metric_history 테이블 생성 및 초기 데이터 적재
   - MySQLDataSource를 LSTM Predictor에 연동
   - CSV 대비 성능/정확도 비교

2. **프론트엔드-백엔드 연동 테스트**
   - 로컬 환경에서 mcp_web + mcp_core 연동 테스트
   - API 스키마 일치 여부 확인
   - 에러 핸들링 개선

3. **배포 자동화**
   - `POST /deploy`, `POST /destroy` 엔드포인트 구현
   - GitHub Actions + Docker + Kubernetes/VM 배포 파이프라인
   - 프론트엔드에서 배포 상태 실시간 확인

4. **Feature Engineering 자동화**
   - ETL 파이프라인 구축 (Airflow, Dagster 등)
   - lag, ma, roll 등 파생 feature 자동 계산
   - 데이터 품질 검증 및 모니터링

5. **모니터링 및 알림 강화**
   - Discord/Slack 알림 고도화 (임계값, 중복 방지, 에스컬레이션)
   - Grafana/Prometheus 대시보드
   - 로그 수집 및 분석 (ELK, CloudWatch)

---
생성일: 2025-11-20
작성자: GitHub Copilot
