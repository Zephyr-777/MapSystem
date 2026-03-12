-- Index configuration for GeologicFeature properties
-- Recommended for production with > 10,000 records

-- 1. GIN Index for JSONB properties (if using PostgreSQL)
CREATE INDEX IF NOT EXISTS idx_geologic_feature_properties ON geologic_features USING GIN (properties);

-- 2. B-Tree indexes for specific frequently queried fields (extracted from JSON)
-- Note: Requires immutable function or expression index
CREATE INDEX IF NOT EXISTS idx_gf_era ON geologic_features ((properties->>'era'));
CREATE INDEX IF NOT EXISTS idx_gf_lithology ON geologic_features ((properties->>'lithology_class'));
CREATE INDEX IF NOT EXISTS idx_gf_structure ON geologic_features ((properties->>'structure_type'));
CREATE INDEX IF NOT EXISTS idx_gf_mineral ON geologic_features ((properties->>'mineral'));

-- 3. Spatial Index (already exists usually, but ensuring)
CREATE INDEX IF NOT EXISTS idx_geologic_feature_geom ON geologic_features USING GIST (geometry);
