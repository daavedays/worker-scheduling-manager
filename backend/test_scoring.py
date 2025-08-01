#!/usr/bin/env python3
"""
Quick test to verify the scoring system is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date, timedelta
from scheduler_engine import SchedulerEngine
from worker import load_workers_from_json

def test_scoring():
    """Test the scoring system"""
    
    print("=== TESTING SCORING SYSTEM ===\n")
    
    # Load workers
    workers = load_workers_from_json('../data/worker_data.json')
    
    # Find Worker 12 and Worker 30
    worker_12 = None
    worker_30 = None
    
    for worker in workers:
        if worker.id == "1000012":
            worker_12 = worker
        elif worker.id == "1000030":
            worker_30 = worker
    
    if not worker_12 or not worker_30:
        print("❌ Could not find Worker 12 or Worker 30")
        return
    
    print(f"Worker 12: Score={worker_12.score}, Seniority={worker_12.seniority}")
    print(f"Worker 30: Score={worker_30.score}, Seniority={worker_30.seniority}")
    print()
    
    # Create scheduler engine
    start_date = date(2025, 7, 6)
    end_date = date(2025, 7, 19)
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # Test scoring for a specific day and task
    test_date = date(2025, 7, 6)
    test_task = "Supervisor"
    
    print(f"Testing scoring for {test_task} on {test_date}:")
    print()
    
    # Get available workers
    available_workers = engine._get_available_workers_for_day(test_date)
    print(f"Available workers: {len(available_workers)}")
    
    # Calculate qualification scarcity
    y_tasks = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    qualification_scarcity = engine._calculate_qualification_scarcity(available_workers, y_tasks)
    print(f"Qualification scarcity: {qualification_scarcity}")
    print()
    
    # Test scoring for both workers
    for worker in [worker_12, worker_30]:
        if worker in available_workers:
            score = engine._calculate_y_task_score(worker, test_task, test_date, qualification_scarcity)
            print(f"{worker.name} score for {test_task}: {score}")
            
            # Break down the scoring
            base_score = int(worker.score) if worker.score is not None else 0
            base_impact = base_score // 20
            print(f"  Base score impact: {base_impact} (was {base_score})")
            
            # Scarcity bonus
            scarcity_score = qualification_scarcity.get(test_task, 1.0)
            scarcity_bonus = int(scarcity_score * 10) if scarcity_score > 2.0 else 0
            print(f"  Scarcity bonus: {scarcity_bonus}")
            
            # Seniority bonus
            seniority_bonus = 0
            if worker.seniority and worker.seniority != 'None':
                try:
                    seniority_value = int(worker.seniority) if isinstance(worker.seniority, (int, str)) else 0
                    seniority_bonus = seniority_value // 2
                except (ValueError, TypeError):
                    pass
            print(f"  Seniority bonus: {seniority_bonus}")
            
            print()
        else:
            print(f"{worker.name} is not available for {test_date}")
            print()
    
    print("✅ Scoring system test completed!")

if __name__ == "__main__":
    test_scoring() 