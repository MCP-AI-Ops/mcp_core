# Persistence (MVP)

This project includes an optional minimal persistence layer for plan requests, predictions, anomaly detections, and alert history.

- Schema: `db/schema_mvp.sql`
- Runtime: enabled only when `DATABASE_URL` is set (SQLAlchemy + PyMySQL).

## Enable

1) Install dependencies (already in `requirements.txt`):
   - `SQLAlchemy>=2.0`
   - `PyMySQL>=1.1.0`

2) Set environment variable (example):

```bash
# MySQL 8 (example)
setx DATABASE_URL "mysql+pymysql://mcp_user:secret@127.0.0.1:3308/mcp_autoscaler"
```

3) Initialize database:

- Execute the SQL file on your MySQL server:

```sql
SOURCE db/schema_mvp.sql;
```

## What gets persisted

- repositories: pseudo repository row per github_url (`service://<github_url>`) created on first request
- plan_requests: one row per `/plans` call
- predictions: 24h prediction array as JSON, model version, recommended instance bounds, expected cost
- anomaly_detections: z-score based anomaly (optional, automatic)
- alert_history: Discord alert attempts and results (optional)

## Safety

- If `DATABASE_URL` is not set or invalid, all DB calls become no-ops; API keeps working.
- Errors during persistence are swallowed and logged at debug level.

