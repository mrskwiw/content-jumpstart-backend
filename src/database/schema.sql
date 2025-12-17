-- Revision Management Database Schema
-- SQLite schema for tracking projects, revisions, and client history

-- Projects: Each deliverable generation is a project
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,  -- Format: ClientName_YYYYMMDD_HHMMSS
    client_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deliverable_path TEXT NOT NULL,
    brief_path TEXT,
    num_posts INTEGER NOT NULL,
    quality_profile_name TEXT,
    status TEXT DEFAULT 'completed',  -- completed, in_progress, archived
    notes TEXT,
    UNIQUE(project_id)
);

CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_name);
CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at);

-- Revisions: Track revision requests per project
CREATE TABLE IF NOT EXISTS revisions (
    revision_id TEXT PRIMARY KEY,  -- Format: {project_id}_rev_{n}
    project_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,  -- 1-5 (scope limit)
    status TEXT DEFAULT 'pending',  -- pending, in_progress, completed, failed
    feedback TEXT NOT NULL,  -- Client's revision request
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    cost REAL DEFAULT 0.0,  -- API cost for this revision
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    UNIQUE(project_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_revisions_project ON revisions(project_id);
CREATE INDEX IF NOT EXISTS idx_revisions_status ON revisions(status);

-- Revision Posts: Individual posts that were revised
CREATE TABLE IF NOT EXISTS revision_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id TEXT NOT NULL,
    post_index INTEGER NOT NULL,  -- 1-30
    template_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
    original_content TEXT NOT NULL,
    original_word_count INTEGER,
    revised_content TEXT NOT NULL,
    revised_word_count INTEGER,
    changes_summary TEXT,  -- Human-readable summary of changes
    FOREIGN KEY (revision_id) REFERENCES revisions(revision_id)
);

CREATE INDEX IF NOT EXISTS idx_revision_posts_revision ON revision_posts(revision_id);

-- Client History: Aggregated stats per client (Phase 8B - Client Memory)
CREATE TABLE IF NOT EXISTS client_history (
    client_name TEXT PRIMARY KEY,
    first_project_date TIMESTAMP,
    last_project_date TIMESTAMP,
    total_projects INTEGER DEFAULT 0,
    total_posts_generated INTEGER DEFAULT 0,
    total_revisions INTEGER DEFAULT 0,
    lifetime_value REAL DEFAULT 0.0,
    average_satisfaction REAL,  -- 1-10 scale
    notes TEXT,

    -- Phase 8B: Preference Tracking
    preferred_templates TEXT,  -- JSON array [1,3,5,7] - templates that work well
    avoided_templates TEXT,    -- JSON array [6,12] - templates revised frequently
    voice_adjustments TEXT,    -- JSON {"tone": "more_casual", "length": "shorter"}
    optimal_word_count_min INTEGER DEFAULT 150,
    optimal_word_count_max INTEGER DEFAULT 250,
    preferred_cta_types TEXT,  -- JSON ["question", "engagement"]

    -- Phase 8B: Voice Patterns
    voice_archetype TEXT,  -- Expert, Friend, Innovator, Guide, Motivator
    average_readability_score REAL,
    signature_phrases TEXT,  -- JSON array of client's consistent phrases

    -- Phase 8B: Quality Profile
    custom_quality_profile_json TEXT,  -- JSON-serialized QualityProfile

    -- Phase 8B: Relationship
    next_project_discount REAL DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Phase 8C: Voice Sample Uploads
    has_voice_samples BOOLEAN DEFAULT 0,
    voice_samples_upload_date TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_client_history_name ON client_history(client_name);
CREATE INDEX IF NOT EXISTS idx_client_history_updated ON client_history(last_updated);

-- Revision Scope Tracking: Track scope usage per project
CREATE TABLE IF NOT EXISTS revision_scope (
    project_id TEXT PRIMARY KEY,
    allowed_revisions INTEGER DEFAULT 5,  -- Contract scope limit
    used_revisions INTEGER DEFAULT 0,
    remaining_revisions INTEGER DEFAULT 5,
    scope_exceeded BOOLEAN DEFAULT 0,
    upsell_offered BOOLEAN DEFAULT 0,
    upsell_accepted BOOLEAN DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- Template Performance: Track which templates get revised often (for optimization)
CREATE TABLE IF NOT EXISTS template_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    template_id INTEGER NOT NULL,
    usage_count INTEGER DEFAULT 0,
    revision_count INTEGER DEFAULT 0,
    revision_rate REAL DEFAULT 0.0,  -- revision_count / usage_count
    last_used TIMESTAMP,

    -- Phase 8B: Quality Metrics
    average_quality_score REAL DEFAULT 0.0,
    client_kept_count INTEGER DEFAULT 0,  -- Posts not revised

    UNIQUE(client_name, template_id)
);

CREATE INDEX IF NOT EXISTS idx_template_perf_client ON template_performance(client_name);
CREATE INDEX IF NOT EXISTS idx_template_perf_template ON template_performance(template_id);
CREATE INDEX IF NOT EXISTS idx_template_perf_client_template ON template_performance(client_name, template_id);

-- Phase 8B: Client Feedback Themes - Track recurring feedback patterns
CREATE TABLE IF NOT EXISTS client_feedback_themes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    theme_type TEXT NOT NULL,  -- 'tone', 'length', 'cta', 'data_usage', 'structure', 'emoji'
    feedback_phrase TEXT NOT NULL,  -- "more casual", "too long", "add emoji", etc.
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_name) REFERENCES client_history(client_name)
);

CREATE INDEX IF NOT EXISTS idx_feedback_themes_client ON client_feedback_themes(client_name);
CREATE INDEX IF NOT EXISTS idx_feedback_themes_type ON client_feedback_themes(theme_type);
CREATE INDEX IF NOT EXISTS idx_feedback_themes_client_type ON client_feedback_themes(client_name, theme_type);

-- Phase 8B: Client Voice Samples - Store analyzed voice guides for pattern synthesis
CREATE TABLE IF NOT EXISTS client_voice_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    project_id TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Voice Metrics
    average_readability REAL,
    voice_archetype TEXT,  -- Expert, Friend, Innovator, Guide, Motivator
    dominant_tone TEXT,
    average_word_count INTEGER,
    question_usage_rate REAL,

    -- Patterns (stored as JSON)
    common_hooks TEXT,        -- JSON array of opening hook patterns
    common_transitions TEXT,  -- JSON array of transition phrases
    common_ctas TEXT,         -- JSON array of CTA patterns
    key_phrases TEXT,         -- JSON array of recurring phrases

    FOREIGN KEY (client_name) REFERENCES client_history(client_name),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_voice_samples_client ON client_voice_samples(client_name);
CREATE INDEX IF NOT EXISTS idx_voice_samples_project ON client_voice_samples(project_id);
CREATE INDEX IF NOT EXISTS idx_voice_samples_date ON client_voice_samples(generated_at);

-- Phase 8C: Voice Sample Uploads - Client-provided content samples for voice matching
CREATE TABLE IF NOT EXISTS voice_sample_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sample_text TEXT NOT NULL,
    sample_source TEXT NOT NULL,  -- linkedin, blog, twitter, email, mixed
    word_count INTEGER NOT NULL,
    file_name TEXT,

    FOREIGN KEY (client_name) REFERENCES client_history(client_name)
);

CREATE INDEX IF NOT EXISTS idx_voice_uploads_client ON voice_sample_uploads(client_name);
CREATE INDEX IF NOT EXISTS idx_voice_uploads_date ON voice_sample_uploads(upload_date);
CREATE INDEX IF NOT EXISTS idx_voice_uploads_source ON voice_sample_uploads(sample_source);

-- Phase 8D: Post Feedback - Track post performance and client feedback
CREATE TABLE IF NOT EXISTS post_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    project_id TEXT NOT NULL,
    post_id TEXT NOT NULL,  -- Content hash or index
    template_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK(feedback_type IN ('kept', 'modified', 'rejected', 'loved')),
    modification_notes TEXT,
    feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Engagement metrics (JSON)
    engagement_data TEXT,  -- {"likes": 100, "comments": 20, "shares": 15, "clicks": 50}

    FOREIGN KEY (client_name) REFERENCES client_history(client_name),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_post_feedback_client ON post_feedback(client_name);
CREATE INDEX IF NOT EXISTS idx_post_feedback_project ON post_feedback(project_id);
CREATE INDEX IF NOT EXISTS idx_post_feedback_type ON post_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_post_feedback_template ON post_feedback(template_id);
CREATE INDEX IF NOT EXISTS idx_post_feedback_date ON post_feedback(feedback_date);

-- Phase 8D: Client Satisfaction - Survey responses
CREATE TABLE IF NOT EXISTS client_satisfaction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    project_id TEXT NOT NULL,

    -- Ratings (1-5 scale)
    satisfaction_score INTEGER CHECK(satisfaction_score BETWEEN 1 AND 5),
    quality_rating INTEGER CHECK(quality_rating BETWEEN 1 AND 5),
    voice_match_rating INTEGER CHECK(voice_match_rating BETWEEN 1 AND 5),

    -- Recommendation
    would_recommend BOOLEAN,

    -- Qualitative feedback
    feedback_text TEXT,
    strengths TEXT,  -- What worked well
    improvements TEXT,  -- What could be better

    collected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (client_name) REFERENCES client_history(client_name),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE INDEX IF NOT EXISTS idx_satisfaction_client ON client_satisfaction(client_name);
CREATE INDEX IF NOT EXISTS idx_satisfaction_project ON client_satisfaction(project_id);
CREATE INDEX IF NOT EXISTS idx_satisfaction_date ON client_satisfaction(collected_date);
CREATE INDEX IF NOT EXISTS idx_satisfaction_score ON client_satisfaction(satisfaction_score);

-- Phase 8D: System Metrics - Daily aggregated performance metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    metric_type TEXT NOT NULL CHECK(metric_type IN ('generation', 'quality', 'cost', 'client', 'template')),
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,

    -- Additional context (JSON)
    metadata TEXT,

    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(metric_date, metric_type, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON system_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON system_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_date_type ON system_metrics(metric_date, metric_type);

-- Views for common queries

-- Active projects with revision status
CREATE VIEW IF NOT EXISTS project_revision_status AS
SELECT
    p.project_id,
    p.client_name,
    p.created_at,
    p.num_posts,
    COUNT(r.revision_id) as total_revisions,
    rs.allowed_revisions,
    rs.remaining_revisions,
    rs.scope_exceeded
FROM projects p
LEFT JOIN revisions r ON p.project_id = r.project_id
LEFT JOIN revision_scope rs ON p.project_id = rs.project_id
WHERE p.status = 'completed'
GROUP BY p.project_id;

-- Client revision summary
CREATE VIEW IF NOT EXISTS client_revision_summary AS
SELECT
    ch.client_name,
    ch.total_projects,
    ch.total_revisions,
    ROUND(CAST(ch.total_revisions AS REAL) / ch.total_projects, 2) as avg_revisions_per_project,
    ch.lifetime_value
FROM client_history ch
WHERE ch.total_projects > 0;
