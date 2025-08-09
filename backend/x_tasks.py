import csv
import json
import os
from datetime import datetime, timedelta, date
try:
    from .worker import load_workers_from_json, save_workers_to_json, EnhancedWorker
    from .scoring import recalc_worker_schedule
    from .closing_schedule_calculator import ClosingScheduleCalculator
except ImportError:
    from worker import load_workers_from_json, save_workers_to_json, EnhancedWorker
    from scoring import recalc_worker_schedule
    from closing_schedule_calculator import ClosingScheduleCalculator

STANDARD_X_TASKS = ["Guarding Duties", "RASAR", "Kitchen"]

# Custom X tasks are stored in a JSON file: { soldier: [ { "task": ..., "start": ..., "end": ... } ] }
CUSTOM_X_TASKS_PATH = 'data/custom_x_tasks.json'
META_PATH = 'data/x_task_meta.json'
WORKER_DATA = 'data/worker_data.json'


# --- Utility Functions ---
def parse_date(s):
    """Parse a date string in dd/mm/yyyy format to a date object."""
    if isinstance(s, date):
        return s
    return datetime.strptime(s, '%d/%m/%Y').date()


def date_range_overlap(start1, end1, start2, end2):
    """Return True if [start1, end1] and [start2, end2] overlap (inclusive)."""
    # print(f"[DEBUG] Checking date range overlap: {start1} - {end1} and {start2} - {end2}")
    return start1 <= end2 and end1 >= start2


# --- Custom X Task Storage ---
def load_custom_x_tasks():
    """
    Loads custom X tasks from the JSON file.
    Returns:
        dict: Mapping of soldier ID to list of custom task dicts.
    """
    if not os.path.exists(CUSTOM_X_TASKS_PATH):
        return {}
    with open(CUSTOM_X_TASKS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_custom_x_tasks(custom_tasks):
    """
    Saves custom X tasks to the JSON file.
    Args:
        custom_tasks (dict): Mapping of soldier ID to list of custom task dicts.
    """
    # print(f"[DEBUG] Saving custom X tasks to {custom_tasks}")
    with open(CUSTOM_X_TASKS_PATH, 'w', encoding='utf-8') as f:
        json.dump(custom_tasks, f, ensure_ascii=False, indent=2)


def trigger_closing_schedule_recalc(affected_worker_ids=None, year=None, half=None):
    """
    NEW: Trigger recalculation of optimal closing dates after X task changes.
    
    This function implements the new workflow where X task updates immediately
    trigger pre-computation of optimal closing dates.
    
    Args:
        affected_worker_ids: List of worker IDs to recalculate (None = all workers)
        year: Year for semester weeks calculation
        half: Half (1 or 2) for semester weeks calculation
    """
    try:
        # Load workers
        workers = load_workers_from_json(WORKER_DATA)
        
        # Filter to affected workers if specified
        if affected_worker_ids:
            workers = [w for w in workers if w.id in affected_worker_ids]
        
        if not workers:
            print("No workers to recalculate")
            return
        
        # Determine semester weeks
        if year and half:
            weeks_data = get_weeks_for_period(year, half)
            # Convert to Friday dates for the calculator (it expects Fridays)
            semester_weeks = []
            for week_num, week_start, week_end in weeks_data:
                # Find Friday in this week (week_start is Sunday, so Friday is +5 days)
                friday = week_start + timedelta(days=5)
                semester_weeks.append(friday)
        else:
            # Use a default range if no year/half specified
            start_date = date.today()
            semester_weeks = [start_date + timedelta(weeks=i) for i in range(26)]
        
        # Recalculate closing schedules
        calc = ClosingScheduleCalculator()
        calc.debug = False  # Reduce console output
        calc.update_all_worker_schedules(workers, semester_weeks)
        
        # Save updated workers back to JSON
        save_workers_to_json(workers, WORKER_DATA)
        
        print(f"✅ Recalculated closing schedules for {len(workers)} workers")
        
        # Return any alerts for the caller
        return calc.get_user_alerts()
        
    except Exception as e:
        print(f"❌ Error recalculating closing schedules: {e}")
        return []


# --- Weekly Grid Logic ---
def load_soldiers(json_path='data/worker_data.json', name_conv_path='data/name_conv.json'):
    return load_workers_from_json(json_path, name_conv_path)


def get_weeks_for_period(year, half):
    """
    Generate 26 weeks for the given year and half.
    Half 1: First Sunday in January, 26 weeks, ends on Saturday.
    Half 2: Next Sunday, 26 weeks, ends on last Saturday before first Sunday of next January.
    Returns list of (week_num, week_start, week_end) with week_end inclusive (Saturday).
    """
    # Find first Sunday in January
    d = date(year, 1, 1)
    while d.weekday() != 6:
        d += timedelta(days=1)
    if half == 1:
        start = d
        end = start + timedelta(weeks=26) - timedelta(days=1)  # 26 weeks, end on Saturday
    else:
        first_half_end = d + timedelta(weeks=26) - timedelta(days=1)
        start = first_half_end + timedelta(days=1)  # Next Sunday
        # Find first Sunday of next January
        next_jan = date(year + 1, 1, 1)

        while next_jan.weekday() != 6:
            next_jan += timedelta(days=1)
        end = next_jan - timedelta(days=1)  # Last Saturday before next first Sunday

    # Generate weeks
    weeks = []
    week_num = 1
    cur = start
    while cur <= end:
        week_start = cur
        week_end = min(week_start + timedelta(days=6), end)
        weeks.append((week_num, week_start, week_end))
        cur = week_end + timedelta(days=1)
        week_num += 1

    #     # TODO: Remove this
    #     print(f"[DEBUG] Week {week_num}: {week_start} - {week_end}")
    # # TODO: Remove this
    # print(f"[DEBUG] Weeks: {weeks}")

    return weeks


# --- CSV Generation ---
def save_x_tasks_to_csv(assignments, weeks, custom_tasks, year, half, csv_path='data/x_task.csv'):
    """
    Saves X task assignments and custom tasks to a CSV file for display.
    UPDATED: Now triggers recalculation of optimal closing dates after saving.
    
    First column: 'שם' (Hebrew name), then week columns as '1 (06/07-12/07)', ...
    Args:
        assignments (dict): Mapping of soldier ID to week assignments.
        weeks (list): List of week tuples.
        custom_tasks (dict): Mapping of soldier ID to custom tasks.
        year (int): The year of the schedule.
        half (int): The half (1 or 2) of the year.
        csv_path (str): Path to save the CSV file.
    """
    # Load id-to-Hebrew name mapping
    name_conv_path = 'data/name_conv.json'
    if os.path.exists(name_conv_path):
        with open(name_conv_path, 'r', encoding='utf-8') as f:
            name_conv_list = json.load(f)
        id_to_hebrew = {}
        for entry in name_conv_list:
            for k, v in entry.items():
                id_to_hebrew[k] = v

    else:
        id_to_hebrew = {}
    headers = ['שם'] + [f'{week_num} ({ws.strftime("%d/%m")}-{we.strftime("%d/%m")})' for week_num, ws, we in weeks]
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for soldier_id, week_tasks in assignments.items():
            hebrew_name = id_to_hebrew.get(soldier_id, soldier_id)
            row = [hebrew_name]
            for i, (week_num, ws, we) in enumerate(weeks):
                custom = None
                for entry in custom_tasks.get(soldier_id, []):
                    c_start = parse_date(entry['start'])
                    c_end = parse_date(entry['end'])
                    if date_range_overlap(ws, we, c_start, c_end):
                        custom = entry
                        break
                if custom:
                    label = f"{custom['task']}"
                    row.append(label)
                else:
                    row.append(week_tasks.get(week_num, '') or '')
            writer.writerow(row)
    # Save meta
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump({'year': year, 'half': half}, f)
    
    # NEW: Trigger recalculation of optimal closing dates for all affected workers
    affected_workers = set(assignments.keys()) | set(custom_tasks.keys())
    if affected_workers:
        print(f"🔄 Triggering closing schedule recalculation for {len(affected_workers)} workers...")
        alerts = trigger_closing_schedule_recalc(list(affected_workers), year, half)
        if alerts:
            print(f"⚠️  Closing schedule alerts: {len(alerts)} issues detected")
            for alert in alerts[:3]:  # Show first 3 alerts
                print(f"  • {alert}")
            if len(alerts) > 3:
                print(f"  ... and {len(alerts) - 3} more")
    else:
        print("No workers affected, skipping closing schedule recalculation")


def load_x_task_meta(meta_path=META_PATH):
    """
    Loads X task schedule metadata (year and half).

    Args:
        meta_path (str): Path to the metadata JSON file.
    Returns:
        dict or None: Metadata dict if exists, else None.
    """
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)
