-- PostgreSQL initialization script for Tenga Inventory POS
-- This script is automatically run on first container startup

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Log initialization
SELECT 'Database initialized for Tenga Inventory POS' as message;
