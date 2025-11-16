"""
简化版测试应用 - 只测试 Gradio UI 和 Gemini LLM 连接
不依赖数据库，直接测试 LLM 交互
"""

import os
import logging
import gradio as gr
from dotenv import load_dotenv
import google.generativeai as genai

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置 Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_api_key_here":
    logger.error("请在 .env 文件中设置有效的 GEMINI_API_KEY")
    raise ValueError("GEMINI_API_KEY 未配置")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_CHAT_MODEL)

logger.info(f"✓ Gemini API 已配置，使用模型: {GEMINI_CHAT_MODEL}")


def chat_with_gemini(message, history):
    """
    与 Gemini 聊天的简单函数
    
    Args:
        message: 用户输入的消息
        history: 聊天历史（Gradio 格式）
    
    Returns:
        str: Gemini 的回复
    """
    if not message or not message.strip():
        return "请输入一个问题。"
    
    try:
        logger.info(f"发送问题到 Gemini: {message[:50]}...")
        
        # 调用 Gemini API
        response = model.generate_content(message)
        answer = response.text
        
        logger.info(f"✓ 收到 Gemini 回复 (长度: {len(answer)})")
        return answer
        
    except Exception as e:
        error_msg = f"❌ 错误: {str(e)}"
        logger.error(f"Gemini API 调用失败: {str(e)}", exc_info=True)
        return error_msg


# 构建 Gradio 界面
with gr.Blocks(title="Gemini LLM 测试") as app:
    gr.Markdown("# 🤖 Gemini LLM 连接测试")
    gr.Markdown("这是一个简化版本，用于测试 Gradio UI 和 Gemini API 连接。")
    
    # 聊天界面
    chatbot = gr.Chatbot(
        label="对话",
        height=500
    )
    
    # 输入框和发送按钮
    with gr.Row():
        msg_input = gr.Textbox(
            label="输入消息",
            placeholder="在这里输入你的问题...",
            lines=2,
            scale=4
        )
        send_btn = gr.Button("发送", variant="primary", scale=1)
    
    # 清除按钮
    clear_btn = gr.Button("清除对话")
    
    # 事件处理
    def respond(message, chat_history):
        """处理用户消息并更新聊天历史"""
        if not message.strip():
            return "", chat_history
        
        # 获取 AI 回复
        bot_response = chat_with_gemini(message, chat_history)
        
        # 添加对话到历史（使用列表格式：[用户消息, AI回复]）
        chat_history.append([message, bot_response])
        
        return "", chat_history
    
    # 绑定事件
    send_btn.click(respond, [msg_input, chatbot], [msg_input, chatbot])
    msg_input.submit(respond, [msg_input, chatbot], [msg_input, chatbot])
    clear_btn.click(lambda: [], None, chatbot)


if __name__ == "__main__":
    logger.info("启动 Gemini LLM 测试应用...")
    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False
    )
