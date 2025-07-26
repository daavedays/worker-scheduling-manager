#!/usr/bin/env python3
"""
Test script for the new SchedulerEngine with weekend closing scoring system.
"""

from datetime import date, timedelta
from .worker import Worker
from .scheduler_engine import SchedulerEngine

def create_test_workers():
    """Create test workers with various scenarios for testing."""
    workers = []
    
    # Worker 1: Never closed before, no X tasks, high score
    w1 = Worker(
        id="1",
        name="Worker 1",
        start_date=date(2023, 1, 1),
        qualifications=["Supervisor", "C&N Driver"],
        closing_interval=4,
        score=50,
        long_timer=False
    )
    workers.append(w1)
    
    # Worker 2: Closed recently, has X task next week
    w2 = Worker(
        id="2", 
        name="Worker 2",
        start_date=date(2023, 1, 1),
        qualifications=["Southern Driver", "Southern Escort"],
        closing_interval=3,
        score=30,
        long_timer=False
    )
    w2.closing_history = [date(2024, 1, 5)]  # Closed last week
    w2.x_tasks = {date(2024, 1, 15): True}  # X task next week
    workers.append(w2)
    
    # Worker 3: Overdue for closing, no conflicts
    w3 = Worker(
        id="3",
        name="Worker 3", 
        start_date=date(2023, 1, 1),
        qualifications=["C&N Escort", "Supervisor"],
        closing_interval=2,
        score=20,
        long_timer=False
    )
    w3.closing_history = [date(2024, 1, 1)]  # Closed 2 weeks ago
    workers.append(w3)
    
    # Worker 4: Long timer, many closings
    w4 = Worker(
        id="4",
        name="Worker 4",
        start_date=date(2022, 1, 1),  # Started earlier
        qualifications=["Southern Driver"],
        closing_interval=5,
        score=10,
        long_timer=True
    )
    w4.closing_history = [date(2024, 1, 1), date(2023, 12, 15), date(2023, 12, 1)]  # Many closings
    workers.append(w4)
    
    return workers

def test_weekend_closing_candidates():
    """Test the weekend closing candidates selection."""
    print("=== Testing Weekend Closing Candidates ===")
    
    workers = create_test_workers()
    engine = SchedulerEngine(workers, date(2024, 1, 1), date(2024, 1, 31))
    
    # Test for week starting Monday, January 8, 2024
    current_week = date(2024, 1, 8)  # Monday
    
    print(f"Testing for week starting: {current_week}")
    print()
    
    # Get candidates with scores
    candidates_with_scores = engine.get_weekend_candidates_with_scores(workers, current_week)
    
    print("Candidates ranked by score:")
    for i, (worker, score) in enumerate(candidates_with_scores, 1):
        print(f"{i}. {worker.name} (ID: {worker.id}) - Score: {score}")
        
        # Show debug info
        debug_info = engine.debug_worker_status(worker, current_week)
        print(f"   - Base score: {debug_info['base_score']}")
        print(f"   - Closing interval: {debug_info['closing_interval']}")
        print(f"   - Delta: {debug_info['delta']}")
        print(f"   - Overdue: {debug_info['overdue']}")
        print(f"   - Total closings: {debug_info['total_closings']}")
        print(f"   - Has X task current week: {debug_info['has_x_task_current_week']}")
        print(f"   - Has X task next week: {debug_info['has_x_task_next_week']}")
        print()
    
    # Test the main method
    candidates = engine.get_weekend_closing_candidates(workers, current_week)
    print("Top candidates for weekend closing:")
    for i, worker in enumerate(candidates[:3], 1):
        print(f"{i}. {worker.name}")
    
    return candidates

def test_weekend_closing_assignment():
    """Test the weekend closing assignment."""
    print("\n=== Testing Weekend Closing Assignment ===")
    
    workers = create_test_workers()
    engine = SchedulerEngine(workers, date(2024, 1, 1), date(2024, 1, 31))
    
    # Assign weekend closers for January 2024
    weekend_closers = engine.assign_weekend_closers(date(2024, 1, 1), date(2024, 1, 31))
    
    print("Weekend closing assignments:")
    for weekend_start, worker in weekend_closers.items():
        print(f"Weekend starting {weekend_start} (Friday): {worker.name}")
        
        # Show the Thursday, Friday, Saturday assignments
        thursday = weekend_start - timedelta(days=1)
        saturday = weekend_start + timedelta(days=1)
        print(f"  - Thursday {thursday}: {worker.name}")
        print(f"  - Friday {weekend_start}: {worker.name}")
        print(f"  - Saturday {saturday}: {worker.name}")
        print()

def test_y_task_assignment():
    """Test the Y task assignment."""
    print("\n=== Testing Y Task Assignment ===")
    
    workers = create_test_workers()
    engine = SchedulerEngine(workers, date(2024, 1, 1), date(2024, 1, 31))
    
    # First assign weekend closers
    engine.assign_weekend_closers(date(2024, 1, 1), date(2024, 1, 31))
    
    # Then assign Y tasks for a week (excluding weekends)
    assigned_workers = engine.assign_y_tasks(date(2024, 1, 7), date(2024, 1, 13))  # Sunday to Saturday
    
    print("Y task assignments:")
    for worker in assigned_workers:
        print(f"{worker.name} assigned to Y tasks:")
        for task_date, task_name in worker.y_tasks.items():
            if date(2024, 1, 7) <= task_date <= date(2024, 1, 13):
                print(f"  - {task_date}: {task_name}")

def test_complete_schedule():
    """Test the complete schedule generation."""
    print("\n=== Testing Complete Schedule ===")
    
    workers = create_test_workers()
    engine = SchedulerEngine(workers, date(2024, 1, 1), date(2024, 1, 31))
    
    # Assign weekend closers
    engine.assign_weekend_closers(date(2024, 1, 1), date(2024, 1, 31))
    
    # Assign Y tasks
    engine.assign_y_tasks(date(2024, 1, 1), date(2024, 1, 31))
    
    # Get complete schedule
    schedule = engine.get_schedule()
    
    print("Complete schedule for January 2024:")
    for date_key in sorted(schedule.keys()):
        if date_key.month == 1:  # Only show January
            print(f"{date_key}: {schedule[date_key]}")

def test_insufficient_workers_report():
    """Test the insufficient workers report."""
    print("\n=== Testing Insufficient Workers Report ===")
    
    workers = create_test_workers()
    engine = SchedulerEngine(workers, date(2024, 1, 1), date(2024, 1, 31))
    
    # Generate report
    report = engine.get_insufficient_workers_report(date(2024, 1, 1), date(2024, 1, 31))
    
    print(f"Report for period: {report['period']}")
    print(f"Total workers: {report['total_workers']}")
    
    if report['weekend_closing_issues']:
        print("Weekend closing issues:")
        for issue in report['weekend_closing_issues']:
            print(f"  {issue['weekend']}: {issue['issue']}")
    
    if report['y_task_issues']:
        print("Y task issues:")
        for issue in report['y_task_issues']:
            print(f"  Week {issue['week']}, {issue['task']}: {issue['issue']}")
    
    if report['recommendations']:
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")

if __name__ == "__main__":
    print("Testing new SchedulerEngine with weekend closing scoring system")
    print("=" * 60)
    
    try:
        test_weekend_closing_candidates()
        test_weekend_closing_assignment()
        test_y_task_assignment()
        test_complete_schedule()
        test_insufficient_workers_report()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 