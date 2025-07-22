# Config
SESSION_TIMEOUT_MINUTES = 30

import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory, Response
from flask_cors import CORS
import backend.x_tasks as x_tasks
import backend.y_tasks as y_tasks
import threading
from typing import Optional
HISTORY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'history.json')
history_lock = threading.Lock()

from backend.worker import Worker, load_workers_from_json
from backend.scheduler_engine import SchedulerEngine


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'super_secret_key_for_local_dev'  # Change for production
app.permanent_session_lifetime = timedelta(minutes=SESSION_TIMEOUT_MINUTES)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
USERS = {
    'bossy_bobby': 'QWE123..',
    'Dav': '8320845',
}

# --- Auth Helpers ---
def is_logged_in():
    """
    Checks if the current user session is logged in and not expired.

    Returns:
        bool: True if logged in and session is valid, False otherwise.
    """
    # Flask's session is always available as a dict
    user = session.get('user')
    expires_at = session.get('expires_at')
    if not user or not expires_at:
        return False
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.strptime(expires_at, '%Y-%m-%dT%H:%M:%S.%f')
        except Exception:
            return False
    return datetime.utcnow() < expires_at

def require_login():
    """
    Returns a 401 Unauthorized response for unauthenticated requests.

    Returns:
        Response: Flask JSON response with error message and 401 status.
    """
    return jsonify({'error': 'Authentication required'}), 401

# --- Auth Endpoints ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if username in USERS and USERS[username] == password:
        session['user'] = username
        session['expires_at'] = (datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
        session.permanent = True
        return jsonify({'success': True, 'user': username})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/session', methods=['GET'])
def check_session():
    if is_logged_in():
        # Refresh session expiry
        session['expires_at'] = (datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)).isoformat()
        return jsonify({'logged_in': True, 'user': session['user']})
    session.clear()
    return jsonify({'logged_in': False})

# --- X Task API ---
@app.route('/api/x-tasks', methods=['GET'])
def get_x_tasks():
    if not is_logged_in():
        return require_login()
    year = int(request.args.get('year', datetime.today().year))
    period = int(request.args.get('period', 1))
    filename = f"x_tasks_{year}_{period}.csv"
    path = os.path.join(DATA_DIR, filename)
    import io, csv, json
    from backend import x_tasks
    # If file does not exist or is empty, generate blank grid with weekly headers
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        workers = x_tasks.load_soldiers(os.path.join(DATA_DIR, 'worker_data.json'))
        weeks = x_tasks.get_weeks_for_period(year, period)
        headers = ['id', 'name'] + [str(week_num) for week_num, _, _ in weeks]
        subheaders = ['', ''] + [f"{ws.strftime('%d/%m')} - {we.strftime('%d/%m')}" for _, ws, we in weeks]
        rows = []
        for w in workers:
            row = [w.id, w.name] + ['' for _ in range(len(weeks))]
            rows.append(row)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(subheaders)
        writer.writerows(rows)
        csv_data = output.getvalue()
        custom_tasks = x_tasks.load_custom_x_tasks()
        return jsonify({"csv": csv_data, "custom_tasks": custom_tasks, "year": year, "half": period})
    else:
        with open(path, 'r', encoding='utf-8') as f:
            csv_data = f.read()
    custom_tasks = x_tasks.load_custom_x_tasks()
    return jsonify({"csv": csv_data, "custom_tasks": custom_tasks, "year": year, "half": period})

@app.route('/api/x-tasks', methods=['POST'])
def save_x_tasks():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    csv_data = data.get('csv')
    custom_tasks = data.get('custom_tasks', {})
    year = int(data.get('year', datetime.today().year))
    period = int(data.get('half', 1))
    if not csv_data or not year or not period:
        return jsonify({'error': 'Missing data'}), 400
    # Save CSV
    filename = f"x_tasks_{year}_{period}.csv"
    x_task_path = os.path.join(DATA_DIR, filename)
    with open(x_task_path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    # Save custom tasks
    import backend.x_tasks as x_tasks
    x_tasks.save_custom_x_tasks(custom_tasks)
    # Save year/half meta (optional, can be removed if not needed)
    meta_path = os.path.join(DATA_DIR, 'x_task_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        import json
        json.dump({'year': year, 'half': period}, f)
    return jsonify({'success': True})

@app.route('/api/x-tasks/exists', methods=['GET'])
def x_tasks_exists():
    if not is_logged_in():
        return require_login()
    year = int(request.args.get('year', datetime.today().year))
    period = int(request.args.get('period', 1))
    filename = f"x_tasks_{year}_{period}.csv"
    path = os.path.join(DATA_DIR, filename)
    exists = os.path.exists(path) and os.stat(path).st_size > 0
    return jsonify({'exists': exists})

def log_history(event):
    with history_lock:
        if not os.path.exists(HISTORY_PATH):
            history = []
        else:
            with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except Exception:
                    history = []
        history.append({
            'event': event,
            'timestamp': datetime.utcnow().isoformat()
        })
        with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

# --- Warnings API ---
@app.route('/api/warnings', methods=['GET'])
def get_warnings():
    if not is_logged_in():
        return require_login()
    warnings = []
    # X/Y conflicts and unassigned tasks
    try:
        # Check Y schedule
        y_path = os.path.join(DATA_DIR, 'y_task.csv')
        if os.path.exists(y_path) and os.stat(y_path).st_size > 0:
            import csv
            with open(y_path, 'r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
                headers = reader[0][1:]
                rows = reader[1:]
                assignments = {row[0]: row[1:] for row in rows}
                # Unassigned tasks
                for i, date in enumerate(headers):
                    assigned = set()
                    for name, vals in assignments.items():
                        if vals[i] and vals[i] != '-':
                            assigned.add(vals[i])
                    for task in ['Supervisor', 'C&N Driver', 'C&N Escort', 'Southern Driver', 'Southern Escort']:
                        if task not in assigned:
                            warnings.append(f"No {task} assigned on {date}.")
                # Overwork: count tasks per soldier
                task_counts = {name: sum(1 for v in vals if v and v != '-') for name, vals in assignments.items()}
                for name, count in task_counts.items():
                    if count > len(headers) * 0.8:  # Arbitrary threshold
                        warnings.append(f"{name} may be overworked: assigned {count} Y tasks.")
        # Check X/Y conflicts
        x_path = os.path.join(DATA_DIR, 'x_task.csv')
        if os.path.exists(x_path) and os.path.exists(y_path):
            import csv
            from backend import y_tasks
            x_assignments = y_tasks.read_x_tasks(x_path)
            with open(y_path, 'r', encoding='utf-8') as f:
                reader = list(csv.reader(f))
                headers = reader[0][1:]
                rows = reader[1:]
                for row in rows:
                    name = row[0]
                    for i, date in enumerate(headers):
                        y_task = row[i+1] if i+1 < len(row) else ''
                        if y_task and y_task != '-' and name in x_assignments and date in x_assignments[name]:
                            warnings.append(f"{name} assigned Y task '{y_task}' on {date} but has an X task.")
    except Exception as e:
        warnings.append(f"Warning check error: {str(e)}")
    return jsonify({'warnings': warnings})

# --- Tally API ---
@app.route('/api/tally', methods=['GET', 'POST'])
def tally():
    if not is_logged_in():
        return require_login()
    path = os.path.join(DATA_DIR, 'soldier_state.json')
    if request.method == 'GET':
        with open(path, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'application/json'}
    else:
        data = request.data.decode('utf-8')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
        return jsonify({'success': True})

# --- Reset/History API ---
# @app.route('/api/reset', methods=['POST'])
# def reset():
#     if not is_logged_in():
#         return require_login()
#     open(os.path.join(DATA_DIR, 'y_task.csv'), 'w').close()
#     open(os.path.join(DATA_DIR, 'soldier_state.json'), 'w').close()
#     log_history('Reset schedules')
#     return jsonify({'success': True})

@app.route('/api/history', methods=['GET'])
def get_history():
    if not is_logged_in():
        return require_login()
    if not os.path.exists(HISTORY_PATH):
        return jsonify({'history': []})
    with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
        try:
            history = json.load(f)
        except Exception:
            history = []
    return jsonify({'history': history})

# --- Y Task API ---
@app.route('/api/y-tasks/list', methods=['GET'])
def list_y_task_schedules():
    if not is_logged_in():
        return require_login()
    schedules = y_tasks.list_y_task_schedules()
    # Return as list of dicts for frontend
    return jsonify({'schedules': [
        {'start': s, 'end': e, 'filename': f} for s, e, f in schedules
    ]})

@app.route('/api/y-tasks', methods=['GET'])
def get_y_tasks():
    if not is_logged_in():
        return require_login()
    # Accept ?date=YYYY-MM-DD or ?start=YYYY-MM-DD&end=YYYY-MM-DD
    date = request.args.get('date')
    start = request.args.get('start')
    end = request.args.get('end')
    filename = None
    if date:
        filename = y_tasks.find_y_task_file_for_date(date)
    elif start and end:
        key = f"{start}_to_{end}"
        index = y_tasks.load_y_task_index()
        filename = index.get(key)
    # If not found, return list of available schedules
    if not filename:
        schedules = y_tasks.list_y_task_schedules()
        return jsonify({'error': 'No Y task schedule found for given date/range.', 'available': [
            {'start': s, 'end': e, 'filename': f} for s, e, f in schedules
        ]}), 404
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Y task CSV file missing.'}), 404
    with open(path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/csv'}

@app.route('/api/y-tasks', methods=['POST'])
def save_y_tasks():
    if not is_logged_in():
        return require_login()
    # Defensive: get start/end from args, form, or json (if present)
    start = request.args.get('start') or request.form.get('start')
    end = request.args.get('end') or request.form.get('end')
    debug_info = {}
    if start is None or end is None:
        if request.is_json and request.get_json(silent=True):
            data = request.get_json()
            start = data.get('start')
            end = data.get('end')
            debug_info['json'] = data
    debug_info['start'] = start
    debug_info['end'] = end
    if not start or not end:
        # print(f"[DEBUG] /api/y-tasks POST missing start/end. Received: {debug_info}") DEBUG
        return jsonify({'error': 'Missing start or end date (ISO format required)', 'debug': debug_info}), 400
    def safe_date(date_str):
        return date_str.replace('/', '-')
    filename = f"y_schedule_{safe_date(start)}_{safe_date(end)}.csv"
    path = os.path.join(DATA_DIR, filename)
    # Only accept JSON with a 'csv' field
    csv_data = None
    if request.is_json and request.get_json(silent=True):
        data = request.get_json()
        csv_data = data.get('csv')
    # fallback: try to decode as plain text (legacy)
    elif request.data:
        try:
            csv_data = request.data.decode('utf-8')
        except Exception:
            csv_data = None
    # Only write if csv_data is a valid CSV (not a JSON string)
    if not csv_data or csv_data.strip().startswith('{'):
        # print(f"[DEBUG] /api/y-tasks POST missing or invalid CSV data. Received: {csv_data[:100] if csv_data else 'None'}") DEBUG
        return jsonify({'error': 'Missing or invalid CSV data'}), 400
    with open(path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    y_tasks.add_y_task_schedule(start, end, filename)
    log_history(f'Saved Y tasks for {start} to {end}')
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/y-tasks/generate', methods=['POST'])
def generate_y_tasks_api():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    start = data.get('start')  # Expect dd/mm/yyyy
    end = data.get('end')
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    d0 = datetime.strptime(start, '%d/%m/%Y')
    d1 = datetime.strptime(end, '%d/%m/%Y')
    dates = [(d0 + timedelta(days=i)) for i in range((d1-d0).days+1)]
    # Load workers and X task data
    workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
    # TODO: Load X task assignments as needed for SchedulerEngine
    engine = SchedulerEngine(workers, d0, d1)
    # Optionally, pass y_task_names_by_day if needed
    engine.assign_y_tasks()
    engine.assign_weekend_closers(d0, d1)
    # Build grid for response
    Y_TASKS_ORDER = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    grid = []
    for y_task in Y_TASKS_ORDER:
        row = []
        for d in dates:
            d_str = d.strftime('%d/%m/%Y')
            found = ''
            for soldier_id, tasks in engine.schedule.get(d, {}).items():
                if tasks == y_task:
                    found = soldier_id
                    break
            row.append(found)
        grid.append(row)
    # Compose CSV: header row is dates, each row is y_task + assignments
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Y Task'] + [d.strftime('%d/%m/%Y') for d in dates])
    for i, y_task in enumerate(Y_TASKS_ORDER):
        writer.writerow([y_task] + grid[i])
    csv_data = output.getvalue()
    return jsonify({
        'y_tasks': Y_TASKS_ORDER,
        'dates': [d.strftime('%d/%m/%Y') for d in dates],
        'grid': grid,
        'warnings': [],
        'filename': f"y_schedule_{d0.strftime('%Y-%m-%d')}_{d1.strftime('%Y-%m-%d')}.csv",
        'iso_start': d0.strftime('%Y-%m-%d'),
        'iso_end': d1.strftime('%Y-%m-%d'),
        'csv': csv_data
    }), 200

@app.route('/api/y-tasks/available-soldiers', methods=['POST'])
def available_soldiers_for_y_task():
    if not is_logged_in():
        return require_login()
    from backend import y_tasks
    from backend.worker import load_workers_from_json
    data = request.get_json() or {}
    date = data.get('date')
    task = data.get('task')
    current_assignments = data.get('current_assignments', {})
    year = int(data.get('year', datetime.today().year))
    period = int(data.get('period', 1))
    x_csv = os.path.join(DATA_DIR, f"x_tasks_{year}_{period}.csv")
    if not date or not task:
        return jsonify({'error': 'Missing date or task'}), 400
    # Use robust loader to get Hebrew names
    workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'), os.path.join(DATA_DIR, 'name_conv.json'))
    x_assignments = y_tasks.read_x_tasks(x_csv)
    soldier_qual = y_tasks.build_qualification_map(workers)
    qualified = [w for w in workers if any(q in y_tasks.QUALIFICATION_MAP[task] for q in soldier_qual[w.id])]
    available = [w for w in qualified if not (w.id in x_assignments and date in x_assignments[w.id])]
    already_assigned = set()
    for wid, days in current_assignments.items():
        if days.get(date) and days.get(date) != '-' and wid in [w.id for w in available]:
            already_assigned.add(wid)
    result = [w for w in available if w.id not in already_assigned]
    # Return list of dicts with id and name
    return jsonify({'available': [{'id': w.id, 'name': w.name} for w in result]})

# --- Combined Schedule API ---
@app.route('/api/combined', methods=['GET'])
def get_combined():
    if not is_logged_in():
        return require_login()
    path = os.path.join(DATA_DIR, 'combined_schedule.csv')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/csv'}

@app.route('/api/combined/grid', methods=['GET'])
def get_combined_grid():
    """
    Returns the combined schedule grid for a selected Y schedule period.
    - Rows: All Y tasks (in order), then all unique X tasks assigned in the period.
    - Columns: All dates in the selected period.
    - Cells: Soldier names assigned to each task on each day.
    Uses helper functions get_all_dates_from_x and read_x_tasks for X task expansion.
    """
    if not is_logged_in():
        return require_login()
    import csv
    from backend import y_tasks
    # --- 1. Determine which Y schedule period to use ---
    start = request.args.get('start')
    end = request.args.get('end')
    y_schedules = y_tasks.list_y_task_schedules()
    if start and end:
        # Find the matching Y schedule
        y_filename = None
        for s, e, f in y_schedules:
            if s == start and e == end:
                y_filename = f
                break
        if not y_filename:
            return jsonify({'error': 'Y schedule not found for given period'}), 404
    else:
        # Default: use the first available Y schedule
        if not y_schedules:
            return jsonify({'error': 'No Y schedules found'}), 404
        start, end, y_filename = y_schedules[0]
    y_path = y_tasks.y_schedule_path(y_filename)
    if not os.path.exists(y_path):
        return jsonify({'error': 'Y schedule CSV not found'}), 404
    # --- 2. Read Y schedule CSV to get dates and Y assignments ---
    with open(y_path, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        if not reader or len(reader) < 2:
            return jsonify({'error': 'Invalid Y schedule CSV format'}), 400
        dates = reader[0][1:]  # First row, skip 'Y Task'
        y_tasks_list = [row[0] for row in reader[1:]]
        y_grid = [row[1:] for row in reader[1:]]  # Each row: assignments for that Y task
    # --- 3. Get X assignments for these dates using helpers ---
    import glob
    import re
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    x_files = glob.glob(os.path.join(DATA_DIR, 'x_tasks_*.csv'))
    if not x_files:
        x_assignments = {}
    else:
        def extract_year_period(fname):
            m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
            if m:
                return int(m.group(1)), int(m.group(2))
            return (0, 0)
        x_files.sort(key=extract_year_period, reverse=True)
        x_csv = x_files[0]
        x_assignments = y_tasks.read_x_tasks(x_csv)
    # --- 4. Collect all unique X tasks assigned in the period (excluding Y task names) ---
    x_tasks_set = set()
    for name, day_map in x_assignments.items():
        for d in dates:
            task = day_map.get(d, '-')
            if task and task != '-' and task not in y_tasks_list:
                x_tasks_set.add(task)
    # print('DEBUG X TASKS FOUND:', x_tasks_set) DEBUG
    # Print assignments for each date
    for name, day_map in x_assignments.items():
        print(f"{name}: {[ (d, day_map.get(d, '-')) for d in dates ]}")
    x_tasks_list = sorted(x_tasks_set)
    # --- 5. Build X task rows: for each X task, fill with soldier names for each date ---
    x_grid = []
    for x_task in x_tasks_list:
        row = []
        for d in dates:
            found = ''
            for name, day_map in x_assignments.items():
                if day_map.get(d, '-') == x_task:
                    found = name
                    break
            row.append(found)
        x_grid.append(row)
    # --- 6. Build final grid and row labels ---
    row_labels = y_tasks_list + x_tasks_list
    grid = y_grid + x_grid
    return jsonify({
        'row_labels': row_labels,
        'dates': dates,
        'grid': grid,
        'y_period': {'start': start, 'end': end, 'filename': y_filename}
    })

@app.route('/api/x-tasks/conflicts', methods=['GET'])
def x_y_conflicts():
    if not is_logged_in():
        return require_login()
    import csv
    conflicts = []
    year = int(request.args.get('year', datetime.today().year))
    period = int(request.args.get('period', 1))
    x_path = os.path.join(DATA_DIR, f"x_tasks_{year}_{period}.csv")
    x_assignments = y_tasks.read_x_tasks(x_path)
    # Check all Y task CSVs
    for start, end, y_filename in y_tasks.list_y_task_schedules():
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            continue
        with open(y_path, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            dates = reader[0][1:]
            for row in reader[1:]:
                soldier = row[0]
                for i, date in enumerate(dates):
                    y_task = row[i+1] if i+1 < len(row) else ''
                    # Ensure date is in dd/mm/yyyy format
                    try:
                        d = datetime.strptime(date, '%d/%m/%Y').strftime('%d/%m/%Y')
                    except Exception:
                        d = date
                    if y_task and y_task != '-' and soldier in x_assignments and d in x_assignments[soldier]:
                        x_task = x_assignments[soldier][d]
                        if x_task and x_task != '-':
                            print(f"[DEBUG] Conflict: {soldier} on {d} - X: {x_task}, Y: {y_task}")
                            conflicts.append({
                                'soldier': soldier,
                                'date': d,
                                'x_task': x_task,
                                'y_task': y_task,
                                'y_file': y_filename
                            })
    print(f"[DEBUG] Total conflicts found: {len(conflicts)}")
    return jsonify({'conflicts': conflicts})

@app.route('/api/y-tasks/clear', methods=['POST'])
def clear_y_task_schedule():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    start = data.get('start')
    end = data.get('end')
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    index = y_tasks.load_y_task_index()
    key = f"{start}_to_{end}"
    filename = index.get(key)
    if not filename:
        return jsonify({'error': 'Schedule not found'}), 404
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
    # Read header to get dates
    import csv
    with open(path, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    if not reader or len(reader) < 2:
        return jsonify({'error': 'Invalid file format'}), 400
    header = reader[0]
    # Clear all cells (keep header)
    cleared = []
    for row in reader[1:]:
        cleared.append([row[0]] + ['' for _ in header[1:]])
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(cleared)
    return jsonify({'success': True})

@app.route('/api/y-tasks/delete', methods=['POST'])
def delete_y_task_schedule():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'Missing filename'}), 400
    path = os.path.join(DATA_DIR, filename)
    # Remove file if it exists
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500
    # Remove from index
    from backend import y_tasks
    index = y_tasks.load_y_task_index()
    key_to_remove = None
    for key, fname in index.items():
        if fname == filename:
            key_to_remove = key
            break
    if key_to_remove:
        del index[key_to_remove]
        y_tasks.save_y_task_index(index)
    return jsonify({'success': True})

@app.route('/api/combined/available-dates', methods=['GET'])
def get_combined_available_dates():
    # Returns all dates covered by any Y schedule
    from backend import y_tasks
    y_schedules = y_tasks.list_y_task_schedules()
    all_dates = set()
    for start, end, y_filename in y_schedules:
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            continue
        import csv
        with open(y_path, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            if not reader or len(reader) < 2:
                continue
            dates = reader[0][1:]
            all_dates.update(dates)
    all_dates = sorted(all_dates, key=lambda d: [int(x) for x in d.split('/')][::-1])
    return jsonify({'dates': all_dates})

@app.route('/api/combined/by-date', methods=['GET'])
def get_combined_by_date():
    if not is_logged_in():
        return require_login()
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'Missing date'}), 400
    from backend import y_tasks, x_tasks
    # Find Y assignments for this date
    y_schedules = y_tasks.list_y_task_schedules()
    y_assignments = {}
    y_tasks_list = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    for start, end, y_filename in y_schedules:
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            continue
        import csv
        with open(y_path, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            if not reader or len(reader) < 2:
                continue
            header = reader[0]
            date_idx = None
            for i, d in enumerate(header[1:]):
                if d == date:
                    date_idx = i + 1
                    break
            if date_idx is None:
                continue
            for row in reader[1:]:
                y_task = row[0]
                if y_task in y_tasks_list:
                    soldier = row[date_idx] if date_idx < len(row) else ''
                    y_assignments[y_task] = soldier
    # Find X assignments for this date
    # Use the most recent x_tasks CSV (by year/period)
    import glob
    import re
    x_files = glob.glob(os.path.join(DATA_DIR, 'x_tasks_*.csv'))
    if not x_files:
        x_assignments = {}
        x_tasks_set = set()
    else:
        # Pick the file with the latest year/period
        def extract_year_period(fname):
            m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
            if m:
                return int(m.group(1)), int(m.group(2))
            return (0, 0)
        x_files.sort(key=extract_year_period, reverse=True)
        x_csv = x_files[0]
        x_assignments = y_tasks.read_x_tasks(x_csv)
        x_tasks_set = set()
        for name, day_map in x_assignments.items():
            task = day_map.get(date, '-')
            if task and task != '-' and task not in y_tasks_list:
                x_tasks_set.add(task)
    x_tasks_list = sorted(x_tasks_set)
    x_assignments_by_task = {task: '' for task in x_tasks_list}
    for name, day_map in x_assignments.items():
        task = day_map.get(date, '-')
        if task and task != '-' and task in x_tasks_list:
            x_assignments_by_task[task] = name
    # Compose response
    return jsonify({
        'date': date,
        'y_tasks': y_tasks_list,
        'x_tasks': x_tasks_list,
        'y_assignments': y_assignments,
        'x_assignments': x_assignments_by_task
    })

@app.route('/api/combined/grid-full', methods=['GET'])
def get_combined_grid_full():
    if not is_logged_in():
        return require_login()
    from backend import y_tasks
    import csv
    # 1. Collect all dates from all Y schedules
    y_schedules = y_tasks.list_y_task_schedules()
    all_dates = set()
    y_data_by_date = {}
    for start, end, y_filename in y_schedules:
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            continue
        with open(y_path, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            if not reader or len(reader) < 2:
                continue
            dates = reader[0][1:]
            for d in dates:
                all_dates.add(d)
            for row in reader[1:]:
                y_task = row[0]
                for i, d in enumerate(dates):
                    if d not in y_data_by_date:
                        y_data_by_date[d] = {}
                    y_data_by_date[d][y_task] = row[i+1] if i+1 < len(row) else ''
    all_dates = sorted(all_dates, key=lambda d: [int(x) for x in d.split('/')][::-1])
    # 2. Get all X assignments for all dates
    import glob
    import re
    x_files = glob.glob(os.path.join(DATA_DIR, 'x_tasks_*.csv'))
    if not x_files:
        x_assignments = {}
        x_tasks_set = set()
    else:
        def extract_year_period(fname):
            m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
            if m:
                return int(m.group(1)), int(m.group(2))
            return (0, 0)
        x_files.sort(key=extract_year_period, reverse=True)
        x_csv = x_files[0]
        x_assignments = y_tasks.read_x_tasks(x_csv)
        x_tasks_set = set()
        for name, day_map in x_assignments.items():
            for d, task in day_map.items():
                if task and task != '-' and task not in ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]:
                    x_tasks_set.add(task)
    x_tasks_list = sorted(x_tasks_set)
    # 3. Build grid: rows = y_tasks + x_tasks, columns = all_dates
    y_tasks_list = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    grid = []
    # Y tasks rows
    for y_task in y_tasks_list:
        row = []
        for d in all_dates:
            row.append(y_data_by_date.get(d, {}).get(y_task, ''))
        grid.append(row)
    # X tasks rows
    for x_task in x_tasks_list:
        row = []
        for d in all_dates:
            found = []
            for name, day_map in x_assignments.items():
                if day_map.get(d, '-') == x_task:
                    found.append(name)
            row.append(', '.join(found))
        grid.append(row)
    row_labels = y_tasks_list + x_tasks_list
    return jsonify({
        'row_labels': row_labels,
        'dates': all_dates,
        'grid': grid
    })

@app.route('/api/combined/by-range', methods=['GET'])
def get_combined_by_range():
    if not is_logged_in():
        return require_login()
    start = request.args.get('start')
    end = request.args.get('end')
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    from backend import y_tasks
    import csv
    from datetime import datetime, timedelta
    # Build date list
    d0 = datetime.strptime(start, '%d/%m/%Y')
    d1 = datetime.strptime(end, '%d/%m/%Y')
    dates = [(d0 + timedelta(days=i)).strftime('%d/%m/%Y') for i in range((d1-d0).days+1)]
    # Collect Y assignments for this period
    y_schedules = y_tasks.list_y_task_schedules()
    y_data_by_date = {}
    for s, e, y_filename in y_schedules:
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            continue
        with open(y_path, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            if not reader or len(reader) < 2:
                continue
            file_dates = reader[0][1:]
            for row in reader[1:]:
                y_task = row[0]
                for i, d in enumerate(file_dates):
                    if d not in y_data_by_date:
                        y_data_by_date[d] = {}
                    y_data_by_date[d][y_task] = row[i+1] if i+1 < len(row) else ''
    # Get X assignments for this period
    import glob
    import re
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    x_files = glob.glob(os.path.join(DATA_DIR, 'x_tasks_*.csv'))
    if not x_files:
        x_assignments = {}
    else:
        def extract_year_period(fname):
            m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
            if m:
                return int(m.group(1)), int(m.group(2))
            return (0, 0)
        x_files.sort(key=extract_year_period, reverse=True)
        x_csv = x_files[0]
        x_assignments = y_tasks.read_x_tasks(x_csv)
    # Collect all unique X tasks assigned for any date in the period
    x_tasks_set = set()
    for name, day_map in x_assignments.items():
        for d in dates:
            task = day_map.get(d, '-')
            if task and task != '-':
                x_tasks_set.add(task)
    x_tasks_list = sorted(x_tasks_set)
    # Build X task rows: for each X task, fill with all soldier names for each date
    x_grid = []
    for x_task in x_tasks_list:
        row = []
        for d in dates:
            found = []
            for name, day_map in x_assignments.items():
                if day_map.get(d, '-') == x_task:
                    found.append(name)
            row.append(', '.join(found))
        x_grid.append(row)
    y_tasks_list = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    grid = []
    # Y tasks rows
    for y_task in y_tasks_list:
        row = []
        for d in dates:
            row.append(y_data_by_date.get(d, {}).get(y_task, ''))
        grid.append(row)
    row_labels = y_tasks_list + x_tasks_list
    grid = grid + x_grid
    return jsonify({
        'row_labels': row_labels,
        'dates': dates,
        'grid': grid
    })

@app.route('/api/combined/save', methods=['POST'])
def save_combined_csv():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    csv_data = data.get('csv')
    filename = data.get('filename')
    if not csv_data or not filename:
        return jsonify({'error': 'Missing csv or filename'}), 400
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    return jsonify({'success': True, 'filename': filename})

# --- In-memory soldier list ---
WORKER_JSON_PATH = os.path.join(DATA_DIR, 'worker_data.json')
WORKERS: list[Worker] = []

def load_workers_to_memory():
    global WORKERS
    WORKERS = load_workers_from_json(WORKER_JSON_PATH)

# Load on startup
load_workers_to_memory()

@app.route('/api/workers', methods=['GET'])
def get_workers():
    if not is_logged_in():
        return require_login()
    # Only return id, name, qualifications
    result = [
        {
            'id': getattr(w, 'id', None),
            'name': w.name,
            'qualifications': w.qualifications
        } for w in WORKERS
    ]
    return jsonify({'workers': result})

@app.route('/api/workers/<id>/qualifications', methods=['POST'])
def update_worker_qualifications(id):
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    qualifications = data.get('qualifications')
    if not isinstance(qualifications, list):
        return jsonify({'error': 'Invalid qualifications'}), 400
    updated = False
    for w in WORKERS:
        if str(getattr(w, 'id', None)) == str(id):
            w.qualifications = qualifications
            updated = True
            break
    if not updated:
        return jsonify({'error': 'Worker not found'}), 404
    # Write all workers back to JSON as a backup log
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump([w.__dict__ for w in WORKERS], f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'id': id, 'qualifications': qualifications})

@app.route('/api/workers', methods=['POST'])
def add_worker():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    # Validate required fields
    required = ['id', 'name', 'qualifications', 'closing_interval']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    # Create Worker instance
    w = Worker(
        id=str(data['id']),
        name=data['name'],
        start_date=data.get('start_date'),
        qualifications=data.get('qualifications', []),
        closing_interval=data.get('closing_interval', 4),
        officer=data.get('officer', False),
        seniority=data.get('seniority'),
        score=data.get('score'),
    )
    WORKERS.append(w)
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump([w.__dict__ for w in WORKERS], f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'worker': w.__dict__})

@app.route('/api/workers/<id>', methods=['PUT'])
def update_worker(id):
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    updated = False
    for w in WORKERS:
        if str(getattr(w, 'id', None)) == str(id):
            w.name = data.get('name', w.name)
            w.start_date = data.get('start_date', w.start_date)
            w.qualifications = data.get('qualifications', w.qualifications)
            w.closing_interval = data.get('closing_interval', w.closing_interval)
            w.officer = data.get('officer', w.officer)
            w.seniority = data.get('seniority', w.seniority)
            w.score = data.get('score', w.score)
            updated = True
            break
    if not updated:
        return jsonify({'error': 'Worker not found'}), 404
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump([w.__dict__ for w in WORKERS], f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'worker': w.__dict__})

@app.route('/api/workers/<id>', methods=['DELETE'])
def delete_worker(id):
    if not is_logged_in():
        return require_login()
    global WORKERS
    before = len(WORKERS)
    WORKERS = [w for w in WORKERS if str(getattr(w, 'id', None)) != str(id)]
    after = len(WORKERS)
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump([w.__dict__ for w in WORKERS], f, ensure_ascii=False, indent=2)
    if before == after:
        return jsonify({'error': 'Worker not found'}), 404
    return jsonify({'success': True})

# --- Serve React Frontend (for local dev) ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
    if path != "" and os.path.exists(os.path.join(frontend_dir, path)):
        return send_from_directory(frontend_dir, path)
    else:
        return send_from_directory(frontend_dir, 'index.html')

@app.route('/data/<path:filename>')
def serve_data(filename):
    return send_from_directory(os.path.join(DATA_DIR), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 