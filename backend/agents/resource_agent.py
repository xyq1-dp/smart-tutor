"""
资源生成智能体 — 多智能体协作生成 5 种学习资源

资源类型：
1. doc — 课程讲解文档
2. mindmap — 知识点思维导图（Mermaid 格式）
3. exercise — 练习题目
4. reading — 拓展阅读材料
5. practice — 代码实操案例
"""

from backend.llm.spark import spark_chat
from backend.utils.anti_hallucination import verify_against_knowledge_base


RESOURCE_PROMPTS = {
    "doc": """你是一位 Python 教育专家。请根据以下信息生成一份课程讲解文档。

学生画像：{profile}
知识点：{topic}

要求：
- 结构清晰，分小节讲解
- 包含代码示例
- 难度与学生的知识基础匹配
- 核心概念用**粗体**标注
- 末尾提供 3 个思考题

请用 Markdown 格式输出。""",

    "mindmap": """你是一位知识整理专家。请为以下知识点生成思维导图。

知识点：{topic}
学生水平：{level}

请用 Mermaid mindmap 语法输出，格式如下：
```mermaid
mindmap
  root((主题))
    子主题1
      知识点A
      知识点B
    子主题2
      知识点C
      知识点D
```
""",

    "exercise": """你是一位 Python 出题专家。请生成针对性的练习题。

知识点：{topic}
学生水平：{level}
学生薄弱点：{weak_points}

要求：
- 包含 3 道单选题 + 2 道代码题
- 难度递进（易→中→难）
- 提供详细解析
- 用 JSON 格式输出

JSON 格式：
{{
  "questions": [
    {{
      "type": "choice/code",
      "difficulty": "easy/medium/hard",
      "question": "题目描述",
      "options": ["A", "B", "C", "D"],  // 仅选择题
      "answer": "正确答案",
      "explanation": "解析"
    }}
  ]
}}""",

    "reading": """你是一位 Python 学习资源整理专家。请根据以下信息整理拓展阅读材料。

知识点：{topic}
学生兴趣方向：{interests}

要求：
- 推荐 3-5 个相关学习资源（书籍、博客、视频、官方文档）
- 说明每个资源的适用人群和推荐理由
- 按难度排序（基础→进阶）
- 提供在线阅读链接（如有）

请用 Markdown 格式输出。""",

    "practice": """你是一位 Python 实战教练。请设计一个代码实操案例。

知识点：{topic}
学生水平：{level}

要求：
- 设计一个真实的编程场景
- 提供问题描述和预期效果
- 给出参考代码（带注释）
- 包含扩展挑战（让学有余力的学生进一步练习）
- 代码确保能正常运行

请用 Markdown 格式输出，代码块用 ```python 包裹。""",
}


async def generate_resource(
    resource_type: str,
    topic: str,
    profile: dict,
) -> str:
    """
    调用对应角色的智能体生成资源

    Args:
        resource_type: doc / mindmap / exercise / reading / practice
        topic: 知识点主题
        profile: 学生画像

    Returns:
        生成的资源内容（Markdown 或 JSON 字符串）
    """
    prompt_template = RESOURCE_PROMPTS.get(resource_type)
    if not prompt_template:
        return f"不支持的资源类型：{resource_type}"

    prompt = prompt_template.format(
        profile=str(profile),
        topic=topic,
        level=profile.get("knowledge_level", "beginner"),
        weak_points=", ".join(profile.get("weak_points", [])),
        interests=", ".join(profile.get("interest_areas", [])),
    )

    content = await spark_chat(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096,
    )

    # 防幻觉检查（对文档类型）
    if resource_type == "doc":
        check_result = await verify_against_knowledge_base(content, topic)
        if not check_result.get("is_accurate", True):
            corrected = check_result.get("corrected", "")
            if corrected:
                content = corrected

    return content


async def generate_all_resources(
    topic: str,
    profile: dict,
    types: list[str] = None,
) -> dict[str, str]:
    """
    为某个知识点生成全部类型的资源

    Returns:
        {"doc": "...", "mindmap": "...", ...}
    """
    if types is None:
        types = ["doc", "mindmap", "exercise", "reading", "practice"]

    results = {}
    for rtype in types:
        results[rtype] = await generate_resource(rtype, topic, profile)

    return results
