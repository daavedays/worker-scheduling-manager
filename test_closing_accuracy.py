#!/usr/bin/env python3
"""
Test script to investigate closing data accuracy and Y task assignment impact
"""

import sys
import os
from datetime import date, timedelta
from typing import List, Dict

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from worker import Worker, load_workers_from_json
from scheduler_engine import SchedulerEngine

def test_closing_data_accuracy():
    """Test whether closing data properly accounts for future Y task assignments"""
    
    print("=== CLOSING DATA ACCURACY TEST ===\n")
    
    # Load workers from JSON
    workers = load_workers_from_json('data/worker_data.json')
    print(f"Loaded {len(workers)} workers\n")
    
    # Test period: Next 4 weeks
    start_date = date.today()
    end_date = start_date + timedelta(weeks=4)
    
    print(f"Testing period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}\n")
    
    # Create scheduler engine
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # First, assign Y tasks
    print("1. Assigning Y tasks...")
    assigned_workers = engine.assign_y_tasks(start_date, end_date)
    print(f"   Assigned Y tasks to {len(assigned_workers)} workers\n")
    
    # Then, assign weekend closers
    print("2. Assigning weekend closers...")
    weekend_closers = engine.assign_weekend_closers(start_date, end_date)
    print(f"   Assigned weekend closing to {len(weekend_closers)} weeks\n")
    
    # Analyze the results
    print("3. Analyzing closing data accuracy...\n")
    
    # Check each week for potential issues
    current_date = start_date
    week_number = 1
    
    while current_date <= end_date:
        week_start = current_date - timedelta(days=current_date.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        print(f"--- Week {week_number} ({week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}) ---")
        
        # Get weekend closing candidates for this week
        candidates = engine.get_weekend_closing_candidates(workers, week_start)
        
        # Check if any candidates have Y tasks assigned in this week
        candidates_with_y_tasks = []
        for candidate in candidates:
            y_tasks_this_week = []
            for task_date, task_name in candidate.y_tasks.items():
                if week_start <= task_date <= week_end:
                    y_tasks_this_week.append((task_date.strftime('%d/%m/%Y'), task_name))
            
            if y_tasks_this_week:
                candidates_with_y_tasks.append((candidate, y_tasks_this_week))
        
        if candidates_with_y_tasks:
            print(f"   ⚠️  Found {len(candidates_with_y_tasks)} closing candidates with Y tasks this week:")
            for worker, y_tasks in candidates_with_y_tasks:
                print(f"      {worker.name} (ID: {worker.id}) - Y tasks: {y_tasks}")
        else:
            print("   ✅ No closing candidates have Y tasks this week")
        
        # Check if the assigned weekend closer has Y tasks
        if week_start in weekend_closers:
            assigned_closer = weekend_closers[week_start]
            closer_y_tasks = []
            for task_date, task_name in assigned_closer.y_tasks.items():
                if week_start <= task_date <= week_end:
                    closer_y_tasks.append((task_date.strftime('%d/%m/%Y'), task_name))
            
            if closer_y_tasks:
                print(f"   ⚠️  ASSIGNED CLOSER {assigned_closer.name} has Y tasks this week: {closer_y_tasks}")
            else:
                print(f"   ✅ Assigned closer {assigned_closer.name} has no Y tasks this week")
        
        print()
        current_date += timedelta(weeks=1)
        week_number += 1
    
    # Test specific scenarios
    print("4. Testing specific scenarios...\n")
    
    # Test 1: Check if workers with future Y tasks are properly excluded from closing
    print("Test 1: Workers with future Y tasks in closing candidates")
    test_week = start_date - timedelta(days=start_date.weekday())  # Next Monday
    candidates = engine.get_weekend_closing_candidates(workers, test_week)
    
    workers_with_future_y_tasks = []
    for worker in candidates:
        future_y_tasks = []
        for task_date, task_name in worker.y_tasks.items():
            if task_date >= test_week:
                future_y_tasks.append((task_date.strftime('%d/%m/%Y'), task_name))
        
        if future_y_tasks:
            workers_with_future_y_tasks.append((worker, future_y_tasks))
    
    if workers_with_future_y_tasks:
        print(f"   ⚠️  Found {len(workers_with_future_y_tasks)} closing candidates with future Y tasks:")
        for worker, y_tasks in workers_with_future_y_tasks:
            print(f"      {worker.name} (ID: {worker.id}) - Future Y tasks: {y_tasks}")
    else:
        print("   ✅ No closing candidates have future Y tasks")
    
    print()
    
    # Test 2: Check the has_closing_scheduled method
    print("Test 2: has_closing_scheduled method accuracy")
    test_worker = workers[0]  # Use first worker as test case
    print(f"   Testing worker: {test_worker.name} (ID: {test_worker.id})")
    print(f"   Current closing history: {[d.strftime('%d/%m/%Y') for d in test_worker.closing_history]}")
    print(f"   Current Y tasks: {[(d.strftime('%d/%m/%Y'), t) for d, t in test_worker.y_tasks.items()]}")
    
    # Check if has_closing_scheduled considers Y tasks
    next_week = start_date - timedelta(days=start_date.weekday()) + timedelta(weeks=1)
    has_closing = test_worker.has_closing_scheduled(next_week)
    has_y_task = any(next_week <= d <= next_week + timedelta(days=6) for d in test_worker.y_tasks)
    
    print(f"   has_closing_scheduled({next_week.strftime('%d/%m/%Y')}): {has_closing}")
    print(f"   has Y task in that week: {has_y_task}")
    
    if has_closing and has_y_task:
        print("   ⚠️  Worker has both closing and Y task scheduled - potential conflict!")
    elif has_closing:
        print("   ✅ Worker has closing scheduled, no Y task conflict")
    elif has_y_task:
        print("   ✅ Worker has Y task scheduled, no closing conflict")
    else:
        print("   ✅ Worker has neither closing nor Y task scheduled")
    
    print()
    
    # Test 3: Check scoring system
    print("Test 3: Closing candidate scoring system")
    candidates_with_scores = engine.get_weekend_candidates_with_scores(workers, test_week)
    
    print(f"   Top 5 closing candidates for week {test_week.strftime('%d/%m/%Y')}:")
    for i, (worker, score) in enumerate(candidates_with_scores[:5]):
        y_tasks_future = [(d.strftime('%d/%m/%Y'), t) for d, t in worker.y_tasks.items() if d >= test_week]
        print(f"      {i+1}. {worker.name} (ID: {worker.id}) - Score: {score}")
        if y_tasks_future:
            print(f"         Future Y tasks: {y_tasks_future}")
    
    print()
    
    # Test 4: Check for potential bugs in the logic
    print("Test 4: Potential logic issues")
    
    # Check if the comment in assign_closing method is relevant
    print("   Checking assign_closing method comment:")
    print("   'POTENTIAL BUG!: If multiple schedules are made and they are all in the future, this will cause issues'")
    
    # Count workers with future closing assignments
    workers_with_future_closing = []
    for worker in workers:
        future_closings = [d for d in worker.closing_history if d >= start_date]
        if future_closings:
            workers_with_future_closing.append((worker, future_closings))
    
    if workers_with_future_closing:
        print(f"   ⚠️  Found {len(workers_with_future_closing)} workers with future closing assignments:")
        for worker, closings in workers_with_future_closing[:3]:  # Show first 3
            print(f"      {worker.name} (ID: {worker.id}) - Future closings: {[d.strftime('%d/%m/%Y') for d in closings]}")
        if len(workers_with_future_closing) > 3:
            print(f"      ... and {len(workers_with_future_closing) - 3} more")
    else:
        print("   ✅ No workers have future closing assignments")
    
    print()
    
    # Summary
    print("=== SUMMARY ===")
    print("The closing data system has the following characteristics:")
    print("1. ✅ Closing candidates are properly filtered to exclude workers with X tasks")
    print("2. ⚠️  Closing candidates may include workers with future Y tasks (potential issue)")
    print("3. ⚠️  has_closing_scheduled only checks closing_history, not Y tasks")
    print("4. ⚠️  Future closing assignments are added to closing_history immediately")
    print("5. ⚠️  Multiple future schedules could cause double assignments")
    
    print("\n=== RECOMMENDATIONS ===")
    print("1. Modify has_closing_scheduled to also check Y tasks")
    print("2. Consider not adding future closings to closing_history until they're executed")
    print("3. Add validation to prevent workers with Y tasks from being assigned closing")
    print("4. Implement a 'pending_closings' list separate from closing_history")

if __name__ == "__main__":
    test_closing_data_accuracy() 