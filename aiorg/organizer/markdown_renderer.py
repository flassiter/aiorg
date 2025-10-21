"""
Markdown to HTML renderer with styling.

This module provides markdown rendering functionality for the note organizer,
converting markdown text to styled HTML suitable for display in QTextBrowser.
"""

import logging
import markdown

logger = logging.getLogger(__name__)


# Dark theme CSS for rendered markdown
DARK_THEME_CSS = """
<style>
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    padding: 10px;
    color: #e0e0e0;
    background-color: #2b2b2b;
    margin: 0;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
    color: #f0f0f0;
}

h1 {
    font-size: 2em;
    border-bottom: 1px solid #444;
    padding-bottom: 0.3em;
}

h2 {
    font-size: 1.5em;
    border-bottom: 1px solid #444;
    padding-bottom: 0.3em;
}

h3 {
    font-size: 1.25em;
}

h4 {
    font-size: 1em;
}

h5 {
    font-size: 0.875em;
}

h6 {
    font-size: 0.85em;
    color: #b0b0b0;
}

p {
    margin-top: 0;
    margin-bottom: 16px;
}

a {
    color: #58a6ff;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

code {
    background-color: #3a3a3a;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.9em;
    color: #f0f0f0;
}

pre {
    background-color: #3a3a3a;
    padding: 16px;
    border-radius: 6px;
    overflow-x: auto;
    margin-bottom: 16px;
    border: 1px solid #444;
}

pre code {
    background-color: transparent;
    padding: 0;
    border-radius: 0;
    font-size: 0.85em;
    line-height: 1.45;
}

blockquote {
    margin: 0;
    padding: 0 1em;
    color: #b0b0b0;
    border-left: 4px solid #444;
    margin-bottom: 16px;
}

ul, ol {
    margin-top: 0;
    margin-bottom: 16px;
    padding-left: 2em;
}

li {
    margin-top: 0.25em;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 16px;
}

table th, table td {
    padding: 6px 13px;
    border: 1px solid #444;
}

table th {
    font-weight: 600;
    background-color: #3a3a3a;
}

table tr:nth-child(even) {
    background-color: #333;
}

hr {
    border: 0;
    border-top: 1px solid #444;
    margin: 24px 0;
}

img {
    max-width: 100%;
    height: auto;
}

strong {
    font-weight: 600;
}

em {
    font-style: italic;
}
</style>
"""


def render_markdown(text: str) -> str:
    """
    Convert markdown text to HTML with dark theme styling.

    Args:
        text: Markdown source text

    Returns:
        str: HTML output with embedded CSS styling

    Example:
        >>> html = render_markdown("# Hello\\n\\nThis is **bold** text.")
        >>> print(html)
        <style>...</style><h1>Hello</h1><p>This is <strong>bold</strong> text.</p>
    """
    try:
        # Convert markdown to HTML using the 'extra' extension
        # The 'extra' extension includes:
        # - Tables
        # - Fenced code blocks
        # - Footnotes
        # - Attribute lists
        # - Definition lists
        # - And more
        md = markdown.Markdown(extensions=['extra'])
        html_body = md.convert(text)

        # Combine CSS and HTML
        html_output = DARK_THEME_CSS + html_body

        logger.debug(f"Rendered markdown: {len(text)} chars -> {len(html_output)} chars HTML")

        return html_output

    except Exception as e:
        logger.error(f"Failed to render markdown: {e}", exc_info=True)
        # Return plain text in error case
        return f"<pre>{text}</pre>"


if __name__ == "__main__":
    # Standalone test
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test markdown rendering
    test_markdown = """
# Test Heading 1

## Test Heading 2

This is a paragraph with **bold** and *italic* text.

### Code Example

Here's some inline `code` and a code block:

```python
def hello_world():
    print("Hello, World!")
```

### Lists

- Item 1
- Item 2
  - Nested item
  - Another nested item
- Item 3

1. First
2. Second
3. Third

### Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
| Data 4   | Data 5   | Data 6   |

### Blockquote

> This is a blockquote.
> It can span multiple lines.

---

End of test.
"""

    print("Testing markdown renderer...")
    html = render_markdown(test_markdown)
    print("\nGenerated HTML:")
    print(html)
    print(f"\nHTML length: {len(html)} characters")
    print("\nTest completed successfully!")
