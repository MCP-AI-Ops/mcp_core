-- MCP Core MVP 스키마 (MySQL 8)
-- 저장소, 플랜 요청, 예측, 이상 탐지, 알림 이력을 저장하는 최소 테이블

CREATE DATABASE IF NOT EXISTS mcp_autoscaler
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE mcp_autoscaler;

-- 저장소 (서비스 또는 코드 저장소 식별)
CREATE TABLE IF NOT EXISTS repositories (
  repo_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '저장소 고유 ID',
  repo_url VARCHAR(500) NOT NULL COMMENT '저장소 URL',
  repo_name VARCHAR(200) NOT NULL COMMENT '저장소 이름',
  repo_provider ENUM('github','gitlab','bitbucket','unknown') NOT NULL DEFAULT 'unknown' COMMENT '저장소 제공자',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시각',
  UNIQUE KEY uk_repo_url (repo_url),
  INDEX idx_repo_name (repo_name)
) ENGINE=InnoDB COMMENT='서비스/저장소 식별 레지스트리';

-- 플랜 요청 (요청된 내용)
CREATE TABLE IF NOT EXISTS plan_requests (
  plan_request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '플랜 요청 고유 ID',
  repo_id BIGINT UNSIGNED NOT NULL COMMENT '저장소 ID (FK)',
  github_url VARCHAR(200) NOT NULL COMMENT '서비스 식별자',
  metric_name VARCHAR(100) NOT NULL COMMENT '메트릭 이름',
  context_json JSON NOT NULL COMMENT '추출된 MCPContext (JSON)',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '요청 시각',
  FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
  INDEX idx_repo_time (repo_id, created_at DESC)
) ENGINE=InnoDB COMMENT='수신된 /plans 요청';

-- 예측 (단일 메트릭 배열)
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '예측 고유 ID',
  repo_id BIGINT UNSIGNED NOT NULL COMMENT '저장소 ID (FK)',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '예측 생성 시각',
  prediction_start TIMESTAMP NOT NULL COMMENT '예측 시작 시각',
  prediction_horizon_hours INT DEFAULT 24 COMMENT '예측 범위 (시간 단위)',
  metric_name VARCHAR(100) NOT NULL COMMENT '예측 대상 메트릭',
  model_version VARCHAR(50) NOT NULL COMMENT '사용한 모델 버전',
  predicted_values JSON NOT NULL CHECK (JSON_TYPE(predicted_values) = 'ARRAY') COMMENT '예측 값 배열',
  recommended_min_instances TINYINT UNSIGNED DEFAULT 1 COMMENT '권장 최소 인스턴스 수',
  recommended_max_instances TINYINT UNSIGNED DEFAULT 3 COMMENT '권장 최대 인스턴스 수',
  expected_cost_per_day DECIMAL(10,2) DEFAULT NULL COMMENT '예상 일일 비용',
  FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
  INDEX idx_repo_pred (repo_id, created_at DESC)
) ENGINE=InnoDB COMMENT='24시간 단일 메트릭 예측';

-- 이상 탐지 (최소 구성)
CREATE TABLE IF NOT EXISTS anomaly_detections (
  anomaly_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '이상 탐지 고유 ID',
  repo_id BIGINT UNSIGNED NOT NULL COMMENT '저장소 ID (FK)',
  prediction_id BIGINT UNSIGNED NULL COMMENT '예측 ID (FK, NULL 가능)',
  detected_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT '탐지 시각',
  anomaly_type VARCHAR(50) DEFAULT 'deviation' COMMENT '이상 유형',
  severity ENUM('low','medium','high','critical') DEFAULT 'medium' COMMENT '심각도',
  anomaly_score DECIMAL(10,6) NOT NULL COMMENT '이상 점수 (z-score 등)',
  detail_json JSON NULL COMMENT '상세 정보 (JSON)',
  alert_sent BOOLEAN DEFAULT FALSE COMMENT '알림 전송 여부',
  FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
  FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id) ON DELETE SET NULL,
  INDEX idx_repo_time (repo_id, detected_at)
) ENGINE=InnoDB COMMENT='이상 탐지 기록';

-- 알림 이력 (Discord 등)
CREATE TABLE IF NOT EXISTS alert_history (
  alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '알림 고유 ID',
  repo_id BIGINT UNSIGNED NOT NULL COMMENT '저장소 ID (FK)',
  created_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3) COMMENT '알림 생성 시각',
  alert_type ENUM('threshold','anomaly','scaling','info') NOT NULL DEFAULT 'anomaly' COMMENT '알림 유형',
  severity ENUM('info','warning','error','critical') NOT NULL DEFAULT 'warning' COMMENT '알림 심각도',
  title VARCHAR(200) NOT NULL COMMENT '알림 제목',
  message TEXT NOT NULL COMMENT '알림 메시지',
  channels JSON NOT NULL COMMENT '전송 채널 목록',
  status ENUM('pending','sent','failed') DEFAULT 'pending' COMMENT '전송 상태',
  response_text TEXT NULL COMMENT '응답 메시지 (실패 시)',
  FOREIGN KEY (repo_id) REFERENCES repositories(repo_id) ON DELETE CASCADE,
  INDEX idx_repo_alerts (repo_id, created_at)
) ENGINE=InnoDB COMMENT='전송된 알림 로그';
