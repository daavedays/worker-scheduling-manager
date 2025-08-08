import os
import csv
import json
from datetime import datetime, timedelta

import pytest

from backend import y_tasks as y


def test_auth_flow(client, login):
    # Unauthenticated access should be blocked
    r = client.get('/api/session')
    assert r.status_code == 200
    assert r.get_json()['logged_in'] is False

    r = client.get('/api/x-tasks')
    assert r.status_code == 401

    # Login
    r = login()
    assert r.status_code == 200
    assert r.get_json()['success'] is True

    # Session should be active
    r = client.get('/api/session')
    js = r.get_json()
    assert js['logged_in'] is True
    assert js['user'] == 'bossy_bobby'

    # Logout
    r = client.post('/api/logout')
    assert r.status_code == 200
    assert r.get_json()['success'] is True


def test_get_x_tasks_and_save_validation(client, login):
    login()
    r = client.get('/api/x-tasks')
    assert r.status_code == 200
    data = r.get_json()
    assert 'csv' in data and 'custom_tasks' in data and 'year' in data and 'half' in data
    assert isinstance(data['csv'], str)

    # Missing required fields
    r = client.post('/api/x-tasks', json={})
    assert r.status_code == 400


def test_get_y_tasks_blank_grid(client, login, app, temp_data_dir):
    login()
    # Ensure y_task.csv is empty so endpoint builds a blank grid
    y_path = os.path.join(temp_data_dir, 'y_task.csv')
    open(y_path, 'w', encoding='utf-8').close()
    r = client.get('/api/y-tasks')
    assert r.status_code == 200
    assert r.headers['Content-Type'].startswith('text/csv')
    text = r.get_data(as_text=True)
    assert 'Y Task' in text


def test_y_tasks_generate_auto_and_grid_written(client, login, temp_data_dir):
    login()
    # Build a short valid date list from X schedule
    allowed_dates = y.get_all_dates_from_x(os.path.join(temp_data_dir, 'x_task.csv'))
    assert len(allowed_dates) >= 5
    dates = allowed_dates[:5]

    r = client.post('/api/y-tasks/generate', json={'mode': 'auto', 'dates': dates})
    assert r.status_code == 200
    js = r.get_json()
    assert js['y_tasks'] == ["Supervisor", "C&N Driver", "C&N Escort", "Southern Driver", "Southern Escort"]
    assert js['dates'] == dates
    assert len(js['grid']) == 5
    assert all(len(row) == len(dates) for row in js['grid'])

    # The generator writes y_task.csv; ensure it exists and has expected header
    y_csv_path = os.path.join(temp_data_dir, 'y_task.csv')
    assert os.path.exists(y_csv_path)
    with open(y_csv_path, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split(',')
    assert header[0] == 'Name'
    assert header[1:] == dates


def test_available_soldiers_endpoint(client, login, temp_data_dir):
    login()
    some_date = y.get_all_dates_from_x(os.path.join(temp_data_dir, 'x_task.csv'))[0]
    r = client.post('/api/y-tasks/available-soldiers', json={
        'date': some_date,
        'task': 'Supervisor',
        'current_assignments': {}
    })
    assert r.status_code == 200
    js = r.get_json()
    assert isinstance(js['available'], list)


def test_warnings_endpoint(client, login):
    login()
    r = client.get('/api/warnings')
    assert r.status_code == 200
    js = r.get_json()
    assert 'warnings' in js
    assert isinstance(js['warnings'], list)


def test_combined_grid_endpoint(client, login, temp_data_dir):
    login()
    # Ensure a Y CSV exists by generating for a few dates
    from backend import y_tasks as y
    allowed_dates = y.get_all_dates_from_x(os.path.join(temp_data_dir, 'x_task.csv'))
    dates = allowed_dates[:5]
    rr = client.post('/api/y-tasks/generate', json={'mode': 'auto', 'dates': dates})
    assert rr.status_code == 200

    r = client.get('/api/combined/grid')
    assert r.status_code == 200
    js = r.get_json()
    assert {'row_labels', 'dates', 'grid'}.issubset(js.keys())
    assert isinstance(js['dates'], list)
    assert isinstance(js['grid'], list)


def test_conflicts_endpoint(client, login):
    login()
    r = client.get('/api/x-tasks/conflicts')
    assert r.status_code == 200
    js = r.get_json()
    assert 'conflicts' in js


def test_tally_post_and_get(client, login, temp_data_dir):
    login()
    payload = {'alpha': 1, 'bravo': 2}
    r = client.post('/api/tally', data=json.dumps(payload))
    assert r.status_code == 200
    r = client.get('/api/tally')
    assert r.status_code == 200
    returned = json.loads(r.get_data(as_text=True))
    assert returned == payload


def test_reset_and_history(client, login):
    login()
    r = client.post('/api/reset')
    assert r.status_code == 200
    r = client.get('/api/history')
    assert r.status_code == 200
    history = r.get_json()['history']
    assert any(h['event'] == 'Reset schedules' for h in history)