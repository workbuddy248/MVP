# src/infrastructure/data_storage.py
"""
Data Storage Infrastructure
Handles persistence of test results, configurations, and learning data
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

class DataStorage:
    """
    Data Storage Manager
    Handles persistence and retrieval of test execution data
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_path = Path(config.get("base_path", "./test_data"))
        self.retention_days = config.get("results_retention_days", 30)
        
        # Create directory structure
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize storage directory structure"""
        
        directories = [
            self.base_path,
            self.base_path / "test_results",
            self.base_path / "execution_logs",
            self.base_path / "screenshots",
            self.base_path / "agent_data",
            self.base_path / "learning_data",
            self.base_path / "configurations"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Data storage initialized at: {self.base_path}")
    
    async def store_test_results(self, execution_result: Dict[str, Any]) -> str:
        """
        Store complete test execution results
        
        Args:
            execution_result: TestExecutionResult from AI Controller
            
        Returns:
            str: File path where results were stored
        """
        
        try:
            execution_id = execution_result.get("execution_id", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"test_results_{execution_id}_{timestamp}.json"
            filepath = self.base_path / "test_results" / filename
            
            # Ensure all data is serializable
            serializable_result = self._make_serializable(execution_result)
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(serializable_result, f, indent=2, default=str)
            
            logger.info(f"Test results stored: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to store test results: {e}")
            raise
    
    async def store_agent_data(self, agent_name: str, agent_result: Dict[str, Any]) -> str:
        """
        Store individual agent execution data
        
        Args:
            agent_name: Name of the agent
            agent_result: Agent execution result
            
        Returns:
            str: File path where data was stored
        """
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename
            filename = f"{agent_name}_{timestamp}.json"
            filepath = self.base_path / "agent_data" / filename
            
            # Store agent data
            agent_data = {
                "agent_name": agent_name,
                "timestamp": timestamp,
                "result": self._make_serializable(agent_result),
                "stored_at": datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(agent_data, f, indent=2, default=str)
            
            logger.info(f"Agent data stored: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to store agent data: {e}")
            raise
    
    async def get_recent_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent test results
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recent test execution results
        """
        
        try:
            results_dir = self.base_path / "test_results"
            result_files = sorted(
                results_dir.glob("test_results_*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]
            
            results = []
            for file_path in result_files:
                try:
                    with open(file_path, 'r') as f:
                        result = json.load(f)
                        results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to load result file {file_path}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(results)} recent test results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent results: {e}")
            return []
    
    async def get_results_by_date_range(self, start_date: datetime, 
                                      end_date: datetime) -> List[Dict[str, Any]]:
        """
        Retrieve test results within a date range
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            List of test results within the date range
        """
        
        try:
            results_dir = self.base_path / "test_results"
            all_files = results_dir.glob("test_results_*.json")
            
            results = []
            for file_path in all_files:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if start_date <= file_mtime <= end_date:
                    try:
                        with open(file_path, 'r') as f:
                            result = json.load(f)
                            results.append(result)
                    except Exception as e:
                        logger.warning(f"Failed to load result file {file_path}: {e}")
                        continue
            
            # Sort by execution time
            results.sort(key=lambda x: x.get("start_time", ""), reverse=True)
            
            logger.info(f"Retrieved {len(results)} results for date range")
            return results
            
        except Exception as e:
            logger.error(f"Failed to retrieve results by date range: {e}")
            return []
    
    async def store_learning_data(self, learning_type: str, data: Dict[str, Any]) -> str:
        """
        Store learning data for AI improvement
        
        Args:
            learning_type: Type of learning data (element_patterns, success_patterns, etc.)
            data: Learning data to store
            
        Returns:
            str: File path where learning data was stored
        """
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{learning_type}_{timestamp}.json"
            filepath = self.base_path / "learning_data" / filename
            
            learning_entry = {
                "learning_type": learning_type,
                "timestamp": timestamp,
                "data": self._make_serializable(data),
                "stored_at": datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(learning_entry, f, indent=2, default=str)
            
            logger.info(f"Learning data stored: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to store learning data: {e}")
            raise
    
    async def get_learning_data(self, learning_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve learning data of specific type
        
        Args:
            learning_type: Type of learning data to retrieve
            limit: Maximum number of entries to return
            
        Returns:
            List of learning data entries
        """
        
        try:
            learning_dir = self.base_path / "learning_data"
            pattern = f"{learning_type}_*.json"
            
            learning_files = sorted(
                learning_dir.glob(pattern),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]
            
            learning_data = []
            for file_path in learning_files:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        learning_data.append(data)
                except Exception as e:
                    logger.warning(f"Failed to load learning file {file_path}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(learning_data)} learning entries for type: {learning_type}")
            return learning_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve learning data: {e}")
            return []
    
    async def cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cutoff_timestamp = cutoff_date.timestamp()
            
            # Directories to clean
            directories_to_clean = [
                self.base_path / "test_results",
                self.base_path / "execution_logs",
                self.base_path / "agent_data"
            ]
            
            total_deleted = 0
            
            for directory in directories_to_clean:
                if directory.exists():
                    for file_path in directory.iterdir():
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_timestamp:
                            try:
                                file_path.unlink()
                                total_deleted += 1
                            except Exception as e:
                                logger.warning(f"Failed to delete old file {file_path}: {e}")
            
            logger.info(f"Cleanup completed. Deleted {total_deleted} old files.")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
    
    async def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage usage statistics"""
        
        try:
            stats = {
                "base_path": str(self.base_path),
                "total_size_mb": 0,
                "directories": {}
            }
            
            for subdir in self.base_path.iterdir():
                if subdir.is_dir():
                    dir_size = 0
                    file_count = 0
                    
                    for file_path in subdir.rglob("*"):
                        if file_path.is_file():
                            dir_size += file_path.stat().st_size
                            file_count += 1
                    
                    stats["directories"][subdir.name] = {
                        "size_mb": round(dir_size / (1024 * 1024), 2),
                        "file_count": file_count
                    }
                    stats["total_size_mb"] += dir_size / (1024 * 1024)
            
            stats["total_size_mb"] = round(stats["total_size_mb"], 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get storage statistics: {e}")
            return {}
    
    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format"""
        
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(asdict(obj) if hasattr(obj, '__dataclass_fields__') else vars(obj))
        elif isinstance(obj, (datetime, Path)):
            return str(obj)
        else:
            return obj