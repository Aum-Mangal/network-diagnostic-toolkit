"""
Tests for analysis/diagnosis.py (Natural Language Parsing & Target Extraction)
"""

from analysis.diagnosis import parse_query


def test_parse_bare_domain():
    p = parse_query("google.com")
    assert p.target == "google.com"
    assert p.intent == "full"
    assert p.natural_language is False
    assert p.needs_target is False
    assert p.extracted_target_type == "domain"


def test_parse_bare_ipv4():
    p = parse_query("1.1.1.1")
    assert p.target == "1.1.1.1"
    assert p.intent == "full"
    assert p.natural_language is False
    assert p.extracted_target_type == "ipv4"


def test_parse_slow_intent_domain():
    p = parse_query("Why is google.com slow?")
    assert p.target == "google.com"
    assert p.intent == "slow"
    assert p.natural_language is True
    assert p.needs_target is False


def test_parse_custom_ports():
    p = parse_query("check port 8080 on 192.168.1.1")
    assert p.target == "192.168.1.1"
    assert p.custom_ports == [8080]
    assert p.intent == "access"
    assert p.needs_target is False


def test_parse_ipv6_target():
    p = parse_query("traceroute to 2001:4860:4860::8888")
    assert p.target == "2001:4860:4860::8888"
    assert p.intent == "route"
    assert p.extracted_target_type == "ipv6"


def test_parse_missing_target():
    p = parse_query("Why is my internet so slow today?")
    assert p.target is None
    assert p.needs_target is True
    assert "No destination target" in p.clarification_prompt
