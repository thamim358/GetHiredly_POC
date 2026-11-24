"""Resume matching, search suggestions, and connection-note drafts."""

from __future__ import annotations

import re
import html
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree

from role_campaign import resume_path


NOTE_LIMIT = 200
HIRING_SEARCH_TERMS = (
    "recruiter", "recruitment", "talent acquisition", "IT recruiter",
    "talent sourcer", "hiring manager", "human resources", "HR business partner",
    "people operations", "people manager", "staffing recruiter", "workforce planning",
)
HIRING_PROFILE_PATTERNS = (
    ("recruiter / recruiting / recruitment", r"\brecruit\w*\b"),
    ("talent acquisition", r"\btalent[\s&/-]+acquisition\b"),
    ("acquisition", r"\bacquisition\b"),
    ("talent sourcing", r"\btalent\s+(?:sourc\w*|acquisition\s+sourc\w*)\b"),
    ("talent partner", r"\btalent\s+(?:partner|advisor|specialist|manager|lead|director)\b"),
    ("talent management", r"\btalent\s+management\b"),
    ("talent", r"\btalent\b"),
    ("human resources", r"\bhuman\s+resources?\b"),
    ("human", r"\bhuman\b"),
    ("resource", r"\bresources?\b"),
    ("human capital", r"\bhuman\s+capital\b"),
    ("HR", r"\bhr(?:bp|\s+(?:business\s+partner|manager|director|specialist|professional|recruiter))?\b"),
    ("hiring", r"\bhir(?:e|ing)\w*\b|\b(?:hiring|recruitment)\s+(?:manager|partner|specialist|lead)\b"),
    ("people operations", r"\bpeople\s+(?:ops|operations)\b"),
    ("people", r"\bpeople\b"),
    ("people manager", r"\bpeople\s+(?:manager|management|partner|specialist|director|lead)\b"),
    ("people and talent", r"\bpeople\s+(?:&|and)\s+talent\b"),
    ("people and culture", r"\bpeople\s+(?:and|&)\s+culture\b|\bpeople\s+experience\b"),
    ("staffing", r"\bstaff(?:ing|er|ers)\b"),
    ("workforce planning", r"\bworkforce\s+(?:planning|management|solutions)\b"),
    ("workforce", r"\bworkforce\b"),
    ("manager", r"\bmanagers?\b"),
    ("opportunity", r"\bopportunit\w*\b"),
    ("RPO", r"\brpo\b|\brecruitment\s+process\s+outsourcing\b"),
)
_WORDS = re.compile(r"[a-z][a-z0-9+#.]{2,}", re.I)
_STOPWORDS = {"about", "after", "also", "and", "are", "for", "from", "have", "into", "job", "jobs", "our", "the", "this", "with", "work", "your"}


def _items(value, label: str) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,\n]", value)
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    items = list(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return items[:12]


@dataclass(frozen=True)
class SearchSpec:
    locations: list[str]
    titles: list[str]
    alternate_titles: list[str]
    skills: list[str]
    work_mode: str
    hiring_text: str
    resume: str
    search_mode: str = "hiring_managers"

    @classmethod
    def from_payload(cls, data: dict) -> "SearchSpec":
        locations = _items(data.get("locations", []), "Locations")
        titles = _items(data.get("titles", []), "Job titles")
        alternate = _items(data.get("alternateTitles", []), "Alternate titles")
        skills = _items(data.get("skills", []), "Skills")
        mode = str(data.get("workMode", "any")).lower()
        search_mode = str(data.get("searchMode", "hiring_managers")).lower()
        if not locations or not titles:
            raise ValueError("Enter at least one target location and job title")
        if mode not in {"any", "remote", "hybrid", "onsite"}:
            raise ValueError("Work preference must be any, remote, hybrid, or onsite")
        if search_mode not in {"hiring_managers", "referral_contacts"}:
            raise ValueError("Choose hiring managers or referral contacts")
        resume_value = data.get("resumePath", "")
        resume = resume_path(resume_value) if str(resume_value or "").strip() else ""
        if resume and Path(resume).suffix.lower() not in {".pdf", ".docx"}:
            raise ValueError("Use a PDF or DOCX resume for job matching")
        return cls(locations, titles, alternate, skills, mode, str(data.get("hiringText", "")).strip()[:1200], resume, search_mode)


def read_resume_text(path: str) -> str:
    if not path:
        return ""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    elif suffix == ".docx":
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    else:
        raise ValueError("Use a PDF or DOCX resume for job matching")
    if len(text.strip()) < 30:
        raise ValueError("The resume has no extractable text. Upload a text-based PDF or DOCX")
    return text[:50000]


def suggested_people_queries(spec: SearchSpec) -> list[str]:
    if spec.search_mode == "hiring_managers":
        return [f'"{term}" {spec.locations[0]}' for term in HIRING_SEARCH_TERMS]
    terms = list(dict.fromkeys(spec.titles + spec.alternate_titles + spec.skills))
    return [f'"{term}" {spec.locations[0]}' for term in terms[:8]]


def people_search_urls(spec: SearchSpec) -> list[str]:
    """Build LinkedIn people search URLs for the selected contact type."""
    return [
        "https://www.linkedin.com/search/results/people/?" + urlencode({"keywords": query, "origin": "GLOBAL_SEARCH_HEADER"})
        for query in suggested_people_queries(spec)
    ]


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.strip()).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text, re.I))


def profile_match(profile_text: str, spec: SearchSpec) -> tuple[bool, list[str], str]:
    """Match one or more related words in the displayed profile headline."""
    text = html.unescape(profile_text or "")
    text = text.replace("\u00a0", " ").replace("\u2011", "-")
    text = re.sub(r"\s+", " ", text).strip()
    if spec.search_mode == "hiring_managers":
        matched = [label for label, pattern in HIRING_PROFILE_PATTERNS if re.search(pattern, text, re.I)]
        if "talent acquisition" in matched:
            matched = [term for term in matched if term not in {"talent", "acquisition"}]
        if "human resources" in matched:
            matched = [term for term in matched if term not in {"human", "resource"}]
        if matched:
            return True, matched, "Hiring profile: " + ", ".join(matched[:3])
        return False, [], "Profile has no hiring related title or term"
    terms = list(dict.fromkeys(spec.titles + spec.alternate_titles + spec.skills))
    keywords = list(dict.fromkeys(
        word for term in terms for word in re.findall(r"[a-z][a-z0-9+#.]*", term.lower())
    ))
    matched = [word for word in keywords if _contains_term(text, word)]
    if matched:
        return True, matched, "Role or skill match: " + ", ".join(matched[:3])
    return False, [], "Profile has no target role or skill match"


def job_search_urls(spec: SearchSpec) -> list[str]:
    urls = []
    for title in (spec.titles + spec.alternate_titles)[:3]:
        for location in spec.locations[:2]:
            params = {"keywords": title, "location": location, "f_TPR": "r604800"}
            urls.append("https://www.linkedin.com/jobs/search/?" + urlencode(params))
    return urls[:6]


def post_search_urls(spec: SearchSpec) -> list[str]:
    words = _WORDS.findall(spec.hiring_text)[:4]
    query_hint = " ".join(words) if words else "hiring"
    return [
        "https://www.linkedin.com/search/results/content/?"
        + urlencode({"keywords": f"{title} {query_hint} {spec.locations[0]}", "datePosted": '"past-week"'})
        for title in (spec.titles + spec.alternate_titles)[:3]
    ]


def score_job(job: dict, spec: SearchSpec, resume_text: str) -> tuple[int, list[str]]:
    title = str(job.get("title", "")).lower()
    summary = " ".join(str(job.get(key, "")) for key in ("title", "company", "location", "description")).lower()
    resume_words = set(_WORDS.findall(resume_text.lower())) - _STOPWORDS
    reasons = []
    score = 0
    for target in spec.titles + spec.alternate_titles:
        if target.lower() in title:
            score += 45
            reasons.append(f"Title: {target}")
            break
        target_words = set(_WORDS.findall(target.lower())) - {"engineer", "developer", "specialist"}
        common = target_words & set(_WORDS.findall(title))
        if common:
            score += min(len(common), 3) * 18
            reasons.append("Title terms: " + ", ".join(sorted(common)))
            break
    matches = [skill for skill in spec.skills if skill.lower() in summary and skill.lower() in resume_text.lower()]
    score += min(len(matches), 5) * 8
    if matches:
        reasons.append("Resume skills: " + ", ".join(matches[:5]))
    overlap = (set(_WORDS.findall(summary)) - _STOPWORDS) & resume_words
    score += min(len(overlap), 8) * 2
    location = str(job.get("location", "")).lower()
    if any(place.lower() in location for place in spec.locations):
        score += 15
        reasons.append("Target location")
    if spec.work_mode != "any" and spec.work_mode in location:
        score += 10
        reasons.append(spec.work_mode.title())
    if spec.hiring_text and any(word.lower() in summary for word in _WORDS.findall(spec.hiring_text)[:6]):
        score += 5
        reasons.append("Hiring text match")
    return min(score, 100), reasons


def location_matches(location: str, spec: SearchSpec) -> bool:
    """Keep only jobs whose displayed location fits the requested places."""
    location = location.lower().strip()
    if not location:
        return False
    if spec.work_mode == "remote" and "remote" not in location:
        return False
    if spec.work_mode == "hybrid" and "hybrid" not in location:
        return False
    if spec.work_mode == "onsite" and any(mode in location for mode in ("remote", "hybrid")):
        return False
    middle_east = ("dubai", "abu dhabi", "united arab emirates", "uae", "riyadh", "saudi arabia", "qatar", "doha", "oman", "muscat", "kuwait", "bahrain")
    for target in spec.locations:
        target = target.lower().strip()
        if target in {"remote", "worldwide", "global"} and "remote" in location:
            return True
        if target in {"middle east", "middle-east"} and any(place in location for place in middle_east):
            return True
        place = target.split(",")[0].strip()
        if place and place in location:
            return True
    return False


def profile_url(url: str) -> str | None:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname not in {"linkedin.com", "www.linkedin.com"} or len(parts) < 2 or parts[0].casefold() != "in" or not parts[1]:
        return None
    return f"https://www.linkedin.com/in/{parts[1].casefold()}/"


def person_name(value: str) -> str:
    """Keep a member's name, never a profile-link action such as 'View'."""
    value = re.sub(r"\s+", " ", (value or "").replace("’", "'")).strip()
    match = re.match(r"^(?:View|Visit)\s+(.+?)(?:'s)?\s+profile\b", value, re.I)
    if match:
        value = match.group(1).strip()
    else:
        value = re.sub(r"'s$", "", value, flags=re.I).strip()
    if re.search(r"\b(?:view|visit|profile|connect|follow)\b", value, re.I) or len(value) < 2:
        return ""
    return value[:70]


def post_topic(text: str, titles: list[str], skills: list[str]) -> str:
    """Describe a post with a concrete role or technology from its text."""
    content = re.sub(r"\s+", " ", text or "").lower()
    title = next((item for item in titles if item.lower() in content), titles[0] if titles else "the role")
    if re.search(r"\b(hiring|opening|recruiting|looking for|seeking)\b", content):
        return f"the {title} opening"
    specific = next((item for item in skills if len(item) >= 5 and item.lower() in content
                     and item.lower() not in {"automation", "testing", "developer", "engineer"}), "")
    return f"{specific} work" if specific else f"{title} work"


def draft_note(name: str, topic: str, field: str, company: str = "", *, mode: str = "hiring_managers", matched_term: str = "") -> str:
    clean_name = person_name(name)
    first = clean_name.split()[0] if clean_name else ""
    greeting = f"Hi {first}," if first else "Hello,"
    field = re.sub(r"\s+", " ", field or "").strip() or "this field"
    if mode == "referral_contacts":
        experience = re.sub(r"\s+", " ", matched_term or field).strip()
        variants = [
            f"{greeting} I noticed your experience with {experience}. I'm exploring {field} roles and would appreciate your advice on the field.",
            f"{greeting} I'm exploring {field} roles and noticed your experience with {experience}. Would you be open to sharing advice?",
            f"{greeting} I'm exploring {field} roles and would value your advice if you have a moment.",
        ]
        return next((note for note in variants if len(note) <= NOTE_LIMIT), variants[-1][:NOTE_LIMIT - 1].rstrip(" ,.;") + ".")
    topic = re.sub(r"^\s*(?:about|on)\s+", "", topic or "", flags=re.I).strip() or "your hiring work"
    company = re.sub(r"\s+", " ", company or "").strip()
    focus = matched_term or topic
    focus = {
        "recruiter / recruiting / recruitment": "recruiting",
        "talent acquisition": "talent acquisition",
        "talent sourcing": "talent sourcing",
        "talent partner": "talent acquisition",
        "human resources": "human resources",
        "HR": "human resources",
        "hiring": "hiring",
        "people operations": "people operations",
        "people manager": "people management",
        "people and culture": "people and culture",
        "staffing": "staffing",
        "workforce planning": "workforce planning",
        "career opportunities": "career opportunities",
        "RPO": "recruitment process outsourcing",
    }.get(focus, focus)
    detail = f" at {company}" if company else ""
    variants = [
        f"{greeting} I noticed your work in {focus}{detail}. I'm exploring {field} opportunities and would welcome your advice on relevant openings.",
        f"{greeting} I'm exploring {field} roles and saw your hiring work{detail}. I'd value your perspective on what teams need.",
        f"{greeting} I'm exploring {field} roles and would be glad to connect about relevant openings.",
    ]
    return next((note for note in variants if len(note) <= NOTE_LIMIT), variants[-1][:NOTE_LIMIT - 1].rstrip(" ,.;") + ".")
