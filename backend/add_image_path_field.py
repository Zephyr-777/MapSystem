#!/usr/bin/env python3
"""
Migration script to add image_path field to GeoAsset model
"""

import os
import sys
import logging
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import get_db, engine

def migrate_image_field():
    """Add image_path column to geo_assets table"""
    logger = logging.getLogger(__name__)

    # Check if column already exists
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('geo_assets')]

    if 'image_path' in columns:
        logger.info("image_path column already exists")
        return True

    try:
        with engine.connect() as conn:
            # Add the column
            conn.execute(text("""
                ALTER TABLE geo_assets
                ADD COLUMN image_path VARCHAR(500) NULL
                COMMENT '优化预览图片路径'
            """))
            conn.commit()
            logger.info("Successfully added image_path column")

            # Add index for better performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_geo_assets_image_path
                ON geo_assets(image_path)
            """))
            conn.commit()
            logger.info("Successfully created image_path index")

            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if migrate_image_field():
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)