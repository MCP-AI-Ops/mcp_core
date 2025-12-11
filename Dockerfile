########################
# 1) Builder Stage
########################
FROM python:3.11-slim AS builder

WORKDIR /app

# Poetry 설치 & 빌드 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip \
    && pip install poetry

# Poetry 설정 (가상환경 비활성화)
ENV POETRY_VIRTUALENVS_CREATE=false

# 의존성 파일만 복사 (캐시 활용)
COPY pyproject.toml poetry.lock* /app/

# Python 의존성 설치
RUN poetry install --no-interaction --no-ansi --without dev

# 앱 코드 복사
COPY . /app


########################
# 2) Runtime Stage
########################
FROM python:3.11-slim

WORKDIR /app

# 런타임 의존성 최소화
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 빌드 결과 복사
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# 모델 파일 다운로드 (GitHub Release에서)
RUN python scripts/download_models.py

EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=25s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]