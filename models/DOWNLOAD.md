# MCP 모델 파일 관리 가이드

## 문제
- 모델 파일(`.h5`, `.pkl`)이 Git 저장소에 포함되어 빌드가 느림
- GitHub Actions, Docker 빌드 시 대용량 파일 전송으로 시간 증가

## 해결 방법

### 📦 모델 파일 다운로드

배포 전 또는 처음 설치 시 다음 명령어를 실행하세요:

```bash
# Python으로 다운로드
python scripts/download_models.py

# 또는 pip로 필요한 패키지 설치 후
pip install requests
python scripts/download_models.py
```

### 🔧 환경 변수 설정

모델 파일 위치를 커스터마이징하려면:

```bash
# .env 파일에 추가
LSTM_MODEL_PATH=/path/to/models/best_mcp_lstm_model.h5
LSTM_METADATA_PATH=/path/to/models/mcp_model_metadata.pkl
LSTM_CSV_PATH=/path/to/data/lstm_ready_cluster_data.csv
```

### 🚀 Docker 빌드 시

```dockerfile
# Dockerfile에 추가
RUN python scripts/download_models.py
```

또는 빌드 전 로컬에서 다운로드:

```bash
python scripts/download_models.py
docker build -t mcp-core .
```

### 📤 모델 파일 업로드 (관리자용)

새 버전의 모델을 배포하려면:

1. **GitHub Release 생성**
   ```bash
   gh release create v1.0.0 \
     models/best_mcp_lstm_model.h5 \
     models/mcp_model_metadata.pkl \
     --title "MCP LSTM Model v1.0.0" \
     --notes "Initial model release"
   ```

2. **별도 레포지토리 사용**
   ```bash
   # 새 private 레포 생성
   gh repo create MCP-AI-Ops/mcp_models --private
   
   # 모델 파일만 커밋
   cd mcp_models
   cp ../mcp_core/models/*.h5 .
   cp ../mcp_core/models/*.pkl .
   git add *.h5 *.pkl
   git commit -m "Add model files"
   git push
   ```

3. **Azure Blob Storage / AWS S3 사용**
   ```python
   # scripts/download_models.py 수정
   # Azure Blob Storage URL로 변경
   "url": "https://<storage-account>.blob.core.windows.net/models/best_mcp_lstm_model.h5"
   ```

## 모델 파일 목록

| 파일명 | 크기 | 필수 | 설명 |
|--------|------|------|------|
| `best_mcp_lstm_model.h5` | 0.25 MB | ✅ | LSTM 예측 모델 |
| `mcp_model_metadata.pkl` | < 0.01 MB | ✅ | 스케일러 및 메타데이터 |
| `best_mcp_lstm_checkpoint.h5` | 0.66 MB | ❌ | 체크포인트 (선택) |

## Git에서 모델 파일 제거

모델 파일을 Git 히스토리에서 완전히 제거하려면:

```bash
# 1. Git 히스토리에서 제거
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch models/*.h5 models/*.pkl' \
  --prune-empty --tag-name-filter cat -- --all

# 2. 강제 푸시
git push origin --force --all

# 3. 로컬 정리
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

**⚠️ 주의:** 협업 중인 경우 팀원들에게 미리 알려야 합니다!

## CI/CD 설정

### GitHub Actions

`.github/workflows/build.yml`:

```yaml
name: Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Download models
        run: |
          pip install requests
          python scripts/download_models.py
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/
```

### Docker Compose

```yaml
services:
  mcp-core:
    build: .
    volumes:
      - ./models:/app/models  # 로컬 모델 마운트
    environment:
      - LSTM_MODEL_PATH=/app/models/best_mcp_lstm_model.h5
```

## 트러블슈팅

### Q: 다운로드 실패 시?

```bash
# 수동 다운로드
curl -L -o models/best_mcp_lstm_model.h5 \
  https://github.com/MCP-AI-Ops/mcp_models/releases/download/v1.0.0/best_mcp_lstm_model.h5
```

### Q: 모델 파일이 없다는 에러?

```python
# app/core/predictor/lstm_predictor.py에서 확인
# 환경 변수가 올바른지 확인
echo $LSTM_MODEL_PATH
```

### Q: 다른 저장소 사용하려면?

`scripts/download_models.py`의 `MODEL_FILES` dict에서 URL만 변경하면 됩니다.
