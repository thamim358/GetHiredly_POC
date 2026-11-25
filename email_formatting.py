"""Render saved email templates as HTML and a readable text alternative."""

import html
import re
from html.parser import HTMLParser

import markdown


_BODY = re.compile(r"(<body\b[^>]*>)(.*?)(</body\s*>)", re.I | re.S)
_BLOCK_TAG = re.compile(r"<(?:p|div|ul|ol|li|table|section|article|h[1-6])\b", re.I)
_MARKDOWN = re.compile(r"\*\*[^*\n]+\*\*|\[[^\]]+\]\(https?://")
_HTML_TEMPLATE = re.compile(r"</?(?:html|head|body|p|div|ul|ol|li|br|strong|b|em|i|a|span|h[1-6])\b", re.I)


def personalize_email_template(template: str, personal: dict | None = None) -> str:
    """Replace supported template tokens with safely escaped profile values."""
    personal = personal or {}
    values = {
        "FULL_NAME": personal.get("fullName", personal.get("name", "")),
        "EMAIL": personal.get("email", ""),
        "PHONE": personal.get("phone", ""),
        "WEBSITE": personal.get("website", ""),
        "LOCATION": personal.get("location", ""),
    }
    result = str(template or "")
    for token, value in values.items():
        result = result.replace(f"[{token}]", html.escape(str(value or "").strip(), quote=True))
    return result
_BULLET = re.compile(r"^(\s*)[•‣◦]\s+", re.M)


def _render_body(body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    # Rich text templates already contain paragraphs/lists. Saved plain-text
    # pastes can contain <br> from the editor, but still need Markdown parsing.
    if _BLOCK_TAG.search(body) and not _MARKDOWN.search(body):
        return body
    if _BLOCK_TAG.search(body):
        # Preserve edited HTML. Markdown inside a block tag is uncommon, and
        # reparsing the whole fragment could damage its existing structure.
        return body
    body = html.unescape(body).replace("\xa0", " ")
    body = _BULLET.sub(r"\1- ", body)
    return markdown.markdown(html.escape(body, quote=False), extensions=["nl2br"], output_format="html")


def render_email_html(template: str) -> str:
    """Convert plain/Markdown templates, including old HTML wrappers, to HTML."""
    template = (template or "").strip()
    match = _BODY.search(template)
    if match:
        body = _render_body(match.group(2))
        return template[:match.start(2)] + body + template[match.end(2):]
    body = _render_body(template)
    return (
        '<html><body style="font-family: Arial, sans-serif; '
        'line-height: 1.6; color: #333;">'
        + body + '</body></html>'
    )


class _PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.hidden_depth:
            self.hidden_depth += 1
            return
        if tag in {"head", "style", "script"}:
            self.hidden_depth = 1
            return
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag == "a":
            self.links.append(dict(attrs).get("href", ""))

    def handle_endtag(self, tag):
        if self.hidden_depth:
            self.hidden_depth -= 1
            return
        if tag == "a" and self.links:
            link = self.links.pop()
            if link and link not in "".join(self.parts[-3:]):
                self.parts.append(f" <{link}>")
        elif tag in {"p", "div", "h1", "h2", "h3", "ul", "ol"}:
            self.parts.append("\n\n")

    def handle_data(self, data):
        if not self.hidden_depth and (data.strip() or (data.isspace() and "\n" not in data)):
            self.parts.append(data)


def plain_text_from_html(html_body: str) -> str:
    parser = _PlainTextParser()
    parser.feed(html_body)
    content = "\n".join(line.strip() for line in "".join(parser.parts).splitlines())
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def editable_email_template(template: str) -> str:
    """Show legacy HTML templates as a normal message in the dashboard editor."""
    template = str(template or "")
    return plain_text_from_html(template) if _HTML_TEMPLATE.search(template) else template
