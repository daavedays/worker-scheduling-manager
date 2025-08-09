"""
Centralized scoring configuration. Tune values here (or override via config/scoring.json).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
import json
import os


@dataclass
class ScoringConfig:
    # Per Y-task weights (weekday fairness only). Supervisor tracked separately in logic
    TASK_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "Supervisor": 1.0,
        "C&N Driver": 1.0,
        "C&N Escort": 1.0,
        "Southern Driver": 1.0,
        "Southern Escort": 1.0,
    })

    # Weekday-only fairness
    WEEKDAY_ONLY_FOR_FAIRNESS: bool = True
    SUPERVISOR_SEPARATE: bool = True

    # Cohort strategy for fairness comparisons
    # "same_num_qualifications" | "has_required_qualification"
    COHORT_STRATEGY: str = "has_required_qualification"

    # Simplified scoring parameters for the new system
    # Early close compensation: fixed bonus (no longer interval-dependent)
    EARLY_CLOSE_BONUS: float = 1.0

    # Overdue reduction: base multiplier per weeks overdue
    OVERDUE_REDUCTION_PER_WEEK: float = 0.75

    # Convert remaining weekends_home_owed to score at semester end
    OWE_TO_SCORE_CONVERSION: float = 0.5

    # Simplified fairness weight
    Y_TASK_FAIRNESS_WEIGHT: float = 0.5

    # Penalties to subtract when assignments are reversed/switched
    SWITCH_PENALTY_Y_TASK: float = 0.5
    SWITCH_PENALTY_CLOSING: float = 1.5

    # Annual reset policy
    YEAR_RESET_ENABLED: bool = True


def load_config(overrides_path: Optional[str] = None) -> ScoringConfig:
    cfg = ScoringConfig()
    # Allow overrides via config/scoring.json
    if overrides_path is None:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        overrides_path = os.path.join(repo_root, "config", "scoring.json")
    try:
        if os.path.exists(overrides_path):
            with open(overrides_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
    except Exception:
        # Fail open with defaults
        pass
    return cfg


