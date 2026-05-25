"""代码执行接口 — 安全的 Python 代码在线运行"""

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


def _is_safe(code: str) -> tuple[bool, str]:
    """检查代码是否安全"""
    code_lower = code.lower()
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern in code_lower:
            return False, f"代码包含受限操作：{pattern}"
    return True, ""


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

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=tempfile.gettempdir(),
        )

        stdout = result.stdout
        stderr = result.stderr

        # 截断过长输出
        truncated = False
        if len(stdout) > 4000:
            stdout = stdout[:4000] + "\n...（输出过长已截断）"
            truncated = True
        if len(stderr) > 2000:
            stderr = stderr[:2000] + "\n...（错误输出过长已截断）"
            truncated = True

        output = stdout
        if stderr:
            output += f"\n[stderr]\n{stderr}"

        return {
            "success": result.returncode == 0,
            "output": output.strip() or "（无输出）",
            "exit_code": result.returncode,
            "truncated": truncated,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "⏱️ 代码执行超时（5 秒限制）。请检查是否有死循环。",
            "truncated": False,
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"执行异常：{str(e)}",
            "truncated": False,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
