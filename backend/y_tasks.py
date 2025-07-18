"""
Y Task Generator - Refactored for Clarity

All data files (x_task.csv, y_task.csv, soldier_data.json) are stored in the 'data/' directory.
"""

import csv
import json
from datetime import datetime, timedelta
import os
from random import shuffle

# All data files are stored in the 'data/' directory.
Y_TASKS = ["Southern Driver", "Southern Escort", "C&N Driver", "C&N Escort", "Supervisor"]
# Map Y task names to the required qualification string
QUALIFICATION_MAP = {
    "Southern Driver": ["Southern Driver"],
    "Southern Escort": ["Southern Escort"],
    "C&N Driver": ["C&N Driver"],
    "C&N Escort": ["C&N Escort"],
    "Supervisor": ["Supervisor"]
}

# --- Configurable lookback window for Y task rotation ---
Y_TASK_LOOKBACK_DAYS = 3  # Change this value to adjust the lookback window

# --- X TASK SCHEDULE CONFIGURATION ---
# Map X task names to their start day (0=Mon, 1=Tue, ..., 6=Sun) and duration in days
X_TASK_SCHEDULES = {
    'Guarding Duties': {'start_day': 2, 'duration': 7},  # Wed (2), 7 days
    'RASAR': {'start_day': 0, 'duration': 7},  # Mon (0), 7 days
    'Kitchen': {'start_day': 0, 'duration': 7},  # Mon (0), 7 days
    # Add more X tasks here as needed
}


# Helper: Get weekday index from date string (dd/mm/yyyy)
def get_weekday(date_str):
    return datetime.strptime(date_str, '%d/%m/%Y').weekday()


# Expand weekly X schedule to daily schedule using X_TASK_SCHEDULES
def expand_x_schedule_to_daily(x_csv_path, all_dates, year=None):
    """
    Returns: {soldier_name: {date: x_task or '-'}}
    Expands period-based X schedule to daily assignments. Each period header is a start date, and the assignment covers all days from start (inclusive) to next period start (exclusive).
    """
    daily_x = {}
    with open(x_csv_path, 'r', encoding='utf-8') as f:
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
            daily_x[name] = {date: '-' for date in all_dates}
            for i, x_task in enumerate(row[1:]):
                x_task = x_task.strip()
                if not x_task or x_task == '-':
                    continue
                start = period_starts[i]
                end = period_ends[i]
                for d in all_dates:
                    d_dt = datetime.strptime(d, '%d/%m/%Y')
                    if start <= d_dt < end:
                        daily_x[name][d] = x_task
    return daily_x


def read_x_tasks(csv_path, year=None):
    x_assignments = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        subheaders = next(reader)
        # If year is not provided, try to infer from meta or use current year
        if year is None:
            try:
                from backend.x_tasks import load_x_task_meta
                meta = load_x_task_meta()
                year = meta['year'] if meta else datetime.today().year
            except Exception:
                year = datetime.today().year
        # Extract start dates from subheaders (e.g., '07/01 - 14/01')
        period_starts = []
        for s in subheaders[1:]:
            start_str = s.split(' - ')[0]
            # If already has year, use as is, else append year
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


def get_all_dates_from_x(csv_path, year=None):
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


def load_soldiers(soldier_json):
    with open(soldier_json, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_qualification_map(soldiers):
    return {s['name']: s.get('qualifications', []) for s in soldiers}


def get_preferred_y_assignments(date_list, soldier_names, y_tasks):
    """
    Ask the user for soldiers with Y task preferences and return a list of assignments:
    [{ 'name': ..., 'task': ..., 'days': [...] }]
    """
    prefs = []
    print('\nDo any soldiers have Y task preferences?')
    while True:
        resp = input("Enter 'yes' to add a preference, or 'no' to continue: ").strip().lower()
        if resp == 'no':
            break
        name = input(f"  Soldier name (must match exactly): ").strip()
        if name not in soldier_names:
            print(f"  Soldier '{name}' not found. Try again.")
            continue
        task = input(f"  Preferred Y task (choose from {y_tasks}): ").strip()
        if task not in y_tasks:
            print(f"  Y task '{task}' not found. Try again.")
            continue
        days_str = input(f"  Days for this preference (comma-separated, or 'all' for every day in range): ").strip()
        if days_str.lower() == 'all':
            days = date_list[:]
        else:
            days = [d.strip() for d in days_str.split(',') if d.strip() in date_list]
            if not days:
                print("  No valid days entered. Try again.")
                continue
        prefs.append({'name': name, 'task': task, 'days': days})
    return prefs


def manual_y_task_entry(date_list, soldier_names, y_tasks, y_assignments, x_assignments, soldier_qual, warnings):
    print('\nManual Y Task Entry:')
    print('You can assign Y tasks for any soldier and day in the selected date range.')
    print("Type 'done' as the soldier name to finish.")
    while True:
        name = input("Soldier name (or 'done'): ").strip()
        if name.lower() == 'done':
            break
        if name not in soldier_names:
            print(f"  Soldier '{name}' not found. Try again.")
            continue
        while True:
            date = input(f"  Date for {name} (dd/mm/yyyy, or 'done'): ").strip()
            if date.lower() == 'done':
                break
            if date not in date_list:
                print(f"  Date '{date}' not in selected range. Try again.")
                continue
            task = input(f"    Y task for {name} on {date} (choose from {y_tasks}, or '-' for none): ").strip()
            if task == '-':
                y_assignments[name][date] = '-'
                continue
            if task not in y_tasks:
                print(f"    Y task '{task}' not found. Try again.")
                continue
            # Conflict checks
            conflict = False
            if not any(q in QUALIFICATION_MAP[task] for q in soldier_qual[name]):
                warnings.append(f"{name} is not qualified for {task} on {date} (manual entry not assigned).")
                conflict = True
            if name in x_assignments and date in x_assignments[name]:
                warnings.append(f"{name} has an X task on {date} (manual entry for {task} not assigned).")
                conflict = True
            if y_assignments[name][date] != '-':
                warnings.append(f"{name} already assigned a Y task on {date} (manual entry for {task} not assigned).")
                conflict = True
            if not conflict:
                y_assignments[name][date] = task


def get_eligible_candidates(task, date, soldier_names, assigned_today, soldier_qual, x_assignments, y_assignments, last_y_task_day, date_list, day_idx, extra_dates=None):
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
    shuffle(candidates)
    return candidates


def generate_y_schedule(soldier_json='data/soldier_data.json', x_csv='data/x_task.csv', y_csv='data/y_task.csv', date_list=None, interactive=False):
    """
    Y schedule generator with lookback window for rotation.
    For each day and Y task, prefers to assign a soldier who has not done that Y task in the last N days.
    N is set by the global variable Y_TASK_LOOKBACK_DAYS.
    Only considers dates in date_list if provided.
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

    if interactive:
        # --- Preferred Y Task Assignments ---
        preferred_assignments = get_preferred_y_assignments(date_list, soldier_names, Y_TASKS)
        for pref in preferred_assignments:
            name, task, days = pref['name'], pref['task'], pref['days']
            for date in days:
                # Check for conflicts
                conflict = False
                if not any(q in QUALIFICATION_MAP[task] for q in soldier_qual[name]):
                    warnings.append(f"{name} is not qualified for {task} on {date} (preference not assigned).")
                    conflict = True
                if name in x_assignments and date in x_assignments[name]:
                    warnings.append(f"{name} has an X task on {date} (preference for {task} not assigned).")
                    conflict = True
                if y_assignments[name][date] != '-':
                    warnings.append(f"{name} already assigned a Y task on {date} (preference for {task} not assigned).")
                    conflict = True
                if not conflict:
                    y_assignments[name][date] = task
                    last_y_task_day[name][task] = date
        # --- Manual Y Task Entry ---
        manual_y_task_entry(date_list, soldier_names, Y_TASKS, y_assignments, x_assignments, soldier_qual, warnings)

    for day_idx, date in enumerate(date_list):
        assigned_today = set()
        weekday = datetime.strptime(date, '%d/%m/%Y').weekday()
        # If Thursday, assign for Thursday, Friday, and Saturday
        if weekday == 3:  # Thursday
            friday_dt = datetime.strptime(date, '%d/%m/%Y') + timedelta(days=1)
            friday = friday_dt.strftime('%d/%m/%Y')
            saturday_dt = friday_dt + timedelta(days=1)
            saturday = saturday_dt.strftime('%d/%m/%Y')
            if friday not in date_list or saturday not in date_list:
                continue
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
            continue  # Skip Friday and Saturday, as they're already assigned
        if weekday in [4, 5]:  # Friday or Saturday, skip (already assigned on Thursday loop)
            continue
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
    # Write the Y schedule to CSV
    headers = ['Name'] + date_list
    with open(y_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for name in soldier_names:
            row = [name] + [y_assignments[name][date] for date in date_list]
            writer.writerow(row)
    print(f"Y task schedule saved to {y_csv}")
    return y_assignments, date_list, soldier_names, warnings


def merge_x_y_csvs(x_csv_path, y_csv_path, output_csv_path):
    """
    Merges X and Y task CSVs into a combined schedule CSV.
    Expands weekly X schedule to daily using X_TASK_SCHEDULES.
    """
    # Read Y CSV
    with open(y_csv_path, newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        y_header = reader[0]
        y_data = {row[0]: row[1:] for row in reader[1:]}
    all_dates = y_header[1:]
    # Expand X schedule to daily
    daily_x = expand_x_schedule_to_daily(x_csv_path, all_dates)
    # Merge rows
    merged_rows = []
    for name in y_data:
        y_row = y_data[name]
        x_row = [daily_x.get(name, {}).get(date, '-') for date in all_dates]
        merged_row = [name]
        for x_task, y_task in zip(x_row, y_row):
            if x_task != '-' and y_task != '-':
                merged_cell = f"{x_task} / {y_task}"
            elif x_task != '-':
                merged_cell = x_task
            elif y_task != '-':
                merged_cell = y_task
            else:
                merged_cell = '-'
            merged_row.append(merged_cell)
        merged_rows.append(merged_row)
    # Write merged CSV
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name'] + all_dates)
        writer.writerows(merged_rows)
    print(f"Combined schedule written to {output_csv_path}")


def get_date_range_from_user(all_dates):
    from datetime import datetime, timedelta
    def parse_date(s):
        return datetime.strptime(s, '%d/%m/%Y')
    while True:
        start_str = input('Enter the start date for the Y schedule (dd/mm/yyyy): ').strip()
        end_str = input('Enter the end date for the Y schedule (dd/mm/yyyy): ').strip()
        try:
            start = parse_date(start_str)
            end = parse_date(end_str)
            if start > end:
                print('Start date must be before or equal to end date.')
                continue
            all_dates_set = set(all_dates)
            date_list = [(start + timedelta(days=i)).strftime('%d/%m/%Y') for i in range((end - start).days + 1)]
            if not all(d in all_dates_set for d in date_list):
                print('Error: The selected date range is not fully covered by the X schedule. Please choose a different range.')
                continue
            return date_list
        except Exception as e:
            print('Invalid date format or range. Please use dd/mm/yyyy.')


# --- Script Entry Point ---
if __name__ == '__main__':
    print('--- Y Task Schedule Generator ---')
    all_dates = get_all_dates_from_x('data/x_task.csv')
    print('Step 1: Select the date range for the Y schedule.')
    date_list = get_date_range_from_user(all_dates)
    print('\nStep 2: Assign any preferred Y tasks for specific soldiers (optional).')
    print('You will be able to enter preferences for any soldier, Y task, and days.')
    print('If there are no preferences, just type "no" when prompted.')
    print('\nStep 3: Manual Y task entry (optional).')
    print('You can manually assign Y tasks for any soldier and day. If you want to skip, just type "done".')
    print('\nStep 4: The system will automatically fill the rest of the schedule.')
    print('---')
    y_assignments, date_list, soldier_names, warnings = generate_y_schedule(date_list=date_list, interactive=True)
    print('\n--- Schedule generation complete. Review any warnings above for conflicts or unassigned tasks. ---')
    merge_x_y_csvs('data/x_task.csv', 'data/y_task.csv', 'data/combined_schedule.csv')
