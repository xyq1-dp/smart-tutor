"""代码执行接口 — 安全的 Python 代码在线运行"""

import re
import subprocess
import tempfile
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 危险代码模式（拒绝执行）
_FORBIDDEN_PATTERNS = [
    "import os", "from os", "import subprocess", "from subprocess",
    "import sys", "__import__", "exec(", "eval(", "compile(",
    "open(", "shutil", "pathlib.Path", "glob",
    "import socket", "import urllib", "import requests",
    "import http", "import ftplib",
]


class ExecuteRequest(BaseModel):
    code: str
    user_id: str = ""


def _is_safe(code: str) -> tuple[bool, str]:
    """检查代码是否安全"""
    code_lower = code.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in code_lower:
            return False, f"代码包含受限操作：{pattern}"
    return True, ""


def extract_error_type(stderr: str) -> str:
    """从stderr中提取Python错误类型"""
    match = re.search(
        r'(\w+Error|SyntaxError|IndentationError|TypeError|'
        r'NameError|ValueError|KeyError|IndexError|'
        r'AttributeError|ZeroDivisionError|ModuleNotFoundError|'
        r'UnboundLocalError|RecursionError|FileNotFoundError|ImportError)',
        stderr,
    )
    return match.group(1) if match else "UnknownError"


@router.post("/execute")
async def execute_code(req: ExecuteRequest):
    """执行 Python 代码并返回输出（最大 5 秒超时）"""
    if not req.code.strip():
        raise HTTPException(status_code=400, detail="代码不能为空")

    is_safe, reason = _is_safe(req.code)
    if not is_safe:
        return {
            "success": False,
            "output": "",
            "error": f"安全限制：{reason}",
            "truncated": False,
        }

    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(req.code)
        tmp_path = f.name

    result = {
        "success": True,
        "output": "",
        "error": "",
        "exit_code": 0,
        "truncated": False,
    }
    stderr_raw = ""
    is_timeout = False

    try:
        proc_result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=tempfile.gettempdir(),
        )

        stdout = proc_result.stdout
        stderr_raw = proc_result.stderr

        # 截断过长输出
        if len(stdout) > 4000:
            stdout = stdout[:4000] + "\n...（输出过长已截断）"
            result["truncated"] = True
        if len(stderr_raw) > 2000:
            stderr_raw = stderr_raw[:2000] + "\n...（错误输出过长已截断）"
            result["truncated"] = True

        output = stdout
        if stderr_raw:
            output += f"\n[stderr]\n{stderr_raw}"

        result["success"] = proc_result.returncode == 0
        result["output"] = output.strip() or "（无输出）"
        result["exit_code"] = proc_result.returncode

    except subprocess.TimeoutExpired:
        is_timeout = True
        result["success"] = False
        result["error"] = "⏱️ 代码执行超时（5 秒限制）。请检查是否有死循环。"

    except Exception as e:
        result["success"] = False
        result["error"] = f"执行异常：{str(e)}"

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # 记录行为 + 错误（有 user_id 时）
    if req.user_id:
        _record_execution(req.user_id, req.code, result, stderr_raw, is_timeout)

    return result


def _record_execution(user_id: str, code: str, result: dict, stderr: str, is_timeout: bool):
    """记录代码执行行为和错误到数据库"""
    try:
        from backend.db.models import record_behavior, record_error
        from backend.db.knowledge_tracing import infer_kc_from_error, update_kc_mastery

        quality = 0.5 if result["success"] else 0.1
        error_type = ""
        related_kcs: list[str] = []

        if not result["success"] and not is_timeout:
            error_type = extract_error_type(stderr)
            related_kcs = infer_kc_from_error(
                error_type=error_type, error_msg=stderr, code=code,
            )

        # 记录行为
        record_behavior(
            user_id=user_id,
            behavior_type="code_execute",
            detail={
                "success": result["success"],
                "exit_code": result.get("exit_code", -1),
                "topics": related_kcs,
            },
            quality_score=quality,
            context={"code_len": len(code), "timeout": is_timeout},
        )

        # 记录错误（执行失败且非超时时）
        if not result["success"] and not is_timeout and error_type:
            record_error(
                user_id=user_id,
                error_type=error_type,
                error_message=stderr[:500],
                error_code=code[:1000],
                related_kc_ids=related_kcs,
            )

        # 更新知识状态
        for kc in related_kcs:
            update_kc_mastery(user_id, kc, quality_score=quality)

        # 如果代码执行成功，从代码内容推断相关KC并标记
        if result["success"]:
            from backend.db.knowledge_tracing import infer_kc_from_text
            text_kcs = infer_kc_from_text(code)
            for kc in text_kcs[:3]:
                update_kc_mastery(user_id, kc, quality_score=0.4)
    except Exception:
        pass
