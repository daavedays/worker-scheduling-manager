import os
import csv
import json
from datetime import datetime, timedelta
from random import shuffle
from typing import List, Dict, Optional, Tuple
from backend.x_tasks import load_soldiers

# --- Y Task Definitions ---
Y_TASKS = ["Southern Driver", "Southern Escort", "C&N Driver", "C&N Escort", "Supervisor"]
QUALIFICATION_MAP = {
    "Southern Driver": ["Southern Driver"],
    "Southern Escort": ["Southern Escort"],
    "C&N Driver": ["C&N Driver"],
    "C&N Escort": ["C&N Escort"],
    "Supervisor": ["Supervisor"]
}
Y_TASK_LOOKBACK_DAYS = 3  # For fairness in rotation

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
    Builds a map of soldier names to their qualifications.

    Args:
        soldiers (list): List of soldier dicts.
    Returns:
        dict: Mapping of soldier name to list of qualifications.
    """
    return {s['name']: s.get('qualifications', []) for s in soldiers}

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
        dict: Mapping of soldier name to {date: x_task} assignments.
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
            start_str = s.split(' - ')[0]
            if len(start_str.split('/')) == 3:
                date_str = start_str
            else:
                date_str = f"{start_str}/{year}"
            period_starts.append(datetime.strptime(date_str, "%d/%m/%Y"))
        period_ends = period_starts[1:] + [period_starts[-1] + timedelta(days=7)]
        for row in reader:
            if not row or not row[0].strip():
                continue
            name = row[0]
            x_assignments[name] = {}
            for i, task in enumerate(row[1:]):
                if task.strip() and task.strip() != '-':
                    start = period_starts[i]
                    end = period_ends[i]
                    d = start
                    while d < end:
                        day = d.strftime('%d/%m/%Y')
                        x_assignments[name][day] = task.strip()
                        d += timedelta(days=1)
    return x_assignments

def get_eligible_candidates(task, date, soldier_names, assigned_today,
 soldier_qual, x_assignments, y_assignments, last_y_task_day,
  date_list, day_idx, extra_dates=None):
    """
    Returns a shuffled list of eligible candidates for a Y task on a given date.
    Filters by qualification, X-task conflicts, and Y-task recency.

    Args:
        task (str): The Y task name.
        date (str): The date.
        soldier_names (list): List of soldier names.
        assigned_today (set): Set of already assigned soldiers for the day.
        soldier_qual (dict): Map of soldier name to qualifications.
        x_assignments (dict): X task assignments.
        y_assignments (dict): Y task assignments.
        last_y_task_day (dict): Last day each soldier did each Y task.
        date_list (list): List of all dates.
        day_idx (int): Index of the current day in date_list.
        extra_dates (list, optional): Additional dates to check for conflicts.
    Returns:
        list: List of eligible soldier names (shuffled).
    """
    # 1. Filter by qualification
    qualified = [n for n in soldier_names if n not in assigned_today and any(q in QUALIFICATION_MAP[task] for q in soldier_qual[n])]
    # 2. Filter by X-task conflicts (for all relevant dates)
    if extra_dates is None:
        extra_dates = [date]
    available = [n for n in qualified if all(not (n in x_assignments and d in x_assignments[n]) for d in extra_dates)]
    # 3. Filter by Y-task recency
    not_recent = []
    for n in available:
        last_idx = None
        if last_y_task_day[n][task]:
            try:
                last_idx = date_list.index(last_y_task_day[n][task])
            except ValueError:
                last_idx = None
        if last_idx is None or day_idx - last_idx >= Y_TASK_LOOKBACK_DAYS:
            not_recent.append(n)
    # 4. Prefer not_recent, but fallback to available
    candidates = not_recent if not_recent else available

    # TODO: instead of using the shufle, add further complications to find specific soldiers for the tasks. 
    shuffle(candidates)

    return candidates

def assign_y_tasks_for_day(date, day_idx, y_assignments, assigned_today, soldier_names, soldier_qual, x_assignments, last_y_task_day, date_list, warnings):
    """
    Assigns Y tasks for a single day, skipping Fri/Sat (handled in Thu block).

    Args:
        date (str): The date.
        day_idx (int): Index of the day in date_list.
        y_assignments (dict): Y task assignments.
        assigned_today (set): Set of already assigned soldiers for the day.
        soldier_names (list): List of soldier names.
        soldier_qual (dict): Map of soldier name to qualifications.
        x_assignments (dict): X task assignments.
        last_y_task_day (dict): Last day each soldier did each Y task.
        date_list (list): List of all dates.
        warnings (list): List to append warnings to.
    """
    for task in Y_TASKS:
        candidates = get_eligible_candidates(
            task, date, soldier_names, assigned_today, soldier_qual, x_assignments, y_assignments, last_y_task_day, date_list, day_idx
        )
        if candidates:
            chosen = candidates[0]
            y_assignments[chosen][date] = task
            assigned_today.add(chosen)
            last_y_task_day[chosen][task] = date
        else:
            warnings.append(f"No qualified soldier for {task} on {date}.")

def assign_y_tasks_for_thursday(date, day_idx, y_assignments, assigned_today, soldier_names, soldier_qual, x_assignments, last_y_task_day, date_list, warnings):
    """
    Assigns Y tasks for Thu, Fri, Sat as a block.
    TODO 1) Add further complications of choosing the correct person to close in accordance to closing intervals.
    TODO 2) Ensure soldiers who have been assigned to weekends with prefrences do the same task for thur, fri, sat.


    Args:
        date (str): The Thursday date.
        day_idx (int): Index of the day in date_list.
        y_assignments (dict): Y task assignments.
        assigned_today (set): Set of already assigned soldiers for the day.
        soldier_names (list): List of soldier names.
        soldier_qual (dict): Map of soldier name to qualifications.
        x_assignments (dict): X task assignments.
        last_y_task_day (dict): Last day each soldier did each Y task.
        date_list (list): List of all dates.
        warnings (list): List to append warnings to.
    """
    friday_dt = datetime.strptime(date, '%d/%m/%Y') + timedelta(days=1)
    friday = friday_dt.strftime('%d/%m/%Y')
    saturday_dt = friday_dt + timedelta(days=1)
    saturday = saturday_dt.strftime('%d/%m/%Y')
    if friday not in date_list or saturday not in date_list:
        return
    for task in Y_TASKS:
        candidates = get_eligible_candidates(
            task, date, soldier_names, assigned_today, soldier_qual, x_assignments, y_assignments, last_y_task_day, date_list, day_idx, extra_dates=[date, friday, saturday]
        )
        if candidates:
            chosen = candidates[0]
            y_assignments[chosen][date] = task
            y_assignments[chosen][friday] = task
            y_assignments[chosen][saturday] = task
            assigned_today.add(chosen)
            last_y_task_day[chosen][task] = saturday  # Saturday is the most recent
        else:
            warnings.append(f"No qualified soldier for {task} on {date}, {friday}, and {saturday}.")

# --- Main Y Task Generation Function ---
def generate_y_schedule(
    soldier_json=os.path.join(DATA_DIR, 'soldier_data.json'),
    x_csv=os.path.join(DATA_DIR, 'x_task.csv'),
    y_csv: Optional[str] = None,
    date_list=None,
    interactive=False
):
    """
    Automatic Y schedule generator with fairness and conflict checks.
    Assigns Y tasks for each day in date_list (or all days in X schedule if not provided).
    Skips Fri/Sat (assigned in Thu block).
    Respects qualifications, X-task conflicts, and recent Y task assignments.

    Args:
        soldier_json (str): Path to soldier data JSON.
        x_csv (str): Path to X task CSV.
        y_csv (str, optional): Path to output Y task CSV. Defaults to None.
        date_list (list, optional): List of dates to schedule. Defaults to None.
        interactive (bool, optional): If True, run interactively. Defaults to False.
    Returns:
        tuple: (y_assignments, date_list, soldier_names, warnings)
    """
    soldiers = load_soldiers(soldier_json)
    x_assignments = read_x_tasks(x_csv)
    all_dates = get_all_dates_from_x(x_csv)
    if date_list is None:
        date_list = all_dates
    soldier_names = [s['name'] for s in soldiers]
    shuffle(soldier_names)
    soldier_qual = build_qualification_map(soldiers)
    y_assignments = {name: {date: '-' for date in date_list} for name in soldier_names}
    warnings = []
    last_y_task_day = {name: {task: '' for task in Y_TASKS} for name in soldier_names}

    for day_idx, date in enumerate(date_list):
        assigned_today = set()
        weekday = datetime.strptime(date, '%d/%m/%Y').weekday()
        if weekday == 3:  # Thursday
            assign_y_tasks_for_thursday(date, day_idx, y_assignments, assigned_today, soldier_names, soldier_qual, x_assignments, last_y_task_day, date_list, warnings)
            continue  # Skip Friday and Saturday, as they're already assigned
        if weekday in [4, 5]:  # Friday or Saturday
            continue
        assign_y_tasks_for_day(date, day_idx, y_assignments, assigned_today, soldier_names, soldier_qual, x_assignments, last_y_task_day, date_list, warnings)

    # Only write to file if y_csv is not None
    if y_csv:
        headers = ['Name'] + date_list
        with open(y_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for name in soldier_names:
                row = [name] + [y_assignments[name][date] for date in date_list]
                writer.writerow(row)
    return y_assignments, date_list, soldier_names, warnings 