"""
Ollama LLM客户端模块
与本地Ollama服务通信，提供AI对话能力
"""

import logging
import json
import requests
from typing import Optional, Callable, Iterator, Dict, Any, List
from dataclasses import dataclass
from threading import Thread
from queue import Queue

from config import config

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """消息"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    timestamp: Optional[float] = None


@dataclass
class ChatResponse:
    """聊天响应"""
    content: str
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """Ollama客户端"""
    
    def __init__(self):
        self.host = config.ollama.host
        self.model = config.ollama.model
        self.temperature = config.ollama.temperature
        self.max_tokens = config.ollama.max_tokens
        self.timeout = config.ollama.timeout
        
        # 对话历史
        self.conversation_history: List[Message] = []
        self.max_history = 20
        
        # 系统提示词
        self.system_prompt = """你是一个友好的AI助手，名叫"小助手"。
你的特点:
1. 回答简洁明了，通常不超过3句话
2. 语气友好亲切
3. 如果不确定，会诚实地说不知道
4. 可以用中文或英文交流

请用简短友好的方式回答用户的问题。"""
        
        # 添加系统消息
        self._add_message('system', self.system_prompt)
        
        # 请求队列
        self.request_queue = Queue()
        self.response_callbacks: Dict[str, Callable] = {}
        
        # 启动处理线程
        self.processing_thread = Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        
        logger.info(f"Ollama客户端初始化完成，模型: {self.model}")
        
    def _add_message(self, role: str, content: str):
        """
        添加消息到历史
        
        Args:
            role: 角色
            content: 内容
        """
        import time
        msg = Message(role=role, content=content, timestamp=time.time())
        self.conversation_history.append(msg)
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history:
            # 保留系统消息和最近的对话
            system_msgs = [m for m in self.conversation_history if m.role == 'system']
            other_msgs = [m for m in self.conversation_history if m.role != 'system']
            other_msgs = other_msgs[-(self.max_history - len(system_msgs)):]
            self.conversation_history = system_msgs + other_msgs
            
    def _build_messages(self) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Returns:
            消息字典列表
        """
        return [
            {'role': msg.role, 'content': msg.content}
            for msg in self.conversation_history
        ]
        
    def chat(
        self, 
        message: str, 
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None
    ) -> Iterator[str]:
        """
        发送聊天消息
        
        Args:
            message: 用户消息
            stream: 是否流式响应
            on_token: 每个token的回调
            on_complete: 完成回调
            
        Yields:
            响应文本片段
        """
        # 添加用户消息
        self._add_message('user', message)
        
        # 构建请求
        url = f"{self.host}/api/chat"
        payload = {
            'model': self.model,
            'messages': self._build_messages(),
            'stream': stream,
            'options': {
                'temperature': self.temperature,
                'num_predict': self.max_tokens
            }
        }
        
        full_response = []
        
        try:
            logger.info(f"发送请求到Ollama: {message[:50]}...")
            
            response = requests.post(
                url,
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                # 流式处理响应
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line)
                        
                        if 'message' in data and 'content' in data['message']:
                            token = data['message']['content']
                            full_response.append(token)
                            
                            if on_token:
                                on_token(token)
                                
                            yield token
                            
                        if data.get('done'):
                            # 记录统计信息
                            if 'total_duration' in data:
                                logger.info(f"生成完成，总耗时: {data['total_duration']/1e9:.2f}s")
                                
                    except json.JSONDecodeError:
                        logger.warning(f"无法解析响应: {line}")
                        continue
            else:
                # 非流式响应
                data = response.json()
                if 'message' in data:
                    content = data['message']['content']
                    full_response.append(content)
                    yield content
                    
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到Ollama服务，请确保Ollama已启动"
            logger.error(error_msg)
            yield f"错误: {error_msg}"
            
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查Ollama服务状态"
            logger.error(error_msg)
            yield f"错误: {error_msg}"
            
        except Exception as e:
            error_msg = f"请求错误: {str(e)}"
            logger.error(error_msg)
            yield f"错误: {error_msg}"
            
        finally:
            # 保存AI回复到历史
            full_text = ''.join(full_response)
            if full_text and not full_text.startswith('错误:'):
                self._add_message('assistant', full_text)
                
            if on_complete:
                on_complete(full_text)
                
    def chat_async(
        self,
        message: str,
        on_token: Callable[[str], None],
        on_complete: Optional[Callable[[str], None]] = None
    ):
        """
        异步发送聊天消息
        
        Args:
            message: 用户消息
            on_token: 每个token的回调
            on_complete: 完成回调
        """
        def _chat_worker():
            full_response = []
            for token in self.chat(message, stream=True):
                full_response.append(token)
                on_token(token)
                
            if on_complete:
                on_complete(''.join(full_response))
                
        thread = Thread(target=_chat_worker, daemon=True)
        thread.start()
        
    def _process_queue(self):
        """处理请求队列"""
        while True:
            try:
                item = self.request_queue.get()
                if item is None:
                    break
                    
                message, callback = item
                full_response = []
                
                for token in self.chat(message, stream=True):
                    full_response.append(token)
                    
                if callback:
                    callback(''.join(full_response))
                    
            except Exception as e:
                logger.error(f"队列处理错误: {e}")
                
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        stream: bool = True
    ) -> Iterator[str]:
        """
        使用generate API生成文本
        
        Args:
            prompt: 提示词
            system: 系统提示词
            stream: 是否流式响应
            
        Yields:
            生成的文本片段
        """
        url = f"{self.host}/api/generate"
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': stream,
            'options': {
                'temperature': self.temperature,
                'num_predict': self.max_tokens
            }
        }
        
        if system:
            payload['system'] = system
            
        try:
            response = requests.post(
                url,
                json=payload,
                stream=stream,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            yield data['response']
                    except json.JSONDecodeError:
                        continue
            else:
                data = response.json()
                if 'response' in data:
                    yield data['response']
                    
        except Exception as e:
            logger.error(f"生成错误: {e}")
            yield f"错误: {str(e)}"
            
    def list_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            模型名称列表
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return models
            
        except Exception as e:
            logger.error(f"获取模型列表失败: {e}")
            return []
            
    def pull_model(self, model_name: str) -> Iterator[str]:
        """
        拉取模型
        
        Args:
            model_name: 模型名称
            
        Yields:
            进度信息
        """
        url = f"{self.host}/api/pull"
        payload = {'name': model_name, 'stream': True}
        
        try:
            response = requests.post(
                url,
                json=payload,
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get('status', '')
                        
                        if 'completed' in data:
                            yield f"{status}: {data['completed']}/{data['total']}"
                        else:
                            yield status
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"拉取模型错误: {e}")
            yield f"错误: {str(e)}"
            
    def is_available(self) -> bool:
        """
        检查Ollama服务是否可用
        
        Returns:
            是否可用
        """
        try:
            response = requests.get(
                f"{self.host}/api/tags",
                timeout=3
            )
            return response.status_code == 200
        except Exception:
            return False
            
    def clear_history(self):
        """清除对话历史"""
        # 保留系统消息
        system_msgs = [m for m in self.conversation_history if m.role == 'system']
        self.conversation_history = system_msgs
        logger.info("对话历史已清除")
        
    def set_model(self, model_name: str):
        """
        设置使用的模型
        
        Args:
            model_name: 模型名称
        """
        self.model = model_name
        config.ollama.model = model_name
        config.save()
        logger.info(f"模型设置为: {model_name}")
        
    def set_temperature(self, temperature: float):
        """
        设置温度参数
        
        Args:
            temperature: 温度 (0.0 - 2.0)
        """
        self.temperature = max(0.0, min(2.0, temperature))
        config.ollama.temperature = self.temperature
        config.save()
        logger.info(f"温度设置为: {self.temperature}")
        
    def set_system_prompt(self, prompt: str):
        """
        设置系统提示词
        
        Args:
            prompt: 提示词
        """
        self.system_prompt = prompt
        
        # 更新历史中的系统消息
        for msg in self.conversation_history:
            if msg.role == 'system':
                msg.content = prompt
                break
        else:
            self._add_message('system', prompt)
            
        logger.info("系统提示词已更新")
