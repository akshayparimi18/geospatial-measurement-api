from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class GeospatialFile(Base):
    __tablename__ = "files"
    
    id = Column(String, primary_key=True, index=True)
    filename = Column(String)
    feature_count = Column(Integer, default=0)
    crs = Column(String)
    status = Column(String, default="PENDING")
    
    features = relationship("FeatureMeasurement", back_populates="file", cascade="all, delete-orphan")

class FeatureMeasurement(Base):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("files.id"))
    feature_index = Column(Integer)
    geometry_type = Column(String)
    properties = Column(JSON)
    
    area_sqm = Column(Float, nullable=True)
    length_m = Column(Float, nullable=True)

    file = relationship("GeospatialFile", back_populates="features")
