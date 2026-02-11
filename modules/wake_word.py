"""
唤醒词检测模块
使用Porcupine进行本地唤醒词检测
"""

import logging
import queue
import struct
import time
from typing import Optional, Callable, List
from pathlib import Path
from enum import Enum

# 尝试导入Porcupine
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logging.warning("pvporcupine未安装")

# 尝试导入PyAudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("pyaudio未安装")

from config import config
from utils.thread_pool import WorkerThread

logger = logging.getLogger(__name__)


class WakeWordState(Enum):
    """唤醒词检测状态"""
    IDLE = 0
    LISTENING = 1
    DETECTED = 2
    COOLDOWN = 3


class WakeWordDetector(WorkerThread):
    """唤醒词检测器"""
    
    # 内置唤醒词关键词
    BUILTIN_KEYWORDS = {
        '小助手': 'xiaozhushou',
        '你好': 'nihao',
        '嘿助手': 'heyassistant',
    }
    
    def __init__(self):
        super().__init__(name="WakeWordDetector")
        
        # Porcupine引擎
        self.porcupine = None
        
        # PyAudio
        self.audio = None
        self.stream = None
        
        # 状态
        self.state = WakeWordState.IDLE
        self.detected_callback: Optional[Callable] = None
        
        # 冷却时间 (防止重复触发)
        self.cooldown_time = 2.0
        self.last_detection_time = 0.0
        
        # 音频参数
        self.sample_rate = 16000
        self.frame_length = 512
        
        # 使用简单关键词检测作为后备
        self.use_simple_detection = not PORCUPINE_AVAILABLE
        
        # 简单检测参数
        self.audio_buffer = []
        self.buffer_size = self.sample_rate * 2  # 2秒缓冲
        
        # 初始化
        self._initialize()
        
    def _initialize(self):
        """初始化唤醒词检测器"""
        if PORCUPINE_AVAILABLE and config.wake_word.access_key:
            try:
                self._init_porcupine()
            except Exception as e:
                logger.error(f"Porcupine初始化失败: {e}")
                self.use_simple_detection = True
        else:
            logger.info("使用简单唤醒词检测")
            self.use_simple_detection = True
            
        # 初始化PyAudio
        if PYAUDIO_AVAILABLE:
            try:
                self.audio = pyaudio.PyAudio()
                logger.info("PyAudio初始化完成")
            except Exception as e:
                logger.error(f"PyAudio初始化失败: {e}")
                
    def _init_porcupine(self):
        """初始化Porcupine引擎"""
        access_key = config.wake_word.access_key
        
        if not access_key:
            logger.warning("未设置Porcupine访问密钥")
            return
            
        # 创建Porcupine实例
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=['computer', 'hey google', 'alexa']
        )
        
        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length
        
        logger.info(f"Porcupine初始化完成，采样率: {self.sample_rate}")
        
    def run(self):
        """线程主循环"""
        if not self._start_stream():
            logger.error("无法启动音频流，线程退出")
            return
            
        logger.info("唤醒词检测线程启动")
        
        while self.running:
            self.wait_if_paused()
            
            if self.state == WakeWordState.IDLE:
                time.sleep(0.1)
                continue
                
            try:
                # 读取音频帧
                pcm = self.stream.read(self.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.frame_length, pcm)
                
                # 检测唤醒词
                if self.use_simple_detection:
                    detected = self._simple_detect(pcm)
                else:
                    detected = self._porcupine_detect(pcm)
                    
                if detected:
                    self._on_wake_word_detected()
                    
            except Exception as e:
                logger.error(f"检测错误: {e}")
                time.sleep(0.1)
                
    def _start_stream(self) -> bool:
        """启动音频流"""
        if not self.audio:
            return False
            
        try:
            self.stream = self.audio.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length
            )
            logger.info("音频流启动成功")
            return True
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            return False
            
    def _porcupine_detect(self, pcm: tuple) -> bool:
        """
        使用Porcupine检测唤醒词
        
        Args:
            pcm: 音频帧数据
            
        Returns:
            是否检测到唤醒词
        """
        if not self.porcupine:
            return False
            
        keyword_index = self.porcupine.process(pcm)
        return keyword_index >= 0
        
    def _simple_detect(self, pcm: tuple) -> bool:
        """
        简单唤醒词检测 (基于音量阈值)
        
        Args:
            pcm: 音频帧数据
            
        Returns:
            是否检测到唤醒词
        """
        # 计算音量
        volume = sum(abs(x) for x in pcm) / len(pcm)
        
        # 添加到缓冲区
        self.audio_buffer.extend(pcm)
        
        # 限制缓冲区大小
        if len(self.audio_buffer) > self.buffer_size:
            self.audio_buffer = self.audio_buffer[-self.buffer_size:]
            
        # 检测音量峰值 (模拟唤醒)
        # 实际项目中应该使用真正的关键词识别
        threshold = 1000  # 音量阈值
        
        if volume > threshold:
            # 检查冷却时间
            current_time = time.time()
            if current_time - self.last_detection_time > self.cooldown_time:
                logger.debug(f"音量触发: {volume}")
                return True
                
        return False
        
    def _on_wake_word_detected(self):
        """唤醒词检测到时的处理"""
        current_time = time.time()
        
        # 检查冷却时间
        if current_time - self.last_detection_time < self.cooldown_time:
            return
            
        self.last_detection_time = current_time
        self.state = WakeWordState.DETECTED
        
        logger.info("唤醒词检测到！")
        
        # 触发回调
        if self.detected_callback:
            self.detected_callback()
            
        # 进入冷却状态
        self.state = WakeWordState.COOLDOWN
        
        # 冷却结束后恢复监听
        time.sleep(self.cooldown_time)
        if self.running:
            self.state = WakeWordState.LISTENING
            
    def start_listening(self):
        """开始监听唤醒词"""
        if not self.audio:
            logger.error("音频未初始化")
            return False
            
        self.state = WakeWordState.LISTENING
        logger.info("开始监听唤醒词")
        return True
        
    def stop_listening(self):
        """停止监听唤醒词"""
        self.state = WakeWordState.IDLE
        logger.info("停止监听唤醒词")
        
    def set_detected_callback(self, callback: Callable):
        """
        设置检测到唤醒词的回调
        
        Args:
            callback: 回调函数
        """
        self.detected_callback = callback
        
    def set_cooldown(self, seconds: float):
        """
        设置冷却时间
        
        Args:
            seconds: 冷却时间 (秒)
        """
        self.cooldown_time = seconds
        logger.info(f"冷却时间设置为: {seconds}秒")
        
    def is_listening(self) -> bool:
        """检查是否正在监听"""
        return self.state in [WakeWordState.LISTENING, WakeWordState.COOLDOWN]
        
    def is_available(self) -> bool:
        """检查唤醒词检测是否可用"""
        return PYAUDIO_AVAILABLE and self.audio is not None
        
    def cleanup(self):
        """清理资源"""
        logger.info("清理唤醒词检测器...")
        
        self.stop()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        if self.audio:
            self.audio.terminate()
            
        if self.porcupine:
            self.porcupine.delete()
            
        logger.info("唤醒词检测器已清理")
