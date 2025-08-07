from datetime import datetime, timedelta, date
from typing import List, Tuple
import json
import os
import csv

# Global score increment values (floats for easy testing)
Y_TASK_SCORE_INCREMENT = 1.0  # Points added per Y task assignment
OFF_INTERVAL_CLOSING_BONUS = 5.0  # Bonus for closing when not your turn
MANUAL_CLOSING_BONUS = 3.0  # Bonus for manual off-interval closing


class Worker:
    def __init__(self, id, name, start_date, qualifications, closing_interval, officer=False, seniority=None,
                 score=None, long_timer=False):
        self.id = id
        self.name = name
        self.start_date = start_date  # datetime.date
        self.qualifications = qualifications  # List[str]
        self.closing_interval = closing_interval  # int
        self.x_tasks = {}  # This will be populated from CSV files
        self.y_tasks = {}  # date -> task name
        self.closing_history = []  # list of dates when closed weekend
        self.officer = officer  # if rank == mandatory, officer = False.
        self.seniority = seniority  # Add this line
        self.score = float(score or 0.0)  # how many points the worker has, default to 0.0
        self.long_timer = long_timer  # Add this line
        
        # NEW: Tally tracking for fairness
        self.x_task_count = 0  # Total X tasks assigned
        self.y_task_count = 0  # Total Y tasks assigned
        self.closing_delta = 0  # How far off from ideal closing interval

    def is_resting_after_x(self, date):
        prev = date - timedelta(days=1)
        return prev in self.x_tasks or date in self.x_tasks

    def will_start_x_soon(self, date):
        for i in range(1, 3):
            if (date + timedelta(days=i)) in self.x_tasks:
                return True
        return False

    def is_due_for_closing(self, date):
        """
        Returns True if the soldier is due for closing,
         False otherwise. based on their closing interval and closing history
        """
        if not self.closing_history:
            return True
        last = self.closing_history[-1]
        delta = (date - last).days // 7
        return (delta >= self.closing_interval, delta)

    def assign_y_task(self, date, task_name):
        self.y_tasks[date] = task_name
        self.y_task_count += 1  # Update tally
        # Update score using global variable
        self.score += Y_TASK_SCORE_INCREMENT

    def assign_closing(self, date, development_mode=True):
        """
        Assign closing to a worker for a specific date.
        
        DEVELOPMENT MODE: Future closing assignments are immediately added to closing_history.
        This allows the engine to consider future assignments when generating subsequent schedules.
        
        PRODUCTION MODE: Only past closing assignments should be added to closing_history.
        Future assignments should be stored separately and only moved to closing_history after the date passes.
        
        Args:
            date: The date for the closing assignment
            development_mode: If True, immediately add to closing_history (for development)
                             If False, only add if date is in the past (for production)
        
        TODO: BEFORE PRODUCTION - Change development_mode=False and implement proper future assignment handling!
        """
        if development_mode:
            # DEVELOPMENT MODE: Immediately add to closing history
            # This allows the engine to consider future assignments when generating subsequent schedules
            # WARNING: This will be changed in production!
            self.closing_history.append(date)
        else:
            # PRODUCTION MODE: Only add past assignments to closing history
            # TODO: Implement proper future assignment handling for production
            # For now, this is a placeholder - implement proper future assignment storage
            if date <= datetime.now().date():
                self.closing_history.append(date)
            else:
                # TODO: Store future assignments separately and move to closing_history when date passes
                # This prevents double assignments when generating multiple future schedules
                pass
        
        # Update closing delta calculation
        self._update_closing_delta()

    def is_available_for_y_task(self, day):
        # Returns True if not already assigned a Y task on this day
        return day not in self.y_tasks

    def has_x_task(self, week_start_date):
        """
        Check if worker has X task during the specified week (week_start_date to week_start_date + 6 days)
        Uses cached X-task data from CSV files
        """
        week_end_date = week_start_date + timedelta(days=6)
        
        # Check if any date in the week has an X-task
        for task_date_str in self.x_tasks.keys():
            try:
                task_date = datetime.strptime(task_date_str, '%d/%m/%Y').date()
                if week_start_date <= task_date <= week_end_date:
                    return True
            except ValueError:
                # Skip invalid date formats
                continue
        
        return False

    def has_specific_x_task(self, week_start_date, task_name):
        """
        Check if worker has a specific X task during the specified week.
        Reads X-task data from CSV files directly.
        """
        week_end_date = week_start_date + timedelta(days=6)
        
        # Check if the worker has the specific task during this week
        for task_date_str, task in self.x_tasks.items():
            try:
                task_date = datetime.strptime(task_date_str, '%d/%m/%Y').date()
                if week_start_date <= task_date <= week_end_date:
                    # Check if the task name matches (case-insensitive)
                    if isinstance(task, str) and task.lower() == task_name.lower():
                        return True
            except ValueError:
                # Skip invalid date formats
                continue
        
        return False

    def had_x_task(self, week_start_date):
        """
        Check if worker had X task during the specified week (week_start_date to week_start_date + 6 days)
        Uses cached X-task data from CSV files
        """
        week_end_date = week_start_date + timedelta(days=6)
        
        # Check if any date in the week has an X-task
        for task_date_str in self.x_tasks.keys():
            try:
                task_date = datetime.strptime(task_date_str, '%d/%m/%Y').date()
                if week_start_date <= task_date <= week_end_date:
                    return True
            except ValueError:
                # Skip invalid date formats
                continue
        
        return False

    def has_closing_scheduled(self, week_start_date):
        """
        Check if worker has closing scheduled during the specified week
        """
        week_end_date = week_start_date + timedelta(days=6)
        return any(week_start_date <= d <= week_end_date for d in self.closing_history)

    def has_y_task_scheduled(self, week_start_date):
        """
        Check if worker has Y task scheduled during the specified week
        """
        week_end_date = week_start_date + timedelta(days=6)
        return any(week_start_date <= d <= week_end_date for d in self.y_tasks)

    def has_any_task_scheduled(self, week_start_date):
        """
        Check if worker has any task (closing or Y task) scheduled during the specified week
        """
        return self.has_closing_scheduled(week_start_date) or self.has_y_task_scheduled(week_start_date)

    def is_due_to_close(self, date):
        """
        Check if worker is due to close on the given date based on their closing interval.
        Returns True if the worker should close on this date according to their schedule.
        
        Args:
            date: The date to check (should be a Friday for weekend closing)
            
        Returns:
            bool: True if worker is due to close on this date, False otherwise
        """
        if self.closing_interval <= 0:
            return False  # Worker doesn't participate in closing
        
        if not self.closing_history:
            return True  # First time closing
        
        # Get the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (date - last_closing).days // 7
        
        # Worker is due if weeks_since_last >= closing_interval
        return weeks_since_last >= self.closing_interval

    def is_overdue_to_close(self, date):
        """
        Check if worker is overdue to close on the given date.
        Returns True if the worker should have closed before this date.
        
        Args:
            date: The date to check
            
        Returns:
            bool: True if worker is overdue to close, False otherwise
        """
        if self.closing_interval <= 0:
            return False  # Worker doesn't participate in closing
        
        if not self.closing_history:
            return True  # Never closed, so overdue
        
        # Get the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (date - last_closing).days // 7
        
        # Worker is overdue if weeks_since_last > closing_interval
        return weeks_since_last > self.closing_interval

    def just_closed(self, date, weeks_threshold=2):
        """
        Check if worker just closed recently (within the specified weeks threshold).
        
        Args:
            date: The date to check from
            weeks_threshold: Number of weeks to consider "recent" (default: 2)
            
        Returns:
            bool: True if worker closed within the threshold, False otherwise
        """
        if not self.closing_history:
            return False
        
        # Get the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (date - last_closing).days // 7
        
        return weeks_since_last <= weeks_threshold

    def get_closing_interval(self):
        """
        Get the worker's closing interval.
        
        Returns:
            int: The closing interval in weeks, or 0 if worker doesn't participate
        """
        return self.closing_interval

    def had_x_task_last_week(self, date):
        """
        Check if worker had an X task in the previous week.
        
        Args:
            date: The date to check from
            
        Returns:
            bool: True if worker had X task in previous week, False otherwise
        """
        # Calculate the previous week's start (Monday)
        days_since_monday = date.weekday()
        current_week_start = date - timedelta(days=days_since_monday)
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_end = previous_week_start + timedelta(days=6)
        
        # Check if worker had any X task in the previous week
        for x_date_str in self.x_tasks.keys():
            try:
                x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                if previous_week_start <= x_date <= previous_week_end:
                    return True
            except ValueError:
                continue
        return False

    def is_starting_x_task_soon(self, date, context_aware=True):
        """
        Check if worker is starting an X task soon, with context awareness.
        
        Args:
            date: The date to check from
            context_aware: If True, considers closing interval context
            
        Returns:
            bool: True if worker is starting X task soon, False otherwise
        """
        if not context_aware:
            # Simple check: X task within next 2 weeks
            future_date = date + timedelta(days=14)
            for x_date_str in self.x_tasks.keys():
                try:
                    x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                    if date <= x_date <= future_date:
                        return True
                except ValueError:
                    continue
            return False
        
        # Context-aware check: Consider closing interval
        if self.closing_interval <= 0:
            return False  # Worker doesn't participate in closing
        
        # Check if worker has X task within their closing interval
        weeks_to_check = min(self.closing_interval, 4)  # Max 4 weeks ahead
        future_date = date + timedelta(weeks=weeks_to_check)
        
        for x_date_str in self.x_tasks.keys():
            try:
                x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                if date <= x_date <= future_date:
                    return True
            except ValueError:
                continue
        return False

    def just_finished_x_task(self, date):
        """
        Check if worker just finished an X task recently.
        
        Args:
            date: The date to check from
            
        Returns:
            bool: True if worker just finished X task, False otherwise
        """
        # Check if worker had X task in the last 3 days
        for x_date_str in self.x_tasks.keys():
            try:
                x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                days_since_x = (date - x_date).days
                if 0 <= days_since_x <= 3:  # Finished within last 3 days
                    return True
            except ValueError:
                continue
        return False

    def get_x_task_type(self, date):
        """
        Get the type of X task on the given date.
        
        Args:
            date: The date to check
            
        Returns:
            str: The X task type, or None if no X task on that date
        """
        # Convert date to string format for lookup
        if hasattr(date, 'strftime'):
            date_str = date.strftime('%d/%m/%Y')
        else:
            date_str = str(date)
        return self.x_tasks.get(date_str)

    def is_weekend_closer_with_y_tasks(self, weekend_date):
        """
        Check if worker is a weekend closer with Y tasks assigned.
        
        Args:
            weekend_date: The Friday date of the weekend
            
        Returns:
            bool: True if worker is weekend closer with Y tasks, False otherwise
        """
        # Check if worker is assigned to close this weekend
        thursday = weekend_date - timedelta(days=1)
        friday = weekend_date
        saturday = weekend_date + timedelta(days=1)
        sunday = weekend_date + timedelta(days=2)
        
        # Check if worker has closing assignment for this weekend
        weekend_closing = any(date in self.closing_history 
                             for date in [thursday, friday, saturday, sunday])
        
        if not weekend_closing:
            return False
        
        # Check if worker has Y tasks assigned for this weekend
        weekend_y_tasks = any(date in self.y_tasks 
                             for date in [thursday, friday, saturday, sunday])
        
        return weekend_y_tasks

    def get_days_until_x_task(self):
        """
        Calculate days until the next X task.
        
        Returns:
            int: Days until next X task, or None if no upcoming X tasks
        """
        if not self.x_tasks:
            return None
        
        today = date.today()
        upcoming_x_tasks = []
        
        for x_date_str in self.x_tasks.keys():
            try:
                x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                if x_date >= today:
                    upcoming_x_tasks.append(x_date)
            except ValueError:
                continue
        
        if not upcoming_x_tasks:
            return None
        
        next_x_task = min(upcoming_x_tasks)
        return (next_x_task - today).days

    def calculate_closing_violation_bonus(self, assigned_date):
        """
        ENHANCED: Calculate bonus points for closing violation (closing not on due date).
        Context-aware: Considers X task timing and closing interval.
        
        Args:
            assigned_date: The date when closing is assigned
            
        Returns:
            int: Bonus points to add to worker score
        """
        # Check if worker has Rituk X task on the assigned date
        if self.get_x_task_type(assigned_date) == "Rituk":
            return 0  # No bonus for Rituk workers
        
        # Calculate how far off from due date
        if not self.closing_history:
            # Never closed before, so this is their first time
            return 5  # Small bonus for first-time assignment
        
        # Find the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (assigned_date - last_closing).days // 7
        
        # Calculate how many weeks off from due date
        weeks_off = abs(weeks_since_last - self.closing_interval)
        
        # If weeks_off is 0, worker is exactly on schedule
        if weeks_off == 0:
            return 0  # No violation, no bonus
        
        # ENHANCED: Context-aware bonus calculation
        base_bonus = min(weeks_off * 5, 20)
        
        # Additional bonus based on X task proximity
        days_until_x_task = self.get_days_until_x_task()
        if days_until_x_task is not None and days_until_x_task <= 14:
            # Worker has X task within 2 weeks
            proximity_bonus = max(0, 15 - days_until_x_task)  # Closer = higher bonus
            base_bonus += proximity_bonus
        
        return base_bonus
    
    def get_closing_interval_context(self, target_date):
        """
        NEW: Get context about worker's closing interval relative to target date.
        
        Args:
            target_date: The date to analyze context for
            
        Returns:
            dict: Context information about closing interval
        """
        if self.closing_interval <= 0:
            return {
                'participates_in_closing': False,
                'is_due': False,
                'is_overdue': False,
                'weeks_off': 0,
                'next_due_date': None
            }
        
        if not self.closing_history:
            # Never closed before
            return {
                'participates_in_closing': True,
                'is_due': True,
                'is_overdue': True,
                'weeks_off': self.closing_interval,
                'next_due_date': target_date
            }
        
        # Find the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (target_date - last_closing).days // 7
        
        # Calculate how many weeks off from due date
        weeks_off = weeks_since_last - self.closing_interval
        
        # Calculate next due date
        next_due_date = last_closing + timedelta(weeks=self.closing_interval)
        
        return {
            'participates_in_closing': True,
            'is_due': weeks_off >= 0,
            'is_overdue': weeks_off > 0,
            'weeks_off': weeks_off,
            'next_due_date': next_due_date
        }
    
    def analyze_x_task_timing(self, target_date):
        """
        NEW: Analyze X task timing relative to target date.
        
        Args:
            target_date: The date to analyze from
            
        Returns:
            dict: Analysis of X task timing
        """
        if not self.x_tasks:
            return {
                'has_upcoming_x_task': False,
                'days_until_x_task': None,
                'x_task_type': None,
                'x_task_date': None,
                'conflicts_with_closing': False
            }
        
        # Find next X task
        upcoming_x_tasks = []
        
        for x_date_str in self.x_tasks.keys():
            try:
                x_date = datetime.strptime(x_date_str, '%d/%m/%Y').date()
                if x_date >= target_date:
                    upcoming_x_tasks.append(x_date)
            except ValueError:
                continue
        
        if not upcoming_x_tasks:
            return {
                'has_upcoming_x_task': False,
                'days_until_x_task': None,
                'x_task_type': None,
                'x_task_date': None,
                'conflicts_with_closing': False
            }
        
        next_x_task_date = min(upcoming_x_tasks)
        days_until_x_task = (next_x_task_date - target_date).days
        x_task_type = self.x_tasks[next_x_task_date.strftime('%d/%m/%Y')]
        
        # Check if X task conflicts with closing interval
        closing_context = self.get_closing_interval_context(target_date)
        conflicts_with_closing = False
        
        if closing_context['participates_in_closing']:
            # Check if X task falls within closing interval
            if closing_context['next_due_date']:
                weeks_between = (next_x_task_date - closing_context['next_due_date']).days // 7
                conflicts_with_closing = abs(weeks_between) <= 1  # Within 1 week of due date
        
        return {
            'has_upcoming_x_task': True,
            'days_until_x_task': days_until_x_task,
            'x_task_type': x_task_type,
            'x_task_date': next_x_task_date,
            'conflicts_with_closing': conflicts_with_closing
        }
    
    def should_warn_about_x_task_conflict(self, target_date):
        """
        NEW: Determine if user should be warned about X task conflict.
        
        Args:
            target_date: The date to check for conflicts
            
        Returns:
            dict: Warning information
        """
        x_task_analysis = self.analyze_x_task_timing(target_date)
        closing_context = self.get_closing_interval_context(target_date)
        
        if not x_task_analysis['has_upcoming_x_task']:
            return {
                'should_warn': False,
                'warning_message': None,
                'severity': None
            }
        
        # Check for high-severity conflicts
        if x_task_analysis['days_until_x_task'] <= 7:
            return {
                'should_warn': True,
                'warning_message': f"Worker has X task '{x_task_analysis['x_task_type']}' in {x_task_analysis['days_until_x_task']} days",
                'severity': 'high'
            }
        
        # Check for medium-severity conflicts
        if x_task_analysis['days_until_x_task'] <= 14 and x_task_analysis['conflicts_with_closing']:
            return {
                'should_warn': True,
                'warning_message': f"Worker has X task '{x_task_analysis['x_task_type']}' in {x_task_analysis['days_until_x_task']} days (conflicts with closing interval)",
                'severity': 'medium'
            }
        
        # Check for low-severity conflicts
        if x_task_analysis['conflicts_with_closing']:
            return {
                'should_warn': True,
                'warning_message': f"Worker has X task '{x_task_analysis['x_task_type']}' in {x_task_analysis['days_until_x_task']} days (may conflict with closing)",
                'severity': 'low'
            }
        
        return {
            'should_warn': False,
            'warning_message': None,
            'severity': None
        }

    def update_score_after_assignment(self, assignment_type, date, is_off_interval=False, is_manual=False):
        """
        Update worker score after assignment.
        
        Args:
            assignment_type: Type of assignment ("y_task", "closing", "x_task")
            date: Date of assignment
            is_off_interval: True if this is an off-interval closing assignment
            is_manual: True if this is a manual assignment
        """
        if assignment_type == "y_task":
            self.score += Y_TASK_SCORE_INCREMENT
        elif assignment_type == "closing":
            # Base closing score (no longer automatic points)
            if is_off_interval:
                self.score += OFF_INTERVAL_CLOSING_BONUS
            if is_manual:
                self.score += MANUAL_CLOSING_BONUS
        elif assignment_type == "x_task":
            # X tasks don't add to score (as per requirements)
            pass

    def reverse_score_after_removal(self, assignment_type, date, is_off_interval=False, is_manual=False):
        """
        Reverse worker score after assignment removal.
        
        Args:
            assignment_type: Type of assignment ("y_task", "closing", "x_task")
            date: Date of assignment
            is_off_interval: True if this was an off-interval closing assignment
            is_manual: True if this was a manual assignment
        """
        if assignment_type == "y_task":
            self.score = max(0.0, self.score - Y_TASK_SCORE_INCREMENT)  # Don't go below 0
        elif assignment_type == "closing":
            # Remove bonuses if applicable
            if is_off_interval:
                self.score = max(0.0, self.score - OFF_INTERVAL_CLOSING_BONUS)
            if is_manual:
                self.score = max(0.0, self.score - MANUAL_CLOSING_BONUS)
        elif assignment_type == "x_task":
            # X tasks don't affect score
            pass

    def get_last_closing_week(self):
        """
        Get the week start date of the last closing assignment
        Returns None if no closing history
        """
        if not self.closing_history:
            return None
        last_closing_date = max(self.closing_history)
        # Return the Monday of that week
        days_since_monday = last_closing_date.weekday()
        return last_closing_date - timedelta(days=days_since_monday)

    def get_total_closings(self):
        """
        Get total number of closing assignments
        """
        return len(self.closing_history)

    def get_total_weeks_served(self):
        """
        Calculate total weeks served since start date
        """
        if not self.start_date:
            return 1  # Default to 1 to avoid division by zero
        today = datetime.now().date()
        days_served = (today - self.start_date).days
        return max(1, days_served // 7)  # At least 1 week
    
    def _update_closing_delta(self):
        """
        Update the closing delta - how far off from ideal closing interval
        """
        if not self.closing_history:
            self.closing_delta = 0
            return
        
        # Calculate expected vs actual closings
        weeks_served = self.get_total_weeks_served()
        expected_closings = weeks_served // self.closing_interval if self.closing_interval > 0 else 0
        actual_closings = len(self.closing_history)
        self.closing_delta = actual_closings - expected_closings
    
    def get_workload_score(self):
        """
        Calculate workload score based on tallies
        Higher score = more overworked = should get fewer future tasks
        """
        workload_score = 0
        
        # X task penalty (each X task adds to workload penalty)
        workload_score += self.x_task_count * 2  # Reduced from 10 to 2
        
        # Y task penalty (each Y task adds to workload penalty)
        workload_score += self.y_task_count * 1  # Reduced from 5 to 1
        
        # Closing delta penalty (if behind schedule, should get priority)
        if self.closing_delta < 0:  # Behind schedule
            workload_score -= abs(self.closing_delta) * 20  # Priority for behind schedule
        elif self.closing_delta > 0:  # Ahead of schedule
            workload_score += self.closing_delta * 15  # Penalty for ahead of schedule
        
        return workload_score
    
    def is_my_turn_to_close(self, weekend_date: date) -> bool:
        """
        Given a weekend date (Friday), returns True if it's this worker's turn to close.
        
        Args:
            weekend_date: The Friday date of the weekend to check
            
        Returns:
            bool: True if it's this worker's turn to close on this weekend
        """
        if self.closing_interval <= 0:
            return False  # Worker doesn't participate in closing
        
        if not self.closing_history:
            return True  # First time closing, always their turn
        
        # Get the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (weekend_date - last_closing).days // 7
        
        # It's their turn if weeks_since_last >= closing_interval
        return weeks_since_last >= self.closing_interval
    
    def closing_status(self, weekend_date: date) -> Tuple[bool, int]:
        """
        Given a weekend date (Friday), returns (is_overdue, weeks_overdue).
        
        Examples:
        - Worker interval=2, closed 3 weeks ago, should have closed 1 week ago: (True, 2)
        - Worker interval=2, closed 1 week ago, not due yet: (False, 0)
        
        Args:
            weekend_date: The Friday date of the weekend to check
            
        Returns:
            Tuple[bool, int]: (is_overdue, weeks_overdue)
                - is_overdue: True if worker is overdue for closing
                - weeks_overdue: How many weeks overdue (0 if not overdue)
        """
        if self.closing_interval <= 0:
            return (False, 0)  # Worker doesn't participate in closing
        
        if not self.closing_history:
            return (False, 0)  # First time, not overdue
        
        # Get the last closing date
        last_closing = max(self.closing_history)
        
        # Calculate weeks since last closing
        weeks_since_last = (weekend_date - last_closing).days // 7
        
        # Calculate how many weeks overdue
        if weeks_since_last > self.closing_interval:
            weeks_overdue = weeks_since_last - self.closing_interval
            return (True, weeks_overdue)
        else:
            return (False, 0)
    
    def check_multiple_y_tasks_per_week(self, week_start_date: date) -> int:
        """
        Check how many Y tasks this worker has in a specific week (excluding Thu/Fri/Sat weekend closers).
        
        Args:
            week_start_date: Monday of the week to check
            
        Returns:
            int: Number of Y tasks assigned in this week (excluding weekend closing tasks)
        """
        week_end_date = week_start_date + timedelta(days=6)
        y_task_count = 0
        
        for task_date, task_name in self.y_tasks.items():
            if isinstance(task_date, str):
                try:
                    task_date = datetime.strptime(task_date, '%d/%m/%Y').date()
                except ValueError:
                    continue
            
            if week_start_date <= task_date <= week_end_date:
                # Skip weekend closing tasks (Thu/Fri/Sat)
                if task_date.weekday() not in [3, 4, 5]:  # 3=Thu, 4=Fri, 5=Sat
                    y_task_count += 1
        
        return y_task_count
    
    def increment_score_for_multiple_y_tasks(self, week_start_date: date):
        """
        Increment score if worker has more than one Y task in a week (excluding weekend closers).
        
        Args:
            week_start_date: Monday of the week to check
        """
        y_task_count = self.check_multiple_y_tasks_per_week(week_start_date)
        
        if y_task_count > 1:
            # Worker has multiple Y tasks in one week, increment score
            bonus_tasks = y_task_count - 1  # First task is normal, rest are bonus
            self.score += bonus_tasks * Y_TASK_SCORE_INCREMENT
    
    def load_y_tasks_from_csv(self, start_date: date, end_date: date, data_dir: str):
        """
        Load Y-task assignments from CSV files for a specific date range.
        This updates the worker's y_tasks dictionary.
        
        Args:
            start_date: Start date for loading Y tasks
            end_date: End date for loading Y tasks
            data_dir: Directory containing Y task CSV files
        """
        y_task_data = load_y_tasks_for_worker(self.id, self.name, start_date, end_date, data_dir)
        
        # Convert string dates to date objects and update y_tasks
        for date_str, task_name in y_task_data.items():
            try:
                task_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                self.y_tasks[task_date] = task_name
            except ValueError:
                continue
                
        # Update tally count
        self.y_task_count = len(self.y_tasks)
    
    def load_x_tasks_from_csv(self, data_dir: str):
        """
        Load X-task assignments from CSV files.
        This updates the worker's x_tasks dictionary.
        
        Args:
            data_dir: Directory containing X task CSV files
        """
        # Load X-tasks for all periods
        for year in [2025, 2026]:
            for period in [1, 2]:
                x_csv = os.path.join(data_dir, f"x_tasks_{year}_{period}.csv")
                if os.path.exists(x_csv):
                    x_task_data = read_x_tasks_from_csv(x_csv)
                    if self.id in x_task_data:
                        self.x_tasks.update(x_task_data[self.id])
        
        # Update tally count
        self.x_task_count = len(self.x_tasks)


# UTIL to load from JSON

def load_workers_from_json(json_path: str, name_conv_path: str = 'data/name_conv.json') -> List[Worker]:
    with open(json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    # Load name conversion (id to Hebrew name)
    try:
        with open(name_conv_path, 'r', encoding='utf-8') as f:
            name_conv_list = json.load(f)
        id_to_hebrew = {}
        for entry in name_conv_list:
            for k, v in entry.items():
                id_to_hebrew[k] = v
    except Exception:
        id_to_hebrew = {}
    
    # Load X-task data directly from CSV files
    try:
        data_dir = os.path.dirname(json_path)
        
        # Load X-tasks for all periods (2025_1, 2025_2, 2026_1, 2026_2)
        all_x_tasks = {}
        for year in [2025, 2026]:
            for period in [1, 2]:
                try:
                    x_csv = os.path.join(data_dir, f"x_tasks_{year}_{period}.csv")
                    
                    if os.path.exists(x_csv):
                        # Read X-tasks directly from CSV without relative imports
                        x_task_data = read_x_tasks_from_csv(x_csv)
                        all_x_tasks.update(x_task_data)
                except Exception as e:
                    print(f"Warning: Could not load X-tasks for {year}_{period}: {e}")
        
        print(f"✅ Loaded X-tasks from CSV files for {len(all_x_tasks)} workers")
    except Exception as e:
        print(f"⚠️  Warning: Could not load X-tasks from CSV files: {e}")
        all_x_tasks = {}
    
    workers = []
    for item in raw:
        sid = str(item.get('id', ''))
        hebrew_name = id_to_hebrew.get(sid, item.get('name', sid))
        # Parse closing_interval from 'closings' (e.g., '1:4' -> 4) or 'closing_interval'
        closings = item.get('closings', None)
        closing_interval = item.get('closing_interval', 0)  # Direct closing_interval field
        if closing_interval == 0 and closings:  # Fallback to old format
            if isinstance(closings, str) and ':' in closings:
                try:
                    closing_interval = int(closings.split(':')[1])
                except Exception:
                    closing_interval = 0
            elif isinstance(closings, int):
                closing_interval = closings
        # Optionally parse start_date if present
        start_date = None
        if 'start_date' in item:
            try:
                start_date = datetime.strptime(item['start_date'], '%Y-%m-%d').date()
            except Exception:
                start_date = None
        long_timer = item.get('long_timer', False)
        if not long_timer and 'rank' in item:
            long_timer = str(item['rank']).lower() == 'long'
        raw_score = item.get('score')
        # Ensure score is a float
        if raw_score is not None:
            try:
                score = float(raw_score)
            except (ValueError, TypeError):
                score = 0.0
        else:
            score = 0.0
        w = Worker(
            id=sid,
            name=hebrew_name,
            start_date=start_date,
            qualifications=item.get('qualifications', []),
            closing_interval=closing_interval,
            officer=item.get('officer', False),
            seniority=item.get('seniority'),
            score=score,
            long_timer=long_timer
        )
        
        # Load X-tasks from CSV data (not from worker_data.json)
        if sid in all_x_tasks:
            w.x_tasks = all_x_tasks[sid]
            print(f"   ✅ Loaded {len(w.x_tasks)} X-tasks for {w.name}")
        else:
            w.x_tasks = {}
            print(f"   🚫 No X-tasks found for {w.name}")
        
        # Load Y-tasks from CSV files (no longer from JSON)
        # Y-tasks will be loaded separately by date range when needed
        
        # Load closing history from dedicated CSV file
        closing_csv_path = os.path.join(data_dir, 'closing_history.csv')
        if os.path.exists(closing_csv_path):
            closing_data = read_closing_history_from_csv(closing_csv_path)
            if sid in closing_data:
                w.closing_history = closing_data[sid]
            else:
                w.closing_history = []
        else:
            # Fallback: Load from JSON if CSV doesn't exist yet
            if 'closing_history' in item:
                try:
                    w.closing_history = [datetime.strptime(d, '%d/%m/%Y').date() for d in item['closing_history']]
                except Exception:
                    w.closing_history = []
            else:
                w.closing_history = []
        
        workers.append(w)
    return workers


def reset_x_tasks_data():
    """Reset x tasks data in worker_data.json file"""
    print("=== RESETTING X TASKS ===")
    file = "../data/x_tasks.json"
    with open(file, 'r', encoding='utf-8') as f:
        workers = json.load(f)
    print(f"Loaded {len(workers)} workers")
    # Reset x task data
    for i, worker in enumerate(workers):
        worker['x_tasks'] = {}


def save_workers_to_json(workers: List[Worker], json_path: str, original_data: List[dict] = None):
    """
    Save workers back to JSON with updated closing history and assignments.
    
    DEVELOPMENT MODE: This saves all assignments including future ones to closing_history.
    This allows subsequent schedule generations to consider previous assignments.
    
    PRODUCTION MODE: This should be modified to only save past assignments to closing_history.
    
    Args:
        workers: List of Worker objects to save
        json_path: Path to save the JSON file
        original_data: Original JSON data to preserve other fields
    
    TODO: BEFORE PRODUCTION - Modify this function to only save past assignments to closing_history!
    """
    # Load original data if provided, otherwise create new structure
    if original_data:
        # Create a mapping of worker ID to original data
        original_map = {str(item.get('id', '')): item for item in original_data}
    else:
        original_map = {}

    # Convert workers to JSON format
    json_data = []
    for worker in workers:
        # Start with original data if available, otherwise create new structure
        if worker.id in original_map:
            worker_data = original_map[worker.id].copy()
        else:
            worker_data = {
                'id': worker.id,
                'name': worker.name,
                'qualifications': worker.qualifications,
                'closing_interval': worker.closing_interval,
                'officer': worker.officer,
                'seniority': worker.seniority,
                'score': worker.score,
                'long_timer': worker.long_timer
            }
            if worker.start_date:
                worker_data['start_date'] = worker.start_date.strftime('%d/%m/%Y')

        # Update with current assignments
        # Handle both string keys and datetime.date objects for x_tasks and y_tasks
        x_tasks_dict = {}
        for d, task in worker.x_tasks.items():
            if hasattr(d, 'strftime'):
                x_tasks_dict[d.strftime('%d/%m/%Y')] = task
            else:
                # Keep dd/mm/yyyy format as requested
                x_tasks_dict[str(d)] = task
        
        y_tasks_dict = {}
        for d, task in worker.y_tasks.items():
            if hasattr(d, 'strftime'):
                y_tasks_dict[d.strftime('%d/%m/%Y')] = task
            else:
                # Keep dd/mm/yyyy format as requested
                y_tasks_dict[str(d)] = task
        
        worker_data['x_tasks'] = x_tasks_dict
        worker_data['y_tasks'] = y_tasks_dict
        worker_data['closing_history'] = [d.strftime('%d/%m/%Y') for d in worker.closing_history]

        json_data.append(worker_data)

    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved {len(workers)} workers to {json_path}")
    print("⚠️  DEVELOPMENT MODE: Future closing assignments saved to closing_history")
    print("⚠️  TODO: BEFORE PRODUCTION - Modify to only save past assignments!")


def read_x_tasks_from_csv(csv_path: str) -> dict:
    """
    Read X-task assignments from CSV file.
    
    Args:
        csv_path: Path to the X-tasks CSV file
        
    Returns:
        Dictionary mapping worker_id -> {date_str: task_name}
    """
    x_task_data = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Read header row (dates)
            header = next(reader)
            dates = header[1:]  # Skip first column (worker name/id)
            
            # Read data rows
            for row in reader:
                if len(row) < 2:
                    continue
                    
                worker_id = row[0]
                assignments = row[1:]
                
                # Parse assignments for this worker
                worker_tasks = {}
                for i, assignment in enumerate(assignments):
                    if i < len(dates) and assignment and assignment != '-':
                        date_str = dates[i]
                        worker_tasks[date_str] = assignment
                
                if worker_tasks:
                    x_task_data[worker_id] = worker_tasks
                    
    except Exception as e:
        print(f"Error reading X-tasks from {csv_path}: {e}")
    
    return x_task_data


def read_y_tasks_from_csv(csv_path: str) -> dict:
    """
    Read Y-task assignments from CSV file.
    
    Args:
        csv_path: Path to the Y-tasks CSV file
        
    Returns:
        Dictionary mapping worker_name -> {date_str: task_name}
    """
    y_task_data = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Read header row (dates)
            header = next(reader)
            dates = header[1:]  # Skip first column (Y task type)
            
            # Read data rows (Y task types)
            for row in reader:
                if len(row) < 2:
                    continue
                    
                y_task_type = row[0]
                assignments = row[1:]
                
                # Parse assignments for this Y task type
                for i, worker_name in enumerate(assignments):
                    if i < len(dates) and worker_name and worker_name != '-':
                        date_str = dates[i]
                        
                        if worker_name not in y_task_data:
                            y_task_data[worker_name] = {}
                        
                        y_task_data[worker_name][date_str] = y_task_type
                        
    except Exception as e:
        print(f"Error reading Y-tasks from {csv_path}: {e}")
    
    return y_task_data


def read_closing_history_from_csv(csv_path: str) -> dict:
    """
    Read closing history from dedicated CSV file.
    
    Args:
        csv_path: Path to the closing history CSV file
        
    Returns:
        Dictionary mapping worker_id -> list of closing dates
    """
    closing_data = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                worker_id = row.get('worker_id', '')
                date_range = row.get('date_ranges', '')
                
                if worker_id and date_range:
                    if worker_id not in closing_data:
                        closing_data[worker_id] = []
                    
                    # Parse date range (assuming format like "03/08/2025-09/08/2025")
                    try:
                        start_date_str, end_date_str = date_range.split('-')
                        start_date = datetime.strptime(start_date_str, '%d/%m/%Y').date()
                        # For closing history, we store the Friday of the closing week
                        # Find the Friday in that week
                        friday_date = start_date + timedelta(days=(4 - start_date.weekday()) % 7)
                        closing_data[worker_id].append(friday_date)
                    except Exception as e:
                        print(f"Error parsing date range {date_range}: {e}")
                        
    except Exception as e:
        print(f"Error reading closing history from {csv_path}: {e}")
    
    return closing_data


def save_closing_history_to_csv(csv_path: str, workers: List[Worker]):
    """
    Save closing history to dedicated CSV file.
    
    Args:
        csv_path: Path to save the closing history CSV file
        workers: List of Worker objects with closing history
    """
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['worker_id', 'name', 'date_ranges', 'week_number', 'part_of_year'])
            
            # Write closing history for each worker
            for worker in workers:
                if worker.closing_history:
                    for closing_date in worker.closing_history:
                        # Calculate week number and part of year
                        week_number = closing_date.isocalendar()[1]
                        part_of_year = f"{closing_date.year}_{1 if closing_date.month <= 6 else 2}"
                        
                        # Create date range (Friday to following Friday)
                        week_start = closing_date - timedelta(days=closing_date.weekday() + 3)  # Go to Monday
                        week_end = week_start + timedelta(days=6)  # Sunday
                        date_range = f"{week_start.strftime('%d/%m/%Y')}-{week_end.strftime('%d/%m/%Y')}"
                        
                        writer.writerow([
                            worker.id,
                            worker.name,
                            date_range,
                            week_number,
                            part_of_year
                        ])
                        
    except Exception as e:
        print(f"Error saving closing history to {csv_path}: {e}")


def load_y_tasks_for_worker(worker_id: str, worker_name: str, start_date: date, end_date: date, data_dir: str) -> dict:
    """
    Load Y-task assignments for a specific worker within a date range.
    
    Args:
        worker_id: Worker's ID
        worker_name: Worker's name
        start_date: Start date for loading Y tasks
        end_date: End date for loading Y tasks
        data_dir: Directory containing Y task CSV files
        
    Returns:
        Dictionary mapping date_str -> task_name for this worker
    """
    y_tasks = {}
    
    try:
        # Find all Y task CSV files in the date range
        y_task_files = []
        for filename in os.listdir(data_dir):
            if filename.startswith('y_tasks_') and filename.endswith('.csv'):
                y_task_files.append(filename)
        
        for filename in y_task_files:
            filepath = os.path.join(data_dir, filename)
            y_task_data = read_y_tasks_from_csv(filepath)
            
            # Get assignments for this worker (try both ID and name)
            worker_assignments = y_task_data.get(worker_name, {})
            if not worker_assignments and worker_id in y_task_data:
                worker_assignments = y_task_data.get(worker_id, {})
            
            # Filter by date range
            for date_str, task_name in worker_assignments.items():
                try:
                    task_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    if start_date <= task_date <= end_date:
                        y_tasks[date_str] = task_name
                except ValueError:
                    continue
                    
    except Exception as e:
        print(f"Error loading Y tasks for worker {worker_name}: {e}")
    
    return y_tasks
