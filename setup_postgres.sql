-- =============================================================================
-- PostgreSQL Setup Script for School Marks Dashboard
-- Run this in pgAdmin Query Tool or psql as the 'postgres' superuser
-- =============================================================================

-- 1. Create the database user
CREATE USER school_marks_user WITH PASSWORD 'your_secure_password_here';

-- 2. Create the database
CREATE DATABASE school_marks_db
    OWNER school_marks_user
    ENCODING 'UTF8'
    LC_COLLATE 'en-US'
    LC_CTYPE 'en-US'
    TEMPLATE template0;

-- 3. Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE school_marks_db TO school_marks_user;

-- 4. Connect to the new database (run this separately in pgAdmin)
-- \c school_marks_db

-- 5. Grant schema privileges (run this AFTER connecting to school_marks_db)
GRANT ALL ON SCHEMA public TO school_marks_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO school_marks_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO school_marks_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO school_marks_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO school_marks_user;

-- =============================================================================
-- VERIFICATION: After running Django migrations, verify tables were created:
-- =============================================================================
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
--
-- Expected tables:
--   marks_academicyear
--   marks_classroom
--   marks_student
--   marks_subject
--   marks_mark
--   marks_graderule
--   auth_user (Django auth tables)
--   django_* (Django system tables)
-- =============================================================================
