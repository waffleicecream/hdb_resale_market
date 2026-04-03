"""
trial_predict.py — HDB Resale Price Prediction using OLS model.

Loads pre-serialized model artifacts from backend/price_model/ and outputs
a predicted resale price + 80% prediction interval in real SGD
(RPI-adjusted, Q4 2025 base = 203.6).

Prerequisites:
  Run Step 7 in backend/price_model/ols_modelling.ipynb to generate:
    backend/price_model/ols_model.pkl
    backend/price_model/ols_scaler.joblib
    backend/price_model/ols_feature_cols.json

Usage:
    Edit POSTAL_CODE, FLAT_TYPE, FLOOR_CATEGORY, REMAINING_LEASE in backend/user_input.py,
    then run: python backend/trial_predict.py
"""

import json
import sys

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

# =============================================================================
# USER INPUTS — edit in backend/user_input.py before running
# =============================================================================
from user_input import POSTAL_CODE, FLAT_TYPE, FLOOR_CATEGORY, REMAINING_LEASE, TOWN_OVERRIDE, compute_features

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR    = Path(__file__).parent          # backend/
MODEL_DIR   = BASE_DIR / "price_model"
MODEL_PATH  = MODEL_DIR / "ols_model.pkl"
SCALER_PATH = MODEL_DIR / "ols_scaler.joblib"
COLS_PATH   = MODEL_DIR / "ols_feature_cols.json"

# =============================================================================
# LOAD MODEL ARTIFACTS
# =============================================================================
for path in (MODEL_PATH, SCALER_PATH, COLS_PATH):
    if not path.exists():
        raise FileNotFoundError(
            f"Missing model artifact: {path}\n"
            "Run Step 7 in backend/price_model/ols_modelling.ipynb first."
        )

sys.path.insert(0, str(BASE_DIR))

ols_model = sm.load(str(MODEL_PATH))
scaler    = joblib.load(SCALER_PATH)
with open(COLS_PATH) as f:
    feature_cols = json.load(f)

# =============================================================================
# COMPUTE FEATURES
# =============================================================================
features = compute_features(POSTAL_CODE, FLAT_TYPE, FLOOR_CATEGORY, REMAINING_LEASE, TOWN_OVERRIDE)

# =============================================================================
# BUILD FEATURE VECTOR
# =============================================================================
CONTINUOUS = [
    "remaining_lease_years", "nearest_train_dist_m", "dist_nearest_hawker_m",
    "dist_nearest_primary_m", "num_primary_1km", "dist_nearest_park_m",
    "dist_nearest_sportsg_m", "dist_nearest_mall_m", "dist_nearest_healthcare_m",
    "num_parks_1km",
]

# Scale continuous features using the saved scaler (fit on training data)
cont_vals   = np.array([[features[c] for c in CONTINUOUS]])
cont_scaled = scaler.transform(cont_vals)
cont_df     = pd.DataFrame(cont_scaled, columns=CONTINUOUS)

# Initialise all dummy columns to 0
dummy_cols = [c for c in feature_cols if c not in CONTINUOUS]
row = {col: 0 for col in dummy_cols}

# Set active dummy (reference categories are left at 0):
#   flat_type ref = 2 ROOM
#   town ref      = ANG MO KIO
#   floor ref     = Low (floors 1–5)
flat_col  = f"flat_type_{FLAT_TYPE}"
town_col  = f"town_{features['town']}"
floor_col = f"floor_category_{FLOOR_CATEGORY}"

if flat_col  in row: row[flat_col]  = 1
if town_col  in row: row[town_col]  = 1
if floor_col in row: row[floor_col] = 1

dummy_df = pd.DataFrame([row])

# Concatenate and reorder to match exact training column order
X_new       = pd.concat([cont_df, dummy_df], axis=1)[feature_cols]
X_new_const = sm.add_constant(X_new, has_constant="add")

# =============================================================================
# PREDICT
# =============================================================================
pred  = ols_model.get_prediction(X_new_const)
frame = pred.summary_frame(alpha=0.2)   # alpha=0.2 → 80% prediction interval

# The OLS model was trained on log(resale_price_real), so all outputs from
# get_prediction() are in log space. np.exp() converts them back to real SGD
# (RPI-adjusted, Q4 2025 base = 203.6). The point estimate is the median
# predicted price (not mean) — no Duan smearing correction applied.
predicted_price = np.exp(frame["mean"].values[0])
pi_lower        = np.exp(frame["obs_ci_lower"].values[0])
pi_upper        = np.exp(frame["obs_ci_upper"].values[0])

# =============================================================================
# OUTPUT
# =============================================================================
print(f"\n{'─' * 52}")
print(f"  HDB Resale Price Prediction (OLS)")
print(f"{'─' * 52}")
print(f"  Postal Code    : {POSTAL_CODE}")
print(f"  Town           : {features['town']}")
print(f"  Flat Type      : {FLAT_TYPE}")
print(f"  Floor Category : {FLOOR_CATEGORY}")
print(f"  Remaining Lease: {REMAINING_LEASE}")
print(f"{'─' * 52}")
print(f"  Predicted Price: SGD {predicted_price:>10,.0f}")
print(f"  80% PI (lower) : SGD {pi_lower:>10,.0f}")
print(f"  80% PI (upper) : SGD {pi_upper:>10,.0f}")
print(f"  (RPI-adjusted, Q4 2025 real terms)")
print(f"{'─' * 52}\n")
