from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, Response, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional, Dict, Any
import json
import io
import tempfile
import os
import shutil
import zipfile
import pandas as pd
import shapefile
from datetime import datetime
from pathlib import Path
import mimetypes

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.geologic_feature import GeologicFeature
from app.core.config import settings
from pydantic import BaseModel

router = APIRouter()

class FeatureProperties(BaseModel):
    id: int
    name: str
    era: Optional[str]
    lithology_class: Optional[str]
    rock_type: Optional[str]
    structure_type: Optional[str]
    mineral: Optional[str]
    elevation: Optional[float]
    sample_date: Optional[str]
    description: Optional[str]
    image_path: Optional[str] = None
    highlights: Optional[Dict[str, str]] = None

class FeatureGeoJSON(BaseModel):
    type: str = "Feature"
    geometry: Dict
    properties: FeatureProperties

class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[FeatureGeoJSON]
    total: int
    page: int
    page_size: int

def resolve_feature_image_path(feature: GeologicFeature) -> Optional[Path]:
    props = feature.properties if isinstance(feature.properties, dict) else {}
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except Exception:
            props = {}

    image_path = props.get("image_path")
    if not image_path:
        return None

    return settings.STORAGE_DIR / image_path


def highlight_text(text: str, query: str) -> str:
    if not text or not query:
        return text
    # Simple case-insensitive highlight
    lower_text = text.lower()
    lower_query = query.lower()
    if lower_query in lower_text:
        start_idx = lower_text.find(lower_query)
        end_idx = start_idx + len(lower_query)
        return f"{text[:start_idx]}<mark>{text[start_idx:end_idx]}</mark>{text[end_idx:]}"
    return text

@router.get("/list", response_model=FeatureCollection)
async def get_features(
    era: Optional[str] = Query(None, description="Filter by Era"),
    lithology: Optional[str] = Query(None, description="Filter by Lithology Class"),
    structure: Optional[str] = Query(None, description="Filter by Structure Type"),
    mineral: Optional[str] = Query(None, description="Filter by Mineral"),
    sample_id: Optional[str] = Query(None, description="Filter by Sample ID"),
    elevation_min: Optional[float] = Query(None),
    elevation_max: Optional[float] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Smart search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get geological features as GeoJSON FeatureCollection.
    Supports smart multi-field fuzzy search, filtering, highlighting, and pagination.
    """
    try:
        # Fetch all properties for Python-side processing (efficient for small dataset < 10000)
        # For larger datasets, we would implement dynamic SQL construction
        query_obj = db.query(GeologicFeature)
        
        # Initial DB-side filtering if possible (e.g. name)
        # But since most fields are in JSON, we'll fetch all and filter in Python
        # except for the limit/offset which we apply AFTER filtering
        
        all_rows = query_obj.all()
        
        filtered_features = []
        
        for f in all_rows:
            props = f.properties if isinstance(f.properties, dict) else {}
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except:
                    props = {}
            
            # --- Field Filters ---
            if era and props.get('era') != era: continue
            if lithology and props.get('lithology_class') != lithology: continue
            if structure and props.get('structure_type') != structure: continue
            if mineral and props.get('mineral') != mineral: continue
            
            # Sample ID (assuming it's the 'name' or a prop)
            f_name = f.name or ""
            if sample_id and sample_id.lower() not in f_name.lower(): continue

            # Elevation
            elev = props.get('elevation')
            if elev is not None:
                if elevation_min is not None and elev < elevation_min: continue
                if elevation_max is not None and elev > elevation_max: continue
            
            # Date
            s_date = props.get('sample_date')
            if s_date:
                if date_start and s_date < date_start: continue
                if date_end and s_date > date_end: continue

            # --- Smart Search & Scoring ---
            score = 0
            highlights = {}
            
            if q:
                q_lower = q.lower()
                matched = False
                
                # Fields to search
                searchable_fields = {
                    'name': f.name,
                    'era': props.get('era', ''),
                    'lithology_class': props.get('lithology_class', ''),
                    'rock_type': props.get('rock_type', ''),
                    'structure_type': props.get('structure_type', ''),
                    'mineral': props.get('mineral', ''),
                    'description': props.get('description', ''),
                    'sample_date': props.get('sample_date', ''),
                    'elevation': str(props.get('elevation', ''))
                }
                
                for field, value in searchable_fields.items():
                    if value and q_lower in str(value).lower():
                        matched = True
                        score += 1
                        # Exact match bonus
                        if q_lower == str(value).lower():
                            score += 5
                        # Highlight
                        if field in ['name', 'description', 'rock_type', 'mineral']:
                            highlights[field] = highlight_text(str(value), q)
                
                if not matched:
                    continue
            else:
                score = 1 # Default score to keep if no query

            # Parse geometry
            geom = None
            if f.geometry:
                if isinstance(f.geometry, str):
                    try:
                        geom = json.loads(f.geometry)
                    except:
                        pass
                elif isinstance(f.geometry, dict):
                    geom = f.geometry
            
            if not geom:
                continue

            filtered_features.append({
                "obj": FeatureGeoJSON(
                    geometry=geom,
                    properties=FeatureProperties(
                        id=f.id,
                        name=f.name,
                        era=props.get('era'),
                        lithology_class=props.get('lithology_class'),
                        rock_type=props.get('rock_type'),
                        structure_type=props.get('structure_type'),
                        mineral=props.get('mineral'),
                        elevation=props.get('elevation'),
                        sample_date=props.get('sample_date'),
                        description=props.get('description'),
                        image_path=props.get('image_path'),
                        highlights=highlights if highlights else None
                    )
                ),
                "score": score
            })

        # Sort by score (descending) then name
        filtered_features.sort(key=lambda x: (-x['score'], x['obj'].properties.name))
        
        # Pagination
        total = len(filtered_features)
        start = (page - 1) * page_size
        end = start + page_size
        paginated = [item['obj'] for item in filtered_features[start:end]]
        
        return FeatureCollection(
            features=paginated,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        print(f"Error fetching features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{feature_id}")
async def get_feature_image(
    feature_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    feature = db.query(GeologicFeature).filter(GeologicFeature.id == feature_id).first()
    if not feature:
        raise HTTPException(status_code=404, detail="GeologicFeature not found")

    image_file = resolve_feature_image_path(feature)
    if not image_file or not image_file.exists() or not image_file.is_file():
        raise HTTPException(status_code=404, detail="Feature image not found")

    media_type, _ = mimetypes.guess_type(str(image_file))
    return FileResponse(image_file, media_type=media_type or "image/jpeg")

@router.get("/export")
async def export_features(
    format: str = Query(..., pattern="^(excel|csv|shapefile|markdown|pdf)$"),
    era: Optional[str] = Query(None),
    lithology: Optional[str] = Query(None),
    structure: Optional[str] = Query(None),
    mineral: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    ids: Optional[str] = Query(None, description="Comma separated IDs for bulk export"),
    srid: Optional[int] = Query(4326, description="Target SRID for coordinates"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Export geological features to Excel, CSV, Shapefile, Markdown or PDF.
    Supports bulk export by IDs and Coordinate Transformation.
    """
    try:
        query_obj = db.query(GeologicFeature)
        
        # Filter by IDs if provided
        if ids:
            id_list = [int(i) for i in ids.split(',') if i.isdigit()]
            if len(id_list) > 5000:
                raise HTTPException(status_code=400, detail="Export limit exceeded (max 5000 items). Please filter your selection.")
            if id_list:
                query_obj = query_obj.filter(GeologicFeature.id.in_(id_list))
        
        all_rows = query_obj.all()
        data_rows = []
        
        # ... filtering logic ...
        apply_filters = not ids
        
        # Prepare projection transformer if needed
        transformer = None
        if srid and srid != 4326:
            try:
                from pyproj import Transformer
                # Always from 4326 (WGS84) to target
                transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{srid}", always_xy=True)
            except Exception as e:
                print(f"Projection init failed: {e}")
                # Fallback to 4326 or raise warning? We'll continue with 4326 but log error
                pass
        
        for f in all_rows:
            props = f.properties if isinstance(f.properties, dict) else {}
            if isinstance(props, str):
                try: props = json.loads(props)
                except: props = {}
            
            if apply_filters:
                if era and props.get('era') != era: continue
                if lithology and props.get('lithology_class') != lithology: continue
                if structure and props.get('structure_type') != structure: continue
                if mineral and props.get('mineral') != mineral: continue
                
                if q:
                    q_lower = q.lower()
                    found = False
                    for v in props.values():
                        if v and q_lower in str(v).lower(): found = True; break
                    if not found and q_lower not in f.name.lower(): continue

            # Extract coordinates
            lon, lat = None, None
            geom = f.geometry
            if isinstance(geom, str):
                try: geom = json.loads(geom)
                except: pass
            
            if isinstance(geom, dict) and geom.get('type') == 'Point':
                coords = geom.get('coordinates')
                if coords and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
            
            # Coordinate Transformation
            if transformer and lon is not None and lat is not None:
                try:
                    lon, lat = transformer.transform(lon, lat)
                except:
                    pass

            row = {
                'id': f.id,
                'name': f.name,
                'era': props.get('era'),
                'lithology': props.get('lithology_class'),
                'rock_type': props.get('rock_type'),
                'structure': props.get('structure_type'),
                'mineral': props.get('mineral'),
                'elevation': props.get('elevation'),
                'date': props.get('sample_date'),
                'description': props.get('description'),
                'longitude': lon,
                'latitude': lat
            }
            data_rows.append(row)
            
        if not data_rows:
             raise HTTPException(status_code=404, detail="No data found for export")
             
        if len(data_rows) > 5000:
             raise HTTPException(status_code=400, detail="Export limit exceeded (max 5000 items). Please refine your filter.")

        df = pd.DataFrame(data_rows)
        
        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Geology Data')
            output.seek(0)
            return StreamingResponse(
                output, 
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": "attachment; filename=geology_data.xlsx"}
            )
            
        elif format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            return Response(
                content=output.getvalue(),
                media_type='text/csv',
                headers={"Content-Disposition": "attachment; filename=geology_data.csv"}
            )
            
        elif format == 'markdown':
            output = io.StringIO()
            # Add header
            output.write(f"# Geology Data Export\n")
            output.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            output.write(f"Total Items: {len(data_rows)}\n\n")
            # Convert DF to Markdown
            output.write(df.to_markdown(index=False))
            return Response(
                content=output.getvalue(),
                media_type='text/markdown',
                headers={"Content-Disposition": "attachment; filename=geology_data.md"}
            )

        elif format == 'pdf':
            # Generate HTML first then convert to PDF
            html_content = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    h1 {{ color: #333; }}
                    table {{ border-collapse: collapse; width: 100%; font-size: 10px; }}
                    th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                </style>
            </head>
            <body>
                <h1>Geology Data Export</h1>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Total Items: {len(data_rows)}</p>
                {df.to_html(index=False)}
            </body>
            </html>
            """
            
            try:
                import pdfkit
                # Configure pdfkit (assuming wkhtmltopdf is installed or handled)
                # If wkhtmltopdf is missing, this will fail. 
                # For this environment, user might not have wkhtmltopdf installed.
                # We'll use a try-except and maybe a simpler library if available, 
                # or just instruct user. 
                # But since I installed 'pdfkit', it requires the binary.
                # Alternative: ReportLab (pure python). But pdfkit is easier for HTML->PDF.
                # Let's assume binary might be missing and handle gracefully.
                
                # Check for wkhtmltopdf
                # config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf') # Example
                pdf = pdfkit.from_string(html_content, False)
                
                return StreamingResponse(
                    io.BytesIO(pdf),
                    media_type='application/pdf',
                    headers={"Content-Disposition": "attachment; filename=geology_data.pdf"}
                )
            except Exception as e:
                print(f"PDF Generation failed: {e}")
                # Fallback to HTML if PDF fails
                return Response(
                    content=html_content,
                    media_type='text/html',
                    headers={"Content-Disposition": "attachment; filename=geology_data.html"}
                )

        elif format == 'shapefile':
            # ... existing shapefile logic ...

            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                shp_path = os.path.join(temp_dir, "geology_data")
                w = shapefile.Writer(shp_path)
                
                # Define fields
                w.field('id', 'N')
                w.field('name', 'C', size=100)
                w.field('era', 'C', size=50)
                w.field('lithology', 'C', size=50)
                w.field('rock_type', 'C', size=50)
                w.field('structure', 'C', size=50)
                w.field('mineral', 'C', size=50)
                w.field('elevation', 'N', decimal=2)
                w.field('date', 'C', size=20)
                
                for row in data_rows:
                    if row['longitude'] is not None and row['latitude'] is not None:
                        w.point(row['longitude'], row['latitude'])
                        w.record(
                            row['id'], 
                            row['name'] or "",
                            row['era'] or "",
                            row['lithology'] or "",
                            row['rock_type'] or "",
                            row['structure'] or "",
                            row['mineral'] or "",
                            row['elevation'] or 0,
                            row['date'] or ""
                        )
                
                w.close()
                
                # Zip the files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename in os.listdir(temp_dir):
                        if filename.startswith("geology_data"):
                            zip_file.write(os.path.join(temp_dir, filename), filename)
                
                zip_buffer.seek(0)
                return StreamingResponse(
                    zip_buffer,
                    media_type='application/zip',
                    headers={"Content-Disposition": "attachment; filename=geology_data_shp.zip"}
                )

    except Exception as e:
        print(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_feature_stats(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get statistics for classification trees.
    """
    try:
        features = db.query(GeologicFeature.properties).all()
        
        stats = {
            "eras": {},
            "lithologies": {},
            "structures": {},
            "minerals": {}
        }
        
        for f in features:
            props = f[0]
            if isinstance(props, str):
                try: props = json.loads(props)
                except: continue
            
            if not isinstance(props, dict): continue
                
            era = props.get('era', 'Unknown')
            stats['eras'][era] = stats['eras'].get(era, 0) + 1
            
            lith = props.get('lithology_class', 'Unknown')
            stats['lithologies'][lith] = stats['lithologies'].get(lith, 0) + 1
            
            struc = props.get('structure_type', 'Unknown')
            stats['structures'][struc] = stats['structures'].get(struc, 0) + 1
            
            min_type = props.get('mineral', 'None')
            if min_type != 'None':
                stats['minerals'][min_type] = stats['minerals'].get(min_type, 0) + 1

        return stats

    except Exception as e:
        print(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
