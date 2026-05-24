"""学习路径规划接口"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class PathRequest(BaseModel):
    user_id: str
    goal: str = ""
    current_level: str = "beginner"


@router.post("/path/plan")
async def plan_learning_path(req: PathRequest):
    """规划个性化学习路径（占位，后续接入路径规划智能体）"""
    return {
        "user_id": req.user_id,
        "goal": req.goal,
        "status": "pending",
        "message": "学习路径规划功能将在第4周实现。",
    }


@router.get("/path/default")
async def get_default_path():
    """返回 Python 程序设计的默认学习路径"""
    return {
        "course": "Python 程序设计基础",
        "stages": [
            {
                "order": 1,
                "title": "Python 基础语法",
                "topics": ["变量与数据类型", "输入输出", "运算符", "字符串基础"],
                "estimated_hours": 4,
            },
            {
                "order": 2,
                "title": "流程控制",
                "topics": ["条件判断 (if/elif/else)", "循环 (for/while)", "break/continue"],
                "estimated_hours": 6,
            },
            {
                "order": 3,
                "title": "函数与模块",
                "topics": ["函数定义与调用", "参数与返回值", "作用域", "模块导入"],
                "estimated_hours": 6,
            },
            {
                "order": 4,
                "title": "数据结构",
                "topics": ["列表与元组", "字典与集合", "列表推导式", "数据操作练习"],
                "estimated_hours": 8,
            },
            {
                "order": 5,
                "title": "面向对象编程",
                "topics": ["类与对象", "继承与多态", "魔法方法", "异常处理"],
                "estimated_hours": 8,
            },
            {
                "order": 6,
                "title": "综合项目实战",
                "topics": ["文件操作", "第三方库使用", "小型项目开发", "代码调试"],
                "estimated_hours": 10,
            },
        ],
    }
