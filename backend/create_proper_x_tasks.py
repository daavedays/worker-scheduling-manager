#!/usr/bin/env python3
"""
Create X task files in the proper format with configurable fill percentage
Usage: python3 create_proper_x_tasks.py <percentage>
Example: python3 create_proper_x_tasks.py 75
"""

import csv
import random
import sys
import json
from datetime import date, timedelta

def create_proper_x_tasks(fill_percentage):
    """Create X task files in the proper format with specified fill percentage"""
    
    # Validate percentage
    if not 0 <= fill_percentage <= 100:
        print("❌ Error: Percentage must be between 0 and 100")
        sys.exit(1)
    
    print(f"=== CREATING X TASK FILES WITH {fill_percentage}% FILL RATE ===\n")
    
    # Define X task types
    x_task_types = [
        "Kitchen", "Training", "Meeting", "Maintenance", "Rituk"
    ]
    
    # Create weekly periods for 2025 part 1 (26 weeks)
    weeks = []
    start_date = date(2025, 1, 5)  # First Sunday of 2025
    
    for week_num in range(1, 27):
        week_start = start_date + timedelta(days=(week_num - 1) * 7)
        week_end = week_start + timedelta(days=6)
        weeks.append((week_num, week_start, week_end))
    
    # Create CSV data for part 1
    csv_data = []
    
    # Header row with week numbers
    header = ['id', 'name']
    for week_num in range(1, 27):
        header.append(str(week_num))
    csv_data.append(header)
    
    # Subheader row with date ranges
    subheader = ['', '']
    for week_num, week_start, week_end in weeks:
        subheader.append(f"{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}")
    csv_data.append(subheader)
    
    # Create 50 workers with specified fill percentage
    for worker_id in range(1, 36):
        worker_row = [f"10000{worker_id:02d}", f"Worker {worker_id}"]
        
        # Add X tasks for each week based on fill percentage
        for week_num in range(1, 27):
            # Convert percentage to probability (e.g., 75% = 0.75)
            probability = fill_percentage / 100.0
            if random.random() < probability:
                task_type = random.choice(x_task_types)
                worker_row.append(task_type)
            else:
                worker_row.append("")
        
        csv_data.append(worker_row)
    
    # Save part 1 to CSV
    filename1 = '../data/x_tasks_2025_1.csv'
    with open(filename1, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data)
    
    print(f"✅ Created {filename1}")
    
    # Create part 2 (weeks 27-52)
    weeks2 = []
    start_date2 = date(2025, 7, 6)  # First Sunday of part 2
    
    for week_num in range(27, 53):
        week_start = start_date2 + timedelta(days=(week_num - 27) * 7)
        week_end = week_start + timedelta(days=6)
        weeks2.append((week_num, week_start, week_end))
    
    # Create CSV data for part 2
    csv_data2 = []
    
    # Header row with week numbers
    header2 = ['id', 'name']
    for week_num in range(27, 53):
        header2.append(str(week_num))
    csv_data2.append(header2)
    
    # Subheader row with date ranges
    subheader2 = ['', '']
    for week_num, week_start, week_end in weeks2:
        subheader2.append(f"{week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')}")
    csv_data2.append(subheader2)
    
    # Create 50 workers for part 2
    for worker_id in range(1, 51):
        worker_row = [f"10000{worker_id:02d}", f"Worker {worker_id}"]
        
        # Add X tasks for each week based on fill percentage
        for week_num in range(27, 53):
            probability = fill_percentage / 100.0
            if random.random() < probability:
                task_type = random.choice(x_task_types)
                worker_row.append(task_type)
            else:
                worker_row.append("")
        
        csv_data2.append(worker_row)
    
    # Save part 2 to CSV
    filename2 = '../data/x_tasks_2025_2.csv'
    with open(filename2, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data2)
    
    print(f"✅ Created {filename2}")
    
    # Update metadata file
    meta_data = {
        "year": 2025,
        "half": 1,
        "available_periods": [1, 2],
        "fill_percentage": fill_percentage,
        "created_at": date.today().isoformat()
    }
    
    meta_filename = '../data/x_task_meta.json'
    with open(meta_filename, 'w', encoding='utf-8') as f:
        json.dump(meta_data, f, indent=2)
    
    print(f"✅ Updated {meta_filename}")
    
    # Show statistics
    total_slots1 = (len(csv_data) - 2) * (len(csv_data[0]) - 2)  # workers * weeks
    total_slots2 = (len(csv_data2) - 2) * (len(csv_data2[0]) - 2)
    total_slots = total_slots1 + total_slots2
    
    total_tasks1 = sum(1 for row in csv_data[2:] for cell in row[2:] if cell.strip())
    total_tasks2 = sum(1 for row in csv_data2[2:] for cell in row[2:] if cell.strip())
    total_tasks = total_tasks1 + total_tasks2
    
    actual_percentage = (total_tasks / total_slots) * 100
    
    print(f"\n📊 Statistics:")
    print(f"  Fill percentage requested: {fill_percentage}%")
    print(f"  Actual fill percentage: {actual_percentage:.1f}%")
    print(f"  Part 1: {total_tasks1} X tasks across {len(csv_data)-2} workers")
    print(f"  Part 2: {total_tasks2} X tasks across {len(csv_data2)-2} workers")
    print(f"  Total: {total_tasks} X tasks out of {total_slots} possible slots")
    
    # Show task type distribution
    task_counts = {}
    for row in csv_data[2:] + csv_data2[2:]:
        for cell in row[2:]:
            if cell.strip():
                task_counts[cell] = task_counts.get(cell, 0) + 1
    
    print(f"\nTask type distribution:")
    for task_type, count in sorted(task_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {task_type}: {count}")

if __name__ == "__main__":
    # Get percentage from command line argument
    if len(sys.argv) != 2:
        print("❌ Usage: python3 create_proper_x_tasks.py <percentage>")
        print("Example: python3 create_proper_x_tasks.py 75")
        sys.exit(1)
    
    try:
        fill_percentage = int(sys.argv[1])
        create_proper_x_tasks(fill_percentage)
    except ValueError:
        print("❌ Error: Percentage must be a number")
        sys.exit(1) 