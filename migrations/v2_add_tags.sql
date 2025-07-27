-- Migration v2: Add Tags System for Account Management
-- This migration adds support for tagging accounts and copying actions between accounts

-- Start transaction for atomic update
BEGIN TRANSACTION;

-- 1. Create tags table
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#6B7280', -- Default gray color
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create account_tags junction table for many-to-many relationship
CREATE TABLE IF NOT EXISTS account_tags (
    account_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, tag_id),
    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_account_tags_account_id ON account_tags(account_id);
CREATE INDEX IF NOT EXISTS idx_account_tags_tag_id ON account_tags(tag_id);

-- 4. Insert some default tags (optional - remove if not needed)
INSERT OR IGNORE INTO tags (name, color) VALUES 
    ('primary', '#3B82F6'),     -- blue
    ('secondary', '#10B981'),   -- green
    ('testing', '#F59E0B'),     -- amber
    ('inactive', '#6B7280'),    -- gray
    ('vip', '#8B5CF6');         -- purple

-- Commit transaction
COMMIT;

-- Rollback commands (save these for emergency rollback)
-- DROP TABLE IF EXISTS account_tags;
-- DROP TABLE IF EXISTS tags;
-- DROP INDEX IF EXISTS idx_tags_name;
-- DROP INDEX IF EXISTS idx_account_tags_account_id;
-- DROP INDEX IF EXISTS idx_account_tags_tag_id;