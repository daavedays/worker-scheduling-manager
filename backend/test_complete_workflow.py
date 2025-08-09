#!/usr/bin/env python3
"""
Test the complete scheduling workflow implementation.
"""

import sys
import os
from datetime import date, timedelta
from typing import List

# Add the backend directory to the path
sys.path.append(os.path.dirname(__file__))

from engine import SchedulingEngineV2, Y_TASK_TYPES
from worker import EnhancedWorker


def create_test_workers() -> List[EnhancedWorker]:
    """Create test workers with various qualifications."""
    workers = [
        EnhancedWorker(
            id="1",
            name="Alice",
            start_date=date(2024, 1, 1),
            qualifications=["Supervisor", "C&N Driver"],
            closing_interval=4,
            score=0.0
        ),
        EnhancedWorker(
            id="2", 
            name="Bob",
            start_date=date(2024, 1, 1),
            qualifications=["C&N Driver", "C&N Escort"],
            closing_interval=4,
            score=0.0
        ),
        EnhancedWorker(
            id="3",
            name="Charlie", 
            start_date=date(2024, 1, 1),
            qualifications=["Southern Driver", "Southern Escort"],
            closing_interval=4,
            score=0.0
        ),
        EnhancedWorker(
            id="4",
            name="Diana",
            start_date=date(2024, 1, 1), 
            qualifications=["Supervisor", "Southern Driver", "Southern Escort"],
            closing_interval=4,
            score=0.0
        ),
        EnhancedWorker(
            id="5",
            name="Eve",
            start_date=date(2024, 1, 1),
            qualifications=["C&N Escort", "Southern Escort"], 
            closing_interval=4,
            score=0.0
        )
    ]
    return workers


def test_weekday_only_scheduling():
    """Test weekday-only scheduling (no weekends)."""
    print("=== Testing Weekday-Only Scheduling ===")
    
    workers = create_test_workers()
    engine = SchedulingEngineV2()
    
    # Create weekday tasks for a week (Mon-Wed)
    start_date = date(2025, 1, 6)  # Monday
    end_date = date(2025, 1, 8)    # Wednesday
    
    weekday_tasks = {
        date(2025, 1, 6): ["Supervisor", "C&N Driver"],  # Monday
        date(2025, 1, 7): ["C&N Escort", "Southern Driver"],  # Tuesday
        date(2025, 1, 8): ["Southern Escort", "Supervisor"],  # Wednesday
    }
    
    result = engine.schedule_range(
        workers=workers,
        start=start_date,
        end=end_date,
        num_closers_per_weekend=2,
        weekday_tasks=weekday_tasks
    )
    
    print(f"Success: {result['success']}")
    print(f"Assignment errors: {len(result['assignment_errors'])}")
    
    if result['assignment_errors']:
        print("Errors:")
        for error in result['assignment_errors']:
            print(f"  {error['severity']}: {error['task_type']} on {error['date']} - {error['reason']}")
    
    print("Y-task assignments:")
    for date_str, assignments in result['y_tasks'].items():
        print(f"  {date_str}:")
        for task_type, worker_id in assignments:
            worker_name = next(w.name for w in workers if w.id == worker_id)
            print(f"    {task_type} -> {worker_name}")
    
    return result['success']


def test_weekend_scheduling():
    """Test weekend scheduling with closers and Y-tasks."""
    print("\n=== Testing Weekend Scheduling ===")
    
    workers = create_test_workers()
    engine = SchedulingEngineV2()
    
    # Create a weekend range
    start_date = date(2025, 1, 2)  # Thursday
    end_date = date(2025, 1, 4)    # Saturday
    
    result = engine.schedule_range(
        workers=workers,
        start=start_date,
        end=end_date,
        num_closers_per_weekend=2,
        weekday_tasks=None  # No weekday tasks
    )
    
    print(f"Success: {result['success']}")
    print(f"Assignment errors: {len(result['assignment_errors'])}")
    
    if result['assignment_errors']:
        print("Errors:")
        for error in result['assignment_errors']:
            print(f"  {error['severity']}: {error['task_type']} on {error['date']} - {error['reason']}")
    
    print("Closers:")
    for date_str, closer_ids in result['closers'].items():
        print(f"  {date_str}:")
        for closer_id in closer_ids:
            worker_name = next(w.name for w in workers if w.id == closer_id)
            print(f"    {worker_name}")
    
    print("Y-task assignments:")
    for date_str, assignments in result['y_tasks'].items():
        print(f"  {date_str}:")
        for task_type, worker_id in assignments:
            worker_name = next(w.name for w in workers if w.id == worker_id)
            print(f"    {task_type} -> {worker_name}")
    
    return result['success']


def test_mixed_scheduling():
    """Test mixed scheduling with both weekdays and weekends."""
    print("\n=== Testing Mixed Scheduling ===")
    
    workers = create_test_workers()
    engine = SchedulingEngineV2()
    
    # Create a range with both weekdays and weekends
    start_date = date(2025, 1, 6)  # Monday
    end_date = date(2025, 1, 11)   # Saturday
    
    weekday_tasks = {
        date(2025, 1, 6): ["Supervisor", "C&N Driver"],  # Monday
        date(2025, 1, 7): ["C&N Escort", "Southern Driver"],  # Tuesday
        date(2025, 1, 8): ["Southern Escort", "Supervisor"],  # Wednesday
    }
    
    result = engine.schedule_range(
        workers=workers,
        start=start_date,
        end=end_date,
        num_closers_per_weekend=2,
        weekday_tasks=weekday_tasks
    )
    
    print(f"Success: {result['success']}")
    print(f"Assignment errors: {len(result['assignment_errors'])}")
    
    if result['assignment_errors']:
        print("Errors:")
        for error in result['assignment_errors']:
            print(f"  {error['severity']}: {error['task_type']} on {error['date']} - {error['reason']}")
    
    print("Closers:")
    for date_str, closer_ids in result['closers'].items():
        print(f"  {date_str}:")
        for closer_id in closer_ids:
            worker_name = next(w.name for w in workers if w.id == closer_id)
            print(f"    {worker_name}")
    
    print("Y-task assignments:")
    for date_str, assignments in result['y_tasks'].items():
        print(f"  {date_str}:")
        for task_type, worker_id in assignments:
            worker_name = next(w.name for w in workers if w.id == worker_id)
            print(f"    {task_type} -> {worker_name}")
    
    return result['success']


if __name__ == "__main__":
    print("Testing Complete Scheduling Workflow")
    print("=" * 50)
    
    # Run tests
    test1_success = test_weekday_only_scheduling()
    test2_success = test_weekend_scheduling() 
    test3_success = test_mixed_scheduling()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Weekday-only scheduling: {'PASS' if test1_success else 'FAIL'}")
    print(f"Weekend scheduling: {'PASS' if test2_success else 'FAIL'}")
    print(f"Mixed scheduling: {'PASS' if test3_success else 'FAIL'}")
    
    overall_success = test1_success and test2_success and test3_success
    print(f"\nOverall: {'PASS' if overall_success else 'FAIL'}")
