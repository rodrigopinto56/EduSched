"""
Database module for schedule management system
Handles persistent storage of schedules and configurations
"""

import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import pandas as pd

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create engine with NullPool for Streamlit compatibility
engine = create_engine(DATABASE_URL, poolclass=NullPool, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class SavedSchedule(Base):
    """Model for saved generated schedules"""
    __tablename__ = 'saved_schedules'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    schedule_data = Column(JSON, nullable=False)  # JSON array of schedule rows
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    total_classes = Column(Integer)
    total_groups = Column(Integer)
    total_conflicts = Column(Integer)

class SavedConfiguration(Base):
    """Model for saved input configurations (groups, teachers, classrooms)"""
    __tablename__ = 'saved_configurations'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Store as JSON
    grupos_data = Column(JSON, nullable=False)
    maestros_data = Column(JSON, nullable=False)
    salones_data = Column(JSON, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database functions
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

# Schedule CRUD operations
def save_schedule(name, description, schedule_df, total_groups, total_conflicts):
    """Save a schedule to database"""
    db = get_db()
    try:
        # Convert DataFrame to JSON
        schedule_json = schedule_df.to_dict(orient='records')
        
        # Create new schedule
        new_schedule = SavedSchedule(
            name=name,
            description=description,
            schedule_data=schedule_json,
            total_classes=len(schedule_df),
            total_groups=total_groups,
            total_conflicts=total_conflicts
        )
        
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        return new_schedule.id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def load_schedule(schedule_id):
    """Load a schedule from database"""
    db = get_db()
    try:
        schedule = db.query(SavedSchedule).filter(SavedSchedule.id == schedule_id).first()
        if schedule:
            # Convert JSON back to DataFrame
            schedule_df = pd.DataFrame(schedule.schedule_data)
            return schedule_df, schedule.name, schedule.description
        return None, None, None
    finally:
        db.close()

def list_schedules():
    """List all saved schedules"""
    db = get_db()
    try:
        schedules = db.query(SavedSchedule).order_by(SavedSchedule.created_at.desc()).all()
        return [{
            'id': s.id,
            'name': s.name,
            'description': s.description,
            'total_classes': s.total_classes,
            'total_groups': s.total_groups,
            'total_conflicts': s.total_conflicts,
            'created_at': s.created_at,
            'updated_at': s.updated_at
        } for s in schedules]
    finally:
        db.close()

def delete_schedule(schedule_id):
    """Delete a schedule from database"""
    db = get_db()
    try:
        schedule = db.query(SavedSchedule).filter(SavedSchedule.id == schedule_id).first()
        if schedule:
            db.delete(schedule)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Configuration CRUD operations
def save_configuration(name, description, grupos_df, maestros_df, salones_df):
    """Save a configuration template to database"""
    db = get_db()
    try:
        # Convert DataFrames to JSON
        grupos_json = grupos_df.to_dict(orient='records')
        maestros_json = maestros_df.to_dict(orient='records')
        salones_json = salones_df.to_dict(orient='records')
        
        # Create new configuration
        new_config = SavedConfiguration(
            name=name,
            description=description,
            grupos_data=grupos_json,
            maestros_data=maestros_json,
            salones_data=salones_json
        )
        
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return new_config.id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def load_configuration(config_id):
    """Load a configuration template from database"""
    db = get_db()
    try:
        config = db.query(SavedConfiguration).filter(SavedConfiguration.id == config_id).first()
        if config:
            # Convert JSON back to DataFrames
            grupos_df = pd.DataFrame(config.grupos_data)
            maestros_df = pd.DataFrame(config.maestros_data)
            salones_df = pd.DataFrame(config.salones_data)
            return grupos_df, maestros_df, salones_df, config.name, config.description
        return None, None, None, None, None
    finally:
        db.close()

def list_configurations():
    """List all saved configurations"""
    db = get_db()
    try:
        configs = db.query(SavedConfiguration).order_by(SavedConfiguration.created_at.desc()).all()
        return [{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'num_grupos': len(c.grupos_data),
            'num_maestros': len(c.maestros_data),
            'num_salones': len(c.salones_data),
            'created_at': c.created_at,
            'updated_at': c.updated_at
        } for c in configs]
    finally:
        db.close()

def delete_configuration(config_id):
    """Delete a configuration from database"""
    db = get_db()
    try:
        config = db.query(SavedConfiguration).filter(SavedConfiguration.id == config_id).first()
        if config:
            db.delete(config)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
