# AGENTS.md

## Review guidelines

- Always write review comments in Korean.
- Keep technical terms in English when they are standard in software engineering or machine learning.
- Be concise, but explain why the issue matters and how to fix it.
- Prioritize real bugs, regressions, security issues, deployment risks, and ML/data issues over style nitpicks.
- Avoid commenting on trivial formatting unless it can cause misunderstanding.

## Project context

This repository is for an AI-Ops / MLOps style platform that includes:
- FastAPI backend
- OpenStack-related deployment/infrastructure integration
- ML-based prediction and anomaly detection pipelines
- Docker / GitHub Actions / self-hosted runner based deployment
- Database and metrics processing logic

When reviewing code, use this context and focus on operational safety and production reliability.

## What to focus on

### 1. Backend / API correctness
- Check for broken FastAPI route logic, invalid request/response handling, and exception paths.
- Flag missing validation, weak error handling, and inconsistent response formats.
- Check whether authentication or authorization-related logic is missing or bypassable.
- Watch for blocking I/O or heavy computation inside request handlers.

### 2. ML / data pipeline risks
- Look for possible data leakage between train/validation/test.
- Check whether feature generation uses future information accidentally.
- Flag inconsistent preprocessing between training and inference.
- Check whether saved model artifacts, metadata, and scalers stay in sync.
- Watch for silent fallback behavior that could hide model failure.
- Flag suspicious metric calculations or evaluation logic.
- Check whether anomaly thresholds, smoothing, aggregation, or time-window logic can produce misleading alerts.

### 3. Time-series / forecasting issues
- Be sensitive to ordering bugs, timestamp alignment problems, resampling errors, and off-by-one mistakes.
- Flag train/test splits that ignore temporal order.
- Check whether forward fill, interpolation, clipping, normalization, or lag feature generation can distort real behavior.
- Watch for target leakage through rolling statistics or future-dependent transformations.

### 4. Infra / deployment safety
- Check whether Docker, GitHub Actions, and deployment logic can break production unexpectedly.
- Flag risky shell commands, destructive cleanup, and commands that may impact unrelated containers or files.
- Check for mistakes in image tags, registry login flow, compose commands, and self-hosted runner cleanup.
- Watch for secrets accidentally exposed in logs, code, workflow files, or exception messages.

### 5. Database / persistence
- Flag schema mismatches, unsafe migrations, missing transactions, and inconsistent model persistence behavior.
- Check whether writes are idempotent where needed.
- Watch for race conditions or duplicate inserts in metric/history/alert flows.

### 6. Security
- Flag hardcoded secrets, tokens, endpoints, or credentials.
- Flag missing permission checks.
- Flag dangerous deserialization, shell injection risks, path traversal risks, and unsafe subprocess usage.
- Be strict about logging sensitive operational data.

## Review style

For each important issue:
- State the problem clearly in Korean.
- Explain why it is risky.
- Suggest a concrete fix.
- If severity is high, say so explicitly.

Preferred tone example:
- "이 부분은 `train/test leakage` 가능성이 있습니다."
- "현재 구현은 예측 시점 이후의 정보를 참조할 수 있어 시계열 평가가 왜곡될 수 있습니다."
- "이 workflow 단계는 self-hosted runner 환경에서 과도하게 파괴적일 수 있습니다."

## What to ignore unless severe

- Minor naming preferences
- Personal style preferences
- Formatting differences already handled by formatter/linter
- Non-critical refactors that do not affect correctness, safety, or maintainability

## Extra instructions

- When possible, prefer comments on correctness, reliability, and production impact.
- For ML-related pull requests, review like a careful ML engineer, not just a general code reviewer.
- For deployment-related pull requests, review like a cautious DevOps engineer.
- If a change looks intentional but risky, call out the risk without assuming the author is wrong.