# SchedulingEngineV2 - Complete Workflow Implementation

## Overview

The `SchedulingEngineV2` class implements a comprehensive worker assignment engine that handles both weekday Y-tasks and weekend closing assignments with scarcity-aware prioritization and fairness principles.

## Key Features

### 1. Scarcity-Aware Assignment
- **Task Prioritization**: Y-tasks are prioritized by scarcity (fewer qualified workers = higher priority)
- **Worker Protection**: Scarce workers (those with rare qualifications) are protected from overuse
- **Scarcity Index**: Each worker has a scarcity index based on their qualifications

### 2. Complete Workflow Support
- **Weekday-Only Scheduling**: Assigns Y-tasks evenly across weekdays (Sun-Wed)
- **Weekend Scheduling**: Assigns closers and Y-tasks for weekends (Thu-Sat)
- **Mixed Scheduling**: Handles date ranges with both weekdays and weekends
- **Required Closing**: Handles workers with required closing dates due to X tasks (e.g., "Rituk")

### 3. Fairness and Error Handling
- **Assignment Errors**: Tracks and reports assignment errors and warnings
- **Manual Override Support**: Provides detailed error information for manual correction
- **Fairness Updates**: Updates worker scores after assignments for fairness tracking

## Core Methods

### `schedule_range(workers, start, end, num_closers_per_weekend, weekday_tasks=None)`

Main orchestration method that implements the complete workflow:

1. **Precompute**: Updates all worker schedules and computes scarcity data
2. **Weekend Processing**: If weekends included, assigns closers first, then Y-tasks
3. **Weekday Processing**: Assigns weekday Y-tasks with scarcity prioritization
4. **Error Reporting**: Provides detailed error and warning information
5. **Fairness Update**: Updates worker scores for fairness tracking

### `assign_weekend_closers(workers, thursday, num_slots, semester_weeks)`

Assigns weekend closers with the following logic:

1. **Required Closers**: Workers with required closing dates due to X tasks
2. **Optimal Closers**: Workers due to close based on their intervals
3. **Consecutive Avoidance**: Prevents consecutive closing assignments
4. **Score-based Selection**: Uses worker scores for tie-breaking

### `assign_weekend_y_tasks(workers, thursday, picked_closers)`

Assigns weekend Y-tasks (Thu-Sat) with scarcity-aware prioritization:

1. **Closer Assignment**: Gives closers the scarcest tasks first
2. **Stage-based Assignment**: Uses three stages for remaining tasks:
   - Stage A: Eligible workers with optimal closing on weekend
   - Stage B: Eligible workers (no optimal closing requirement)
   - Stage C: Any remaining qualified workers

### `assign_weekday_y_tasks(workers, tasks_by_date)`

Assigns weekday Y-tasks with scarcity prioritization:

1. **Task Prioritization**: Orders tasks by scarcity (fewer qualified = higher priority)
2. **Worker Selection**: Uses score and scarcity index for worker selection
3. **Fairness Tracking**: Updates worker scores and task counts

## Data Structures

### `AssignmentDecision`
```python
@dataclass
class AssignmentDecision:
    worker_id: str
    worker_name: str
    reason: str
    debug: Dict[str, float]
```

### `AssignmentError`
```python
@dataclass
class AssignmentError:
    task_type: str
    date: date
    reason: str
    severity: str  # 'warning' or 'error'
```

## Workflow Logic

### Weekday-Only Scheduling
1. Check if date range includes weekends
2. If no weekends: assign weekday Y-tasks evenly
3. Ensure all dates are filled
4. Verify fairness by scores and even distribution
5. Report any unassigned tasks as errors

### Weekend Scheduling
1. Start with weekend closers:
   - Assign workers with required closing due to X tasks ("Rituk")
   - Assign them both closing duty and scarce-qualification Y-tasks
   - Remove those Y-tasks from the unassigned pool
2. For remaining Y-tasks:
   - Build eligible workers list (no recent close, no next required close, not already assigned)
   - For each Y-task:
     - Map qualified workers using scarcity principle
     - Pick lowest score candidate among qualified workers with optimal closing dates
     - If no optimal candidates, retry with all eligible workers
     - If still unassigned, pick from all remaining workers
3. Report warnings for any unassigned tasks

### Error Handling
- **Assignment Errors**: Tasks that could not be assigned automatically
- **Assignment Warnings**: Issues detected during assignment process
- **Manual Override Support**: Detailed error information for manual correction

## Usage Examples

### Basic Weekday Scheduling
```python
engine = SchedulingEngineV2()
workers = load_workers_from_json("worker_data.json")

weekday_tasks = {
    date(2025, 1, 6): ["Supervisor", "C&N Driver"],
    date(2025, 1, 7): ["C&N Escort", "Southern Driver"],
}

result = engine.schedule_range(
    workers=workers,
    start=date(2025, 1, 6),
    end=date(2025, 1, 8),
    num_closers_per_weekend=2,
    weekday_tasks=weekday_tasks
)

print(f"Success: {result['success']}")
print(f"Errors: {len(result['assignment_errors'])}")
```

### Weekend Scheduling
```python
result = engine.schedule_range(
    workers=workers,
    start=date(2025, 1, 2),  # Thursday
    end=date(2025, 1, 4),    # Saturday
    num_closers_per_weekend=2,
    weekday_tasks=None
)

print("Closers:")
for date_str, closer_ids in result['closers'].items():
    print(f"  {date_str}: {closer_ids}")

print("Y-tasks:")
for date_str, assignments in result['y_tasks'].items():
    print(f"  {date_str}: {assignments}")
```

## Integration

The engine integrates with:

- **EnhancedWorker**: Worker class with qualifications, scores, and closing schedules
- **ClosingScheduleCalculator**: Pre-computes required and optimal closing dates
- **Scoring System**: Updates worker scores for fairness tracking
- **Assignment Tracking**: Maintains Y-task counts and closing history

## Error Recovery

When automatic assignment fails:

1. **Error Analysis**: Review `assignment_errors` for specific issues
2. **Manual Correction**: Use error details to manually assign tasks
3. **Rescoring**: Re-run fairness updates after manual corrections
4. **Validation**: Verify all assignments meet requirements

## Performance

- **Efficient Precomputation**: Computes scarcity data once per scheduling session
- **Stage-based Assignment**: Reduces assignment complexity with staged approach
- **Error Tracking**: Minimal overhead for comprehensive error reporting
- **Scalable**: Handles large worker pools and date ranges efficiently
