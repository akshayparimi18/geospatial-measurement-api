import os
import uuid
import shutil
import fiona
import geopandas as gpd
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import engine, get_db, init_db
from models import GeospatialFile, FeatureMeasurement

# Enable KML driver in fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'

app = FastAPI(title="Geospatial File Measurement API")

@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs("uploads", exist_ok=True)

@app.post("/api/files/")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.zip', '.kml')):
        raise HTTPException(status_code=400, detail="Only .zip (Shapefile) or .kml files are supported.")
    
    file_id = str(uuid.uuid4())
    file_path = f"uploads/{file_id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Initialize DB record
    db_file = GeospatialFile(id=file_id, filename=file.filename, status="PROCESSING")
    db.add(db_file)
    db.commit()
    
    try:
        # Read geospatial file using GeoPandas
        if file.filename.endswith('.zip'):
            gdf = gpd.read_file(f"zip://{file_path}")
        else:
            gdf = gpd.read_file(file_path, driver='KML')
        
        db_file.crs = str(gdf.crs)
        
        # Reproject to a localized metric UTM CRS if geographic (e.g., EPSG:4326)
        if gdf.crs and gdf.crs.is_geographic:
            gdf = gdf.to_crs(gdf.estimate_utm_crs())
            
        db_file.feature_count = len(gdf)
        
        # Process features and calculate measurements
        features = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None:
                continue
                
            geom_type = geom.geom_type
            area = geom.area if geom_type in ['Polygon', 'MultiPolygon'] else None
            length = geom.length if geom_type in ['LineString', 'MultiLineString'] else None
            
            # Safely extract properties (excluding the geometry column)
            props = {str(k): str(v) for k, v in row.items() if k != 'geometry'}
            
            feature = FeatureMeasurement(
                file_id=file_id,
                feature_index=idx,
                geometry_type=geom_type,
                properties=props,
                area_sqm=area,
                length_m=length
            )
            features.append(feature)
            
        db.add_all(features)
        db_file.status = "COMPLETED"
        db.commit()
        
        return {"id": file_id, "message": "File processed successfully"}
        
    except Exception as e:
        db_file.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/files/{id}/")
async def get_file_info(id: str, db: Session = Depends(get_db)):
    db_file = db.query(GeospatialFile).filter(GeospatialFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    return {
        "id": db_file.id,
        "filename": db_file.filename,
        "feature_count": db_file.feature_count,
        "crs": db_file.crs,
        "status": db_file.status
    }

@app.get("/api/files/{id}/measurements/")
async def get_file_measurements(id: str, db: Session = Depends(get_db)):
    db_file = db.query(GeospatialFile).filter(GeospatialFile.id == id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    features = db.query(FeatureMeasurement).filter(FeatureMeasurement.file_id == id).all()
    
    return [
        {
            "feature_index": f.feature_index,
            "geometry_type": f.geometry_type,
            "area_sqm": f.area_sqm,
            "length_m": f.length_m,
            "properties": f.properties
        } for f in features
    ]
