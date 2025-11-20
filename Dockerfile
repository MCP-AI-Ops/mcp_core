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

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (불필요한 파일 제외)
COPY app/ ./app/
COPY models/ ./models/
COPY data/ ./data/
COPY db/ ./db/
COPY scripts/ ./scripts/

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=25s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
