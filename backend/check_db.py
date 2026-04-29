import sys
import os
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.geologic_feature import GeologicFeature
from sqlalchemy import text

def check_db():
    db = SessionLocal()
    try:
        # Check connection
        db.execute(text("SELECT 1"))
        print("Database connection: OK")
        
        # Check table count
        count = db.query(GeologicFeature).count()
        print(f"GeologicFeature count: {count}")
        
        if count > 0:
            # Check sample data
            sample = db.query(GeologicFeature).first()
            print(f"Sample ID: {sample.id}")
            print(f"Sample Name: {sample.name}")
            print(f"Sample Props: {sample.properties}")
            print(f"Sample Geom: {sample.geometry}")
        else:
            print("Table is empty!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
