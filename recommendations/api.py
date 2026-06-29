"""
recommendations/api.py
========================
Recommendation endpoints as a FastAPI router, mounted by api/main.py
(the single deployed backend for Phase 6). Kept in recommendations/
rather than api/ since it's tightly coupled to recommendations/serve.py
-- the router is the "public interface" of this module, same as how
metrics/ exposes Python functions and dashboard/app.py calls them.

init_state() loads the pickled model state produced by
recommendations/train_and_save.py rather than training live at boot.
Training needs the full event-level DataFrame + a sparse interaction
matrix in memory at once on top of pandas/lightgbm/implicit's own
footprint -- comfortably more than Render's free-tier 512MB, and it
crashed the API on boot (OOM) before this split existed. Re-run
train_and_save.py and commit the new model_state.pkl whenever the
underlying data changes.
"""

import pickle
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from recommendations.serve import get_recommendation

STATE: dict = {}
MODEL_STATE_PATH = Path(__file__).parent / "model_state.pkl"


def init_state():
    """Called once from api/main.py's lifespan startup hook."""
    print(f"Loading recommendation models from {MODEL_STATE_PATH}...")
    with open(MODEL_STATE_PATH, "rb") as f:
        STATE.update(pickle.load(f))
    print("Recommendation models ready.")


router = APIRouter(tags=["recommendations"])


class RecommendationItem(BaseModel):
    widget_id: int
    widget_type: str
    score: float


class RecommendationResponse(BaseModel):
    user_id: int
    method_used: str
    is_cold_start: bool
    why: str
    recommendations: list[RecommendationItem]


@router.get("/recommend", response_model=RecommendationResponse)
def recommend(user_id: int, n: int = 10):
    if "hybrid_model" not in STATE:
        raise HTTPException(503, "Models still training, try again shortly.")
    result = get_recommendation(STATE, user_id, n=n)
    if result is None:
        raise HTTPException(404, f"user_id {user_id} not found")
    return result


@router.get("/recommend/health")
def health():
    return {"status": "ok", "models_loaded": "hybrid_model" in STATE}
