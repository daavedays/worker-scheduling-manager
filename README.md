# Worker Scheduling Manager

A full-stack application for managing worker schedules, tasks, and qualifications. Built with React (frontend) and Flask (backend).

## Features
- Manage workers (add, edit, remove, qualifications)
- X/Y task scheduling
- Modern UI with search/autocomplete
- Data stored as worker instances (not just JSON)

## Copyright & License

**Copyright © 2024 David Mirzoyan. All rights reserved.**

This project and all its code, design, and documentation are the sole property of David Mirzoyan. No part of this project may be copied, distributed, or used without explicit written permission from the owner.

This project is proprietary and not open source unless otherwise specified.

## Author
David Mirzoyan

---

For questions or licensing inquiries, contact: [your-email@example.com]

## Project Structure

```
worker-scheduling-manager/
│
├── backend/                # All backend (Flask) code
│   ├── app.py              # Flask app entry point
│   ├── x_tasks.py          # X task logic (imported by app.py)
│   ├── y_tasks.py          # Y task logic (imported by app.py)
│   ├── utils.py            # Shared backend helpers
│   └── __init__.py         # Package marker
│
├── data/                   # All data files (DO NOT DELETE)
│   ├── x_task.csv
│   ├── y_task.csv
│   ├── combined_schedule.csv
│   ├── soldier_data.json
│   ├── soldier_state.json
│   └── text.txt
│
├── frontend/               # All React frontend code
│   ├── src/
│   ├── public/
│   └── ...
│
├── venv/ or .venv/         # Python virtual environment (not tracked)
├── package.json            # Frontend dependencies
├── README.md               # This file
└── ...
```

---

## Setup

### 1. Backend (Flask)
- Requires Python 3.8+
- Install dependencies:
  ```sh
  python -m venv venv
  source venv/bin/activate
  pip install flask flask-cors
  ```
- Run the backend:
  ```sh
  python backend/app.py
  ```
  The backend will be available at `http://localhost:5000`.

### 2. Frontend (React)
- Requires Node.js 16+
- Install dependencies:
  ```sh
  cd frontend
  npm install
  ```
- Run the frontend:
  ```sh
  npm start
  ```
  The frontend will be available at `http://localhost:3000`.

---

## Generating Schedules

- All schedule data is stored in the `data/` directory.
- X and Y task logic is in `backend/x_tasks.py` and `backend/y_tasks.py`.
- You can generate or modify schedules by running scripts in the backend directory, or via the web UI.
- The backend exposes API endpoints for schedule management (see `backend/app.py`).

---

## Notes
- Do **not** delete or move files in the `data/` directory.
- All code is organized for clarity and extensibility.
- For any issues, check the README or code comments for guidance. 