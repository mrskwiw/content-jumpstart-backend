-- Migration: Add composite indexes to posts table
-- Date: 2025-12-15
-- Description: Adds composite indexes to improve query performance

-- Composite indexes for common filter combinations
CREATE INDEX IF NOT EXISTS ix_posts_project_status ON posts(project_id, status);
CREATE INDEX IF NOT EXISTS ix_posts_status_created ON posts(status, created_at);
CREATE INDEX IF NOT EXISTS ix_posts_platform_status ON posts(target_platform, status);

-- Single column indexes for common searches
CREATE INDEX IF NOT EXISTS ix_posts_template_name ON posts(template_name);
CREATE INDEX IF NOT EXISTS ix_posts_word_count ON posts(word_count);
CREATE INDEX IF NOT EXISTS ix_posts_readability ON posts(readability_score);

-- Performance notes:
-- - ix_posts_project_status: Speeds up filtered queries like "get posts by project with status=approved"
-- - ix_posts_status_created: Speeds up status filtering with time-based ordering
-- - ix_posts_platform_status: Speeds up platform-specific status queries
-- - ix_posts_template_name: Improves ILIKE searches on template names
-- - ix_posts_word_count: Speeds up range queries (min/max word count filters)
-- - ix_posts_readability: Speeds up readability score range queries
