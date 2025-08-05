#!/usr/bin/env python3
"""
Migration script to move Y tasks from worker_data.json to CSV files.
This prevents JSON file bloat and enables proper caching.
"""

import os
import sys
import json
from datetime import datetime, date
from collections import defaultdict

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

def migrate_y_tasks_to_csv():
    """Migrate Y tasks from worker_data.json to CSV files"""
    
    data_dir = os.path.dirname(__file__)
    worker_data_path = os.path.join(data_dir, 'worker_data.json')
    
    if not os.path.exists(worker_data_path):
        print("❌ worker_data.json not found")
        return
    
    print("🔄 Starting Y task migration...")
    
    # Load worker data
    with open(worker_data_path, 'r', encoding='utf-8') as f:
        workers = json.load(f)
    
    # Group Y tasks by date ranges
    y_task_groups = defaultdict(lambda: defaultdict(dict))
    
    for worker in workers:
        worker_id = worker.get('id')
        worker_name = worker.get('name', '').strip()
        y_tasks = worker.get('y_tasks', {})
        
        if not y_tasks:
            continue
        
        print(f"📋 Processing worker {worker_name} ({worker_id}) with {len(y_tasks)} Y tasks")
        
        for date_str, task_name in y_tasks.items():
            try:
                # Parse date
                if '/' in date_str:
                    # Already in dd/mm/yyyy format
                    parsed_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                else:
                    # Assume yyyy-mm-dd format
                    parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Group by year and month for better organization
                year_month = f"{parsed_date.year:04d}-{parsed_date.month:02d}"
                
                # Store task assignment
                y_task_groups[year_month][worker_name][date_str] = task_name
                
            except Exception as e:
                print(f"⚠️ Error parsing date {date_str} for worker {worker_name}: {e}")
    
    if not y_task_groups:
        print("ℹ️ No Y tasks found to migrate")
        return
    
    # Import Y task manager
    try:
        from y_task_manager import get_y_task_manager
        y_task_manager = get_y_task_manager(data_dir)
    except ImportError as e:
        print(f"❌ Could not import Y task manager: {e}")
        return
    
    # Create CSV files for each month
    migrated_count = 0
    
    for year_month, worker_assignments in y_task_groups.items():
        if not worker_assignments:
            continue
        
        # Get all unique dates and tasks
        all_dates = set()
        all_tasks = set()
        
        for worker_name, date_assignments in worker_assignments.items():
            for date_str, task_name in date_assignments.items():
                all_dates.add(date_str)
                all_tasks.add(task_name)
        
        # Sort dates and tasks
        sorted_dates = sorted(all_dates, key=lambda d: datetime.strptime(d, '%d/%m/%Y') if '/' in d else datetime.strptime(d, '%Y-%m-%d'))
        sorted_tasks = sorted(all_tasks)
        
        # Create grid data
        grid_data = []
        for task_name in sorted_tasks:
            row = []
            for date_str in sorted_dates:
                # Find worker assigned to this task on this date
                assigned_worker = None
                for worker_name, date_assignments in worker_assignments.items():
                    if date_str in date_assignments and date_assignments[date_str] == task_name:
                        assigned_worker = worker_name
                        break
                
                row.append(assigned_worker or '-')
            grid_data.append(row)
        
        # Determine start and end dates
        start_date = sorted_dates[0]
        end_date = sorted_dates[-1]
        
        # Convert dates to dd/mm/yyyy format if needed
        if '/' not in start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            start_date = start_dt.strftime('%d/%m/%Y')
        
        if '/' not in end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_dt.strftime('%d/%m/%Y')
        
        try:
            # Save to CSV
            filename = y_task_manager.save_y_tasks_to_csv(
                start_date, end_date, grid_data, sorted_dates, sorted_tasks
            )
            
            print(f"✅ Created CSV file: {filename}")
            print(f"   Period: {start_date} to {end_date}")
            print(f"   Tasks: {len(sorted_tasks)}")
            print(f"   Dates: {len(sorted_dates)}")
            print(f"   Assignments: {sum(len(row) for row in grid_data)}")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"❌ Error creating CSV for {year_month}: {e}")
    
    print(f"\n🎉 Migration completed!")
    print(f"📊 Created {migrated_count} CSV files")
    
    # Optionally clear Y tasks from JSON
    clear_json = input("\n❓ Clear Y tasks from worker_data.json? (y/N): ").lower().strip()
    if clear_json == 'y':
        clear_y_tasks_from_json(worker_data_path, workers)
        print("✅ Cleared Y tasks from worker_data.json")
    else:
        print("ℹ️ Y tasks remain in worker_data.json (legacy data)")


def clear_y_tasks_from_json(worker_data_path, workers):
    """Clear Y tasks from worker data JSON"""
    for worker in workers:
        if 'y_tasks' in worker:
            worker['y_tasks'] = {}
    
    with open(worker_data_path, 'w', encoding='utf-8') as f:
        json.dump(workers, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    migrate_y_tasks_to_csv() 