import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.geo_asset import GeoAsset

db = SessionLocal()
try:
    count = db.query(GeoAsset).count()
    print(f"GeoAsset table has {count} records.")
except Exception as e:
    print(f"Error querying GeoAsset table: {e}")
finally:
    db.close()
