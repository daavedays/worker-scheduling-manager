#!/usr/bin/env python3
"""
Weekend Y Task Assignment Module
Quota system with closing interval respect for fair distribution
"""

from datetime import date, timedelta
from typing import List, Tuple, Dict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from worker import Worker


class WeekendScheduler:
    """
    Weekend Y task scheduler - quota system with closing interval respect
    """
    
    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        # Track weekend task assignments for quota enforcement
        self.weekend_task_counts = {task: {} for task in self.y_tasks}
        # Calculate task scarcity for quota system
        self.task_scarcity = self._calculate_task_scarcity()
    
    def assign_y_tasks(self, start_date: date, end_date: date) -> List[Tuple[date, str, str]]:
        """
        Assign Y tasks for weekends (Thursday to Sunday)
        Uses quota system with closing interval respect
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            List of assignments (date, task, worker_name)
        """
        assignments = []
        current_date = start_date
        
        while current_date <= end_date:
            # Only process on Thursdays (start of weekend)
            if current_date.weekday() == 3:  # Thursday
                # Calculate week number
                week_start = current_date - timedelta(days=current_date.weekday())
                week_number = (week_start - start_date).days // 7
                
                # Assign weekend tasks using quota system
                weekend_assignments = self._assign_weekend_tasks_quota(current_date, week_number)
                assignments.extend(weekend_assignments)
            
            current_date += timedelta(days=1)
        
        return assignments
    
    def _assign_weekend_tasks_quota(self, thursday_date: date, week_number: int) -> List[Tuple[date, str, str]]:
        """
        Assign all weekend tasks (Thursday-Sunday) using quota system
        """
        assignments = []
        
        # Select 5 workers for this weekend using quota system
        weekend_workers = self._select_weekend_workers_quota(week_number, thursday_date)
        
        # Assign each worker to a Y task for the entire weekend
        for i, task in enumerate(self.y_tasks):
            if i < len(weekend_workers):
                worker = weekend_workers[i]
                
                # Assign Y task for Thursday-Sunday (4 days)
                for j in range(4):
                    task_date = thursday_date + timedelta(days=j)
                    
                    # Check if worker already has a Y task on this date
                    if task_date not in worker.y_tasks:
                        worker.assign_y_task(task_date, task)
                        assignments.append((task_date, task, worker.name))
                        
                        # Update weekend task counts
                        if worker.name not in self.weekend_task_counts[task]:
                            self.weekend_task_counts[task][worker.name] = 0
                        self.weekend_task_counts[task][worker.name] += 1
                    else:
                        print(f"Warning: {worker.name} already has a Y task on {task_date}")
        
        return assignments
    
    def _calculate_task_scarcity(self) -> Dict[str, float]:
        """
        Calculate scarcity of each task (higher = more scarce)
        """
        scarcity = {}
        total_workers = len(self.workers)
        
        for task in self.y_tasks:
            qualified_count = sum(1 for w in self.workers if task in w.qualifications)
            scarcity[task] = total_workers / qualified_count if qualified_count > 0 else float('inf')
        
        return scarcity
    
    def _select_weekend_workers_quota(self, week_number: int, current_date: date) -> List[Worker]:
        """
        Select 5 workers for weekend using quota system
        
        Args:
            week_number: Week number from start date
            current_date: Current Thursday date
            
        Returns:
            List of 5 workers selected for weekend
        """
        # Get all workers with closing intervals
        closing_workers = [w for w in self.workers if w.closing_interval > 0]
        
        # Step 1: Find workers who are DUE to close this week
        due_workers = []
        for worker in closing_workers:
            if week_number % worker.closing_interval == 0:
                due_workers.append(worker)
        
        # Step 2: If we don't have enough due workers, add more based on quota system
        if len(due_workers) < 5:
            # Sort all closing workers by quota-based weekend score
            all_closing_workers = sorted(closing_workers, 
                                       key=lambda w: self._calculate_weekend_quota_score(w, current_date))
            
            for worker in all_closing_workers:
                if worker not in due_workers:
                    due_workers.append(worker)
                    if len(due_workers) >= 5:
                        break
        
        # Step 3: Sort due workers by quota-based weekend score
        due_workers.sort(key=lambda w: self._calculate_weekend_quota_score(w, current_date))
        
        # Select the 5 workers with best scores
        selected_workers = due_workers[:5]
        
        return selected_workers
    
    def _calculate_weekend_quota_score(self, worker: Worker, current_date: date) -> float:
        """
        Calculate quota-based fairness score for weekend assignment (lower is better)
        """
        # Count weekend tasks
        weekend_tasks = 0
        for task_date, task_name in worker.y_tasks.items():
            if task_date.weekday() >= 3:  # Thursday-Sunday
                weekend_tasks += 1
        
        # RARE QUALIFICATION BONUS: Workers with rare qualifications get priority
        rare_qualification_bonus = 0
        worker_qualifications = worker.qualifications
        
        # Check if worker has rare qualifications
        if "Supervisor" in worker_qualifications and len(worker_qualifications) <= 2:
            rare_qualification_bonus = -80  # High priority for Supervisor with few qualifications
        elif any(task in worker_qualifications for task in ["C&N Driver", "C&N Escort"]) and len(worker_qualifications) <= 3:
            rare_qualification_bonus = -60  # Medium priority for C&N tasks with few qualifications
        elif "Southern Driver" in worker_qualifications and len(worker_qualifications) <= 3:
            rare_qualification_bonus = -40  # Lower priority for Southern Driver with few qualifications
        elif len(worker_qualifications) == 1 and "Southern Escort" in worker_qualifications:
            rare_qualification_bonus = -20  # Priority for workers who ONLY have Southern Escort
        
        # Recent weekend workload penalty (last 4 weeks)
        recent_weekend_tasks = 0
        for i in range(4):
            check_week = current_date - timedelta(weeks=i)
            for j in range(4):  # Thursday-Sunday
                check_date = check_week + timedelta(days=j)
                if check_date in worker.y_tasks:
                    recent_weekend_tasks += 1
        
        # Task-specific weekend workload penalty
        weekend_task_specific = {}
        for task in self.y_tasks:
            weekend_task_specific[task] = 0
        
        for task_date, task_name in worker.y_tasks.items():
            if task_date.weekday() >= 3:  # Thursday-Sunday
                if task_name in weekend_task_specific:
                    weekend_task_specific[task_name] += 1
        
        # Calculate task-specific penalty
        task_specific_penalty = sum(weekend_task_specific.values()) * 10.0
        
        # Calculate final score
        score = (
            weekend_tasks * 12.0 +           # Primary factor
            rare_qualification_bonus +        # Rare qualification bonus
            recent_weekend_tasks * 6.0 +     # Recent weekend workload
            task_specific_penalty            # Task-specific balance
        )
        
        return score
    
    def get_weekend_stats(self) -> Dict:
        """
        Get weekend distribution statistics
        """
        weekend_task_counts = {}
        for worker in self.workers:
            weekend_tasks = 0
            for task_date, task_name in worker.y_tasks.items():
                if task_date.weekday() >= 3:  # Thursday-Sunday
                    weekend_tasks += 1
            weekend_task_counts[worker.name] = weekend_tasks
        
        counts = list(weekend_task_counts.values())
        if not counts:
            return {"error": "No weekend tasks assigned"}
        
        avg_weekend_tasks = sum(counts) / len(counts)
        min_weekend_tasks = min(counts)
        max_weekend_tasks = max(counts)
        variance = sum((x - avg_weekend_tasks) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        fairness_ratio = max_weekend_tasks / min_weekend_tasks if min_weekend_tasks > 0 else float('inf')
        
        return {
            "average_weekend_tasks": avg_weekend_tasks,
            "min_weekend_tasks": min_weekend_tasks,
            "max_weekend_tasks": max_weekend_tasks,
            "standard_deviation": std_dev,
            "fairness_ratio": fairness_ratio,
            "fairness_assessment": self._assess_fairness(fairness_ratio),
            "weekend_task_distribution": weekend_task_counts
        }
    
    def _assess_fairness(self, ratio: float) -> str:
        """
        Assess fairness based on ratio
        Note: Weekend fairness is different from weekday due to closing intervals
        """
        if ratio < 2.0:
            return "EXCELLENT"
        elif ratio < 3.0:
            return "GOOD"
        elif ratio < 5.0:
            return "ACCEPTABLE"
        else:
            return "POOR" 