#!/usr/bin/env python3
"""
Weekday Y Task Assignment Module
Complete separation system - workers assigned only to their rare qualifications
"""

from datetime import date, timedelta
from typing import List, Tuple, Dict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from worker import Worker


class WeekdayScheduler:
    """
    Weekday Y task scheduler - complete separation system for fair distribution
    """
    
    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        # Track task assignments for separation enforcement
        self.task_assignment_counts = {task: {} for task in self.y_tasks}
        # Calculate task scarcity for separation system
        self.task_scarcity = self._calculate_task_scarcity()
        # Categorize workers by qualification scarcity
        self.worker_categories = self._categorize_workers()
    
    def assign_y_tasks(self, start_date: date, end_date: date) -> List[Tuple[date, str, str]]:
        """
        Assign Y tasks for weekdays (Sunday to Wednesday)
        Uses complete separation system for fair distribution
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            List of assignments (date, task, worker_name)
        """
        assignments = []
        current_date = start_date
        
        while current_date <= end_date:
            # Skip weekends (Thursday and later)
            if current_date.weekday() >= 4:  # Thursday (4) to Sunday (6)
                current_date += timedelta(days=1)
                continue
            
            # Assign 5 Y tasks for this day using separation system
            day_assignments = self._assign_day_tasks_separation(current_date)
            assignments.extend(day_assignments)
            
            current_date += timedelta(days=1)
        
        return assignments
    
    def _assign_day_tasks_separation(self, current_date: date) -> List[Tuple[date, str, str]]:
        """
        Assign all 5 Y tasks for a specific day using separation system
        """
        assignments = []
        assigned_workers = set()  # Track workers assigned this day
        
        # Sort tasks by scarcity (most scarce first) - rare qualifications get priority
        task_priority = sorted(self.y_tasks, key=lambda task: self.task_scarcity[task], reverse=True)
        
        for task in task_priority:
            # Find best worker for this task using separation system
            best_worker = self._find_worker_by_separation(current_date, task, assigned_workers)
            
            if best_worker:
                best_worker.assign_y_task(current_date, task)
                assignments.append((current_date, task, best_worker.name))
                assigned_workers.add(best_worker)
                
                # Update task assignment counts
                if best_worker.name not in self.task_assignment_counts[task]:
                    self.task_assignment_counts[task][best_worker.name] = 0
                self.task_assignment_counts[task][best_worker.name] += 1
            else:
                print(f"Warning: No available worker for {task} on {current_date}")
        
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
    
    def _categorize_workers(self) -> Dict[str, List[Worker]]:
        """
        Categorize workers by their qualification scarcity
        """
        categories = {
            "supervisor_only": [],      # Workers with Supervisor + few other qualifications
            "cn_driver_only": [],       # Workers with C&N Driver + few other qualifications  
            "cn_escort_only": [],       # Workers with C&N Escort + few other qualifications
            "southern_driver_only": [], # Workers with Southern Driver + few other qualifications
            "southern_escort_only": [], # Workers with ONLY Southern Escort
            "highly_qualified": []      # Workers with many qualifications (4-5)
        }
        
        for worker in self.workers:
            qualifications = worker.qualifications
            
            if "Supervisor" in qualifications and len(qualifications) <= 2:
                categories["supervisor_only"].append(worker)
            elif "C&N Driver" in qualifications and len(qualifications) <= 3:
                categories["cn_driver_only"].append(worker)
            elif "C&N Escort" in qualifications and len(qualifications) <= 3:
                categories["cn_escort_only"].append(worker)
            elif "Southern Driver" in qualifications and len(qualifications) <= 3:
                categories["southern_driver_only"].append(worker)
            elif len(qualifications) == 1 and "Southern Escort" in qualifications:
                categories["southern_escort_only"].append(worker)
            else:
                categories["highly_qualified"].append(worker)
        
        return categories
    
    def _find_worker_by_separation(self, current_date: date, task: str, assigned_workers: set) -> Worker:
        """
        Find worker using separation system - prioritize workers with rare qualifications
        """
        # Get all qualified workers for this task
        qualified_workers = []
        for worker in self.workers:
            if (task in worker.qualifications and 
                current_date not in worker.y_tasks and
                worker not in assigned_workers):
                qualified_workers.append(worker)
        
        if not qualified_workers:
            return None
        
        # Calculate separation score for each worker
        best_worker = None
        best_score = float('inf')
        
        for worker in qualified_workers:
            score = self._calculate_separation_score(worker, current_date, task)
            
            if score < best_score:
                best_score = score
                best_worker = worker
        
        return best_worker
    
    def _calculate_separation_score(self, worker: Worker, current_date: date, task: str) -> float:
        """
        Calculate separation-based fairness score (lower is better)
        Prioritizes workers with rare qualifications for their specific tasks
        """
        # Base score: total Y tasks (lower is better)
        total_y_tasks = len(worker.y_tasks)
        
        # SEPARATION BONUS: Workers with rare qualifications get very high priority for those tasks
        separation_bonus = 0
        worker_qualifications = worker.qualifications
        
        if task == "Supervisor":
            if worker in self.worker_categories["supervisor_only"]:
                separation_bonus = -500  # Very high priority for Supervisor-only workers
            elif worker in self.worker_categories["highly_qualified"]:
                separation_bonus = 200   # Penalty for highly qualified workers doing Supervisor
        elif task in ["C&N Driver", "C&N Escort"]:
            if task == "C&N Driver" and worker in self.worker_categories["cn_driver_only"]:
                separation_bonus = -400  # High priority for C&N Driver-only workers
            elif task == "C&N Escort" and worker in self.worker_categories["cn_escort_only"]:
                separation_bonus = -400  # High priority for C&N Escort-only workers
            elif worker in self.worker_categories["highly_qualified"]:
                separation_bonus = 150   # Penalty for highly qualified workers doing C&N tasks
        elif task == "Southern Driver":
            if worker in self.worker_categories["southern_driver_only"]:
                separation_bonus = -300  # Medium priority for Southern Driver-only workers
            elif worker in self.worker_categories["highly_qualified"]:
                separation_bonus = 100   # Penalty for highly qualified workers doing Southern Driver
        elif task == "Southern Escort":
            if worker in self.worker_categories["southern_escort_only"]:
                separation_bonus = -200  # Priority for Southern Escort-only workers
            elif worker in self.worker_categories["highly_qualified"]:
                separation_bonus = 50    # Small penalty for highly qualified workers doing Southern Escort
        
        # Task-specific assignment count (prefer workers with fewer assignments for this task)
        task_assignments = self.task_assignment_counts[task].get(worker.name, 0)
        task_assignment_penalty = task_assignments * 50.0
        
        # Recent workload penalty (last 7 days)
        recent_tasks = 0
        for i in range(7):
            check_date = current_date - timedelta(days=i)
            if check_date in worker.y_tasks:
                recent_tasks += 1
        
        # Calculate final score
        score = (
            total_y_tasks * 10.0 +           # Primary factor
            separation_bonus +                # Separation bonus/penalty
            task_assignment_penalty +         # Task-specific balance
            recent_tasks * 5.0               # Recent workload
        )
        
        return score
    
    def get_distribution_stats(self) -> Dict:
        """
        Get distribution statistics for analysis
        """
        task_counts = {}
        for worker in self.workers:
            task_counts[worker.name] = len(worker.y_tasks)
        
        counts = list(task_counts.values())
        if not counts:
            return {"error": "No tasks assigned"}
        
        avg_tasks = sum(counts) / len(counts)
        min_tasks = min(counts)
        max_tasks = max(counts)
        variance = sum((x - avg_tasks) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        fairness_ratio = max_tasks / min_tasks if min_tasks > 0 else float('inf')
        
        return {
            "average_tasks": avg_tasks,
            "min_tasks": min_tasks,
            "max_tasks": max_tasks,
            "standard_deviation": std_dev,
            "fairness_ratio": fairness_ratio,
            "fairness_assessment": self._assess_fairness(fairness_ratio),
            "task_distribution": task_counts
        }
    
    def _assess_fairness(self, ratio: float) -> str:
        """
        Assess fairness based on ratio
        """
        if ratio < 1.5:
            return "EXCELLENT"
        elif ratio < 2.0:
            return "GOOD"
        elif ratio < 3.0:
            return "ACCEPTABLE"
        else:
            return "POOR" 