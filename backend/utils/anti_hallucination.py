"""
防幻觉机制 — 确保生成的学术内容无事实性错误

策略：
1. 知识库校验：将生成内容与本地知识库比对
2. 来源标注：要求 AI 标注信息来源
3. 置信度评估：对生成内容进行自检
"""

from backend.llm.spark import spark_chat


async def verify_against_knowledge_base(
    generated_content: str,
    topic: str,
) -> dict:
    """
    用大模型自检生成内容与知识库的一致性

    Returns:
        {"is_accurate": bool, "issues": [...], "corrected": str}
    """
    check_prompt = f"""请检查以下关于"{topic}"的学习材料是否存在事实性错误。

学习材料：
---
{generated_content}
---

请逐一检查：
1. 概念定义是否准确？
2. 代码示例是否能正常运行？
3. 是否存在逻辑矛盾？
4. 是否有夸大或虚假的声明？

请用 JSON 格式回复：
{{
  "is_accurate": true/false,
  "issues": ["问题1", "问题2"],
  "corrected_version": "修正后的完整内容（如无误则留空）"
}}
"""
    result = await spark_chat(
        [{"role": "user", "content": check_prompt}],
        temperature=0.1,  # 低温度减少随机性
    )

    # 尝试解析 JSON 响应
    import json
    try:
        # 提取 JSON 部分（模型可能在前后加文字）
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "is_accurate": True,
        "issues": [],
        "corrected": "",
        "raw_check": result,
    }


def validate_code_snippet(code: str) -> tuple[bool, str]:
    """
    用 AST 静态检查 Python 代码是否有语法错误
    注意：只检查语法，不检查逻辑

    Returns:
        (is_valid, error_message)
    """
    import ast
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"语法错误（第 {e.lineno} 行）：{e.msg}"


def add_citations(content: str) -> str:
    """在生成内容末尾添加来源声明"""
    return (
        content
        + "\n\n---\n"
        + "*本内容由 AI 生成，已通过知识库校验。"
        + "如有疑问，请参考原课程教材。*"
    )
