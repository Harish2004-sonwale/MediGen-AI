"""Locust Performance and Load Testing Suite for MediGen AI.

Phase 9.0.20: Platform Hardening, Production Deployment Hardening & Enterprise Scalability.

Target SLAs:
- 100+ Concurrent simulated clinicians
- p95 latency < 200ms for core read & dashboard queries
- p95 latency < 800ms for timeline & FHIR bundle aggregations
- Zero 5xx server errors under standard load

Usage:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000
    # Headless benchmark run:
    locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 1m --host http://localhost:8000
"""

import json
import logging
from locust import HttpUser, between, task

logger = logging.getLogger("medigen.loadtest")


class ClinicianUser(HttpUser):
    """Simulates an active physician or nurse reviewing charts and querying clinical analytics."""

    wait_time = between(1.0, 3.0)  # 1 to 3 seconds think time between clinical actions

    def on_start(self):
        """Authenticate user on session start if credentials exist or use public token."""
        self.client.headers.update({
            "User-Agent": "MediGenAI-LocustLoadTester/1.0",
            "Accept": "application/json",
        })

    # 1. Health & Liveness Probes (High frequency baseline)
    @task(10)
    def probe_liveness(self):
        self.client.get("/health", name="[Probe] Liveness /health")

    @task(5)
    def probe_readiness(self):
        self.client.get("/ready", name="[Probe] Readiness /ready")

    # 2. Operational Metrics & FHIR Metadata
    @task(3)
    def query_fhir_metadata(self):
        self.client.get("/api/v1/fhir/metadata", name="[FHIR] CapabilityStatement /metadata")

    @task(2)
    def query_prometheus_metrics(self):
        self.client.get("/api/v1/health/metrics/prometheus", name="[Metrics] Prometheus /metrics")

    # 3. Patient Demographics & Encounters (Read-only)
    @task(8)
    def list_patients(self):
        self.client.get("/api/v1/patients", name="[Clinical] List Patients")

    @task(6)
    def list_encounters(self):
        self.client.get("/api/v1/encounters", name="[Clinical] List Encounters")

    # 4. Clinical Quality Measures & Dashboards
    @task(4)
    def query_quality_measures(self):
        self.client.get("/api/v1/quality/measures", name="[Quality] List CQM Measures")

    # 5. Security & Compliance Posture
    @task(3)
    def query_compliance_summary(self):
        self.client.get("/api/v1/security/compliance-summary", name="[Security] Compliance Summary")

    # 6. Longitudinal Timeline Queries
    @task(5)
    def query_patient_timeline(self):
        # Queries patient timeline for test patient PAT-001
        self.client.get("/api/v1/timeline/PAT-001", name="[Timeline] Patient Timeline PAT-001")

    # 7. FHIR Resource Reads
    @task(4)
    def export_fhir_patient(self):
        self.client.get("/api/v1/fhir/Patient/PAT-001", name="[FHIR] Read Patient PAT-001")
