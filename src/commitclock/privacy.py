"""Best-effort redaction shared by local audit output and selected diff snippets.

This is defense in depth, not a guarantee that source code is nonconfidential.
Path exclusions and explicit provider consent are still required.
"""

import re
from collections.abc import Iterable

_REDACTED = "[REDACTED]"
_ASSIGNMENT = re.compile(
    r"""(?im)((?:["']?)(?:[\w-]*(?:api[_-]?key|password|passwd|secret|token)[\w-]*)"""
    r"""["']?\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;]+)"""
)
_PEM = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.S)
_TOKEN = re.compile(
    r"\b(?:AIza[\w-]{20,}|gh[pousr]_[\w]{20,}|github_pat_[\w]{20,}|sk-[\w-]{16,})\b"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[^\s\"',;]+")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def redact(text: str, secrets: Iterable[str] = ()) -> str:
    for secret in sorted({s for s in secrets if s}, key=len, reverse=True):
        text = text.replace(secret, _REDACTED)
    text = _PEM.sub(_REDACTED, text)
    text = _ASSIGNMENT.sub(lambda m: m.group(1) + _REDACTED, text)
    text = _BEARER.sub("Bearer " + _REDACTED, text)
    text = _TOKEN.sub(_REDACTED, text)
    return _CONTROL.sub("", text)
