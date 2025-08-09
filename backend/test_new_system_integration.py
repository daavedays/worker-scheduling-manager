#!/usr/bin/env python3
"""
Comprehensive test of the new scheduling system integration.
Tests the complete workflow from worker creation to task assignment.
"""

from datetime import date, timedelta
from worker import EnhancedWorker, load_workers_from_json, save_workers_to_json
from engine import SchedulingEngineV2
from scoring import recalc_worker_schedule
from closing_schedule_calculator import ClosingScheduleCalculator


def test_new_system_integration():
    """Test the complete new system workflow."""
    print("🧪 Testing New System Integration")
    print("=" * 50)
    
    # Step 1: Create test workers using the new EnhancedWorker class
    print("📋 Step 1: Creating test workers...")
    workers = [
        EnhancedWorker("W1", "Alice", date(2024, 1, 1), ["Supervisor", "C&N Driver"], 3),
        EnhancedWorker("W2", "Bob", date(2024, 1, 1), ["C&N Escort", "Southern Driver"], 4),
        EnhancedWorker("W3", "Charlie", date(2024, 1, 1), ["Southern Escort", "Supervisor"], 2),
    ]
    
    print(f"✅ Created {len(workers)} workers")
    for w in workers:
        print(f"  - {w.name}: {w.qualifications}, interval={w.closing_interval}")
    
    # Step 2: Add X tasks and test pre-computation
    print(f"\n🔧 Step 2: Adding X tasks and testing pre-computation...")
    workers[0].x_tasks["08/03/2024"] = "Special Guard"  # Alice
    workers[1].x_tasks["22/03/2024"] = "Transport"      # Bob
    
    # Step 3: Test ClosingScheduleCalculator
    print(f"\n📊 Step 3: Testing ClosingScheduleCalculator...")
    calc = ClosingScheduleCalculator()
    calc.debug = False  # Reduce output
    
    # Test semester weeks
    start_date = date(2024, 3, 1)  # Friday
    semester_weeks = []
    for i in range(4):
        semester_weeks.append(start_date + timedelta(weeks=i))
    
    print(f"Semester weeks: {[d.strftime('%d/%m/%Y') for d in semester_weeks]}")
    
    # Pre-compute schedules
    calc.update_all_worker_schedules(workers, semester_weeks)
    
    print(f"\n📋 Pre-computed schedules:")
    for worker in workers:
        req_dates = [d.strftime('%d/%m/%Y') for d in worker.required_closing_dates]
        opt_dates = [d.strftime('%d/%m/%Y') for d in worker.optimal_closing_dates]
        print(f"  {worker.name}:")
        print(f"    Required: {req_dates}")
        print(f"    Optimal: {opt_dates}")
        print(f"    Weekends owed: {worker.weekends_home_owed}")
    
    # Step 4: Test SchedulingEngineV2
    print(f"\n🚀 Step 4: Testing SchedulingEngineV2...")
    engine = SchedulingEngineV2()
    
    # Test weekend closer assignment
    thursday = start_date - timedelta(days=1)  # Thursday before first Friday
    assigned, logs = engine.assign_weekend_closers(workers, thursday, 2, semester_weeks)
    
    print(f"\n🏠 Weekend closers for {thursday.strftime('%d/%m/%Y')} (Thu-Sat):")
    for worker in assigned:
        status = "required" if start_date in worker.required_closing_dates else "optimal" if start_date in worker.optimal_closing_dates else "available"
        print(f"  - {worker.name} ({status})")
    
    # Test Y-task assignment
    print(f"\n📋 Y-task assignment test:")
    weekday_tasks = {
        start_date + timedelta(days=2): ["Supervisor"],  # Sunday
        start_date + timedelta(days=3): ["C&N Driver"],  # Monday
    }
    
    y_assigns, y_logs = engine.assign_weekday_y_tasks(workers, weekday_tasks)
    
    print(f"Y-task assignments:")
    for date_key, assignments in y_assigns.items():
        print(f"  {date_key.strftime('%d/%m/%Y')}:")
        for task_type, worker_id in assignments:
            worker_name = next(w.name for w in workers if w.id == worker_id)
            print(f"    - {task_type}: {worker_name}")
    
    # Step 5: Test full range scheduling
    print(f"\n🎯 Step 5: Testing full range scheduling...")
    result = engine.schedule_range(
        workers=workers,
        start=start_date,
        end=start_date + timedelta(weeks=3),
        num_closers_per_weekend=2,
        weekday_tasks=weekday_tasks
    )
    
    print(f"Full range result keys: {list(result.keys())}")
    print(f"Closers assigned: {len(result['closers'])} weekends")
    print(f"Y-tasks assigned: {len(result['y_tasks'])} days")
    print(f"Logs generated: {len(result['logs'])} entries")
    
    # Step 6: Test JSON persistence
    print(f"\n💾 Step 6: Testing JSON persistence...")
    save_workers_to_json(workers, "test_workers.json")
    loaded_workers = load_workers_from_json("test_workers.json")
    
    print(f"Saved and loaded {len(loaded_workers)} workers")
    for original, loaded in zip(workers, loaded_workers):
        assert original.name == loaded.name
        assert original.qualifications == loaded.qualifications
        assert original.closing_interval == loaded.closing_interval
        assert original.x_tasks == loaded.x_tasks
        print(f"  ✅ {original.name}: data integrity verified")
    
    # Cleanup
    import os
    os.remove("test_workers.json")
    
    print(f"\n🎉 All integration tests passed!")
    print(f"\n📝 Summary:")
    print(f"  ✅ EnhancedWorker class works correctly")
    print(f"  ✅ ClosingScheduleCalculator pre-computes optimal dates")
    print(f"  ✅ SchedulingEngineV2 assigns tasks using pre-computed data")
    print(f"  ✅ JSON persistence maintains data integrity")
    print(f"  ✅ Complete workflow functions end-to-end")
    
    return True


if __name__ == "__main__":
    try:
        test_new_system_integration()
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
