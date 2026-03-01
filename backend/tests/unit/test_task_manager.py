"""
单元测试 - TaskManager 核心功能
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from task_service.task_manager import TaskManager
from apscheduler.schedulers.background import BackgroundScheduler


@pytest.fixture(autouse=True)
def reset_task_manager():
    """在每个测试前重置 TaskManager 单例，确保测试独立"""
    # 保存原始实例（如果有）
    original_instance = TaskManager._instance
    # 重置单例
    TaskManager._instance = None
    yield
    # 测试后恢复原始实例（如果需要）
    TaskManager._instance = original_instance


class TestTaskManager:
    """TaskManager 单元测试"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = TaskManager()
        manager2 = TaskManager()
        assert manager1 is manager2, "TaskManager should be a singleton"
    
    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        manager = TaskManager()
        assert manager.scheduler is not None, "Scheduler should be initialized"
        assert isinstance(manager.scheduler, BackgroundScheduler), "Scheduler should be BackgroundScheduler"
    
    def test_add_job_interval(self):
        """测试添加间隔触发器任务"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.get_job = Mock(return_value=None)
        manager.scheduler.add_job = Mock()
        manager.remove_job = Mock()  # Mock remove_job to avoid side effects
        
        # Use correct format: {"value": 60, "unit": "seconds"}
        with patch('task_service.task_manager.IntervalTrigger') as mock_trigger:
            mock_trigger.return_value = Mock()
            manager.add_job(1, "interval", '{"value": 60, "unit": "seconds"}', "active", 0)
        
        manager.scheduler.add_job.assert_called_once()
        call_args = manager.scheduler.add_job.call_args
        assert call_args[1]['id'] == "1", "Job ID should be task_id as string"
        assert call_args[1]['replace_existing'] is True, "Should replace existing job"
    
    def test_add_job_cron(self):
        """测试添加 Cron 触发器任务"""
        manager = TaskManager()
        mock_scheduler = Mock(spec=['get_job', 'add_job'])  # Use spec to ensure methods exist
        mock_scheduler.get_job = Mock(return_value=None)
        mock_scheduler.add_job = Mock()
        manager.scheduler = mock_scheduler
        
        manager.add_job(2, "cron", "0 0 * * *", "active", 0)
        
        mock_scheduler.add_job.assert_called_once()
    
    def test_remove_job(self):
        """测试移除任务"""
        manager = TaskManager()
        # Create a fresh mock scheduler - need to replace the existing one
        # Ensure we completely replace the scheduler to avoid interference from other tests
        mock_scheduler = Mock(spec=['get_job', 'remove_job'])  # Use spec to ensure methods exist
        mock_job = Mock()
        mock_job.id = "1"  # Ensure mock_job is truthy
        mock_scheduler.get_job = Mock(return_value=mock_job)
        mock_scheduler.remove_job = Mock()
        # Directly replace scheduler attribute - this should work even with singleton
        manager.scheduler = mock_scheduler
        
        # Verify scheduler was replaced
        assert manager.scheduler is mock_scheduler, "Scheduler should be replaced"
        
        # Call remove_job
        manager.remove_job(1)
        
        # Verify get_job was called to check if job exists
        assert mock_scheduler.get_job.called, "get_job should be called to check job existence"
        mock_scheduler.get_job.assert_called_once_with("1")
        # Verify remove_job was called (get_job is called internally to check if job exists)
        assert mock_scheduler.remove_job.called, "remove_job should be called when job exists"
        mock_scheduler.remove_job.assert_called_once_with("1")
    
    def test_remove_job_not_exists(self):
        """测试移除不存在的任务"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.get_job = Mock(return_value=None)
        manager.scheduler.remove_job = Mock()
        
        manager.remove_job(999)
        
        manager.scheduler.remove_job.assert_not_called()
    
    def test_pause_job(self):
        """测试暂停任务"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.get_job = Mock(return_value=Mock())
        manager.scheduler.pause_job = Mock()
        
        manager.pause_job(1)
        
        manager.scheduler.pause_job.assert_called_once_with("1")
    
    def test_resume_job(self):
        """测试恢复任务"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.get_job = Mock(return_value=Mock())
        manager.scheduler.resume_job = Mock()
        
        manager.resume_job(1)
        
        manager.scheduler.resume_job.assert_called_once_with("1")
    
    def test_get_next_run_time(self):
        """测试获取下次运行时间"""
        manager = TaskManager()
        manager.scheduler = Mock()
        mock_job = Mock()
        mock_job.next_run_time = "2024-01-01 12:00:00"
        manager.scheduler.get_job = Mock(return_value=mock_job)
        
        result = manager.get_next_run_time(1)
        
        assert result == "2024-01-01 12:00:00", "Should return next_run_time"
    
    def test_get_next_run_time_not_exists(self):
        """测试获取不存在任务的下次运行时间"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.get_job = Mock(return_value=None)
        
        result = manager.get_next_run_time(999)
        
        assert result is None, "Should return None for non-existent job"
    
    def test_stop_execution(self):
        """测试停止执行"""
        manager = TaskManager()
        with patch('task_service.task_manager.process_manager') as mock_pm:
            mock_pm.stop_execution = Mock(return_value=True)
            result = manager.stop_execution(1)
            assert result is True, "Should return True on success"
            mock_pm.stop_execution.assert_called_once_with(1)
    
    def test_stop_execution_not_running(self):
        """测试停止不存在的执行"""
        manager = TaskManager()
        with patch('task_service.task_manager.process_manager') as mock_pm:
            mock_pm.stop_execution = Mock(return_value=False)
            result = manager.stop_execution(999)
            assert result is False, "Should return False for non-existent execution"
            mock_pm.stop_execution.assert_called_once_with(999)
    
    def test_start_scheduler(self):
        """测试启动调度器"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.running = False
        manager.scheduler.start = Mock()
        
        with patch('task_service.task_manager.resource_monitor') as mock_rm:
            mock_rm.start = Mock()
            manager.start()
            manager.scheduler.start.assert_called_once()
            mock_rm.start.assert_called_once()
    
    def test_start_scheduler_already_running(self):
        """测试启动已运行的调度器"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.running = True
        manager.scheduler.start = Mock()
        
        manager.start()
        
        manager.scheduler.start.assert_not_called()
    
    def test_shutdown_scheduler(self):
        """测试关闭调度器"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.running = True
        manager.scheduler.shutdown = Mock()
        
        with patch('task_service.task_manager.resource_monitor') as mock_rm:
            mock_rm.stop = Mock()
            manager.shutdown()
            mock_rm.stop.assert_called_once()
            manager.scheduler.shutdown.assert_called_once()
    
    def test_shutdown_scheduler_not_running(self):
        """测试关闭未运行的调度器"""
        manager = TaskManager()
        manager.scheduler = Mock()
        manager.scheduler.running = False
        manager.scheduler.shutdown = Mock()
        
        manager.shutdown()
        
        manager.scheduler.shutdown.assert_not_called()
    
    def test_load_jobs_from_db(self):
        """测试从数据库加载任务"""
        manager = TaskManager()
        manager.add_job = Mock()
        
        mock_task = Mock()
        mock_task.id = 1
        mock_task.trigger_type = "interval"
        mock_task.trigger_value = '{"value": 60, "unit": "seconds"}'
        mock_task.status = "active"
        mock_task.priority = 0
        
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all = Mock(return_value=[mock_task])
        mock_session.query.return_value = mock_query
        
        with patch('task_service.task_manager.SessionLocal', return_value=mock_session):
            manager.load_jobs_from_db()
            
            manager.add_job.assert_called_once_with(1, "interval", '{"value": 60, "unit": "seconds"}', "active", 0)
