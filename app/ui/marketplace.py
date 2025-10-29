from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import subprocess
import sys
import os

from app.db.models import StrategyPreset, User, get_db
from app.ui.auth import get_current_user
from app.ui.presets import PresetInDB # Reuse the schema

# --- Admin User Check ---
# In a real app, this would be a proper role-based access control system.
# For this prototype, we'll just check if the username is 'admin'.
def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.username != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return current_user

# --- API Router ---
router = APIRouter()

@router.get("/marketplace/", response_model=List[PresetInDB])
def get_marketplace_presets(db: Session = Depends(get_db)):
    """
    List all strategy presets that are approved for the marketplace.
    """
    return db.query(StrategyPreset).filter(StrategyPreset.is_in_marketplace == True).all()

@router.post("/marketplace/promote/{preset_id}", response_model=PresetInDB)
def promote_preset_to_marketplace(
    preset_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Promote a given preset to the marketplace. (Admin only)
    """
    preset = db.query(StrategyPreset).filter(StrategyPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    preset.is_in_marketplace = True
    db.commit()
    db.refresh(preset)
    return preset

@router.post("/marketplace/lease/{preset_id}")
def lease_and_run_strategy(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    "Lease" a marketplace strategy and run it on the user's own account.
    This launches a live trader process in the background.
    """
    preset = db.query(StrategyPreset).filter(
        StrategyPreset.id == preset_id,
        StrategyPreset.is_in_marketplace == True
    ).first()

    if not preset:
        raise HTTPException(status_code=404, detail="Marketplace preset not found")

    if not current_user.api_key or not current_user.api_secret:
        raise HTTPException(status_code=400, detail="User has no API keys configured.")

    # --- Launch the live trader as a background process ---
    # WARNING: This is a simplified prototype. A robust production system would use a
    # proper job queue and process manager (e.g., Celery, RQ, Kubernetes Jobs).

    # We pass the user's decrypted keys and the preset's config to the script
    # via environment variables for security.
    process_env = os.environ.copy()
    process_env["LIVE_API_KEY"] = current_user.api_key
    process_env["LIVE_API_SECRET"] = current_user.api_secret
    process_env["LIVE_STRATEGY_CONFIG"] = json.dumps(preset.config)

    # Example: run_live_trader.py would need to be adapted to read these env vars
    command = [
        sys.executable,
        "run_live_trader.py", # This script needs to be adapted
        f"--user-id={current_user.id}",
        f"--preset-id={preset.id}"
    ]

    try:
        subprocess.Popen(command, env=process_env)
        print(f"Launched live trader for user {current_user.username} with preset {preset.name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch trader: {e}")

    return {"status": "success", "message": f"Live trader for preset '{preset.name}' has been launched."}
