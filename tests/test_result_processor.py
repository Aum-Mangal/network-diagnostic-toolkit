"""
Tests for core/result_processor.py (Rules Engine, Thresholds & Scoring)
"""

from core.diagnostic_engine import DiagnosticPayload
from core.result_processor import ResultProcessor, WEIGHTS


def test_result_processor_healthy():
    payload = DiagnosticPayload(
        target="example.com",
        resolved_ip="93.184.216.34",
        intent="connectivity",
        intended_modules=["dns", "ping"],
        modules_run=["dns", "ping"],
        results={
            "dns": {
                "success": True,
                "response_time_ms": 15.0,
                "ipv4_addresses": ["93.184.216.34"],
            },
            "ping": {
                "sent": 4,
                "received": 4,
                "packet_loss": 0.0,
                "avg_latency": 22.0,
                "status": "HEALTHY",
            }
        }
    )
    processor = ResultProcessor()
    result = processor.process(payload)

    assert result.health_score >= 90
    assert result.overall_status == "HEALTHY"
    assert len([p for p in result.problems if p.severity == "critical"]) == 0


def test_result_processor_unreachable():
    payload = DiagnosticPayload(
        target="deadhost.invalid",
        resolved_ip="192.0.2.1",
        intent="connectivity",
        intended_modules=["ping"],
        modules_run=["ping"],
        results={
            "ping": {
                "sent": 4,
                "received": 0,
                "packet_loss": 100.0,
                "avg_latency": 0.0,
                "status": "CRITICAL",
            }
        }
    )
    processor = ResultProcessor()
    result = processor.process(payload)

    assert result.health_score < 50
    assert result.overall_status == "CRITICAL"
    unreachable_probs = [p for p in result.problems if "unreachable" in p.description.lower()]
    assert len(unreachable_probs) > 0
    # Explainable measurement and threshold
    assert unreachable_probs[0].measurement != ""
    assert unreachable_probs[0].threshold != ""


def test_result_processor_rfc1812_rate_limiting():
    """Verify router * * * hops are identified as normal RFC 1812 rate-limiting when destination is reached."""
    payload = DiagnosticPayload(
        target="google.com",
        resolved_ip="142.250.190.46",
        intent="route",
        intended_modules=["traceroute"],
        modules_run=["traceroute"],
        results={
            "traceroute": {
                "total_hops": 4,
                "reached": True,
                "hops": [
                    {"hop": 1, "ip": "192.168.1.1", "latency_ms": 1.2},
                    {"hop": 2, "ip": None, "latency_ms": None}, # * * *
                    {"hop": 3, "ip": "10.0.0.1", "latency_ms": 12.0},
                    {"hop": 4, "ip": "142.250.190.46", "latency_ms": 18.5},
                ]
            }
        }
    )
    processor = ResultProcessor()
    result = processor.process(payload)

    info_probs = [p for p in result.problems if "rate-limiting" in p.description.lower()]
    assert len(info_probs) == 1
    assert info_probs[0].severity == "info"


def test_result_processor_honest_error_scoring():
    """Verify that if a planned module crashes, it lowers the score rather than being silently ignored."""
    payload = DiagnosticPayload(
        target="example.com",
        resolved_ip="93.184.216.34",
        intent="full",
        intended_modules=["dns", "ping", "traceroute", "port"],
        modules_run=["ping"],
        errors={
            "dns": "System DNS resolver failed",
            "traceroute": "Permission denied"
        },
        results={
            "ping": {
                "sent": 4,
                "received": 4,
                "packet_loss": 0.0,
                "avg_latency": 20.0,
            }
        }
    )
    processor = ResultProcessor()
    result = processor.process(payload)

    # Since 2 out of 4 modules failed, the score cannot be 100
    assert result.health_score < 70
    assert any("failed to execute" in p.description for p in result.problems)


def test_result_processor_icmp_blocked_tcp_alive():
    """Verify that when ICMP is blocked by firewall but TCP 443 connects, health score stays high."""
    payload = DiagnosticPayload(
        target="amazon.com",
        resolved_ip="205.251.242.103",
        intent="connectivity",
        intended_modules=["ping"],
        modules_run=["ping"],
        results={
            "ping": {
                "sent": 4,
                "received": 0,
                "lost": 4,
                "packet_loss": 100.0,
                "avg_latency": 28.5,
                "min_latency": 28.5,
                "max_latency": 28.5,
                "status": "ICMP_BLOCKED_TCP_OK",
                "icmp_blocked": True,
                "tcp_fallback": {"port": 443, "rtt_ms": 28.5},
            }
        }
    )
    processor = ResultProcessor()
    result = processor.process(payload)

    assert result.health_score >= 80
    assert result.overall_status == "HEALTHY"
    assert any("Host ALIVE via TCP port 443" in p.description for p in result.problems)
