import logging
from sqlalchemy import text
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_schema():
    logger.info("Starting schema fix...")
    try:
        with engine.connect() as conn:
            # Check if column exists
            logger.info("Adding 'description' column to 'geo_assets' table...")
            conn.execute(text("ALTER TABLE geo_assets ADD COLUMN IF NOT EXISTS description VARCHAR(500);"))
            conn.commit()
            logger.info("Successfully added 'description' column.")
    except Exception as e:
        logger.error(f"Error fixing schema: {e}")
        raise

if __name__ == "__main__":
    fix_schema()
