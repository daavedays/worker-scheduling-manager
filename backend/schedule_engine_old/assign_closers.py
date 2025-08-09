#!/usr/bin/env python3
"""
Weekend Closer Assignment Module
Enhanced with X-task proximity rules, Rituk priority, and intelligent interval adherence
"""

from datetime import date, timedelta
from typing import List, Tuple, Dict
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from worker import Worker


class CloserScheduler:
    """
    Weekend closer scheduler - assigns actual closing duties with enhanced X-task awareness
    """
    
    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.weekend_closers = {}  # Track assigned closers by week
    
    def assign_closers(self, start_date: date, end_date: date) -> List[Tuple[date, str]]:
        """
        Assign weekend closers based on closing intervals with enhanced X-task proximity rules
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            List of closing assignments (date, worker_name)
        """
        assignments = []
        current_date = start_date
        
        while current_date <= end_date:
            # Only process on Thursdays (start of weekend)
            if current_date.weekday() == 3:  # Thursday
                # Calculate week number
                week_start = current_date - timedelta(days=current_date.weekday())
                week_number = (week_start - start_date).days // 7
                
                # Only assign if we haven't already assigned a closer for this week
                if week_number not in self.weekend_closers:
                    chosen_worker = self._select_closer_for_week_enhanced(week_number, current_date)
                    
                    if chosen_worker:
                        # Assign closing for Thursday-Sunday
                        for i in range(4):
                            closing_date = current_date + timedelta(days=i)
                            if closing_date <= end_date:
                                chosen_worker.assign_closing(closing_date)
                                assignments.append((closing_date, chosen_worker.name))
                        
                        # Track this assignment
                        self.weekend_closers[week_number] = chosen_worker
                        print(f"Week {week_number}: {chosen_worker.name} assigned as closer")
            
            current_date += timedelta(days=1)
        
        return assignments
    
    def _select_closer_for_week_enhanced(self, week_number: int, current_date: date) -> Worker:
        """
        Select a worker to close this week with enhanced X-task proximity rules
        
        Args:
            week_number: Week number from start date
            current_date: Current Thursday date
            
        Returns:
            Selected worker for closing
        """
        # Get workers with closing intervals
        closing_workers = [w for w in self.workers if w.closing_interval > 0]
        
        # ENHANCED: X-task proximity filtering
        available_workers = self._filter_workers_by_x_task_proximity(closing_workers, current_date)
        
        if not available_workers:
            print(f"Warning: No workers available for closing week {week_number} due to X-task conflicts")
            return None
        
        # ENHANCED: Intelligent interval prioritization
        prioritized_workers = self._prioritize_workers_by_interval_status(available_workers, week_number)
        
        if not prioritized_workers:
            return None
        
        # Select best worker from prioritized list
        return self._select_best_worker_from_prioritized_list(prioritized_workers, week_number)
    
    def _filter_workers_by_x_task_proximity(self, workers: List[Worker], current_date: date) -> List[Worker]:
        """
        Filter workers based on X-task proximity rules
        
        RULES:
        1. Workers with X-tasks next week (following week) are COMPLETELY EXCLUDED
        2. Workers with X-tasks in 2 weeks are highly not preferred
        3. Workers with X-tasks in 3 weeks are not preferred but more preferred than 2 weeks
        """
        available_workers = []
        
        for worker in workers:
            # RULE 1: Completely exclude workers with X-tasks next week
            next_week_start = current_date + timedelta(days=7)
            if worker.has_x_task(next_week_start):
                continue
            
            # RULE 2 & 3: Check 2-week and 3-week X-tasks for penalties
            two_weeks_start = current_date + timedelta(days=14)
            three_weeks_start = current_date + timedelta(days=21)
            
            has_two_week_x_task = worker.has_x_task(two_weeks_start)
            has_three_week_x_task = worker.has_x_task(three_weeks_start)
            
            # Apply penalties but don't exclude completely
            if has_two_week_x_task:
                worker.temp_x_task_penalty = 100  # High penalty for 2-week X-tasks
            elif has_three_week_x_task:
                worker.temp_x_task_penalty = 50   # Medium penalty for 3-week X-tasks
            else:
                worker.temp_x_task_penalty = 0
            
            available_workers.append(worker)
        
        return available_workers
    
    def _prioritize_workers_by_interval_status(self, workers: List[Worker], week_number: int) -> List[Worker]:
        """
        Prioritize workers by their closing interval status
        
        PRIORITY ORDER:
        1. Overdue workers (highest priority)
        2. Due workers (medium priority)
        3. Not due workers (lowest priority)
        """
        overdue_workers = []
        due_workers = []
        not_due_workers = []
        
        for worker in workers:
            # Calculate overdue status
            last_closing_week = worker.get_last_closing_week()
            if last_closing_week is None:
                overdue_workers.append(worker)  # Never closed = always overdue
                continue
            
            delta = (week_number * 7) - (last_closing_week - date.today()).days
            overdue = delta - worker.closing_interval
            
            if overdue > 0:
                overdue_workers.append(worker)
            elif overdue == 0:
                due_workers.append(worker)
            else:
                not_due_workers.append(worker)
        
        # Return in priority order
        return overdue_workers + due_workers + not_due_workers
    
    def _select_best_worker_from_prioritized_list(self, prioritized_workers: List[Worker], week_number: int) -> Worker:
        """
        Select the best worker from the prioritized list using intelligent scoring
        
        For workers with similar closing intervals, use worker.score for comparison
        """
        if not prioritized_workers:
            return None
        
        # Group workers by closing interval
        interval_groups = {}
        for worker in prioritized_workers:
            interval = worker.closing_interval
            if interval not in interval_groups:
                interval_groups[interval] = []
            interval_groups[interval].append(worker)
        
        # For each interval group, select the best worker
        best_candidates = []
        for interval, workers in interval_groups.items():
            if len(workers) == 1:
                best_candidates.append(workers[0])
            else:
                # Multiple workers with same interval - use worker.score for comparison
                best_worker = min(workers, key=lambda w: w.score if w.score is not None else float('inf'))
                best_candidates.append(best_worker)
        
        # Among best candidates from each interval, select based on comprehensive scoring
        return self._select_worker_by_comprehensive_score(best_candidates, week_number)
    
    def _select_worker_by_comprehensive_score(self, candidates: List[Worker], week_number: int) -> Worker:
        """
        Select worker using comprehensive scoring system
        """
        if not candidates:
            return None
        
        worker_scores = []
        for worker in candidates:
            score = self._calculate_comprehensive_closer_score(worker, week_number)
            worker_scores.append((worker, score))
        
        # Sort by score (lower is better)
        worker_scores.sort(key=lambda x: x[1])
        
        return worker_scores[0][0] if worker_scores else None
    
    def _calculate_comprehensive_closer_score(self, worker: Worker, week_number: int) -> float:
        """
        Calculate comprehensive score for closer assignment (lower is better)
        """
        score = 0
        
        # Base score: closing history count (lower is better)
        # NOT GOOD!
        # closing_count = len(worker.closing_history)
        # score += closing_count * 5.0
        
        # X-task proximity penalty (from filtering)
        score += getattr(worker, 'temp_x_task_penalty', 0)
        
        # Worker score consideration (higher score = more overworked = should close less)
        if worker.score is not None and float('-inf') < worker.score < float('inf'):
            score -= worker.score  # Negative because lower score is better
        
        # Qualification scarcity bonus (fewer qualifications = higher priority)
        qualification_count = len(worker.qualifications)
        #TODO: Ensure this is updated when qualifications are updated
        qualification_bonus = (5 - qualification_count) * 10.0
        score += qualification_bonus
        
        # Recent closing penalty
        recent_closing_penalty = 0
        if worker.closing_history:
            last_closing = max(worker.closing_history)
            days_since_last = (date.today() - last_closing).days
            if days_since_last < 14:  # Within 2 weeks
                recent_closing_penalty = 20.0
        score += recent_closing_penalty
        
        return score
    
    def assign_y_tasks_for_rituk_workers(self, weekend_date: date, y_tasks: List[str]) -> List[Tuple[date, str, str]]:
        """
        NEW: Assign Y-tasks to workers with Rituk on weekends using scarcity function
        
        Args:
            weekend_date: Thursday date of the weekend
            y_tasks: List of Y-tasks to assign
            
        Returns:
            List of Y-task assignments (date, task, worker_name)
        """
        assignments = []
        
        # Find workers with Rituk on this weekend
        rituk_workers = []
        for worker in self.workers:
            for i in range(4):  # Thursday to Sunday
                check_date = weekend_date + timedelta(days=i)
                if check_date in worker.x_tasks and worker.x_tasks[check_date] == "Rituk":
                    rituk_workers.append(worker)
                    break
        
        if not rituk_workers:
            return assignments
        
        # Calculate task scarcity for prioritization
        task_scarcity = self._calculate_task_scarcity(y_tasks)
        
        # Sort tasks by scarcity (most scarce first)
        sorted_tasks = sorted(y_tasks, key=lambda task: task_scarcity.get(task, 1.0), reverse=True)
        
        # Assign tasks to Rituk workers using scarcity-based priority
        for i, task in enumerate(sorted_tasks):
            if i < len(rituk_workers):
                worker = rituk_workers[i]
                
                # Assign Y-task for Thursday-Sunday
                for j in range(4):
                    task_date = weekend_date + timedelta(days=j)
                    if task_date not in worker.y_tasks:
                        worker.assign_y_task(task_date, task)
                        assignments.append((task_date, task, worker.name))
        
        return assignments
    
    def _calculate_task_scarcity(self, tasks: List[str]) -> Dict[str, float]:
        """
        Calculate scarcity of each task (higher = more scarce)
        """
        scarcity = {}
        total_workers = len(self.workers)
        
        for task in tasks:
            qualified_count = sum(1 for w in self.workers if task in w.qualifications)
            scarcity[task] = total_workers / qualified_count if qualified_count > 0 else float('inf')
        
        return scarcity
    
    def get_closing_stats(self) -> Dict:
        """
        Get closing assignment statistics
        """
        closing_counts = {}
        for worker in self.workers:
            closing_counts[worker.name] = len(worker.closing_history)
        
        counts = list(closing_counts.values())
        if not counts:
            return {"error": "No closing assignments"}
        
        avg_closings = sum(counts) / len(counts)
        min_closings = min(counts)
        max_closings = max(counts)
        variance = sum((x - avg_closings) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5
        fairness_ratio = max_closings / min_closings if min_closings > 0 else float('inf')
        
        # Calculate interval adherence
        interval_adherence = self._calculate_interval_adherence()
        
        return {
            "average_closings": avg_closings,
            "min_closings": min_closings,
            "max_closings": max_closings,
            "standard_deviation": std_dev,
            "fairness_ratio": fairness_ratio,
            "fairness_assessment": self._assess_fairness(fairness_ratio),
            "interval_adherence": interval_adherence,
            "closing_distribution": closing_counts
        }
    
    def _calculate_interval_adherence(self) -> Dict:
        """
        Calculate how well the assignments adhere to closing intervals
        """
        adherence_data = {}
        
        for worker in self.workers:
            if worker.closing_interval <= 0:
                continue
            
            # Calculate expected vs actual closings
            total_weeks = 13  # Approximate for our test period
            expected_closings = total_weeks // worker.closing_interval
            actual_closings = len(worker.closing_history)
            
            accuracy = actual_closings / expected_closings if expected_closings > 0 else 0
            
            adherence_data[worker.name] = {
                "interval": worker.closing_interval,
                "expected": expected_closings,
                "actual": actual_closings,
                "accuracy": accuracy
            }
        
        return adherence_data
    
    def _assess_fairness(self, ratio: float) -> str:
        """
        Assess fairness based on ratio
        """
        if ratio < 2.0:
            return "EXCELLENT"
        elif ratio < 3.0:
            return "GOOD"
        elif ratio < 5.0:
            return "ACCEPTABLE"
        else:
            return "POOR" 