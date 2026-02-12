"""
AI助手桌面应用 - 主程序入口

功能特点:
- 3D FBX模型显示 (无边框、透明背景、可拖动)
- 语音唤醒和识别
- 语音合成 (多种声音选择)
- Ollama本地LLM集成
- 多线程架构

作者: AI Assistant
版本: 1.0.0
"""

import sys
import logging
import signal
from pathlib import Path
import subprocess

# 添加项目根目录到路径
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import config
from modules.window import MainWindow
from modules.tray_icon import TrayIconManager
from utils.thread_pool import ThreadPoolManager


# 配置日志
def setup_logging():
    """配置日志系统"""
    log_dir = base_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "ai-assistant.log"
    
    logging.basicConfig(
        level=getattr(logging, config.general.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


# 全局日志实例
logger = setup_logging()


class AIAssistantApp:
    """AI助手应用程序"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.tray_manager = None
        self.thread_pool = None
        
    def initialize(self):
        """初始化应用程序"""
        logger.info("=" * 50)
        logger.info("AI助手桌面应用启动中...")
        logger.info("=" * 50)

        # 创建Qt应用
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出
        
        # 设置应用程序字体
        font = QFont("Segoe UI", 10)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.app.setFont(font)
        
        # 启用高DPI支持
        self.app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
        # 初始化线程池
        self.thread_pool = ThreadPoolManager()
        logger.info("线程池初始化完成")
        
        # 创建主窗口
        self.main_window = MainWindow()
        logger.info("主窗口创建完成")
        # 计算并设置窗口位置，注意 primaryScreen() 可能返回 None（无显示环境）
        try:
            screen = self.app.primaryScreen()
            # 回退到配置中的位置以防 screen 为 None
            if screen is None:
                logger.warning("无法获取主屏幕 (primaryScreen 返回 None)，将使用配置中的窗口位置作为回退")
                target_x = config.window.pos_x
                target_y = config.window.pos_y
            else:
                available_area = screen.availableGeometry()

                # 获取窗口自身尺寸
                window_width = self.main_window.width()
                window_height = self.main_window.height()

                # 计算右下角位置：屏幕右下角坐标 - 窗口尺寸（确保窗口完全在屏幕内）
                target_x = available_area.right() - window_width
                target_y = available_area.bottom() - window_height

                # 兜底：防止窗口尺寸超过屏幕（位置不小于0）
                target_x = max(0, target_x)
                target_y = max(0, target_y)

            # 强制移动窗口到计算出的位置
            self.main_window.move(target_x, target_y)
        except Exception:
            # 任意异常时使用配置中的位置并记录日志
            logger.exception("设置窗口位置时发生异常，使用配置中的位置作为回退")
            try:
                self.main_window.move(config.window.pos_x, config.window.pos_y)
            except Exception:
                logger.exception("回退移动窗口也失败")
        
        # 创建系统托盘
        self.tray_manager = TrayIconManager(self.main_window)
        logger.info("系统托盘初始化完成")
        
        # 连接信号
        self._connect_signals()
        
        # 显示主窗口
        self.main_window.show()
        logger.info("主窗口显示完成")
        
        logger.info("AI助手启动成功！")
        logger.info(f"窗口位置: ({config.window.pos_x}, {config.window.pos_y})")
        logger.info(f"当前模型: {config.model.current}")
        logger.info(f"Ollama模型: {config.ollama.model}")
        
    def _connect_signals(self):
        """连接信号和槽"""
        # 托盘显示/隐藏信号
        self.tray_manager.show_window_signal.connect(self.main_window.show_window)
        self.tray_manager.hide_window_signal.connect(self.main_window.hide_window)
        
        # 退出信号
        self.tray_manager.quit_signal.connect(self.quit)
        
        # 窗口关闭时保存位置
        self.main_window.position_changed.connect(
            lambda x, y: config.update_window_position(x, y)
        )
        
    def run(self):
        """运行应用程序"""
        try:
            self.initialize()
            return self.app.exec()
        except Exception as e:
            logger.error(f"应用程序运行错误: {e}", exc_info=True)
            return 1
            
    def quit(self):
        """退出应用程序"""
        logger.info("正在关闭AI助手...")
        
        # 停止所有线程
        if self.thread_pool:
            self.thread_pool.shutdown()
            
        # 清理资源
        if self.main_window:
            self.main_window.cleanup()
            
        if self.tray_manager:
            self.tray_manager.cleanup()
            
        # 保存配置
        config.save()
        
        logger.info("AI助手已关闭")
        self.app.quit()


def signal_handler(signum, _frame):
    """信号处理函数"""
    logger.info(f"接收到信号: {signum}")
    QApplication.quit()


def main():
    """主函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并运行应用
    app = AIAssistantApp()
    return app.run()


if __name__ == "__main__":
    subprocess.run(["python", "./ai-assistant/logs/clean.py"])
    sys.exit(main())
