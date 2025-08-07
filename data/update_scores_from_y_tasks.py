#!/usr/bin/env python3
"""
Update worker scores based on existing Y task assignments in CSV files.
This script will read all Y task CSV files and update worker scores accordingly.
"""

import os
import csv
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / 'backend'))

from worker import load_workers_from_json, save_workers_to_json

def update_scores_from_y_tasks():
    """Update worker scores based on existing Y task assignments."""
    
    data_dir = Path(__file__).parent
    worker_json_path = data_dir / 'worker_data.json'
    
    # Load workers
    workers = load_workers_from_json(str(worker_json_path))
    
    # Count Y task assignments per worker
    worker_assignments = {}
    
    # Find all Y task CSV files
    y_task_files = []
    for filename in os.listdir(data_dir):
        if filename.startswith('y_tasks_') and filename.endswith('.csv'):
            y_task_files.append(filename)
    
    print(f"Found {len(y_task_files)} Y task files")
    
    # Process each Y task file
    for filename in y_task_files:
        filepath = data_dir / filename
        print(f"Processing {filename}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                
                # Read header row
                header = next(reader)
                dates = header[1:]  # Skip 'Y Task' column
                
                # Read data rows
                for row in reader:
                    if len(row) > 1:
                        y_task = row[0]
                        assignments = row[1:]
                        
                        # Count assignments for each worker
                        for assignment in assignments:
                            if assignment and assignment != '-':  # If there's an assignment
                                worker_name = assignment
                                if worker_name not in worker_assignments:
                                    worker_assignments[worker_name] = 0
                                worker_assignments[worker_name] += 1
                                
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"Found assignments for {len(worker_assignments)} workers:")
    for worker_name, count in worker_assignments.items():
        print(f"  {worker_name}: {count} assignments")
    
    # Update worker scores
    updated_count = 0
    for worker in workers:
        if worker.name in worker_assignments:
            old_score = worker.score
            worker.score += worker_assignments[worker.name]
            print(f"Updated {worker.name}: {old_score} -> {worker.score}")
            updated_count += 1
    
    # Save updated workers directly to JSON
    print(f"\nSaving updated workers to {worker_json_path}...")
    
    # Convert workers to JSON format
    workers_data = []
    for worker in workers:
        worker_dict = {
            'id': worker.id,
            'name': worker.name,
            'qualifications': worker.qualifications,
            'closing_interval': worker.closing_interval,
            'officer': worker.officer,
            'seniority': worker.seniority,
            'score': worker.score,  # This should now have the updated score
            'long_timer': worker.long_timer,
            'x_tasks': worker.x_tasks,
            'y_tasks': worker.y_tasks,
            'closing_history': worker.closing_history
        }
        workers_data.append(worker_dict)
    
    # Save to JSON file
    with open(worker_json_path, 'w', encoding='utf-8') as f:
        json.dump(workers_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Updated scores for {updated_count} workers")
    print(f"✅ Worker data saved to {worker_json_path}")
    
    # Verify the save worked
    print("\nVerifying saved scores:")
    for worker in workers[:5]:  # Check first 5 workers
        if worker.name in worker_assignments:
            print(f"  {worker.name}: {worker.score}")

if __name__ == "__main__":
    update_scores_from_y_tasks() 