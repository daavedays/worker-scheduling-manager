# Worker Scheduling Manager – Backend API Documentation

This document describes the available API endpoints for the Flask backend. All endpoints require authentication (login) unless otherwise noted.

---

## Authentication

### `POST /api/login`
- **Body:** `{ "username": string, "password": string }`
- **Response:** `{ "success": true, "user": string }` or `{ "error": string }`
- **Notes:** Sets a session cookie.

### `POST /api/logout`
- **Response:** `{ "success": true }`

### `GET /api/session`
- **Response:** `{ "logged_in": bool, "user"?: string }`

---

## X Task Endpoints

### `GET /api/x-tasks`
- **Response:** `{ "csv": string, "custom_tasks": object, "year": int, "half": int }`
- **Notes:** Returns the X task schedule as CSV and custom tasks as JSON.

### `POST /api/x-tasks`
- **Body:** `{ "csv": string, "custom_tasks": object, "year": int, "half": int }`
- **Response:** `{ "success": true }`

---

## Y Task Endpoints

### `GET /api/y-tasks`
- **Response:** CSV file (Y task schedule)

### `POST /api/y-tasks`
- **Body:** CSV file (raw text)
- **Response:** `{ "success": true }`

### `POST /api/y-tasks/generate`
- **Body:**
  - `start`: string ("dd/mm/yyyy")
  - `end`: string ("dd/mm/yyyy")
  - `mode`: "auto" | "hybrid"
  - `partial_grid`, `y_tasks`, `dates` (for hybrid mode)
- **Response:** `{ "y_tasks": [...], "dates": [...], "grid": [...], "warnings": [...], "year": int }` or `{ "error": string }`

### `POST /api/y-tasks/available-soldiers`
- **Body:** `{ "date": string, "task": string, "current_assignments": object }`
- **Response:** `{ "available": [string] }`

---

## Combined Schedule

### `GET /api/combined`
- **Response:** CSV file (combined X/Y schedule)

---

## Warnings

### `GET /api/warnings`
- **Response:** `{ "warnings": [...] }`

---

## Tally (Soldier State)

### `GET /api/tally`
- **Response:** JSON (soldier state)

### `POST /api/tally`
- **Body:** JSON (soldier state)
- **Response:** `{ "success": true }`

---

## Reset/History

### `POST /api/reset`
- **Response:** `{ "success": true }`

### `GET /api/history`
- **Response:** `{ "history": [...] }`

---

## Static/Data Files

### `GET /data/<filename>`
- **Response:** Serves files from the `data/` directory (CSV, JSON, etc.)

---

## Notes
- All endpoints (except `/api/login`) require a valid session cookie.
- CORS is enabled for local development.
- For more details, see the source code in `backend/app.py` and related modules. 