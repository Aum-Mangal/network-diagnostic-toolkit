"""
Tests for core/validator.py
"""

import pytest
from core.validator import validate, ValidationResult


def test_validate_domain():
    res = validate("google.com")
    assert res.is_valid is True
    assert res.input_type == "domain"
    assert res.resolved_ip is not None
    assert res.error is None


def test_validate_ipv4():
    res = validate("8.8.8.8")
    assert res.is_valid is True
    assert res.input_type == "ipv4"
    assert res.resolved_ip == "8.8.8.8"
    assert res.error is None


def test_validate_localhost():
    res = validate("localhost")
    assert res.is_valid is True
    assert res.input_type == "localhost"
    assert res.resolved_ip == "127.0.0.1"


def test_validate_invalid_string():
    res = validate("this is definitely not a domain!!")
    assert res.is_valid is False
    assert res.input_type == "unknown"
    assert res.error is not None


def test_validate_empty():
    res = validate("")
    assert res.is_valid is False
    assert res.input_type == "unknown"
