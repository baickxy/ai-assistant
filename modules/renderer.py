"""
简化的渲染器模块 - 使用QPainter渲染2D图片
由于QOpenGLWidget在PyQt6 + Intel Iris Xe Graphics上存在渲染问题，
改用QWidget + QPainter实现可靠的2D图片显示
"""

import logging
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, Qt, QRect, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent, QImage, QPainter, QColor, QPixmap, QFont, QLinearGradient

from config import config
# FBX和动画功能暂时禁用，因为不使用OpenGL
# from .fbx_loader import FBXLoader
# from .animator import Animator

logger = logging.getLogger(__name__)


class OpenGLRenderer(QWidget):
    """简化的渲染器 - 使用QPainter渲染2D图片"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 图片数据
        self.image: Optional[QImage] = None
        self.pixmap: Optional[QPixmap] = None
        self.image_path: Optional[Path] = None

        # 图片显示模式
        self.scale_mode = "fit"  # "fit" (适应) 或 "stretch" (拉伸)

        # 鼠标控制
        self.last_mouse_pos = None
        # 窗口拖动状态（按住 Ctrl + 左键 在渲染区拖动窗口）
        self._window_drag_pos = None
        self._window_is_dragging = False

        # 动画定时器（用于可能的动画GIF）
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update)
        self.animation_timer.start(16)  # ~60fps

        logger.info("渲染器初始化完成 (使用QPainter模式)")

    def paintEvent(self, event):
        """使用QPainter绘制图片或背景"""
        try:
            painter = QPainter(self)

            # 启用抗锯齿
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # 如果有图片，绘制图片
            if self.pixmap is not None and not self.pixmap.isNull():
                if self.scale_mode == "fit":
                    # 适应模式：保持宽高比
                    target_rect = self._calculate_fitted_rect(self.pixmap.size(), self.rect())
                    painter.drawPixmap(target_rect, self.pixmap)
                    logger.debug(f"paintEvent: 绘制图片(fit模式)，大小: {self.width()}x{self.height()}")
                else:
                    # 拉伸模式：填充整个区域
                    painter.drawPixmap(self.rect(), self.pixmap)
                    logger.debug(f"paintEvent: 绘制图片(stretch模式)，大小: {self.width()}x{self.height()}")
            else:
                # 没有图片时，绘制渐变背景
                self._draw_default_background(painter)

            painter.end()
        except Exception as e:
            logger.error(f"paintEvent绘制失败: {e}", exc_info=True)

    def _calculate_fitted_rect(self, image_size, widget_rect):
        """计算适应模式的矩形（保持宽高比）"""
        img_width = image_size.width()
        img_height = image_size.height()
        widget_width = widget_rect.width()
        widget_height = widget_rect.height()

        if img_width == 0 or img_height == 0:
            return widget_rect

        # 计算缩放比例
        scale_x = widget_width / img_width
        scale_y = widget_height / img_height
        scale = min(scale_x, scale_y)

        # 计算新的尺寸
        scaled_width = int(img_width * scale)
        scaled_height = int(img_height * scale)

        # 居中显示
        x = (widget_width - scaled_width) // 2
        y = (widget_height - scaled_height) // 2

        return QRect(x, y, scaled_width, scaled_height)

    def _draw_default_background(self, painter):
        """绘制默认背景"""
        rect = self.rect()

        # 创建渐变背景
        gradient = QLinearGradient(QPointF(0, 0), QPointF(rect.width(), rect.height()))
        gradient.setColorAt(0.0, QColor(100, 149, 237))  # 矢车菊蓝
        gradient.setColorAt(1.0, QColor(65, 105, 225))  # 皇家蓝
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect)

        # 绘制提示文本
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 12))
        text = "请加载图片"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = (rect.width() - text_rect.width()) // 2
        text_y = (rect.height() - text_rect.height()) // 2
        painter.drawText(text_x, text_y, text)

        logger.debug("paintEvent: 绘制默认背景")

    def _update(self):
        """定时更新（用于动画GIF等）"""
        # 如果需要支持动画GIF，可以在这里更新当前帧
        pass

    # 鼠标事件处理
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        # 支持按住 Ctrl + 左键 拖动窗口（避免与模型旋转冲突）
        try:
            modifiers = event.modifiers()
        except Exception:
            modifiers = None

        if event.button() == Qt.MouseButton.LeftButton and modifiers is not None and (modifiers & Qt.KeyboardModifier.ControlModifier):
            # 将拖动信息传递给主窗口
            parent_win = self.window()
            if parent_win is not None:
                try:
                    # 将拖动信息保存在渲染器自身，避免修改父窗口的未知属性
                    self._window_drag_pos = event.globalPosition().toPoint() - parent_win.frameGeometry().topLeft()
                    self._window_is_dragging = True
                except Exception:
                    logger.debug("开始窗口拖动失败")
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()
            logger.debug(f"鼠标按下: {event.pos()}")

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        # 如果主窗口处于拖动状态，处理窗口移动
        parent_win = self.window()
        if parent_win is not None and getattr(self, '_window_is_dragging', False):
            try:
                if self._window_drag_pos is not None:
                    new_pos = event.globalPosition().toPoint() - self._window_drag_pos
                    parent_win.move(new_pos)
            except Exception:
                logger.debug("窗口拖动移动失败")
            event.accept()
            return

        if self.last_mouse_pos is not None:
            # 目前渲染器为2D图片展示，鼠标拖动仅记录位置（可扩展为图片平移）
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        # 停止任何窗口拖动
        # 停止窗口拖动（如果正在进行）
        if getattr(self, '_window_is_dragging', False):
            self._window_is_dragging = False
            event.accept()
            return

        self.last_mouse_pos = None

    def load_fbx(self, file_path: Path):
        """加载FBX模型（已禁用，使用图片代替）"""
        logger.warning("FBX模型加载已禁用，请使用图片文件")
        logger.info(f"尝试加载图片: {file_path}")
        # 尝试将.fbx替换为图片扩展名
        for ext in ['.png', '.jpg', '.jpeg', '.bmp']:
            image_path = file_path.with_suffix(ext)
            if image_path.exists():
                self.load_image(image_path)
                return
        logger.error(f"未找到对应的图片文件: {file_path}")

    def load_image(self, file_path: Path):
        """加载图片"""
        try:
            self.image_path = file_path
            self.image = QImage(str(file_path))

            if self.image.isNull():
                logger.error(f"图片加载失败（空图片）: {file_path}")
                return False

            # 转换为QPixmap以提高性能
            self.pixmap = QPixmap.fromImage(self.image)

            # 从配置获取缩放模式
            scale_config = getattr(config.model, 'scale_mode', 'fit') if hasattr(config.model, 'scale_mode') else 'fit'
            self.scale_mode = scale_config if scale_config in ['fit', 'stretch'] else 'fit'

            logger.info(f"图片加载成功: {file_path}, 大小: {self.image.width()}x{self.image.height()}, 模式: {self.scale_mode}")
            self.update()  # 触发重绘
            return True
        except Exception as e:
            logger.error(f"图片加载失败: {e}", exc_info=True)
            return False

    def set_scale_mode(self, mode: str):
        """设置图片缩放模式"""
        if mode in ['fit', 'stretch']:
            self.scale_mode = mode
            self.update()
            logger.info(f"缩放模式设置为: {mode}")

    def cleanup(self):
        """清理资源"""
        if self.animation_timer:
            self.animation_timer.stop()
        self.image = None
        self.pixmap = None
        logger.info("渲染器资源清理完成")

