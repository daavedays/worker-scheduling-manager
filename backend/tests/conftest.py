import os
import shutil
import json
import pytest

# Ensure backend is importable
import backend.app as app_module


@pytest.fixture()
def temp_data_dir(tmp_path):
    """Create a temporary copy of the data directory for isolated tests."""
    src = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    src = os.path.abspath(src)
    dest = tmp_path / 'data'
    dest.mkdir(parents=True, exist_ok=True)
    # Copy selected files used by the app
    for name in [
        'soldier_data.json',
        'x_task.csv',
        'x_task_meta.json',
        'custom_x_tasks.json',
    ]:
        src_path = os.path.join(src, name)
        if os.path.exists(src_path):
            shutil.copy(src_path, dest / name)
    # Ensure files that the app writes exist where safe (avoid creating empty CSVs)
    for name, initial in [
        ('soldier_state.json', '{}'),
        ('history.json', '[]')
    ]:
        p = dest / name
        if not p.exists():
            p.write_text(initial, encoding='utf-8')
    return str(dest)


@pytest.fixture()
def app(temp_data_dir):
    """Provide the Flask app configured to use the temp data dir."""
    # Patch paths used by the app
    app_module.DATA_DIR = temp_data_dir
    app_module.HISTORY_PATH = os.path.join(temp_data_dir, 'history.json')
    flask_app = app_module.app
    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def login(client):
    def _login(username='bossy_bobby', password='QWE123..'):
        return client.post('/api/login', json={'username': username, 'password': password})
    return _login