from datetime import date, timedelta
from typing import List, Dict
from collections import defaultdict
from backend.worker import Worker

class SchedulerEngine:
    def __init__(self, workers: List[Worker], start_date: date, end_date: date):
        self.workers = workers
        self.start_date = start_date
        self.end_date = end_date
        self.schedule: Dict[date, Dict[str, str]] = {}  # date -> task name -> worker id
        self.closing_history = defaultdict(list)  # {worker_name: [date1, date2, ...]}

    def get_available_workers(self, task_name: str, day: date) -> List[Worker]:
        eligible = [w for w in self.workers
                    if task_name in w.qualifications and w.is_available_for_y_task(day)]
        eligible.sort(key=lambda w: (w.long_timer, len(w.y_tasks)))
        return eligible

    def assign_y_tasks_for_day(self, day: date):
        # TODO: Add a lookback feature, that will try and assign each soldier a y task once or at most twice a week.
        self.schedule[day] = {}
        # TODO: make a file where the tasks can be imported from, edited and removed. 
        for task in ["Southern Driver", "Southern Escort", "C&N Driver", "C&N Escort", "Supervisor"]:
            candidates = self.get_available_workers(task, day)
            if candidates:
                chosen = candidates[0]
                chosen.assign_y_task(day, task)
                self.schedule[day][task] = chosen.name
            else:
                self.schedule[day][task] = None  # No eligible worker found

    def assign_y_tasks(self):
        day = self.start_date
        while day <= self.end_date:
            if day.weekday() < 5:  # Sunday to Thursday only
                self.assign_y_tasks_for_day(day)
            day += timedelta(days=1)

    def get_weeks_since_last_close(self, worker, weekend_date):
        closings = self.closing_history.get(worker.name, [])
        if not closings:
            return float('inf')
        last = max(closings)
        return (weekend_date - last).days // 7

    def has_x_task_during(self, worker, start, end):
        return any(start <= d <= end for d in worker.x_tasks)

    def should_close_this_weekend(self, worker, current_weekend):
        interval = worker.closing_interval
        closings = self.closing_history.get(worker.name, [])
        if not closings:
            return True  # never closed? time to work
        last_closing = max(closings)
        delta_weeks = (current_weekend - last_closing).days // 7
        return delta_weeks >= interval

    def assign_weekend_closers(self, start_date, end_date):
        current = start_date
        while current <= end_date:
            if current.weekday() == 4:  # Friday
                weekend = current
                closers = []
                candidates = [w for w in self.workers if not w.long_timer]
                # Remove anyone with an x task that weekend
                candidates = [w for w in candidates if not self.has_x_task_during(w, weekend, weekend + timedelta(days=1))]
                # Sort by fairness — how long since last close, descending
                candidates.sort(key=lambda w: self.get_weeks_since_last_close(w, weekend), reverse=True)
                for w in candidates:
                    if self.should_close_this_weekend(w, weekend):
                        closers.append(w)
                        self.closing_history[w.name].append(weekend)
                        break  # only assign exactly one for now
                # Add to schedule
                self.schedule[weekend] = {"weekend_closer": closers[0].name if closers else "No closer"}
                self.schedule[weekend + timedelta(days=1)] = {"weekend_closer": closers[0].name if closers else "No closer"}
            current += timedelta(days=1) 