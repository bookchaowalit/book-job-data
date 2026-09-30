"""Field allowlist and contact redaction for job.v1 records.

Scraper captures pass through as CSV, so any column a board adds would reach
Bronze and the API unchanged. Records keep only known job.v1 fields, and
free-text fields have email addresses and phone numbers masked. The exact
source bytes stay in the internal landing zone as replay evidence; they are
never served by the API.
"""
from __future__ import annotations

import re
from typing import Any

# Columns the scraper writes (job_postings, career_postings, matched_jobs,
# pipeline/leads) plus fields added by ingest and the Bronze item builder.
POSTING_FIELDS = {
    "title", "company", "location", "salary", "url", "source", "keyword",
    "posted", "tags", "scraped_at", "description", "search_lane",
}
MATCH_FIELDS = {
    "rank", "score", "visa_sponsorship", "qualification_status", "policy_version",
    "employment_type", "work_arrangement", "thailand_eligibility",
    "concurrent_employment", "engagement_boundary", "application_readiness",
    "qualification_reasons", "primary_matches", "secondary_matches", "bonuses",
    "verified_role_requirements", "verified_destination_country",
    "verified_destination_eligibility", "verified_career_transition",
    "verified_employment_terms", "verification_source_url", "verified_at",
    "verified_employment_type", "verified_work_arrangement",
    "verified_thailand_eligibility", "verified_concurrent_employment",
    "verified_engagement_boundary", "verified_bridge_compensation",
    "verified_scope_duration", "verified_mentor", "verified_conversion_path",
    "verification_notes",
}
# pipeline.csv lead rows; its "contact" and "email" columns are intentionally absent.
LEAD_FIELDS = {"lead_id", "status", "value", "next_action", "notes"}
SYSTEM_FIELDS = {
    "id", "canonical_url", "event_time", "observed_at", "provider", "input_name",
    "record_id", "ingest_run_id", "source_record_id", "raw_object_key",
    "source_url", "apply_url", "link", "board", "created_date", "date",
}
ALLOWED_FIELDS = frozenset(POSTING_FIELDS | MATCH_FIELDS | LEAD_FIELDS | SYSTEM_FIELDS)

# Free text that may quote a recruiter's contact details.
TEXT_FIELDS = frozenset({
    "title", "company", "location", "salary", "tags", "description", "keyword",
    "qualification_reasons", "verification_notes", "notes", "next_action",
    "verified_role_requirements", "verified_employment_terms",
})

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_CANDIDATE_RE = re.compile(
    r"(?<![\w/.])\+?\(?\d{1,4}\)?(?:[ .-]?\(?\d{2,5}\)?){2,5}(?![\w/])"
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

EMAIL_MASK = "[redacted-email]"
PHONE_MASK = "[redacted-phone]"


def _mask_phone(match: re.Match[str]) -> str:
    text = match.group(0)
    digits = re.sub(r"\D", "", text)
    if not 9 <= len(digits) <= 15 or _DATE_RE.search(text):
        return text
    return PHONE_MASK


def redact_text(value: str) -> str:
    if not value:
        return value
    value = _EMAIL_RE.sub(EMAIL_MASK, value)
    return _PHONE_CANDIDATE_RE.sub(_mask_phone, value)


def sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with unknown fields dropped and contact details masked."""
    clean: dict[str, Any] = {}
    for key, value in record.items():
        if key not in ALLOWED_FIELDS:
            continue
        if key in TEXT_FIELDS and isinstance(value, str):
            value = redact_text(value)
        clean[key] = value
    return clean
