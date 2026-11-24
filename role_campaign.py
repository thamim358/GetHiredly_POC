"""Validate role campaigns and keep each role tied to its own resume."""

from pathlib import Path


UPLOADS = (Path(__file__).resolve().parent / "uploads").resolve()


def resume_path(value: str) -> str:
    """Return a safe uploaded resume path, or raise a useful validation error."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Each role needs an uploaded resume")
    candidate = (Path(__file__).resolve().parent / value).resolve()
    if candidate.parent != UPLOADS or candidate.suffix.lower() not in {".pdf", ".doc", ".docx"}:
        raise ValueError("Resume must be an uploaded PDF, DOC, or DOCX file")
    if not candidate.is_file():
        raise ValueError(f"Uploaded resume is missing: {candidate.name}")
    return str(candidate)


def campaign_roles(job: dict) -> list[dict]:
    """Normalize a single role or a multi-role email campaign."""
    roles = job.get("roles")
    if roles is None:
        roles = [job]
    if not isinstance(roles, list) or not roles:
        raise ValueError("Add at least one job role")
    normalized = []
    for index, role in enumerate(roles, 1):
        if not isinstance(role, dict):
            raise ValueError(f"Role {index} is invalid")
        kind = str(role.get("role") or "").strip()
        title = str(role.get("customTitle") or "").strip() if kind == "custom" else kind
        subject = str(role.get("subject") or "").strip()
        body = str(role.get("emailTemplate") or "").strip()
        terms = role.get("searchTerms")
        if not isinstance(terms, list):
            raise ValueError(f"Role {index} needs search keywords")
        terms = [str(term).strip() for term in terms if str(term).strip()]
        if not title or not subject or not body or not terms:
            raise ValueError(f"Role {index} needs a title, subject, keywords, and email template")
        resume = resume_path(role.get("resumeFile") or ("uploads/uploaded_resume.pdf" if roles == [job] else ""))
        normalized.append({
            "role": str(role.get("role") or "custom"),
            "title": title,
            "subject": subject,
            "search_terms": terms,
            "email_body": body,
            "resume_file": resume,
        })
    return normalized
