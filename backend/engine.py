from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Set

try:
    # Try relative imports first (when used as module)
    from .worker import EnhancedWorker
    from .closing_schedule_calculator import ClosingScheduleCalculator
    from .scoring_config import ScoringConfig, load_config
    from .scoring import (
        recalc_worker_schedule,
        update_score_on_close_early,
        update_score_on_y_fairness,
    )
except ImportError:
    # Fall back to absolute imports (when run directly)
    from worker import EnhancedWorker
    from closing_schedule_calculator import ClosingScheduleCalculator
    from scoring_config import ScoringConfig, load_config
    from scoring import (
        recalc_worker_schedule,
        update_score_on_close_early,
        update_score_on_y_fairness,
    )


Y_TASK_TYPES = [
    "Supervisor",
    "C&N Driver",
    "C&N Escort",
    "Southern Driver",
    "Southern Escort",
]


def compute_qualification_scarcity(workers: List[EnhancedWorker]) -> Tuple[Dict[str, int], Dict[str, float]]:
    """Compute per-task availability counts and scarcity scores (lower is less scarce).

    scarcity[task] = 1 / max(1, num_qualified)
    """
    availability: Dict[str, int] = {t: 0 for t in Y_TASK_TYPES}
    for w in workers:
        for t in Y_TASK_TYPES:
            if t in w.qualifications:
                availability[t] += 1
    scarcity: Dict[str, float] = {}
    for t, n in availability.items():
        scarcity[t] = 1.0 / max(1, n)
    return availability, scarcity


def compute_worker_scarcity_index(worker: EnhancedWorker, task_scarcity: Dict[str, float]) -> float:
    """Average scarcity across the worker's Y-task qualifications.

    Higher value ⇒ more scarce ⇒ protect from closing/overuse.
    """
    values: List[float] = []
    for t in Y_TASK_TYPES:
        if t in worker.qualifications:
            values.append(task_scarcity.get(t, 0.0))
    if not values:
        return 0.0
    return sum(values) / len(values)


@dataclass
class AssignmentDecision:
    worker_id: str
    worker_name: str
    reason: str
    debug: Dict[str, float]


@dataclass
class AssignmentError:
    task_type: str
    date: date
    reason: str
    severity: str  # 'warning' or 'error'


class SchedulingEngineV2:
    """Enhanced automatic scheduling engine with complete workflow implementation."""

    def __init__(self, cfg: Optional[ScoringConfig] = None):
        self.cfg = cfg or load_config()
        self.calc = ClosingScheduleCalculator()
        self.assignment_errors: List[AssignmentError] = []

    # ---------- Precompute ----------
    def precompute_all(self, workers: List[EnhancedWorker], semester_weeks: List[date]) -> None:
        """Precompute all worker schedules and scarcity data."""
        for w in workers:
            recalc_worker_schedule(w, semester_weeks)

        # Compute scarcity for Y-task assignment prioritization
        self.availability, self.task_scarcity = compute_qualification_scarcity(workers)
        self.worker_scarcity_index = {
            w.id: compute_worker_scarcity_index(w, self.task_scarcity)
            for w in workers
        }

    # ---------- Weekend closers ----------
    def rank_weekend_closer_candidates(
        self,
        workers: List[EnhancedWorker],
        friday: date,
    ) -> List[Tuple[EnhancedWorker, Tuple]]:
        """Rank weekend closer candidates using pre-computed optimal closing dates."""
        ranked: List[Tuple[EnhancedWorker, Tuple]] = []
        for w in workers:
            # Ineligible if closed last week (no consecutive closes)
            if any(h == friday - timedelta(days=7) for h in w.closing_history):
                continue
            
            # Use pre-computed optimal closing dates as primary criteria
            is_due = friday in w.optimal_closing_dates
            
            # Calculate distance to nearest optimal date for tie-breaking
            distances = [abs((d - friday).days // 7) for d in w.optimal_closing_dates]
            distance_to_due = min(distances) if distances else 999
            
            # Simple scoring: due workers first, then by distance to optimal, then basic fairness
            last_close = max(w.closing_history) if w.closing_history else date(1970,1,1)
            key = (
                0 if is_due else 1,          # due workers have highest priority
                distance_to_due,             # closer to optimal is better
                w.score,                     # basic fairness (lower score = less worked)
                last_close,                  # older last close gets priority
                w.id,                        # stable sort
            )
            ranked.append((w, key))
        ranked.sort(key=lambda x: x[1])
        return ranked

    # ---------- Weekday Y-task assignment ----------
    def pick_y_task_assignee(
        self,
        task_type: str,
        candidates: List[EnhancedWorker],
    ) -> Optional[AssignmentDecision]:
        """Pick Y-task assignee using scarcity and fairness principles."""
        if not candidates:
            return None
        
        ranked = []
        for w in candidates:
            # Candidate must actually have the qualification
            if task_type not in w.qualifications:
                continue
            
            # Priority based on:
            # 1. Current Y-task count for this specific task type (fewer = higher priority)
            # 2. Worker score (lower = less overworked = higher priority)
            # 3. Scarcity index (higher = more scarce = protect from overuse)
            current_task_count = w.y_task_counts.get(task_type, 0)
            scarcity_index = self.worker_scarcity_index.get(w.id, 0.0)
            
            key = (
                current_task_count,          # workers with fewer of this task type first
                w.score,                     # basic fairness (lower score = less worked)
                -scarcity_index,             # protect scarce workers (negative for reverse sort)
                w.id,                        # stable sort
            )
            ranked.append((w, key))
        
        if not ranked:
            return None
        
        ranked.sort(key=lambda x: x[1])
        chosen, key = ranked[0]
        current_task_count = key[0]
        
        return AssignmentDecision(
            worker_id=chosen.id,
            worker_name=chosen.name,
            reason=f"Scarcity-aware pick for {task_type} (count: {current_task_count}, score: {chosen.score:.1f})",
            debug={
                "current_task_count": current_task_count,
                "score": chosen.score,
                "scarcity_index": self.worker_scarcity_index.get(chosen.id, 0.0),
            },
        )

    # ---------- Weekend Y-task assignment ----------
    def _prioritize_tasks_by_scarcity(self, workers: List[EnhancedWorker], task_list: List[str]) -> List[str]:
        """Prioritize tasks by scarcity (fewer qualified workers first)."""
        availability, _ = compute_qualification_scarcity(workers)
        # Fewer qualified first (scarcer tasks first)
        return sorted(task_list, key=lambda t: availability.get(t, 0))

    def _eligible_weekend_worker(
        self,
        worker: EnhancedWorker,
        friday: date,
        already_assigned_ids: Set[str],
        ignore_recent_close: bool = False,
        ignore_next_required: bool = False,
        task: str = None,
        task_type_counts: Dict[str, Dict[str, int]] = None,
        max_same_task_type: int = None
    ) -> bool:
        """
        Check if worker is eligible for weekend Y-task assignment.
        
        Args:
            worker: The worker to check
            friday: The Friday date of the weekend
            already_assigned_ids: Set of worker IDs already assigned for this day
            ignore_recent_close: Whether to ignore recent closing restriction
            ignore_next_required: Whether to ignore next required closing restriction
            task: The task type being assigned
            task_type_counts: Dictionary mapping worker IDs to their task type counts
            max_same_task_type: Maximum number of times a worker can be assigned the same task type
        """
        # Skip if already assigned elsewhere for this weekend
        if worker.id in already_assigned_ids:
            return False
        
        # Avoid consecutive closes (last week) unless explicitly ignored
        if not ignore_recent_close and any(h == friday - timedelta(days=7) for h in worker.closing_history):
            return False
        
        # Avoid required next week to prevent back-to-back with required close unless explicitly ignored
        if not ignore_next_required and friday + timedelta(days=7) in getattr(worker, 'required_closing_dates', []):
            return False
            
        # Skip if worker already reached task type limit
        if task and task_type_counts and max_same_task_type:
            worker_task_counts = task_type_counts.get(worker.id, {})
            current_task_type_count = worker_task_counts.get(task, 0)
            if current_task_type_count >= max_same_task_type:
                return False
        
        return True

    def _has_x_task_conflict(self, worker: EnhancedWorker, target_date: date) -> bool:
        """Check if worker has X-task conflict on the target date."""
        if not hasattr(worker, 'x_tasks') or not worker.x_tasks:
            return False
            
        # Check both date object and string formats
        date_str = target_date.strftime('%d/%m/%Y')
        
        # Check if worker has X-task on this exact date
        if target_date in worker.x_tasks or date_str in worker.x_tasks:
            x_task = worker.x_tasks.get(target_date) or worker.x_tasks.get(date_str)
            # Allow RITUK X-tasks (they can do Y-tasks too)
            if x_task and x_task.lower() != 'rituk':
                return True
        
        return False

    def _filter_weekday_candidates(
        self, 
        qualified_workers: List[EnhancedWorker], 
        task_date: date,
        task_type: str,
        day_assigned_ids: Set[str],
        weekly_assigned_workers: Set[str],
        logs: List[str],
        weekly_worker_counts: Dict[str, int] = None,
        task_type_counts: Dict[str, Dict[str, int]] = None,
        weekly_limit: int = 1,
        max_same_task_type: int = 1,
        allow_fallback: bool = True
    ) -> List[EnhancedWorker]:
        """
        Apply comprehensive filtering for weekday Y-task candidates (strict criteria).
        
        Filters out workers who:
        1. Already assigned a Y-task today (hard constraint)
        2. Already reached their weekly Y-task limit (soft constraint if allow_fallback=True)
        3. Already reached their task type limit (soft constraint if allow_fallback=True)
        4. Are weekend closers (closing on upcoming Friday)
        5. Had X-task in last 1 day (cooldown period)
        6. Already have Y-task on this date in persistent data (hard constraint)
        
        Args:
            task_type: The type of task being assigned
            allow_fallback: If True, will return all workers who meet hard constraints
                           when no workers meet all constraints
            task_type_counts: Dictionary mapping worker IDs to their task type counts
            max_same_task_type: Maximum number of times a worker can be assigned the same task type
        """
        # First try with all constraints
        eligible = []
        weekly_counts = weekly_worker_counts or {}
        type_counts = task_type_counts or {}
        
        for worker in qualified_workers:
            # 1. Skip if already assigned Y-task today (HARD CONSTRAINT)
            if worker.id in day_assigned_ids:
                continue
                
            # 2. WEEKLY LIMIT: Skip if already reached weekly limit
            current_weekly_count = weekly_counts.get(worker.id, 0)
            if worker.id in weekly_assigned_workers or current_weekly_count >= weekly_limit:
                continue
                
            # 3. TASK TYPE LIMIT: Skip if already reached task type limit
            worker_task_counts = type_counts.get(worker.id, {})
            current_task_type_count = worker_task_counts.get(task_type, 0)
            if current_task_type_count >= max_same_task_type:
                logs.append(f"  {worker.name} excluded: already assigned {task_type} {current_task_type_count} times (limit: {max_same_task_type})")
                continue
                
            # 3. Skip if worker is a weekend closer (check upcoming Friday)
            friday = task_date + timedelta(days=(4 - task_date.weekday()) % 7)
            if friday in getattr(worker, 'required_closing_dates', []):
                logs.append(f"  {worker.name} excluded: weekend closer on {friday.strftime('%d/%m/%Y')}")
                continue
                
            # 4. Skip if worker had X-task within last 1 day (cooldown)
            yesterday = task_date - timedelta(days=1)
            if self._has_x_task_conflict(worker, yesterday):
                x_task = worker.x_tasks.get(yesterday) or worker.x_tasks.get(yesterday.strftime('%d/%m/%Y'))
                logs.append(f"  {worker.name} excluded: X-task cooldown ({x_task} on {yesterday.strftime('%d/%m/%Y')})")
                continue
                
            # 5. Skip if already has Y-task on this date in persistent data (HARD CONSTRAINT)
            if hasattr(worker, 'y_tasks') and task_date in worker.y_tasks:
                logs.append(f"  {worker.name} excluded: already has Y-task on {task_date.strftime('%d/%m/%Y')}")
                continue
                
            eligible.append(worker)
        
        # If we have eligible workers, return them
        if eligible or not allow_fallback:
            return eligible
            
        # FALLBACK: If no workers meet all criteria, try with relaxed constraints
        logs.append(f"⚠️ FALLBACK: No ideal candidates for {task_type} on {task_date.strftime('%d/%m/%Y')}, relaxing limits")
        
        # First try relaxing just the weekly limit
        fallback_eligible = []
        for worker in qualified_workers:
            # 1. Skip if already assigned Y-task today (HARD CONSTRAINT)
            if worker.id in day_assigned_ids:
                continue
                
            # 2. Skip if already has Y-task on this date in persistent data (HARD CONSTRAINT)
            if hasattr(worker, 'y_tasks') and task_date in worker.y_tasks:
                continue
            
            # 3. TASK TYPE LIMIT: Still try to respect task type limit
            worker_task_counts = type_counts.get(worker.id, {})
            current_task_type_count = worker_task_counts.get(task_type, 0)
            if current_task_type_count >= max_same_task_type:
                continue
                
            # Add to fallback list
            fallback_eligible.append(worker)
            
        # If still no eligible workers, try relaxing task type limit too
        if not fallback_eligible:
            logs.append(f"⚠️ EXTREME FALLBACK: No candidates for {task_type} even with relaxed weekly limit, relaxing task type limit too")
            for worker in qualified_workers:
                # 1. Skip if already assigned Y-task today (HARD CONSTRAINT)
                if worker.id in day_assigned_ids:
                    continue
                    
                # 2. Skip if already has Y-task on this date in persistent data (HARD CONSTRAINT)
                if hasattr(worker, 'y_tasks') and task_date in worker.y_tasks:
                    continue
                    
                # Add to fallback list
                fallback_eligible.append(worker)
        
        # Sort fallback candidates by score (prefer less overworked workers)
        fallback_eligible.sort(key=lambda w: w.score)
        
        return fallback_eligible

    def _filter_weekday_candidates_relaxed(
        self, 
        qualified_workers: List[EnhancedWorker], 
        task_date: date, 
        day_assigned_ids: Set[str],
        logs: List[str]
    ) -> List[EnhancedWorker]:
        """
        Apply relaxed filtering for weekday Y-task candidates when strict criteria fails.
        
        Only enforces critical constraints:
        1. Not already assigned Y-task today
        2. Not already has Y-task on this date in persistent data
        3. Not weekend closer (still enforce this as it's a hard conflict)
        
        Returns workers sorted by score (less overworked first).
        """
        eligible = []
        
        for worker in qualified_workers:
            # 1. Skip if already assigned Y-task today (hard constraint)
            if worker.id in day_assigned_ids:
                continue
                
            # 2. Skip if already has Y-task on this date in persistent data (hard constraint)
            if hasattr(worker, 'y_tasks') and task_date in worker.y_tasks:
                continue
                
            # 3. Skip if worker is a weekend closer (hard constraint)
            friday = task_date + timedelta(days=(4 - task_date.weekday()) % 7)
            if friday in getattr(worker, 'required_closing_dates', []):
                continue
                
            eligible.append(worker)
        
        # Sort by score (less overworked workers first)
        eligible.sort(key=lambda w: w.score)
            
        return eligible

    def _select_fairest_weekday_candidate(
        self, 
        eligible_workers: List[EnhancedWorker], 
        task: str, 
        logs: List[str]
    ) -> EnhancedWorker:
        """
        Select the fairest candidate for weekday Y-task assignment.
        
        Prioritizes:
        1. Lower total score (less overworked)
        2. Lower count for this specific task type
        3. Worker scarcity index (protect scarce workers)
        """
        if not eligible_workers:
            return None
            
        # Sort by fairness criteria
        def sort_key(worker):
            task_count = worker.y_task_counts.get(task, 0)
            # Handle case where worker_scarcity_index might not be initialized
            scarcity_penalty = getattr(self, 'worker_scarcity_index', {}).get(worker.id, 0.0)
            
            return (
                worker.score,           # Primary: total workload (lower is better)
                task_count,            # Secondary: task-specific fairness 
                -scarcity_penalty,     # Tertiary: protect scarce workers (higher scarcity = avoid)
                worker.id              # Stable sort
            )
        
        eligible_workers.sort(key=sort_key)
        chosen = eligible_workers[0]
        
        # Log selection reasoning
        task_count = chosen.y_task_counts.get(task, 0)
        logs.append(f"  Selected {chosen.name}: score={chosen.score:.1f}, {task}_count={task_count}")
        
        return chosen

    def assign_weekend_y_tasks(
        self,
        workers: List[EnhancedWorker],
        thursday: date,
        picked_closers: List[EnhancedWorker],
        task_type_counts: Dict[str, Dict[str, int]] = None,
        max_same_task_type: int = 1
    ) -> Tuple[Dict[date, List[Tuple[str, str]]], List[str]]:
        """
        Assign weekend Y-tasks (Thu–Sat) with scarcity-aware prioritization.
        
        Args:
            workers: List of workers to assign tasks to
            thursday: The Thursday date of the weekend block
            picked_closers: List of workers assigned as weekend closers
            task_type_counts: Dictionary mapping worker IDs to their task type counts
            max_same_task_type: Maximum number of times a worker can be assigned the same task type
        """
        logs: List[str] = []
        assigns: Dict[date, List[Tuple[str, str]]] = {}
        friday = thursday + timedelta(days=1)
        saturday = thursday + timedelta(days=2)
        days = [thursday, friday, saturday]
        
        # Initialize task type counts if not provided
        worker_task_type_counts = task_type_counts or {}

        # 1) Prioritize tasks by scarcity
        tasks_in_priority = self._prioritize_tasks_by_scarcity(workers, Y_TASK_TYPES)
        logs.append(f"Weekend task priority by scarcity: {tasks_in_priority}")

        # Helper to add assignment
        def add_assign(d: date, task: str, w: EnhancedWorker):
            assigns.setdefault(d, []).append((task, w.id))
            # CRITICAL FIX: Actually assign the Y task to the worker object
            w.assign_y_task(d, task)
            
            # Update task type counts
            if w.id not in worker_task_type_counts:
                worker_task_type_counts[w.id] = {}
            worker_task_type_counts[w.id][task] = worker_task_type_counts[w.id].get(task, 0) + 1
            
            # increment per-task count to impact fairness
            if task in w.y_task_counts:
                w.y_task_counts[task] += 1
            logs.append(f"Weekend Y assign {task} → {w.name} on {d.strftime('%d/%m/%Y')}")

        # 2) Assign closers first (they work Thu–Sat)
        for d in days:
            assigned_ids_for_day: Set[str] = set()
            # Give closers the scarcest tasks first
            for task in tasks_in_priority:
                # Pick among closers who are qualified and not already assigned another task this day
                candidates = [w for w in picked_closers if task in w.qualifications and w.id not in assigned_ids_for_day]
                if not candidates:
                    logs.append(f"No eligible closers for {task} on {d.strftime('%d/%m/%Y')}")
                    continue
                
                # Prefer lower score and higher scarcity
                candidates.sort(key=lambda w: (w.score, -self.worker_scarcity_index.get(w.id, 0.0), w.id))
                chosen = candidates[0]
                add_assign(d, task, chosen)
                assigned_ids_for_day.add(chosen.id)

        # 3) Fill remaining Y tasks for weekend from eligible workers
        for d in days:
            assigned_ids_for_day: Set[str] = set(wid for _, wid in assigns.get(d, []))
            
            for task in tasks_in_priority:
                # If task already assigned at least once this day, continue to keep 1 per task per day
                if any(t == task for t, _ in assigns.get(d, [])):
                    continue
                
                qualified = [w for w in workers if task in w.qualifications]
                if not qualified:
                    error = AssignmentError(
                        task_type=task,
                        date=d,
                        reason=f"No workers qualified for {task}",
                        severity="error"
                    )
                    self.assignment_errors.append(error)
                    logs.append(f"ERROR: No qualified workers for {task} on {d.strftime('%d/%m/%Y')}")
                    continue

                # Stage A: eligible and with optimal closing on this weekend (preference)
                stage_a = [w for w in qualified
                           if self._eligible_weekend_worker(
                               w, friday, assigned_ids_for_day, 
                               task=task, task_type_counts=worker_task_type_counts, max_same_task_type=max_same_task_type
                           )
                           and friday in getattr(w, 'optimal_closing_dates', [])]
                
                # Stage B: eligible workers (no optimal closing requirement)
                stage_b = [w for w in qualified if self._eligible_weekend_worker(
                    w, friday, assigned_ids_for_day,
                    task=task, task_type_counts=worker_task_type_counts, max_same_task_type=max_same_task_type
                )]
                
                # Stage C: any remaining qualified workers (ignore eligibility constraints)
                stage_c = [w for w in qualified if w.id not in assigned_ids_for_day]

                assigned = False
                for pool, label in ((stage_a, 'optimal'), (stage_b, 'eligible'), (stage_c, 'any')):
                    if not pool:
                        continue
                    
                    # Sort by score, then by scarcity (protect scarce workers), then by ID for stability
                    pool.sort(key=lambda w: (w.score, -self.worker_scarcity_index.get(w.id, 0.0), w.id))
                    chosen = pool[0]
                    add_assign(d, task, chosen)
                    assigned_ids_for_day.add(chosen.id)
                    logs.append(f"  Stage {label}: {chosen.name} (score: {chosen.score:.1f})")
                    assigned = True
                    break

                if not assigned:
                    error = AssignmentError(
                        task_type=task,
                        date=d,
                        reason=f"All qualified workers already assigned or ineligible",
                        severity="error"
                    )
                    self.assignment_errors.append(error)
                    logs.append(f"ERROR: Could not assign {task} on {d.strftime('%d/%m/%Y')}")

        return assigns, logs

    # ---------- Weekend scheduling ----------
    def assign_weekend_closers(
        self,
        workers: List[EnhancedWorker],
        thursday: date,
        num_slots: int,
        semester_weeks: List[date],
    ) -> Tuple[List[EnhancedWorker], List[str]]:
        """Assign weekend closers with required X-task handling."""
        logs: List[str] = []
        assigned: List[EnhancedWorker] = []

        # 1) Required by X task/required dates
        friday = thursday + timedelta(days=1)
        required: List[EnhancedWorker] = [
            w for w in workers if friday in w.required_closing_dates
        ]
        for w in required:
            assigned.append(w)
            self.after_closing_assigned(w, friday, semester_weeks)
            logs.append(f"Required close: {w.name} (X task Rituk)")

        remaining = max(0, num_slots - len(assigned))
        if remaining == 0:
            logs.append(f"All slots filled by required closers")
            return assigned, logs

        # 2) Rank candidates for remaining slots
        next_friday = friday + timedelta(days=7)
        prev_friday = friday - timedelta(days=7)
        candidates_ranked = []
        for (w, key) in self.rank_weekend_closer_candidates(workers, friday):
            if w in assigned:
                continue
            if next_friday in w.required_closing_dates:
                # Skip to avoid consecutive with next week's required close
                continue
            if prev_friday in w.required_closing_dates:
                # Skip to avoid consecutive with last week's required close
                continue
            candidates_ranked.append((w, key))

        for w, key in candidates_ranked:
            if remaining == 0:
                break
            # Avoid consecutive closes
            if any(h == friday - timedelta(days=7) for h in w.closing_history):
                continue
            
            # With pre-computed optimal dates, assignment is much simpler
            is_due = friday in w.optimal_closing_dates
            status = "due" if is_due else "available"
            
            assigned.append(w)
            self.after_closing_assigned(w, friday, semester_weeks)
            remaining -= 1
            logs.append(f"Picked close: {w.name} ({status}) (Thu–Sat block starting {thursday.strftime('%d/%m/%Y')})")

        if remaining > 0:
            logs.append(f"WARNING: Could not fill {remaining} remaining closer slots")
            error = AssignmentError(
                task_type="Weekend_Closer",
                date=friday,
                reason=f"Could not fill {remaining} closer slots",
                severity="warning"
            )
            self.assignment_errors.append(error)

        return assigned, logs

    # ---------- Weekday Y-task scheduling ----------
    def assign_weekday_y_tasks(
        self,
        workers: List[EnhancedWorker],
        tasks_by_date: Dict[date, List[str]],
        weekly_limit: int = 1,
        max_same_task_type: int = 1,
        task_type_counts: Dict[str, Dict[str, int]] = None,
    ) -> Tuple[Dict[date, List[Tuple[str, str]]], List[str]]:
        """
        Assign weekday Y tasks with comprehensive fairness and conflict avoidance.
        
        Key improvements:
        1. Score-based fair distribution (prioritize underworked workers)
        2. Prevent assignments to weekend closers
        3. X-task cooldown period (1 day after X-tasks)
        4. STRICT weekly limit (default: max 1 Y-task per worker per week)
        5. TASK TYPE LIMIT (default: max 1 of the same task type per worker)
        6. Proper conflict detection and logging
        
        Args:
            workers: List of workers to assign tasks to
            tasks_by_date: Dictionary mapping dates to lists of task types
            weekly_limit: Maximum number of Y-tasks per worker per week (default: 1)
            max_same_task_type: Maximum number of times a worker can be assigned the same task type (default: 1)
            task_type_counts: Dictionary mapping worker IDs to their task type counts
        """
        logs: List[str] = []
        assignments: Dict[date, List[Tuple[str, str]]] = {}
        
        # Track weekly assignments to enforce strict weekly limit
        weekly_assigned_workers = set()
        weekly_worker_counts = {}  # Track how many tasks each worker has this week
        worker_task_type_counts = task_type_counts or {}  # Track how many of each task type per worker
        
        logs.append(f"Enforcing strict weekly limit: max {weekly_limit} Y-task per worker")
        logs.append(f"Enforcing task variety: max {max_same_task_type} of the same task type per worker")
        
        # Prioritize tasks by scarcity across all workers
        all_tasks = set()
        for task_list in tasks_by_date.values():
            all_tasks.update(task_list)
        task_priority = self._prioritize_tasks_by_scarcity(workers, list(all_tasks))
        logs.append(f"Weekday task priority by scarcity: {task_priority}")

        for d, task_list in sorted(tasks_by_date.items()):
            # Skip weekend days for weekday Y-tasks
            if d.weekday() in {3, 4, 5}:  # Thu, Fri, Sat
                logs.append(f"Skip Y-tasks on weekend day {d.strftime('%d/%m/%Y')} (Thu–Sat)")
                continue
            
            day_assigns: List[Tuple[str, str]] = []
            
            # Assign tasks in scarcity order
            prioritized_tasks = [t for t in task_priority if t in task_list]
            for task in prioritized_tasks:
                # Get already assigned worker IDs for this day
                day_assigned_ids = set(wid for _, wid in day_assigns)
                
                # Find qualified workers
                qualified_workers = [w for w in workers if task in w.qualifications]
                if not qualified_workers:
                    error = AssignmentError(
                        task_type=task,
                        date=d,
                        reason=f"No workers qualified for {task}",
                        severity="error"
                    )
                    self.assignment_errors.append(error)
                    logs.append(f"ERROR: No qualified workers for {task} on {d.strftime('%d/%m/%Y')}")
                    continue
                
                # Apply comprehensive filtering with priority levels
                eligible_workers = self._filter_weekday_candidates(
                    qualified_workers, d, task, day_assigned_ids, weekly_assigned_workers, logs,
                    weekly_worker_counts, worker_task_type_counts, weekly_limit, max_same_task_type
                )
                
                if not eligible_workers:
                    # Try relaxed criteria if no one is available
                    logs.append(f"No ideal candidates for {task} on {d.strftime('%d/%m/%Y')}, trying relaxed criteria...")
                    eligible_workers = self._filter_weekday_candidates_relaxed(
                        qualified_workers, d, day_assigned_ids, logs
                    )
                
                if not eligible_workers:
                    error = AssignmentError(
                        task_type=task,
                        date=d,
                        reason=f"All qualified workers have conflicts or are overworked",
                        severity="error"
                    )
                    self.assignment_errors.append(error)
                    logs.append(f"ERROR: No available candidates for {task} on {d.strftime('%d/%m/%Y')} after all filtering")
                    continue
                
                # Select best candidate using score-based fairness
                chosen = self._select_fairest_weekday_candidate(eligible_workers, task, logs)
                
                # Make the assignment
                day_assigns.append((task, chosen.id))
                chosen.assign_y_task(d, task)
                weekly_assigned_workers.add(chosen.id)
                
                # Update weekly count tracking
                weekly_worker_counts[chosen.id] = weekly_worker_counts.get(chosen.id, 0) + 1
                
                # Update task type count tracking
                if chosen.id not in worker_task_type_counts:
                    worker_task_type_counts[chosen.id] = {}
                worker_task_type_counts[chosen.id][task] = worker_task_type_counts[chosen.id].get(task, 0) + 1
                
                # Update counters
                if task in chosen.y_task_counts:
                    chosen.y_task_counts[task] += 1
                
                logs.append(f"Y assign {task} → {chosen.name} on {d.strftime('%d/%m/%Y')} (score: {chosen.score:.1f})")
            
            assignments[d] = day_assigns

        # Batch fairness after assigning all weekdays
        for w in workers:
            update_score_on_y_fairness(w, workers, self.cfg)

        return assignments, logs

    # ---------- Hooks -----------
    def after_closing_assigned(self, worker: EnhancedWorker, friday: date, semester_weeks: List[date]):
        """Update worker after closing assignment."""
        if friday not in worker.closing_history:
            worker.closing_history.append(friday)
            worker.closing_history.sort()
        # Recompute only for this worker to keep optimal dates and owed in sync
        recalc_worker_schedule(worker, semester_weeks)

    # ---------- Range utilities ----------
    @staticmethod
    def iter_weekend_block_starts(start: date, end: date) -> List[date]:
        """Return Thursday dates (weekend block starts Thu–Sat)."""
        thursdays: List[date] = []
        cur = start
        # move to first Thursday
        while cur.weekday() != 3 and cur <= end:
            cur += timedelta(days=1)
        while cur <= end:
            thursdays.append(cur)
            cur += timedelta(days=7)
        return thursdays

    # ---------- Full range orchestration ----------
    def schedule_range(
        self,
        workers: List[EnhancedWorker],
        start: date,
        end: date,
        num_closers_per_weekend: int,
        weekday_tasks: Optional[Dict[date, List[str]]] = None,
        weekly_limit: int = 1,
        max_same_task_type: int = 1,
    ) -> Dict:
        """
        Complete scheduling workflow as specified.
        
        Args:
            workers: List of workers to assign tasks to
            start: Start date of scheduling period
            end: End date of scheduling period
            num_closers_per_weekend: Number of closers to assign per weekend
            weekday_tasks: Dictionary mapping dates to lists of task types
            weekly_limit: Maximum number of Y-tasks per worker per week (default: 1)
            max_same_task_type: Maximum number of times a worker can be assigned the same task type (default: 1)
        """
        # Reset assignment errors
        self.assignment_errors.clear()
        
        # Build semester weeks (Fridays) and precompute
        thursdays = self.iter_weekend_block_starts(start, end)
        fridays = [t + timedelta(days=1) for t in thursdays]
        semester_weeks = fridays[:]
        
        # Ensure semester_weeks has at least one element for the closing schedule calculator
        if not semester_weeks:
            # If no weekends in range, use the start date as a placeholder
            semester_weeks = [start]
        
        self.precompute_all(workers, semester_weeks)

        closers: Dict[date, List[str]] = {}
        logs: List[str] = []
        y_assigns: Dict[date, List[Tuple[str, str]]] = {}
        
        # CRITICAL FIX: Track worker assignments across all tasks
        weekly_worker_counts: Dict[str, int] = {}  # worker_id -> total count
        task_type_counts: Dict[str, Dict[str, int]] = {}  # worker_id -> {task_type -> count}
        
        logs.append(f"Enforcing strict weekly limit: max {weekly_limit} Y-task per worker across ALL assignments")
        logs.append(f"Enforcing task variety: max {max_same_task_type} of the same task type per worker")

        # Check if range includes weekends
        has_weekends = len(thursdays) > 0

        if has_weekends:
            # Start with weekend closers
            logs.append("=== WEEKEND SCHEDULING ===")
            for thursday, friday in zip(thursdays, fridays):
                logs.append(f"Processing weekend starting {thursday.strftime('%d/%m/%Y')}")
                
                # Assign weekend closers first
                picked_closers, closer_logs = self.assign_weekend_closers(
                    workers, thursday, num_closers_per_weekend, semester_weeks
                )
                closers[friday] = [w.id for w in picked_closers]
                logs.extend([f"{friday.strftime('%d/%m/%Y')}: {msg}" for msg in closer_logs])
                
                # CRITICAL FIX: Filter workers who haven't reached weekly limit
                available_workers = [w for w in workers if weekly_worker_counts.get(w.id, 0) < weekly_limit]
                
                # If we have enough available workers, use them
                if len(available_workers) > 0:
                    if len(available_workers) < len(workers):
                        logs.append(f"Filtered out {len(workers) - len(available_workers)} workers who reached weekly limit")
                else:
                    # FALLBACK: If no workers under the limit, use all workers
                    # but prioritize those with lower scores
                    logs.append("⚠️ FALLBACK: No workers under weekly limit for weekend tasks, using all workers")
                    available_workers = workers.copy()
                    # Sort by score to prioritize less overworked workers
                    available_workers.sort(key=lambda w: w.score)
                
                # Assign weekend Y tasks (Thu–Sat) with scarcity and fairness
                weekend_y, weekend_logs = self.assign_weekend_y_tasks(
                    available_workers, 
                    thursday, 
                    picked_closers,
                    task_type_counts=task_type_counts,
                    max_same_task_type=max_same_task_type
                )
                logs.extend([f"{friday.strftime('%d/%m/%Y')}: {msg}" for msg in weekend_logs])
                
                # Merge into y_assigns and update weekly counts
                for d, pairs in weekend_y.items():
                    y_assigns.setdefault(d, []).extend(pairs)
                    # Update weekly counts and task type counts
                    for task_type, worker_id in pairs:
                        # Update weekly total count
                        weekly_worker_counts[worker_id] = weekly_worker_counts.get(worker_id, 0) + 1
                        
                        # Update task type count
                        if worker_id not in task_type_counts:
                            task_type_counts[worker_id] = {}
                        task_type_counts[worker_id][task_type] = task_type_counts[worker_id].get(task_type, 0) + 1

        # Assign weekday Y tasks
        if weekday_tasks:
            logs.append("=== WEEKDAY SCHEDULING ===")
            
            # CRITICAL FIX: Track workers who are weekend closers to exclude them from weekday tasks
            weekend_closer_ids = set()
            for friday_date, closer_list in closers.items():
                weekend_closer_ids.update(closer_list)
                
            if weekend_closer_ids:
                logs.append(f"Excluding {len(weekend_closer_ids)} weekend closers from weekday Y-tasks")
                closer_names = [next((w.name for w in workers if w.id == cid), cid) for cid in weekend_closer_ids]
                logs.append(f"Weekend closers: {', '.join(closer_names)}")
            
            # Filter workers who:
            # 1. Are not weekend closers
            # 2. Haven't reached their weekly limit (if possible)
            eligible_weekday_workers = []
            
            for w in workers:
                # Skip weekend closers
                if w.id in weekend_closer_ids:
                    continue
                    
                # Skip if reached weekly limit
                if weekly_worker_counts.get(w.id, 0) >= weekly_limit:
                    continue
                    
                eligible_weekday_workers.append(w)
            
            # If we have enough eligible workers, use them
            if len(eligible_weekday_workers) > 0:
                if len(eligible_weekday_workers) < len(workers) - len(weekend_closer_ids):
                    filtered_count = len(workers) - len(weekend_closer_ids) - len(eligible_weekday_workers)
                    logs.append(f"Filtered out {filtered_count} workers who reached weekly limit")
            else:
                # FALLBACK: If no workers under the limit, use all non-weekend-closers
                # but prioritize those with lower scores
                logs.append("⚠️ FALLBACK: No workers under weekly limit, using all available workers")
                eligible_weekday_workers = [w for w in workers if w.id not in weekend_closer_ids]
                # Sort by score to prioritize less overworked workers
                eligible_weekday_workers.sort(key=lambda w: w.score)
            
            # Apply strict weekly limit and task type limit
            weekday_y, weekday_logs = self.assign_weekday_y_tasks(
                eligible_weekday_workers, 
                weekday_tasks, 
                weekly_limit=weekly_limit,
                max_same_task_type=max_same_task_type,
                task_type_counts=task_type_counts
            )
            logs.extend(weekday_logs)
            
            # Merge into y_assigns and update weekly counts
            for d, pairs in weekday_y.items():
                y_assigns.setdefault(d, []).extend(pairs)
                # Update weekly counts and task type counts
                for task_type, worker_id in pairs:
                    # Update weekly total count
                    weekly_worker_counts[worker_id] = weekly_worker_counts.get(worker_id, 0) + 1
                    
                    # Update task type count
                    if worker_id not in task_type_counts:
                        task_type_counts[worker_id] = {}
                    task_type_counts[worker_id][task_type] = task_type_counts[worker_id].get(task_type, 0) + 1

        # Check for assignment errors and provide summary
        if self.assignment_errors:
            logs.append("=== ASSIGNMENT ERRORS/WARNINGS ===")
            error_count = sum(1 for e in self.assignment_errors if e.severity == "error")
            warning_count = sum(1 for e in self.assignment_errors if e.severity == "warning")
            
            if error_count > 0:
                logs.append(f"ERRORS: {error_count} tasks could not be assigned automatically")
            if warning_count > 0:
                logs.append(f"WARNINGS: {warning_count} assignment issues detected")
            
            for error in self.assignment_errors:
                logs.append(f"{error.severity.upper()}: {error.task_type} on {error.date.strftime('%d/%m/%Y')} - {error.reason}")

        # Final fairness update
        logs.append("=== FINAL FAIRNESS UPDATE ===")
        for w in workers:
            update_score_on_y_fairness(w, workers, self.cfg)

        return {
            "closers": closers,
            "y_tasks": y_assigns,
            "logs": logs,
            "assignment_errors": [
                {
                    "task_type": e.task_type,
                    "date": e.date.strftime('%d/%m/%Y'),
                    "reason": e.reason,
                    "severity": e.severity
                }
                for e in self.assignment_errors
            ],
            "success": len([e for e in self.assignment_errors if e.severity == "error"]) == 0
        }


