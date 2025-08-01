#!/usr/bin/env python3
"""
Comprehensive reset script that creates X tasks and properly populates worker data
Usage: python3 reset_and_create_x_tasks.py <percentage>
Example: python3 reset_and_create_x_tasks.py 75
"""

import csv
import random
import sys
import json
import os
from datetime import date, timedelta

def reset_and_create_x_tasks(fill_percentage):
    """Reset everything and create X tasks with proper worker data population"""
    
    # Validate percentage
    if not 0 <= fill_percentage <= 100:
        print("❌ Error: Percentage must be between 0 and 100")
        sys.exit(1)
    
    print(f"=== COMPREHENSIVE RESET WITH {fill_percentage}% X TASK FILL RATE ===\n")
    
    # Define X task types
    x_task_types = [
        "Kitchen", "Training", "Meeting", "Maintenance", "Rituk"
    ]
    
    # Define qualification levels (more qualifications = better score)
    qualification_levels = [
        ["Supervisor"],  # Basic - 1 qualification
        ["Supervisor", "C&N Driver"],  # 2 qualifications
        ["Supervisor", "C&N Driver", "C&N Escort"],  # 3 qualifications
        ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver"],  # 4 qualifications
        ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]  # 5 qualifications
    ]
    
    # Create 35 workers with varying qualification levels
    workers = []
    
    print("Creating 35 workers with varying qualification levels...")
    
    for worker_id in range(1, 36):
        # Assign qualification level based on worker ID (more qualifications for higher IDs)
        qualification_index = min((worker_id - 1) // 7, len(qualification_levels) - 1)  # 0-4
        qualifications = qualification_levels[qualification_index]
        
        # Calculate score based on qualifications (more qualifications = higher score)
        base_score = len(qualifications) * 15  # 15 points per qualification
        random_bonus = random.randint(-5, 5)  # Small random variation
        score = max(0, min(100, base_score + random_bonus))
        
        # Random seniority (1-10)
        seniority = random.randint(1, 10)
        
        # Random closing interval (3-6 weeks)
        closing_interval = random.randint(3, 6)
        
        worker_data = {
            "id": f"10000{worker_id:02d}",
            "name": f"Worker {worker_id}",
            "qualifications": qualifications,
            "closing_interval": closing_interval,
            "x_tasks": {},
            "y_tasks": {},
            "closing_history": [],
            "officer": False,
            "seniority": seniority,
            "score": score,
            "long_timer": False,
            "x_task_count": 0,
            "y_task_count": 0,
            "closing_delta": 0
        }
        
        workers.append(worker_data)
        
        print(f"  Worker {worker_id}: {len(qualifications)} qualifications, score {score}")
    
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
    
    # Create X tasks for each worker and populate worker data
    print(f"\nCreating X tasks with {fill_percentage}% fill rate...")
    
    # Calculate how many weeks each worker should have X tasks
    # About 8 weeks per half year = 16 weeks total for the year
    # Convert percentage to weeks (e.g., 75% = 12 weeks, 50% = 8 weeks)
    weeks_per_half = int((fill_percentage / 100.0) * 8)  # 8 weeks base
    total_weeks_with_x_tasks = weeks_per_half * 2  # For both halves
    
    # Create week selections for each worker
    worker_week_selections = {}
    for worker in workers:
        # Randomly select which weeks this worker will have X tasks
        all_weeks = list(range(1, 53))  # All 52 weeks
        selected_weeks = random.sample(all_weeks, min(total_weeks_with_x_tasks, len(all_weeks)))
        worker_week_selections[worker["id"]] = selected_weeks
    
    for worker in workers:
        worker_row = [worker["id"], worker["name"]]
        selected_weeks = worker_week_selections[worker["id"]]
        
        # Add X tasks for each week based on selection
        for week_num in range(1, 27):  # Part 1: weeks 1-26
            week_start, week_end = weeks[week_num - 1][1], weeks[week_num - 1][2]
            
            if week_num in selected_weeks:
                task_type = random.choice(x_task_types)
                worker_row.append(task_type)
                
                # Populate worker data with X tasks for the entire week
                current_date = week_start
                while current_date <= week_end:
                    worker["x_tasks"][current_date.isoformat()] = task_type
                    current_date += timedelta(days=1)
                
                worker["x_task_count"] += 1
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
    
    # Create X tasks for part 2
    for worker in workers:
        worker_row = [worker["id"], worker["name"]]
        selected_weeks = worker_week_selections[worker["id"]]
        
        # Add X tasks for each week based on selection (same selection as part 1)
        for week_num in range(27, 53):  # Part 2: weeks 27-52
            week_start, week_end = weeks2[week_num - 27][1], weeks2[week_num - 27][2]
            
            if week_num in selected_weeks:
                task_type = random.choice(x_task_types)
                worker_row.append(task_type)
                
                # Populate worker data with X tasks for the entire week
                current_date = week_start
                while current_date <= week_end:
                    worker["x_tasks"][current_date.isoformat()] = task_type
                    current_date += timedelta(days=1)
                
                worker["x_task_count"] += 1
            else:
                worker_row.append("")
        
        csv_data2.append(worker_row)
    
    # Save part 2 to CSV
    filename2 = '../data/x_tasks_2025_2.csv'
    with open(filename2, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(csv_data2)
    
    print(f"✅ Created {filename2}")
    
    # Save worker data
    worker_filename = '../data/worker_data.json'
    with open(worker_filename, 'w', encoding='utf-8') as f:
        json.dump(workers, f, indent=2)
    
    print(f"✅ Created {worker_filename}")
    
    # Update metadata file
    meta_data = {
        "year": 2025,
        "half": 1,
        "available_periods": [1, 2],
        "fill_percentage": fill_percentage,
        "created_at": date.today().isoformat(),
        "worker_count": 35
    }
    
    meta_filename = '../data/x_task_meta.json'
    with open(meta_filename, 'w', encoding='utf-8') as f:
        json.dump(meta_data, f, indent=2)
    
    print(f"✅ Updated {meta_filename}")
    
    # Clear Y tasks and other data
    y_tasks_filename = '../data/y_tasks.json'
    if os.path.exists(y_tasks_filename):
        os.remove(y_tasks_filename)
        print(f"✅ Cleared {y_tasks_filename}")
    
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
    
    # Show qualification distribution
    qualification_counts = {}
    for worker in workers:
        qual_count = len(worker["qualifications"])
        qualification_counts[qual_count] = qualification_counts.get(qual_count, 0) + 1
    
    print(f"\nQualification distribution:")
    for qual_count, worker_count in sorted(qualification_counts.items()):
        print(f"  {qual_count} qualifications: {worker_count} workers")
    
    # Show score distribution
    score_ranges = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for worker in workers:
        score = worker["score"]
        if score <= 20:
            score_ranges["0-20"] += 1
        elif score <= 40:
            score_ranges["21-40"] += 1
        elif score <= 60:
            score_ranges["41-60"] += 1
        elif score <= 80:
            score_ranges["61-80"] += 1
        else:
            score_ranges["81-100"] += 1
    
    print(f"\nScore distribution:")
    for range_name, count in score_ranges.items():
        print(f"  {range_name}: {count} workers")
    
    print(f"\n✅ Reset complete! Ready to test with improved accuracy.")

if __name__ == "__main__":
    # Get percentage from command line argument
    if len(sys.argv) != 2:
        print("❌ Usage: python3 reset_and_create_x_tasks.py <percentage>")
        print("Example: python3 reset_and_create_x_tasks.py 75")
        sys.exit(1)
    
    try:
        fill_percentage = int(sys.argv[1])
        reset_and_create_x_tasks(fill_percentage)
    except ValueError:
        print("❌ Error: Percentage must be a number")
        sys.exit(1) 