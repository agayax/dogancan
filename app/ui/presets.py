from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.models import StrategyPreset, User, get_db
from app.ui.auth import get_current_user
import pydantic

# --- Pydantic Schemas for Presets ---
class PresetBase(pydantic.BaseModel):
    name: str
    description: Optional[str] = None
    config: dict
    is_public: bool = False

class PresetCreate(PresetBase):
    pass

class PresetInDB(PresetBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

# --- API Router ---
router = APIRouter()

@router.post("/presets/", response_model=PresetInDB)
def create_preset(
    preset: PresetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new strategy preset for the current user.
    """
    db_preset = StrategyPreset(**preset.dict(), owner_id=current_user.id)
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    return db_preset

@router.get("/presets/public/", response_model=List[PresetInDB])
def read_public_presets(db: Session = Depends(get_db)):
    """
    Get a list of all presets marked as public.
    """
    return db.query(StrategyPreset).filter(StrategyPreset.is_public == True).all()

@router.get("/presets/mine/", response_model=List[PresetInDB])
def read_my_presets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all presets owned by the current user.
    """
    return db.query(StrategyPreset).filter(StrategyPreset.owner_id == current_user.id).all()

@router.post("/presets/{preset_id}/fork", response_model=PresetInDB)
def fork_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a copy of a public preset for the current user (forking).
    """
    original_preset = db.query(StrategyPreset).filter(StrategyPreset.id == preset_id).first()
    if not original_preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    if not original_preset.is_public:
        raise HTTPException(status_code=403, detail="Cannot fork a private preset")

    # Create a new preset, appending "(forked)" to the name
    new_preset_data = {
        "name": f"{original_preset.name} (forked)",
        "description": original_preset.description,
        "config": original_preset.config,
        "is_public": False, # Forked presets are private by default
        "owner_id": current_user.id
    }

    db_preset = StrategyPreset(**new_preset_data)
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    return db_preset
