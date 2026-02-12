"""
主窗口模块
实现无边框、透明背景、可拖动的3D模型显示窗口
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QApplication, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction

from config import config
from .renderer import OpenGLRenderer
from .chat_panel import ChatPanel
from .settings_panel import SettingsPanel
from .voice_synthesizer import VoiceSynthesizer

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    # 信号定义
    position_changed = pyqtSignal(int, int)  # 窗口位置改变信号
    
    def __init__(self):
        super().__init__()
        
        # 拖动相关
        self._drag_pos = None
        self._is_dragging = False
        
        # 子窗口
        self.chat_panel = None
        self.settings_panel = None

        # 语音合成器
        self.voice_synthesizer = None
        
        # 初始化UI
        self._setup_window()
        self._setup_ui()
        self._setup_interactions()
        
        logger.info("主窗口初始化完成")
        
    def _setup_window(self):
        """设置窗口属性"""
        # 无边框窗口
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # 不在任务栏显示
        )
        self.setWindowTitle("AI助手")

        # 透明背景
        # 仅在需要半透明窗口时启用透明背景，否则保持不透明以确保渲染可见
        # 仅在配置将窗口设置为高度透明时启用透明背景（阈值 0.5），
        # 避免默认配置（如 0.95）导致整个窗口不可见。
        try:
            window_opacity = getattr(config.window, 'opacity', 1.0)
            if window_opacity < 0.5:
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        except (AttributeError, TypeError) as e:
            logger.warning(f"设置透明背景时出错: {e}")

        # 设置窗口大小和位置
        self.setGeometry(
            config.window.pos_x,
            config.window.pos_y,
            config.window.width,
            config.window.height
        )

        # 设置窗口透明度
        self.setWindowOpacity(config.window.opacity)

        logger.info(f"窗口设置完成: 位置({self.x()}, {self.y()}), 大小({self.width()}x{self.height()})")


        
    def _setup_ui(self):
        """设置UI界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 渲染器 (显示2D图片)
        self.renderer = OpenGLRenderer(self)
        layout.addWidget(self.renderer)

        # 加载默认图片
        try:
            model_path = config.get_model_path()
            if model_path.exists():
                self.renderer.load_image(model_path)
                logger.info(f"默认图片加载成功: {model_path}")
            else:
                # 如果默认图片不存在，尝试加载assets/icons目录下的图片
                icons_dir = Path(__file__).parent.parent / "assets" / "icons"
                if icons_dir.exists():
                    for img_file in icons_dir.glob("*.png"):
                        self.renderer.load_image(img_file)
                        logger.info(f"从icons目录加载图片: {img_file}")
                        break
        except Exception as e:
            logger.warning(f"加载默认图片失败: {e}")

        # 创建对话面板 (初始隐藏) - 作为顶层窗口创建，便于独立显示/移动
        self.chat_panel = ChatPanel(None)
        self.chat_panel.hide()

        # 创建设置面板 (初始隐藏) - 作为顶层窗口创建，设置时按屏幕坐标定位
        self.settings_panel = SettingsPanel(None)
        self.settings_panel.hide()

        # 初始化语音合成器
        self.voice_synthesizer = VoiceSynthesizer()

        # 连接语音请求信号
        self.chat_panel.voice_requested.connect(self._on_voice_requested)

        logger.info("UI设置完成")


        
    def _setup_interactions(self):
        """设置交互"""
        # 启用鼠标跟踪
        self.setMouseTracking(True)
        central_widget = self.centralWidget()
        if central_widget:
            central_widget.setMouseTracking(True)
            
        # 启动位置保存定时器
        # 启动位置保存定时器
        self._save_pos_timer = QTimer(self)
        self._save_pos_timer.timeout.connect(self._save_position)
        self._save_pos_timer.start(5000)  # 每5秒保存一次位置
        logger.debug("位置保存定时器已启动")
        
    def _save_position(self):
        """保存窗口位置"""
        pos = self.pos()
        try:
            current_x = getattr(config.window, 'pos_x', pos.x())
            current_y = getattr(config.window, 'pos_y', pos.y())
            if pos.x() != current_x or pos.y() != current_y:
                self.position_changed.emit(pos.x(), pos.y())
        except (AttributeError, TypeError) as e:
            logger.warning(f"保存窗口位置时出错: {e}")
            
    # ==================== 鼠标事件处理 ====================
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            self._drag_pos = global_pos - self.frameGeometry().topLeft()
            self._is_dragging = True

            # 点击效果: 轻微缩放
            try:
                current_opacity = getattr(config.window, 'opacity', 1.0)
                self.setWindowOpacity(current_opacity * 0.9)
            except (AttributeError, TypeError) as e:
                logger.warning(f"设置窗口透明度时出错: {e}")

            event.accept()
            
        elif event.button() == Qt.MouseButton.RightButton:
            # 显示右键菜单
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self._is_dragging and self._drag_pos is not None:
            try:
                new_pos = event.globalPosition().toPoint() - self._drag_pos
                self.move(new_pos)
            except (AttributeError, TypeError) as e:
                logger.warning(f"计算窗口位置时出错: {e}")
            event.accept()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

            # 恢复透明度
            try:
                self.setWindowOpacity(getattr(config.window, 'opacity', 1.0))
            except (AttributeError, TypeError) as e:
                logger.warning(f"恢复窗口透明度时出错: {e}")

            # 保存位置
            pos = self.pos()
            self.position_changed.emit(pos.x(), pos.y())

            event.accept()
            
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 双击打开/关闭对话面板
            self.toggle_chat_panel()
            event.accept()
            
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
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
        
        # 对话选项
        chat_action = QAction("💬 打开对话", self)
        chat_action.triggered.connect(self.show_chat_panel)
        menu.addAction(chat_action)
        
        # 设置选项
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.show_settings_panel)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # 退出选项
        quit_action = QAction("❌ 退出", self)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)
        
        menu.exec(pos)
        
    def _on_quit(self):
        """退出处理"""
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()
        
    # ==================== 窗口控制 ====================
    
    def show_window(self):
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()
        
    def hide_window(self):
        """隐藏窗口"""
        self.hide()
        
    def toggle_visibility(self):
        """切换窗口可见性"""
        if self.isVisible():
            self.hide_window()
        else:
            self.show_window()
            
    # ==================== 面板控制 ====================
    
    def show_chat_panel(self):
        """显示对话面板"""
        if self.chat_panel:
            # 计算面板位置 (窗口右侧)
            panel_x = self.x() + self.width() + 10
            panel_y = self.y()

            # 确保面板在可见屏幕范围内
            try:
                screen = QApplication.primaryScreen()
                if screen is not None:
                    geom = screen.availableGeometry()
                    # 若面板超出右侧边界，则将其放到主窗口左侧
                    if panel_x + self.chat_panel.width() > geom.right():
                        panel_x = max(geom.left(), self.x() - self.chat_panel.width() - 10)
                    # 保证垂直方向也在屏幕内
                    panel_y = min(max(panel_y, geom.top()), geom.bottom() - self.chat_panel.height())
                else:
                    # 回退到在屏幕上的合理位置
                    panel_x = max(0, panel_x)
                    panel_y = max(0, panel_y)
            except Exception:
                pass

            self.chat_panel.move(panel_x, panel_y)
            self.chat_panel.show()
            # 尝试提升并激活窗口以确保可见
            try:
                self.chat_panel.raise_()
                self.chat_panel.activateWindow()
            except Exception:
                logger.debug("提升或激活对话面板失败，但面板已显示")
            
    def hide_chat_panel(self):
        """隐藏对话面板"""
        if self.chat_panel:
            self.chat_panel.hide()
            
    def toggle_chat_panel(self):
        """切换对话面板"""
        if self.chat_panel and self.chat_panel.isVisible():
            self.hide_chat_panel()
        else:
            self.show_chat_panel()
            
    def show_settings_panel(self):
        """显示设置面板"""
        if self.settings_panel:
            # 居中显示
            screen_obj = QApplication.primaryScreen()
            if screen_obj is None:
                logger.warning("无法获取主屏幕，使用默认位置")
                self.settings_panel.setGeometry(100, 100, 500, 600)
            else:
                screen = screen_obj.geometry()
                panel_width = 500
                panel_height = 600
                
                x = (screen.width() - panel_width) // 2
                y = (screen.height() - panel_height) // 2
                
                self.settings_panel.setGeometry(x, y, panel_width, panel_height)
            
            self.settings_panel.show()
            self.settings_panel.raise_()
            self.settings_panel.activateWindow()
            
    def hide_settings_panel(self):
        """隐藏设置面板"""
        if self.settings_panel:
            self.settings_panel.hide()
            
    # ==================== 其他方法 ====================

    def _on_voice_requested(self, text: str):
        """处理语音请求"""
        if self.voice_synthesizer and text:
            self.voice_synthesizer.speak(text)

    def set_model(self, model_path: Path):
        """设置图片 (原3D模型已改用2D图片)"""
        if self.renderer:
            self.renderer.load_image(model_path)

    def play_animation(self, animation_name: str):
        """播放动画 (已禁用，2D图片不支持动画)"""
        logger.warning("动画功能已禁用 (2D图片渲染模式)")

    def cleanup(self):
        """清理资源"""
        logger.info("清理主窗口资源...")
        
        if self.chat_panel:
            self.chat_panel.close()
            
        if self.settings_panel:
            self.settings_panel.close()
            
        if self.renderer:
            self.renderer.cleanup()
            
        self._save_pos_timer.stop()
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 最小化到托盘而不是关闭
        try:
            minimize_to_tray = getattr(config.general, 'minimize_to_tray', False)
            if minimize_to_tray:
                self.hide_window()
                event.ignore()
            else:
                self.cleanup()
                event.accept()
        except (AttributeError, TypeError) as e:
            logger.warning(f"处理窗口关闭事件时出错: {e}")
            # 发生错误时默认执行清理
            self.cleanup()
            event.accept()
