-- ============================================
-- MCP Core - User Authentication Schema
-- ============================================
-- This schema provides user management and cloud account integration
-- for the MCP Core orchestrator system.

-- Users Table
-- Stores user authentication information and cloud provider credentials
CREATE TABLE IF NOT EXISTS users (
    -- Primary Key
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    
    -- Authentication Fields
    username            VARCHAR(64) NOT NULL UNIQUE,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    
    -- User Profile
    full_name           VARCHAR(128),
    organization        VARCHAR(128),
    
    -- Account Status
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    email_verified_at   DATETIME,
    
    -- Cloud Provider Integration
    -- Supports AWS, Azure, GCP, and other cloud providers
    cloud_provider      ENUM('aws', 'azure', 'gcp', 'alibaba', 'oracle', 'ibm', 'other') DEFAULT NULL,
    cloud_account_id    VARCHAR(128),
    cloud_region        VARCHAR(64),
    cloud_access_key    VARCHAR(512),      -- Encrypted access key
    cloud_secret_key    VARCHAR(512),      -- Encrypted secret key
    cloud_tenant_id     VARCHAR(128),      -- For Azure
    cloud_project_id    VARCHAR(128),      -- For GCP
    cloud_config_json   JSON,              -- Additional cloud-specific configuration
    
    -- API Access
    api_key             VARCHAR(128) UNIQUE,
    api_key_expires_at  DATETIME,
    
    -- Session Management
    last_login_at       DATETIME,
    last_login_ip       VARCHAR(45),       -- IPv6 compatible
    failed_login_count  INT DEFAULT 0,
    locked_until        DATETIME,
    
    -- Security
    two_factor_enabled  BOOLEAN DEFAULT FALSE,
    two_factor_secret   VARCHAR(255),      -- Encrypted TOTP secret
    backup_codes        JSON,              -- Encrypted backup codes array
    
    -- Timestamps
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME,          -- Soft delete support
    
    -- Indexes for performance
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_api_key (api_key),
    INDEX idx_cloud_provider (cloud_provider),
    INDEX idx_is_active (is_active),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Sessions Table
-- Tracks active user sessions for security and audit purposes
CREATE TABLE IF NOT EXISTS user_sessions (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED NOT NULL,
    session_token       VARCHAR(255) NOT NULL UNIQUE,
    ip_address          VARCHAR(45),
    user_agent          VARCHAR(512),
    expires_at          DATETIME NOT NULL,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_session_token (session_token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Password Reset Tokens Table
-- Manages password reset workflow
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED NOT NULL,
    token               VARCHAR(255) NOT NULL UNIQUE,
    expires_at          DATETIME NOT NULL,
    used_at             DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_token (token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Email Verification Tokens Table
-- Manages email verification workflow
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED NOT NULL,
    token               VARCHAR(255) NOT NULL UNIQUE,
    expires_at          DATETIME NOT NULL,
    verified_at         DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_token (token),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit Log Table
-- Tracks all user actions for security and compliance
CREATE TABLE IF NOT EXISTS user_audit_log (
    id                  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id             BIGINT UNSIGNED,
    action              VARCHAR(128) NOT NULL,
    resource_type       VARCHAR(64),
    resource_id         VARCHAR(128),
    ip_address          VARCHAR(45),
    user_agent          VARCHAR(512),
    metadata            JSON,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at),
    INDEX idx_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
