"""
Tests for reports/report_generator.py
"""

import json
from core.diagnostic_engine import DiagnosticPayload
from core.result_processor import ResultProcessor
from reports.report_generator import generate_txt_report, generate_json_report


def test_txt_and_json_reports():
    payload = DiagnosticPayload(
        target="google.com",
        resolved_ip="142.250.190.46",
        intent="slow",
        intended_modules=["dns", "ping", "traceroute"],
        modules_run=["dns", "ping", "traceroute"],
        results={
            "dns": {
                "success": True,
                "response_time_ms": 14.2,
                "ipv4_addresses": ["142.250.190.46"],
            },
            "ping": {
                "sent": 4,
                "received": 4,
                "packet_loss": 0.0,
                "avg_latency": 25.1,
                "min_latency": 22.0,
                "max_latency": 29.0,
                "status": "HEALTHY",
            },
            "traceroute": {
                "total_hops": 2,
                "reached": True,
                "hops": [
                    {"hop": 1, "ip": "192.168.1.1", "hostname": "router.local", "latency_ms": 1.1},
                    {"hop": 2, "ip": "142.250.190.46", "hostname": "google.com", "latency_ms": 25.0},
                ]
            }
        }
    )
    processor = ResultProcessor()
    processed = processor.process(payload)

    txt = generate_txt_report(processed)
    assert "NETWORK DIAGNOSTIC REPORT" in txt
    assert "google.com" in txt
    assert "CONNECTIVITY (PING)" in txt
    assert "DNS RESOLUTION" in txt
    assert "ROUTING (TRACEROUTE)" in txt

    json_str = generate_json_report(processed)
    data = json.loads(json_str)
    assert data["target"] == "google.com"
    assert data["intent"] == "slow"
    assert data["health_score"] >= 90
    assert "results" in data
