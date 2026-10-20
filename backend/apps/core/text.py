"""Sanitising for staff-written text that is rendered as HTML."""

import html
import re

import nh3

RICH_TEXT_TAGS = {
    "p",
    "br",
    "strong",
    "em",
    "b",
    "i",
    "a",
    "ul",
    "ol",
    "li",
    "h3",
    "h4",
    "blockquote",
}
URL_PATTERN = re.compile(r"(https://[^\s<]+[^\s<.,;:!?)\]'\"])")
# The admin's editor (Trix) writes each paragraph as a <div>, and a blank line as an
# empty one; they are kept as paragraphs, without the blank ones.
DIV_TAG = re.compile(r"<(/?)div\b[^>]*>", re.IGNORECASE)
EMPTY_PARAGRAPH = re.compile(r"<p>(?:\s|&nbsp;|<br>)*</p>")


def _clean(markup, tags):
    return nh3.clean(
        markup,
        tags=tags,
        attributes={"a": {"href"}},
        url_schemes={"https", "mailto"},
        link_rel="noopener noreferrer nofollow",
        strip_comments=True,
    )


def sanitize_rich_text(markup):
    """Allow a small set of formatting tags; drop scripts, styles and attributes."""
    paragraphs = DIV_TAG.sub(lambda match: f"<{match.group(1)}p>", markup or "")
    return EMPTY_PARAGRAPH.sub("", _clean(paragraphs, RICH_TEXT_TAGS))


def caption_to_html(text):
    """Plain text with line breaks and https links, rendered as safe HTML."""
    escaped = html.escape((text or "").strip())
    linked = URL_PATTERN.sub(r'<a href="\1">\1</a>', escaped)
    with_breaks = linked.replace("\r\n", "\n").replace("\n", "<br>")
    return _clean(with_breaks, {"a", "br"})
