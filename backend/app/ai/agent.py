"""AI 助手编排层：DeepSeek function-calling + 流式输出"""
import json

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from .metrics import TOOLS, run_tool

SYSTEM_PROMPT = (
    "你是 LM 订单管理系统的 AI 助手「小护卫」。"
    "你的职责是用「问答」方式帮用户查数据、看经营情况。"
    "规则：\n"
    "1. 所有数字都必须通过调用工具（function）得到，禁止自己编造任何金额、数量、日期。\n"
    "2. 用户问数据类问题时，判断意图并调用最合适的工具，参数用工具 schema 规定的字段。\n"
    "3. 得到工具返回的表格数据后，用 1~3 句简洁中文做总结，引用最关键的数字，并说明口径与数据来源。\n"
    "4. 禁止输出 markdown 表格（数据已以卡片表格展示）；不要用 | 符号画表。\n"
    "5. 不要输出任何 SQL，不要声称能执行写操作；涉及「分数据/提单/收工」等写操作时，说明当前版本仅支持查询。\n"
    "6. 涉及手机号等敏感信息时，注意已脱敏。\n"
)


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    if not DEEPSEEK_API_KEY:
        return None
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def available():
    try:
        import openai  # noqa
    except ImportError:
        return False
    return bool(DEEPSEEK_API_KEY)


def _chat_tools(client, messages, model):
    resp = client.chat.completions.create(
        model=model, messages=messages, tools=TOOLS, temperature=0.1)
    return resp.choices[0].message


def _stream_text(client, messages, model):
    stream = client.chat.completions.create(model=model, messages=messages, temperature=0.4, stream=True)
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def chat_stream(db, history, message):
    """生成器，产出事件 dict：{type: token|card|tool|done|error, data: ...}"""
    client = _client()
    if client is None:
        yield {"type": "text", "data": "AI 助手未配置：请在后端设置 DEEPSEEK_API_KEY 环境变量后重启。"}
        yield {"type": "done", "data": {}}
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history) + [
        {"role": "user", "content": message}]

    try:
        msg = _chat_tools(client, messages, DEEPSEEK_MODEL)
    except Exception as e:  # noqa
        yield {"type": "error", "data": f"模型调用失败：{e}"}
        yield {"type": "done", "data": {}}
        return

    # 无工具调用：直接流式回答
    if not msg.tool_calls:
        text = ""
        try:
            for tok in _stream_text(client, messages, DEEPSEEK_MODEL):
                text += tok
                yield {"type": "token", "data": tok}
        except Exception as e:  # noqa
            yield {"type": "error", "data": f"流式回答失败：{e}"}
        yield {"type": "done", "data": {"summary": text}}
        return

    tool_call = msg.tool_calls[0]
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except Exception:
        args = {}
    card = run_tool(db, name, args)
    yield {"type": "card", "data": card}
    yield {"type": "tool", "data": {"tool": name, "args": args}}

    summary_msgs = messages + [
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": tool_call.id, "type": "function",
             "function": {"name": name, "arguments": tool_call.function.arguments or "{}"}}]},
        {"role": "tool", "tool_call_id": tool_call.id,
         "content": json.dumps(card, ensure_ascii=False, default=str)},
    ]
    text = ""
    try:
        for tok in _stream_text(client, summary_msgs, DEEPSEEK_MODEL):
            text += tok
            yield {"type": "token", "data": tok}
    except Exception as e:  # noqa
        yield {"type": "error", "data": f"总结生成失败：{e}"}
    yield {"type": "done", "data": {"summary": text, "tool": name, "args": args, "card": card}}
