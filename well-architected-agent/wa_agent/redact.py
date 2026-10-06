"""Redaction for output people may share (issue reports, chat): identifiers,
tokens and secret-like values are masked. The agent never reads secrets; this
is a second line of defence for anything a CLI echoes back."""

from __future__ import annotations

import re

_PATTERNS = [
    (re.compile(r"\bdapi[0-9a-f]{32}(-\d+)?\b"), "<databricks-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), "<jwt>"),
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "<aws-access-key>"),
    # No \b: in ARM_CLIENT_SECRET the "_" before SECRET is a word character.
    (re.compile(r"(?i)(?<![a-z0-9])(client[_-]?secret|secret|password|passwd|token|sig|account[_-]?key|access[_-]?key)"
                r"(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"), r"\1\2<redacted>"),
    (re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"), "<guid>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    (re.compile(r"(?i)/resourceGroups/[^/\s'\"]+"), "/resourceGroups/<rg>"),
    (re.compile(r"(?i)/(workspaces|virtualNetworks|subnets|accessConnectors|storageAccounts)/[^/\s'\"]+"), r"/\1/<name>"),
    (re.compile(r"\badb-\d+\.\d+\.azuredatabricks\.net\b"), "adb-<id>.azuredatabricks.net"),
    (re.compile(r"\b\d{6,}\.\d+\.gcp\.databricks\.com\b"), "<id>.gcp.databricks.com"),
    (re.compile(r"\b[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com\b"), "<project>.iam.gserviceaccount.com"),
    (re.compile(r"\barn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:\d{12}:\S+"), "<aws-arn>"),
    (re.compile(r"\bdbc-[0-9a-f]{8}-[0-9a-f]{4}\.cloud\.databricks\.com\b"), "dbc-<id>.cloud.databricks.com"),
    (re.compile(r"\b\d{15,16}\b"), "<workspace-id>"),
    (re.compile(r"\b\d{12}\b"), "<aws-account-id>"),
]


def redact(text: str, terms: set[str] | None = None) -> str:
    for term in sorted(terms or (), key=len, reverse=True):
        if term and len(term) >= 3:
            text = re.sub(re.escape(term), "<redacted>", text, flags=re.IGNORECASE)
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactingWriter:
    """File-like wrapper: everything written through it is redacted."""

    def __init__(self, out, enabled: bool = True):
        self.out, self.enabled, self.terms = out, enabled, set()

    def write(self, text: str) -> int:
        return self.out.write(redact(text, self.terms) if self.enabled else text)

    def flush(self) -> None:
        self.out.flush()
