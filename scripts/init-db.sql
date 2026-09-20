-- Initialize database for Reyex Support Bot
-- This script runs automatically when PostgreSQL container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database (if not exists)
-- Note: This is handled by the POSTGRES_DB environment variable
