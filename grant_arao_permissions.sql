-- ============================================================================
-- Grant permissions on arao catalog to Metadata Manager app
-- Run this in FEVM SQL warehouse
-- ============================================================================

-- Step 1: Identify the app's service principal
-- Run this first to see what the current_user is when the app runs:
-- SELECT current_user();

-- Step 2: Grant permissions to the app
-- The service principal name is typically 'metadata-manager' or might include a UUID

-- Grant USE CATALOG permission
GRANT USE CATALOG ON CATALOG arao TO `metadata-manager`;

-- Grant USE SCHEMA permissions
GRANT USE SCHEMA ON SCHEMA arao.metadata_manager TO `metadata-manager`;
GRANT USE SCHEMA ON SCHEMA arao.metadata_test TO `metadata-manager`;

-- Grant SELECT on all tables in metadata_test (for browsing test data)
GRANT SELECT ON SCHEMA arao.metadata_test TO `metadata-manager`;

-- Grant ALL PRIVILEGES on metadata_manager schema (app needs to read/write)
GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `metadata-manager`;

-- If the above fails, try with the full service principal name format:
-- GRANT USE CATALOG ON CATALOG arao TO `<workspace-id>-metadata-manager`;
-- GRANT USE SCHEMA ON SCHEMA arao.metadata_manager TO `<workspace-id>-metadata-manager`;
-- GRANT USE SCHEMA ON SCHEMA arao.metadata_test TO `<workspace-id>-metadata-manager`;
-- GRANT SELECT ON SCHEMA arao.metadata_test TO `<workspace-id>-metadata-manager`;
-- GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `<workspace-id>-metadata-manager`;
