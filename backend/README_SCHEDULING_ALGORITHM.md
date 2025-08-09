# Enhanced Scheduling Algorithm

## Overview

The scheduling algorithm has been enhanced to provide fair and balanced Y-task distribution while respecting various constraints. The algorithm now includes:

1. **Strict Weekly Limit** (with fallback): Normally limits workers to 1 Y-task per week, but allows exceptions when necessary
2. **Task Type Variety**: Prevents assigning the same task type to the same worker repeatedly
3. **Weekend Closer Exclusion**: Workers assigned as weekend closers are excluded from weekday Y-tasks
4. **Score-Based Fair Distribution**: Uses worker scores to prioritize less overworked workers
5. **X-Task Cooldown**: Prevents Y-task assignments 1 day after X-tasks
6. **Comprehensive Conflict Detection**: Prevents scheduling conflicts

## Algorithm Details

### Weekly Limit with Fallback Logic

The algorithm tries to limit each worker to 1 Y-task per week. However, when there aren't enough qualified workers available, it will use a fallback mechanism:

1. First, it tries to find workers who:
   - Have not reached their weekly limit
   - Are not weekend closers
   - Don't have X-task conflicts
   - Don't have existing Y-tasks on the same day

2. If no workers meet all criteria, it relaxes the weekly limit constraint and:
   - Prioritizes workers with lower scores (less overworked)
   - Still enforces hard constraints (no same-day conflicts)

This ensures tasks are always assigned, even in scenarios with limited qualified workers.

### Task Type Variety

The algorithm prevents assigning the same task type to the same worker repeatedly. By default, each worker can only be assigned a specific task type (e.g., "Supervisor") once per scheduling period. This ensures:

1. **Balanced Skill Development**: Workers get experience with different types of tasks
2. **Reduced Monotony**: Workers don't get stuck doing the same task repeatedly
3. **Fairer Distribution**: Prevents certain workers from being typecast into specific roles

When there aren't enough qualified workers available, the algorithm has a two-stage fallback:

1. First, it tries to relax the weekly limit while still respecting task type limits
2. If still no workers are available, it relaxes both limits, prioritizing workers with lower scores

This ensures task variety while still guaranteeing that all tasks are assigned.

### Weekend Closer Exclusion

Workers who are assigned as weekend closers (Friday-Saturday) are completely excluded from weekday Y-task assignments. This prevents overloading workers who already have weekend responsibilities.

### Score-Based Fair Distribution

The algorithm uses multiple factors to select the fairest candidate:

1. **Worker Score**: Lower-scored workers are prioritized
2. **Task-Specific Count**: Workers with fewer assignments of the specific task type are preferred
3. **Worker Scarcity Index**: Considers how many tasks a worker is qualified for

### X-Task Cooldown

Workers who had an X-task in the last 1 day are not assigned Y-tasks. This provides a cooldown period between different task types.

### Conflict Detection

The algorithm detects and prevents various conflicts:

1. **Same-Day Y-Task Conflicts**: No worker gets multiple Y-tasks on the same day
2. **X-Task Conflicts**: Y-tasks don't conflict with X-tasks
3. **Weekend Closer Conflicts**: Weekend closers don't get weekday Y-tasks

## Usage

The scheduling algorithm is implemented in `SchedulingEngineV2` in `backend/engine.py`. The main method to use is:

```python
engine = SchedulingEngineV2()
result = engine.schedule_range(
    workers=workers,
    start=start_date,
    end=end_date,
    num_closers_per_weekend=2,
    weekday_tasks=weekday_tasks,
    weekly_limit=1,  # Maximum Y-tasks per worker per week
    max_same_task_type=1  # Maximum times a worker can be assigned the same task type
)
```

You can adjust both `weekly_limit` and `max_same_task_type` parameters to control the distribution of tasks.

## Test Results

The algorithm has been thoroughly tested with various scenarios:

1. **Normal Case**: Workers get at most 1 Y-task per week
2. **Task Variety Case**: Workers don't get assigned the same task type repeatedly
3. **Weekend Closer Case**: Weekend closers get no weekday Y-tasks
4. **Limited Workers Case**: When there aren't enough qualified workers, the algorithm uses fallback logic to assign multiple tasks to the same worker, prioritizing those with lower scores

## Maintenance Notes

When modifying the scheduling algorithm, ensure:

1. The fallback logic is preserved to handle cases with limited qualified workers
2. Hard constraints (same-day conflicts) are never relaxed
3. Score-based fairness is maintained
4. Task variety is maintained to prevent repetitive assignments
5. Worker objects are updated with assignments using `worker.assign_y_task(date, task)`
6. Task type counts are properly tracked and updated
