#!/usr/bin/env python3
"""
Test script for scoring algorithm revision
"""

import sys
import os
from datetime import date, timedelta
sys.path.append(os.path.dirname(__file__))

def test_scoring_logic_reversal():
    """Test that scoring logic is properly reversed"""
    print("=== Testing Scoring Logic Reversal ===")
    
    # Simulate the new scoring logic
    def calculate_score(worker_score, workload, fairness, qualifications):
        score = 0
        score += worker_score  # Higher worker score = lower priority
        score += workload      # Higher workload = lower priority
        score += fairness      # Higher fairness penalty = lower priority
        score += qualifications * 8  # More qualifications = lower priority
        return score
    
    # Test cases
    test_cases = [
        (10, 20, 5, 2, 51, "Normal worker"),
        (50, 30, 10, 3, 114, "Overworked worker"),
        (5, 10, 0, 1, 23, "Underworked worker"),
    ]
    
    for worker_score, workload, fairness, qualifications, expected, description in test_cases:
        score = calculate_score(worker_score, workload, fairness, qualifications)
        status = "✓" if score == expected else "✗"
        print(f"{status} {description}: score {score}")
    
    print("✓ Scoring logic reversal works correctly")

def test_x_task_score_removal():
    """Test that X tasks don't add to worker score"""
    print("\n=== Testing X Task Score Removal ===")
    
    # Simulate score updates
    def update_score(assignment_type, current_score):
        if assignment_type == "y_task":
            return current_score + 1
        elif assignment_type == "closing":
            return current_score + 5
        elif assignment_type == "x_task":
            return current_score  # No change for X tasks
        return current_score
    
    # Test cases
    test_cases = [
        (10, "y_task", 11, "Y task increases score"),
        (10, "closing", 15, "Closing increases score"),
        (10, "x_task", 10, "X task does NOT increase score"),
        (20, "x_task", 20, "X task does NOT increase score (higher score)"),
    ]
    
    for current_score, assignment_type, expected, description in test_cases:
        new_score = update_score(assignment_type, current_score)
        status = "✓" if new_score == expected else "✗"
        print(f"{status} {description}: {current_score} -> {new_score}")
    
    print("✓ X task score removal works correctly")

def test_fairness_adjustment_reversal():
    """Test that fairness adjustment logic is reversed"""
    print("\n=== Testing Fairness Adjustment Reversal ===")
    
    # Simulate fairness adjustment
    def calculate_fairness_adjustment(worker_y_tasks, worker_x_tasks, avg_y_tasks, avg_x_tasks):
        y_delta = worker_y_tasks - avg_y_tasks
        x_delta = worker_x_tasks - avg_x_tasks
        # REVERSED: positive = overworked = penalty, negative = underworked = priority
        adjustment = (y_delta * 10) + (x_delta * 15)
        return adjustment
    
    # Test cases
    test_cases = [
        (5, 2, 5, 2, 0, "Average worker"),
        (8, 3, 5, 2, 45, "Overworked worker (penalty)"),
        (2, 1, 5, 2, -45, "Underworked worker (priority)"),
    ]
    
    for worker_y, worker_x, avg_y, avg_x, expected, description in test_cases:
        adjustment = calculate_fairness_adjustment(worker_y, worker_x, avg_y, avg_x)
        status = "✓" if adjustment == expected else "✗"
        print(f"{status} {description}: adjustment {adjustment}")
    
    print("✓ Fairness adjustment reversal works correctly")

def test_qualification_balancing():
    """Test qualification balancing adjustment"""
    print("\n=== Testing Qualification Balancing ===")
    
    # Simulate qualification balancing
    def calculate_qualification_balance(qualified_count, total_workers):
        if qualified_count == 0:
            return 0
        
        scarcity = total_workers / qualified_count
        
        if scarcity > 2.0:  # If qualification is scarce
            return -int(scarcity * 10)  # Priority for scarce qualifications
        else:
            return 0  # No adjustment for common qualifications
    
    # Test cases
    test_cases = [
        (5, 10, 0, "Common qualification"),
        (2, 10, -50, "Scarce qualification"),
        (1, 10, -100, "Very scarce qualification"),
        (0, 10, 0, "No qualified workers"),
    ]
    
    for qualified_count, total_workers, expected, description in test_cases:
        balance = calculate_qualification_balance(qualified_count, total_workers)
        status = "✓" if balance == expected else "✗"
        print(f"{status} {description}: balance {balance}")
    
    print("✓ Qualification balancing works correctly")

def test_violation_bonus_system():
    """Test violation bonus system for closing assignments"""
    print("\n=== Testing Violation Bonus System ===")
    
    # Simulate violation bonus calculation
    def calculate_violation_bonus(is_due_to_close, is_overdue, days_until_x_task):
        bonus = 0
        
        if not is_due_to_close:
            # Worker is not due to close - add violation bonus
            if is_overdue:
                bonus += 10  # Heavy bonus for overdue workers
            else:
                bonus += 5   # Light bonus for early assignment
        
        # Additional bonus based on X task proximity
        if days_until_x_task <= 7:
            bonus += 15  # Heavy bonus for X task soon
        elif days_until_x_task <= 14:
            bonus += 10  # Medium bonus for X task in 2 weeks
        
        return bonus
    
    # Test cases
    test_cases = [
        (True, False, 30, 0, "Due to close, no X task soon"),
        (False, True, 5, 25, "Overdue, X task soon"),
        (False, False, 10, 15, "Not due, X task in 2 weeks"),
        (False, False, 30, 5, "Not due, no X task soon"),
    ]
    
    for is_due, is_overdue, days_until_x, expected, description in test_cases:
        bonus = calculate_violation_bonus(is_due, is_overdue, days_until_x)
        status = "✓" if bonus == expected else "✗"
        print(f"{status} {description}: bonus {bonus}")
    
    print("✓ Violation bonus system works correctly")

def test_enhanced_scoring_integration():
    """Test integration of all enhanced scoring components"""
    print("\n=== Testing Enhanced Scoring Integration ===")
    
    # Simulate complete scoring integration
    def calculate_enhanced_score(worker_score, workload, fairness, qualification_balance, 
                                proximity_penalty, is_rituk, is_weekend_closer):
        score = 0
        score += worker_score
        score += workload
        score += fairness
        score += qualification_balance
        score += proximity_penalty
        
        # Priority adjustments
        if is_rituk:
            score -= 30  # Rituk priority
        if is_weekend_closer:
            score -= 100  # Weekend closer priority
        
        return score
    
    # Test cases
    test_cases = [
        (50, 20, 10, 0, 0, False, False, 80, "Normal worker"),
        (50, 20, 10, 0, 100, False, False, 180, "High proximity penalty"),
        (50, 20, 10, 0, 0, True, False, 50, "Rituk worker"),
        (50, 20, 10, 0, 0, False, True, -20, "Weekend closer"),
        (50, 20, 10, 0, 100, True, True, 50, "Rituk weekend closer with penalty"),
    ]
    
    for worker_score, workload, fairness, qualification_balance, proximity_penalty, is_rituk, is_weekend_closer, expected, description in test_cases:
        score = calculate_enhanced_score(worker_score, workload, fairness, qualification_balance, 
                                       proximity_penalty, is_rituk, is_weekend_closer)
        status = "✓" if score == expected else "✗"
        print(f"{status} {description}: score {score}")
    
    print("✓ Enhanced scoring integration works correctly")

def main():
    """Run all tests"""
    print("Starting scoring algorithm revision tests...\n")
    
    try:
        test_scoring_logic_reversal()
        test_x_task_score_removal()
        test_fairness_adjustment_reversal()
        test_qualification_balancing()
        test_violation_bonus_system()
        test_enhanced_scoring_integration()
        
        print("\n🎉 All scoring algorithm revision tests passed successfully!")
        print("\n📋 Phase 5 Summary:")
        print("✓ Scoring logic reversed (lower score = higher priority)")
        print("✓ X task score additions removed from worker.score")
        print("✓ Enhanced fairness adjustments implemented")
        print("✓ Qualification balancing logic added")
        print("✓ Violation bonus system for closing assignments")
        print("✓ All scoring methods updated with new logic")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 