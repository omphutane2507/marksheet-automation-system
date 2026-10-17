-- =============================================================================
-- Run this in pgAdmin → student_analysis server → Query Tool
-- =============================================================================

-- Step 1: Create the dedicated user
CREATE USER school_marks_user WITH PASSWORD 'school123';

-- Step 2: Create the database
CREATE DATABASE school_marks_db OWNER school_marks_user;

-- Step 3: Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE school_marks_db TO school_marks_user;
