#!/usr/bin/env python3
"""
Date Range Parser for Y Task Assignment
Handles any combination of weekdays and weekends within a date range
"""

from datetime import date, timedelta
from typing import List, Tuple, Dict

class DateRangeParser:
    """
    Parses date ranges and separates weekdays from weekends
    """
    
    def __init__(self):
        # Weekday: Sunday (6) to Wednesday (2)
        # Weekend: Thursday (3) to Saturday (5)
        self.weekday_days = [6, 0, 1, 2]  # Sun, Mon, Tue, Wed
        self.weekend_days = [3, 4, 5]     # Thu, Fri, Sat
    
    def parse_date_range(self, start_date: date, end_date: date) -> Dict:
        """
        Parse a date range and separate weekdays from weekends
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            Dictionary with separated date ranges:
            {
                'weekdays': [(start, end), ...],
                'weekends': [(start, end), ...],
                'analysis': {...}
            }
        """
        weekday_ranges = []
        weekend_ranges = []
        
        current_date = start_date
        current_weekday_start = None
        current_weekend_start = None
        
        while current_date <= end_date:
            weekday = current_date.weekday()
            
            # Check if it's a weekday
            if weekday in self.weekday_days:
                # If we were in a weekend range, close it
                if current_weekend_start is not None:
                    weekend_ranges.append((current_weekend_start, current_date - timedelta(days=1)))
                    current_weekend_start = None
                
                # Start or continue weekday range
                if current_weekday_start is None:
                    current_weekday_start = current_date
                    
            # Check if it's a weekend day
            elif weekday in self.weekend_days:
                # If we were in a weekday range, close it
                if current_weekday_start is not None:
                    weekday_ranges.append((current_weekday_start, current_date - timedelta(days=1)))
                    current_weekday_start = None
                
                # Start or continue weekend range
                if current_weekend_start is None:
                    current_weekend_start = current_date
            
            current_date += timedelta(days=1)
        
        # Close any open ranges
        if current_weekday_start is not None:
            weekday_ranges.append((current_weekday_start, end_date))
        if current_weekend_start is not None:
            weekend_ranges.append((current_weekend_start, end_date))
        
        # Analyze the ranges
        analysis = self._analyze_ranges(start_date, end_date, weekday_ranges, weekend_ranges)
        
        return {
            'weekdays': weekday_ranges,
            'weekends': weekend_ranges,
            'analysis': analysis
        }
    
    def _analyze_ranges(self, start_date: date, end_date: date, 
                       weekday_ranges: List[Tuple[date, date]], 
                       weekend_ranges: List[Tuple[date, date]]) -> Dict:
        """
        Analyze the parsed date ranges
        """
        total_days = (end_date - start_date).days + 1
        
        weekday_days = sum((end - start).days + 1 for start, end in weekday_ranges)
        weekend_days = sum((end - start).days + 1 for start, end in weekend_ranges)
        
        return {
            'total_days': total_days,
            'weekday_days': weekday_days,
            'weekend_days': weekend_days,
            'weekday_ranges_count': len(weekday_ranges),
            'weekend_ranges_count': len(weekend_ranges),
            'weekday_percentage': (weekday_days / total_days) * 100 if total_days > 0 else 0,
            'weekend_percentage': (weekend_days / total_days) * 100 if total_days > 0 else 0
        }
    
    def get_weekend_weeks(self, start_date: date, end_date: date) -> List[int]:
        """
        Get list of week numbers that contain weekends in the date range
        
        Args:
            start_date: Start date for assignment period
            end_date: End date for assignment period
            
        Returns:
            List of week numbers (0-based from start_date)
        """
        weekend_weeks = set()
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() in self.weekend_days:
                # Calculate week number from start_date
                week_start = current_date - timedelta(days=current_date.weekday())
                week_number = (week_start - start_date).days // 7
                weekend_weeks.add(week_number)
            
            current_date += timedelta(days=1)
        
        return sorted(list(weekend_weeks))
    
    def validate_date_range(self, start_date: date, end_date: date) -> Tuple[bool, str]:
        """
        Validate a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            (is_valid, error_message)
        """
        if start_date > end_date:
            return False, "Start date cannot be after end date"
        
        if (end_date - start_date).days > 365:
            return False, "Date range cannot exceed 1 year"
        
        return True, ""
    
    def print_analysis(self, start_date: date, end_date: date):
        """
        Print a detailed analysis of the date range
        """
        print(f"📅 Date Range Analysis: {start_date} to {end_date}")
        print("=" * 50)
        
        parsed = self.parse_date_range(start_date, end_date)
        analysis = parsed['analysis']
        
        print(f"📊 Total Days: {analysis['total_days']}")
        print(f"📊 Weekday Days: {analysis['weekday_days']} ({analysis['weekday_percentage']:.1f}%)")
        print(f"📊 Weekend Days: {analysis['weekend_days']} ({analysis['weekend_percentage']:.1f}%)")
        print()
        
        print("📅 Weekday Ranges:")
        for i, (start, end) in enumerate(parsed['weekdays'], 1):
            days = (end - start).days + 1
            print(f"   {i}. {start} to {end} ({days} days)")
        
        print("\n📅 Weekend Ranges:")
        for i, (start, end) in enumerate(parsed['weekends'], 1):
            days = (end - start).days + 1
            print(f"   {i}. {start} to {end} ({days} days)")
        
        print(f"\n🎯 Weekend Weeks: {self.get_weekend_weeks(start_date, end_date)}") 