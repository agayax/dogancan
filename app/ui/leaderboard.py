from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.db.models import PaperTradingSession, get_db
import pydantic

# --- Pydantic Schemas for Leaderboard ---

class LeaderboardEntry(pydantic.BaseModel):
    rank: int
    username: str
    preset_name: str
    sharpe_ratio: float
    max_drawdown: float
    pnl_percentage: float
    resilience_score: float

    class Config:
        orm_mode = True

# --- API Router ---
router = APIRouter()

@router.get("/leaderboard/", response_model=List[LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    """
    Retrieves and ranks public paper trading sessions to create a leaderboard.
    """
    # Query public sessions, pre-loading user and preset info to avoid extra queries
    sessions = (
        db.query(PaperTradingSession)
        .filter(PaperTradingSession.is_public == True)
        .options(joinedload(PaperTradingSession.user), joinedload(PaperTradingSession.preset))
        .all()
    )

    # Convert numeric fields and handle potential None values
    for s in sessions:
        s.sharpe_ratio = float(s.sharpe_ratio or 0)
        s.max_drawdown = float(s.max_drawdown or 0)
        s.pnl_percentage = float(s.pnl_percentage or 0)
        s.resilience_score = float(s.resilience_score or 0)

    # Sort sessions by Sharpe Ratio (desc), then PnL (desc)
    sessions.sort(key=lambda s: (s.sharpe_ratio, s.pnl_percentage), reverse=True)

    # Build the response model with ranks
    leaderboard_entries = []
    for i, session in enumerate(sessions):
        leaderboard_entries.append(
            LeaderboardEntry(
                rank=i + 1,
                username=session.user.username,
                preset_name=session.preset.name,
                sharpe_ratio=session.sharpe_ratio,
                max_drawdown=session.max_drawdown,
                pnl_percentage=session.pnl_percentage,
                resilience_score=session.resilience_score
            )
        )

    return leaderboard_entries
