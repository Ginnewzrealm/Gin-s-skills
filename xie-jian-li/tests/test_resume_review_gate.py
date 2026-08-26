import sys
import importlib.util
from pathlib import Path
import tempfile
import json

_MODULE_DIR = Path(__file__).parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location(
    "resume_review_gate", _MODULE_DIR / "resume_review_gate.py"
)
resume_review_gate = importlib.util.module_from_spec(_spec)
sys.modules["resume_review_gate"] = resume_review_gate
_spec.loader.exec_module(resume_review_gate)

load_state = resume_review_gate.load_state
save_state = resume_review_gate.save_state
format_resume_text = resume_review_gate.format_resume_text


def test_format_resume_text_basic():
    resume = {
        "basic_info": {"name": "张三", "phone": "13800138000", "email": "zhangsan@example.com"},
        "advantages": ["5年产品经验", "擅长用户增长"],
        "work_history": [
            {
                "title": "某科技公司",
                "role": "产品经理",
                "period": "2020-2023",
                "bullets": ["负责核心产品从0到1", "DAU 提升 50%"],
            }
        ],
        "skills": ["Axure", "SQL", "数据分析"],
    }
    text = format_resume_text(resume)
    assert "张三" in text
    assert "5年产品经验" in text
    assert "DAU 提升 50%" in text
    assert "Axure" in text


def test_load_state_creates_default():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = Path(tmp) / "review_state.json"
        state = load_state(str(state_path))
        assert state["render_approved"] is False
        assert state["feedback"] == ""


def test_save_and_load_state():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = Path(tmp) / "review_state.json"
        save_state(str(state_path), {"render_approved": True, "feedback": "", "approved_at": "2026-01-01"})
        state = load_state(str(state_path))
        assert state["render_approved"] is True
