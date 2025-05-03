import html
import re


def strip_markdown_v1(text: str) -> str:
    """Simple Markdown stripping function."""
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*#+\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)

    return text.strip()


def strip_markdown_v2(text: str) -> str:
    """Advanced Markdown stripping function."""
    # Inline code
    text = re.sub(r"`(.*?)`", r"\1", text)
    # Bold ** or __
    text = re.sub(r"(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1", r"\2", text)
    # Italic * or _
    text = re.sub(r"(\*|_)(?=\S)(.+?[*_]*)(?<=\S)\1", r"\1\2\1", text)
    text = re.sub(r"(\*|_)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    # Strikethrough ~~
    text = re.sub(r"(~~)(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    # Links [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Images ![alt](url) -> alt (or empty string if alt is not found)
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", text)
    # Headers (remove #)
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Blockquotes (remove >)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # List items (remove bullet/number, keep indentation roughly)
    text = re.sub(r"^\s*([*+-]|\d+\.)\s+", "  ", text, flags=re.MULTILINE)
    # Code blocks (remove fences ```)
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```\s*$", "", text, flags=re.MULTILINE)

    text = html.escape(text)

    return text.strip()


strip_markdown = strip_markdown_v2
