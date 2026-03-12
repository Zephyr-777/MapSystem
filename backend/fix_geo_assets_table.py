from sqlalchemy import text
from app.core.database import SessionLocal

def add_columns():
    db = SessionLocal()
    try:
        # Check if is_sidecar exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='geo_assets' AND column_name='is_sidecar';"))
        if not result.fetchone():
            print("Adding column 'is_sidecar'...")
            db.execute(text("ALTER TABLE geo_assets ADD COLUMN is_sidecar BOOLEAN DEFAULT FALSE;"))
        else:
            print("Column 'is_sidecar' already exists.")

        # Check if sub_type exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='geo_assets' AND column_name='sub_type';"))
        if not result.fetchone():
            print("Adding column 'sub_type'...")
            db.execute(text("ALTER TABLE geo_assets ADD COLUMN sub_type VARCHAR(50);"))
        else:
            print("Column 'sub_type' already exists.")
            
        # Check if parent_id exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='geo_assets' AND column_name='parent_id';"))
        if not result.fetchone():
            print("Adding column 'parent_id'...")
            db.execute(text("ALTER TABLE geo_assets ADD COLUMN parent_id INTEGER REFERENCES geo_assets(id);"))
        else:
            print("Column 'parent_id' already exists.")

        db.commit()
        print("Schema update completed successfully.")
            
    except Exception as e:
        print(f"Error adding columns: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_columns()
