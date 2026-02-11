"""
系统托盘模块
提供系统托盘图标和菜单
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

try:
    import pystray
    from PIL import Image, ImageDraw
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logging.warning("pystray或Pillow未安装")

from config import config

logger = logging.getLogger(__name__)


class TrayIconManager(QObject):
    """系统托盘管理器"""
    
    # 信号
    show_window_signal = pyqtSignal()
    hide_window_signal = pyqtSignal()
    quit_signal = pyqtSignal()
    settings_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.parent_window = parent
        self.tray_icon = None
        
        # 初始化托盘图标
        self._initialize()
        
    def _initialize(self):
        """初始化系统托盘"""
        # 使用Qt的系统托盘
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置图标
        icon = self._create_icon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("AI助手")
        
        # 创建菜单
        self._create_menu()
        
        # 连接信号
        self.tray_icon.activated.connect(self._on_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        logger.info("系统托盘初始化完成")
        
    def _create_icon(self) -> QIcon:
        """创建托盘图标"""
        # 尝试加载自定义图标
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "icon.png"
        
        if icon_path.exists():
            return QIcon(str(icon_path))
        
        # 创建默认图标
        return self._create_default_icon()
        
    def _create_default_icon(self) -> QIcon:
        """创建默认图标"""
        if PYSTRAY_AVAILABLE:
            # 使用PIL创建图标
            width = 64
            height = 64
            
            # 创建图像
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            
            # 绘制圆形背景
            dc.ellipse(
                [4, 4, width-4, height-4],
                fill=(15, 52, 96, 255),  # #0f3460
                outline=(233, 69, 96, 255),  # #e94560
                width=3
            )
            
            # 绘制AI文字
            dc.text(
                (width//2-12, height//2-10),
                "AI",
                fill=(255, 255, 255, 255),
                font=None
            )
            
            # 保存临时文件
            temp_path = Path(__file__).parent.parent / "assets" / "icons" / "temp_icon.png"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(temp_path)
            
            return QIcon(str(temp_path))
        else:
            # 返回空图标
            return QIcon()
            
    def _create_menu(self):
        """创建托盘菜单"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
                border: 1px solid #2d3561;
                border-radius: 8px;
                padding: 8px;
            }
            QMenu::item {
                color: #ffffff;
                padding: 8px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0f3460;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2d3561;
                margin: 4px 8px;
            }
        """)
        
        # 显示/隐藏
        self.show_action = QAction("显示助手", self)
        self.show_action.triggered.connect(self._show_window)
        menu.addAction(self.show_action)
        
        # 对话
        chat_action = QAction("💬 打开对话", self)
        chat_action.triggered.connect(self._open_chat)
        menu.addAction(chat_action)
        
        menu.addSeparator()
        
        # 设置
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # 退出
        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        
    def _on_activated(self, reason):
        """托盘图标被激活"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # 双击显示/隐藏窗口
            self._toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 单击显示菜单
            pass
            
    def _toggle_window(self):
        """切换窗口显示"""
        if self.parent_window and self.parent_window.isVisible():
            self.hide_window_signal.emit()
            self.show_action.setText("显示助手")
        else:
            self.show_window_signal.emit()
            self.show_action.setText("隐藏助手")
            
    def _show_window(self):
        """显示窗口"""
        self.show_window_signal.emit()
        self.show_action.setText("隐藏助手")
        
    def _open_chat(self):
        """打开对话"""
        self.show_window_signal.emit()
        if self.parent_window:
            self.parent_window.show_chat_panel()
            
    def _open_settings(self):
        """打开设置"""
        self.settings_signal.emit()
        if self.parent_window:
            self.parent_window.show_settings_panel()
            
    def _quit(self):
        """退出应用"""
        self.quit_signal.emit()
        
    def show_notification(self, title: str, message: str):
        """
        显示通知
        
        Args:
            title: 标题
            message: 消息内容
        """
        if self.tray_icon:
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
            
    def set_tooltip(self, text: str):
        """
        设置工具提示
        
        Args:
            text: 提示文本
        """
        if self.tray_icon:
            self.tray_icon.setToolTip(text)
            
    def cleanup(self):
        """清理资源"""
        logger.info("清理系统托盘...")
        
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
