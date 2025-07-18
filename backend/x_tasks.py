import csv
import json
import os
from datetime import datetime, timedelta

STANDARD_X_TASKS = ["Guarding Duties", "RASAR", "Kitchen"]

# Custom X tasks are stored in a JSON file: { soldier: [ { "task": ..., "start": ..., "end": ... } ] }
CUSTOM_X_TASKS_PATH = 'data/custom_x_tasks.json'
META_PATH = 'data/x_task_meta.json'

# --- Custom X Task Storage ---
def load_custom_x_tasks():
    if not os.path.exists(CUSTOM_X_TASKS_PATH):
        return {}
    with open(CUSTOM_X_TASKS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_custom_x_tasks(custom_tasks):
    with open(CUSTOM_X_TASKS_PATH, 'w', encoding='utf-8') as f:
        json.dump(custom_tasks, f, ensure_ascii=False, indent=2)

# --- Weekly Grid Logic ---
def load_soldiers(json_path='data/soldier_data.json'):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_weeks_for_period(start, end):
    weeks = []
    d = start
    week_num = 1
    while d < end:
        week_start = d
        week_end = min(week_start + timedelta(days=7), end)
        weeks.append((week_num, week_start, week_end))
        d = week_end
        week_num += 1
    return weeks

# --- CSV Generation ---
def save_x_tasks_to_csv(assignments, weeks, custom_tasks, year, half, csv_path='data/x_task.csv'):
    headers = ['name'] + [str(week_num) for week_num, _, _ in weeks]
    subheaders = [''] + [f"{ws.strftime('%d/%m')} - {we.strftime('%d/%m')}" for _, ws, we in weeks]
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerow(subheaders)
        for name, week_tasks in assignments.items():
            row = [name]
            for i, (week_num, ws, we) in enumerate(weeks):
                # Check for custom task overlap
                custom = None
                for entry in custom_tasks.get(name, []):
                    c_start = datetime.strptime(entry['start'], '%d/%m/%Y')
                    c_end = datetime.strptime(entry['end'], '%d/%m/%Y')
                    # If any overlap with this week
                    if not (we <= c_start or ws >= c_end):
                        custom = entry
                        break
                if custom:
                    label = f"{custom['task']}\n({custom['start']}-{custom['end']})"
                    row.append(label)
                else:
                    row.append(week_tasks.get(week_num, '-') or '-')
            writer.writerow(row)
    # Save year and half to metadata
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump({'year': year, 'half': half}, f)

def load_x_task_meta(meta_path=META_PATH):
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# --- Daily Expansion for Y Task Blocking ---
def expand_x_tasks_to_daily(assignments, weeks, custom_tasks):
    # Returns { soldier: { date: x_task or '-' } }
    daily = {}
    for name, week_tasks in assignments.items():
        daily[name] = {}
        for week_num, ws, we in weeks:
            # Fill with standard task by default
            task = week_tasks.get(week_num, '-')
            d = ws
            while d < we:
                daily[name][d.strftime('%d/%m/%Y')] = task
                d += timedelta(days=1)
        # Overwrite with custom tasks
        for entry in custom_tasks.get(name, []):
            c_start = datetime.strptime(entry['start'], '%d/%m/%Y')
            c_end = datetime.strptime(entry['end'], '%d/%m/%Y')
            d = c_start
            while d < c_end:
                daily[name][d.strftime('%d/%m/%Y')] = entry['task']
                d += timedelta(days=1)
    return daily

# --- CLI for testing ---
def input_x_tasks(weeks):
    assignments = {}
    print(f"Input X task assignments for {len(weeks)} weeks. Type 'done' as name to finish.")
    print("If you leave a week blank, it will be filled with '-' automatically.")
    while True:
        name = input("Soldier name (or 'done'): ").strip()
        if name.lower() == 'done':
            break
        if not name:
            continue
        if name not in assignments:
            assignments[name] = {}
        for i, (week_num, ws, we) in enumerate(weeks):
            week_label = f"Week {week_num} ({ws.strftime('%d/%m')} - {we.strftime('%d/%m')})"
            print(f"    Assign for {week_label}:")
            print(f"      1. Guarding Duties\n      2. RASAR\n      3. Kitchen\n      4. Other")
            choice = input("      Choose (1-4): ").strip()
            if choice in ['1', '2', '3']:
                assignments[name][week_num] = STANDARD_X_TASKS[int(choice)-1]
            elif choice == '4':
                task_name = input("        Enter custom task name: ").strip()
                date_start = input("        Start date (dd/mm/yyyy): ").strip()
                date_end = input("        End date (dd/mm/yyyy, exclusive): ").strip()
                # Save to custom tasks
                custom_tasks = load_custom_x_tasks()
                if name not in custom_tasks:
                    custom_tasks[name] = []
                custom_tasks[name].append({"task": task_name, "start": date_start, "end": date_end})
                save_custom_x_tasks(custom_tasks)
                assignments[name][week_num] = f"{task_name}\n({date_start}-{date_end})"
            else:
                assignments[name][week_num] = '-'
    return assignments

def main():
    year = int(input("Enter the starting year for the schedule (e.g. 2025): ").strip())
    half = int(input("Enter which half (1 for Jan-Jul, 2 for Jul-Jan): ").strip())
    if half == 1:
        start = datetime(year, 1, 7)
        end = datetime(year, 7, 7)
    else:
        start = datetime(year, 7, 7)
        end = datetime(year + 1, 1, 7)
    weeks = get_weeks_for_period(start, end)
    if os.path.exists('data/y_task.csv'):
        print("WARNING: A Y schedule (y_task.csv) already exists.")
        print("Updating X tasks may cause conflicts with the existing Y schedule.")
        print("It is recommended to regenerate the Y schedule after updating X tasks.\n")
    custom_tasks = load_custom_x_tasks()
    assignments = input_x_tasks(weeks)
    save_x_tasks_to_csv(assignments, weeks, custom_tasks, year, half)
    print(f"X task schedule saved to data/x_task.csv")

if __name__ == '__main__':
    main() 