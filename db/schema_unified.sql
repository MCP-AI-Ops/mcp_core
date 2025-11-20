-- Unified MCP Core Schema (MySQL 8)
-- Minimal production set: context, feature snapshot, prediction, optional points, metric history, anomalies, alerts.
-- Database name aligned to docker-compose: mcp_core
-- Apply order: create DB, use DB, create tables.

CREATE DATABASE IF NOT EXISTS mcp_core
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE mcp_core;

-- 1. MCP Context snapshots
CREATE TABLE IF NOT EXISTS mcp_contexts (
  context_id CHAR(36) PRIMARY KEY COMMENT 'UUID',
  user_id VARCHAR(100) NULL COMMENT '사용자 식별자',
  github_url VARCHAR(500) NOT NULL,
  requirements_text TEXT NULL COMMENT '사용자 자연어 요구사항 원본',
  service_type ENUM('web','api','db') NOT NULL DEFAULT 'web',
  runtime_env ENUM('prod','dev') NOT NULL DEFAULT 'prod',
  time_slot ENUM('peak','normal','low','weekend') NOT NULL DEFAULT 'normal',
  expected_users INT UNSIGNED NULL,
  region VARCHAR(50) NULL,
  request_timestamp DATETIME NOT NULL COMMENT '요청 시각 (MCPContext.timestamp)',
  context_json JSON NOT NULL COMMENT 'Claude 변환 전체 컨텍스트',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_time (user_id, created_at DESC),
  INDEX idx_github (github_url),
  INDEX idx_time_slot (time_slot),
  FULLTEXT idx_requirements (requirements_text)
) ENGINE=InnoDB COMMENT='MCP 컨텍스트 스냅샷';

-- 2. Feature snapshots
CREATE TABLE IF NOT EXISTS prediction_features (
  feature_snapshot_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  context_id CHAR(36) NOT NULL,
  github_url VARCHAR(500) NOT NULL,
  window_start DATETIME NOT NULL COMMENT '사용된 feature 시작',
  window_end DATETIME NOT NULL COMMENT '사용된 feature 종료',
  sequence_length INT NOT NULL COMMENT '시퀀스 길이 (예: 24)',
  feature_count INT NOT NULL COMMENT 'feature 개수 (예: 79)',
  features_json JSON NOT NULL COMMENT 'feature 이름/값 묶음',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (context_id) REFERENCES mcp_contexts(context_id) ON DELETE CASCADE,
  INDEX idx_context (context_id),
  INDEX idx_github_window (github_url, window_end DESC)
) ENGINE=InnoDB COMMENT='예측에 사용된 feature 스냅샷';

-- 3. Processed predictions
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  context_id CHAR(36) NOT NULL,
  feature_snapshot_id BIGINT UNSIGNED NOT NULL,
  user_id VARCHAR(100) NULL COMMENT '예측 요청 사용자',
  github_url VARCHAR(500) NOT NULL,
  metric_name VARCHAR(100) NOT NULL,
  model_version VARCHAR(100) NOT NULL,
  generated_at DATETIME NOT NULL COMMENT '예측 생성 시각',
  horizon_hours INT NOT NULL DEFAULT 24,
  predictions_json JSON NOT NULL COMMENT '24시간 [{time, value}, ...]',
  scale_factor DECIMAL(12,6) NULL COMMENT '스케일 팩터',
  recommended_flavor ENUM('small','medium','large') NULL,
  min_instances TINYINT UNSIGNED DEFAULT 1,
  max_instances TINYINT UNSIGNED DEFAULT 3,
  expected_cost_per_day DECIMAL(10,2) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (context_id) REFERENCES mcp_contexts(context_id) ON DELETE CASCADE,
  FOREIGN KEY (feature_snapshot_id) REFERENCES prediction_features(feature_snapshot_id) ON DELETE CASCADE,
  INDEX idx_user_time (user_id, generated_at DESC),
  INDEX idx_github_metric (github_url, metric_name, generated_at DESC),
  INDEX idx_model (model_version)
) ENGINE=InnoDB COMMENT='후처리된 예측 결과';

-- 4. 옵션: 개별 시각별 포인트
CREATE TABLE IF NOT EXISTS prediction_points (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  prediction_id BIGINT UNSIGNED NOT NULL,
  forecast_time DATETIME NOT NULL COMMENT '예측 대상 시각',
  predicted_value DOUBLE NOT NULL,
  actual_value DOUBLE NULL COMMENT '실제 발생 값',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE CASCADE,
  INDEX idx_prediction (prediction_id),
  INDEX idx_forecast_time (forecast_time)
) ENGINE=InnoDB COMMENT='시간별 예측값';

-- 5. 모델 학습/특징 소스용 시계열
CREATE TABLE IF NOT EXISTS metric_history (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  github_url VARCHAR(200) NOT NULL,
  ts DATETIME NOT NULL COMMENT 'UTC 타임스탬프',
  metric_name VARCHAR(100) NOT NULL,
  value DOUBLE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_metric (github_url, ts, metric_name),
  INDEX idx_github_url (github_url),
  INDEX idx_metric_name (metric_name),
  INDEX idx_ts (ts)
) ENGINE=InnoDB COMMENT='모델 feature 시계열';

-- 6. 이상 탐지 기록 – 확장용
CREATE TABLE IF NOT EXISTS anomaly_detections (
  anomaly_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  prediction_id BIGINT UNSIGNED NULL,
  github_url VARCHAR(500) NOT NULL,
  detected_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
  anomaly_type VARCHAR(50) DEFAULT 'deviation',
  severity ENUM('low','medium','high','critical') DEFAULT 'medium',
  anomaly_score DECIMAL(10,6) NOT NULL,
  detail_json JSON NULL,
  alert_sent BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE SET NULL,
  INDEX idx_repo_time (github_url, detected_at)
) ENGINE=InnoDB COMMENT='이상 탐지 기록';

-- 7. 알림 발송 이력 – 확장용
CREATE TABLE IF NOT EXISTS alert_history (
  alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  github_url VARCHAR(500) NOT NULL,
  created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
  alert_type ENUM('threshold','anomaly','scaling','info') NOT NULL DEFAULT 'anomaly',
  severity ENUM('info','warning','error','critical') NOT NULL DEFAULT 'warning',
  title VARCHAR(200) NOT NULL,
  message TEXT NOT NULL,
  channels JSON NOT NULL,
  status ENUM('pending','sent','failed') DEFAULT 'pending',
  response_text TEXT NULL,
  INDEX idx_repo_alerts (github_url, created_at)
) ENGINE=InnoDB COMMENT='알림 이력';

-- Legacy cleanup (if old tables remain)
DROP TABLE IF EXISTS plan_requests;
-- Older predictions table replaced by new schema above.
-- repositories omitted; add separately if multi-repo registry needed.

-- End unified schema.