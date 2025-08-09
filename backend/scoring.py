from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

try:
    # Try relative imports first (when used as module)
    from .worker import EnhancedWorker
    from .closing_schedule_calculator import ClosingScheduleCalculator
    from .scoring_config import ScoringConfig, load_config
except ImportError:
    # Fall back to absolute imports (when run directly)
    from worker import EnhancedWorker
    from closing_schedule_calculator import ClosingScheduleCalculator
    from scoring_config import ScoringConfig, load_config


def determine_cohort(worker: EnhancedWorker, all_workers: List[EnhancedWorker], task_type: Optional[str], strategy: str) -> List[EnhancedWorker]:
    if strategy == "same_num_qualifications":
        target = len(worker.qualifications)
        return [w for w in all_workers if len(w.qualifications) == target]
    # default: has_required_qualification
    if task_type is None:
        return list(all_workers)
    return [w for w in all_workers if task_type in w.y_task_counts]


def compute_weekday_task_averages(workers: List[EnhancedWorker], year: int, cfg: ScoringConfig) -> Dict[str, float]:
    # Only counts weekday Y tasks (Sun–Wed). Weekend Y tasks by closers are excluded from fairness.
    totals: Dict[str, int] = {}
    counts: Dict[str, int] = {}
    for w in workers:
        for task, c in w.y_task_counts.items():
            # Supervisor tracked separately by logic that consumes this function
            totals[task] = totals.get(task, 0) + c
            counts[task] = counts.get(task, 0) + (1 if c is not None else 0)
    averages: Dict[str, float] = {}
    for task, total in totals.items():
        n = counts.get(task, 1)
        averages[task] = total / max(1, n)
    return averages


def compute_weighted_totals(workers: List[EnhancedWorker], cfg: ScoringConfig) -> Dict[str, float]:
    weighted: Dict[str, float] = {}
    for w in workers:
        total = 0.0
        for task, count in w.y_task_counts.items():
            weight = cfg.TASK_WEIGHTS.get(task, 1.0)
            total += count * weight
        weighted[w.id] = total
    return weighted


def update_score_on_close_early(worker: EnhancedWorker, weeks_early_relative_to_interval: int, cfg: ScoringConfig) -> float:
    """Simplified early close scoring - no longer needed with pre-computed optimal dates."""
    # With optimal_closing_dates pre-computed, we don't need complex early close compensation
    # Just add a basic score adjustment for tracking
    basic_bonus = cfg.EARLY_CLOSE_BONUS  # Simple fixed bonus for any early close
    worker.add_score_bonus(basic_bonus, f"Early close (simplified)")
    return basic_bonus


def update_score_on_close_overdue(worker: EnhancedWorker, weeks_overdue: int, cfg: ScoringConfig) -> float:
    reduction = max(0.0, weeks_overdue * cfg.OVERDUE_REDUCTION_PER_WEEK)
    if reduction > 0:
        worker.subtract_score_bonus(reduction, f"Overdue close by {weeks_overdue}w")
    return reduction


def apply_semester_end_compensation(worker: EnhancedWorker, cfg: ScoringConfig) -> float:
    if getattr(worker, "weekends_home_owed", 0) <= 0:
        return 0.0
    converted = worker.weekends_home_owed * cfg.OWE_TO_SCORE_CONVERSION
    worker.add_score_bonus(converted, f"Converted {worker.weekends_home_owed} weekends owed → score")
    worker.weekends_home_owed = 0
    worker.home_weeks_owed = 0
    return converted


def update_score_on_y_fairness(worker: EnhancedWorker, all_workers: List[EnhancedWorker], cfg: ScoringConfig) -> Dict[str, float]:
    """Simplified Y-task fairness - basic scoring for workload tracking."""
    breakdown: Dict[str, float] = {}
    
    # Simple total Y-task count comparison
    worker_total = sum(worker.y_task_counts.values())
    all_totals = [sum(w.y_task_counts.values()) for w in all_workers]
    avg_total = sum(all_totals) / max(1, len(all_totals))
    
    # Simple bonus if significantly over average
    over_average = max(0.0, worker_total - avg_total)
    if over_average > 1.0:  # Only penalize if significantly over average
        bonus = over_average * cfg.Y_TASK_FAIRNESS_WEIGHT  # Configurable fairness weight
        worker.add_score_bonus(bonus, f"Over Y-task average: +{over_average:.1f}")
        breakdown["total_y_tasks"] = bonus
    
    return breakdown


def recalc_worker_schedule(worker: EnhancedWorker, semester_weeks: List[date]) -> Dict:
    """Recalculate closing dates for a single worker and update owed weekends if needed."""
    calc = ClosingScheduleCalculator()
    result = calc.calculate_worker_closing_schedule(worker, semester_weeks)
    worker.required_closing_dates = result["required_dates"]
    worker.optimal_closing_dates = result["optimal_dates"]
    # synchronize owed aliases
    worker.weekends_home_owed = result["final_weekends_home_owed"]
    worker.home_weeks_owed = worker.weekends_home_owed
    return result


def reverse_assignment_penalty(worker: EnhancedWorker, assignment_type: str, cfg: ScoringConfig) -> float:
    if assignment_type == "y_task":
        penalty = cfg.SWITCH_PENALTY_Y_TASK
    elif assignment_type == "closing":
        penalty = cfg.SWITCH_PENALTY_CLOSING
    else:
        penalty = 0.0
    if penalty > 0:
        worker.subtract_score_bonus(penalty, f"Reversed {assignment_type} assignment")
    return penalty


