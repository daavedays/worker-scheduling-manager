# Config
SESSION_TIMEOUT_MINUTES = 30

import os
import json
import csv
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify, session, send_from_directory, Response
from flask_cors import CORS
import threading
from typing import Optional

# Handle imports for both module and direct execution
try:
    from . import x_tasks
    from . import y_tasks
    from .worker import Worker, load_workers_from_json, EnhancedWorker
    from .engine import SchedulingEngineV2
    from .scoring import recalc_worker_schedule
    from .closing_schedule_calculator import ClosingScheduleCalculator
except ImportError:
    import x_tasks
    import y_tasks
    from worker import Worker, load_workers_from_json, EnhancedWorker
    from engine import SchedulingEngineV2
    from scoring import recalc_worker_schedule
    from closing_schedule_calculator import ClosingScheduleCalculator

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

# --- Enhanced Scheduling API Endpoints ---
@app.route('/api/scheduling/comprehensive-test', methods=['POST'])
def run_comprehensive_test():
    """
    Run comprehensive scheduling test with SchedulingEngineV2
    """
    if not is_logged_in():
        return require_login()
    
    try:
        data = request.get_json() or {}
        start_date_str = data.get('start_date', '2025-01-01')
        end_date_str = data.get('end_date', '2025-06-30')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Load workers
        workers = load_workers_from_json("data/worker_data.json")
        
        # Create and run SchedulingEngineV2
        engine = SchedulingEngineV2()
        
        # Run comprehensive test with 2 closers per weekend (typical configuration)
        result = engine.schedule_range(
            workers=workers,
            start=start_date,
            end=end_date,
            num_closers_per_weekend=2,
            weekday_tasks={}  # Can be enhanced to include weekday Y-tasks if needed
        )
        
        return jsonify({
            'success': result.get('success', True),
            'message': 'Comprehensive test completed with SchedulingEngineV2',
            'period': f"{start_date_str} to {end_date_str}",
            'total_workers': len(workers),
            'closers_assigned': len(result.get('closers', {})),
            'y_tasks_assigned': len(result.get('y_tasks', {})),
            'logs': result.get('logs', [])[-10:],  # Last 10 log entries
            'assignment_errors': result.get('assignment_errors', []),
            'legacy_route': False
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduling/workload-analysis', methods=['GET'])
def get_workload_analysis():
    """
    Get comprehensive workload analysis by qualification count
    """
    if not is_logged_in():
        return require_login()
    
    try:
        workers = load_workers_from_json("data/worker_data.json")
        
        # Group workers by qualification count
        qualification_groups = {}
        for worker in workers:
            qual_count = len(worker.qualifications)
            if qual_count not in qualification_groups:
                qualification_groups[qual_count] = []
            qualification_groups[qual_count].append(worker)
        
        analysis = {}
        for qual_count in sorted(qualification_groups.keys()):
            workers_in_group = qualification_groups[qual_count]
            
            # Calculate averages
            y_task_counts = [len(w.y_tasks) for w in workers_in_group]
            closing_counts = [len(w.closing_history) for w in workers_in_group]
            closing_intervals = [w.closing_interval for w in workers_in_group]
            
            avg_y_tasks = sum(y_task_counts) / len(y_task_counts) if y_task_counts else 0
            avg_closings = sum(closing_counts) / len(closing_counts) if closing_counts else 0
            avg_interval = sum(closing_intervals) / len(closing_intervals) if closing_intervals else 0
            
            # Estimate X tasks based on qualification scarcity
            if qual_count == 1:
                estimated_x_tasks = 120
            elif qual_count == 2:
                estimated_x_tasks = 80
            elif qual_count == 3:
                estimated_x_tasks = 40
            elif qual_count == 4:
                estimated_x_tasks = 20
            else:  # 5 qualifications
                estimated_x_tasks = 10
            
            total_workload = avg_y_tasks + estimated_x_tasks + avg_closings
            
            analysis[qual_count] = {
                'worker_count': len(workers_in_group),
                'avg_y_tasks': round(avg_y_tasks, 1),
                'avg_closings': round(avg_closings, 1),
                'avg_closing_interval': round(avg_interval, 1),
                'estimated_x_tasks': estimated_x_tasks,
                'total_workload': round(total_workload, 1),
                'workers': [
                    {
                        'name': w.name,
                        'qualifications': w.qualifications,
                        'y_tasks': len(w.y_tasks),
                        'closings': len(w.closing_history),
                        'closing_interval': w.closing_interval
                    }
                    for w in workers_in_group
                ]
            }
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'total_workers': len(workers)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduling/closer-analysis', methods=['GET'])
def get_closer_analysis():
    """
    Get closer assignment analysis with qualification balance
    """
    if not is_logged_in():
        return require_login()
    
    try:
        workers = load_workers_from_json("data/worker_data.json")
        
        # Analyze by qualification count
        qualification_groups = {}
        for worker in workers:
            qual_count = len(worker.qualifications)
            if qual_count not in qualification_groups:
                qualification_groups[qual_count] = []
            qualification_groups[qual_count].append(worker)
        
        analysis = {}
        for qual_count in sorted(qualification_groups.keys()):
            workers_in_group = qualification_groups[qual_count]
            
            closing_intervals = [w.closing_interval for w in workers_in_group]
            avg_interval = sum(closing_intervals) / len(closing_intervals)
            
            analysis[qual_count] = {
                'worker_count': len(workers_in_group),
                'avg_closing_interval': round(avg_interval, 1),
                'closing_frequency': f"Every {avg_interval:.1f} weeks",
                'workers': [
                    {
                        'name': w.name,
                        'qualifications': w.qualifications,
                        'closing_interval': w.closing_interval,
                        'closing_frequency': f"Every {w.closing_interval} weeks"
                    }
                    for w in workers_in_group
                ]
            }
        
        # Calculate correlation
        qualification_counts = []
        closing_intervals = []
        
        for worker in workers:
            if worker.closing_interval > 0:
                qualification_counts.append(len(worker.qualifications))
                closing_intervals.append(worker.closing_interval)
        
        correlation = 0
        if qualification_counts:
            n = len(qualification_counts)
            sum_x = sum(qualification_counts)
            sum_y = sum(closing_intervals)
            sum_xy = sum(x * y for x, y in zip(qualification_counts, closing_intervals))
            sum_x2 = sum(x * x for x in qualification_counts)
            sum_y2 = sum(y * y for y in closing_intervals)
            
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5
            
            correlation = numerator / denominator if denominator != 0 else 0
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'correlation': round(correlation, 3),
            'correlation_interpretation': get_correlation_interpretation(correlation)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_correlation_interpretation(correlation):
    """Helper function to interpret correlation coefficient"""
    if correlation > 0.7:
        return "Strong positive correlation: More qualifications = Higher closing intervals"
    elif correlation > 0.3:
        return "Moderate positive correlation: More qualifications = Higher closing intervals"
    elif correlation > -0.3:
        return "Weak correlation: No clear relationship"
    elif correlation > -0.7:
        return "Moderate negative correlation: More qualifications = Lower closing intervals"
    else:
        return "Strong negative correlation: More qualifications = Lower closing intervals"

@app.route('/api/scheduling/engine-status', methods=['GET'])
def get_engine_status():
    """
    Get overall engine status and performance metrics using SchedulingEngineV2
    """
    if not is_logged_in():
        return require_login()
    
    try:
        workers = load_workers_from_json("data/worker_data.json")
        
        # Create SchedulingEngineV2 instance for health check
        engine = SchedulingEngineV2()
        
        # Run a quick health check with a small date range
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 14)  # 2 weeks for quick test
        
        # Quick test to ensure engine is working
        health_result = engine.schedule_range(
            workers=workers,
            start=start_date,
            end=end_date,
            num_closers_per_weekend=2,
            weekday_tasks={}
        )
        
        # Analyze worker qualifications
        qualification_counts = {
            'supervisor': len([w for w in workers if 'Supervisor' in w.qualifications]),
            'cn_driver': len([w for w in workers if 'C&N Driver' in w.qualifications]),
            'cn_escort': len([w for w in workers if 'C&N Escort' in w.qualifications]),
            'southern_driver': len([w for w in workers if 'Southern Driver' in w.qualifications]),
            'southern_escort': len([w for w in workers if 'Southern Escort' in w.qualifications])
        }
        
        return jsonify({
            'success': True,
            'status': 'HEALTHY',
            'message': 'SchedulingEngineV2 is operational and tested successfully',
            'engine_version': 'SchedulingEngineV2',
            'health_check': {
                'test_period': f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}",
                'closers_assigned': len(health_result.get('closers', {})),
                'y_tasks_assigned': len(health_result.get('y_tasks', {})),
                'assignment_errors': len(health_result.get('assignment_errors', [])),
                'success': health_result.get('success', False)
            },
            'worker_metrics': {
                'total_workers': len(workers),
                'qualification_distribution': qualification_counts,
                'workers_with_x_tasks': len([w for w in workers if w.x_tasks]),
                'workers_with_y_tasks': len([w for w in workers if w.y_tasks]),
                'workers_with_closing_history': len([w for w in workers if w.closing_history])
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'ERROR',
            'message': f'Engine health check failed: {str(e)}',
            'error': str(e)
        }), 500

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
    import x_tasks
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
    import x_tasks
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
            try:
                from . import y_tasks
            except ImportError:
                import y_tasks
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
    
    # Clean up orphaned index entries first
    cleanup_y_task_index()
    
    # Get Y task manager
    try:
        from .y_task_manager import get_y_task_manager
        y_task_manager = get_y_task_manager(DATA_DIR)
    except ImportError:
        try:
            from y_task_manager import get_y_task_manager
            y_task_manager = get_y_task_manager(DATA_DIR)
        except ImportError:
            return jsonify({'error': 'Y task manager not available'}), 500
    
    # Get all Y task periods using the new manager
    periods = y_task_manager.list_y_task_periods()
    
    # Convert to the format expected by frontend
    schedules = []
    for period in periods:
        schedules.append({
            'start': period['start_date'],
            'end': period['end_date'],
            'filename': period['filename']
        })
    
    return jsonify({'schedules': schedules})

@app.route('/api/y-tasks', methods=['GET'])
def get_y_tasks():
    if not is_logged_in():
        return require_login()
    
    # Get Y task manager
    try:
        from .y_task_manager import get_y_task_manager
        y_task_manager = get_y_task_manager(DATA_DIR)
    except ImportError:
        try:
            from y_task_manager import get_y_task_manager
            y_task_manager = get_y_task_manager(DATA_DIR)
        except ImportError:
            return jsonify({'error': 'Y task manager not available'}), 500
    
    # Accept ?date=dd/mm/yyyy or ?start=dd/mm/yyyy&end=dd/mm/yyyy
    date = request.args.get('date')
    start = request.args.get('start')
    end = request.args.get('end')
    filename = None
    
    if date:
        # Find file for specific date
        periods = y_task_manager.list_y_task_periods()
        for period in periods:
            try:
                d = datetime.strptime(date, '%d/%m/%Y').date()
                s = datetime.strptime(period['start_date'], '%d/%m/%Y').date()
                e = datetime.strptime(period['end_date'], '%d/%m/%Y').date()
                if s <= d <= e:
                    filename = period['filename']
                    break
            except Exception:
                continue
    elif start and end:
        # Find file for date range
        periods = y_task_manager.list_y_task_periods()
        for period in periods:
            if period['start_date'] == start and period['end_date'] == end:
                filename = period['filename']
                break
    
    # If not found, return list of available schedules
    if not filename:
        periods = y_task_manager.list_y_task_periods()
        available = []
        for period in periods:
            available.append({
                'start': period['start_date'],
                'end': period['end_date'],
                'filename': period['filename']
            })
        return jsonify({'error': 'No Y task schedule found for given date/range.', 'available': available}), 404
    
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'Y task CSV file missing.'}), 404
    
    with open(path, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/csv'}

@app.route('/api/y-tasks', methods=['POST'])
def save_y_tasks():
    if not is_logged_in():
        return require_login()
    
    # Get Y task manager
    try:
        from .y_task_manager import get_y_task_manager
        y_task_manager = get_y_task_manager(DATA_DIR)
    except ImportError:
        try:
            from y_task_manager import get_y_task_manager
            y_task_manager = get_y_task_manager(DATA_DIR)
        except ImportError:
            return jsonify({'error': 'Y task manager not available'}), 500
    
    # Get request data
    data = request.get_json() or {}
    start_date = data.get('start')
    end_date = data.get('end')
    grid_data = data.get('grid', [])
    dates = data.get('dates', [])
    y_tasks = data.get('y_tasks', [])
    
    if not start_date or not end_date:
        return jsonify({'error': 'Missing start or end date'}), 400
    
    if not grid_data or not dates or not y_tasks:
        return jsonify({'error': 'Missing grid data, dates, or Y tasks'}), 400
    
    try:
        # Save to CSV using Y task manager
        filename = y_task_manager.save_y_tasks_to_csv(start_date, end_date, grid_data, dates, y_tasks)
        
        # Update worker scores based on Y task assignments
        from worker import load_workers_from_json, save_workers_to_json
        import json
        
        # Load current workers
        workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
        
        # Load current worker data to preserve other fields
        try:
            with open(os.path.join(DATA_DIR, 'worker_data.json'), 'r', encoding='utf-8') as f:
                original_data = json.load(f)
        except Exception:
            original_data = []
        
        # Count Y task assignments per worker and update scores
        worker_assignments = {}
        for i, y_task in enumerate(y_tasks):
            for j, date_str in enumerate(dates):
                if j < len(grid_data[i]) and grid_data[i][j]:  # If there's an assignment
                    worker_name = grid_data[i][j]
                    if worker_name not in worker_assignments:
                        worker_assignments[worker_name] = 0
                    worker_assignments[worker_name] += 1
        
        # Update worker scores
        for worker in workers:
            if worker.name in worker_assignments:
                # Add 1 point per Y task assignment
                worker.score += worker_assignments[worker.name]
        
        # Save updated workers
        save_workers_to_json(workers, os.path.join(DATA_DIR, 'worker_data.json'), original_data)
        
        log_history(f'Saved Y tasks for {start_date} to {end_date} and updated {len(worker_assignments)} worker scores')
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as e:
        print(f"Error saving Y tasks: {e}")
        return jsonify({'error': f'Failed to save Y tasks: {str(e)}'}), 500

@app.route('/api/y-tasks/generate', methods=['POST'])
def generate_y_tasks_api():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    start = data.get('start')  # Expect dd/mm/yyyy
    end = data.get('end')
    mode = data.get('mode', 'auto')  # auto, hybrid, manual
    partial_grid = data.get('partial_grid', [])
    y_tasks = data.get('y_tasks', [])
    dates = data.get('dates', [])
    
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    
    d0 = datetime.strptime(start, '%d/%m/%Y').date()
    d1 = datetime.strptime(end, '%d/%m/%Y').date()
    
    # Load workers and X task data
    workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
    
    # Load X task data directly from CSV files
    try:
        # Check if date range spans across the transition period (June to July)
        start_period = 1 if d0.month <= 6 else 2
        end_period = 1 if d1.month <= 6 else 2
        
        # Load X task files for all periods that overlap with the date range
        periods_to_load = set()
        periods_to_load.add(start_period)
        periods_to_load.add(end_period)
        
        # If the range spans across the transition, we need both periods
        if start_period != end_period:
            periods_to_load.add(1)
            periods_to_load.add(2)
        
        print(f"Loading X task files for periods: {periods_to_load}")
        
        # Load X task data directly from CSV files
        x_assignments = {}
        for period in periods_to_load:
            try:
                # Import y_tasks module for X task loading
                from . import y_tasks as y_tasks_module
                x_csv = os.path.join(DATA_DIR, f"x_tasks_{d0.year}_{period}.csv")
                
                if os.path.exists(x_csv):
                    print(f"Loading X-task file: {x_csv}")
                    period_assignments = y_tasks_module.read_x_tasks(x_csv)
                    
                    # Merge assignments from this period
                    for worker_id, assignments in period_assignments.items():
                        if worker_id not in x_assignments:
                            x_assignments[worker_id] = {}
                        x_assignments[worker_id].update(assignments)
                else:
                    print(f"X-task file not found: {x_csv}")
            except Exception as e:
                print(f"Error loading X tasks for period {period}: {e}")
        
        # Load X assignments into workers
        for worker in workers:
            if worker.id in x_assignments:
                for date_str, task_name in x_assignments[worker.id].items():
                    try:
                        # Store as string key (dd/mm/yyyy format) instead of datetime.date object
                        worker.x_tasks[date_str] = task_name
                    except Exception as e:
                        print(f"Error loading X task {date_str}: {e}")
                        
        print("✅ X task data loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load X task data: {e}")
    
    # Create new scheduling engine
    print(f"🚀 Creating SchedulingEngineV2 with {len(workers)} workers")
    engine = SchedulingEngineV2()
    print("✅ SchedulingEngineV2 created successfully")
    
    # Handle different modes
    if mode == 'hybrid' and partial_grid and y_tasks and dates:
        # Load existing assignments from partial grid
        for y_idx, y_task in enumerate(y_tasks):
            for d_idx, date_str in enumerate(dates):
                if partial_grid[y_idx] and partial_grid[y_idx][d_idx]:
                    worker_name = partial_grid[y_idx][d_idx]
                    # Find worker by name
                    for worker in workers:
                        if worker.name == worker_name:
                            try:
                                date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                                worker.assign_y_task(date_obj, y_task)
                            except Exception as e:
                                print(f"Error assigning Y task {date_str}: {e}")
                                pass
                            break
    
    # Generate schedule using new SchedulingEngineV2
    try:
        # Prepare weekday Y tasks if provided
        weekday_tasks = {}
        if mode != 'auto' and y_tasks and dates:
            # Build weekday_tasks from provided data
            for d_idx, date_str in enumerate(dates):
                try:
                    date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                    if d0 <= date_obj <= d1:
                        # Check which Y tasks are needed on this date
                        needed_tasks = []
                        for y_idx, y_task in enumerate(y_tasks):
                            # For auto mode, schedule all tasks. For hybrid/manual, respect existing assignments
                            if mode == 'auto' or not (partial_grid and partial_grid[y_idx] and partial_grid[y_idx][d_idx]):
                                needed_tasks.append(y_task)
                        if needed_tasks:
                            weekday_tasks[date_obj] = needed_tasks
                except ValueError:
                    continue
        else:
            # Auto mode: create full Y task schedule for all weekdays
            Y_TASKS_ORDER = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
            current_date = d0
            while current_date <= d1:
                # Only schedule Y tasks on weekdays (Monday=0 to Friday=4, Sunday=6)
                if current_date.weekday() in [0, 1, 2, 6]:  # Mon, Tue, Wed, Sun
                    weekday_tasks[current_date] = Y_TASKS_ORDER.copy()
                current_date += timedelta(days=1)
        
        print(f"📋 Scheduling {len(weekday_tasks)} days of Y tasks")
        
        # Use the new engine to generate the complete schedule
        result = engine.schedule_range(
            workers=workers,
            start=d0,
            end=d1,
            num_closers_per_weekend=2,  # Default to 2 closers per weekend
            weekday_tasks=weekday_tasks
        )
        
        # Convert result to the format expected by the frontend
        schedule = {}
        
        # Add Y task assignments
        for date_obj, assignments in result['y_tasks'].items():
            if date_obj not in schedule:
                schedule[date_obj] = {}
            for task_type, worker_id in assignments:
                # Find worker name
                worker_name = next((w.name for w in workers if w.id == worker_id), worker_id)
                schedule[date_obj][task_type] = worker_name
        
        # Add weekend closing assignments
        for friday_date, closer_ids in result['closers'].items():
            if friday_date not in schedule:
                schedule[friday_date] = {}
            # Add closer assignments (weekend closers for Thu-Sat)
            for i, worker_id in enumerate(closer_ids):
                worker_name = next((w.name for w in workers if w.id == worker_id), worker_id)
                closer_key = "Weekend_Closer" if i == 0 else f"Weekend_Closer_{i+1}"
                schedule[friday_date][closer_key] = worker_name
        
        # Save updated worker data (scores may have been updated)
        from worker import save_workers_to_json
        save_workers_to_json(workers, os.path.join(DATA_DIR, 'worker_data.json'))
    
        # Build grid for response
        Y_TASKS_ORDER = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        all_dates = [(d0 + timedelta(days=i)) for i in range((d1-d0).days+1)]
        
        grid = []
        warnings = []
        
        # Always create rows for all 5 Y task types, even if some are empty
        for y_task in Y_TASKS_ORDER:
            row = []
            for d in all_dates:
                d_str = d.strftime('%d/%m/%Y')
                found = ''
                if d in schedule and y_task in schedule[d]:
                    found = schedule[d][y_task]
                row.append(found)
            grid.append(row)
        
        # Generate warnings from scheduling logs
        detailed_report = None
        try:
            # Use the new engine's logs for warnings
            scheduling_logs = result.get('logs', [])
            
            # Extract warnings from logs
            for log in scheduling_logs:
                if 'No candidate' in log or 'conflict' in log.lower() or 'issue' in log.lower():
                    warnings.append(log)
            
            # Create a simplified report for compatibility
            detailed_report = {
                'weekend_closing_issues': [],
                'y_task_issues': [],
                'logs': scheduling_logs
            }
            
            # Count scheduling issues
            no_candidate_logs = [log for log in scheduling_logs if 'No candidate' in log]
            if no_candidate_logs:
                warnings.append(f"Assignment issues: {len(no_candidate_logs)} tasks could not be assigned")
                detailed_report['y_task_issues'] = no_candidate_logs
        except Exception as e:
            warnings.append(f"Could not generate worker shortage report: {e}")
        
        # Compose CSV data (but don't save yet - only save when user clicks "Save")
        import csv, io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Y Task'] + [d.strftime('%d/%m/%Y') for d in all_dates])
        for i, y_task in enumerate(Y_TASKS_ORDER):
            writer.writerow([y_task] + grid[i])
        csv_data = output.getvalue()
        
        # Generate filename (but don't save yet)
        filename = f"y_tasks_{start.replace('/', '-')}_to_{end.replace('/', '-')}.csv"
        
        return jsonify({
            'success': True,
            'grid': grid,
            'dates': [d.strftime('%d/%m/%Y') for d in all_dates],  # Include dates array for frontend
            'warnings': warnings,
            'filename': filename,
            'csv_data': csv_data,  # Include CSV data for frontend to save
            'detailed_report': detailed_report
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate schedule: {e}'}), 500

@app.route('/api/y-tasks/available-soldiers', methods=['POST'])
def available_soldiers_for_y_task():
    if not is_logged_in():
        return require_login()
    try:
        from . import y_tasks
    except ImportError:
        import y_tasks
    from worker import load_workers_from_json
    data = request.get_json() or {}
    date = data.get('date')
    task = data.get('task')
    current_assignments = data.get('current_assignments', {})
    
    if not date or not task:
        return jsonify({'error': 'Missing date or task'}), 400
    
    try:
        # Parse date
        date_obj = datetime.strptime(date, '%d/%m/%Y').date()
        
        # Load workers
        workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
        
        # Load X task assignments
        year = date_obj.year
        period = 1 if date_obj.month <= 6 else 2
        x_csv = os.path.join(DATA_DIR, f"x_tasks_{year}_{period}.csv")
        
        # Load X assignments into workers
        if os.path.exists(x_csv):
            x_assignments = y_tasks.read_x_tasks(x_csv)
            for worker in workers:
                if worker.id in x_assignments:
                    for date_str, task_name in x_assignments[worker.id].items():
                        try:
                            x_date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                            worker.assign_x_task(x_date_obj, task_name)
                        except:
                            pass
        
        # Load current Y task assignments into workers
        for worker in workers:
            for wid, days in current_assignments.items():
                if wid == worker.id:
                    for day_str, task_name in days.items():
                        if task_name and task_name != '-':
                            try:
                                y_date_obj = datetime.strptime(day_str, '%d/%m/%Y').date()
                                worker.y_tasks[y_date_obj] = task_name
                            except:
                                pass
        
        # Use the same logic as the scheduler engine
        available = []
        for worker in workers:
            # Skip if worker doesn't have this qualification
            if task not in worker.qualifications:
                    continue
            
            # Skip if worker has X task on this day (except Rituk)
            has_rituk = worker.has_specific_x_task(date_obj, "Rituk")
            if date_obj in worker.x_tasks and not has_rituk:
                continue
            
            # Skip if worker already has Y task on this day
            if date_obj in worker.y_tasks:
                continue
            
            # Skip if worker finished X task within last 2 days
            recently_finished = False
            for i in range(1, 3):  # 1 and 2 days ago
                check_date = date_obj - timedelta(days=i)
                if check_date in worker.x_tasks:
                    recently_finished = True
                    break
            
            if recently_finished:
                continue
            
            available.append(worker)
        
        # Return list of dicts with id and name
        return jsonify({'available': [{'id': w.id, 'name': w.name} for w in available]})
        
    except Exception as e:
        return jsonify({'error': f'Failed to get available soldiers: {str(e)}'}), 500

# --- Combined Schedule API ---
@app.route('/api/combined', methods=['GET'])
def get_combined():
    if not is_logged_in():
        return require_login()
    """
    Dynamically build a combined CSV from the latest Y schedule and current X tasks.
    - First row: ["Y Tasks", <dd/mm/yyyy>, <dd/mm/yyyy>, ...]
    - First column: task names (Y tasks first)
    - Cells: worker names assigned to that task on that date
    """
    import csv, io, glob, re
    try:
        try:
            from . import y_tasks
        except ImportError:
            import y_tasks

        # 1) Determine Y schedule to use (latest in index)
        schedules = y_tasks.list_y_task_schedules()
        if not schedules:
            return '', 200, {'Content-Type': 'text/csv'}
        # pick the first (list_y_task_schedules returns list in existing order)
        start, end, y_filename = schedules[0]
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            return '', 200, {'Content-Type': 'text/csv'}

        # 2) Read Y CSV
        with open(y_path, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        if not rows or len(rows) < 2:
            return '', 200, {'Content-Type': 'text/csv'}
        dates = rows[0][1:]
        y_task_names = [r[0] for r in rows[1:]]
        y_grid = [r[1:] for r in rows[1:]]

        # 3) Optionally expand X tasks for these dates
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        x_files = glob.glob(os.path.join(data_dir, 'x_tasks_*.csv'))
        x_assignments = {}
        if x_files:
            def extract_year_period(fname):
                m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
                if m:
                    return int(m.group(1)), int(m.group(2))
                return (0, 0)
            x_files.sort(key=extract_year_period, reverse=True)
            x_csv = x_files[0]
            x_assignments = y_tasks.read_x_tasks(x_csv)

        # Build CSV
        out = io.StringIO()
        writer = csv.writer(out)
        # Header row: label then dates
        writer.writerow(["Y Tasks"] + dates)
        # Y task rows
        for i, task in enumerate(y_task_names):
            writer.writerow([task] + y_grid[i])

        # Optionally, append unique X task rows under a separator
        # Collect X tasks for these dates
        x_task_set = set()
        for name, day_map in x_assignments.items():
            for d in dates:
                t = day_map.get(d, '-')
                if t and t != '-' and t not in y_task_names:
                    x_task_set.add(t)
        if x_task_set:
            # Separator row
            writer.writerow([])
            writer.writerow(["X Tasks"] + ["" for _ in dates])
            for xt in sorted(x_task_set):
                row = []
                for d in dates:
                    assigned = ''
                    for name, day_map in x_assignments.items():
                        if day_map.get(d, '-') == xt:
                            assigned = name
                            break
                    row.append(assigned)
                writer.writerow([xt] + row)

        csv_text = out.getvalue()
        return csv_text, 200, {'Content-Type': 'text/csv'}
    except Exception as e:
        return '', 200, {'Content-Type': 'text/csv'}

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
    try:
        from . import y_tasks
    except ImportError:
        import y_tasks
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
    try:
        from . import y_tasks
    except ImportError:
        import y_tasks
    conflicts = []
    year = int(request.args.get('year', datetime.today().year))
    period = int(request.args.get('period', 1))
    x_path = os.path.join(DATA_DIR, f"x_tasks_{year}_{period}.csv")
    
    # Check if X-tasks file exists
    if not os.path.exists(x_path):
        print(f"[DEBUG] X-tasks file not found: {x_path}")
        return jsonify({'conflicts': [], 'message': f'No X-tasks file found for {year} period {period}'})
    
    x_assignments = y_tasks.read_x_tasks(x_path)
    
    # Check if any Y-task schedules exist
    y_schedules = list(y_tasks.list_y_task_schedules())
    if not y_schedules:
        print(f"[DEBUG] No Y-task schedules found")
        return jsonify({'conflicts': [], 'message': 'No Y-task schedules found'})
    
    # Check all Y task CSVs
    for start, end, y_filename in y_schedules:
        y_path = y_tasks.y_schedule_path(y_filename)
        if not os.path.exists(y_path):
            print(f"[DEBUG] Y-task file not found: {y_path}")
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
    
    try:
        # Get Y task manager
        try:
            from .y_task_manager import get_y_task_manager
            y_task_manager = get_y_task_manager(DATA_DIR)
        except ImportError:
            try:
                from y_task_manager import get_y_task_manager
                y_task_manager = get_y_task_manager(DATA_DIR)
            except ImportError:
                return jsonify({'error': 'Y task manager not available'}), 500
        
        # Find the period key for this filename
        index_path = os.path.join(DATA_DIR, 'y_tasks_index.json')
        if not os.path.exists(index_path):
            return jsonify({'error': 'Y task index not found'}), 404
        
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Find the period key that matches this filename
        period_key = None
        for key, data in index.items():
            if data.get('filename') == filename:
                period_key = key
                break
        
        if not period_key:
            return jsonify({'error': 'Schedule not found in index'}), 404
        
        # Extract start and end dates from period key
        # Format: "start_date_to_end_date"
        parts = period_key.split('_to_')
        if len(parts) != 2:
            return jsonify({'error': 'Invalid period key format'}), 400
        
        start_date = parts[0].replace('-', '/')
        end_date = parts[1].replace('-', '/')
        
        # Use the Y task manager's deletion method
        success = y_task_manager.delete_y_task_period(start_date, end_date)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete schedule'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

@app.route('/api/y-tasks/insufficient-workers-report', methods=['POST'])
def get_insufficient_workers_report():
    if not is_logged_in():
        return require_login()
    data = request.get_json() or {}
    start = data.get('start')  # Expect dd/mm/yyyy
    end = data.get('end')
    
    if not start or not end:
        return jsonify({'error': 'Missing start or end date'}), 400
    
    try:
        d0 = datetime.strptime(start, '%d/%m/%Y').date()
        d1 = datetime.strptime(end, '%d/%m/%Y').date()
        
        # Load workers
        workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
        
        # Load X task assignments
        x_assignments = {}
        try:
            # Check if date range spans across the transition period (June to July)
            start_period = 1 if d0.month <= 6 else 2
            end_period = 1 if d1.month <= 6 else 2
            
            # Load X task files for all periods that overlap with the date range
            periods_to_load = set()
            periods_to_load.add(start_period)
            periods_to_load.add(end_period)
            
            # If the range spans across the transition, we need both periods
            if start_period != end_period:
                periods_to_load.add(1)
                periods_to_load.add(2)
            
            for period in periods_to_load:
                x_csv = os.path.join(DATA_DIR, f"x_tasks_{d0.year}_{period}.csv")
                if os.path.exists(x_csv):
                    try:
                        from . import y_tasks
                    except ImportError:
                        import y_tasks
                    period_assignments = y_tasks.read_x_tasks(x_csv)
                    
                    # Merge assignments from this period
                    for worker_id, assignments in period_assignments.items():
                        if worker_id not in x_assignments:
                            x_assignments[worker_id] = {}
                        x_assignments[worker_id].update(assignments)
            
            # Load X assignments into workers
            for worker in workers:
                if worker.id in x_assignments:
                    for date_str, task_name in x_assignments[worker.id].items():
                        try:
                            date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                            worker.assign_x_task(date_obj, task_name)
                        except Exception as e:
                            print(f"Error parsing date {date_str}: {e}")
        except Exception as e:
            print(f"Warning: Could not load X task data: {e}")
        
        # Use new system to generate availability report
        print(f"🔍 Generating availability report with new system")
        
        # Create basic availability analysis
        Y_TASKS_ORDER = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
        
        # Analyze worker availability for each task type
        task_availability = {}
        for task in Y_TASKS_ORDER:
            qualified_workers = [w for w in workers if task in w.qualifications]
            task_availability[task] = {
                'total_qualified': len(qualified_workers),
                'qualified_workers': [w.name for w in qualified_workers]
            }
        
        # Check for potential issues
        y_task_issues = []
        weekend_closing_issues = []
        
        # Check Y task qualification coverage
        for task, info in task_availability.items():
            if info['total_qualified'] < 2:  # Flag if fewer than 2 qualified workers
                y_task_issues.append({
                    'task': task,
                    'qualified_count': info['total_qualified'],
                    'qualified_workers': info['qualified_workers'],
                    'severity': 'high' if info['total_qualified'] == 0 else 'medium'
                })
        
        # Check weekend closing capacity (simplified check)
        total_workers = len(workers)
        if total_workers < 4:  # Need at least 4 workers for sustainable weekend closing
            weekend_closing_issues.append({
                'issue': 'insufficient_total_workers',
                'total_workers': total_workers,
                'recommended_minimum': 4
            })
        
        # Build report in the format expected by frontend
        report = {
            'y_task_issues': y_task_issues,
            'weekend_closing_issues': weekend_closing_issues,
            'task_availability': task_availability,
            'summary': {
                'total_workers': total_workers,
                'total_issues': len(y_task_issues) + len(weekend_closing_issues)
            },
            'detailed_y_task_issues': [],  # For compatibility
            'period': f"{start} to {end}"
        }
        
        return jsonify(report), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate report: {str(e)}'}), 500

@app.route('/api/combined/available-dates', methods=['GET'])
def get_combined_available_dates():
    # Returns all dates covered by any Y schedule
    try:
        from . import y_tasks
    except ImportError:
        import y_tasks
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
    try:
        from . import y_tasks, x_tasks
    except ImportError:
        import y_tasks
        import x_tasks
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
    try:
        from . import y_tasks
    except ImportError:
        import y_tasks
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
    
    # Define DATA_DIR
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
    
    # Get Y task manager
    try:
        from .y_task_manager import get_y_task_manager
        y_task_manager = get_y_task_manager(DATA_DIR)
    except ImportError:
        try:
            from y_task_manager import get_y_task_manager
            y_task_manager = get_y_task_manager(DATA_DIR)
        except ImportError:
            return jsonify({'error': 'Y task manager not available'}), 500
    
    import csv
    from datetime import datetime, timedelta
    # Parse requested range as dates
    d0 = datetime.strptime(start, '%d/%m/%Y').date()
    d1 = datetime.strptime(end, '%d/%m/%Y').date()
    dates_set = set()
    
    # Collect Y assignments for this period using the new Y task manager
    y_data_by_date = {}
    periods = y_task_manager.list_y_task_periods()
    for period in periods:
        period_start = period['start_date']
        period_end = period['end_date']
        filename = period['filename']
        
        # Check if this period overlaps with the requested range
        try:
            p_start = datetime.strptime(period_start, '%d/%m/%Y').date()
            p_end = datetime.strptime(period_end, '%d/%m/%Y').date()
            req_start = datetime.strptime(start, '%d/%m/%Y').date()
            req_end = datetime.strptime(end, '%d/%m/%Y').date()
            
            # Check for overlap
            if p_start <= req_end and p_end >= req_start:
                y_path = os.path.join(DATA_DIR, filename)
                if os.path.exists(y_path):
                    with open(y_path, 'r', encoding='utf-8') as f:
                        reader = list(csv.reader(f))
                        if not reader or len(reader) < 2:
                            continue
                        file_dates = reader[0][1:]
                        for row in reader[1:]:
                            y_task = row[0]
                            for i, d in enumerate(file_dates):
                                try:
                                    dd = datetime.strptime(d, '%d/%m/%Y').date()
                                except Exception:
                                    continue
                                if dd < d0 or dd > d1:
                                    continue
                                dates_set.add(d)
                                if d not in y_data_by_date:
                                    y_data_by_date[d] = {}
                                y_data_by_date[d][y_task] = row[i+1] if i+1 < len(row) else ''
        except Exception as e:
            print(f"Error processing Y task period {period_start} to {period_end}: {e}")
            continue
    # Final dates list sorted ascending; fallback to full requested range if no Y dates found
    dates = sorted(list(dates_set), key=lambda ds: datetime.strptime(ds, '%d/%m/%Y').date())
    if not dates:
        # Fallback: build daily dates across the requested range
        span = (d1 - d0).days
        dates = [(d0 + timedelta(days=i)).strftime('%d/%m/%Y') for i in range(span + 1)]
    # Get X assignments for this period
    import glob
    import re
    x_files = glob.glob(os.path.join(DATA_DIR, 'x_tasks_*.csv'))
    if not x_files:
        x_assignments = {}
    else:
        # Find the X tasks file that covers the date range
        def extract_year_period(fname):
            m = re.search(r'x_tasks_(\d+)_(\d+)\.csv', fname)
            if m:
                return int(m.group(1)), int(m.group(2))
            return (0, 0)
        
        # Sort files by year and period
        x_files.sort(key=extract_year_period)
        
        # Use canonical parser that returns dd/mm/yyyy -> task mapping per worker
        x_csv = x_files[0] if x_files else None
        x_assignments = {}
        if x_csv and os.path.exists(x_csv):
            try:
                try:
                    from . import y_tasks as y_tasks_module
                except ImportError:
                    import y_tasks as y_tasks_module
                x_assignments = y_tasks_module.read_x_tasks(x_csv)
            except Exception as e:
                print(f"Error reading X tasks file {x_csv}: {e}")
                x_assignments = {}
    # Collect all unique X tasks assigned for any date in the period
    x_tasks_set = set()
    for name, day_map in x_assignments.items():
        for d in dates:
            task = day_map.get(d, '-')
            if task and task != '-' and task not in ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]:
                x_tasks_set.add(task)
    x_tasks_list = sorted(x_tasks_set)
    # Build X task rows: for each X task, fill with all soldier names for each date
    x_grid = []
        # Load worker data for ID to name conversion
    from worker import load_workers_from_json
    workers = load_workers_from_json(os.path.join(DATA_DIR, 'worker_data.json'))
    worker_id_to_name = {w.id: w.name for w in workers}
    
    for x_task in x_tasks_list:
        row = []
        for d in dates:
            found = []
            for name, day_map in x_assignments.items():
                if day_map.get(d, '-') == x_task:
                    # Convert worker ID to name
                    worker_name = worker_id_to_name.get(name, name)
                    found.append(worker_name)
            row.append(', '.join(found))
        x_grid.append(row)
    y_tasks_list = ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    grid = []
    # Y tasks rows filled from y_data_by_date
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
    
    # Normalize header to use dd/mm/yyyy dates (remove any "name" column and numeric indices)
    try:
        import csv, io
        # Try to infer dates from existing Y schedule for this range
        # Filename format: combined_dd-mm-yyyy_dd-mm-yyyy.csv
        import re
        m = re.search(r'combined_(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2}-\d{4})', filename)
        inferred_dates = []
        if m:
            start_str = m.group(1).replace('-', '/')
            end_str = m.group(2).replace('-', '/')
            try:
                from .y_task_manager import get_y_task_manager
                y_task_manager = get_y_task_manager(DATA_DIR)
            except Exception:
                y_task_manager = None
            if y_task_manager:
                # Find a matching/overlapping Y schedule and read its header dates
                periods = y_task_manager.list_y_task_periods()
                for period in periods:
                    if period['start_date'] == start_str and period['end_date'] == end_str:
                        y_path = os.path.join(DATA_DIR, period['filename'])
                        if os.path.exists(y_path):
                            with open(y_path, 'r', encoding='utf-8') as yf:
                                rows = list(csv.reader(yf))
                                if rows:
                                    inferred_dates = rows[0][1:]  # skip 'Y Task'
                        break
        # Parse posted CSV
        buf = io.StringIO(csv_data)
        rows = list(csv.reader(buf))
        if rows:
            header = rows[0]
            # Build correct header: ["Task"] + inferred_dates (if available)
            if inferred_dates:
                rows[0] = ["Task"] + inferred_dates
            else:
                # Fallback: keep any non-numeric labels from existing header
                cleaned = ["Task"]
                for h in header[1:]:
                    if re.fullmatch(r"\d+", h or ""):
                        continue
                    if h and h.lower() != 'name':
                        cleaned.append(h)
                rows[0] = cleaned if len(cleaned) > 1 else header
            # Rewrite any '-' cells to empty string
            for r in range(1, len(rows)):
                rows[r] = [ ('' if (c == '-' or c is None) else c) for c in rows[r] ]
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerows(rows)
            csv_data = out.getvalue()
    except Exception:
        # On any error, fall back to raw csv_data
        pass
    
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

@app.route('/api/workers/reload', methods=['POST'])
def reload_workers():
    """Reload workers from JSON file"""
    if not is_logged_in():
        return require_login()
    try:
        load_workers_to_memory()
        return jsonify({'success': True, 'count': len(WORKERS)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/workers', methods=['GET'])
def get_workers():
    if not is_logged_in():
        return require_login()
    # Return id, name, qualifications, closing_interval, officer
    result = [
        {
            'id': getattr(w, 'id', None),
            'name': w.name,
            'qualifications': w.qualifications,
            'closing_interval': getattr(w, 'closing_interval', 4),
            'officer': getattr(w, 'officer', False)
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
    # Write all workers back to JSON
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
    
    # Convert workers to JSON-serializable format
    workers_data = []
    for worker in WORKERS:
        worker_dict = {
            'id': worker.id,
            'name': worker.name,
            'qualifications': worker.qualifications,
            'closing_interval': worker.closing_interval,
            'officer': worker.officer,
            'seniority': worker.seniority,
            'score': worker.score,
            'x_tasks': {str(k): v for k, v in worker.x_tasks.items()},
            'y_tasks': {str(k): v for k, v in worker.y_tasks.items()},
            'closing_history': [str(d) for d in worker.closing_history]
        }
        workers_data.append(worker_dict)
    
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(workers_data, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'worker': worker_dict})

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
    
    # Convert workers to JSON-serializable format
    workers_data = []
    for worker in WORKERS:
        worker_dict = {
            'id': worker.id,
            'name': worker.name,
            'qualifications': worker.qualifications,
            'closing_interval': worker.closing_interval,
            'officer': worker.officer,
            'seniority': worker.seniority,
            'score': worker.score,
            'x_tasks': {str(k): v for k, v in worker.x_tasks.items()},
            'y_tasks': {str(k): v for k, v in worker.y_tasks.items()},
            'closing_history': [str(d) for d in worker.closing_history]
        }
        workers_data.append(worker_dict)
    
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(workers_data, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'worker': workers_data[0] if workers_data else {}})

@app.route('/api/workers/<id>', methods=['DELETE'])
def delete_worker(id):
    if not is_logged_in():
        return require_login()
    global WORKERS
    before = len(WORKERS)
    WORKERS = [w for w in WORKERS if str(getattr(w, 'id', None)) != str(id)]
    after = len(WORKERS)
    
    # Convert workers to JSON-serializable format
    workers_data = []
    for worker in WORKERS:
        worker_dict = {
            'id': worker.id,
            'name': worker.name,
            'qualifications': worker.qualifications,
            'closing_interval': worker.closing_interval,
            'officer': worker.officer,
            'seniority': worker.seniority,
            'score': worker.score,
            'x_tasks': {str(k): v for k, v in worker.x_tasks.items()},
            'y_tasks': {str(k): v for k, v in worker.y_tasks.items()},
            'closing_history': [str(d) for d in worker.closing_history]
        }
        workers_data.append(worker_dict)
    
    with open(WORKER_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(workers_data, f, ensure_ascii=False, indent=2)
    if before == after:
        return jsonify({'error': 'Worker not found'}), 404
    return jsonify({'success': True})

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """
    Get comprehensive statistics for charts and analysis
    
    SINGLE SOURCE OF TRUTH: worker_data.json only
    
    This endpoint ONLY reads from worker_data.json to ensure data consistency.
    All task assignments, worker information, and metrics are derived from worker objects.
    
    Data Sources (ENFORCED):
    ✅ worker_data.json - worker info, x_tasks, y_tasks, closing_history, scores
    ❌ CSV files - NO direct CSV reading (CSV files are export/import only)
    ❌ Y-task manager CSV access - NO external file parsing
    ❌ Multiple data sources - SINGLE source of truth principle
    
    This ensures:
    - Data consistency across the application
    - No double-counting of tasks
    - Reliable statistics that match the main data store
    - Better performance (no CSV parsing)
    """
    if not is_logged_in():
        return require_login()
    
    try:
        # Define paths
        DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
        WORKER_JSON_PATH = os.path.join(DATA_DIR, 'worker_data.json')
        
        # SINGLE SOURCE OF TRUTH: Load all data from worker_data.json only
        workers = load_workers_from_json(WORKER_JSON_PATH)
        
        print(f"📊 Statistics: Loading data for {len(workers)} workers from worker_data.json")
        
        # Count X and Y tasks from worker objects (single source of truth)
        all_x_tasks = {}
        all_y_tasks = {}
        x_tasks_timeline = []
        y_tasks_timeline = []
        
        # Initialize closing tracking variables (used throughout statistics)
        worker_closing_counts = {}
        worker_closing_dates = {}
        
        # Extract task counts directly from worker objects
        for worker in workers:
            worker_id = worker.id
            
            # Count X tasks from worker's x_tasks field
            x_task_count = len(worker.x_tasks) if worker.x_tasks else 0
            all_x_tasks[worker_id] = x_task_count
            
            # Count Y tasks from worker's y_tasks field
            y_task_count = len(worker.y_tasks) if worker.y_tasks else 0
            all_y_tasks[worker_id] = y_task_count
        
        # Create simplified timeline data based on current date
        current_year = datetime.now().year
        
        # X-tasks timeline (simplified - based on total current assignments)
        total_x_tasks = sum(all_x_tasks.values())
        if total_x_tasks > 0:
            x_tasks_timeline.append({
                'period': f"{current_year}-Current",
                'year': current_year,
                'half': 1,
                'total_tasks': total_x_tasks
            })
        
        # Y-tasks timeline (simplified - based on total current assignments)
        total_y_tasks = sum(all_y_tasks.values())
        if total_y_tasks > 0:
            y_tasks_timeline.append({
                'period': f"Current Assignments",
                'total_tasks': total_y_tasks
            })
        
        print(f"📊 Statistics: Found {total_x_tasks} X-tasks and {total_y_tasks} Y-tasks from worker data")
        
        # Check if we have meaningful data to display
        has_meaningful_data = total_x_tasks > 0 or total_y_tasks > 0
        
        if not has_meaningful_data:
            print("📊 Statistics: No task assignments found - returning empty statistics")
            return jsonify({
                'x_tasks_pie': [],
                'y_tasks_pie': [],
                'combined_pie': [],
                'x_tasks_timeline': [],
                'y_tasks_timeline': [],
                'fairness_metrics': {
                    'seniority_distribution': {},
                    'score_vs_tasks': [],
                    'weekend_vs_weekday': {},
                    'task_type_distribution': {},
                    'qualification_utilization': {},
                    'y_task_analysis': {'worker_distribution': [], 'statistics': None},
                    'closing_interval_analysis': {'worker_distribution': [], 'statistics': None},
                    'worker_performance_metrics': []
                },
                'summary': {
                    'total_workers': len(workers),
                    'total_x_tasks': 0,
                    'total_y_tasks': 0,
                    'total_combined': 0,
                    'data_source': 'worker_data.json',
                    'note': 'No task assignments found - statistics will populate when tasks are assigned'
                },
                'y_task_bar_chart': [],
                'score_vs_y_tasks': [],
                'closing_accuracy': [],
                'qualification_analysis': [],
                'workload_distribution': [],
                'seniority_analysis': [],
                'task_timeline_analysis': [],
                'average_y_tasks': 0
            })
        
        # Prepare pie chart data
        x_tasks_pie = []
        y_tasks_pie = []
        combined_pie = []
        
        for worker in workers:
            x_count = all_x_tasks.get(worker.id, 0)
            y_count = all_y_tasks.get(worker.id, 0)
            combined_count = x_count + y_count
            
            if x_count > 0:
                x_tasks_pie.append({
                    'name': worker.name,
                    'value': x_count,
                    'worker_id': worker.id
                })
            
            if y_count > 0:
                y_tasks_pie.append({
                    'name': worker.name,
                    'value': y_count,
                    'worker_id': worker.id
                })
            
            if combined_count > 0:
                combined_pie.append({
                    'name': worker.name,
                    'value': combined_count,
                    'worker_id': worker.id
                })
        
        # Sort by value (descending)
        x_tasks_pie.sort(key=lambda x: x['value'], reverse=True)
        y_tasks_pie.sort(key=lambda x: x['value'], reverse=True)
        combined_pie.sort(key=lambda x: x['value'], reverse=True)
        
        # Prepare bar chart data for X tasks timeline
        x_tasks_timeline.sort(key=lambda x: (x['year'], x['half']))
        
        # Calculate percentages for pie charts
        total_x = sum(item['value'] for item in x_tasks_pie)
        total_y = sum(item['value'] for item in y_tasks_pie)
        total_combined = sum(item['value'] for item in combined_pie)
        
        for item in x_tasks_pie:
            item['percentage'] = round((item['value'] / total_x * 100), 1) if total_x > 0 else 0
        
        for item in y_tasks_pie:
            item['percentage'] = round((item['value'] / total_y * 100), 1) if total_y > 0 else 0
        
        for item in combined_pie:
            item['percentage'] = round((item['value'] / total_combined * 100), 1) if total_combined > 0 else 0
        
        # Calculate fairness metrics
        fairness_metrics = {
            'seniority_distribution': {},
            'score_vs_tasks': [],
            'weekend_vs_weekday': {},
            'task_type_distribution': {},
            'qualification_utilization': {},
            'y_task_analysis': {},
            'closing_interval_analysis': {},
            'worker_performance_metrics': []
        }

        # TODO: REMOVE OLD FAIRNESS METRICS
        # Seniority distribution
        for worker in workers:
            # Handle seniority values properly - convert to string for consistent comparison
            if worker.seniority and worker.seniority != 'None':
                try:
                    # Try to convert to int first, then to string for consistent formatting
                    seniority = str(int(worker.seniority))
                except (ValueError, TypeError):
                    seniority = str(worker.seniority)
            else:
                seniority = 'Unknown'
            
            if seniority not in fairness_metrics['seniority_distribution']:
                fairness_metrics['seniority_distribution'][seniority] = {'x_tasks': 0, 'y_tasks': 0, 'workers': 0}
            fairness_metrics['seniority_distribution'][seniority]['x_tasks'] += all_x_tasks.get(worker.id, 0)
            fairness_metrics['seniority_distribution'][seniority]['y_tasks'] += all_y_tasks.get(worker.id, 0)
            fairness_metrics['seniority_distribution'][seniority]['workers'] += 1
        
        # Score vs tasks correlation
        for worker in workers:
            score = int(worker.score) if worker.score is not None else 0
            total_tasks = all_x_tasks.get(worker.id, 0) + all_y_tasks.get(worker.id, 0)
            fairness_metrics['score_vs_tasks'].append({
                'worker_name': worker.name,
                'score': score,
                'total_tasks': total_tasks,
                'x_tasks': all_x_tasks.get(worker.id, 0),
                'y_tasks': all_y_tasks.get(worker.id, 0)
            })
        
        # Sort by score for better visualization
        fairness_metrics['score_vs_tasks'].sort(key=lambda x: x['score'], reverse=True)
        
        # Qualification utilization
        all_qualifications = set()
        for worker in workers:
            all_qualifications.update(worker.qualifications)
        
        for qualification in all_qualifications:
            qualified_workers = [w for w in workers if qualification in w.qualifications]
            total_qualified_tasks = sum(all_x_tasks.get(w.id, 0) + all_y_tasks.get(w.id, 0) for w in qualified_workers)
            fairness_metrics['qualification_utilization'][qualification] = {
                'qualified_workers': len(qualified_workers),
                'total_tasks': total_qualified_tasks,
                'avg_tasks_per_worker': total_qualified_tasks / len(qualified_workers) if qualified_workers and len(qualified_workers) > 0 else 0
            }
        
        # Task distribution histogram
        task_counts = []
        for worker in workers:
            total_tasks = all_x_tasks.get(worker.id, 0) + all_y_tasks.get(worker.id, 0)
            task_counts.append(total_tasks)
        
        # Create histogram bins
        if task_counts:
            min_tasks = min(task_counts)
            max_tasks = max(task_counts)
            bin_size = (max_tasks - min_tasks) / 10 if max_tasks > min_tasks else 1
            
            histogram = {}
            for i in range(10):
                bin_start = min_tasks + (i * bin_size)
                bin_end = min_tasks + ((i + 1) * bin_size)
                bin_label = f"{int(bin_start)}-{int(bin_end)}"
                histogram[bin_label] = 0
            
            # Count workers in each bin
            for count in task_counts:
                bin_index = min(9, int((count - min_tasks) / bin_size) if bin_size > 0 else 0)
                bin_start = min_tasks + (bin_index * bin_size)
                bin_end = min_tasks + ((bin_index + 1) * bin_size)
                bin_label = f"{int(bin_start)}-{int(bin_end)}"
                histogram[bin_label] += 1
            
            fairness_metrics['task_distribution_histogram'] = histogram
        
        # Y Task Analysis
        y_task_workers = []
        for worker in workers:
            y_count = all_y_tasks.get(worker.id, 0)
            if y_count > 0:
                # Count actual closing assignments from Y task data
                closing_count = 0
                if worker.id in worker_closing_counts:
                    closing_count = worker_closing_counts[worker.id]
                
                y_task_workers.append({
                    'worker_name': worker.name,
                    'worker_id': worker.id,
                    'y_tasks': y_count,
                    'score': int(worker.score) if worker.score is not None else 0,
                    'seniority': worker.seniority if worker.seniority and worker.seniority != 'None' else 'Unknown',
                    'closing_interval': worker.closing_interval,
                    'qualifications': worker.qualifications,
                    'closing_count': closing_count,
                    'closing_dates': worker_closing_dates.get(worker.id, [])
                })
        
        # Sort by Y task count for better visualization
        y_task_workers.sort(key=lambda x: x['y_tasks'], reverse=True)
        fairness_metrics['y_task_analysis']['worker_distribution'] = y_task_workers
        
        # Calculate Y task statistics
        if y_task_workers:
            y_task_counts = [w['y_tasks'] for w in y_task_workers]
            fairness_metrics['y_task_analysis']['statistics'] = {
                'total_workers_with_y_tasks': len(y_task_workers),
                'average_y_tasks_per_worker': sum(y_task_counts) / len(y_task_counts) if y_task_counts else 0,
                'median_y_tasks': sorted(y_task_counts)[len(y_task_counts)//2] if y_task_counts else 0,
                'min_y_tasks': min(y_task_counts) if y_task_counts else 0,
                'max_y_tasks': max(y_task_counts) if y_task_counts else 0,
                'standard_deviation': (sum((x - sum(y_task_counts)/len(y_task_counts))**2 for x in y_task_counts) / len(y_task_counts))**0.5 if y_task_counts and len(y_task_counts) > 1 else 0
            }
        
        # Closing Interval Analysis - Count actual closings from Y task data
        closing_workers = []
        
        # Initialize closing tracking variables for interval analysis
        
        # Count closing assignments from worker's closing_history (single source of truth)
        for worker in workers:
            closing_count = len(worker.closing_history) if worker.closing_history else 0
            worker_closing_counts[worker.id] = closing_count
            
            # Convert closing dates to strings in dd/mm/yyyy format for compatibility
            closing_date_strings = []
            if worker.closing_history:
                for closing_date in worker.closing_history:
                    if isinstance(closing_date, date):
                        closing_date_strings.append(closing_date.strftime('%d/%m/%Y'))
                    elif isinstance(closing_date, str):
                        closing_date_strings.append(closing_date)
            worker_closing_dates[worker.id] = closing_date_strings
        
        # Calculate closing interval accuracy for each worker
        for worker in workers:
            if worker.closing_interval > 0:  # Only workers who participate in closing
                total_closings = worker_closing_counts.get(worker.id, 0)
                
                # Calculate total weeks in the data period
                # For the Y task data, we have from July 2025 to January 2026 (about 26 weeks)
                total_weeks = 26  # Approximate based on the data period
                
                # Calculate how well they follow their interval
                if total_closings > 0 and total_weeks > 0 and worker.closing_interval > 0:
                    actual_interval = total_weeks / total_closings
                    interval_accuracy = abs(actual_interval - worker.closing_interval) / worker.closing_interval
                    interval_percentage = max(0, 100 - (interval_accuracy * 100))
                else:
                    actual_interval = 0
                    interval_accuracy = 1
                    interval_percentage = 0
                
                closing_workers.append({
                    'worker_name': worker.name,
                    'worker_id': worker.id,
                    'closing_interval': worker.closing_interval,
                    'total_closings': total_closings,
                    'total_weeks_served': total_weeks,
                    'actual_interval': round(actual_interval, 2),
                    'interval_accuracy': round(interval_percentage, 2),
                    'closing_dates': worker_closing_dates.get(worker.id, []),
                    'score': int(worker.score) if worker.score is not None else 0
                })
        
        # Sort by interval accuracy for better visualization
        closing_workers.sort(key=lambda x: x['interval_accuracy'], reverse=True)
        fairness_metrics['closing_interval_analysis']['worker_distribution'] = closing_workers
        
        # Calculate closing interval statistics
        if closing_workers:
            accuracy_scores = [w['interval_accuracy'] for w in closing_workers]
            fairness_metrics['closing_interval_analysis']['statistics'] = {
                'total_closing_workers': len(closing_workers),
                'average_accuracy': sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
                'workers_above_90_percent': sum(1 for acc in accuracy_scores if acc >= 90),
                'workers_above_80_percent': sum(1 for acc in accuracy_scores if acc >= 80),
                'workers_below_50_percent': sum(1 for acc in accuracy_scores if acc < 50),
                'algorithm_accuracy_percentage': sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
            }
        
        # Worker Performance Metrics (for algorithm improvement)
        for worker in workers:
            x_count = all_x_tasks.get(worker.id, 0)
            y_count = all_y_tasks.get(worker.id, 0)
            total_tasks = x_count + y_count
            
                        # Calculate workload balance
            if total_tasks > 0:
                x_percentage = (x_count / total_tasks) * 100
                y_percentage = (y_count / total_tasks) * 100
            else:
                x_percentage = 0
                y_percentage = 0
            
            # Calculate if worker is overworked/underworked
            avg_tasks_per_worker = total_combined / len(workers) if workers else 0
            workload_deviation = ((total_tasks - avg_tasks_per_worker) / avg_tasks_per_worker) * 100 if avg_tasks_per_worker > 0 else 0
            
            fairness_metrics['worker_performance_metrics'].append({
                'worker_name': worker.name,
                'worker_id': worker.id,
                'total_tasks': total_tasks,
                'x_tasks': x_count,
                'y_tasks': y_count,
                'x_percentage': round(x_percentage, 2),
                'y_percentage': round(y_percentage, 2),
                'workload_deviation': round(workload_deviation, 2),
                'score': int(worker.score) if worker.score is not None else 0,
                'seniority': worker.seniority if worker.seniority and worker.seniority != 'None' else 'Unknown',
                'closing_interval': worker.closing_interval,
                'qualifications': worker.qualifications
            })
        
        # Sort by workload deviation to identify overworked/underworked workers
        fairness_metrics['worker_performance_metrics'].sort(key=lambda x: abs(x['workload_deviation']), reverse=True)
        
        # ENHANCED: Calculate Y task distribution with color coding for bar chart
        y_task_bar_data = []
        if y_task_workers:
            avg_y_tasks = sum(w['y_tasks'] for w in y_task_workers) / len(y_task_workers)
            tolerance = avg_y_tasks * 0.05  # 5% tolerance
            
            for worker in y_task_workers:
                if worker['y_tasks'] > avg_y_tasks + tolerance:
                    color = 'red'  # Overworked
                elif worker['y_tasks'] < avg_y_tasks - tolerance:
                    color = 'blue'  # Underworked
                else:
                    color = 'green'  # Average range
                
                y_task_bar_data.append({
                    'name': worker['worker_name'],
                    'y_tasks': worker['y_tasks'],
                    'color': color,
                    'deviation': worker['y_tasks'] - avg_y_tasks,
                    'percentage': round((worker['y_tasks'] / avg_y_tasks) * 100, 1)
                })
        
        # ENHANCED: Score vs Y tasks correlation analysis
        score_vs_y_tasks = []
        for worker in workers:
            y_count = all_y_tasks.get(worker.id, 0)
            score = int(worker.score) if worker.score is not None else 0
            score_vs_y_tasks.append({
                'name': worker.name,
                'score': score,
                'y_tasks': y_count,
                'ratio': round(y_count / score, 2) if score > 0 else 0
            })
        
        # Sort by score for better visualization
        score_vs_y_tasks.sort(key=lambda x: x['score'], reverse=True)
        
        # ENHANCED: Closing interval accuracy analysis
        closing_accuracy_data = []
        for worker in workers:
            if worker.closing_interval > 0:
                actual_closings = worker_closing_counts.get(worker.id, 0)
                total_weeks = 26  # Approximate based on data period
                
                if actual_closings > 0:
                    actual_interval = total_weeks / actual_closings
                    accuracy_percentage = max(0, 100 - (abs(actual_interval - worker.closing_interval) / worker.closing_interval) * 100)
                else:
                    accuracy_percentage = 0
                    actual_interval = 0
                
                closing_accuracy_data.append({
                    'name': worker.name,
                    'target_interval': worker.closing_interval,
                    'actual_interval': round(actual_interval, 2),
                    'accuracy_percentage': round(accuracy_percentage, 1),
                    'total_closings': actual_closings,
                    'color': 'green' if accuracy_percentage >= 80 else 'orange' if accuracy_percentage >= 60 else 'red'
                })
        
        # ENHANCED: Additional useful graphs
        # 1. Qualification utilization analysis
        qualification_analysis = []
        for qualification in all_qualifications:
            qualified_workers = [w for w in workers if qualification in w.qualifications]
            total_tasks = sum(all_y_tasks.get(w.id, 0) for w in qualified_workers)
            avg_tasks_per_qualified = total_tasks / len(qualified_workers) if qualified_workers else 0
            
            qualification_analysis.append({
                'qualification': qualification,
                'qualified_workers': len(qualified_workers),
                'total_tasks': total_tasks,
                'avg_tasks_per_worker': round(avg_tasks_per_qualified, 2),
                'utilization_rate': round((len(qualified_workers) / len(workers)) * 100, 1)
            })
        
        # 2. Workload distribution analysis
        workload_distribution = []
        for worker in workers:
            total_tasks = all_x_tasks.get(worker.id, 0) + all_y_tasks.get(worker.id, 0)
            x_percentage = (all_x_tasks.get(worker.id, 0) / total_tasks * 100) if total_tasks > 0 else 0
            y_percentage = (all_y_tasks.get(worker.id, 0) / total_tasks * 100) if total_tasks > 0 else 0
            
            workload_distribution.append({
                'name': worker.name,
                'total_tasks': total_tasks,
                'x_tasks': all_x_tasks.get(worker.id, 0),
                'y_tasks': all_y_tasks.get(worker.id, 0),
                'x_percentage': round(x_percentage, 1),
                'y_percentage': round(y_percentage, 1),
                'balance_score': abs(x_percentage - y_percentage)  # Lower is better
            })
        
        # 3. Seniority vs task distribution
        seniority_analysis = []
        seniority_groups = {}
        for worker in workers:
            seniority = worker.seniority if worker.seniority and worker.seniority != 'None' else 'Unknown'
            if seniority not in seniority_groups:
                seniority_groups[seniority] = {'workers': [], 'total_tasks': 0, 'avg_score': 0}
            
            total_tasks = all_x_tasks.get(worker.id, 0) + all_y_tasks.get(worker.id, 0)
            seniority_groups[seniority]['workers'].append(worker.name)
            seniority_groups[seniority]['total_tasks'] += total_tasks
        
        for seniority, data in seniority_groups.items():
            avg_tasks = data['total_tasks'] / len(data['workers']) if data['workers'] else 0
            seniority_analysis.append({
                'seniority': seniority,
                'worker_count': len(data['workers']),
                'total_tasks': data['total_tasks'],
                'avg_tasks_per_worker': round(avg_tasks, 2)
            })
        
        # 4. Task type distribution over time
        task_timeline_analysis = []
        for period in y_tasks_timeline:
            task_timeline_analysis.append({
                'period': period['period'],
                'total_tasks': period['total_tasks']
            })
        
        return jsonify({
            'x_tasks_pie': x_tasks_pie,
            'y_tasks_pie': y_tasks_pie,
            'combined_pie': combined_pie,
            'x_tasks_timeline': x_tasks_timeline,
            'fairness_metrics': fairness_metrics,
            'summary': {
                'total_workers': len(workers),
                'total_x_tasks': total_x,
                'total_y_tasks': total_y,
                'total_combined': total_combined,
                'data_source': 'worker_data.json',
                'note': 'All statistics derived from worker data JSON file only'
            },
            # ENHANCED: New comprehensive statistics
            'y_task_bar_chart': y_task_bar_data,
            'score_vs_y_tasks': score_vs_y_tasks,
            'closing_accuracy': closing_accuracy_data,
            'qualification_analysis': qualification_analysis,
            'workload_distribution': workload_distribution,
            'seniority_analysis': seniority_analysis,
            'task_timeline_analysis': task_timeline_analysis,
            'average_y_tasks': round(sum(w['y_tasks'] for w in y_task_workers) / len(y_task_workers), 2) if y_task_workers else 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# Legacy-compatible Y tasks index for frontend
# Frontend expects /data/y_tasks.json to be a mapping: { "start_to_end": "filename.csv" }
@app.route('/data/y_tasks.json')
def serve_y_tasks_index_legacy():
    index_path = os.path.join(DATA_DIR, 'y_tasks_index.json')
    if not os.path.exists(index_path):
        return jsonify({})
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            raw_index = json.load(f)
        # Convert to { period_key: filename }
        simplified = {}
        for key, meta in raw_index.items():
            filename = meta.get('filename') if isinstance(meta, dict) else None
            if filename:
                simplified[key] = filename
        return jsonify(simplified)
    except Exception as e:
        # Fail open with empty mapping
        return jsonify({})

# Cache functionality has been removed - all data is loaded directly from files

def cleanup_y_task_index():
    """Clean up orphaned Y task index entries (entries that reference non-existent files)"""
    try:
        index_path = os.path.join(DATA_DIR, 'y_tasks_index.json')
        if not os.path.exists(index_path):
            return
        
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        # Check each entry and remove if file doesn't exist
        cleaned_index = {}
        for period_key, data in index.items():
            filename = data.get('filename')
            if filename:
                filepath = os.path.join(DATA_DIR, filename)
                if os.path.exists(filepath):
                    cleaned_index[period_key] = data
                else:
                    print(f"🧹 Cleaning up orphaned index entry: {period_key} -> {filename}")
        
        # Save cleaned index
        if len(cleaned_index) != len(index):
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_index, f, indent=2, ensure_ascii=False)
            print(f"✅ Cleaned Y task index: removed {len(index) - len(cleaned_index)} orphaned entries")
            
    except Exception as e:
        print(f"Error cleaning up Y task index: {e}")

# --- Y Task API ---

if __name__ == '__main__':
    app.run(debug=True, port=5001) 