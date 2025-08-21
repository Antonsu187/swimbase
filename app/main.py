from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    create_engine, Column, String, Integer, Text, ForeignKey,
    DateTime, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# --------- DB Setup (SQLite Datei) ----------
engine = create_engine("sqlite:///swimplans.db", future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def gen_id() -> str:
    return str(uuid4())

# --------- Modelle ----------
class ProgramTemplate(Base):
    __tablename__ = "program_template"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sets = relationship(
        "ProgramTemplateSet",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ProgramTemplateSet.order_idx",
    )

class ProgramTemplateSet(Base):
    __tablename__ = "program_template_set"
    id = Column(String, primary_key=True, default=gen_id)
    template_id = Column(String, ForeignKey("program_template.id", ondelete="CASCADE"), nullable=False)
    order_idx = Column(Integer, nullable=False)
    # Dropdown-Optionen als JSON-Arrays (z. B. [3,4,6], [25,50])
    repeat_count_options = Column(JSON, nullable=False)
    distance_m_options   = Column(JSON, nullable=False)
    default_notes = Column(JSON)  # z.B. {"de":"Brust: Gleit + 1 Zug"}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    template = relationship("ProgramTemplate", back_populates="sets")

class Workout(Base):
    __tablename__ = "workout"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    source_template_id = Column(String, ForeignKey("program_template.id", ondelete="SET NULL"))
    notes = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sets = relationship(
        "WorkoutSet",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.order_idx",
    )

class WorkoutSet(Base):
    __tablename__ = "workout_set"
    id = Column(String, primary_key=True, default=gen_id)
    workout_id = Column(String, ForeignKey("workout.id", ondelete="CASCADE"), nullable=False)
    order_idx = Column(Integer, nullable=False)
    repeat_count = Column(Integer, nullable=False)
    distance_m = Column(Integer, nullable=False)
    rest_s = Column(Integer)        # frei eintragen
    sendoff_s = Column(Integer)     # frei eintragen
    intensity_zone = Column(String) # frei eintragen
    notes = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workout = relationship("Workout", back_populates="sets")
    drills = relationship(
        "SetDrill",
        back_populates="set",
        cascade="all, delete-orphan",
        order_by="SetDrill.order_idx",
    )

class Drill(Base):
    __tablename__ = "drill"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class SetDrill(Base):
    __tablename__ = "set_drill"
    id = Column(String, primary_key=True, default=gen_id)
    set_id = Column(String, ForeignKey("workout_set.id", ondelete="CASCADE"), nullable=False)
    drill_id = Column(String, ForeignKey("drill.id", ondelete="RESTRICT"), nullable=False)
    order_idx = Column(Integer, nullable=False, default=1)
    params = Column(JSON)  # optional, z. B. {"cue":"Gleit zählen"}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    set = relationship("WorkoutSet", back_populates="drills")
    drill = relationship("Drill")

# --------- DB erstellen & seeden ----------
Base.metadata.create_all(engine)

def seed_if_empty():
    db = SessionLocal()
    try:
        if db.query(ProgramTemplate).count() > 0:
            db.close()
            return

        tpl1 = ProgramTemplate(
            id="00000000-0000-0000-0000-000000000001",
            name="Technik Brust – Kurz",
            summary="Fokus Timing, Gleit, enger Kick",
        )
        tpl1.sets = [
            ProgramTemplateSet(
                template_id=tpl1.id, order_idx=1,
                repeat_count_options=[3,4,6],
                distance_m_options=[25,50],
                default_notes={"de":"Brust: Gleit + 1 Zug"},
            ),
            ProgramTemplateSet(
                template_id=tpl1.id, order_idx=2,
                repeat_count_options=[3,4,6],
                distance_m_options=[25,50],
                default_notes={"de":"Brust-Beine mit Brett"},
            ),
        ]

        tpl2 = ProgramTemplate(
            id="00000000-0000-0000-0000-000000000002",
            name="Freistil Sprint – Start/UW",
            summary="Kurz, explosiv, Unterwasser + Sculling",
        )
        tpl2.sets = [
            ProgramTemplateSet(
                template_id=tpl2.id, order_idx=1,
                repeat_count_options=[3,4,6],
                distance_m_options=[25,50],
                default_notes={"de":"Start + Unterwasser Delfin (6/8 Kicks)"},
            ),
            ProgramTemplateSet(
                template_id=tpl2.id, order_idx=2,
                repeat_count_options=[3,4,6],
                distance_m_options=[25,50],
                default_notes={"de":"Sculling vorn"},
            ),
        ]

        drills = [
            Drill(id="00000000-0000-0000-0000-0000000000A1", name="Brust: Gleit + 1 Zug",
                  description="Timing & Gleitphase fühlen; enger, schneller Kick"),
            Drill(id="00000000-0000-0000-0000-0000000000A2", name="Brust-Beine mit Brett",
                  description="Stabiler Rumpf; enger Kick aus dem Knie, Fersen schnappen"),
            Drill(id="00000000-0000-0000-0000-0000000000B1", name="Unterwasser Delfin 6/8",
                  description="Wellenbewegung aus der Hüfte; Streamline; 6–8 Kicks"),
            Drill(id="00000000-0000-0000-0000-0000000000B2", name="Sculling vorn",
                  description="Druckrichtung spüren; EVF; kleine saubere Handbewegungen"),
        ]

        db.add_all([tpl1, tpl2] + drills)
        db.commit()
    finally:
        db.close()

seed_if_empty()

# --------- API ---------
app = FastAPI(title="Swim Plans (Python)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Pydantic Schemas
class InstantiateSet(BaseModel):
    order_idx: int
    repeat_count: int
    distance_m: int
    rest_s: Optional[int] = None
    sendoff_s: Optional[int] = None
    intensity_zone: Optional[str] = None

class InstantiateBody(BaseModel):
    template_id: Optional[str] = None
    name: str
    sets: List[InstantiateSet]

@app.get("/templates")
def get_templates():
    db = SessionLocal()
    try:
        tpls = db.query(ProgramTemplate).order_by(ProgramTemplate.name).all()
        out = []
        for t in tpls:
            out.append({
                "id": t.id,
                "name": t.name,
                "summary": t.summary,
                "sets": [
                    {
                        "id": s.id,
                        "order_idx": s.order_idx,
                        "repeat_count_options": s.repeat_count_options,
                        "distance_m_options": s.distance_m_options,
                        "default_notes": s.default_notes,
                    }
                    for s in t.sets
                ],
            })
        return out
    finally:
        db.close()

@app.post("/workouts/instantiate")
def instantiate_workout(body: InstantiateBody):
    db = SessionLocal()
    try:
        w = Workout(name=body.name, source_template_id=body.template_id)
        db.add(w)
        db.flush()  # w.id verfügbar

        for s in body.sets:
            ws = WorkoutSet(
                workout_id=w.id,
                order_idx=s.order_idx,
                repeat_count=s.repeat_count,
                distance_m=s.distance_m,
                rest_s=s.rest_s,
                sendoff_s=s.sendoff_s,
                intensity_zone=s.intensity_zone,
            )
            db.add(ws)

        db.commit()
        return {"id": w.id, "name": w.name}
    finally:
        db.close()

@app.get("/workouts/{workout_id}/sets")
def get_workout_sets(workout_id: str):
    db = SessionLocal()
    try:
        sets = db.query(WorkoutSet).filter(WorkoutSet.workout_id == workout_id).order_by(WorkoutSet.order_idx).all()
        if not sets:
            # Prüfe ob Workout existiert
            if not db.query(Workout).filter(Workout.id == workout_id).first():
                raise HTTPException(status_code=404, detail="Workout nicht gefunden")
        out = []
        for s in sets:
            drills = [
                {
                    "drill_id": sd.drill_id,
                    "name": sd.drill.name if sd.drill else None,
                    "order_idx": sd.order_idx,
                    "params": sd.params,
                } for sd in s.drills
            ]
            out.append({
                "id": s.id,
                "order_idx": s.order_idx,
                "repeat_count": s.repeat_count,
                "distance_m": s.distance_m,
                "rest_s": s.rest_s,
                "sendoff_s": s.sendoff_s,
                "intensity_zone": s.intensity_zone,
                "drills": drills,
            })
        return out
    finally:
        db.close()

class AddDrillBody(BaseModel):
    drill_id: str
    order_idx: Optional[int] = 1
    params: Optional[Dict[str, Any]] = None

@app.post("/sets/{set_id}/drills")
def add_drill_to_set(set_id: str, body: AddDrillBody):
    db = SessionLocal()
    try:
        target_set = db.query(WorkoutSet).filter(WorkoutSet.id == set_id).first()
        if not target_set:
            raise HTTPException(status_code=404, detail="Set nicht gefunden")
        if not db.query(Drill).filter(Drill.id == body.drill_id).first():
            raise HTTPException(status_code=404, detail="Drill nicht gefunden")

        sd = SetDrill(
            set_id=set_id,
            drill_id=body.drill_id,
            order_idx=body.order_idx or 1,
            params=body.params,
        )
        db.add(sd)
        db.commit()
        return {"ok": True, "id": sd.id}
    finally:
        db.close()
