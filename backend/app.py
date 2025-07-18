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
HISTORY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'history.json')
history_lock = threading.Lock()


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
    path = os.path.join(DATA_DIR, 'x_task.csv')
    import io, csv, json
    from datetime import datetime, timedelta
    from backend import x_tasks
    # If file does not exist or is empty, generate blank grid with weekly headers
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        soldiers = x_tasks.load_soldiers(os.path.join(DATA_DIR, 'soldier_data.json'))
        year = datetime.today().year
        half = 1
        if half == 1:
            start = datetime(year, 1, 7)
            end = datetime(year, 7, 7)
        else:
            start = datetime(year, 7, 7)
            end = datetime(year + 1, 1, 7)
        weeks = x_tasks.get_weeks_for_period(start, end)
        headers = ['name'] + [str(week_num) for week_num, _, _ in weeks]
        subheaders = [''] + [f"{ws.strftime('%d/%m')} - {we.strftime('%d/%m')}" for _, ws, we in weeks]
        rows = []
        for s in soldiers:
            row = [s['name']] + ['' for _ in range(len(weeks))]
            rows.append(row)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(subheaders)
        writer.writerows(rows)
        csv_data = output.getvalue()
        custom_tasks = x_tasks.load_custom_x_tasks()
        return jsonify({"csv": csv_data, "custom_tasks": custom_tasks, "year": year, "half": half})
    else:
        with open(path, 'r', encoding='utf-8') as f:
            csv_data = f.read()
    custom_tasks = x_tasks.load_custom_x_tasks()
    # Load year and half from metadata
    meta = x_tasks.load_x_task_meta()
    year = meta['year'] if meta else datetime.today().year
    half = meta['half'] if meta else 1
    return jsonify({"csv": csv_data, "custom_tasks": custom_tasks, "year": year, "half": half})

@app.route('/api/x-tasks', methods=['POST'])
def save_x_tasks():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    csv_data = data.get('csv')
    custom_tasks = data.get('custom_tasks', {})
    year = data.get('year')
    half = data.get('half')
    if not csv_data or not year or not half:
        return jsonify({'error': 'Missing data'}), 400
    # Save CSV
    x_task_path = os.path.join(DATA_DIR, 'x_task.csv')
    with open(x_task_path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    # Save custom tasks
    import backend.x_tasks as x_tasks
    x_tasks.save_custom_x_tasks(custom_tasks)
    # Save year/half meta
    meta_path = os.path.join(DATA_DIR, 'x_task_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        import json
        json.dump({'year': year, 'half': half}, f)
    return jsonify({'success': True})

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
@app.route('/api/reset', methods=['POST'])
def reset():
    if not is_logged_in():
        return require_login()
    open(os.path.join(DATA_DIR, 'y_task.csv'), 'w').close()
    open(os.path.join(DATA_DIR, 'soldier_state.json'), 'w').close()
    log_history('Reset schedules')
    return jsonify({'success': True})

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
@app.route('/api/y-tasks', methods=['GET'])
def get_y_tasks():
    if not is_logged_in():
        return require_login()
    path = os.path.join(DATA_DIR, 'y_task.csv')
    if not os.path.exists(path) or os.stat(path).st_size == 0:
        # Generate blank Y task grid
        from backend import x_tasks, y_tasks
        import io, csv
        # Get weeks from x_task.csv
        x_path = os.path.join(DATA_DIR, 'x_task.csv')
        with open(x_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            x_headers = next(reader)
            x_subheaders = next(reader)
        week_numbers = x_headers[1:]
        week_ranges = x_subheaders[1:]
        # Get Y task names
        y_task_names = getattr(y_tasks, 'Y_TASKS', [
            'Southern Driver', 'Southern Escort', 'C&N Driver', 'C&N Escort', 'Supervisor'])
        # Build blank grid
        headers = ['Y Task'] + week_numbers
        subheaders = [''] + week_ranges
        rows = []
        for y_task in y_task_names:
            row = [y_task] + ['' for _ in week_numbers]
            rows.append(row)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerow(subheaders)
        writer.writerows(rows)
        csv_data = output.getvalue()
        return csv_data, 200, {'Content-Type': 'text/csv'}
    with open(path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/csv'}

@app.route('/api/y-tasks', methods=['POST'])
def save_y_tasks():
    if not is_logged_in():
        return require_login()
    csv_data = request.data.decode('utf-8')
    path = os.path.join(DATA_DIR, 'y_task.csv')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(csv_data)
    log_history('Saved Y tasks')
    return jsonify({'success': True})

@app.route('/api/y-tasks/generate', methods=['POST'])
def generate_y_tasks_api():
    if not is_logged_in():
        return require_login()
    import json
    from backend import y_tasks, x_tasks
    data = request.get_json() or {}
    start = data.get('start')
    end = data.get('end')
    mode = data.get('mode', 'auto')
    # Load year and half from meta
    meta = x_tasks.load_x_task_meta()
    year = meta['year'] if meta else datetime.today().year
    half = meta['half'] if meta else 1
    # Compute dates list if not provided
    dates = data.get('dates')
    if not dates and start and end:
        # Build date list from start to end (inclusive)
        try:
            d0 = datetime.strptime(start, '%d/%m/%Y')
            d1 = datetime.strptime(end, '%d/%m/%Y')
            dates = []
            d = d0
            while d <= d1:
                dates.append(d.strftime('%d/%m/%Y'))
                d += timedelta(days=1)
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400
    if not dates:
        return jsonify({'error': 'No dates provided'}), 400
    # --- BLOCK if any date is outside X schedule range ---
    x_dates = set()
    try:
        x_dates = set(y_tasks.get_all_dates_from_x(os.path.join(DATA_DIR, 'x_task.csv')))
    except Exception:
        return jsonify({'error': 'Could not read X task schedule for validation.'}), 400
    out_of_range = [d for d in dates if d not in x_dates]
    if out_of_range:
        # Instead of listing all dates, just show the allowed range
        if x_dates:
            sorted_x_dates = sorted(x_dates, key=lambda d: datetime.strptime(d, '%d/%m/%Y'))
            min_date = sorted_x_dates[0]
            max_date = sorted_x_dates[-1]
            return jsonify({'error': f"Y task generation blocked: The selected date range is not fully covered by the X task schedule. Allowed range: {min_date} to {max_date}."}), 400
        else:
            return jsonify({'error': 'Y task generation blocked: No valid dates found in X task schedule.'}), 400
    # --- HYBRID MODE: Fill empty cells, preserve user assignments ---
    if mode == 'hybrid':
        partial_grid = data.get('partial_grid')
        y_tasks_list = data.get('y_tasks')
        if not (partial_grid and y_tasks_list and dates):
            return jsonify({'error': 'Missing partial_grid, y_tasks, or dates'}), 400
        # Build a map: (y_task, date) -> assigned soldier (from partial_grid)
        manual_assignments = {}
        for y_idx, y_task in enumerate(y_tasks_list):
            for d_idx, date in enumerate(dates):
                soldier = partial_grid[y_idx][d_idx]
                if soldier:
                    manual_assignments[(y_task, date)] = soldier
        # Get all soldiers
        soldiers = y_tasks.load_soldiers(os.path.join(DATA_DIR, 'soldier_data.json'))
        soldier_names = [s['name'] for s in soldiers]
        # Build current_assignments for the generator
        current_assignments = {name: {date: '-' for date in dates} for name in soldier_names}
        for (y_task, date), soldier in manual_assignments.items():
            if soldier in current_assignments:
                current_assignments[soldier][date] = y_task
        # Run the generator, but skip already assigned cells
        y_assignments, _, _, warnings = y_tasks.generate_y_schedule(
            soldier_json=os.path.join(DATA_DIR, 'soldier_data.json'),
            x_csv=os.path.join(DATA_DIR, 'x_task.csv'),
            y_csv=os.path.join(DATA_DIR, 'y_task.csv'),
            date_list=dates,
            interactive=False
        )
        # Build grid: rows = y_tasks_list, columns = dates
        grid = []
        for y_task in y_tasks_list:
            row = []
            for date in dates:
                # If user assigned, use that
                if (y_task, date) in manual_assignments:
                    row.append(manual_assignments[(y_task, date)])
                else:
                    # Find which soldier (if any) is assigned this y_task on this date
                    found = ''
                    for soldier, day_map in y_assignments.items():
                        if day_map.get(date) == y_task:
                            found = soldier
                            break
                    row.append(found)
            grid.append(row)
        return jsonify({
            'y_tasks': y_tasks_list,
            'dates': dates,
            'grid': grid,
            'warnings': warnings
        }), 200
    # --- AUTO MODE: Return grid for frontend ---
    if mode == 'auto':
        Y_TASKS_ORDER = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        y_assignments, _, _, warnings = y_tasks.generate_y_schedule(
            soldier_json=os.path.join(DATA_DIR, 'soldier_data.json'),
            x_csv=os.path.join(DATA_DIR, 'x_task.csv'),
            y_csv=os.path.join(DATA_DIR, 'y_task.csv'),
            date_list=dates
        )
        grid = []
        for y_task in Y_TASKS_ORDER:
            row = []
            for date in dates:
                found = ''
                for soldier, day_map in y_assignments.items():
                    if day_map.get(date) == y_task:
                        found = soldier
                        break
                row.append(found)
            grid.append(row)
        return jsonify({
            'y_tasks': Y_TASKS_ORDER,
            'dates': dates,
            'grid': grid,
            'warnings': warnings,
            'year': year
        }), 200
    # --- LEGACY/CSV MODE ---
    y_assignments, date_list, soldier_names, warnings = y_tasks.generate_y_schedule(
        soldier_json=os.path.join(DATA_DIR, 'soldier_data.json'),
        x_csv=os.path.join(DATA_DIR, 'x_task.csv'),
        y_csv=os.path.join(DATA_DIR, 'y_task.csv'),
        date_list=dates
    )
    with open(os.path.join(DATA_DIR, 'y_task.csv'), 'r', encoding='utf-8') as f:
        csv_data = f.read()
    return jsonify({'csv': csv_data, 'warnings': warnings, 'year': year}), 200

@app.route('/api/y-tasks/available-soldiers', methods=['POST'])
def available_soldiers_for_y_task():
    if not is_logged_in():
        return require_login()
    from backend import y_tasks
    data = request.get_json() or {}
    date = data.get('date')
    task = data.get('task')
    current_assignments = data.get('current_assignments', {})  # {soldier_name: {date: y_task}}
    print(f"[DEBUG] Incoming available-soldiers request: date={date}, task={task}, current_assignments={current_assignments}")
    if not date or not task:
        print("[DEBUG] Missing date or task in request")
        return jsonify({'error': 'Missing date or task'}), 400
    # Load soldiers and X assignments
    soldiers = y_tasks.load_soldiers(os.path.join(DATA_DIR, 'soldier_data.json'))
    x_assignments = y_tasks.read_x_tasks(os.path.join(DATA_DIR, 'x_task.csv'))
    soldier_qual = y_tasks.build_qualification_map(soldiers)
    qualified = [s['name'] for s in soldiers if any(q in y_tasks.QUALIFICATION_MAP[task] for q in soldier_qual[s['name']])]
    print(f"[DEBUG] Qualified soldiers for task '{task}': {qualified}")
    # Exclude soldiers with X task on that date
    available = [n for n in qualified if not (n in x_assignments and date in x_assignments[n])]
    print(f"[DEBUG] After X task exclusion, available: {available}")
    # Exclude soldiers already assigned a Y task on that date in current_assignments
    already_assigned = set()
    for n, days in current_assignments.items():
        if days.get(date) and days.get(date) != '-' and n in available:
            already_assigned.add(n)
    result = [n for n in available if n not in already_assigned]
    print(f"[DEBUG] After already-assigned exclusion, final available: {result}")
    return jsonify({'available': result})

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
    if not is_logged_in():
        return require_login()
    import csv
    from backend import y_tasks
    # Get date range from query params, or use all dates in y_task.csv
    start = request.args.get('start')
    end = request.args.get('end')
    y_path = os.path.join(DATA_DIR, 'y_task.csv')
    x_path = os.path.join(DATA_DIR, 'x_task.csv')
    # --- Get all dates ---
    with open(y_path, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        date_headers = reader[0][1:]
    if start and end:
        try:
            from datetime import datetime, timedelta
            d0 = datetime.strptime(start, '%d/%m/%Y')
            d1 = datetime.strptime(end, '%d/%m/%Y')
            all_dates = []
            d = d0
            while d <= d1:
                all_dates.append(d.strftime('%d/%m/%Y'))
                d += timedelta(days=1)
            dates = [d for d in date_headers if d in all_dates]
        except Exception:
            dates = date_headers
    else:
        dates = date_headers
    # --- Y task assignments ---
    y_tasks_list = ['Supervisor', 'C&N Driver', 'C&N Escort', 'Southern Driver', 'Southern Escort']
    y_assignments = {task: ['' for _ in dates] for task in y_tasks_list}
    with open(y_path, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        rows = reader[1:]
        for row in rows:
            name = row[0]
            for i, date in enumerate(dates):
                y_task = row[i+1] if i+1 < len(row) else ''
                if y_task and y_task != '-' and y_task in y_tasks_list:
                    y_assignments[y_task][i] = name
    # --- X task assignments (expanded to daily) ---
    x_assignments = y_tasks.read_x_tasks(x_path)
    # Find all X tasks present in the date range
    x_tasks_set = set()
    for name, day_map in x_assignments.items():
        for date in dates:
            x_task = day_map.get(date, '-')
            if x_task and x_task != '-' and x_task not in y_tasks_list:
                x_tasks_set.add(x_task)
    x_tasks_list = sorted(x_tasks_set)
    x_assignments_by_task = {task: ['' for _ in dates] for task in x_tasks_list}
    for name, day_map in x_assignments.items():
        for i, date in enumerate(dates):
            x_task = day_map.get(date, '-')
            if x_task and x_task != '-' and x_task in x_tasks_list:
                x_assignments_by_task[x_task][i] = name
    # --- Build grid ---
    grid = []
    row_labels = []
    for y_task in y_tasks_list:
        grid.append(y_assignments[y_task])
        row_labels.append(y_task)
    for x_task in x_tasks_list:
        grid.append(x_assignments_by_task[x_task])
        row_labels.append(x_task)
    return jsonify({
        'row_labels': row_labels,
        'dates': dates,
        'grid': grid
    })

@app.route('/api/x-tasks/conflicts', methods=['GET'])
def x_y_conflicts():
    if not is_logged_in():
        return require_login()
    import csv
    from backend import y_tasks
    x_path = os.path.join(DATA_DIR, 'x_task.csv')
    y_path = os.path.join(DATA_DIR, 'y_task.csv')
    conflicts = []
    if not (os.path.exists(x_path) and os.path.exists(y_path)):
        return jsonify({'conflicts': []})
    x_assignments = y_tasks.read_x_tasks(x_path)
    with open(y_path, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        dates = reader[0][1:]
        for row in reader[1:]:
            soldier = row[0]
            for i, date in enumerate(dates):
                y_task = row[i+1] if i+1 < len(row) else ''
                if y_task and y_task != '-' and soldier in x_assignments and date in x_assignments[soldier]:
                    x_task = x_assignments[soldier][date]
                    conflicts.append({
                        'soldier': soldier,
                        'date': date,
                        'x_task': x_task,
                        'y_task': y_task
                    })
    return jsonify({'conflicts': conflicts})

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