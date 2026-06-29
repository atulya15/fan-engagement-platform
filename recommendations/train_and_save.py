"""
recommendations/train_and_save.py
====================================
Trains the recommender once and pickles the result to
recommendations/model_state.pkl, which api.py loads at boot instead of
training live.

Why this exists: training (load_events -> temporal_split -> ALS ->
build_training_examples -> LightGBM) needs the full event-level
DataFrame and a sparse interaction matrix in memory at once, on top of
pandas/lightgbm/implicit's own import footprint -- comfortably more
than Render's free-tier 512MB, and it crashed the API on boot before
this script existed. The state that get_recommendation actually needs
to SERVE a request is much smaller (a few small dicts, the LightGBM
booster, and an ALS-derived score dict) -- see serve.py's
train_recommender_state for exactly what's dropped.

Run this manually whenever the underlying data changes (mirrors the
snapshot/build_snapshot.py pattern already used for the site):

    python -m recommendations.train_and_save

Then commit the resulting model_state.pkl so the deployed API can load
it without needing a live DATABASE_URL connection or a training pass
on every boot.
"""

import pickle
import sys
from pathlib import Path

from recommendations.serve import train_recommender_state

MODEL_STATE_PATH = Path(__file__).parent / "model_state.pkl"


def main():
    print("Training recommendation models...")
    state = train_recommender_state()
    with open(MODEL_STATE_PATH, "wb") as f:
        pickle.dump(state, f)
    size_mb = MODEL_STATE_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved {MODEL_STATE_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
