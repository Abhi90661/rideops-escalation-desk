"""Editable escalation checklists.

These entries are hypotheses to validate with Sandeep's engineering team.
They are not claims derived from the ticket outcomes.
"""

HYPOTHESIS_NOTE = "Hypothesis to validate with Sandeep's engineering team"

PLAYBOOKS = {
    "Roster / booking not syncing": {
        "checklist": ["Booking cutoff configuration vs shift time", "Employees and shift", "Admin role", "Trip IDs", "Re-sync attempted", "Screenshot"],
        "required": {"trip_ids": "Trip IDs", "shift": "Employees and shift", "screenshot": "Screenshot"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "Live tracking / GPS incorrect": {
        "checklist": ["Trip ID", "Driver and vehicle", "Last ping time", "App version and OS", "Network", "One trip or many"],
        "required": {"trip_id": "Trip ID", "last_ping": "Last ping time", "app_version": "App version and OS", "screenshot": "Screenshot"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "Report export failing": {
        "checklist": ["Report type", "Date range (flag over 15 days)", "Row count", "Retry result", "Browser", "Scheduled or manual"],
        "required": {"report_type": "Report type", "date_range": "Date range", "retry_result": "Retry result"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "OTP / boarding issue": {
        "checklist": ["Trip ID", "Employee ID", "OTP sent time", "SMS delivery status", "App version"],
        "required": {"trip_id": "Trip ID", "employee_id": "Employee ID", "otp_sent_time": "OTP sent time"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "Billing / invoice discrepancy": {
        "checklist": ["Invoice ID", "Expected vs billed trip count", "Rate card", "Dispute window"],
        "required": {"invoice_id": "Invoice ID", "trip_count": "Expected vs billed trip count", "rate_card": "Rate card"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "Cab delay / no-show complaint": {
        "checklist": ["Trip ID", "Scheduled pickup and driver assignment", "Employee impact", "Timestamp and location", "Driver app status"],
        "required": {"trip_id": "Trip ID", "impact": "Employee impact", "timestamp": "Timestamp"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "Login / access issue": {
        "checklist": ["User or admin identity", "SSO or password path", "Role and permissions", "Affected users", "Recent access change"],
        "required": {"user": "User or admin identity", "role": "Role and permissions", "affected_users": "Affected users"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
    "How-to / feature request": {
        "checklist": ["Requested action", "Screenshots or steps", "Current feature behavior", "Business need"],
        "required": {"requested_action": "Requested action", "evidence": "Screenshots or steps"},
        "hypothesis": True,
        "hypothesis_note": HYPOTHESIS_NOTE,
    },
}
DEFAULT_PLAYBOOK = {
    "checklist": ["Reproduce the issue", "Capture client impact", "Attach screenshot or logs"],
    "required": {"evidence": "Screenshot or logs"},
    "hypothesis": True,
    "hypothesis_note": HYPOTHESIS_NOTE,
}

