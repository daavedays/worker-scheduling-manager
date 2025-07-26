from datetime import date, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
from .worker import Worker

class SchedulerEngine:
    def __init__(self, workers: List[Worker], start_date: date, end_date: date):
        self.workers = workers
        self.start_date = start_date
        self.end_date = end_date
        self.schedule: Dict[date, Dict[str, str]] = {}  # date -> task name -> worker id
        self.weekend_closers: Dict[date, Worker] = {}  # weekend_start_date -> assigned worker

    def get_weekend_closing_candidates(self, workers: List[Worker], current_week: date) -> List[Worker]:
        """
        Get list of workers eligible for weekend closing assignment for the specified week.
        Returns workers sorted by score (highest first) for Thursday, Friday, and Saturday assignments.
        
        Args:
            workers: List of workers to evaluate
            current_week: Monday of the week in question
            
        Returns:
            List of workers sorted by closing score (highest first)
        """
        candidates = []
        rituk_candidates = []  # Special priority for workers with "Rituk" X task
        
        for worker in workers:
            # Check if worker has "Rituk" X task - these get top priority
            has_rituk = worker.has_specific_x_task(current_week, "Rituk") or worker.has_specific_x_task(current_week + timedelta(days=7), "Rituk")
            
            # Skip if worker has X task in current week or next week (except Rituk)
            if (worker.has_x_task(current_week) or worker.has_x_task(current_week + timedelta(days=7))) and not has_rituk:
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
            
            # Skip if overdue < 0 (not due yet) - but allow workers who never closed
            # Allow workers to be reassigned even if they have future closing dates
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
            
            # Special bonus for workers with "Rituk" X task
            if has_rituk:
                score += 100  # Very high priority
            
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
            
            if has_rituk:
                rituk_candidates.append((worker, score))
            else:
                candidates.append((worker, score))
        
        # Sort by score (highest first)
        rituk_candidates.sort(key=lambda x: x[1], reverse=True)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return Rituk candidates first, then regular candidates
        return [worker for worker, score in rituk_candidates] + [worker for worker, score in candidates]

    def assign_y_tasks(self, start_date: date, end_date: date) -> List[Worker]:
        """
        Assign Y tasks to workers for the specified date range.
        Assigns Y tasks for Sunday-Wednesday and weekend Y tasks for Thursday-Saturday.
        
        Args:
            start_date: Start date for Y task assignments
            end_date: End date for Y task assignments
            
        Returns:
            List of workers assigned to Y tasks
        """
        # Clear existing Y task assignments for the date range
        for worker in self.workers:
            worker.y_tasks = {date: task for date, task in worker.y_tasks.items() 
                            if date < start_date or date > end_date}
        
        assigned_workers = []
        current_date = start_date
        
        # First, assign weekend Y tasks for each week
        while current_date <= end_date:
            weekday = current_date.weekday()
            
            if weekday == 0:  # Monday - assign weekend Y tasks for this week
                week_start = current_date
                weekend_assignments = self._assign_weekend_y_tasks_for_week(week_start)
                assigned_workers.extend(weekend_assignments)
            
            current_date += timedelta(days=1)
        
        # Then, assign daily Y tasks for Sunday-Wednesday
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday()
            
            if weekday in [6, 0, 1, 2]:  # Sunday (6), Monday (0), Tuesday (1), Wednesday (2) - Y tasks
                day_assignments = self._assign_y_tasks_for_day(current_date)
                assigned_workers.extend(day_assignments)
            
            current_date += timedelta(days=1)
        
        return assigned_workers

    def _get_available_workers_for_day(self, current_date: date) -> List[Worker]:
        """
        Get workers available for Y tasks on a specific day.
        Excludes workers with X tasks, Y tasks on this day, weekend closing assignments, or recent X task completion.
        Note: Workers can be assigned multiple Y tasks in the same week (but not on the same day).
        """
        available = []
        
        for worker in self.workers:
            # Skip if worker has X task on this day (except Rituk)
            has_rituk = worker.has_specific_x_task(current_date, "Rituk")
            if current_date in worker.x_tasks and not has_rituk:
                continue
            
            # Skip if worker already has Y task on this day
            if current_date in worker.y_tasks:
                continue
            
            # Skip if worker is assigned weekend closing for this week
            week_start = current_date - timedelta(days=current_date.weekday())
            if week_start in self.weekend_closers and self.weekend_closers[week_start] == worker:
                continue
            
            # Skip if worker finished X task within last 2 days
            if self._recently_finished_x_task(worker, current_date):
                continue
            
            available.append(worker)
        
        return available

    def _get_available_workers_for_week(self, week_start: date) -> List[Worker]:
        """
        Get workers available for Y tasks during a specific week (Monday to Thursday).
        Excludes workers with X tasks, weekend closing assignments, or recent X task completion.
        Note: Y task conflicts are checked at the day level in _assign_y_tasks_for_week.
        """
        available = []
        
        for worker in self.workers:
            # Skip if worker has X task during this week (except Rituk)
            has_rituk = worker.has_specific_x_task(week_start, "Rituk")
            if worker.has_x_task(week_start) and not has_rituk:
                continue
            
            # Skip if worker is assigned weekend closing for this week
            if week_start in self.weekend_closers and self.weekend_closers[week_start] == worker:
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
            
            if not qualified_workers:
                # If no qualified workers, try to find any available worker
                print(f"Warning: No qualified workers available for {task} on {current_date}, trying unqualified workers")
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
                    score -= 50  # Heavy penalty for unqualified workers
                scored_workers.append((worker, score))
            
            # Sort by score (highest first)
            scored_workers.sort(key=lambda x: x[1], reverse=True)
            
            # Assign the highest scoring worker
            if scored_workers:
                chosen_worker = scored_workers[0][0]
                chosen_worker.assign_y_task(current_date, task)
                assigned_workers.append(chosen_worker)
                used_workers_today.add(chosen_worker.id)  # Mark as used for this day
        
        return assigned_workers

    def _assign_weekend_y_tasks_for_week(self, week_start: date) -> List[Worker]:
        """
        Assign Y tasks for the entire weekend (Thursday to Saturday).
        One worker per Y task type, same worker does same task for entire weekend.
        """
        assigned_workers = []
        
        # Only assign if we haven't already assigned weekend Y tasks for this week
        if week_start not in self.weekend_closers:
            y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
            
            # Get weekend closing candidates for this week
            candidates = self.get_weekend_closing_candidates(self.workers, week_start)
            
            if candidates:
                # Assign one worker per Y task type for the entire weekend
                for task in y_tasks:
                    # Find the best candidate for this specific task
                    best_candidate = None
                    best_score = -1
                    
                    for candidate in candidates:
                        # Skip if candidate already assigned to a weekend task this week
                        if any(candidate == w for w in assigned_workers):
                            continue
                        
                        # Skip if candidate doesn't have this qualification
                        if task not in candidate.qualifications:
                            continue
                        
                        # Calculate score for this candidate and task
                        score = self._calculate_weekend_y_task_score(candidate, task, week_start)
                        
                        if score > best_score:
                            best_score = score
                            best_candidate = candidate
                    
                    if best_candidate:
                        # Assign this worker to the task for Thursday, Friday, Saturday
                        thursday = week_start + timedelta(days=3)  # Thursday
                        friday = week_start + timedelta(days=4)    # Friday
                        saturday = week_start + timedelta(days=5)  # Saturday
                        
                        best_candidate.assign_y_task(thursday, task)
                        best_candidate.assign_y_task(friday, task)
                        best_candidate.assign_y_task(saturday, task)
                        
                        assigned_workers.append(best_candidate)
                        
                        # Update weekend closers tracking (for compatibility)
                        self.weekend_closers[week_start] = best_candidate
                    else:
                        print(f"Warning: No suitable candidate found for {task} on week starting {week_start}")
            else:
                print(f"Warning: No weekend closing candidates available for week starting {week_start}")
        
        return assigned_workers

    def _assign_weekend_closer_for_day(self, current_date: date) -> List[Worker]:
        """
        Assign weekend closer for a specific day (Thursday to Saturday).
        """
        assigned_workers = []
        
        # Get weekend closing candidates for this week
        week_start = current_date - timedelta(days=current_date.weekday())  # Monday of this week
        
        # Only assign if we haven't already assigned a closer for this week
        if week_start not in self.weekend_closers:
            candidates = self.get_weekend_closing_candidates(self.workers, week_start)
            
            if candidates:
                chosen_worker = candidates[0]
                # Assign closing for Thursday, Friday, Saturday, Sunday
                thursday = week_start + timedelta(days=3)  # Thursday
                friday = week_start + timedelta(days=4)    # Friday
                saturday = week_start + timedelta(days=5)  # Saturday
                sunday = week_start + timedelta(days=6)    # Sunday
                
                chosen_worker.assign_closing(thursday)
                chosen_worker.assign_closing(friday)
                chosen_worker.assign_closing(saturday)
                chosen_worker.assign_closing(sunday)
                assigned_workers.append(chosen_worker)
                
                # Update weekend closers tracking
                self.weekend_closers[week_start] = chosen_worker
            else:
                print(f"Warning: No weekend closing candidates available for week starting {week_start}")
        
        return assigned_workers

    def _calculate_weekend_y_task_score(self, worker: Worker, task: str, week_start: date) -> int:
        """
        Calculate score for a worker for a specific Y task during the weekend.
        Uses the same logic as weekend closing candidates but with task-specific considerations.
        """
        # Get base score from weekend closing candidate logic
        current_week = week_start
        
        # Skip if worker has X task in current week or next week
        if worker.has_x_task(current_week) or worker.has_x_task(current_week + timedelta(days=7)):
            return -1
        
        # Skip workers with closing_interval of 0 (they don't participate in closing)
        if worker.closing_interval <= 0:
            return -1
        
        # Calculate delta (weeks since last closing)
        last_closing_week = worker.get_last_closing_week()
        if last_closing_week is None:
            delta = float('inf')  # Never closed before
            overdue = float('inf')  # Never closed, so always overdue
        else:
            delta = (current_week - last_closing_week).days // 7
            overdue = delta - worker.closing_interval
        
        score = int(worker.score) if worker.score is not None else 0
        
        # Skip if overdue < 0 (not due yet) - but allow workers who never closed
        # Allow workers to be reassigned even if they have future closing dates
        # Only exclude if they are truly not due yet (last closing in past and not overdue)
        if last_closing_week is not None and overdue < 0 and last_closing_week <= current_week:
            return -1
        
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
        
        # Task-specific bonuses
        # Bonus for workers with fewer Y task assignments this month
        current_month = week_start.replace(day=1)
        y_tasks_this_month = sum(1 for task_date in worker.y_tasks 
                                if task_date >= current_month)
        score -= y_tasks_this_month * 15  # Stronger preference for workers with fewer recent Y tasks
        
        # Bonus for workers with higher seniority
        if worker.seniority and worker.seniority != 'None':
            try:
                seniority_value = int(worker.seniority) if isinstance(worker.seniority, (int, str)) else 0
                score += seniority_value * 3
            except (ValueError, TypeError):
                pass  # Skip if seniority can't be converted to int
        
        # Penalty for long timers (prefer newer workers for Y tasks)
        if worker.long_timer:
            score -= 15
        
        return score

    def _calculate_qualification_scarcity(self, available_workers: List[Worker], y_tasks: List[str]) -> Dict[str, float]:
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
                if check_day in worker.x_tasks:
                    score += 10
            
            # Prefer earlier in the week
            score += i * 2
            
            if score < best_score:
                best_score = score
                best_day = day
        
        return best_day

    def _calculate_y_task_score(self, worker: Worker, task: str, current_date: date, qualification_scarcity: Dict[str, float]) -> int:
        """
        Calculate score for a worker for a specific Y task during a specific week.
        Uses scarcity-based scoring and smart constraints.
        """
        # Ensure score is an integer
        base_score = int(worker.score) if worker.score is not None else 0
        score = base_score
        
        # Scarcity bonus - workers with scarce qualifications get higher priority
        scarcity_score = qualification_scarcity.get(task, 1.0)
        if scarcity_score > 2.0:  # If qualification is scarce
            score += int(scarcity_score * 10)  # Bonus for scarce qualifications
        
        # Bonus for workers with fewer Y task assignments this month
        current_month = current_date.replace(day=1)
        y_tasks_this_month = sum(1 for task_date in worker.y_tasks 
                                if task_date >= current_month)
        score -= y_tasks_this_month * 15  # Stronger preference for workers with fewer recent Y tasks
        
        # Bonus for workers with fewer Y task assignments this week
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        y_tasks_this_week = sum(1 for task_date in worker.y_tasks 
                               if week_start <= task_date <= week_end)
        score -= y_tasks_this_week * 25  # Strong preference for workers with fewer Y tasks this week
        
        # Bonus for workers with higher seniority
        if worker.seniority and worker.seniority != 'None':
            try:
                seniority_value = int(worker.seniority) if isinstance(worker.seniority, (int, str)) else 0
                score += seniority_value * 3
            except (ValueError, TypeError):
                pass  # Skip if seniority can't be converted to int
        
        # Penalty for long timers (prefer newer workers for Y tasks)
        if worker.long_timer:
            score -= 15
        
        # Bonus for workers who haven't had Y tasks recently
        recent_y_tasks = sum(1 for task_date in worker.y_tasks 
                           if (current_date - task_date).days <= 14)
        score -= recent_y_tasks * 20
        
        # Penalty for workers with many qualifications (spread the load)
        qualification_count = len(worker.qualifications)
        if qualification_count > 3:
            score -= (qualification_count - 3) * 5
        
        # Bonus for workers with "Rituk" X task (they should get Y tasks too)
        if worker.has_specific_x_task(current_date, "Rituk"):
            score += 30
        
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
                candidates = self.get_weekend_closing_candidates(self.workers, weekend_start - timedelta(days=4))  # Monday of this week
                
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
            
            # Skip if overdue < 0 (not due yet) - but allow workers who never closed
            # Allow workers to be reassigned even if they have future closing dates
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
        Generate a report of insufficient workers for Y tasks in the given date range.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with detailed report of insufficient workers
        """
        report = {
            'period': f"{start_date} to {end_date}",
            'total_workers': len(self.workers),
            'workers_with_closing_interval': sum(1 for w in self.workers if w.closing_interval > 0),
            'workers_with_qualifications': sum(1 for w in self.workers if w.qualifications),
            'weekend_closing_issues': [],
            'y_task_issues': [],
            'recommendations': []
        }
        
        # Check weekend closing issues
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() == 4:  # Friday
                weekend_start = current_date
                candidates = self.get_weekend_closing_candidates(self.workers, weekend_start - timedelta(days=4))
                
                if not candidates:
                    report['weekend_closing_issues'].append({
                        'weekend': weekend_start,
                        'issue': 'No available candidates for weekend closing'
                    })
                elif len(candidates) < 2:
                    report['weekend_closing_issues'].append({
                        'weekend': weekend_start,
                        'issue': f'Only {len(candidates)} candidate(s) available for weekend closing'
                    })
            
            current_date += timedelta(days=1)
        
        # Check Y task issues - check each day individually
        current_date = start_date
        while current_date <= end_date:
            # Only check weekdays (Monday to Thursday)
            if current_date.weekday() < 4:  # Monday = 0, Tuesday = 1, Wednesday = 2, Thursday = 3
                # Get available workers for this specific day
                available_workers = []
                for worker in self.workers:
                    # Skip if worker has X task on this day (except Rituk)
                    has_rituk = worker.has_specific_x_task(current_date, "Rituk")
                    if current_date in worker.x_tasks and not has_rituk:
                        continue
                    
                    # Skip if worker already has Y task on this day
                    if current_date in worker.y_tasks:
                        continue
                    
                    # Skip if worker is assigned weekend closing for this week
                    week_start = current_date - timedelta(days=current_date.weekday())
                    if week_start in self.weekend_closers and self.weekend_closers[week_start] == worker:
                        continue
                    
                    # Skip if worker finished X task within last 2 days
                    if self._recently_finished_x_task(worker, current_date):
                        continue
                    
                    available_workers.append(worker)
                
                y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
                
                for task in y_tasks:
                    qualified_count = sum(1 for w in available_workers if task in w.qualifications)
                    if qualified_count == 0:
                        report['y_task_issues'].append({
                            'date': current_date,
                            'task': task,
                            'issue': 'No qualified workers available'
                        })
                    elif qualified_count < 2:
                        report['y_task_issues'].append({
                            'date': current_date,
                            'task': task,
                            'issue': f'Only {qualified_count} qualified worker(s) available'
                        })
            
            current_date += timedelta(days=1)
        
        # Generate recommendations
        if report['weekend_closing_issues']:
            report['recommendations'].append("Consider reducing X task assignments during weekends")
        
        if report['y_task_issues']:
            report['recommendations'].append("Consider training more workers for scarce qualifications")
            report['recommendations'].append("Review X task assignments to free up more workers for Y tasks")
        
        return report 