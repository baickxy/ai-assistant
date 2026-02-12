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
from .system_tools import SystemTools, TOOL_FUNCTIONS

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

系统工具使用说明:
当用户询问时间、日期、系统信息、位置、天气等信息时，你必须使用以下系统工具:

重要提示：你必须在回复中直接使用 TOOL:SYSTEM 指令，不要只是描述它！

工具调用格式：
TOOL:SYSTEM {"function": "工具名称", "params": {"参数名": "参数值"}}

可用工具列表:
1. 获取时间: TOOL:SYSTEM {"function": "get_time", "params": {"format": "%H:%M:%S"}}
2. 获取日期: TOOL:SYSTEM {"function": "get_date"}
3. 获取系统信息: TOOL:SYSTEM {"function": "get_system_info"}
4. 获取网络信息: TOOL:SYSTEM {"function": "get_network_info"}
5. 获取位置: TOOL:SYSTEM {"function": "get_location"}
6. 获取天气: TOOL:SYSTEM {"function": "get_weather", "params": {"location": "城市名"}}
7. 执行命令: TOOL:SYSTEM {"function": "execute_command", "params": {"command": "命令"}}
8. 读取文件: TOOL:SYSTEM {"function": "read_file", "params": {"file_path": "文件路径"}}
9. 写入文件: TOOL:SYSTEM {"function": "write_file", "params": {"file_path": "文件路径", "content": "内容", "mode": "w"}}
10. 删除文件: TOOL:SYSTEM {"function": "delete_file", "params": {"file_path": "文件路径"}}
11. 列出目录: TOOL:SYSTEM {"function": "list_directory", "params": {"dir_path": "目录路径", "show_hidden": false}}

注意: 写入和删除C盘文件时需要用户确认。

使用示例:
用户: 现在几点了？
你的回复: TOOL:SYSTEM {"function": "get_time", "params": {"format": "%H:%M"}}

用户: 今天是什么日期？
你的回复: TOOL:SYSTEM {"function": "get_date"}

请记住：必须直接输出 TOOL:SYSTEM 指令，不要用引号包裹，不要加其他文字说明。

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

    def _post_with_retries(self, url: str, json_payload: dict, stream: bool = False, timeout: Optional[int] = None, max_retries: int = 3):
        """
        POST 请求带简单重试机制（用于处理短暂的 5xx 错误或连接抖动）
        返回 requests.Response 或抛出最后的异常
        """
        attempt = 0
        last_exc = None
        while attempt < max_retries:
            try:
                resp = requests.post(url, json=json_payload, stream=stream, timeout=timeout or self.timeout)
                # 如果是服务器错误(5xx)，记录并重试
                if 500 <= resp.status_code < 600:
                    logger.warning(f"Ollama 返回 5xx({resp.status_code})，重试 {attempt+1}/{max_retries}")
                    last_exc = requests.HTTPError(f"HTTP {resp.status_code}")
                    attempt += 1
                    continue

                resp.raise_for_status()
                return resp

            except requests.exceptions.RequestException as e:
                last_exc = e
                logger.warning(f"请求 Ollama 失败 (尝试 {attempt+1}/{max_retries}): {e}")
                attempt += 1

        # 所有尝试失败，抛出最后一个异常
        if last_exc:
            raise last_exc
        raise Exception("未知的请求失败")

    def _get_with_retries(self, url: str, timeout: Optional[int] = None, max_retries: int = 3):
        """
        GET 请求带简单重试机制，返回 requests.Response 或抛出最后异常
        """
        attempt = 0
        last_exc = None
        while attempt < max_retries:
            try:
                resp = requests.get(url, timeout=timeout or self.timeout)
                if 500 <= resp.status_code < 600:
                    logger.warning(f"Ollama 返回 5xx({resp.status_code})，重试 {attempt+1}/{max_retries}")
                    last_exc = requests.HTTPError(f"HTTP {resp.status_code}")
                    attempt += 1
                    continue

                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                last_exc = e
                logger.warning(f"请求 Ollama(GET) 失败 (尝试 {attempt+1}/{max_retries}): {e}")
                attempt += 1

        if last_exc:
            raise last_exc
        raise Exception("未知的GET请求失败")
        
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

    def _parse_tool_fetch(self, text: str) -> Optional[Dict[str, Any]]:
        """
        在模型返回文本中查找 TOOL:FETCH 指令并解析其后面的 JSON 参数。

        期望格式示例：
        TOOL:FETCH {"url": "https://example.com", "method": "GET"}

        Returns:
            dict: 解析后的参数字典，至少包含 url 字段；解析失败返回 None
        """
        import re

        if not text:
            return None

        # 尝试找到 "TOOL:FETCH" 后面紧跟一个 JSON 对象
        pattern = re.compile(r"TOOL:FETCH\s*(\{.*\})", re.DOTALL)
        m = pattern.search(text)
        if not m:
            return None

        json_text = m.group(1)
        try:
            params = json.loads(json_text)
            if isinstance(params, dict) and 'url' in params:
                return params
        except Exception:
            logger.warning("解析 TOOL:FETCH JSON 失败")
            return None

        return None

    def _parse_system_tool(self, text: str) -> Optional[Dict[str, Any]]:
        """
        在模型返回文本中查找 TOOL:SYSTEM 指令并解析其后面的 JSON 参数。

        期望格式示例：
        TOOL:SYSTEM {"function": "get_time", "params": {"format": "%Y-%m-%d %H:%M:%S"}}

        Returns:
            dict: 解析后的参数字典，至少包含 function 字段；解析失败返回 None
        """
        import re

        if not text:
            return None

        # 尝试找到 "TOOL:SYSTEM" 后面紧跟一个 JSON 对象
        pattern = re.compile(r"TOOL:SYSTEM\s*(\{.*\})", re.DOTALL)
        m = pattern.search(text)
        if not m:
            return None

        json_text = m.group(1)
        try:
            params = json.loads(json_text)
            if isinstance(params, dict) and 'function' in params:
                return params
        except Exception:
            logger.warning("解析 TOOL:SYSTEM JSON 失败")
            return None

        return None

    def _execute_system_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行系统工具调用

        Args:
            params: 参数字典，必须包含 function 字段，可选包含 params 字段

        Returns:
            dict: 工具执行结果
        """
        function_name = params.get('function')
        if not function_name:
            return {
                "success": False,
                "error": "缺少 function 参数"
            }

        if function_name not in TOOL_FUNCTIONS:
            return {
                "success": False,
                "error": f"未知的工具函数: {function_name}"
            }

        tool_params = params.get('params', {})
        try:
            # 执行工具函数
            result = TOOL_FUNCTIONS[function_name](**tool_params)

            # 检查是否需要用户确认（C盘文件操作）
            if isinstance(result, dict) and result.get('requires_confirmation'):
                logger.warning(f"系统工具 {function_name} 需要用户确认: {result.get('error')}")
                # 返回需要确认的信息，让上层处理
                return result

            logger.info(f"系统工具 {function_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"执行系统工具 {function_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _perform_fetch(self, params: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        执行受控的网络请求。仅在配置允许时执行。

        params 支持字段: url, method, headers, body
        返回结果字典: {status_code, headers, body}
        """
        if not bool(getattr(config.ollama, 'allow_network', False)):
            raise PermissionError("网络访问被禁用 (config.ollama.allow_network=False)")

        url = params.get('url')
        if not url:
            raise ValueError('fetch 参数中缺少 url')
        url = str(url)
        method = (params.get('method') or 'GET').upper()
        headers = params.get('headers') or {}
        body = params.get('body')

        try:
            if method == 'GET':
                resp = requests.get(url, headers=headers, timeout=timeout or self.timeout)
            elif method == 'POST':
                resp = requests.post(url, headers=headers, json=body, timeout=timeout or self.timeout)
            else:
                # 支持基本方法，其他方法使用 generic request
                resp = requests.request(method, url, headers=headers, data=body, timeout=timeout or self.timeout)

            # 尝试解析文本体（文本优先）
            content_type = resp.headers.get('Content-Type', '')
            body_text = None
            try:
                # 尝试 json
                if 'application/json' in content_type:
                    body_text = json.dumps(resp.json(), ensure_ascii=False)
                else:
                    body_text = resp.text
            except Exception:
                body_text = resp.text or ''

            return {
                'status_code': resp.status_code,
                'headers': dict(resp.headers),
                'body': body_text,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"执行 fetch 失败: {e}")
            raise

    def chat_with_tools(
        self,
        message: str,
        stream: bool = False,
        max_tool_iterations: Optional[int] = None,
        fetch_timeout: Optional[int] = None,
    ) -> str:
        """
        与模型对话，同时支持模型通过 TOOL:FETCH 发起受控网络请求，
        以及通过 TOOL:SYSTEM 调用系统工具。

        流程:
        1. 发送用户消息并获取模型回复
        2. 如果回复包含 TOOL:FETCH 指令，且配置允许（config.ollama.allow_network），则执行请求
        3. 如果回复包含 TOOL:SYSTEM 指令，且配置允许（config.ollama.allow_system_tools），则执行系统工具调用
        4. 将请求结果作为新的用户消息回传给模型，继续生成
        5. 重复直到模型不再请求工具或达到迭代上限

        返回最终模型文本（字符串）。
        """
        if not message:
            return ''

        # 使用配置中的最大迭代次数（如果未提供）
        if max_tool_iterations is None:
            max_tool_iterations = getattr(config.ollama, 'max_tool_iterations', 3)

        # 检查是否允许使用系统工具
        allow_system_tools = bool(getattr(config.ollama, 'allow_system_tools', True))

        # 首次调用：添加用户消息并请求模型
        current_user_message = message
        final_reply = ''

        for iteration in range(max_tool_iterations + 1):
            # 使用非流式获取完整回复，方便检测工具调用
            try:
                replies = list(self.chat(current_user_message, stream=False))
            except Exception as e:
                logger.error(f"chat 调用失败: {e}")
                return f"错误: {e}"

            if not replies:
                return ''

            assistant_reply = ''.join(replies)
            final_reply = assistant_reply

            # 检查是否包含 TOOL:SYSTEM 指令（优先检查系统工具）
            system_tool_params = self._parse_system_tool(assistant_reply)
            if system_tool_params:
                # 发现系统工具调用
                logger.info(f"检测到 TOOL:SYSTEM，参数: {system_tool_params}")

                # 检查是否允许使用系统工具
                if not allow_system_tools:
                    logger.warning("配置中禁止系统工具调用，跳过 TOOL:SYSTEM 执行")
                    # 将这一信息追加到回复并结束
                    return final_reply + "\n\n[系统工具调用被禁止：请在设置中启用 allow_system_tools]"

                try:
                    system_tool_result = self._execute_system_tool(system_tool_params)
                except Exception as e:
                    # 将错误作为工具结果回传给模型，继续下一轮
                    tool_message = json.dumps({'tool': 'system', 'error': str(e)}, ensure_ascii=False)
                    logger.info(f"系统工具执行失败，作为工具结果回传: {tool_message}")
                    current_user_message = f"[TOOL_RESULT] {tool_message}"
                    continue

                # 构造工具结果消息并作为用户消息追加
                tool_message = json.dumps({
                    'tool': 'system',
                    'function': system_tool_params.get('function'),
                    'result': system_tool_result
                }, ensure_ascii=False)
                logger.debug(f"将系统工具结果回传给模型: {tool_message[:200]}")

                current_user_message = f"[TOOL_RESULT] {tool_message}"
                # 继续下一次循环以让模型基于工具结果生成新的回复
                continue

            # 检查是否包含 TOOL:FETCH 指令
            tool_params = self._parse_tool_fetch(assistant_reply)
            if not tool_params:
                # 没有工具调用，结束
                return final_reply

            # 发现工具调用，执行受控 fetch
            logger.info(f"检测到 TOOL:FETCH，参数: {tool_params}")

            if not bool(getattr(config.ollama, 'allow_network', False)):
                logger.warning("配置中禁止网络访问，跳过 TOOL:FETCH 执行")
                # 将这一信息追加到回复并结束
                return final_reply + "\n\n[工具调用被禁止：请在设置中启用 allow_network]"

            try:
                fetch_result = self._perform_fetch(tool_params, timeout=fetch_timeout)
            except Exception as e:
                # 将错误作为工具结果回传给模型，继续下一轮
                tool_message = json.dumps({'tool': 'fetch', 'error': str(e)}, ensure_ascii=False)
                logger.info(f"fetch 失败，作为工具结果回传: {tool_message}")
                current_user_message = f"[TOOL_RESULT] {tool_message}"
                # loop to continue
                continue

            # 构造工具结果消息并作为用户消息追加
            body_text = fetch_result.get('body') or ''
            if not isinstance(body_text, str):
                try:
                    body_text = str(body_text)
                except Exception:
                    body_text = ''

            safe_result = {
                'tool': 'fetch',
                'url': str(tool_params.get('url')),
                'status_code': fetch_result.get('status_code'),
                'body': body_text[:4000],
            }

            tool_message = json.dumps(safe_result, ensure_ascii=False)
            logger.debug(f"将工具结果回传给模型: {tool_message[:200]}")

            current_user_message = f"[TOOL_RESULT] {tool_message}"

            # 继续下一次循环以让模型基于工具结果生成新的回复

        # 达到迭代上限，返回当前回复并提示
        return final_reply + "\n\n[工具迭代达到上限]"
        
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
                'num_predict': self.max_tokens,
                'allow_network': bool(getattr(config.ollama, 'allow_network', False))
            }
        }
        
        full_response = []
        
        try:
            logger.info(f"发送请求到Ollama: {message[:50]}...")
            
            # 使用带重试的 POST 请求
            try:
                logger.debug(f"Ollama 请求 payload options: {payload.get('options')}")
                response = self._post_with_retries(url, payload, stream=stream, timeout=self.timeout)
            except Exception as e:
                error_msg = f"请求错误: {str(e)}"
                logger.error(error_msg)
                yield f"错误: {error_msg}"
                return
            
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
                try:
                    data = response.json()
                    if 'message' in data:
                        content = data['message']['content']
                        full_response.append(content)
                        yield content
                except Exception:
                    logger.exception("解析非流式响应失败")
                    yield f"错误: 无法解析响应"
                    return
                    
        except requests.exceptions.ConnectionError:
            error_msg = "无法连接到Ollama服务，请确保Ollama已启动"
            logger.error(error_msg)
            yield f"错误: {error_msg}"

        except requests.exceptions.Timeout:
            error_msg = "请求超时，请检查Ollama服务状态"
            logger.error(error_msg)
            yield f"错误: {error_msg}"

        except Exception as e:
            # 捕获并返回更友好的信息，便于 UI 显示
            error_msg = f"请求错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
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
                'num_predict': self.max_tokens,
                'allow_network': bool(getattr(config.ollama, 'allow_network', False))
            }
        }
        
        if system:
            payload['system'] = system
            
        try:
            try:
                logger.debug(f"Ollama 请求 payload options: {payload.get('options')}")
                response = self._post_with_retries(url, payload, stream=stream, timeout=self.timeout)
            except Exception as e:
                logger.error(f"生成请求失败: {e}")
                yield f"错误: {str(e)}"
                return

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
            try:
                response = self._get_with_retries(f"{self.host}/api/tags", timeout=5)
            except Exception as e:
                logger.error(f"获取模型列表失败: {e}")
                return []

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
            response = self._post_with_retries(url, payload, stream=True, timeout=300)

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
            try:
                response = self._get_with_retries(f"{self.host}/api/tags", timeout=3)
                return response.status_code == 200
            except Exception:
                return False
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
