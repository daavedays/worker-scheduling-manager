import json
import os

def reset_all_data():
    """Reset all worker data including assignments, history, and scores"""
    print("=== RESETTING ALL WORKER DATA ===")
    
    # Load worker data
    try:
        with open('worker_data.json', 'r', encoding='utf-8') as file:
            worker_data = json.load(file)
        print(f"Loaded {len(worker_data)} workers")
    except FileNotFoundError:
        print("Error: worker_data.json not found")
        return
    except Exception as e:
        print(f"Error loading worker data: {e}")
        return
    
    # Reset all worker data
    for worker in worker_data:
        # Reset assignments
        worker['x_tasks'] = {}
        worker['y_tasks'] = {}
        worker['closing_history'] = []
        
        # Reset scores
        worker['score'] = 0
        
        # Reset tallies (if they exist)
        if 'x_task_count' in worker:
            worker['x_task_count'] = 0
        if 'y_task_count' in worker:
            worker['y_task_count'] = 0
        if 'closing_delta' in worker:
            worker['closing_delta'] = 0
    
    # Save reset data back to file
    try:
        with open('worker_data.json', 'w', encoding='utf-8') as file:
            json.dump(worker_data, file, indent=2, ensure_ascii=False)
        print("✅ Successfully reset all worker data")
        print("   - Cleared all X task assignments")
        print("   - Cleared all Y task assignments") 
        print("   - Cleared all closing history")
        print("   - Reset all worker scores to 0")
        print("   - Reset all task tallies")
    except Exception as e:
        print(f"Error saving reset data: {e}")

def reset_x_tasks_only():
    """Reset only X task assignments"""
    print("=== RESETTING X TASKS ONLY ===")
    
    try:
        with open('worker_data.json', 'r', encoding='utf-8') as file:
            worker_data = json.load(file)
        print(f"Loaded {len(worker_data)} workers")
    except FileNotFoundError:
        print("Error: worker_data.json not found")
        return
    except Exception as e:
        print(f"Error loading worker data: {e}")
        return
    
    # Reset only X tasks
    for worker in worker_data:
        worker['x_tasks'] = {}
        if 'x_task_count' in worker:
            worker['x_task_count'] = 0
    
    # Save reset data back to file
    try:
        with open('worker_data.json', 'w', encoding='utf-8') as file:
            json.dump(worker_data, file, indent=2, ensure_ascii=False)
        print("✅ Successfully reset X task assignments")
    except Exception as e:
        print(f"Error saving reset data: {e}")

def reset_y_tasks_only():
    """Reset only Y task assignments"""
    print("=== RESETTING Y TASKS ONLY ===")
    
    try:
        with open('worker_data.json', 'r', encoding='utf-8') as file:
            worker_data = json.load(file)
        print(f"Loaded {len(worker_data)} workers")
    except FileNotFoundError:
        print("Error: worker_data.json not found")
        return
    except Exception as e:
        print(f"Error loading worker data: {e}")
        return
    
    # Reset only Y tasks
    for worker in worker_data:
        worker['y_tasks'] = {}
        if 'y_task_count' in worker:
            worker['y_task_count'] = 0
    
    # Save reset data back to file
    try:
        with open('worker_data.json', 'w', encoding='utf-8') as file:
            json.dump(worker_data, file, indent=2, ensure_ascii=False)
        print("✅ Successfully reset Y task assignments")
    except Exception as e:
        print(f"Error saving reset data: {e}")

def reset_closing_history_only():
    """Reset only closing history"""
    print("=== RESETTING CLOSING HISTORY ONLY ===")
    
    try:
        with open('worker_data.json', 'r', encoding='utf-8') as file:
            worker_data = json.load(file)
        print(f"Loaded {len(worker_data)} workers")
    except FileNotFoundError:
        print("Error: worker_data.json not found")
        return
    except Exception as e:
        print(f"Error loading worker data: {e}")
        return
    
    # Reset only closing history
    for worker in worker_data:
        worker['closing_history'] = []
        if 'closing_delta' in worker:
            worker['closing_delta'] = 0
    
    # Save reset data back to file
    try:
        with open('worker_data.json', 'w', encoding='utf-8') as file:
            json.dump(worker_data, file, indent=2, ensure_ascii=False)
        print("✅ Successfully reset closing history")
    except Exception as e:
        print(f"Error saving reset data: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        reset_type = sys.argv[1].lower()
        if reset_type == "x":
            reset_x_tasks_only()
        elif reset_type == "y":
            reset_y_tasks_only()
        elif reset_type == "closing":
            reset_closing_history_only()
        elif reset_type == "all":
            reset_all_data()
        else:
            print("Usage: python reset_data.py [all|x|y|closing]")
            print("  all     - Reset all data (default)")
            print("  x       - Reset only X tasks")
            print("  y       - Reset only Y tasks")
            print("  closing - Reset only closing history")
    else:
        # Default: reset all data
        reset_all_data()



