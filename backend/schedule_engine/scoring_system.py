#!/usr/bin/env python3
"""
Scoring System Module
Fine-tuning layer on top of proven fair algorithms
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from worker import Worker


class ScoringSystem:
    """
    Scoring system for fine-tuning assignments
    Built on top of proven fair algorithms
    """
    
    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.score_weights = {
            "qualification_bonus": 15,      # Bonus for qualified workers
            "qualification_penalty": 2,     # Penalty for unqualified workers
            "seniority_bonus": 5,           # Bonus for senior workers
            "recent_task_penalty": 1,       # Penalty for recent tasks
            "workload_penalty": 2,          # Penalty for high workload
            "fairness_adjustment": 200      # Dominant fairness factor
        }
    
    def calculate_worker_score(self, worker: Worker, task: str, current_date: date) -> int:
        """
        Calculate score for a worker for a specific task
        
        Args:
            worker: Worker to score
            task: Task to assign
            current_date: Date of assignment
            
        Returns:
            Score (lower = better)
        """
        score = 0
        
        # Base fairness score (proven algorithm)
        score += self._calculate_fairness_score(worker, task, current_date)
        
        # Qualification scoring
        score += self._calculate_qualification_score(worker, task)
        
        # Seniority scoring
        score += self._calculate_seniority_score(worker)
        
        # Recent task penalties
        score += self._calculate_recent_task_penalty(worker, current_date)
        
        # Workload penalties
        score += self._calculate_workload_penalty(worker)
        
        return score
    
    def _calculate_fairness_score(self, worker: Worker, task: str, current_date: date) -> int:
        """
        Calculate fairness score (dominant factor)
        Based on proven "least tasks first" algorithm
        """
        # Count current tasks (Y tasks for Y assignments, closing for closing assignments)
        if task in ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]:
            # Y task assignment
            current_tasks = len(worker.y_tasks)
        else:
            # Closing assignment
            current_tasks = len(worker.closing_history)
        
        # Fairness adjustment (higher tasks = higher score = lower priority)
        fairness_adjustment = current_tasks * self.score_weights["fairness_adjustment"]
        
        return fairness_adjustment
    
    def _calculate_qualification_score(self, worker: Worker, task: str) -> int:
        """
        Calculate qualification-based score
        """
        score = 0
        
        if task in worker.qualifications:
            # Bonus for qualified workers
            score -= self.score_weights["qualification_bonus"]
        else:
            # Penalty for unqualified workers
            score += self.score_weights["qualification_penalty"]
        
        return score
    
    def _calculate_seniority_score(self, worker: Worker) -> int:
        """
        Calculate seniority-based score
        """
        score = 0
        
        # Convert seniority to number (if string)
        seniority = worker.seniority
        if isinstance(seniority, str):
            try:
                seniority = int(seniority)
            except (ValueError, TypeError):
                seniority = 0
        
        # Bonus for senior workers (lower score = higher priority)
        if seniority > 0:
            score -= seniority * self.score_weights["seniority_bonus"]
        
        return score
    
    def _calculate_recent_task_penalty(self, worker: Worker, current_date: date) -> int:
        """
        Calculate penalty for recent tasks
        """
        score = 0
        
        # Check for recent Y tasks (last 7 days)
        recent_y_tasks = 0
        for task_date in worker.y_tasks:
            if (current_date - task_date).days <= 7:
                recent_y_tasks += 1
        
        score += recent_y_tasks * self.score_weights["recent_task_penalty"]
        
        # Check for recent closing assignments (last 14 days)
        recent_closings = 0
        for closing_date in worker.closing_history:
            if (current_date - closing_date).days <= 14:
                recent_closings += 1
        
        score += recent_closings * self.score_weights["recent_task_penalty"]
        
        return score
    
    def _calculate_workload_penalty(self, worker: Worker) -> int:
        """
        Calculate workload penalty
        """
        score = 0
        
        # Total workload penalty
        total_tasks = len(worker.y_tasks) + len(worker.closing_history)
        score += total_tasks * self.score_weights["workload_penalty"]
        
        return score
    
    def get_scoring_analysis(self, worker: Worker, task: str, current_date: date) -> Dict:
        """
        Get detailed scoring analysis for debugging
        """
        fairness_score = self._calculate_fairness_score(worker, task, current_date)
        qualification_score = self._calculate_qualification_score(worker, task)
        seniority_score = self._calculate_seniority_score(worker)
        recent_penalty = self._calculate_recent_task_penalty(worker, current_date)
        workload_penalty = self._calculate_workload_penalty(worker)
        
        total_score = fairness_score + qualification_score + seniority_score + recent_penalty + workload_penalty
        
        return {
            "worker_name": worker.name,
            "task": task,
            "date": current_date,
            "fairness_score": fairness_score,
            "qualification_score": qualification_score,
            "seniority_score": seniority_score,
            "recent_penalty": recent_penalty,
            "workload_penalty": workload_penalty,
            "total_score": total_score,
            "current_y_tasks": len(worker.y_tasks),
            "current_closings": len(worker.closing_history),
            "qualifications": worker.qualifications,
            "seniority": worker.seniority
        }
    
    def update_weights(self, new_weights: Dict):
        """
        Update scoring weights
        """
        for key, value in new_weights.items():
            if key in self.score_weights:
                self.score_weights[key] = value
    
    def get_current_weights(self) -> Dict:
        """
        Get current scoring weights
        """
        return self.score_weights.copy() 