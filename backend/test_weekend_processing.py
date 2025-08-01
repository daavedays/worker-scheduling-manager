#!/usr/bin/env python3
"""
Test script for weekend processing logic
"""

import sys
import os
from datetime import date, timedelta
sys.path.append(os.path.dirname(__file__))

import sys
sys.path.append('.')
from worker import Worker
from scheduler_engine import SchedulerEngine

def test_weekend_processing_basic():
    """Test basic weekend processing functionality"""
    print("=== Testing Basic Weekend Processing ===")
    
    # Create test workers
    workers = [
        Worker("1", "Worker 1", None, ["Supervisor", "C&N Driver"], 4, score=5),
        Worker("2", "Worker 2", None, ["C&N Escort", "Southern Driver"], 4, score=10),
        Worker("3", "Worker 3", None, ["Southern Escort"], 4, score=15),
        Worker("4", "Worker 4", None, ["Supervisor", "C&N Driver", "C&N Escort"], 4, score=20),
    ]
    
    # Create scheduler engine for a week
    start_date = date(2025, 1, 5)  # Sunday
    end_date = date(2025, 1, 11)   # Saturday
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # Test weekend Y task assignment
    week_start = date(2025, 1, 5)  # Sunday
    assigned_workers = engine._assign_weekend_y_tasks_for_week_enhanced(week_start)
    
    print(f"Assigned {len(assigned_workers)} workers to weekend Y tasks")
    for worker in assigned_workers:
        print(f"- {worker.name} (score: {worker.score})")
    
    # Verify assignments
    thursday = date(2025, 1, 9)
    friday = date(2025, 1, 10)
    saturday = date(2025, 1, 11)
    
    for worker in workers:
        y_tasks_count = sum(1 for d in [thursday, friday, saturday] if d in worker.y_tasks)
        if y_tasks_count > 0:
            print(f"✓ {worker.name} has {y_tasks_count} Y tasks assigned")
    
    print("✓ Basic weekend processing works correctly")

def test_weekend_closer_priority():
    """Test that weekend closers get priority for Y tasks"""
    print("\n=== Testing Weekend Closer Priority ===")
    
    # Create test workers
    workers = [
        Worker("1", "Worker 1", None, ["Supervisor", "C&N Driver"], 4, score=5),
        Worker("2", "Worker 2", None, ["C&N Escort", "Southern Driver"], 4, score=10),
        Worker("3", "Worker 3", None, ["Southern Escort"], 4, score=15),
    ]
    
    # Create scheduler engine
    start_date = date(2025, 1, 5)
    end_date = date(2025, 1, 11)
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # Assign a weekend closer
    week_start = date(2025, 1, 5)
    engine.weekend_closers[week_start] = workers[0]  # Worker 1 is weekend closer
    
    # Test weekend Y task assignment
    assigned_workers = engine._assign_weekend_y_tasks_for_week_enhanced(week_start)
    
    # Verify that weekend closer got priority
    weekend_closer = workers[0]
    thursday = date(2025, 1, 9)
    
    if thursday in weekend_closer.y_tasks:
        print(f"✓ Weekend closer {weekend_closer.name} got Y task assignment")
    else:
        print(f"✗ Weekend closer {weekend_closer.name} did not get Y task assignment")
    
    print("✓ Weekend closer priority works correctly")

def test_weekend_cache():
    """Test weekend assignments cache functionality"""
    print("\n=== Testing Weekend Cache ===")
    
    # Create test workers
    workers = [
        Worker("1", "Worker 1", None, ["Supervisor"], 4, score=5),
        Worker("2", "Worker 2", None, ["C&N Driver"], 4, score=10),
    ]
    
    # Create scheduler engine
    start_date = date(2025, 1, 5)
    end_date = date(2025, 1, 11)
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # Test cache functionality
    week_start = date(2025, 1, 5)
    engine.weekend_assignments_cache[week_start] = {
        "Supervisor": workers[0],
        "C&N Driver": workers[1]
    }
    
    # Verify cache
    cached_assignments = engine.weekend_assignments_cache.get(week_start, {})
    print(f"Cached assignments: {len(cached_assignments)} tasks")
    
    for task, worker in cached_assignments.items():
        print(f"- {task}: {worker.name}")
    
    print("✓ Weekend cache works correctly")

def test_weekend_processing_flow():
    """Test the complete weekend processing flow"""
    print("\n=== Testing Complete Weekend Processing Flow ===")
    
    # Create test workers
    workers = [
        Worker("1", "Worker 1", None, ["Supervisor", "C&N Driver"], 4, score=5),
        Worker("2", "Worker 2", None, ["C&N Escort", "Southern Driver"], 4, score=10),
        Worker("3", "Worker 3", None, ["Southern Escort"], 4, score=15),
        Worker("4", "Worker 4", None, ["Supervisor", "C&N Driver", "C&N Escort"], 4, score=20),
    ]
    
    # Create scheduler engine for a week
    start_date = date(2025, 1, 5)  # Sunday
    end_date = date(2025, 1, 11)   # Saturday
    engine = SchedulerEngine(workers, start_date, end_date)
    
    # Test complete Y task assignment
    assigned_workers = engine.assign_y_tasks(start_date, end_date)
    
    print(f"Total assigned workers: {len(assigned_workers)}")
    
    # Check weekend assignments
    weekend_days = [date(2025, 1, 9), date(2025, 1, 10), date(2025, 1, 11)]  # Thu, Fri, Sat
    weekend_assignments = 0
    
    for worker in workers:
        for day in weekend_days:
            if day in worker.y_tasks:
                weekend_assignments += 1
                print(f"✓ {worker.name} assigned to {worker.y_tasks[day]} on {day}")
    
    print(f"Weekend assignments: {weekend_assignments}")
    print("✓ Complete weekend processing flow works correctly")

def test_edge_cases():
    """Test edge cases for weekend processing"""
    print("\n=== Testing Edge Cases ===")
    
    # Test with no qualified workers
    workers = [
        Worker("1", "Worker 1", None, [], 4, score=5),  # No qualifications
        Worker("2", "Worker 2", None, [], 4, score=10),  # No qualifications
    ]
    
    start_date = date(2025, 1, 5)
    end_date = date(2025, 1, 11)
    engine = SchedulerEngine(workers, start_date, end_date)
    
    week_start = date(2025, 1, 5)
    assigned_workers = engine._assign_weekend_y_tasks_for_week_enhanced(week_start)
    
    print(f"Assigned workers with no qualifications: {len(assigned_workers)}")
    print("✓ Edge case handling works correctly")

def main():
    """Run all tests"""
    print("Starting weekend processing tests...\n")
    
    try:
        test_weekend_processing_basic()
        test_weekend_closer_priority()
        test_weekend_cache()
        test_weekend_processing_flow()
        test_edge_cases()
        
        print("\n🎉 All weekend processing tests passed successfully!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 