"""辩论核心逻辑 — 供后端 API 调用。"""

import os
from typing import Generator

from openai import OpenAI

# ── API 配置（可通过环境变量覆盖）────────────────────────────────────────────
PRO_BASE_URL = os.getenv("PRO_BASE_URL", "https://api.deepseek.com")
PRO_API_KEY = os.getenv("PRO_API_KEY", "sk-30714e448c3c4e248c3f4640075e952a")

CON_BASE_URL = os.getenv("CON_BASE_URL", "https://api.deepseek.com")
CON_API_KEY = os.getenv("CON_API_KEY", "sk-30714e448c3c4e248c3f4640075e952a")

REFEREE_BASE_URL = os.getenv("REFEREE_BASE_URL", "https://api.deepseek.com")
REFEREE_API_KEY = os.getenv("REFEREE_API_KEY", "sk-30714e448c3c4e248c3f4640075e952a")

MODEL_OPTIONS = {
    "DeepSeek-V4": "deepseek-chat",
    "别的ai买不起(勿选)": ""
}

TOTAL_ROUNDS = 4

PRO_SYSTEM_PROMPT = (
    "你是一位学识渊博、理性客观的思辨大师，坚定持有【正方】立场。"
    "你的目标不是口舌抬杠，而是通过严密的逻辑、扎实的数据，穷尽正方最具说服力的核心论据。"
    "必须使用强人原则（Steel-maning），认真反驳反方最理性的那一点。"
    "字数控制在 200-300 字，语气保持冷静、高级、雄辩。"
)

CON_SYSTEM_PROMPT = (
    "你是一位学识渊博、理性客观的思辨大师，坚定持有【反方】立场。"
    "你的目标不是口舌抬杠，而是通过严密的逻辑、扎实的数据，穷尽反方最具说服力的核心论据，"
    "指出正方立论的深层盲区与潜在风险。"
    "必须使用强人原则（Steel-maning），认真反驳正方最理性的那一点。"
    "字数控制在 200-300 字，语气保持冷静、高级、雄辩。"
)

REFEREE_SYSTEM_PROMPT = (
    "你是一位精通形式逻辑与公共政策的大法官。请仔细阅读正反两方的完整辩论记录。"
    "你的职责是作出严肃、可辩护的胜负裁决，而非和稀泥或充当和事佬。"
    "你必须在正方与反方中择一宣布获胜，依据是其论证在逻辑严密性、证据支撑、"
    "对辩题的回应度以及对对方最强论点的有效反驳上整体更站得住脚。"
    "禁止输出「双方都有道理」「难分高下」等回避性结论；若势均力敌，"
    "须指出决定性的一两条论据并据此判胜。"
    "请严格按以下 Markdown 结构输出："
    "1. 核心交锋点拆解（本场辩论的底层冲突与胜负关键）；"
    "2. 正方逻辑解剖（最强论点、薄弱环节与失分之处）；"
    "3. 反方逻辑解剖（最强论点、薄弱环节与失分之处）；"
    "4. 胜负裁决（明确写出「本场胜方：正方/反方」，并逐条说明判胜理由）；"
    "5. 客观总结（200 字以内，冷静概括整场辩论与终审结论，不煽情、不和稀泥）。"
)


def get_client(base_url: str, api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def format_history_text(history: list, topic: str) -> str:
    lines = [f"【辩题】{topic}", ""]
    for entry in history:
        label = "正方" if entry["role"] == "pro" else "反方"
        rnd = entry.get("round", "?")
        lines.append(f"【{label} · 第{rnd}轮】")
        lines.append(entry["content"])
        lines.append("")
    return "\n".join(lines)


def build_user_message(role: str, topic: str, history: list, round_num: int) -> str:
    if round_num == 1 and role == "pro":
        return f"【辩题】{topic}\n\n请作为正方，进行第 1 轮开篇陈述，亮出核心立论。"

    if round_num == 1 and role == "con":
        pro_first = next(h["content"] for h in history if h["role"] == "pro")
        return (
            f"【辩题】{topic}\n\n"
            f"【正方 · 第 1 轮发言】\n{pro_first}\n\n"
            f"请作为反方，针对正方开篇立论进行第 1 轮反驳。"
        )

    opponent_role = "con" if role == "pro" else "pro"
    opponent_label = "反方" if opponent_role == "con" else "正方"
    opponent_msgs = [h for h in history if h["role"] == opponent_role]
    latest_opponent = opponent_msgs[-1]["content"] if opponent_msgs else ""

    history_text = format_history_text(history, topic)
    self_label = "正方" if role == "pro" else "反方"

    return (
        f"{history_text}\n"
        f"【{opponent_label} · 最新发言】\n{latest_opponent}\n\n"
        f"请作为{self_label}，进行第 {round_num} 轮发言。"
        f"必须直接回应对方最新论点中最有力的那一点，不得回避或自说自话。"
    )


def stream_completion(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_message: str,
) -> Generator[str, None, None]:
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        stream=True,
        temperature=0.7,
    )
    full = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            full += delta
            yield full


def run_debate_stream(
    topic: str,
    pro_model_key: str,
    con_model_key: str,
) -> Generator[dict, None, None]:
    """生成辩论事件流，供 SSE 推送。"""
    pro_client = get_client(PRO_BASE_URL, PRO_API_KEY)
    con_client = get_client(CON_BASE_URL, CON_API_KEY)
    referee_client = get_client(REFEREE_BASE_URL, REFEREE_API_KEY)

    pro_model = MODEL_OPTIONS[pro_model_key]
    con_model = MODEL_OPTIONS[con_model_key]
    referee_model = MODEL_OPTIONS[list(MODEL_OPTIONS.keys())[0]]

    history: list = []

    for round_num in range(1, TOTAL_ROUNDS + 1):
        for role, client, model, system_prompt in [
            ("pro", pro_client, pro_model, PRO_SYSTEM_PROMPT),
            ("con", con_client, con_model, CON_SYSTEM_PROMPT),
        ]:
            user_msg = build_user_message(role, topic, history, round_num)
            yield {"type": "speech_start", "role": role, "round": round_num}

            full_text = ""
            for partial in stream_completion(client, model, system_prompt, user_msg):
                full_text = partial
                yield {
                    "type": "speech_delta",
                    "role": role,
                    "round": round_num,
                    "content": full_text,
                }

            history.append({"role": role, "content": full_text, "round": round_num})
            yield {
                "type": "speech_end",
                "role": role,
                "round": round_num,
                "content": full_text,
            }

    yield {"type": "referee_start"}

    referee_input = (
        f"【辩题】{topic}\n\n"
        f"【完整辩论记录】\n{format_history_text(history, topic)}\n\n"
        "请基于以上完整记录，撰写《思辨终审报告》，必须明确判定正方或反方获胜。"
    )

    report = ""
    stream = referee_client.chat.completions.create(
        model=referee_model,
        messages=[
            {"role": "system", "content": REFEREE_SYSTEM_PROMPT},
            {"role": "user", "content": referee_input},
        ],
        stream=True,
        temperature=0.5,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            report += delta
            yield {"type": "referee_delta", "content": report}

    yield {"type": "referee_end", "content": report, "history": history}
    yield {"type": "done"}
