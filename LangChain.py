import os
from datetime import datetime
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage


#  配置环境,生成输出文件路径
load_dotenv()

if not os.getenv("DEEPSEEK_API_KEY"):
    raise ValueError("请在 .env 文件中添加 DEEPSEEK_API_KEY")

output_dir = "outputs"
os.makedirs(output_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = os.path.join(output_dir, f"deepseek_v1_output_{timestamp}.txt")


#  初始化 Model (LangChain v1 推荐方式)
# 指定 output_version="v1" 以使用标准的 content_blocks
model = init_chat_model(
    "deepseek-chat",
    model_provider="openai",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    temperature=0.7,
    output_version="v1"
)

def parse_ai_content(message: AIMessage) -> str:
    """【进化点：自动格式解读】
    自动从复杂的 content_blocks 中提取纯文本，过滤掉思考过程或工具调用。
    """
    if isinstance(message.content, str):
        return message.content
    # 提取所有文本块并拼接
    return "".join(
        block.get("text", "")
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    )

def write_novel_workflow(prompt: str):
    """【进化点：写作工作流】
    成熟的 Agent 不会直接盲目写 4000 字，而是分为：构思大纲 -> 逐章细化。
    """
    # 步骤 A: 生成大纲
    print("🎨 正在构思小说大纲...")
    outline_msg = [
        SystemMessage("你是一个资深网文架构师，擅长科幻与玄幻结合。"),
        HumanMessage(f"请为以下需求写一个包含5个章节的大纲：{prompt}")
    ]
    outline_res = model.invoke(outline_msg)
    outline_text = parse_ai_content(outline_res)

    full_novel = [f"【大纲】\n{outline_text}\n\n" + "="*20 + "\n"]

    # 步骤 B: 逐章扩写 (模拟成熟 Agent 的分段处理)
    # 这里简单演示扩写第一章，实际应用中可用循环
    print("✍️ 正在直接根据指令开始正文创作...")
    writing_msg = [
        SystemMessage("你是一个优秀的网文作家，直接开始正文，不要废话，不要反问。"),
        HumanMessage(f"根据这个需求：{prompt}。请直接开始创作第一章，字数要详实，细节要丰富。")
    ]
    content_res = model.invoke(writing_msg)
    chapter_text = parse_ai_content(content_res)
    full_novel.append(chapter_text)

    return "\n".join(full_novel), content_res.usage_metadata

#  定义工具 (使用标准装饰器)
def get_current_time(location: str) -> str:
    """获取指定位置的当前时间。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 将工具绑定到模型
model_with_tools = model.bind_tools([get_current_time])


#  构建消息序列并执行
if __name__ == "__main__":
    user_prompt = "你是一个小说创作助手。请帮我写一段关于小说创作的创意文本，包含玄幻元素，直接开始创作，不要进行开场白或反问。"

    # 按照文档推荐，使用 Message 对象列表
    messages = [
        SystemMessage("你是一个精通科幻创作的资深作家，语气要优雅且富有想象力。"),
        HumanMessage(user_prompt)
    ]

    # 调用模型
    response = model_with_tools.invoke(messages)

    # 检查是否有工具调用 (Tool Calls)
    # 如果模型决定调用工具，处理逻辑如下：
    if response.tool_calls:
        for tool_call in response.tool_calls:
            # 模拟执行工具
            result = get_current_time(tool_call["args"].get("location", "Unknown"))
            # 将工具结果反馈给模型
            messages.append(response)
            messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
            # 再次调用模型获取最终文案
            response = model_with_tools.invoke(messages)


    #  结果持久化与元数据提取

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"=== [Timestamp: {timestamp}] ===\n")
        f.write(f"User Prompt: {user_prompt}\n\n")
        f.write(f"AI Content:\n{response.content}\n\n")

        # 利用 v1 提供的 usage_metadata
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            f.write(f"--- Token Usage ---\n")
            f.write(f"Total Tokens: {usage.get('total_tokens')}\n")
            f.write(f"Input Tokens: {usage.get('input_tokens')}\n")
            f.write(f"Output Tokens: {usage.get('output_tokens')}\n")

    print(f"✨ 创作完成！结果已存至: {output_file}")
    print(f"📊 消耗总 Token: {response.usage_metadata.get('total_tokens')}")