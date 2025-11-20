"""Metric history ingestion placeholder.

Usage examples:
  # In container or local env (ensure DATABASE_URL points to MySQL)
  python scripts/ingest_metric_history.py --csv data/lstm_ready_cluster_data.csv \
      --github-url https://github.com/MCP-AI-Ops/mcp_core --metric total_events \
      --time-column timestamp --value-column total_events

This script demonstrates how to batch-load raw metric rows into the
`metric_history` table for later feature extraction / model training.

It intentionally keeps logic minimal; customize parsing or time-zone
handling as needed. For large files consider chunked reading.
"""
from __future__ import annotations

import os
import argparse
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text


def get_engine() -> any:
    url = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://mcp_user:wjdwlsgh03@localhost:3306/mcp_core",
    )
    return create_engine(url, pool_pre_ping=True, future=True)


def ingest(
    engine,
    csv_path: str,
    github_url: str,
    metric_name: str,
    time_column: str,
    value_column: str,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    df = pd.read_csv(csv_path)
    if limit:
        df = df.head(limit)
    if time_column not in df.columns or value_column not in df.columns:
        raise ValueError("Missing required columns in CSV")

    rows = []
    for _, r in df.iterrows():
        ts_raw = r[time_column]
        # Try ISO or fallback epoch seconds
        if isinstance(ts_raw, (int, float)):
            ts = datetime.utcfromtimestamp(int(ts_raw))
        else:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", ""))
        value = float(r[value_column])
        rows.append({"github_url": github_url, "ts": ts, "metric_name": metric_name, "value": value})

    if dry_run:
        print(f"[dry-run] Would insert {len(rows)} rows")
        return len(rows)

    insert_sql = text(
        """
        INSERT IGNORE INTO metric_history (github_url, ts, metric_name, value)
        VALUES (:github_url, :ts, :metric_name, :value)
        """
    )
    with engine.begin() as conn:
        conn.execute(insert_sql, rows)
    print(f"Inserted {len(rows)} rows into metric_history")
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest metrics into metric_history")
    ap.add_argument("--csv", required=True, help="CSV file path")
    ap.add_argument("--github-url", required=True, help="Repository URL")
    ap.add_argument("--metric", required=True, help="Metric name to store")
    ap.add_argument("--time-column", default="timestamp", help="Time column name in CSV")
    ap.add_argument("--value-column", required=True, help="Value column name in CSV")
    ap.add_argument("--limit", type=int, default=None, help="Optional limit for rows")
    ap.add_argument("--dry-run", action="store_true", help="Do not insert, only count")
    args = ap.parse_args()

    engine = get_engine()
    ingest(
        engine,
        csv_path=args.csv,
        github_url=args.github_url,
        metric_name=args.metric,
        time_column=args.time_column,
        value_column=args.value_column,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
