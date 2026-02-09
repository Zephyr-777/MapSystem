from sqlalchemy import create_engine, inspect
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
engine = create_engine(DATABASE_URL)

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('geo_assets')]
print(f"Columns in geo_assets: {columns}")

if 'description' in columns:
    print("SUCCESS: 'description' column exists.")
else:
    print("FAILURE: 'description' column MISSING.")
