from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey, DateTime, JSON, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
import uuid
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./swim.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELS (SQLAlchemy) ---
class ProgramTemplate(Base):
    __tablename__ = "program_template"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    summary = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    sets = relationship("ProgramTemplateSet", back_populates="template", cascade="all, delete")

class ProgramTemplateSet(Base):
    __tablename__ = "program_template_set"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String, ForeignKey("program_template.id", ondelete="CASCADE"))
    order_idx = Column(Integer, nullable=False)
    repeat_count_options = Column(JSON, nullable=False)
    distance_m_options = Column(JSON, nullable=False)
    default_notes = Column(JSON)

    template = relationship("ProgramTemplate", back_populates="sets")

class Workout(Base):
    __tablename__ = "workout"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    source_template_id = Column(String, ForeignKey("program_template.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    sets = relationship("WorkoutSet", back_populates="workout", cascade="all, delete")

class WorkoutSet(Base):
    __tablename__ = "workout_set"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workout_id = Column(String, ForeignKey("workout.id", ondelete="CASCADE"))
    order_idx = Column(Integer, nullable=False)
    repeat_count = Column(Integer, nullable=False)
    distance_m = Column(Integer, nullable=False)
    rest_s = Column(Integer)
    sendoff_s = Column(Integer)
    intensity_zone = Column(String)
    notes = Column(JSON)

    workout = relationship("Workout", back_populates="sets")
    drills = relationship("SetDrill", back_populates="set", cascade="all, delete")

class Drill(Base):
    __tablename__ = "drill"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)

class SetDrill(Base):
    __tablename__ = "set_drill"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    set_id = Column(String, ForeignKey("workout_set.id", ondelete="CASCADE"))
    drill_id = Column(String, ForeignKey("drill.id", ondelete="CASCADE"))
    order_idx = Column(Integer, default=0)
    params = Column(JSON)

    set = relationship("WorkoutSet", back_populates="drills")
    drill = relationship("Drill")

# --- CREATE TABLES ---
Base.metadata.create_all(bind=engine)

# --- FASTAPI APP ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # für Entwicklung offen lassen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas (für API) ---
class TemplateSetSchema(BaseModel):
    order_idx: int
    repeat_count_options: List[int]
    distance_m_options: List[int]
    default_notes: Optional[dict]

    class Config:
        orm_mode = True

class TemplateSchema(BaseModel):
    id: str
    name: str
    summary: Optional[str]
    sets: List[TemplateSetSchema]

    class Config:
        orm_mode = True

class WorkoutSetSchema(BaseModel):
    id: str
    order_idx: int
    repeat_count: int
    distance_m: int
    rest_s: Optional[int]
    sendoff_s: Optional[int]
    intensity_zone: Optional[str]
    notes: Optional[dict]
    drills: Optional[List[dict]]

    class Config:
        orm_mode = True

class WorkoutSchema(BaseModel):
    id: str
    name: str
    source_template_id: Optional[str]
    created_at: datetime
    sets: List[WorkoutSetSchema]

    class Config:
        orm_mode = True

# --- ROUTES ---
@app.get("/templates", response_model=List[TemplateSchema])
def get_templates():
    db = SessionLocal()
    try:
        return db.query(ProgramTemplate).all()
    finally:
        db.close()

@app.post("/workouts/instantiate")
def instantiate_workout(payload: dict):
    db = SessionLocal()
    try:
        tpl_id = payload.get("template_id")
        name = payload.get("name", "Neues Workout")
        sets_data = payload.get("sets", [])

        workout = Workout(name=name, source_template_id=tpl_id)
        db.add(workout)
        db.flush()

        for s in sets_data:
            ws = WorkoutSet(
                workout_id=workout.id,
                order_idx=s["order_idx"],
                repeat_count=s["repeat_count"],
                distance_m=s["distance_m"],
                rest_s=s.get("rest_s"),
                sendoff_s=s.get("sendoff_s"),
                intensity_zone=s.get("intensity_zone"),
            )
            db.add(ws)

        db.commit()
        return {"id": workout.id, "name": workout.name}
    finally:
        db.close()

@app.get("/workouts", response_model=List[WorkoutSchema])
def list_workouts():
    db = SessionLocal()
    try:
        return db.query(Workout).all()
    finally:
        db.close()

@app.get("/workouts/{workout_id}", response_model=WorkoutSchema)
def get_workout(workout_id: str):
    db = SessionLocal()
    try:
        workout = db.query(Workout).filter_by(id=workout_id).first()
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        return workout
    finally:
        db.close()

@app.get("/workouts/{workout_id}/sets", response_model=List[WorkoutSetSchema])
def get_workout_sets(workout_id: str):
    db = SessionLocal()
    try:
        workout = db.query(Workout).filter_by(id=workout_id).first()
        if not workout:
            raise HTTPException(status_code=404, detail="Workout not found")
        return workout.sets
    finally:
        db.close()
