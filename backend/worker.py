from datetime import datetime, timedelta
from typing import List
import json

class Worker:
    def __init__(self, id, name, start_date, qualifications, closing_interval, officer=False, seniority=None, score=None, long_timer=False):
        self.id = id
        self.name = name
        self.start_date = start_date  # datetime.date
        self.qualifications = qualifications  # List[str]
        self.closing_interval = closing_interval  # int
        self.x_tasks = {}  # date -> True if assigned
        self.y_tasks = {}  # date -> task name
        self.closing_history = []  # list of dates when closed weekend
        self.officer = officer # if rank == mandatory, officer = False. 
        self.seniority = seniority  # Add this line
        self.score = score or 0  # how many points the worker has, default to 0
        self.long_timer = long_timer  # Add this line

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

    def assign_closing(self, date):
        #TODO: Before publication,
        #  ensure the closing history is updated only after soldiers' closing date is before current date.
        # POTENTIAL BUG!: If multiple schedules are made and they are all in the future, this will cause issues, 
        # since the soldier could be assigned for 2 weekends in a row. 
        self.closing_history.append(date)

    def is_available_for_y_task(self, day):
        # Returns True if not already assigned a Y task on this day
        return day not in self.y_tasks

    def has_x_task(self, week_start_date):
        """
        Check if worker has X task during the specified week (week_start_date to week_start_date + 6 days)
        """
        week_end_date = week_start_date + timedelta(days=6)
        return any(week_start_date <= d <= week_end_date for d in self.x_tasks)

    def has_specific_x_task(self, week_start_date, task_name):
        """
        Check if worker has a specific X task during the specified week
        """
        week_end_date = week_start_date + timedelta(days=6)
        # For now, we'll check if the worker has any X task during this week
        # In the future, this could be enhanced to check specific task names
        # when the X task system supports task names
        return any(week_start_date <= d <= week_end_date for d in self.x_tasks)

    def had_x_task(self, week_start_date):
        """
        Check if worker had X task during the specified week (week_start_date to week_start_date + 6 days)
        """
        week_end_date = week_start_date + timedelta(days=6)
        return any(week_start_date <= d <= week_end_date for d in self.x_tasks)

    def has_closing_scheduled(self, week_start_date):
        """
        Check if worker has closing scheduled during the specified week
        """
        week_end_date = week_start_date + timedelta(days=6)
        return any(week_start_date <= d <= week_end_date for d in self.closing_history)

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
        w = Worker(
            id=sid,
            name=hebrew_name,
            start_date=start_date,
            qualifications=item.get('qualifications', []),
            closing_interval=closing_interval,
            officer=item.get('officer', False),
            seniority=item.get('seniority'),
            score=item.get('score'),
            long_timer=long_timer
        )
        # Optionally load x_tasks, y_tasks, closing_history if present
        if 'x_tasks' in item:
            for d in item['x_tasks']:
                try:
                    w.x_tasks[datetime.strptime(d, '%Y-%m-%d').date()] = True
                except Exception:
                    pass
        if 'y_tasks' in item:
            for d, t in item['y_tasks'].items():
                try:
                    w.y_tasks[datetime.strptime(d, '%Y-%m-%d').date()] = t
                except Exception:
                    pass
        if 'closing_history' in item:
            try:
                w.closing_history = [datetime.strptime(d, '%Y-%m-%d').date() for d in item['closing_history']]
            except Exception:
                w.closing_history = []
        workers.append(w)
    return workers 