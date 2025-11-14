#!/bin/bash
# MVP 배포 전 검증 스크립트 (Linux/Mac)
# 사용법: bash validate_mvp.sh

set -e

echo ""
echo "=== MCP Core MVP 배포 전 검증 ==="
echo ""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 1. 필수 모델 파일 확인
echo -e "${YELLOW}[1/6] 모델 파일 확인...${NC}"
MODEL_FILES=(
    "models/best_mcp_lstm_model.h5"
    "models/mcp_model_metadata.pkl"
)

MISSING_MODELS=()
for file in "${MODEL_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo -e "  ${GREEN}✓${NC} $file ($size)"
    else
        echo -e "  ${RED}✗${NC} $file (없음)"
        MISSING_MODELS+=("$file")
    fi
done

if [ ${#MISSING_MODELS[@]} -gt 0 ]; then
    echo -e "\n${RED}필수 모델 파일이 누락되었습니다!${NC}"
    echo -e "   ${YELLOW}다음 파일을 준비해주세요:${NC}"
    for file in "${MISSING_MODELS[@]}"; do
        echo "   - $file"
    done
    echo -e "\n   ${CYAN}자세한 내용: models/README.md 참고${NC}"
    echo ""
    exit 1
fi

# 2. .env 파일 확인
echo -e "\n${YELLOW}[2/6] 환경 변수 파일 확인...${NC}"
if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} .env 파일 존재"
    
    # 중요 변수 확인
    if ! grep -q "DATABASE_URL=" .env; then
        echo -e "  ${YELLOW}DATABASE_URL이 설정되지 않았습니다${NC}"
    fi
    if grep -q "DISCORD_WEBHOOK_URL=$\|DISCORD_WEBHOOK_URL=\s*$" .env; then
        echo -e "  ${YELLOW}DISCORD_WEBHOOK_URL이 비어있습니다 (선택적)${NC}"
    fi
    if grep -q "GITHUB_TOKEN=$\|GITHUB_TOKEN=\s*$" .env; then
        echo -e "  ${YELLOW}GITHUB_TOKEN이 비어있습니다 (Rate Limit 주의)${NC}"
    fi
else
    echo -e "  ${RED}✗${NC} .env 파일이 없습니다"
    echo -e "     ${YELLOW}실행: cp .env.example .env${NC}"
    exit 1
fi

# 3. Docker 확인
echo -e "\n${YELLOW}[3/6] Docker 설치 확인...${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "  ${GREEN}✓${NC} $DOCKER_VERSION"
else
    echo -e "  ${RED}✗${NC} Docker를 찾을 수 없습니다"
    echo -e "     ${YELLOW}설치: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

# 4. Docker Compose 확인
echo -e "\n${YELLOW}[4/6] Docker Compose 확인...${NC}"
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "  ${GREEN}✓${NC} $COMPOSE_VERSION"
else
    echo -e "  ${RED}✗${NC} Docker Compose를 찾을 수 없습니다"
    exit 1
fi

# 5. 포트 사용 확인
echo -e "\n${YELLOW}[5/6] 포트 충돌 확인...${NC}"
PORTS=(3308 8000 8001)
USED_PORTS=()

for port in "${PORTS[@]}"; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an | grep -q ":$port.*LISTEN" 2>/dev/null; then
        echo -e "  ${RED}✗${NC} 포트 $port 이미 사용 중"
        USED_PORTS+=("$port")
    else
        echo -e "  ${GREEN}✓${NC} 포트 $port 사용 가능"
    fi
done

if [ ${#USED_PORTS[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}다음 포트가 이미 사용 중입니다:${NC}"
    for port in "${USED_PORTS[@]}"; do
        echo "   - $port"
    done
    echo -e "\n   ${CYAN}기존 프로세스 종료 또는 docker-compose.yml에서 포트 변경 필요${NC}"
fi

# 6. 데이터 파일 확인
echo -e "\n${YELLOW}[6/6] 데이터 파일 확인...${NC}"
if [ -f "data/lstm_ready_cluster_data.csv" ]; then
    size=$(du -h "data/lstm_ready_cluster_data.csv" | cut -f1)
    echo -e "  ${GREEN}✓${NC} data/lstm_ready_cluster_data.csv ($size)"
else
    echo -e "  ${RED}✗${NC} data/lstm_ready_cluster_data.csv (없음)"
    echo -e "     ${YELLOW}LSTM 예측이 작동하지 않습니다 (Baseline으로 폴백)${NC}"
fi

# 최종 요약
echo -e "\n${CYAN}=== 검증 완료 ===${NC}"

if [ ${#MISSING_MODELS[@]} -eq 0 ] && [ -f ".env" ]; then
    echo -e "\n${GREEN}MVP 배포 준비가 완료되었습니다!${NC}"
    echo ""
    echo -e "${CYAN}다음 명령으로 시작하세요:${NC}"
    echo -e "  ${NC}docker-compose up -d --build${NC}"
    echo ""
    echo -e "${CYAN}헬스 체크:${NC}"
    echo -e "  ${NC}curl http://localhost:8001/health${NC}"
    echo -e "  ${NC}curl http://localhost:8000/health${NC}"
    echo ""
else
    echo -e "\n${YELLOW}일부 문제를 해결 후 다시 시도하세요${NC}"
    echo ""
    exit 1
fi
