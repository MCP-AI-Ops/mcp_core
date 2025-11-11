-- Migration Example: Add user preferences
-- Filename: 20250112_1200_add_user_preferences.sql
-- This is an example of how to create a migration file for future schema changes

-- Add user preferences columns to users table
ALTER TABLE users 
ADD COLUMN preferences JSON COMMENT 'User preferences and settings',
ADD COLUMN timezone VARCHAR(64) DEFAULT 'UTC' COMMENT 'User timezone',
ADD COLUMN language VARCHAR(10) DEFAULT 'ko' COMMENT 'Preferred language (ko, en, etc.)';

-- Create index for faster timezone queries
CREATE INDEX idx_timezone ON users(timezone);

-- Add comment to document the change
-- Migration applied on: [DATE]
-- Author: [NAME]
-- Description: Added user preferences and localization support
