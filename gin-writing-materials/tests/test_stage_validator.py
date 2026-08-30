#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for scripts/stage_validator.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from stage_validator import (
    decide_next_stage,
    validate_transition,
    advance_stage,
    is_hard_gate,
)


def test_decide_next_stage_for_mine():
    session = {"stage": "domain_selected", "status": "active"}
    result = decide_next_stage(session, "mine")
    assert result["current_key"] == "domain_selected"
    assert "project_located" in result["completed_keys"]
    assert "topic_defined" in result["completed_keys"]


def test_decide_next_stage_when_completed():
    session = {"stage": "completed", "status": "completed"}
    result = decide_next_stage(session, "mine")
    assert result["current_key"] == "completed"
    assert "project_located" in result["completed_keys"]


def test_decide_next_stage_for_review():
    session = {}
    result = decide_next_stage(session, "review")
    assert result["current_key"] == "project_located"


def test_validate_transition_forward():
    result = validate_transition("project_located", "topic_defined", "mine")
    assert result["valid"] is True


def test_validate_transition_loopback():
    result = validate_transition("mining", "topic_defined", "mine")
    assert result["valid"] is True


def test_validate_transition_skip_not_allowed():
    result = validate_transition("project_located", "mining", "mine")
    assert result["valid"] is False


def test_advance_stage():
    session = {"stage": "topic_defined"}
    assert advance_stage(session, "mine") == "anchors_loaded"


def test_advance_stage_at_end():
    session = {"stage": "completed"}
    assert advance_stage(session, "mine") is None


def test_is_hard_gate():
    assert is_hard_gate("topic_defined", "mine") is True
    assert is_hard_gate("project_located", "mine") is False


def test_is_hard_gate_for_review():
    assert is_hard_gate("correcting", "correct") is True
    assert is_hard_gate("project_located", "review") is False
