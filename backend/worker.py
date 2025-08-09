from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Optional
import json
import os
import csv


class EnhancedWorker:
    """
    Enhanced Worker class with streamlined functionality based on requirements
    """
    
    def __init__(self, id: str, name: str, start_date: date, qualifications: List[str], 
                 closing_interval: int, officer: bool = False, seniority: str = None,
                 score: float = 0.0, long_timer: bool = False, weekends_home_owed: int = 0):
        # Core attributes as requested
        self.id = id
        self.name = name
        self.qualifications = qualifications.copy() if qualifications else []
        self.closing_interval = closing_interval
        self.score = float(score)  # Higher = more overworked = lower priority
        
        # Pre-computed closing schedule based on X tasks
        self.required_closing_dates = []  # Must close (due to X tasks)
        self.optimal_closing_dates = []   # Should close (based on intervals)  
        # Compensation owed to worker (alias both names for compatibility)
        self.weekends_home_owed = int(weekends_home_owed)
        self.home_weeks_owed = int(weekends_home_owed)
        
        # Y task tracking by type for scoring
        self.y_task_counts = {
            "Supervisor": 0,
            "C&N Driver": 0,
            "C&N Escort": 0,
            "Southern Driver": 0,
            "Southern Escort": 0
        }
        
        # Task tracking (required by multiple methods and persistence)
        self.x_tasks = {}  # date_string -> task_name
        self.y_tasks = {}  # date -> task_name
        self.closing_history = []
        
        # Legacy compatibility
        self.start_date = start_date
        self.officer = officer
        self.seniority = seniority
        self.long_timer = long_timer
        self.x_task_count = 0
        self.y_task_count = 0
        self.closing_delta = 0
    
    # ============================================================================
    # CORE SCORING METHODS
    # ============================================================================
    
    def add_score_bonus(self, amount: float, reason: str):
        """Add bonus to score (higher = more overworked = lower assignment priority)"""
        self.score += amount
        print(f"{self.name}: +{amount:.1f} bonus ({reason}) → Total: {self.score:.1f}")
    
    def subtract_score_bonus(self, amount: float, reason: str):
        """Subtract from score (lower = less overworked = higher assignment priority)"""
        old_score = self.score
        self.score = max(0.0, self.score - amount)
        actual_reduction = old_score - self.score
        print(f"{self.name}: -{actual_reduction:.1f} reduction ({reason}) → Total: {self.score:.1f}")
    
    # ============================================================================
    # CLOSING SCHEDULE METHODS
    # ============================================================================
    
    def get_weeks_until_due_to_close(self, current_week: date) -> int:
        """Get how many weeks until worker is due to close"""
        if self.closing_interval <= 0:
            return float('inf')
        if not self.closing_history:
            return 0
        last_close = max(self.closing_history)
        weeks_since = (current_week - last_close).days // 7
        return max(0, self.closing_interval - weeks_since)
    
    def has_closing_scheduled(self, target_date: date) -> bool:
        """Check if worker has closing scheduled on target date"""
        return target_date in self.required_closing_dates or target_date in self.optimal_closing_dates
    
    def has_y_task_scheduled(self, target_date: date) -> bool:
        """Check if worker has Y task scheduled on target date"""
        return target_date in self.y_tasks
    
    def has_any_task_scheduled(self, target_date: date) -> bool:
        """Check if worker has any task scheduled on target date"""
        return (self.has_closing_scheduled(target_date) or 
                self.has_y_task_scheduled(target_date) or
                self.has_x_task_on_date(target_date))
    
    def just_closed(self, current_date: date, days_threshold: int = 7) -> bool:
        """Check if worker closed recently"""
        if not self.closing_history:
            return False
        last_close = max(self.closing_history)
        days_since = (current_date - last_close).days
        return days_since <= days_threshold
    
    def get_closing_interval(self) -> int:
        """Get worker's closing interval"""
        return self.closing_interval

    def get_last_closing_week(self) -> Optional[date]:
        """Get the date of worker's last closing"""
        return max(self.closing_history) if self.closing_history else None
    
    def get_total_closings(self) -> int:
        """Get total number of closings"""
        return len(self.closing_history)
    
    def _update_closing_delta(self):
        """Update the closing delta - how far off from ideal closing interval"""
        if not self.closing_history:
            self.closing_delta = 0
            return
        weeks_served = self.get_total_weeks_served()
        expected_closings = weeks_served // self.closing_interval if self.closing_interval > 0 else 0
        actual_closings = len(self.closing_history)
        self.closing_delta = actual_closings - expected_closings
    
    def closing_status(self, current_week: date) -> Dict:
        """Updated closing status using required and optimal closing dates"""
        status = {
            'is_due': current_week in self.optimal_closing_dates,
            'is_required': current_week in self.required_closing_dates,
            'is_overdue': False,
            'weeks_overdue': 0,
            'weeks_until_due': self.get_weeks_until_due_to_close(current_week)
        }
        overdue_count = sum(1 for opt_date in self.optimal_closing_dates if opt_date < current_week)
        if overdue_count > 0:
            status['is_overdue'] = True
            status['weeks_overdue'] = overdue_count
        return status
    
    # ============================================================================
    # X TASK METHODS
    # ============================================================================
    
    def has_specific_x_task(self, target_date: date, task_name: str) -> bool:
        """Check if worker has specific X task on target date"""
        x_task = self.get_x_task_on_date(target_date)
        return x_task is not None and x_task.lower() == task_name.lower()
    
    def has_x_task_on_date(self, target_date: date) -> bool:
        """Check if worker has any X task on specific date"""
        date_str = target_date.strftime('%d/%m/%Y')
        return date_str in self.x_tasks
    
    def get_x_task_on_date(self, target_date: date) -> Optional[str]:
        """Get X task name on specific date"""
        date_str = target_date.strftime('%d/%m/%Y')
        return self.x_tasks.get(date_str)
    
    def had_x_task(self, target_date: date, days_back: int = 7) -> bool:
        """Check if worker had X task recently"""
        for i in range(1, days_back + 1):
            check_date = target_date - timedelta(days=i)
            if self.has_x_task_on_date(check_date):
                return True
        return False
    
    def just_finished_x_task(self, current_date: date, days_threshold: int = 7) -> bool:
        """Check if worker just finished an X task"""
        return self.had_x_task(current_date, days_threshold)
    
    def get_x_task_type(self, target_date: date) -> Optional[str]:
        """Get X task type on specific date"""
        return self.get_x_task_on_date(target_date)
    
    def should_warn_about_x_task_conflict(self, target_week: date) -> Dict:
        """Check if assignment would conflict with X tasks"""
        conflicts = []
        for offset in [-1, 0, 1]:
            check_date = target_week + timedelta(days=offset * 7)
            if self.has_x_task_on_date(check_date):
                x_task = self.get_x_task_on_date(check_date)
                conflicts.append({
                    'date': check_date,
                    'x_task': x_task,
                    'severity': 'high' if offset == 0 else 'medium'
                })
        
        should_warn = len(conflicts) > 0 and not any(
            conflict['x_task'].lower() == 'rituk' for conflict in conflicts
        )
        
        return {
            'should_warn': should_warn,
            'conflicts': conflicts,
            'warning_message': f"Assignment conflicts with X task(s): {[c['x_task'] for c in conflicts]}" if should_warn else ""
        }
    
    # ============================================================================
    # Y TASK METHODS
    # ============================================================================
    
    def check_multiple_y_tasks_per_week(self, week_start_date: date) -> int:
        """Check how many Y tasks this worker has in a specific week"""
        count = 0
        for i in range(7):
            check_date = week_start_date + timedelta(days=i)
            if check_date in self.y_tasks:
                count += 1
        return count
    
    def increment_score_for_multiple_y_tasks(self, week_start_date: date, threshold: int = 2):
        """Updated method for multiple Y task penalty"""
        y_task_count = self.check_multiple_y_tasks_per_week(week_start_date)
        if y_task_count >= threshold:
            excess = y_task_count - threshold + 1
            bonus = excess * 1.0
            self.add_score_bonus(bonus, f"Multiple Y tasks in week {week_start_date.strftime('%d/%m/%Y')}")

    def assign_y_task(self, task_date: date, task_name: str):
        """Assign Y task to worker"""
        self.y_tasks[task_date] = task_name
        if task_name in self.y_task_counts:
            self.y_task_counts[task_name] += 1
        else:
            self.y_task_counts[task_name] = 1
        self.y_task_count += 1   
 
    
    def assign_closing(self, closing_date: date):
        """Assign closing to worker"""
        if closing_date not in self.closing_history:
            self.closing_history.append(closing_date)
            self.closing_history.sort()
    
    # ============================================================================
    # UPDATED SCORING METHODS
    # ============================================================================
    
    def update_score_after_assignment(self, assignment_type: str, date: date):
        """Simplified scoring after assignment - basic tracking only"""
        if assignment_type == "y_task":
            self.add_score_bonus(1.0, f"Y task on {date.strftime('%d/%m/%Y')}")
        elif assignment_type == "closing":
            self.add_score_bonus(1.5, f"Closing on {date.strftime('%d/%m/%Y')}")
    
    def reverse_score_after_removal(self, assignment_type: str, date: date):
        """Simplified scoring after removing assignment"""
        if assignment_type == "y_task":
            self.subtract_score_bonus(1.0, f"Y task removed {date.strftime('%d/%m/%Y')}")
        elif assignment_type == "closing":
            self.subtract_score_bonus(1.5, f"Closing removed {date.strftime('%d/%m/%Y')}")
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def get_total_weeks_served(self) -> int:
        """Calculate total weeks worker has been active"""
        if self.start_date:
            return (date.today() - self.start_date).days // 7
        return 0
    
    def clear_schedule(self):
        """Clear pre-computed schedule"""
        self.required_closing_dates = []
        self.optimal_closing_dates = []
        self.home_weeks_owed = 0
    
    # ============================================================================
    # DATA PERSISTENCE METHODS
    # ============================================================================
    
    def to_dict(self) -> Dict:
        """Convert worker to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'qualifications': self.qualifications,
            'closing_interval': self.closing_interval,
            'officer': self.officer,
            'seniority': self.seniority,
            'score': self.score,
            'long_timer': self.long_timer,
            'x_tasks': self.x_tasks,
            'y_tasks': {date_obj.isoformat(): task for date_obj, task in self.y_tasks.items()},
            'closing_history': [d.isoformat() for d in self.closing_history],
            'required_closing_dates': [d.isoformat() for d in self.required_closing_dates],
            'optimal_closing_dates': [d.isoformat() for d in self.optimal_closing_dates],
            'home_weeks_owed': self.home_weeks_owed,
            'weekends_home_owed': self.weekends_home_owed,
            'y_task_counts': self.y_task_counts,
            'x_task_count': self.x_task_count,
            'y_task_count': self.y_task_count,
            'closing_delta': self.closing_delta
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EnhancedWorker':
        """Create worker from dictionary"""
        start_date = None
        if data.get('start_date'):
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        worker = cls(
            id=data['id'],
            name=data['name'],
            start_date=start_date,
            qualifications=data['qualifications'],
            closing_interval=data['closing_interval'],
            officer=data.get('officer', False),
            seniority=data.get('seniority'),
            score=data.get('score', 0.0),
            long_timer=data.get('long_timer', False),
            weekends_home_owed=data.get('weekends_home_owed', data.get('home_weeks_owed', 0))
        )
        
        # Load task data
        worker.x_tasks = data.get('x_tasks', {})
        
        # Load Y tasks
        y_tasks_data = data.get('y_tasks', {})
        for date_str, task in y_tasks_data.items():
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            worker.y_tasks[date_obj] = task
        
        # Load closing history TODO: UPDATE DATES TO BE DD/MM/YYYY!!!!!!!!!! 
        closing_history_data = data.get('closing_history', [])
        worker.closing_history = [datetime.strptime(d, '%Y-%m-%d').date() for d in closing_history_data]
        
        # Load enhanced data
        worker.y_task_counts = data.get('y_task_counts', {
            "Supervisor": 0, "C&N Driver": 0, "C&N Escort": 0,
            "Southern Driver": 0, "Southern Escort": 0
        })
        worker.home_weeks_owed = data.get('home_weeks_owed', data.get('weekends_home_owed', 0))
        worker.weekends_home_owed = data.get('weekends_home_owed', worker.home_weeks_owed)
        
        # Load pre-computed schedule
        required_dates = data.get('required_closing_dates', [])
        worker.required_closing_dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in required_dates]
        
        optimal_dates = data.get('optimal_closing_dates', [])
        worker.optimal_closing_dates = [datetime.strptime(d, '%Y-%m-%d').date() for d in optimal_dates]
        
        # Load legacy data
        worker.x_task_count = data.get('x_task_count', 0)
        worker.y_task_count = data.get('y_task_count', 0)
        worker.closing_delta = data.get('closing_delta', 0)
        
        return worker


# ============================================================================
# FILE I/O FUNCTIONS (Keep existing functionality)
# ============================================================================

def load_workers_from_json(filepath: str, name_conv_path: str | None = None) -> List[EnhancedWorker]:
    """Load workers from JSON file (legacy-compatible signature).

    name_conv_path is ignored and kept for backward compatibility with old modules.
    """
    workers = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            workers_data = json.load(f)
        for worker_data in workers_data:
            worker = EnhancedWorker.from_dict(worker_data)
            workers.append(worker)
    except FileNotFoundError:
        print(f"Worker file not found: {filepath}")
    except Exception as e:
        print(f"Error loading workers: {e}")
    return workers


def save_workers_to_json(workers: List[EnhancedWorker], filepath: str, original_data: List = None):
    """Save workers to JSON file"""
    workers_data = [worker.to_dict() for worker in workers]
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(workers_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved {len(workers)} workers to {filepath}")
    except Exception as e:
        print(f"❌ Error saving workers: {e}")


def load_y_tasks_from_csv(filepath: str, workers: List[EnhancedWorker]):
    """Load Y tasks from CSV file"""
    if not os.path.exists(filepath):
        print(f"Y tasks file not found: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            # Parse dates from headers (skip first column which is task name)
            dates = []
            for header in headers[1:]:
                try:
                    dates.append(datetime.strptime(header, '%d/%m/%Y').date())
                except ValueError:
                    continue
            
            # Read task assignments
            for row in reader:
                if not row:
                    continue
                    
                task_name = row[0]
                for i, worker_name in enumerate(row[1:]):
                    if worker_name and i < len(dates):
                        # Find worker and assign task
                        for worker in workers:
                            if worker.name == worker_name:
                                worker.assign_y_task(dates[i], task_name)
                                break
                    
    except Exception as e:
        print(f"Error loading Y tasks from CSV: {e}")


def load_x_tasks_from_csv(filepath: str, workers: List[EnhancedWorker]):
    """Load X tasks from CSV file"""
    if not os.path.exists(filepath):
        print(f"X tasks file not found: {filepath}")
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            
            # Parse dates from headers (skip first column which is worker name)
            dates = []
            for header in headers[1:]:
                try:
                    dates.append(header)  # Keep as string for X tasks
                except ValueError:
                    continue
            
            # Read X task assignments
            for row in reader:
                if not row:
                    continue
                    
                worker_name = row[0]
                worker = next((w for w in workers if w.name == worker_name), None)
                
                if worker:
                    for i, task_name in enumerate(row[1:]):
                        if task_name and task_name.strip() and i < len(dates):
                            worker.x_tasks[dates[i]] = task_name.strip()
                        
    except Exception as e:
        print(f"Error loading X tasks from CSV: {e}")


def reset_x_tasks_data(workers: List[EnhancedWorker]):
    """Reset X task data for all workers"""
    for worker in workers:
        worker.x_tasks = {}
        worker.clear_schedule()  # Clear pre-computed schedules too


def load_y_tasks_for_worker(worker: EnhancedWorker, y_tasks_data: Dict[str, Dict[str, str]]):
    """Load Y tasks for a specific worker from parsed data"""
    if worker.name in y_tasks_data:
        worker.y_tasks = {}
        worker.y_task_counts = {
            "Supervisor": 0,
            "C&N Driver": 0,
            "C&N Escort": 0,
            "Southern Driver": 0,
            "Southern Escort": 0
        }
        
        for date_str, task_name in y_tasks_data[worker.name].items():
            try:
                task_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                worker.assign_y_task(task_date, task_name)
            except ValueError:
                continue
                    
    
# Backward compatibility
Worker = EnhancedWorker
