#!/usr/bin/env python3
"""
Reset Worker Data Script
Resets all worker data including x_tasks, y_tasks, closing_history, and scores
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent
WORKER_JSON_PATH = DATA_DIR / "worker_data.json"

def reset_all_worker_data():
    """
    Reset all worker data: x_tasks, y_tasks, closing_history, and scores
    Also clears Y task CSV files and index
    """
    print("🔄 Starting comprehensive worker data reset...")
    
    # Check if worker data file exists
    if not WORKER_JSON_PATH.exists():
        print("❌ Worker data file not found!")
        print(f"   Expected location: {WORKER_JSON_PATH}")
        return False
    
    # Load current worker data
    try:
        with open(WORKER_JSON_PATH, 'r', encoding='utf-8') as f:
            workers_data = json.load(f)
        print(f"✅ Loaded {len(workers_data)} workers from {WORKER_JSON_PATH}")
    except Exception as e:
        print(f"❌ Error loading worker data: {e}")
        return False
    
    # Reset each worker
    reset_count = 0
    for worker in workers_data:
        # Reset all assignments - ALWAYS reset these fields
        worker['score'] = 0
        worker['y_task_count'] = 0
        worker['x_task_count'] = 0
        worker['closing_delta'] = 0
        worker['required_closing_dates'] = []
        worker['optimal_closing_dates'] = []
        worker['weekends_home_owed'] = 0
        worker['home_weeks_owed'] = 0
        worker['closing_history'] = []
        worker['y_tasks'] = {}
        worker['x_tasks'] = {}
        worker['y_task_counts'] = {
            "Supervisor": 0,
            "C&N Driver": 0,
            "C&N Escort": 0,
            "Southern Driver": 0,
            "Southern Escort": 0
        }

        reset_count += 1
        print(f"   ✅ Reset {worker['name']} (ID: {worker['id']})")
    
    # Save reset data
    try:
        with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(workers_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully reset {reset_count} workers")
        print(f"   📁 File saved: {WORKER_JSON_PATH}")
    except Exception as e:
        print(f"❌ Error saving reset data: {e}")
        return False
    
    # Clear Y task CSV files and index
    print("\n🗑️  Clearing Y task CSV files and index...")
    
    # Clear Y task CSV files
    y_task_files = list(DATA_DIR.glob("y_tasks_*.csv"))
    for y_file in y_task_files:
        try:
            y_file.unlink()
            print(f"   ✅ Deleted: {y_file.name}")
        except Exception as e:
            print(f"   ❌ Error deleting {y_file.name}: {e}")
    
    # Clear Y task index
    y_index_path = DATA_DIR / "y_tasks_index.json"
    if y_index_path.exists():
        try:
            y_index_path.unlink()
            print(f"   ✅ Deleted: {y_index_path.name}")
        except Exception as e:
            print(f"   ❌ Error deleting {y_index_path.name}: {e}")
    
    # Clear X task CSV files
    x_task_files = list(DATA_DIR.glob("x_tasks_*.csv"))
    for x_file in x_task_files:
        try:
            x_file.unlink()
            print(f"   ✅ Deleted: {x_file.name}")
        except Exception as e:
            print(f"   ❌ Error deleting {x_file.name}: {e}")
    
    print(f"   📊 Cleared {len(y_task_files)} Y task files and {len(x_task_files)} X task files")
    
    # Cache functionality has been removed - no need to clear cache
    print("\n🗑️  Cache functionality has been removed - all data is loaded directly from files")
    
    # Verify the reset
    print("\n📊 Reset Summary:")
    print(f"   - Workers processed: {reset_count}")
    print(f"   - X tasks: CLEARED")
    print(f"   - Y tasks: CLEARED")
    print(f"   - Closing history: CLEARED")
    print(f"   - Scores: RESET TO 0")
    print(f"   - Task counts: RESET TO 0")
    print(f"   - Y task CSV files: CLEARED")
    print(f"   - Y task index: CLEARED")
    print(f"   - X task CSV files: CLEARED")
    print(f"   - Y task counts: RESET TO 0")

    
    # Verify the data was actually reset
    verify_reset(workers_data)
    
    return True

def verify_reset(workers_data):
    """
    Verify that the reset was successful
    """
    print("\n🔍 Verifying reset...")
    
    total_x_tasks = 0
    total_y_tasks = 0
    total_closings = 0
    total_score = 0
    
    for worker in workers_data:
        total_x_tasks += len(worker.get('x_tasks', {}))
        total_y_tasks += len(worker.get('y_tasks', {}))
        total_closings += len(worker.get('closing_history', []))
        total_score += worker.get('score', 0)
    
    print(f"✅ Verification results:")
    print(f"   - Total X tasks: {total_x_tasks} (should be 0)")
    print(f"   - Total Y tasks: {total_y_tasks} (should be 0)")
    print(f"   - Total closings: {total_closings} (should be 0)")
    print(f"   - Total score: {total_score} (should be 0)")
    
    if total_x_tasks == 0 and total_y_tasks == 0 and total_closings == 0 and total_score == 0:
        print("🎉 Reset verification PASSED!")
        return True
    else:
        print("❌ Reset verification FAILED!")
        return False

def show_worker_summary():
    """
    Show a summary of current worker data
    """
    print("\n📋 Current Worker Summary:")
    
    if not WORKER_JSON_PATH.exists():
        print("❌ Worker data file not found!")
        return
    
    try:
        with open(WORKER_JSON_PATH, 'r', encoding='utf-8') as f:
            workers_data = json.load(f)
        
        total_x_tasks = 0
        total_y_tasks = 0
        total_closings = 0
        total_score = 0
        
        for worker in workers_data:
            x_count = len(worker.get('x_tasks', {}))
            y_count = len(worker.get('y_tasks', {}))
            closing_count = len(worker.get('closing_history', []))
            score = worker.get('score', 0)
            
            total_x_tasks += x_count
            total_y_tasks += y_count
            total_closings += closing_count
            total_score += score
            
            if x_count > 0 or y_count > 0 or closing_count > 0 or score > 0:
                print(f"   {worker['name']}: {x_count} X, {y_count} Y, {closing_count} closings, score {score}")
        
        print(f"\n📊 Totals:")
        print(f"   - X tasks: {total_x_tasks}")
        print(f"   - Y tasks: {total_y_tasks}")
        print(f"   - Closings: {total_closings}")
        print(f"   - Total score: {total_score}")
        
    except Exception as e:
        print(f"❌ Error reading worker data: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 WORKER DATA RESET SCRIPT")
    print("=" * 60)
    
    # Show current state before reset
    print("\n📋 Current state before reset:")
    show_worker_summary()
    
    # Ask for confirmation
    print("\n⚠️  WARNING: This will reset ALL worker data!")
    print("   - All X tasks will be cleared")
    print("   - All Y tasks will be cleared")
    print("   - All closing history will be cleared")
    print("   - All scores will be reset to 0")
    print("   - All Y task CSV files will be deleted")
    print("   - All X task CSV files will be deleted")
    print("   - Y task index will be cleared")
    
    response = input("\n❓ Do you want to continue? (y/N): ").strip().lower()
    
    if response in ['y', 'yes']:
        print("\n🔄 Starting reset...")
        success = reset_all_worker_data()
        
        if success:
            print("\n🎉 Reset completed successfully!")
            print("\n📋 Final state after reset:")
            show_worker_summary()
        else:
            print("\n❌ Reset failed!")
    else:
        print("\n❌ Reset cancelled by user.")
