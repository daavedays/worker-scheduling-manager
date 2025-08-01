#!/usr/bin/env python3
"""
Reset all worker seniority and scores to balanced values
"""

import json
import random
from datetime import datetime
from worker import reset_x_tasks_data

def reset_worker_scores():
    """Reset all worker seniority and scores to balanced values"""

    print("=== RESETTING WORKER SCORES AND SENIORITY ===\n")

    # Load current worker data
    with open('../data/worker_data.json', 'r', encoding='utf-8') as f:
        workers = json.load(f)

    print(f"Loaded {len(workers)} workers")

    # Reset scores and seniority for all workers
    for i, worker in enumerate(workers):
        # Reset score to a random value between 0-20 (much lower than current values)
        # worker['score'] = random.randint(0, 20)
        worker['score'] = 0

        # Reset seniority to a random value between 1-10 (more balanced range)
        # worker['seniority'] = random.randint(1, 10)
        worker['seniority'] = 0

        # Reset closing history
        worker['closing_history'] = {}

        worker['x_tasks'] = {}

        print(f"Worker {worker['id']} ({worker['name']}): Score={worker['score']}, Seniority={worker['seniority']}")

    # Save updated worker data
    with open('../data/worker_data.json', 'w', encoding='utf-8') as f:
        json.dump(workers, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Reset {len(workers)} workers:")
    print(f"  - Scores: 0-20 (was 0-100)")
    print(f"  - Seniority: 1-10 (was 1-19)")
    print(f"  - File saved: data/worker_data.json")

# Note to reset x tasks data, import worker.reset_x_tasks_data
if __name__ == "__main__":
    reset_worker_scores()



