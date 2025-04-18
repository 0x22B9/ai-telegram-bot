# src/utils/text_processing.py
import re
import html # Для экранирования HTML сущностей

def strip_markdown_v1(text: str) -> str:
    """
    Простая версия очистки Markdown. Удаляет основные маркеры.
    Может быть не идеальной для сложных случаев.
    """
    # Удаляем **bold** -> bold, *italic* -> italic, _italic_ -> italic
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # Удаляем `inline code` -> inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Удаляем ~~strikethrough~~ -> strikethrough
    text = re.sub(r'~~([^~]+)~~', r'\1', text)
    # Удаляем [link text](url) -> link text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Удаляем ![image alt](url) -> image alt
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
    # Удаляем маркеры списков (*, -, 1.) в начале строк
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Удаляем заголовки (#, ##) в начале строк
    text = re.sub(r'^\s*#+\s+', '', text, flags=re.MULTILINE)
    # Удаляем цитаты (>) в начале строк
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)

    return text.strip() # Убираем пробелы по краям

def strip_markdown_v2(text: str) -> str:
    """
    Более продвинутая версия очистки Markdown с использованием более точных regex
    и сохранением некоторой структуры (например, новых строк).
    """
    # Inline code
    text = re.sub(r'`(.*?)`', r'\1', text)
    # Bold ** or __
    text = re.sub(r'(\*\*|__)(?=\S)(.+?[*_]*)(?<=\S)\1', r'\2', text)
    # Italic * or _
    text = re.sub(r'(\*|_)(?=\S)(.+?[*_]*)(?<=\S)\1', r'\1\2\1', text) # Сначала заменим на что-то временное или оставим как есть? Лучше убрать маркеры.
    text = re.sub(r'(\*|_)(?=\S)(.+?)(?<=\S)\1', r'\2', text) # Убираем маркеры *курсива* и _курсива_
    # Strikethrough ~~
    text = re.sub(r'(~~)(?=\S)(.+?)(?<=\S)\1', r'\2', text)
    # Links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Images ![alt](url) -> alt (или пустая строка если alt нет)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    # Headers (remove #)
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Blockquotes (remove >)
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # List items (remove bullet/number, keep indentation roughly)
    text = re.sub(r'^\s*([*+-]|\d+\.)\s+', '  ', text, flags=re.MULTILINE) # Заменяем маркер на пару пробелов
    # Code blocks (remove fences ```)
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)

    # --- Очистка HTML сущностей ---
    # Экранируем базовые HTML сущности, которые могли остаться или быть в исходном тексте
    # Это ВАЖНО для parse_mode="HTML"
    text = html.escape(text)

    return text.strip()

# Используем вторую, более надежную версию
strip_markdown = strip_markdown_v2