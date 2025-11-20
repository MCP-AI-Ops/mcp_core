# 정리 노트 (feat/#13/db 브랜치)

## 삭제 대상 파일/폴더

### 즉시 삭제 가능 (Git 커밋 전)
```powershell
# Python 캐시
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# 백업 env
Remove-Item .env.backup -ErrorAction SilentlyContinue

# macOS 메타
Remove-Item .DS_Store -ErrorAction SilentlyContinue

# 데모 노트북 (선택)
Remove-Item demoMCPproject.ipynb -ErrorAction SilentlyContinue
```

### ✅ 삭제 완료 (feat/#13/db)
- `app/core/db.py` - ⚠️ deprecated 마킹됨 (다음 마이그레이션에서 제거)
- `app/routes/router_auth.py` - ✅ 삭제됨
- `app/models/model_user.py` - ✅ 삭제됨
- `docs/MCP_CORE_ARCHITECTURE.md` - ✅ 삭제됨 (인코딩 손상)
- `docs/persistence_mvp.md` - ✅ 삭제됨 (구식 스키마)
- 루트 테스트 스크립트들 - ✅ 삭제됨
- 구식 schema_mcp.txt - ✅ 삭제됨

## DB 레이어 정리 완료

**Before:**
- `db.py` (레거시 raw SQL) + `db_sqlalchemy.py` (신규 ORM) 혼재
- 충돌 위험: 둘 다 `get_db()` 제공

**After:**
- `db_sqlalchemy.py` 단일 진실의 원천 (Single Source of Truth)
- `db.py`는 deprecated 마킹 후 다음 PR에서 삭제
- 통합 스키마: `db/schema_unified.sql`

## Git 커밋 체크리스트

- [ ] `.env` 파일이 staged 안 되었는지 확인
- [ ] `__pycache__` 폴더들 삭제 완료
- [ ] `.gitignore`에 필수 항목 포함 확인:
  - `.env`
  - `__pycache__/`
  - `.venv/`
  - `*.log`
- [ ] 커밋 메시지:
  ```
  feat(db): Unified schema and ORM migration
  
  - Add db/schema_unified.sql (replace MVP/simplified schemas)
  - Standardize database name to mcp_core (from mcp_autoscaler)
  - Mark db.py as deprecated (use db_sqlalchemy.py)
  - Add metric ingestion script
  - Update all documentation references
  ```

## 다음 단계

1. 로컬 정리:
   ```powershell
   # 캐시 삭제
   Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
   
   # .env 확인
   git status | Select-String ".env"
   ```

2. Git 커밋:
   ```powershell
   git add .
   git status  # .env 없는지 확인!
   git commit -m "feat(db): Unified schema and ORM migration"
   git push origin feat/#13/db
   ```

3. 원격 서버 배포:
   ```bash
   cd /opt/mcp
   git pull origin feat/#13/db
   docker compose down
   docker volume rm mcp_mysql_data  # 기존 데이터 삭제 OK시
   docker compose up -d
   docker exec -it mcp_mysql mysql -u root -padmin -e "USE mcp_core; SHOW TABLES;"
   ```

4. 테스트:
   ```bash
   docker exec -it mcp-core python -m app.core.db_sqlalchemy
   curl http://localhost:8000/health
   ```
