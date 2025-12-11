# MCP Core 모델 파일

이 디렉토리에는 학습된 LSTM 모델 파일이 포함되어야 합니다.

## 필수 파일

프로젝트를 실행하려면 다음 파일이 필요합니다:

1. **best_mcp_lstm_model.h5** (메인 LSTM 모델)
   - 크기: ~2-5MB
   - 용도: 24시간 예측 수행

2. **mcp_model_metadata.pkl** (모델 메타데이터)
   - 크기: ~100KB
   - 용도: Feature scaler, target scaler, feature names, sequence length 등

3. **best_mcp_lstm_checkpoint.h5** (체크포인트, 선택적)

## 모델 파일 다운로드 (Git에 포함되지 않음)

모델 파일은 `.gitignore`에 의해 Git 저장소에서 제외됩니다.
다음 중 한 가지 방법으로 모델 파일을 준비하세요:

### 방법 1: GitHub Release에서 다운로드 (권장)
```bash

# git pull origin main
# python scripts/download_models.py

# .github/workflows/deploy.yml
- name: Download models
  run: python scripts/download_models.py
```

### 방법 2: Google Drive / OneDrive 등에서 수동 다운로드
프로젝트 관리자에게 모델 파일 공유 링크를 요청하세요.

### 방법 3: 직접 학습
```bash
# Jupyter Notebook으로 모델 재학습
# train_from_notebook.py 실행
python -m app.core.predictor.train_from_notebook
```

## 현재 상태 확인

현재 디렉토리에 있는 파일:
```bash
ls -lh models/
```

필수 파일이 없으면 Docker Compose 실행 시 오류가 발생합니다:
```
PredictionError: LSTM 모델을 로드할 수 없습니다
```

## 모델 스펙

- **프레임워크**: TensorFlow/Keras 2.x
- **입력 시퀀스 길이**: 24 (1일)
- **출력 길이**: 24 (다음 24시간)
- **특징**: service_type, time_slot, cpu, memory, users 등
- **학습 데이터**: data/lstm_ready_cluster_data.csv
