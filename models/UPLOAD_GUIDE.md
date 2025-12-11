# GitHub Release를 사용한 모델 파일 업로드 가이드

## 1. GitHub CLI 설치 (이미 설치되어 있으면 skip)

```bash
# Windows (winget)
winget install GitHub.cli

# Mac (brew)
brew install gh

# Linux
sudo apt install gh
```

## 2. GitHub CLI 인증

```bash
gh auth login
```

## 3. 릴리스 생성 및 모델 파일 업로드

### 방법 A: 새 릴리스 생성

```bash
# 프로젝트 루트에서 실행
cd c:\Users\wjdwl\mcp_core

# 릴리스 생성 및 파일 업로드
gh release create v1.0.0 \
  models/best_mcp_lstm_model.h5 \
  models/best_mcp_lstm_checkpoint.h5 \
  models/mcp_model_metadata.pkl \
  --title "MCP LSTM Model v1.0.0" \
  --notes "## MCP LSTM 모델 파일

- best_mcp_lstm_model.h5: 메인 예측 모델 (0.25 MB)
- mcp_model_metadata.pkl: 스케일러 및 메타데이터
- best_mcp_lstm_checkpoint.h5: 체크포인트 (선택사항)

### 사용 방법
\`\`\`bash
python scripts/download_models.py
\`\`\`
"
```

### 방법 B: 기존 릴리스에 추가

```bash
# 기존 릴리스에 파일 추가
gh release upload v1.0.0 \
  models/best_mcp_lstm_model.h5 \
  models/mcp_model_metadata.pkl
```

## 4. 릴리스 URL 확인

```bash
# 릴리스 목록 확인
gh release list

# 특정 릴리스 보기
gh release view v1.0.0 --web
```

릴리스가 생성되면 다음과 같은 URL이 생성됩니다:
```
https://github.com/MCP-AI-Ops/mcp_core/releases/download/v1.0.0/best_mcp_lstm_model.h5
```

## 5. download_models.py 업데이트

`scripts/download_models.py` 파일에서 URL을 실제 릴리스 URL로 변경:

```python
MODEL_FILES = {
    "best_mcp_lstm_model.h5": {
        "url": "https://github.com/MCP-AI-Ops/mcp_core/releases/download/v1.0.0/best_mcp_lstm_model.h5",
        # ...
    },
}
```

## 6. 테스트

```bash
# models 디렉터리 백업
mv models models.backup

# 모델 다운로드 테스트
python scripts/download_models.py

# 정상 작동 확인
ls -lh models/
```

## 별도 Private 레포지토리 사용 (옵션)

대용량 모델이 많거나 보안이 중요한 경우:

```bash
# 1. 새 private 레포 생성
gh repo create MCP-AI-Ops/mcp_models --private --description "MCP Model Files"

# 2. 모델 파일 복사 및 커밋
cd ..
git clone https://github.com/MCP-AI-Ops/mcp_models.git
cd mcp_models

cp ../mcp_core/models/*.h5 .
cp ../mcp_core/models/*.pkl .

git add *.h5 *.pkl
git commit -m "Add initial model files"
git push

# 3. GitHub Release 생성
gh release create v1.0.0 *.h5 *.pkl \
  --title "Model Files v1.0.0" \
  --notes "Initial model release"
```

그 다음 `download_models.py`의 URL을 변경:
```python
"url": "https://github.com/MCP-AI-Ops/mcp_models/releases/download/v1.0.0/best_mcp_lstm_model.h5"
```

## 트러블슈팅

### Q: `gh` 명령어를 찾을 수 없습니다

```bash
# PATH에 추가 (Windows)
# GitHub CLI 기본 설치 경로: C:\Program Files\GitHub CLI\

# 또는 웹 인터페이스 사용
# https://github.com/MCP-AI-Ops/mcp_core/releases/new
```

### Q: 인증 실패

```bash
gh auth logout
gh auth login
# 브라우저로 인증 진행
```

### Q: 파일이 너무 큽니다 (100MB 이상)

GitHub Release는 개별 파일당 2GB까지 가능하지만, 100MB 이상은:
- Git LFS 사용
- Azure Blob Storage / AWS S3 사용
- 모델 압축 고려
