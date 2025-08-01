from datetime import date, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
from .worker import Worker


class ScoreKeeper:
    """
    ENHANCED: Tracks worker scores and ensures fairness in task distribution.
    
    REVISED LOGIC: LOWER scores = HIGHER priority (better candidates)
    
    This class manages the scoring system for worker assignments, ensuring:
    - Fair distribution of tasks across workers
    - Proper handling of X tasks (no score additions)
    - Context-aware violation bonuses for closing assignments
    - Qualification balancing for scarce skills
    
    Key Features:
    - Persistent score tracking for each worker
    - Fairness adjustments based on workload balance
    - Qualification scarcity prioritization
    - X task exception handling (no score impact)
    """
    
    def __init__(self, workers: List[Worker]):
        """
        Initialize the ScoreKeeper with a list of workers.
        
        Args:
            workers: List of Worker objects to track
        """
        self.workers = workers
        self.assignment_history = {}  # worker_id -> list of assignments
    
    def update_worker_score(self, worker: Worker, assignment_type: str, date: date):
        """
        ENHANCED: Update worker score based on new assignment.
        REVISED: X tasks do NOT add to worker.score (as per requirements).
        """
        if assignment_type == "y_task":
            # Worker gets Y task - increase their score (make them less likely to get more tasks)
            worker.score += 1  # No cap on score
        elif assignment_type == "closing":
            # Worker gets closing - increase their score (make them less likely to get more tasks)
            worker.score += 5  # Base closing score
            # Add violation bonus if applicable
            violation_bonus = worker.calculate_closing_violation_bonus(date)
            worker.score += violation_bonus
        elif assignment_type == "x_task":
            # X tasks do NOT add to worker.score (as per requirements)
            pass
    
    def get_fairness_adjustment(self, worker: Worker) -> int:
        """
        Get fairness adjustment for a worker.
        CORRECT LOGIC: Returns positive value for overworked workers (penalty for tasks).
        Returns negative value for underworked workers (priority for tasks).
        Higher score = more overworked = should get fewer future tasks
        Lower score = less overworked = should get more future tasks
        """
        # Calculate workload balance
        avg_y_tasks = sum(len(w.y_tasks) for w in self.workers) / len(self.workers)
        avg_x_tasks = sum(len(w.x_tasks) for w in self.workers) / len(self.workers)
        
        # Worker's workload vs average
        y_task_delta = len(worker.y_tasks) - avg_y_tasks
        # x_task_delta = len(worker.x_tasks) - avg_x_tasks
        
        # CORRECT: Fairness adjustment (positive = overworked = penalty, negative = underworked = priority)
        # Overworked workers get higher scores (penalty), underworked workers get lower scores (priority)
        # INCREASED: Make fairness the dominant factor in scoring
        adjustment = (y_task_delta * 200)  # Increased from 50 to 200
        
        return int(adjustment)
    
    def get_qualification_balancing_adjustment(self, worker: Worker, task: str) -> int:
        """
        NEW: Get qualification balancing adjustment.
        Workers with rare qualifications get priority for those tasks.
        """
        # Count how many workers have this qualification
        qualified_count = sum(1 for w in self.workers if task in w.qualifications)
        total_workers = len(self.workers)
        
        if qualified_count == 0:
            return 0  # No qualified workers
        
        # Calculate scarcity (higher = more scarce)
        scarcity = total_workers / qualified_count
        
        if scarcity > 2.0:  # If qualification is scarce
            return -int(scarcity * 10)  # Priority for scarce qualifications
        else:
            return 0  # No adjustment for common qualifications


class SchedulerEngine:
    """
    ENHANCED: Advanced scheduling engine for worker task assignments.
    
    This engine implements a sophisticated scheduling algorithm that:
    - Assigns Y tasks with context-aware scoring
    - Manages weekend closing assignments with priority logic
    - Handles X task proximity and conflicts
    - Provides comprehensive warning systems
    - Ensures fair workload distribution
    
    Key Features:
    - Context-aware scoring (lower scores = higher priority)
    - Weekend vs weekday assignment logic
    - X task proximity analysis and penalties
    - Rituk exception handling
    - Violation bonus system for closing assignments
    - User warning system for conflicts
    - Local caching for performance optimization
    """
    
    def __init__(self, workers: List[Worker], start_date: date, end_date: date):
        """
        Initialize the SchedulerEngine with workers and date range.
        
        Args:
            workers: List of Worker objects to schedule
            start_date: Start date for scheduling period
            end_date: End date for scheduling period
        """
        self.workers = workers
        self.start_date = start_date
        self.end_date = end_date
        self.schedule: Dict[date, Dict[str, str]] = {}  # date -> task name -> worker id
        self.weekend_closers: Dict[date, Worker] = {}  # weekend_start_date -> assigned worker
        
        # ENHANCED: Local cache for weekend assignments (performance optimization)
        self.weekend_assignments_cache: Dict[date, Dict[str, Worker]] = {}  # week_start -> task -> worker
        
        # NEW: Score keeper for tracking fairness and workload balance
        self.score_keeper = ScoreKeeper(workers)
        
        # NEW: Warning system for X task conflicts (user experience enhancement)
        self.x_task_warnings = []

    def get_weekend_closing_candidates(self, workers: List[Worker], current_week: date) -> List[Worker]:
        """
        Get list of workers eligible for weekend closing assignment for the specified week.
        NEW SIMPLIFIED SCORING: Higher scores = better workers = should get FEWER tasks
        
        Args:
            workers: List of workers to evaluate
            current_week: Monday of the week in question
            
        Returns:
            List of workers sorted by closing score (lowest first - best workers get priority)
        """
        candidates = []
        rituk_candidates = []  # Special priority for workers with "Rituk" X task

        for worker in workers:
            # Check if worker has "Rituk" X task - these get top priority
            has_rituk = worker.has_specific_x_task(current_week, "Rituk") or worker.has_specific_x_task(
                current_week + timedelta(days=7), "Rituk")

            # Skip if worker has X task in current week or next week (except Rituk)
            if (worker.has_x_task(current_week) or worker.has_x_task(
                    current_week + timedelta(days=7))) and not has_rituk:
                continue

            # Skip workers with closing_interval of 0 (they don't participate in closing)
            if worker.closing_interval <= 0:
                continue

            # ENHANCED: Context-aware closing interval analysis
            closing_context = worker.get_closing_interval_context(current_week)
            
            # Skip if not due yet (but allow workers who never closed)
            if not closing_context['is_due'] and closing_context['next_due_date'] is not None:
                continue

            # ENHANCED: REVISED SCORING SYSTEM
            score = 0
            
            # Base worker score (higher = more overworked = lower priority)
            base_score = int(worker.score) if worker.score is not None else 0
            score += base_score
            
            # ENHANCED: Workload penalty (overworked workers get higher scores = lower priority)
            workload_score = worker.get_workload_score()
            score += workload_score
            
            # ENHANCED: Fairness adjustment from score keeper
            fairness_adjustment = self.score_keeper.get_fairness_adjustment(worker)
            score += fairness_adjustment
            
            # ENHANCED: Context-aware overdue bonus (workers who are overdue get priority = lower scores)
            if closing_context['is_overdue']:
                score -= closing_context['weeks_off'] * 15  # Enhanced priority for overdue workers
            
            # ENHANCED: X task proximity penalties with context awareness
            if worker.had_x_task_last_week(current_week):
                score += 100  # Heavy penalty for workers with X task last week
            
            if worker.just_finished_x_task(current_week):
                score += 50  # Penalty for workers who just finished X task
            
            # Context-aware upcoming X task penalties
            if worker.is_starting_x_task_soon(current_week, context_aware=True):
                score += 75  # Penalty for workers starting X task soon
            
            # ENHANCED: Rituk workers get priority (lower scores)
            if has_rituk:
                score -= 100  # Enhanced priority for Rituk workers

            if has_rituk:
                rituk_candidates.append((worker, score))
            else:
                candidates.append((worker, score))
            
            # ENHANCED: Check for X task conflicts and generate warnings
            warning_info = worker.should_warn_about_x_task_conflict(current_week)
            if warning_info['should_warn']:
                self.x_task_warnings.append({
                    'worker_id': worker.id,
                    'worker_name': worker.name,
                    'warning_message': warning_info['warning_message'],
                    'severity': warning_info['severity'],
                    'week': current_week
                })

        # Sort by score (lowest first - best workers get priority)
        rituk_candidates.sort(key=lambda x: x[1])
        candidates.sort(key=lambda x: x[1])

        # Return Rituk candidates first, then regular candidates
        return [worker for worker, score in rituk_candidates] + [worker for worker, score in candidates]
    
    def get_x_task_warnings(self):
        """
        NEW: Get all X task conflict warnings.
        
        Returns:
            List of warning dictionaries
        """
        return self.x_task_warnings
    
    def clear_x_task_warnings(self):
        """
        NEW: Clear all X task conflict warnings.
        """
        self.x_task_warnings = []

    def assign_y_tasks(self, start_date: date, end_date: date) -> List[Worker]:
        """
        ENHANCED: Assign Y tasks to workers for the specified date range.
        
        NEW LOGIC: Process weekends first, then weekdays.
        Weekend closers get Y tasks for Thursday-Saturday.
        
        This method implements a two-phase assignment strategy:
        
        Phase 1 (Weekend Processing):
        - Processes Thursday, Friday, Saturday assignments first
        - Prioritizes weekend closers for Y tasks on their closing weekends
        - Uses enhanced scoring with context-aware logic
        - Caches weekend assignments to prevent conflicts
        
        Phase 2 (Weekday Processing):
        - Processes Sunday, Monday, Tuesday, Wednesday assignments
        - Uses standard Y task assignment logic
        - Considers X task proximity and availability
        
        Key Features:
        - Context-aware scoring (lower scores = higher priority)
        - X task proximity analysis and penalties
        - Rituk exception handling
        - Fairness adjustments for workload balance
        - Qualification scarcity prioritization
        - Performance optimization through caching
        
        Args:
            start_date: Start date for Y task assignments
            end_date: End date for Y task assignments
            
        Returns:
            List of workers assigned to Y tasks
            
        Raises:
            ValueError: If start_date > end_date
            RuntimeError: If insufficient qualified workers available
        """
        # PERFORMANCE OPTIMIZATION: Clear existing Y task assignments for the date range
        # This prevents conflicts and ensures clean slate for new assignments
        for worker in self.workers:
            worker.y_tasks = {date: task for date, task in worker.y_tasks.items()
                              if date < start_date or date > end_date}

        assigned_workers = []
        processed_weeks = set()  # PERFORMANCE: Track which weeks we've already processed for weekend assignments
        
        # PHASE 1: Process weekend assignments FIRST (Thursday-Saturday)
        # This ensures weekend closers get Y tasks before weekday assignments
        # PERFORMANCE: Single pass through date range with early weekend detection
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()

            # CONTEXT-AWARE: Only process Thursday, Friday, Saturday for weekend assignments
            if weekday in [3, 4, 5]:  # Thursday, Friday, Saturday - Weekend Y tasks
                # ALGORITHM: Find the Sunday that starts this week (week starts on Sunday)
                week_start = current_date - timedelta(days=weekday + 1)  # Go back to Sunday

                # PERFORMANCE: Only assign weekend Y tasks if we haven't already processed this week
                # This prevents duplicate assignments and improves efficiency
                if week_start not in processed_weeks:
                    weekend_assignments = self._assign_weekend_y_tasks_for_week_enhanced(week_start)
                    assigned_workers.extend(weekend_assignments)
                    processed_weeks.add(week_start)  # Mark this week as processed

            current_date += timedelta(days=1)

        # PHASE 2: Process weekday assignments (Sunday-Wednesday)
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()

            if weekday in [6, 0, 1, 2]:  # Sunday, Monday, Tuesday, Wednesday - Daily Y tasks
                day_assignments = self._assign_y_tasks_for_day(current_date)
                assigned_workers.extend(day_assignments)

            current_date += timedelta(days=1)

        return assigned_workers

    def assign_y_tasks_weekday(self, start_date: date, end_date: date) -> List[Worker]:
        """
        NEW SIMPLIFIED FUNCTION: Assign Y tasks for weekdays only (Sunday-Wednesday).
        
        Args:
            start_date: Start date for Y task assignments
            end_date: End date for Y task assignments
            
        Returns:
            List of workers assigned to Y tasks
        """
        assigned_workers = []
        current_date = start_date
        
        while current_date <= end_date:
            weekday = current_date.weekday()
            
            # Only assign for weekdays (Sunday=6, Monday=0, Tuesday=1, Wednesday=2)
            if weekday in [6, 0, 1, 2]:
                day_assignments = self._assign_y_tasks_for_day(current_date)
                assigned_workers.extend(day_assignments)
            
            current_date += timedelta(days=1)
        
        return assigned_workers

    def assign_y_tasks_weekend(self, weekend_date: date) -> List[Worker]:
        """
        NEW SIMPLIFIED FUNCTION: Assign Y tasks for a specific weekend (Thursday-Saturday).
        
        Args:
            weekend_date: Any date in the weekend (Thursday, Friday, or Saturday)
            
        Returns:
            List of workers assigned to Y tasks
        """
        # Find the Sunday that starts this week
        weekday = weekend_date.weekday()
        if weekday in [3, 4, 5]:  # Thursday, Friday, Saturday
            week_start = weekend_date - timedelta(days=weekday + 1)  # Go back to Sunday
            return self._assign_weekend_y_tasks_for_week_enhanced(week_start)
        else:
            return []  # Not a weekend

    def _get_available_workers_for_day(self, current_date: date) -> List[Worker]:
        """
        ENHANCED: Get workers available for Y tasks on a specific day.
        NEW LOGIC: Context-aware X task proximity filtering with Rituk exceptions.
        """
        available = []

        for worker in self.workers:
            # ENHANCED: Context-aware X task proximity filtering
            if not self._is_worker_available_for_x_task_proximity(worker, current_date):
                continue

            # Skip if worker already has Y task on this day
            if current_date in worker.y_tasks:
                continue

            # Skip if worker is assigned weekend closing for this week
            weekday = current_date.weekday()
            if weekday == 6:  # Sunday
                week_start = current_date
            else:
                week_start = current_date - timedelta(days=weekday)
            if week_start in self.weekend_closers and self.weekend_closers[week_start] == worker:
                continue

            # Skip if worker has weekend Y task assignments for this week
            has_weekend_y_task = False
            for i in range(4, 7):  # Thursday (4), Friday (5), Saturday (6)
                weekend_date = week_start + timedelta(days=i)
                if weekend_date in worker.y_tasks:
                    has_weekend_y_task = True
                    break
            
            if has_weekend_y_task:
                continue

            # Skip if worker has been assigned Y tasks in previous days of this week
            has_weekday_y_task_this_week = False
            for i in range(weekday):
                previous_day = week_start + timedelta(days=i)
                if previous_day in worker.y_tasks:
                    has_weekday_y_task_this_week = True
                    break
            
            if has_weekday_y_task_this_week:
                continue

            available.append(worker)

        return available

    def _is_worker_available_for_x_task_proximity(self, worker: Worker, current_date: date) -> bool:
        """
        ENHANCED: Context-aware X task proximity filtering.
        Determines if a worker is available considering X task proximity and Rituk exceptions.
        
        Args:
            worker: Worker to check
            current_date: Date to check availability for
            
        Returns:
            True if worker is available, False otherwise
        """
        # Check for X task on current day
        if current_date in worker.x_tasks:
            x_task_type = worker.x_tasks[current_date]
            
            # Rituk exception: Workers with Rituk can still be assigned Y tasks
            if x_task_type == "Rituk":
                return True
            
            # Other X tasks: Worker is not available
            return False
        
        # Check for X task proximity penalties
        proximity_penalty = self._calculate_x_task_proximity_penalty(worker, current_date)
        if proximity_penalty > 100:  # Heavy penalty threshold
            return False
        
        # Check for recently finished X tasks
        if self._recently_finished_x_task(worker, current_date):
            return False
        
        return True

    def _calculate_x_task_proximity_penalty(self, worker: Worker, current_date: date) -> int:
        """
        ENHANCED: Calculate X task proximity penalty based on context.
        
        Args:
            worker: Worker to check
            current_date: Date to check proximity for
            
        Returns:
            Penalty score (higher = more penalty)
        """
        penalty = 0
        
        # Check for X tasks in the last week
        if worker.had_x_task_last_week(current_date):
            penalty += 100  # Heavy penalty for workers with X task last week
        
        # Check for recently finished X tasks (within 3 days)
        if worker.just_finished_x_task(current_date):
            penalty += 50  # Penalty for workers who just finished X task
        
        # Check for upcoming X tasks (context-aware)
        if worker.is_starting_x_task_soon(current_date, context_aware=True):
            penalty += 75  # Penalty for workers starting X task soon
        
        # Check for X tasks in the next week
        next_week_start = current_date + timedelta(days=7 - current_date.weekday())
        for i in range(7):
            check_date = next_week_start + timedelta(days=i)
            if check_date in worker.x_tasks:
                x_task_type = worker.x_tasks[check_date]
                if x_task_type != "Rituk":  # Rituk doesn't add penalty
                    penalty += 25  # Light penalty for upcoming X tasks
        
        return penalty

    # TODO: Implement this function to be merged with the one above, copied code.
    # ensure backend and frontend files are redone to use a single function of get_available_workers
    def _get_available_workers_for_week(self, week_start: date) -> List[Worker]:
        """
        Get workers available for Y tasks during a specific week (Sunday to Saturday).
        Excludes workers with X tasks, weekend closing assignments, or recent X task completion.
        Note: Y task conflicts are checked at the day level in _assign_y_tasks_for_week.
        """
        available = []

        for worker in self.workers:
            # Skip if worker has X task during this week (except Rituk)
            # Check each day of the week for X tasks
            has_x_task_this_week = False
            has_rituk_this_week = False

            for i in range(7):  # Sunday to Saturday
                check_date = week_start + timedelta(days=i)
                if check_date in worker.x_tasks:
                    if worker.x_tasks[check_date] == "Rituk":
                        has_rituk_this_week = True
                    else:
                        has_x_task_this_week = True

            if has_x_task_this_week and not has_rituk_this_week:
                continue

            # Skip if worker is assigned weekend closing for this week
            if week_start in self.weekend_closers and self.weekend_closers[week_start] == worker:
                continue

            # NEW: Skip if worker already has weekend Y task assignments for this week
            # Check if worker has any Y tasks during the weekend (Thursday-Saturday) of this week
            has_weekend_y_task = False
            for i in range(4, 7):  # Thursday (4), Friday (5), Saturday (6)
                weekend_date = week_start + timedelta(days=i)
                if weekend_date in worker.y_tasks:
                    has_weekend_y_task = True
                    break
            
            if has_weekend_y_task:
                continue

            # Skip if worker finished X task within last 2 days
            if self._recently_finished_x_task(worker, week_start):
                continue

            available.append(worker)

        return available

    def _recently_finished_x_task(self, worker: Worker, current_date: date) -> bool:
        """
        Check if worker finished an X task within the last 2 days before the current date.
        """
        # Check if worker had X task in the 2 days before this date
        for i in range(1, 3):  # 1 and 2 days ago
            check_date = current_date - timedelta(days=i)
            if check_date in worker.x_tasks:
                return True
        return False

    def _assign_y_tasks_for_day(self, current_date: date) -> List[Worker]:
        """
        Assign Y tasks to available workers for a specific day (Sunday to Wednesday).
        Uses scarcity-based assignment and smart scoring system.
        """
        y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        assigned_workers = []
        used_workers_today = set()  # Track used workers for this specific day

        # Get available workers for this day
        available_workers = self._get_available_workers_for_day(current_date)

        # Calculate qualification scarcity
        qualification_scarcity = self._calculate_qualification_scarcity(available_workers, y_tasks)

        # Assign tasks based on scarcity (most scarce first)
        for task in y_tasks:
            # First try to find qualified workers for this task
            qualified_workers = [w for w in available_workers
                                 if task in w.qualifications and
                                 w.id not in used_workers_today and
                                 current_date not in w.y_tasks]

            # If no qualified workers, try to find any available worker
            if not qualified_workers:
                print(
                    f"Warning: No qualified workers available for {task} on {current_date}, trying unqualified workers")
                unqualified_workers = [w for w in available_workers
                                                                              if w.id not in used_workers_today and
                                       current_date not in w.y_tasks]

                if not unqualified_workers:
                    print(f"Warning: No available workers at all for {task} on {current_date}")
                    continue

                # Use unqualified workers as fallback
                qualified_workers = unqualified_workers

            # Score workers for this task
            scored_workers = []
            for worker in qualified_workers:
                score = self._calculate_y_task_score(worker, task, current_date, qualification_scarcity)
                # Penalty for unqualified workers
                if task not in worker.qualifications:
                    score += 40  # Heavy penalty for unqualified workers
                scored_workers.append((worker, score))

            # Sort by score (lowest first = best candidates)
            scored_workers.sort(key=lambda x: x[1], reverse=False)

            # Assign the lowest scoring worker (best candidate)
            if scored_workers:
                chosen_worker = scored_workers[0][0]
                chosen_worker.assign_y_task(current_date, task)
                
                # Update score keeper
                self.score_keeper.update_worker_score(chosen_worker, "y_task", current_date)
                
                assigned_workers.append(chosen_worker)
                used_workers_today.add(chosen_worker.id)  # Mark as used for this day

        return assigned_workers

    def _assign_weekend_y_tasks_for_week_enhanced(self, week_start: date) -> List[Worker]:
        """
        ENHANCED: Assign Y tasks for the entire weekend (Thursday to Saturday).
        NEW LOGIC: Weekend closers get priority for Y tasks.
        One worker per Y task type, same worker does same task for entire weekend.
        """
        assigned_workers = []

        # TODO: Change the task names to be located in a class of their own,
        #  so that they can be easily changed/added/removed without having to go through the code.
        y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]

        # STEP 1: Get weekend closer for this week
        weekend_closer = self._get_weekend_closer_for_week(week_start)
        
        # STEP 2: Get available workers for the weekend (excluding weekend closer)
        available_workers = self._get_available_workers_for_week(week_start)
        if weekend_closer:
            available_workers = [w for w in available_workers if w != weekend_closer]

        # STEP 3: Assign Y tasks with weekend closer priority
        for task in y_tasks:
            best_candidate = None
            best_score = float('inf')

            # PRIORITY 1: Check if weekend closer is qualified and available for this task
            if weekend_closer and task in weekend_closer.qualifications:
                # Weekend closer gets automatic priority for Y tasks
                best_candidate = weekend_closer
                best_score = -100  # Very low score to ensure priority
                print(f"Weekend closer {weekend_closer.name} assigned to {task} for weekend starting {week_start}")

            # PRIORITY 2: If no weekend closer or they're not qualified, find best available worker
            if not best_candidate:
                for candidate in available_workers:
                    # Skip if already assigned to a weekend task this week
                    if any(candidate == w for w in assigned_workers):
                        continue

                    # Skip if doesn't have this qualification
                    if task not in candidate.qualifications:
                        continue

                    # Calculate score for this candidate and task
                    thursday = week_start + timedelta(days=4)  # Thursday (Sunday + 4 days)
                    score = self._calculate_y_task_score(candidate, task, thursday, 
                                                       {"Supervisor": 1.0, "C&N Driver": 1.0, "C&N Escort": 1.0, 
                                                        "Southern Driver": 1.0, "Southern Escort": 1.0})

                    if score < best_score:  # Lower score = better
                        best_score = score
                        best_candidate = candidate

            if best_candidate:
                # Assign this worker to the task for Thursday, Friday, Saturday
                thursday = week_start + timedelta(days=4)  # Thursday (Sunday + 4 days)
                friday = week_start + timedelta(days=5)  # Friday (Sunday + 5 days)
                saturday = week_start + timedelta(days=6)  # Saturday (Sunday + 6 days)

                # Only assign if the day is within our date range
                if thursday >= self.start_date and thursday <= self.end_date:
                    best_candidate.assign_y_task(thursday, task)
                    best_candidate.update_score_after_assignment("y_task", thursday)
                if friday >= self.start_date and friday <= self.end_date:
                    best_candidate.assign_y_task(friday, task)
                    best_candidate.update_score_after_assignment("y_task", friday)
                if saturday >= self.start_date and saturday <= self.end_date:
                    best_candidate.assign_y_task(saturday, task)
                    best_candidate.update_score_after_assignment("y_task", saturday)

                assigned_workers.append(best_candidate)
                
                # Remove this worker from available workers to prevent double assignment
                available_workers = [w for w in available_workers if w != best_candidate]
            else:
                print(f"Warning: No suitable candidate found for {task} on week starting {week_start}")

        return assigned_workers

    def _get_weekend_closer_for_week(self, week_start: date) -> Worker:
        """
        Get the weekend closer for a specific week.
        Returns the assigned weekend closer or None if none assigned.
        """
        return self.weekend_closers.get(week_start)



    def _assign_weekend_closer_for_day(self, current_date: date) -> List[Worker]:
        """
        Assign weekend closer for a specific day (Thursday to Saturday).
        """
        assigned_workers = []

        # Get weekend closing candidates for this week
        # Calculate week start (Sunday) for this date
        weekday = current_date.weekday()
        week_start = current_date - timedelta(days=weekday + 1)  # Go back to Sunday

        # Only assign if we haven't already assigned a closer for this week
        if week_start not in self.weekend_closers:
            candidates = self.get_weekend_closing_candidates(self.workers, week_start)

            if candidates:
                chosen_worker = candidates[0]
                # Assign closing for Thursday, Friday, Saturday, Sunday
                thursday = week_start + timedelta(days=4)  # Thursday (Sunday + 4 days)
                friday = week_start + timedelta(days=5)  # Friday (Sunday + 5 days)
                saturday = week_start + timedelta(days=6)  # Saturday (Sunday + 6 days)
                sunday = week_start + timedelta(days=7)  # Sunday of next week

                chosen_worker.assign_closing(thursday)
                chosen_worker.assign_closing(friday)
                chosen_worker.assign_closing(saturday)
                chosen_worker.assign_closing(sunday)
                
                # Update score keeper for closing assignments
                self.score_keeper.update_worker_score(chosen_worker, "closing", thursday)
                self.score_keeper.update_worker_score(chosen_worker, "closing", friday)
                self.score_keeper.update_worker_score(chosen_worker, "closing", saturday)
                self.score_keeper.update_worker_score(chosen_worker, "closing", sunday)
                
                assigned_workers.append(chosen_worker)

                # Update weekend closers tracking
                self.weekend_closers[week_start] = chosen_worker
            else:
                print(f"Warning: No weekend closing candidates available for week starting {week_start}")
        print(f"DEBUG: Printing assigned weekend closers for day: \n {assigned_workers}")
        return assigned_workers

    def _calculate_weekend_y_task_score(self, worker: Worker, task: str, week_start: date) -> int:
        """
        Calculate score for a worker for a weekend Y task.
        NEW SIMPLIFIED SCORING: Higher scores = better workers = should get FEWER tasks
        """
        current_week = week_start

        # Skip if worker has X task in current week or next week
        if worker.has_x_task(current_week) or worker.has_x_task(current_week + timedelta(days=7)):
            return -1

        # Skip workers with closing_interval of 0 (they don't participate in closing)
        if worker.closing_interval <= 0:
            return -1

        # Calculate overdue status
        last_closing_week = worker.get_last_closing_week()
        if last_closing_week is None:
            overdue = float('inf')  # Never closed, so always overdue
        else:
            delta = (current_week - last_closing_week).days // 7
            overdue = delta - worker.closing_interval

        # Skip if not due yet (but allow workers who never closed)
        if last_closing_week is not None and overdue < 0 and last_closing_week <= current_week:
            return -1

        # NEW SIMPLIFIED SCORING SYSTEM
        score = 0
        
        # Base worker score (higher = better worker = should get fewer tasks)
        base_score = int(worker.score) if worker.score is not None else 0
        score += base_score
        
        # ENHANCED: Qualification-based compensation
        # Workers with more qualifications should get fewer tasks (higher scores)
        qualification_bonus = len(worker.qualifications) * 8  # 8 points per qualification
        score += qualification_bonus
        
        # ENHANCED: Task-specific qualification bonus
        # If worker has the specific qualification for this task, give them priority (lower score)
        if task in worker.qualifications:
            score -= 15  # Priority for qualified workers
        
        # Workload penalty (overworked workers get higher scores = fewer tasks)
        workload_score = worker.get_workload_score()
        score += workload_score
        
        # Overdue bonus (workers who are overdue get priority = lower scores)
        if overdue > 0:
            score -= overdue * 10  # Overdue workers get priority
        
        # X task penalties (workers with upcoming X tasks should not close)
        if worker.has_x_task(current_week + timedelta(days=14)):  # 2 weeks
            score += 20  # Strong penalty
        elif worker.has_x_task(current_week + timedelta(days=21)):  # 3 weeks
            score += 10  # Medium penalty
        
        # Recent X task penalty
        if worker.had_x_task(current_week - timedelta(days=7)):
            score += 15  # Penalty for recent X task
        
        # Recent Y task penalty (last 14 days)
        recent_y_tasks = sum(1 for task_date in worker.y_tasks
                             if (week_start - task_date).days <= 14)
        score += recent_y_tasks * 10  # Penalty for recent Y tasks

        return score

    def _calculate_qualification_scarcity(self, available_workers: List[Worker], y_tasks: List[str]) -> Dict[
        str, float]:
        """
        Calculate scarcity score for each qualification.
        Lower score = more scarce qualification.
        """
        scarcity = {}
        total_workers = len(available_workers)

        for task in y_tasks:
            qualified_count = sum(1 for w in available_workers if task in w.qualifications)
            if qualified_count == 0:
                scarcity[task] = float('inf')  # No qualified workers
            else:
                scarcity[task] = total_workers / qualified_count  # Higher = more scarce

        return scarcity

    def _choose_best_day_for_assignment(self, week_start: date, worker: Worker) -> date:
        """
        Choose the best day (Monday to Thursday) for assigning a Y task to a worker.
        Prefers days when the worker has fewer conflicts.
        """
        best_day = week_start  # Default to Monday
        best_score = float('inf')

        for i in range(4):  # Monday to Thursday
            day = week_start + timedelta(days=i)

            # Skip if worker already has assignment on this day
            if day in worker.y_tasks:
                continue

            # Calculate conflict score (lower is better)
            score = 0

            # Penalty for having X task nearby
            for j in range(-1, 2):  # Day before, same day, day after
                check_day = day + timedelta(days=j)
                # TODO: ENSURE NOT 'RITUK'!
                if check_day in worker.x_tasks:
                    score += 10

            # Prefer earlier in the week
            score += i * 2

            if score < best_score:
                best_score = score
                best_day = day

        return best_day

    def _calculate_y_task_score(self, worker: Worker, task: str, current_date: date,
                                qualification_scarcity: Dict[str, float]) -> int:
        """
        ENHANCED: Calculate internal score for a worker for a specific Y task.
        REVISED: LOWER score = HIGHER priority (better candidate)
        """
        # ALGORITHM: Start with base score of 0 (lower scores = higher priority)
        score = 0
        
        # PERSISTENT SCORE: Add worker's persistent score (higher score = more overworked = lower priority)
        # Workers who have done more work get higher scores (penalty for future tasks)
        score += int(worker.score) if worker.score is not None else 0
        
        # QUALIFICATION PENALTY: Workers with more qualifications should get fewer tasks (higher scores)
        # This prevents overloading workers with many skills
        # REDUCED: Qualification penalty should not overwhelm fairness
        qualification_penalty = len(worker.qualifications) * 2  # Reduced from 8 to 2
        score += qualification_penalty
        
        # TASK-SPECIFIC BONUS: Qualified workers get priority for their qualified tasks
        if task in worker.qualifications:
            score -= 15  # Priority for qualified workers
        
        # ENHANCED: Workload penalty (overworked workers get higher scores = lower priority)
        workload_score = worker.get_workload_score()
        score += workload_score
        
        # ENHANCED: Fairness adjustment from score keeper
        fairness_adjustment = self.score_keeper.get_fairness_adjustment(worker)
        score += fairness_adjustment
        
        # ENHANCED: Qualification balancing adjustment
        qualification_balance = self.score_keeper.get_qualification_balancing_adjustment(worker, task)
        score += qualification_balance
        
        # Qualification scarcity (workers with scarce qualifications get priority)
        scarcity_score = qualification_scarcity.get(task, 1.0)
        if scarcity_score > 2.0:  # If qualification is scarce
            score -= int(scarcity_score * 5)  # Priority for scarce qualifications
        
        # Recent Y task penalties (small penalties to prevent overloading in short periods)
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        y_tasks_this_week = sum(1 for task_date in worker.y_tasks
                                if week_start <= task_date <= week_end)
        score += y_tasks_this_week * 2  # Small penalty for Y tasks this week
        
        # Recent Y task penalty (last 14 days)
        recent_y_tasks = sum(1 for task_date in worker.y_tasks
                             if (current_date - task_date).days <= 14)
        score += recent_y_tasks * 1  # Small penalty for recent Y tasks
        
        # ENHANCED: X task proximity penalties with context awareness
        if worker.had_x_task_last_week(current_date):
            score += 100  # Heavy penalty for workers with X task last week
        
        if worker.just_finished_x_task(current_date):
            score += 50  # Penalty for workers who just finished X task
        
        # Context-aware upcoming X task penalties
        if worker.is_starting_x_task_soon(current_date, context_aware=True):
            score += 75  # Penalty for workers starting X task soon
        
        # Rituk workers get priority (lower scores)
        if worker.has_specific_x_task(current_date, "Rituk"):
            score -= 30  # Priority for Rituk workers
        
        # Additional X task proximity penalties
        proximity_penalty = self._calculate_x_task_proximity_penalty(worker, current_date)
        score += proximity_penalty
        
        return score

    def assign_weekend_closers(self, start_date: date, end_date: date) -> Dict[date, Worker]:
        """
        Assign weekend closers for the specified date range.
        Uses the new scoring system from get_weekend_closing_candidates.
        Handles cases where there are insufficient workers.
        
        Args:
            start_date: Start date for weekend closing assignments
            end_date: End date for weekend closing assignments
            
        Returns:
            Dictionary mapping weekend start dates to assigned workers
        """
        # Clear existing weekend closing assignments for the date range
        self.weekend_closers = {weekend: worker for weekend, worker in self.weekend_closers.items()
                                if weekend < start_date or weekend > end_date}

        # Clear closing history for workers in the date range
        for worker in self.workers:
            worker.closing_history = [date for date in worker.closing_history
                                      if date < start_date or date > end_date]

        current_date = start_date

        while current_date <= end_date:
            # Find Friday (weekend start)
            if current_date.weekday() == 4:  # Friday
                weekend_start = current_date

                # Get candidates for this weekend
                candidates = self.get_weekend_closing_candidates(self.workers, weekend_start - timedelta(
                    days=4))  # Monday of this week

                # Assign the highest scoring candidate
                if candidates:
                    chosen_worker = candidates[0]
                    self.weekend_closers[weekend_start] = chosen_worker

                    # Assign closing for Thursday, Friday, Saturday, Sunday
                    thursday = weekend_start - timedelta(days=1)  # Thursday
                    friday = weekend_start  # Friday
                    saturday = weekend_start + timedelta(days=1)  # Saturday
                    sunday = weekend_start + timedelta(days=2)  # Sunday

                    chosen_worker.assign_closing(thursday)
                    chosen_worker.assign_closing(friday)
                    chosen_worker.assign_closing(saturday)
                    chosen_worker.assign_closing(sunday)
                    
                    # Update score keeper for closing assignments
                    self.score_keeper.update_worker_score(chosen_worker, "closing", thursday)
                    self.score_keeper.update_worker_score(chosen_worker, "closing", friday)
                    self.score_keeper.update_worker_score(chosen_worker, "closing", saturday)
                    self.score_keeper.update_worker_score(chosen_worker, "closing", sunday)
                else:
                    # Handle case where no candidates are available
                    print(f"Warning: No weekend closing candidates available for {weekend_start}")
                    # Could implement fallback logic here (e.g., force assign someone)

                current_date += timedelta(days=7)  # Move to next Friday
            else:
                current_date += timedelta(days=1)

        return self.weekend_closers

    def get_schedule(self) -> Dict[date, Dict[str, str]]:
        """
        Get the complete schedule including both Y tasks and weekend closings.
        """
        schedule = {}

        # Add Y task assignments
        for worker in self.workers:
            for task_date, task_name in worker.y_tasks.items():
                if task_date not in schedule:
                    schedule[task_date] = {}
                schedule[task_date][task_name] = worker.name

        # Add weekend Y task assignments (these are already in worker.y_tasks)
        # The weekend Y tasks are assigned as regular Y tasks, so they're already included above

        return schedule

    def get_weekend_candidates_with_scores(self, workers: List[Worker], current_week: date) -> List[Tuple[Worker, int]]:
        """
        Get weekend closing candidates with their scores for debugging purposes.
        
        Args:
            workers: List of workers to evaluate
            current_week: Monday of the week in question
            
        Returns:
            List of (worker, score) tuples sorted by score (highest first)
        """
        candidates = []

        for worker in workers:
            # Skip if worker has X task in current week or next week
            if worker.has_x_task(current_week) or worker.has_x_task(current_week + timedelta(days=7)):
                continue

            # Skip workers with closing_interval of 0 (they don't participate in closing)
            if worker.closing_interval <= 0:
                continue

            # Calculate delta (weeks since last closing)
            last_closing_week = worker.get_last_closing_week()
            if last_closing_week is None:
                delta = float('inf')  # Never closed before
                overdue = float('inf')  # Never closed, so always overdue
            else:
                delta = (current_week - last_closing_week).days // 7
                overdue = delta - worker.closing_interval

            score = int(worker.score) if worker.score is not None else 0

            # Skip if overdue < 0 (not due yet) - but allow workers to be reassigned even if they have future closing dates
            # Only exclude if they are truly not due yet (last closing in past and not overdue)
            if last_closing_week is not None and overdue < 0 and last_closing_week <= current_week:
                continue

            # Add base score based on overdue status
            if last_closing_week is None:
                score += 50  # Bonus for never closed before
            elif overdue == 0:
                score += 30
            else:
                score += 20 + min(overdue, 20)  # Cap overdue bonus at 20

            # Penalty if worker has X task in 3 weeks and closing interval >= 5
            if worker.has_x_task(current_week + timedelta(days=14)) and worker.closing_interval >= 5:
                score -= 5

            # Penalty if worker had X task in previous week
            if worker.had_x_task(current_week - timedelta(days=7)):
                score -= 15

            # Penalty if worker has closing scheduled for next week
            if worker.has_closing_scheduled(current_week + timedelta(days=7)):
                score -= 20

            # Normalize by total closings vs weeks served
            normalized = worker.get_total_closings() / worker.get_total_weeks_served()
            score -= int(normalized * 10)

            candidates.append((worker, score))

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates

    def debug_worker_status(self, worker: Worker, current_week: date) -> Dict:
        """
        Get detailed debug information about a worker's status for weekend closing.
        
        Args:
            worker: Worker to analyze
            current_week: Monday of the week in question
            
        Returns:
            Dictionary with debug information
        """
        debug_info = {
            'worker_id': worker.id,
            'worker_name': worker.name,
            'base_score': worker.score,
            'closing_interval': worker.closing_interval,
            'total_closings': worker.get_total_closings(),
            'total_weeks_served': worker.get_total_weeks_served(),
            'has_x_task_current_week': worker.has_x_task(current_week),
            'has_x_task_next_week': worker.has_x_task(current_week + timedelta(days=7)),
            'has_x_task_3_weeks': worker.has_x_task(current_week + timedelta(days=14)),
            'had_x_task_previous_week': worker.had_x_task(current_week - timedelta(days=7)),
            'has_closing_next_week': worker.has_closing_scheduled(current_week + timedelta(days=7)),
        }

        # Calculate delta and overdue
        last_closing_week = worker.get_last_closing_week()
        if last_closing_week is None:
            debug_info['delta'] = float('inf')
            debug_info['overdue'] = float('inf')
        else:
            delta = (current_week - last_closing_week).days // 7
            overdue = delta - worker.closing_interval
            debug_info['delta'] = delta
            debug_info['overdue'] = overdue

        return debug_info

    def get_insufficient_workers_report(self, start_date: date, end_date: date) -> Dict:
        """
        Generate a report of insufficient workers for the specified date range.
        
        Args:
            start_date: Start date for the report
            end_date: End date for the report
            
        Returns:
            Dictionary containing reports of insufficient workers
        """
        report = {
            'weekend_closing_issues': [],
            'y_task_issues': []
        }

        current_date = start_date
        while current_date <= end_date:
            # Check weekend closing issues
            if current_date.weekday() == 4:  # Friday
                weekend_start = current_date
                candidates = self.get_weekend_closing_candidates(self.workers, weekend_start - timedelta(days=4))
                if len(candidates) < 5:  # Need at least 5 workers for 5 Y task types
                    report['weekend_closing_issues'].append({
                        'week': weekend_start.strftime('%Y-%m-%d'),
                        'available_candidates': len(candidates),
                        'required': 5
                    })

            # Check Y task issues for weekdays
            if current_date.weekday() in [6, 0, 1, 2]:  # Sunday to Wednesday
                available_workers = self._get_available_workers_for_day(current_date)
                qualified_counts = {}
                for task in ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]:
                    qualified_count = sum(1 for w in available_workers if task in w.qualifications)
                    qualified_counts[task] = qualified_count

                # Check if any task has insufficient qualified workers
                for task, count in qualified_counts.items():
                    if count == 0:
                        report['y_task_issues'].append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'task': task,
                            'qualified_workers': count,
                            'required': 1
                        })

            current_date += timedelta(days=1)

        return report

    def save_updated_worker_data(self, json_path: str, original_data: List[dict] = None):
        """
        Save the updated worker data with closing history and assignments to JSON.
        
        DEVELOPMENT MODE: This saves all assignments including future ones to closing_history.
        This allows subsequent schedule generations to consider previous assignments.
        
        PRODUCTION MODE: This should be modified to only save past assignments to closing_history.
        
        Args:
            json_path: Path to save the JSON file
            original_data: Original JSON data to preserve other fields
        
        TODO: BEFORE PRODUCTION - Modify this function to only save past assignments to closing_history!
        """
        from worker import save_workers_to_json

        save_workers_to_json(self.workers, json_path, original_data)

        print("⚠️  DEVELOPMENT MODE: Future closing assignments saved to closing_history")
        print("⚠️  TODO: BEFORE PRODUCTION - Modify to only save past assignments!")
        print("⚠️  This allows subsequent schedule generations to consider previous assignments")
