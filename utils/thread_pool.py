"""
线程池管理模块
提供多线程任务执行和管理功能
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any, Optional
from queue import Queue
import threading

logger = logging.getLogger(__name__)


class ThreadPoolManager:
    """线程池管理器"""
    
    def __init__(self, max_workers: int = 4):
        """
        初始化线程池
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = Queue()
        self.running = True
        self._lock = threading.Lock()
        
        logger.info(f"线程池初始化完成，最大工作线程: {max_workers}")
        
    def submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        if not self.running:
            logger.warning("线程池已关闭，无法提交任务")
            return None
            
        future = self.executor.submit(func, *args, **kwargs)
        
        with self._lock:
            self.tasks.put(future)
            
        logger.debug(f"任务已提交: {func.__name__}")
        return future
        
    def submit_with_callback(
        self, 
        func: Callable, 
        callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
        *args, 
        **kwargs
    ) -> Any:
        """
        提交任务并设置回调
        
        Args:
            func: 要执行的函数
            callback: 成功回调函数
            error_callback: 错误回调函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            Future对象
        """
        future = self.submit(func, *args, **kwargs)
        
        if future:
            def done_callback(f):
                try:
                    result = f.result()
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"任务执行错误: {e}")
                    if error_callback:
                        error_callback(e)
                        
            future.add_done_callback(done_callback)
            
        return future
        
    def map(self, func: Callable, iterable):
        """
        对可迭代对象中的每个元素应用函数
        
        Args:
            func: 要应用的函数
            iterable: 可迭代对象
            
        Returns:
            结果迭代器
        """
        return self.executor.map(func, iterable)
        
    def shutdown(self, wait: bool = True):
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        self.running = False
        self.executor.shutdown(wait=wait)
        logger.info("线程池已关闭")


class WorkerThread(threading.Thread):
    """工作线程基类"""
    
    def __init__(self, name: str = None):
        super().__init__(name=name, daemon=True)
        self.running = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停
        
    def start(self):
        """启动线程"""
        self.running = True
        super().start()
        
    def stop(self):
        """停止线程"""
        self.running = False
        self._pause_event.set()  # 确保线程能继续执行以退出
        
    def pause(self):
        """暂停线程"""
        self._pause_event.clear()
        
    def resume(self):
        """恢复线程"""
        self._pause_event.set()
        
    def wait_if_paused(self):
        """如果暂停则等待"""
        self._pause_event.wait()
        
    def run(self):
        """线程主循环 (子类必须实现)"""
        raise NotImplementedError("子类必须实现run方法")


class TaskQueue:
    """任务队列"""
    
    def __init__(self):
        self.queue = Queue()
        self.results = Queue()
        
    def put(self, task: Callable, *args, **kwargs):
        """添加任务"""
        self.queue.put((task, args, kwargs))
        
    def get(self, block: bool = True, timeout: Optional[float] = None):
        """获取任务"""
        return self.queue.get(block=block, timeout=timeout)
        
    def task_done(self):
        """标记任务完成"""
        self.queue.task_done()
        
    def put_result(self, result: Any):
        """添加结果"""
        self.results.put(result)
        
    def get_result(self, block: bool = True, timeout: Optional[float] = None):
        """获取结果"""
        return self.results.get(block=block, timeout=timeout)
        
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self.queue.empty()
        
    def size(self) -> int:
        """获取队列大小"""
        return self.queue.qsize()
