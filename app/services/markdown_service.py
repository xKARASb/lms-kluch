import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension

class MarkdownService:
    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'extra',
                'abbr',
                'attr_list',
                'def_list',
                'fenced_code',
                'footnotes',
                'md_in_html',
                'tables',
                'admonition',
                'codehilite',
                'legacy_attrs',
                'legacy_em',
                'meta',
                'nl2br',
                'sane_lists',
                'smarty',
                'toc',
                'wikilinks'
            ]
        )
    
    def convert_to_html(self, markdown_text: str) -> str:
        """Конвертирует Markdown в HTML"""
        return self.md.convert(markdown_text)
    
    def sanitize_markdown(self, markdown_text: str) -> str:
        """Очищает Markdown от потенциально опасного содержимого"""
        # В реальном проекте добавьте здесь sanitization логику
        # Например, используйте библиотеку like bleach
        return markdown_text