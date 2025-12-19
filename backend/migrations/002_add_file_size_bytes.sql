-- Migration: Add file_size_bytes column to deliverables table
-- Date: 2025-12-19
-- Purpose: Store actual file size for deliverables

-- Add file_size_bytes column
ALTER TABLE deliverables ADD COLUMN file_size_bytes INTEGER;

-- Create index for potential sorting by file size
CREATE INDEX IF NOT EXISTS idx_deliverables_file_size ON deliverables(file_size_bytes);
