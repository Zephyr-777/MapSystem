import sys
import os
import json
import random
from datetime import datetime, timedelta
from shapely.geometry import Point, mapping

sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine
from app.models.geologic_feature import GeologicFeature, Base

# Eras and associated lithologies
ERAS = {
    "Archean": ["Gneiss", "Granulite", "Schist"],
    "Proterozoic": ["Quartzite", "Marble", "Slate"],
    "Paleozoic": ["Limestone", "Sandstone", "Shale", "Coal"],
    "Mesozoic": ["Conglomerate", "Volcanic Breccia", "Tuff"],
    "Cenozoic": ["Mudstone", "Siltstone", "Loess"]
}

STRUCTURES = ["Fault", "Fold", "Joint", "Unconformity"]
MINERALS = ["Gold", "Copper", "Iron", "Coal", "Quartz", "Feldspar", "None"]

# Beijing area bounds
LAT_MIN, LAT_MAX = 39.4, 41.0
LON_MIN, LON_MAX = 115.4, 117.5

def generate_data():
    db = SessionLocal()
    try:
        print("Clearing existing data...")
        db.query(GeologicFeature).delete()
        db.commit()
        
        print("Generating 500 new geological features...")
        features = []
        for i in range(500):
            era = random.choice(list(ERAS.keys()))
            lithology = random.choice(ERAS[era])
            structure = random.choice(STRUCTURES)
            mineral = random.choice(MINERALS)
            
            # Random location
            lat = random.uniform(LAT_MIN, LAT_MAX)
            lon = random.uniform(LON_MIN, LON_MAX)
            
            # Create GeoJSON geometry
            geom = {
                "type": "Point",
                "coordinates": [lon, lat]
            }
            
            props = {
                "era": era,
                "lithology_class": "Sedimentary" if lithology in ["Limestone", "Sandstone"] else "Metamorphic", # Simplified
                "rock_type": lithology,
                "structure_type": structure,
                "mineral": mineral,
                "elevation": round(random.uniform(50, 2000), 2),
                "sample_date": (datetime.now() - timedelta(days=random.randint(0, 3650))).strftime("%Y-%m-%d"),
                "description": f"{era} {lithology} with {structure} structure. Contains {mineral}.",
                "coordinates": [lon, lat]
            }
            
            feature = GeologicFeature(
                name=f"Sample-{i+1:04d}",
                type="Virtual",
                geometry=json.dumps(geom),
                properties=props # SQLAlchemy JSON type will handle dict automatically if using PG, or we dump if SQLite
            )
            # If using SQLite (which might be the case for local dev if PG is not active or configured differently in alembic), 
            # properties might need to be a dict if the model says JSON. 
            # But wait, in `check_db.py` output: `Sample Props: {'era': ...}`. It is a dict.
            # So we pass a dict.
            
            features.append(feature)
        
        db.add_all(features)
        db.commit()
        print("Successfully generated 500 features.")
        
    except Exception as e:
        print(f"Error generating data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_data()
