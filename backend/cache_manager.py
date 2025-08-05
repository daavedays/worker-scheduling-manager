#!/usr/bin/env python3
"""
Cache Manager for Worker Scheduling System
Handles caching of X-tasks, Y-tasks, and related calculations for performance optimization
"""

import time
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

class CacheManager:
    """
    Manages caching for X-tasks, Y-tasks, and related calculations.
    Provides fast access to frequently accessed data.
    """
    
    def __init__(self):
        # X-Task caching
        self.x_task_cache: Dict[str, Dict] = {}  # period -> worker_id -> date -> task
        self.x_task_cache_time: Dict[str, float] = {}  # period -> timestamp
        self.x_task_cache_ttl = 300  # 5 minutes
        
        # Y-Task caching
        self.y_task_cache: Dict[str, Dict] = {}  # period -> worker_id -> date -> task
        self.y_task_cache_time: Dict[str, float] = {}
        self.y_task_cache_ttl = 300  # 5 minutes
        
        # Calculation caching
        self.proximity_cache: Dict[str, int] = {}  # worker_date_key -> penalty
        self.proximity_cache_ttl = 60  # 1 minute
        
        self.availability_cache: Dict[str, List] = {}  # date_key -> available_workers
        self.availability_cache_ttl = 30  # 30 seconds
        
        # Conflict detection caching
        self.conflict_cache: Dict[str, List] = {}  # period_key -> conflicts
        self.conflict_cache_ttl = 120  # 2 minutes
        
        # Cache statistics
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _get_cache_key(self, *args) -> str:
        """Generate a cache key from arguments"""
        return "_".join(str(arg) for arg in args)
    
    def _is_cache_valid(self, cache_time: float, ttl: int) -> bool:
        """Check if cache entry is still valid"""
        return (time.time() - cache_time) < ttl
    
    def get_x_task_data(self, period: int, year: int, data_dir: str) -> Dict:
        """
        Get X-task data with caching.
        
        Args:
            period: Period number (1 or 2)
            year: Year
            data_dir: Data directory path
            
        Returns:
            Dictionary of X-task assignments
        """
        cache_key = f"x_tasks_{year}_{period}"
        
        # Check if we have valid cached data
        if (cache_key in self.x_task_cache and 
            cache_key in self.x_task_cache_time and
            self._is_cache_valid(self.x_task_cache_time[cache_key], self.x_task_cache_ttl)):
            
            self.cache_hits += 1
            print(f"✅ X-task cache HIT for period {period}")
            return self.x_task_cache[cache_key]
        
        # Cache miss - load from file
        self.cache_misses += 1
        print(f"❌ X-task cache MISS for period {period}")
        
        x_task_data = self._load_x_tasks_from_file(period, year, data_dir)
        
        # Cache the data
        self.x_task_cache[cache_key] = x_task_data
        self.x_task_cache_time[cache_key] = time.time()
        
        return x_task_data
    
    def _load_x_tasks_from_file(self, period: int, year: int, data_dir: str) -> Dict:
        """Load X-tasks from CSV file"""
        try:
            from . import y_tasks as y_tasks_module
            x_csv = os.path.join(data_dir, f"x_tasks_{year}_{period}.csv")
            
            if os.path.exists(x_csv):
                print(f"Loading X-task file: {x_csv}")
                return y_tasks_module.read_x_tasks(x_csv)
            else:
                print(f"X-task file not found: {x_csv}")
                return {}
        except Exception as e:
            print(f"Error loading X-tasks: {e}")
            return {}
    
    def get_y_task_data(self, period: str, data_dir: str) -> Dict:
        """
        Get Y-task data with caching.
        
        Args:
            period: Period string (e.g., "01-01-2025_to_31-03-2025")
            data_dir: Data directory path
            
        Returns:
            Dictionary of Y-task assignments
        """
        cache_key = f"y_tasks_{period}"
        
        # Check if we have valid cached data
        if (cache_key in self.y_task_cache and 
            cache_key in self.y_task_cache_time and
            self._is_cache_valid(self.y_task_cache_time[cache_key], self.y_task_cache_ttl)):
            
            self.cache_hits += 1
            print(f"✅ Y-task cache HIT for period {period}")
            return self.y_task_cache[cache_key]
        
        # Cache miss - load from file
        self.cache_misses += 1
        print(f"❌ Y-task cache MISS for period {period}")
        
        y_task_data = self._load_y_tasks_from_file(period, data_dir)
        
        # Cache the data
        self.y_task_cache[cache_key] = y_task_data
        self.y_task_cache_time[cache_key] = time.time()
        
        return y_task_data
    
    def _load_y_tasks_from_file(self, period: str, data_dir: str) -> Dict:
        """Load Y-tasks from CSV file"""
        try:
            y_csv = os.path.join(data_dir, f"y_tasks_{period}.csv")
            
            if os.path.exists(y_csv):
                print(f"Loading Y-task file: {y_csv}")
                # Implement Y-task loading logic here
                return {}
            else:
                print(f"Y-task file not found: {y_csv}")
                return {}
        except Exception as e:
            print(f"Error loading Y-tasks: {e}")
            return {}
    
    def get_proximity_penalty(self, worker_id: int, current_date: date, 
                             x_task_data: Dict) -> int:
        """
        Get X-task proximity penalty with caching.
        
        Args:
            worker_id: Worker ID
            current_date: Current date
            x_task_data: X-task data
            
        Returns:
            Penalty score
        """
        cache_key = self._get_cache_key("proximity", worker_id, current_date)
        
        # Check if we have valid cached penalty
        if (cache_key in self.proximity_cache and
            self._is_cache_valid(self.proximity_cache.get(f"{cache_key}_time", 0), 
                               self.proximity_cache_ttl)):
            
            self.cache_hits += 1
            return self.proximity_cache[cache_key]
        
        # Cache miss - calculate penalty
        self.cache_misses += 1
        penalty = self._calculate_proximity_penalty(worker_id, current_date, x_task_data)
        
        # Cache the result
        self.proximity_cache[cache_key] = penalty
        self.proximity_cache[f"{cache_key}_time"] = time.time()
        
        return penalty
    
    def _calculate_proximity_penalty(self, worker_id: int, current_date: date, 
                                   x_task_data: Dict) -> int:
        """Calculate X-task proximity penalty"""
        penalty = 0
        
        if str(worker_id) not in x_task_data:
            return penalty
        
        worker_x_tasks = x_task_data[str(worker_id)]
        
        # Check for X tasks in the last week
        for i in range(1, 8):
            check_date = current_date - timedelta(days=i)
            date_str = check_date.strftime('%d/%m/%Y')
            if date_str in worker_x_tasks:
                penalty += 100  # Heavy penalty for recent X tasks
        
        # Check for upcoming X tasks
        for i in range(1, 15):
            check_date = current_date + timedelta(days=i)
            date_str = check_date.strftime('%d/%m/%Y')
            if date_str in worker_x_tasks:
                penalty += 25  # Light penalty for upcoming X tasks
        
        return penalty
    
    def get_available_workers(self, current_date: date, workers: List, 
                            x_task_data: Dict) -> List:
        """
        Get available workers for a date with caching.
        
        Args:
            current_date: Current date
            workers: List of workers
            x_task_data: X-task data
            
        Returns:
            List of available workers
        """
        cache_key = self._get_cache_key("available", current_date)
        
        # Check if we have valid cached availability
        if (cache_key in self.availability_cache and
            self._is_cache_valid(self.availability_cache.get(f"{cache_key}_time", 0),
                               self.availability_cache_ttl)):
            
            self.cache_hits += 1
            return self.availability_cache[cache_key]
        
        # Cache miss - calculate availability
        self.cache_misses += 1
        available_workers = self._calculate_available_workers(current_date, workers, x_task_data)
        
        # Cache the result
        self.availability_cache[cache_key] = available_workers
        self.availability_cache[f"{cache_key}_time"] = time.time()
        
        return available_workers
    
    def _calculate_available_workers(self, current_date: date, workers: List, 
                                   x_task_data: Dict) -> List:
        """Calculate available workers for a date"""
        available = []
        date_str = current_date.strftime('%d/%m/%Y')
        
        for worker in workers:
            # Check if worker has X task on this date
            if (str(worker.id) in x_task_data and 
                date_str in x_task_data[str(worker.id)]):
                continue  # Worker not available
            
            # Check proximity penalty
            penalty = self.get_proximity_penalty(worker.id, current_date, x_task_data)
            if penalty > 100:  # Heavy penalty threshold
                continue  # Worker not available
            
            available.append(worker)
        
        return available
    
    def get_conflicts(self, period: str, x_task_data: Dict, y_task_data: Dict) -> List:
        """
        Get conflicts between X and Y tasks with caching.
        
        Args:
            period: Period string
            x_task_data: X-task data
            y_task_data: Y-task data
            
        Returns:
            List of conflicts
        """
        cache_key = f"conflicts_{period}"
        
        # Check if we have valid cached conflicts
        if (cache_key in self.conflict_cache and
            self._is_cache_valid(self.conflict_cache.get(f"{cache_key}_time", 0),
                               self.conflict_cache_ttl)):
            
            self.cache_hits += 1
            return self.conflict_cache[cache_key]
        
        # Cache miss - calculate conflicts
        self.cache_misses += 1
        conflicts = self._calculate_conflicts(x_task_data, y_task_data)
        
        # Cache the result
        self.conflict_cache[cache_key] = conflicts
        self.conflict_cache[f"{cache_key}_time"] = time.time()
        
        return conflicts
    
    def _calculate_conflicts(self, x_task_data: Dict, y_task_data: Dict) -> List:
        """Calculate conflicts between X and Y tasks"""
        conflicts = []
        
        for worker_id, x_assignments in x_task_data.items():
            if worker_id in y_task_data:
                y_assignments = y_task_data[worker_id]
                
                for date_str, x_task in x_assignments.items():
                    if date_str in y_assignments:
                        conflicts.append({
                            'worker_id': worker_id,
                            'date': date_str,
                            'x_task': x_task,
                            'y_task': y_assignments[date_str]
                        })
        
        return conflicts
    
    def invalidate_cache(self, cache_type: str = None):
        """
        Invalidate cache entries.
        
        Args:
            cache_type: Type of cache to invalidate ('x_tasks', 'y_tasks', 'all')
        """
        if cache_type == 'x_tasks' or cache_type == 'all':
            self.x_task_cache.clear()
            self.x_task_cache_time.clear()
            print("🗑️ X-task cache cleared")
        
        if cache_type == 'y_tasks' or cache_type == 'all':
            self.y_task_cache.clear()
            self.y_task_cache_time.clear()
            print("🗑️ Y-task cache cleared")
        
        if cache_type == 'all':
            self.proximity_cache.clear()
            self.availability_cache.clear()
            self.conflict_cache.clear()
            print("🗑️ All caches cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'x_task_cache_size': len(self.x_task_cache),
            'y_task_cache_size': len(self.y_task_cache),
            'proximity_cache_size': len(self.proximity_cache),
            'availability_cache_size': len(self.availability_cache)
        }
    
    def print_cache_stats(self):
        """Print cache statistics"""
        stats = self.get_cache_stats()
        print("\n📊 Cache Statistics:")
        print(f"   Hits: {stats['hits']}")
        print(f"   Misses: {stats['misses']}")
        print(f"   Hit Rate: {stats['hit_rate']:.2%}")
        print(f"   X-Task Cache Entries: {stats['x_task_cache_size']}")
        print(f"   Y-Task Cache Entries: {stats['y_task_cache_size']}")
        print(f"   Proximity Cache Entries: {stats['proximity_cache_size']}")
        print(f"   Availability Cache Entries: {stats['availability_cache_size']}")


# Global cache manager instance
cache_manager = CacheManager() 