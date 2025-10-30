# 📋 수정 내용 요약

## 🎯 전체 변경 개요

**목적:** CSV/MySQL 데이터 소스를 추상화하고, LSTM과 Baseline의 역할을 명확히 분리

**핵심 철학:**
- ✅ LSTM: 진짜 모델만 담당, 실패 시 예외 발생
- ✅ Baseline: 통계 기반 예측 + 폴백(fallback) 역할
- ✅ Data Sources: CSV/MySQL 자동 전환 (환경변수로 제어)

---

## 📁 변경된 파일 목록

### 1️⃣ **새로 추가된 파일**
```
app/core/predictor/data_sources/
├── __init__.py          (새로 생성)
├── base.py              (새로 생성)
├── csv_source.py        (새로 생성)
└── factory.py           (새로 생성)
```

### 2️⃣ **수정된 파일**
```
app/core/errors.py                    (에러 클래스 추가)
app/core/predictor/lstm_predictor.py  (더미 제거, 데이터 소스 연동)
app/core/predictor/baseline_predictor.py (통계 기반 + 폴백 역할)
data/lstm_ready_cluster_data.csv      (BigQuery 전처리 데이터)
models/best_mcp_lstm_model.h5         (LSTM 모델)
models/mcp_model_metadata.pkl         (스케일러 메타데이터)
```

---

## 🔧 상세 변경 내용

### **1. app/core/errors.py**

#### 변경 전:
```python
class ContextVaidationError(ValueError):
    pass

class ModelValidationError(RuntimeError):
    pass

class PredictionError(RuntimeError):
    pass
```

#### 변경 후:
```python
class ContextVaidationError(ValueError):
    pass

class ModelValidationError(RuntimeError):
    pass

class PredictionError(RuntimeError):
    pass

# 새로 추가 ↓
class DataSourceError(RuntimeError):
    """데이터 소스 오류"""
    pass

class DataNotFoundError(DataSourceError):
    """데이터 없음"""
    pass

class PredictionError(RuntimeError):
    """예측 실패"""
    pass
```

---

### **2. app/core/predictor/data_sources/ (새로 생성)**

#### **목적:**
데이터 조회를 추상화하여 CSV ↔ MySQL 쉽게 전환

#### **파일 설명:**

##### `base.py`
```python
# 데이터 소스의 인터페이스 정의
class DataSource(ABC):
    def fetch_historical_data(...) -> np.ndarray:
        """최근 N시간 데이터 조회"""
        pass
    
    def is_available() -> bool:
        """사용 가능 여부"""
        pass
```

##### `csv_source.py`
```python
# CSV 파일에서 데이터 읽기
class CSVDataSource(DataSource):
    def __init__(self, csv_path="data/lstm_ready_cluster_data.csv"):
        self.df = pd.read_csv(csv_path)
    
    def fetch_historical_data(service_id, metric_name, hours=168):
        # CSV에서 최근 168시간 데이터 반환
        return self.df[metric_name].values[-hours:]
```

##### `factory.py`
```python
# 환경변수에 따라 CSV/MySQL 자동 선택
def get_data_source():
    source_type = os.getenv("DATA_SOURCE_TYPE", "csv")
    
    if source_type == "csv":
        return CSVDataSource()
    elif source_type == "mysql":
        return MySQLDataSource()  # Phase 2
```

---

### **3. app/core/predictor/lstm_predictor.py**

#### 주요 변경사항:

##### ✅ **추가된 것:**
- 데이터 소스 연동 (`get_data_source()`)
- 실패 시 `PredictionError` 예외 발생
- 메타데이터 구조 지원 (딕셔너리 or 스케일러 객체)

#### 변경 전:
```python
def run(...):
    # 데이터 없으면 더미 생성
    historical_data = self._generate_dummy_data(168)
    
    # 모델 없으면 더미 예측 반환
    if self.base_model is None:
        return self._generate_dummy_prediction(...)
```

#### 변경 후:
```python
def run(...):
    # 모델 없으면 예외 발생
    if self.model is None:
        raise PredictionError("LSTM model not loaded")
    
    # 데이터 소스에서 조회 (실패 시 예외 발생)
    historical_data = self.data_source.fetch_historical_data(
        service_id=service_id,
        metric_name=metric_name,
        hours=168
    )
```

---

### **4. app/core/predictor/baseline_predictor.py**

#### 주요 변경사항:

##### ✅ **새로운 역할:**
1. **통계 기반 예측**: 실제 데이터로 이동평균 예측
2. **폴백(fallback)**: 데이터 없거나 LSTM 실패 시 더미 예측

#### 변경 전:
```python
def run(...):
    base = 0.3
    slope = 0.01 if ctx.time_slot in ("normal", "low") else 0.02
    
    for k in range(1, 25):
        preds.append(
            PredictionPoint(
                time=now + timedelta(hours=k),
                value=base + slope * k
            )
        )
```

#### 변경 후:
```python
def run(...):
    # 1. 데이터 있으면 통계 예측
    try:
        recent_data = self.data_source.fetch_historical_data(...)
        return self._statistical_prediction(...)  # 평균/트렌드 기반
    except:
        # 2. 데이터 없으면 더미 예측
        return self._fallback_prediction(...)

def _statistical_prediction(..., recent_data):
    """실제 데이터 기반 통계 예측"""
    avg = recent_data.mean()
    trend = (recent_data[-1] - recent_data[0]) / len(recent_data)
    
    for k in range(1, 25):
        value = last_value + trend * k  # 트렌드 반영

def _fallback_prediction(...):
    """데이터 없을 때 더미 예측"""
    # metric별 기본값 사용
    if metric_name == "total_events":
        base = 50.0
```

---

## 🔄 실행 흐름 변화

### **변경 전:**
```
요청
 ↓
LSTM Predictor
 ├─ 모델 있음? → 예측
 └─ 모델 없음? → 더미 반환
```

### **변경 후:**
```
요청
 ↓
LSTM Predictor (try)
 ├─ 모델 로드 성공
 │   ├─ CSV/MySQL에서 데이터 조회
 │   └─ 예측 실행
 │
 └─ 실패 (PredictionError) → Baseline으로 폴백
     ├─ 데이터 있음? → 통계 예측
     └─ 데이터 없음? → 더미 예측
```

---

## 🎯 예상 동작 시나리오

### **시나리오 1: 정상 (LSTM + CSV)**
```
1. 요청: /plans (service_id=cluster, metric_name=total_events)
2. LSTM 실행
   ├─ CSV에서 168시간 데이터 로드
   ├─ 전처리 (스케일링)
   ├─ LSTM 모델 예측
   └─ 24시간 예측값 반환
3. 응답: [42, 45, 48, ..., 60] (24개 값)
```

### **시나리오 2: LSTM 실패 → Baseline 폴백**
```
1. 요청: /plans
2. LSTM 실행 → PredictionError (모델 로드 실패)
3. Baseline 실행
   ├─ CSV에서 24시간 데이터 로드
   ├─ 평균/트렌드 계산
   └─ 통계 기반 예측 반환
4. 응답: [48, 49, 49, ..., 52] (24개 값)
```

### **시나리오 3: 데이터도 없음 → 완전 폴백**
```
1. 요청: /plans
2. LSTM 실행 → PredictionError
3. Baseline 실행
   ├─ CSV 조회 실패 (파일 없음)
   └─ 더미 예측 생성
4. 응답: [50, 50.5, 51, ..., 62] (더미)
```

---

## 📊 파일 크기 비교

| 파일 | 변경 전 | 변경 후 | 변화 |
|------|---------|---------|------|
| `lstm_predictor.py` | ~270줄 | ~110줄 | **-160줄** (더미 제거) |
| `baseline_predictor.py` | ~20줄 | ~140줄 | **+120줄** (통계+폴백) |
| `data_sources/` | 없음 | ~400줄 | **+400줄** (새로 생성) |
| **총합** | ~290줄 | ~650줄 | **+360줄** |

---

## ✅ 장점

### **1. 유연성**
```bash
# CSV 사용 (현재)
export DATA_SOURCE_TYPE=csv

# MySQL로 전환 (Phase 2)
export DATA_SOURCE_TYPE=mysql
```
→ 코드 수정 없이 환경변수만 변경!

### **2. 역할 분리**
- **LSTM**: 딥러닝 예측만 담당
- **Baseline**: 통계 + 폴백 담당
- **DataSource**: 데이터 조회만 담당

### **3. 테스트 용이**
```python
# 테스트 시 Mock 데이터 소스 주입 가능
test_source = MockDataSource()
predictor = LSTMPredictor()
predictor.data_source = test_source
```

### **4. 에러 처리 명확**
- LSTM 실패 → `PredictionError` 발생
- Baseline이 안전하게 처리
- 사용자는 항상 예측값 받음

---

### **테스트:**
```bash
# 1. CSV 데이터 확인
python -c "from app.core.predictor.data_sources import get_data_source; print(get_data_source().get_data_info())"

# 2. LSTM 예측 테스트
python -c "from app.core.predictor.lstm_predictor import LSTMPredictor; ..."

# 3. API 실행
uvicorn app.main:app --reload
```

### **Phase 2 (MySQL 전환):**
1. MySQL 스키마 설계
2. `MySQLDataSource` 구현
3. 환경변수만 변경: `DATA_SOURCE_TYPE=mysql`

---

## 📌 요약

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| **데이터 조회** | 하드코딩 | 추상화 (CSV/MySQL) |
| **LSTM 역할** | 예측 + 더미 | 예측만 |
| **Baseline 역할** | 간단한 더미 | 통계 + 폴백 |
| **에러 처리** | 더미 반환 | 예외 발생 → 폴백 |
| **확장성** | 낮음 | 높음 (MySQL 준비) |
| **코드 품질** | 혼재 | 명확한 분리 |

---

## 🎨 아키텍처 다이어그램

### **Before (변경 전)**
```
┌─────────────────┐
│  API Request    │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  LSTM    │
    │ (All-in) │
    └────┬─────┘
         │
    ┌────▼──────┐
    │ Response  │
    └───────────┘
```

### **After (변경 후)**
```
┌─────────────────┐
│  API Request    │
└────────┬────────┘
         │
    ┌────▼─────┐      ┌──────────────┐
    │  LSTM    │◄─────│ DataSource   │
    │          │      │ (CSV/MySQL)  │
    └────┬─────┘      └──────────────┘
         │
      [실패?]
         │
    ┌────▼─────┐      ┌──────────────┐
    │ Baseline │◄─────│ DataSource   │
    │ (Fallback)│     │ (CSV/MySQL)  │
    └────┬─────┘      └──────────────┘
         │
    ┌────▼──────┐
    │ Response  │
    └───────────┘
```

---

## 📝 환경변수 설정

### **.env 파일 예시**
```bash
# Data Source Configuration
DATA_SOURCE_TYPE=csv
CSV_DATA_PATH=data/lstm_ready_cluster_data.csv

# Model Configuration
MODEL_DIR=models

# Phase 2 (MySQL)
# DATA_SOURCE_TYPE=mysql
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=your_password
# MYSQL_DATABASE=mcp_db
```

---

## 🔍 디버깅 가이드

### **1. CSV 파일 로드 실패**
```python
# 확인
from pathlib import Path
csv_path = Path("data/lstm_ready_cluster_data.csv")
print(f"CSV exists: {csv_path.exists()}")

# 해결
# - 파일 경로 확인
# - 파일 권한 확인
```

### **2. LSTM 모델 로드 실패**
```python
# 확인
from pathlib import Path
model_path = Path("models/best_mcp_lstm_model.h5")
print(f"Model exists: {model_path.exists()}")

# 해결
# - 파일명 정확히 일치하는지 확인
# - TensorFlow 버전 확인 (pip show tensorflow)
```

### **3. 예측값이 이상함**
```python
# 스케일러 확인
import pickle
with open("models/mcp_model_metadata.pkl", "rb") as f:
    meta = pickle.load(f)
    print(type(meta))  # dict or scaler 객체?
    if isinstance(meta, dict):
        print(meta.keys())
```

**작성자:** 진호  
**작성일:** 2025-10-30  
**브랜치:** `data/model`  
**버전:** 1.0.0

---

**결론: 깔끔하게 역할이 분리되고, CSV/MySQL 전환이 쉬워졌습니다!** 🎉