import os
import csv
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
try:
    from .worker import load_workers_from_json, save_workers_to_json, EnhancedWorker
    from .engine import SchedulingEngineV2
    from .scoring import recalc_worker_schedule
except ImportError:
    from worker import load_workers_from_json, save_workers_to_json, EnhancedWorker
    from engine import SchedulingEngineV2
    from scoring import recalc_worker_schedule
import re

# --- Y Task Definitions ---
Y_TASKS = ["Southern Driver", "Southern Escort", "C&N Driver", "C&N Escort", "Supervisor"]
QUALIFICATION_MAP = {
    "Southern Driver": ["Southern Driver"],
    "Southern Escort": ["Southern Escort"],
    "C&N Driver": ["C&N Driver"],
    "C&N Escort": ["C&N Escort"],
    "Supervisor": ["Supervisor"]
}
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
INDEX_PATH = os.path.join(DATA_DIR, 'y_tasks.json')


# --- Y Task Index Management Utilities ---
def load_y_task_index() -> Dict[str, str]:
    """
    Loads the Y task index from the index file.

    Returns:
        Dict[str, str]: Mapping of period keys (start_to_end) to Y schedule filenames.
    """
    if not os.path.exists(INDEX_PATH):
        return {}
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_y_task_index(index: Dict[str, str]):
    """
    Saves the Y task index to the index file.

    Args:
        index (Dict[str, str]): The index mapping period keys to filenames.
    """
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def add_y_task_schedule(start: str, end: str, filename: str):
    """
    Adds a Y task schedule to the index and saves it.

    Args:
        start (str): Start date in dd/mm/yyyy.
        end (str): End date in dd/mm/yyyy.
        filename (str): The filename of the Y schedule CSV.
    """
    index = load_y_task_index()
    key = f"{start}_to_{end}"
    index[key] = filename
    save_y_task_index(index)


def find_y_task_file_for_date(date: str) -> Optional[str]:
    """
    Finds the Y schedule filename that covers a given date.

    Args:
        date (str): The date to search for (dd/mm/yyyy).
    Returns:
        Optional[str]: The filename if found, else None.
    """
    index = load_y_task_index()
    for key, fname in index.items():
        try:
            start, end = key.split('_to_')
            # All dates are in dd/mm/yyyy format
            d = datetime.strptime(date, '%d/%m/%Y').date()
            s = datetime.strptime(start, '%d/%m/%Y').date()
            e = datetime.strptime(end, '%d/%m/%Y').date()
            if s <= d <= e:
                return fname
        except Exception:
            continue
    return None


def list_y_task_schedules() -> List[Tuple[str, str, str]]:
    """
    Lists all Y schedule periods and their filenames.

    Returns:
        List[Tuple[str, str, str]]: List of (start, end, filename) tuples.
    """
    index = load_y_task_index()
    result = []
    for key, fname in index.items():
        try:
            start, end = key.split('_to_')
            result.append((start, end, fname))
        except Exception:
            continue
    return result


def y_schedule_path(filename: str) -> str:
    """
    Returns the full path to a Y schedule CSV file.

    Args:
        filename (str): The filename of the Y schedule CSV.
    Returns:
        str: The full path to the file.
    """
    # Always use sanitized filenames (with - instead of /)
    return os.path.join(DATA_DIR, filename)


# --- Utility Functions ---
def build_qualification_map(soldiers):
    """
    Builds a map of soldier IDs to their qualifications.
    Args:
        soldiers (list): List of Worker instances.
    Returns:
        dict: Mapping of soldier ID to list of qualifications.
    """
    return {s.id: s.qualifications for s in soldiers}


def get_weekday(date_str):
    """
    Returns the weekday index for a date string.

    Args:
        date_str (str): Date in dd/mm/yyyy format.
    Returns:
        int: Weekday index (0=Monday, 6=Sunday).
    """
    return datetime.strptime(date_str, '%d/%m/%Y').weekday()


def get_all_dates_from_x(csv_path, year=None):
    """
    Expands all week ranges in an X task CSV to daily dates (dd/mm/yyyy).

    Args:
        csv_path (str): Path to the X task CSV.
        year (int, optional): Year to use for date expansion. Defaults to None.
    Returns:
        list: List of all dates as dd/mm/yyyy strings.
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        subheaders = next(reader)
        if year is None:
            try:
                from backend.x_tasks import load_x_task_meta
                meta = load_x_task_meta()
                year = meta['year'] if meta else datetime.today().year
            except Exception:
                year = datetime.today().year
        period_starts = []
        for s in subheaders[1:]:
            start_str = s.split(' - ')[0]
            if len(start_str.split('/')) == 3:
                date_str = start_str
            else:
                date_str = f"{start_str}/{year}"
            period_starts.append(datetime.strptime(date_str, "%d/%m/%Y"))
        period_ends = period_starts[1:] + [period_starts[-1] + timedelta(days=7)]
        all_dates = []
        for start, end in zip(period_starts, period_ends):
            d = start
            while d < end:
                all_dates.append(d.strftime('%d/%m/%Y'))
                d += timedelta(days=1)
        return all_dates


def read_x_tasks(csv_path, year=None):
    """
    Reads X task assignments from a CSV and expands them to daily assignments.
    Args:
        csv_path (str): Path to the X task CSV.
        year (int, optional): Year to use for date expansion. Defaults to None.
    Returns:
        dict: Mapping of soldier ID to {date: x_task} assignments.
    """
    if not os.path.exists(csv_path):
        return {}
    x_assignments = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        subheaders = next(reader)
        if year is None:
            try:
                from backend.x_tasks import load_x_task_meta
                meta = load_x_task_meta()
                year = meta['year'] if meta else datetime.today().year
            except Exception:
                year = datetime.today().year
        period_starts = []
        for s in subheaders[1:]:
            if not s.strip():  # Skip empty subheaders
                continue
            start_str = s.split(' - ')[0].strip()
            if len(start_str.split('/')) == 3:
                date_str = start_str
            else:
                date_str = f"{start_str}/{year}"
            try:
                period_starts.append(datetime.strptime(date_str, "%d/%m/%Y"))
            except ValueError as e:
                print(f"Warning: Could not parse date '{date_str}' from subheader '{s}': {e}")
                continue
        period_ends = period_starts[1:] + [period_starts[-1] + timedelta(days=7)]

        for row in reader:
            if not row or not row[0].strip():
                continue
            soldier_id = row[0]  # Always use ID as key
            x_assignments[soldier_id] = {}

            # Skip the name column (index 1) and start from index 2
            for i, task in enumerate(row[2:], 0):  # Start from index 2, enumerate from 0
                if i >= len(period_starts):
                    break
                if task.strip() and task.strip() != '-':
                    start = period_starts[i]
                    end = period_ends[i]
                    d = start
                    while d < end:
                        day = d.strftime('%d/%m/%Y')
                        x_assignments[soldier_id][day] = task.strip()
                        d += timedelta(days=1)
    return x_assignments


# Remove all legacy assignment and scheduling logic below
# Only keep file I/O and API glue code as needed

# NEW: Y schedule generation using SchedulingEngineV2 with pre-computed closing dates

def generate_y_schedule(
        worker_json_path,
        x_task_data,
        start_date: date,
        end_date: date,
        y_task_names_by_day: dict
):
    """
    Generate Y task schedule using the new simplified scheduling engine.
    
    This function implements the new workflow:
    1. Load workers (with pre-computed optimal closing dates from X task updates)
    2. Use SchedulingEngineV2 for simplified, fair assignment
    3. Return schedule in the expected format for persistence
    
    Args:
        worker_json_path: Path to worker data JSON
        x_task_data: X task data (used for validation/conflict checking)
        start_date: Start date of scheduling period
        end_date: End date of scheduling period 
        y_task_names_by_day: Dict mapping dates to lists of Y task types needed
        
    Returns:
        Dict with date strings as keys and task assignments
    """
    # Load workers (they should already have optimal closing dates pre-computed)
    workers = load_workers_from_json(worker_json_path)
    
    print(f"🚀 Generating Y schedule with new engine for {len(workers)} workers")
    print(f"📅 Period: {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
    
    # Create the new scheduling engine
    engine = SchedulingEngineV2()
    
    # Convert y_task_names_by_day to the format expected by the new engine
    # Input format: {date_string: [task_types]}
    # Engine format: {date_object: [task_types]}
    weekday_tasks = {}
    for date_str, task_list in y_task_names_by_day.items():
        try:
            date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
            if start_date <= date_obj <= end_date:
                weekday_tasks[date_obj] = task_list
        except ValueError:
            print(f"⚠️  Skipping invalid date: {date_str}")
    
    print(f"📋 Scheduling {len(weekday_tasks)} days of Y tasks")
    
    # Use the new engine to generate the complete schedule
    result = engine.schedule_range(
        workers=workers,
        start=start_date,
        end=end_date,
        num_closers_per_weekend=2,  # Default to 2 closers per weekend
        weekday_tasks=weekday_tasks
    )
    
    # Extract Y task assignments and convert to expected format
    schedule_str = {}
    
    # Add Y task assignments
    for date_obj, assignments in result['y_tasks'].items():
        date_str = date_obj.strftime('%d/%m/%Y')
        if date_str not in schedule_str:
            schedule_str[date_str] = {}
        
        for task_type, worker_id in assignments:
            # Find worker name for the assignment
            worker_name = next((w.name for w in workers if w.id == worker_id), worker_id)
            schedule_str[date_str][task_type] = worker_name
    
    # Add weekend closing assignments 
    for friday_date, closer_ids in result['closers'].items():
        date_str = friday_date.strftime('%d/%m/%Y')
        if date_str not in schedule_str:
            schedule_str[date_str] = {}
        
        # Add closer assignments (can be multiple closers per weekend)
        for i, worker_id in enumerate(closer_ids):
            worker_name = next((w.name for w in workers if w.id == worker_id), worker_id)
            closer_key = "Weekend_Closer" if i == 0 else f"Weekend_Closer_{i+1}"
            schedule_str[date_str][closer_key] = worker_name
    
    # Save updated worker data (scores may have been updated)
    save_workers_to_json(workers, worker_json_path)
    
    # Print summary
    total_y_assignments = sum(len([k for k in tasks.keys() if not k.startswith("Weekend_Closer")]) 
                             for tasks in schedule_str.values())
    total_closers = sum(len([k for k in tasks.keys() if k.startswith("Weekend_Closer")]) 
                       for tasks in schedule_str.values())
    
    print(f"✅ Schedule generated successfully:")
    print(f"  📋 Y task assignments: {total_y_assignments}")
    print(f"  🏠 Weekend closers: {total_closers}")
    print(f"  📝 Logs: {len(result['logs'])} entries")
    
    # Show any important logs
    for log in result['logs'][:5]:  # Show first 5 log entries
        print(f"    • {log}")
    if len(result['logs']) > 5:
        print(f"    ... and {len(result['logs']) - 5} more")
    
    return schedule_str
