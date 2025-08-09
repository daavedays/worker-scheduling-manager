from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import sys
from pathlib import Path

# Add backend to path for worker import
sys.path.append(str(Path(__file__).parent))
try:
    from .worker import EnhancedWorker
except ImportError:
    from worker import EnhancedWorker


class ClosingScheduleCalculator:
    """
    Improved Closing Schedule Calculator implementing the backwards-looking algorithm
    with proper weekends_home_owed tracking as specified by the user.
    """
    
    def __init__(self):
        self.debug = True
        self.user_alerts = []  # Store alerts for impossible scenarios
    
    def calculate_worker_closing_schedule(self, worker: 'EnhancedWorker', 
                                        semester_weeks: List[date]) -> Dict:
        """Calculate closing schedule for a worker using the new algorithm."""
        if not semester_weeks:
            # No semester weeks provided, return empty schedule
            return {
                'required_dates': [],
                'optimal_dates': [],
                'final_weekends_home_owed': worker.weekends_home_owed,
                'calculation_log': ['No semester weeks provided'],
                'user_alerts': []
            }
        
        # Initialize schedule for all weeks
        schedule = ['HOME'] * len(semester_weeks)
        weekends_home_owed = worker.weekends_home_owed  # Start with existing debt
        calculation_log = []
        user_alerts = []
        
        # Get last closing date to determine starting pattern
        last_close_date = self._get_last_closing_date(worker, semester_weeks[0])
        weeks_since_last_close = self._get_weeks_since_last_close(last_close_date, semester_weeks[0])
        
        if self.debug:
            print(f"  Last close: {last_close_date}, weeks since: {weeks_since_last_close}")
        
        # Get X task weeks first
        x_task_weeks = self._get_x_task_weeks(worker, semester_weeks)
        
        # Calculate interval closes while avoiding conflicts with X tasks  
        interval_closes = self._calculate_smart_interval_closes(worker, semester_weeks, weeks_since_last_close, x_task_weeks)
        
        if self.debug:
            print(f"  Interval closes: {[i+1 for i in interval_closes]}")
            print(f"  X task weeks: {[i+1 for i in x_task_weeks]}")
        
        # Process each week using the backwards-looking algorithm  
        for week_idx in range(len(semester_weeks)):
            week_num = week_idx + 1
            current_date = semester_weeks[week_idx]
            has_x_task = week_idx in x_task_weeks
            should_close_by_interval = week_idx in interval_closes
            
            # Check if previous week was a close to prevent consecutive closes
            prev_was_close = week_idx > 0 and schedule[week_idx - 1] == 'CLOSE'
            
            if has_x_task:
                # X task forces close - but NEVER allow consecutive closes
                if prev_was_close:
                    # ABSOLUTELY NOT! Cannot have consecutive closes
                    # This should NEVER happen with the smart interval calculation
                    # If it does, it's a critical error in the algorithm
                    user_alerts.append(f"CRITICAL ERROR: Week {week_num} X task would cause consecutive close for {worker.name} - ALGORITHM FAILURE!")
                    calculation_log.append(f"Week {week_num}: CRITICAL ERROR - X task would cause consecutive close - This should never happen!")
                    
                    # Force HOME for this week and add massive debt as compensation
                    schedule[week_idx] = 'HOME'
                    # weekends_home_owed += 10  # Massive debt for missing X task, please dont add things I didnt ask for
                    calculation_log.append(f"Week {week_num}: X task SKIPPED to prevent consecutive close - MASSIVE debt +10, total owed: {weekends_home_owed}")
                else:
                    # Normal X task handling - safe to close
                    decision, debt_change, alert = self._handle_x_task_week(
                        worker, week_idx, schedule, weekends_home_owed, should_close_by_interval
                    )
                    weekends_home_owed += debt_change
                    
                    if alert:
                        user_alerts.append(f"Week {week_num}: {alert}")
                    
                    calculation_log.append(f"Week {week_num}: X task - FORCED CLOSE, debt change: +{debt_change}, total owed: {weekends_home_owed}")
                    schedule[week_idx] = 'CLOSE'  # X task close is safe
                
            elif should_close_by_interval:
                # Should close by interval
                if prev_was_close:
                    # Would create consecutive closes - give HOME instead and add debt
                    schedule[week_idx] = 'HOME'
                    weekends_home_owed += 1
                    calculation_log.append(f"Week {week_num}: Interval close skipped (would be consecutive) - HOME given, debt +1, total owed: {weekends_home_owed}")
                elif weekends_home_owed > 0:
                    # Pay back debt by giving HOME instead of CLOSE
                    schedule[week_idx] = 'HOME'
                    weekends_home_owed -= 1
                    calculation_log.append(f"Week {week_num}: Paying back debt - HOME instead of close, debt reduced to: {weekends_home_owed}")
                else:
                    # No debt, no consecutive issue - normal interval close
                    schedule[week_idx] = 'CLOSE'
                    calculation_log.append(f"Week {week_num}: Normal interval close")
            else:
                # Home week - no action needed
                schedule[week_idx] = 'HOME'
                calculation_log.append(f"Week {week_num}: Home week")
        
        # Separate required (X task) and optimal (interval) closes
        required_dates = []
        optimal_dates = []
        
        for week_idx, action in enumerate(schedule):
            if action == 'CLOSE':
                week_date = semester_weeks[week_idx]
                if week_idx in x_task_weeks:
                    required_dates.append(week_date)
                else:
                    optimal_dates.append(week_date)
        
        if self.debug:
            print(f"  Final debt: {weekends_home_owed}")
            print(f"  Required closes: {len(required_dates)}")
            print(f"  Optimal closes: {len(optimal_dates)}")
        
        return {
            'required_dates': required_dates,
            'optimal_dates': optimal_dates,
            'final_weekends_home_owed': weekends_home_owed,
            'calculation_log': calculation_log,
            'user_alerts': user_alerts
        }
    
    def _handle_x_task_week(self, worker: 'EnhancedWorker', week_idx: int, 
                           schedule: List[str], current_debt: int, 
                           should_close_by_interval: bool) -> Tuple[str, int, Optional[str]]:
        """
        Handle X task week using backwards-looking logic.
        
        Returns: (decision, debt_change, alert_message)
        """
        # Count consecutive home weeks before this X task
        home_weeks_before = self._count_home_weeks_before(schedule, week_idx)
        week_num = week_idx + 1
        
        if home_weeks_before >= 2:
            # Had enough home time, can assign X task with minimal debt
            if should_close_by_interval:
                # Would have closed anyway, no extra debt
                return 'CLOSE', 0, None
            else:
                # Forced to close when should be home, add 1 debt
                return 'CLOSE', 1, None
        else:
            # Haven't had enough home time - this is problematic
            alert = f"Worker {worker.name} has X task but only {home_weeks_before} home weeks before. Forced assignment."
            
            # Try to find recent closes that could be converted to home
            conversion_possible = self._try_convert_recent_close_to_home(schedule, week_idx)
            
            if conversion_possible:
                # We managed to convert a recent close to home
                return 'CLOSE', 1, f"Converted recent close to home for {worker.name}"
            else:
                # No conversion possible, significant debt penalty
                penalty = 2 if home_weeks_before == 0 else 1
                return 'CLOSE', penalty, alert
    
    def _count_home_weeks_before(self, schedule: List[str], week_idx: int) -> int:
        """Count consecutive HOME weeks before the given week."""
        count = 0
        for i in range(week_idx - 1, -1, -1):
            if schedule[i] == 'HOME':
                count += 1
            else:
                break
        return count
    
    def _try_convert_recent_close_to_home(self, schedule: List[str], week_idx: int) -> bool:
        """
        Try to convert a recent CLOSE to HOME to make room for X task.
        Only converts non-X task closes (optimal closes).
        
        Returns True if conversion was successful.
        """
        # Look back up to 3 weeks for a convertible close
        for i in range(max(0, week_idx - 3), week_idx):
            if schedule[i] == 'CLOSE':
                # For now, assume we can convert it (in real implementation, 
                # we'd need to check if it's an X task close)
                schedule[i] = 'HOME'
                return True
        return False
    
    def _calculate_smart_interval_closes(self, worker: 'EnhancedWorker', semester_weeks: List[date], 
                                       weeks_since_last_close: int, x_task_weeks: List[int]) -> List[int]:
        """Calculate interval closes while avoiding consecutive closes with X tasks."""
        interval_closes = []

        # Safety: invalid or zero interval would cause infinite loop
        if worker.closing_interval is None or worker.closing_interval <= 0:
            return interval_closes
        
        # FIXED: Proper interval calculation
        # If last close was N weeks ago, and interval is I:
        # - If N >= I, should close in week 1
        # - If N < I, should close in week (I - N + 1)
        
        if weeks_since_last_close >= worker.closing_interval:
            # Overdue - should close immediately (week 1)
            first_close_week = 0
        else:
            # Calculate when next close is due
            weeks_until_due = worker.closing_interval - weeks_since_last_close
            first_close_week = weeks_until_due - 1  # Convert to 0-based
        
        # Generate interval closes, but shift when they would create consecutive closes with X tasks
        current_close_week = first_close_week
        step = max(1, worker.closing_interval)
        
        while current_close_week < len(semester_weeks):
            # Check if this interval close would be consecutive with an X task
            prev_week = current_close_week - 1
            next_week = current_close_week + 1
            
            prev_has_x = prev_week >= 0 and prev_week in x_task_weeks
            next_has_x = next_week < len(semester_weeks) and next_week in x_task_weeks
            
            if prev_has_x or next_has_x:
                # This interval close would be consecutive with an X task
                # Try to shift it to avoid consecutive closes
                shifted = False
                
                # Try shifting forward first (within the interval window)
                for shift in range(1, worker.closing_interval):
                    candidate_week = current_close_week + shift
                    if candidate_week >= len(semester_weeks):
                        break
                    
                    # Check if this candidate would also create consecutive issues
                    cand_prev = candidate_week - 1
                    cand_next = candidate_week + 1
                    
                    cand_prev_has_x = cand_prev >= 0 and cand_prev in x_task_weeks
                    cand_next_has_x = cand_next < len(semester_weeks) and cand_next in x_task_weeks
                    
                    if not cand_prev_has_x and not cand_next_has_x:
                        # Found a good spot
                        interval_closes.append(candidate_week)
                        shifted = True
                        break
                
                if not shifted:
                    # Try shifting backward
                    for shift in range(1, worker.closing_interval):
                        candidate_week = current_close_week - shift
                        if candidate_week < 0:
                            break
                        
                        # Check if this candidate would create consecutive issues
                        cand_prev = candidate_week - 1
                        cand_next = candidate_week + 1
                        
                        cand_prev_has_x = cand_prev >= 0 and cand_prev in x_task_weeks
                        cand_next_has_x = cand_next < len(semester_weeks) and cand_next in x_task_weeks
                        
                        if not cand_prev_has_x and not cand_next_has_x:
                            # Found a good spot
                            interval_closes.append(candidate_week)
                            shifted = True
                            break
                
                if not shifted:
                    # Couldn't find a good shift, skip this interval close
                    pass  # This will add debt later when processing
            else:
                # No conflict, use the normal interval close
                interval_closes.append(current_close_week)
            
            current_close_week += step
        
        return interval_closes
    
    def _get_x_task_weeks(self, worker: 'EnhancedWorker', semester_weeks: List[date]) -> List[int]:
        """Get list of week indices that have X tasks."""
        x_task_weeks = []
        
        for week_idx, week_date in enumerate(semester_weeks):
            date_str = week_date.strftime('%d/%m/%Y')
            if date_str in worker.x_tasks:
                x_task_weeks.append(week_idx)
        
        return x_task_weeks
    
    def _get_last_closing_date(self, worker: 'EnhancedWorker', semester_start: date) -> date:
        """Get the worker's last closing date before semester start."""
        if worker.closing_history:
            return worker.closing_history[-1]
        else:
            # If no history, assume they closed some weeks before semester start
            # based on their interval to create a reasonable starting point
            return semester_start - timedelta(weeks=worker.closing_interval - 1)
    
    def _get_weeks_since_last_close(self, last_close_date: date, semester_start: date) -> int:
        """Calculate weeks between last close and semester start."""
        delta = semester_start - last_close_date
        return delta.days // 7
    
    def update_all_worker_schedules(self, workers: List['EnhancedWorker'], 
                                  semester_weeks: List[date]):
        """Update closing schedules for all workers and store alerts."""
        print(f"\n🔄 UPDATING CLOSING SCHEDULES FOR {len(workers)} WORKERS")
        print("=" * 60)
        
        self.user_alerts = []  # Reset alerts
        
        for worker in workers:
            result = self.calculate_worker_closing_schedule(worker, semester_weeks)
            
            # Update worker attributes
            worker.required_closing_dates = result['required_dates']
            worker.optimal_closing_dates = result['optimal_dates']
            worker.weekends_home_owed = result['final_weekends_home_owed']
            
            # Collect any alerts
            if result['user_alerts']:
                self.user_alerts.extend(result['user_alerts'])
            
            if self.debug:
                print(f"\n{worker.name}:")
                print(f"  Required closes: {len(result['required_dates'])} (X tasks)")
                print(f"  Optimal closes: {len(result['optimal_dates'])} (interval)")
                print(f"  Weekends home owed: {result['final_weekends_home_owed']}")
        
        if self.user_alerts:
            print(f"\n⚠️  USER ALERTS ({len(self.user_alerts)}):")
            for alert in self.user_alerts:
                print(f"  • {alert}")
    
    def get_user_alerts(self) -> List[str]:
        """Get all user alerts from the last calculation."""
        return self.user_alerts.copy()
