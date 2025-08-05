#!/usr/bin/env python3
"""
Master Scheduler for Y Task Assignment
Handles any combination of weekdays and weekends within a date range
"""

import sys
from datetime import date, timedelta
from typing import List, Tuple, Dict
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from worker import Worker
from schedule_engine.date_range_parser import DateRangeParser
from schedule_engine.assign_weekday import WeekdayScheduler
from schedule_engine.assign_weekend import WeekendScheduler

class MasterScheduler:
    """
    Master scheduler that handles any date range combination
    """
    
    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.date_parser = DateRangeParser()
        self.weekday_scheduler = WeekdayScheduler(workers)
        self.weekend_scheduler = WeekendScheduler(workers)
    
    def assign_y_tasks(self, start_date: date, end_date: date) -> Dict:
        """
        Assign Y tasks for any date range combination
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            Dictionary with assignments and analysis:
            {
                'assignments': [(date, task, worker_name), ...],
                'weekday_assignments': [...],
                'weekend_assignments': [...],
                'date_analysis': {...},
                'weekday_stats': {...},
                'weekend_stats': {...}
            }
        """
        # Validate date range
        is_valid, error_msg = self.date_parser.validate_date_range(start_date, end_date)
        if not is_valid:
            return {"error": error_msg}
        
        # Parse date range into weekdays and weekends
        parsed_ranges = self.date_parser.parse_date_range(start_date, end_date)
        
        # Reset worker assignments for clean start
        for worker in self.workers:
            worker.y_tasks = {}
        
        # Assign weekday tasks
        weekday_assignments = []
        for weekday_start, weekday_end in parsed_ranges['weekdays']:
            assignments = self.weekday_scheduler.assign_y_tasks(weekday_start, weekday_end)
            weekday_assignments.extend(assignments)
        
        # Assign weekend tasks
        weekend_assignments = []
        for weekend_start, weekend_end in parsed_ranges['weekends']:
            assignments = self.weekend_scheduler.assign_y_tasks(weekend_start, weekend_end)
            weekend_assignments.extend(assignments)
        
        # Combine all assignments
        all_assignments = weekday_assignments + weekend_assignments
        
        # Get statistics
        weekday_stats = self.weekday_scheduler.get_distribution_stats()
        weekend_stats = self.weekend_scheduler.get_weekend_stats()
        
        return {
            'assignments': all_assignments,
            'weekday_assignments': weekday_assignments,
            'weekend_assignments': weekend_assignments,
            'date_analysis': parsed_ranges['analysis'],
            'weekday_stats': weekday_stats,
            'weekend_stats': weekend_stats,
            'total_assignments': len(all_assignments),
            'weekday_assignments_count': len(weekday_assignments),
            'weekend_assignments_count': len(weekend_assignments)
        }
    
    def get_comprehensive_stats(self, start_date: date, end_date: date) -> Dict:
        """
        Get comprehensive statistics for the entire date range
        """
        result = self.assign_y_tasks(start_date, end_date)
        
        if 'error' in result:
            return result
        
        # Add comprehensive analysis
        result['comprehensive_analysis'] = {
            'date_range': f"{start_date} to {end_date}",
            'total_days': result['date_analysis']['total_days'],
            'weekday_percentage': result['date_analysis']['weekday_percentage'],
            'weekend_percentage': result['date_analysis']['weekend_percentage'],
            'weekday_fairness': result['weekday_stats'].get('fairness_ratio', 0),
            'weekend_fairness': result['weekend_stats'].get('fairness_ratio', 0),
            'overall_fairness': self._calculate_overall_fairness(),
            'assignment_efficiency': self._calculate_assignment_efficiency(result)
        }
        
        return result
    
    def _calculate_overall_fairness(self) -> float:
        """
        Calculate overall fairness across all workers
        """
        task_counts = [len(worker.y_tasks) for worker in self.workers]
        if not task_counts or min(task_counts) == 0:
            return float('inf')
        
        return max(task_counts) / min(task_counts)
    
    def _calculate_assignment_efficiency(self, result: Dict) -> Dict:
        """
        Calculate assignment efficiency metrics
        """
        total_assignments = result['total_assignments']
        total_days = result['date_analysis']['total_days']
        expected_assignments = total_days * 5  # 5 Y tasks per day
        
        efficiency = (total_assignments / expected_assignments) * 100 if expected_assignments > 0 else 0
        
        return {
            'total_assignments': total_assignments,
            'expected_assignments': expected_assignments,
            'efficiency_percentage': efficiency,
            'unassigned_slots': expected_assignments - total_assignments
        }
    
    def print_detailed_analysis(self, start_date: date, end_date: date):
        """
        Print detailed analysis of the assignment
        """
        print(f"🎯 Master Scheduler Analysis: {start_date} to {end_date}")
        print("=" * 60)
        
        # Print date range analysis
        self.date_parser.print_analysis(start_date, end_date)
        
        # Get comprehensive results
        result = self.get_comprehensive_stats(start_date, end_date)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return
        
        print(f"\n📊 Assignment Summary:")
        print(f"   Total Assignments: {result['total_assignments']}")
        print(f"   Weekday Assignments: {result['weekday_assignments_count']}")
        print(f"   Weekend Assignments: {result['weekend_assignments_count']}")
        
        print(f"\n📈 Fairness Analysis:")
        print(f"   Weekday Fairness Ratio: {result['weekday_stats'].get('fairness_ratio', 0):.2f}")
        print(f"   Weekend Fairness Ratio: {result['weekend_stats'].get('fairness_ratio', 0):.2f}")
        print(f"   Overall Fairness Ratio: {result['comprehensive_analysis']['overall_fairness']:.2f}")
        
        print(f"\n⚡ Efficiency Analysis:")
        efficiency = result['comprehensive_analysis']['assignment_efficiency']
        print(f"   Assignment Efficiency: {efficiency['efficiency_percentage']:.1f}%")
        print(f"   Unassigned Slots: {efficiency['unassigned_slots']}")
        
        print(f"\n🎯 Weekend Weeks: {self.date_parser.get_weekend_weeks(start_date, end_date)}")
        
        # Check for double assignments
        self._check_double_assignments(result['assignments'])
    
    def _check_double_assignments(self, assignments: List[Tuple[date, str, str]]):
        """
        Check for double assignments to same worker on same day
        """
        daily_assignments = {}
        double_assignments = 0
        
        for assignment_date, task, worker_name in assignments:
            if assignment_date not in daily_assignments:
                daily_assignments[assignment_date] = {}
            if worker_name not in daily_assignments[assignment_date]:
                daily_assignments[assignment_date][worker_name] = []
            daily_assignments[assignment_date][worker_name].append(task)
        
        for date_obj, workers_dict in daily_assignments.items():
            for worker_name, tasks in workers_dict.items():
                if len(tasks) > 1:
                    double_assignments += 1
                    print(f"   ❌ {worker_name} has {len(tasks)} Y tasks on {date_obj}: {tasks}")
        
        if double_assignments == 0:
            print(f"   ✅ No double assignments found")
        else:
            print(f"   ❌ Found {double_assignments} double assignments") 