"""
对话面板模块
提供聊天界面和交互功能
"""

import logging
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QScrollArea, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QPalette

from config import config
from .llm_client import OllamaClient

logger = logging.getLogger(__name__)


class MessageBubble(QFrame):
    """消息气泡"""
    
    def __init__(self, text: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        
        self.is_user = is_user
        self.text = text
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI"""
        # 设置样式
        if self.is_user:
            bg_color = "#0f3460"
            text_color = "#ffffff"
            border_radius = "12px 12px 4px 12px"
        else:
            bg_color = "#252542"
            text_color = "#ffffff"
            border_radius = "12px 12px 12px 4px"
            
        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {bg_color};
                border-radius: {border_radius};
            }}
        """)

        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)
        
        # 文本标签
        self.label = QLabel(self.text)
        self.label.setWordWrap(True)
        # 设置大小策略，使标签能够扩展
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        # 设置最大宽度，避免文本超出气泡范围
        # 聊天面板350px - 容器边距32px - 滚动条6px - 气泡边距24px = 288px
        self.label.setMaximumWidth(288)
        self.label.setMinimumWidth(50)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 14px;
                line-height: 1.5;
                background: transparent;
            }}
        """)
        self.label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        
        layout.addWidget(self.label)
        
        # 设置大小策略
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        # 设置气泡最小宽度，避免太窄
        self.setMinimumWidth(100)
        
    def update_text(self, text: str):
        """更新文本"""
        self.text = text
        self.label.setText(text)
        # 保证 QLabel 重新计算大小与布局，避免文本看似被截断
        try:
            self.label.adjustSize()
            self.label.updateGeometry()
            self.updateGeometry()
            self.adjustSize()
        except Exception:
            pass

    def resizeEvent(self, event):
        """在气泡大小变化时调整布局"""
        try:
            # 确保标签根据气泡大小自动调整
            self.label.adjustSize()
            self.adjustSize()
        except Exception:
            pass
        return super().resizeEvent(event)


class ChatWorker(QThread):
    """聊天工作线程"""
    
    token_received = pyqtSignal(str)
    response_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    confirmation_requested = pyqtSignal(dict)  # 新增：需要用户确认的信号
    
    def __init__(self, llm_client: OllamaClient, message: str):
        super().__init__()
        self.llm_client = llm_client
        self.message = message
        self.pending_confirmation = None  # 待确认的操作
        
    def run(self):
        """运行聊天"""
        try:
            # 使用带工具桥接的接口，获取最终完整回复
            final = self.llm_client.chat_with_tools(self.message, stream=False)

            # 为了保持 UI 的流式感，将最终回复分片发送到 token_received
            if final:
                chunk_size = 64
                for i in range(0, len(final), chunk_size):
                    self.token_received.emit(final[i:i+chunk_size])

            self.response_complete.emit(final)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatPanel(QWidget):
    """对话面板"""
    
    # 信号
    voice_requested = pyqtSignal(str)  # 请求语音朗读
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # LLM客户端
        self.llm_client = OllamaClient()
        
        # 当前聊天工作线程
        self.current_worker: Optional[ChatWorker] = None
        
        # 消息气泡列表
        self.message_bubbles: list = []
        
        # 当前AI消息气泡
        self.current_ai_bubble: Optional[MessageBubble] = None
        
        # 初始化UI
        self._setup_ui()
        
        # 欢迎消息
        self._add_ai_message("你好！我是你的AI助手，有什么可以帮助你的吗？")
        
        logger.info("对话面板初始化完成")
        
    def _setup_ui(self):
        """设置UI界面"""
        # 窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置大小
        self.setFixedSize(350, 500)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 主容器 (毛玻璃效果)
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(26, 26, 46, 0.95);
                border: 1px solid #2d3561;
                border-radius: 16px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)
        
        # 标题栏
        title_bar = QHBoxLayout()
        
        title_label = QLabel("💬 AI助手")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
            }
        """)
        title_bar.addWidget(title_label)
        
        title_bar.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b8b8d1;
                border: none;
                border-radius: 14px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e94560;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_bar.addWidget(close_btn)
        
        container_layout.addLayout(title_bar)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #2d3561;")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)
        
        # 消息区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background: #2d3561;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0f3460;
            }
        """)
        
        # 消息容器
        self.messages_widget = QWidget()
        self.messages_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(12)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)

        self.scroll_area.setWidget(self.messages_widget)
        container_layout.addWidget(self.scroll_area)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #252542;
                border: 1px solid #2d3561;
                border-radius: 20px;
                padding: 10px 16px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #0f3460;
            }
            QLineEdit::placeholder {
                color: #6b6b8a;
            }
        """)
        self.input_field.returnPressed.connect(self._send_message)
        # 设置输入框的大小策略为可扩展
        self.input_field.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        input_layout.addWidget(self.input_field, stretch=1)
        
        # 发送按钮
        send_btn = QPushButton("发送")
        send_btn.setFixedSize(60, 40)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
            QPushButton:pressed {
                background-color: #c73e54;
            }
            QPushButton:disabled {
                background-color: #2d3561;
                color: #6b6b8a;
            }
        """)
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)
        
        container_layout.addLayout(input_layout)
        
        main_layout.addWidget(container)
        
    def _send_message(self):
        """发送消息"""
        text = self.input_field.text().strip()
        if not text:
            return
            
        # 清空输入框
        self.input_field.clear()
        
        # 添加用户消息
        self._add_user_message(text)
        
        # 发送给LLM
        self._send_to_llm(text)
        
    def _add_user_message(self, text: str):
        """添加用户消息"""
        # 创建消息行布局
        row = QHBoxLayout()
        row.addStretch()

        bubble = MessageBubble(text, is_user=True)
        # 设置气泡大小策略
        bubble.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        row.addWidget(bubble)

        self.messages_layout.addLayout(row)
        self.message_bubbles.append(bubble)

        # 立即适配新加入气泡的宽度
        try:
            self._adapt_bubble_width(bubble)
        except Exception:
            pass

        # 滚动到底部
        self._scroll_to_bottom()
        
    def _add_ai_message(self, text: str = ""):
        """添加AI消息"""
        # 创建消息行布局
        row = QHBoxLayout()

        self.current_ai_bubble = MessageBubble(text, is_user=False)
        # 设置AI消息气泡的大小策略
        self.current_ai_bubble.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )
        # AI消息靠左，但让气泡可以扩展
        row.addWidget(self.current_ai_bubble)
        row.addStretch()

        self.messages_layout.addLayout(row)
        self.message_bubbles.append(self.current_ai_bubble)
        try:
            self._adapt_bubble_width(self.current_ai_bubble)
        except Exception:
            pass

        # 滚动到底部
        self._scroll_to_bottom()
        
    def _update_ai_message(self, text: str):
        """更新AI消息"""
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(text)
            try:
                # 文本变更后也尝试适配宽度
                self._adapt_bubble_width(self.current_ai_bubble)
            except Exception:
                pass
            self._scroll_to_bottom()

    def _adapt_bubble_width(self, bubble: MessageBubble):
        """根据当前消息区域宽度调整单个气泡内 label 的最大宽度。"""
        if not bubble:
            return

        # 聊天面板固定宽度为350，减去边距和滚动条
        # 容器边距: 16 * 2 = 32
        # 滚动条宽度: 6
        # 气泡内边距: 12 * 2 = 24
        # 总计边距: 32 + 6 + 24 = 62
        max_w = 350 - 62  # = 288

        if hasattr(bubble, 'label') and bubble.label is not None:
            bubble.label.setMaximumWidth(max_w)
            bubble.updateGeometry()
            
    def _send_to_llm(self, message: str):
        """发送消息给LLM"""
        # 检查是否有正在进行的对话
        if self.current_worker and self.current_worker.isRunning():
            logger.warning("有正在进行的对话，请等待完成")
            return
            
        # 创建AI消息气泡
        self._add_ai_message("思考中...")
        
        # 创建工作线程
        self.current_worker = ChatWorker(self.llm_client, message)
        self.current_worker.token_received.connect(self._on_token)
        self.current_worker.response_complete.connect(self._on_complete)
        self.current_worker.error_occurred.connect(self._on_error)
        
        # 启动线程
        self.current_worker.start()
        
    def _on_token(self, token: str):
        """接收到token"""
        # 更新AI消息
        current_text = self.current_ai_bubble.text
        if current_text == "思考中...":
            current_text = ""
        self._update_ai_message(current_text + token)
        
    def _on_complete(self, full_text: str):
        """响应完成"""
        logger.info("LLM响应完成")
        
        # 请求语音朗读
        if config.general.voice_feedback:
            self.voice_requested.emit(full_text)
            
    def _on_error(self, error: str):
        """发生错误"""
        logger.error(f"LLM错误: {error}")
        self._update_ai_message(f"错误: {error}")
        
    def _scroll_to_bottom(self):
        """滚动到底部"""
        QTimer.singleShot(10, lambda: 
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )
        )

    def resizeEvent(self, a0):
        """当面板大小变化时，调整所有消息气泡的布局"""
        try:
            # 调整所有消息气泡的布局
            for bubble in list(self.message_bubbles):
                try:
                    if hasattr(bubble, 'label'):
                        bubble.label.adjustSize()
                        bubble.updateGeometry()
                except Exception:
                    continue
        except Exception:
            pass

        return super().resizeEvent(a0)
        
    def clear_history(self):
        """清除历史消息"""
        # 清除UI
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # 清除布局中的子项
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                        
        self.message_bubbles.clear()
        self.current_ai_bubble = None
        
        # 清除LLM历史
        self.llm_client.clear_history()
        
        # 添加欢迎消息
        self._add_ai_message("历史已清除，让我们开始新的对话吧！")
        
    def add_system_message(self, text: str):
        """添加系统消息"""
        self._add_ai_message(text)
        
    def closeEvent(self, event):
        """关闭事件"""
        # 停止工作线程
        if self.current_worker and self.current_worker.isRunning():
            # 注意：无法安全终止线程，只能等待
            pass
        event.accept()
