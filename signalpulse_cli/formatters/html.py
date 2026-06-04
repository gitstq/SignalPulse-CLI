"""
HTML output formatter for SignalPulse-CLI.

Generates standalone HTML reports from signal data with embedded
CSS styling, suitable for viewing in web browsers or sharing.
"""

from typing import Any, Dict, List, Optional

from ..config import Config
from ..sources.base import SignalItem
from ..utils import format_relative_time, format_number, extract_domain, utc_now


# Embedded CSS stylesheet for the HTML report
CSS_STYLES = """
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #1a1a2e;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background-color: #f8f9fa;
}
.header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    margin-bottom: 30px;
}
.header h1 {
    margin: 0 0 10px 0;
    font-size: 28px;
}
.header .meta {
    opacity: 0.85;
    font-size: 14px;
}
.source-summary {
    display: flex;
    gap: 15px;
    margin-bottom: 30px;
    flex-wrap: wrap;
}
.source-badge {
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 14px;
}
.source-badge.hackernews { background: #ff6600; color: white; }
.source-badge.reddit { background: #ff4500; color: white; }
.source-badge.github { background: #24292e; color: white; }
.source-badge.producthunt { background: #da552f; color: white; }
table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}
th {
    background: #2d3436;
    color: white;
    padding: 12px 16px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
td {
    padding: 12px 16px;
    border-bottom: 1px solid #eee;
    font-size: 14px;
}
tr:hover {
    background-color: #f5f6fa;
}
.score-bar {
    display: inline-block;
    height: 8px;
    border-radius: 4px;
    min-width: 20px;
}
.score-high { background: linear-gradient(90deg, #e74c3c, #c0392b); }
.score-medium { background: linear-gradient(90deg, #f39c12, #e67e22); }
.score-low { background: linear-gradient(90deg, #2ecc71, #27ae60); }
.title-cell {
    max-width: 500px;
}
.title-cell a {
    color: #667eea;
    text-decoration: none;
    font-weight: 500;
}
.title-cell a:hover {
    text-decoration: underline;
}
.domain {
    color: #636e72;
    font-size: 12px;
}
.age {
    color: #636e72;
    font-size: 12px;
    white-space: nowrap;
}
.briefing-section {
    background: white;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}
.briefing-section h2 {
    color: #667eea;
    border-bottom: 2px solid #667eea;
    padding-bottom: 10px;
    margin-top: 0;
}
.briefing-section h3 {
    color: #2d3436;
}
.briefing-section p {
    color: #2d3436;
}
.briefing-section ul, .briefing-section ol {
    color: #2d3436;
}
.footer {
    text-align: center;
    color: #636e72;
    font-size: 12px;
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #dee2e6;
}
""".strip()


class HTMLFormatter:
    """HTML report formatter.

    Generates standalone, styled HTML documents from signal data
    and AI briefings. The output includes embedded CSS and requires
    no external dependencies.

    Attributes:
        config: Application configuration.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the HTML formatter.

        Args:
            config: Application configuration.
        """
        self.config = config

    def render_items(
        self, items: List[SignalItem], title: str = "Signal Pulse Report"
    ) -> str:
        """Render signal items as a complete HTML document.

        Generates a styled HTML page with a header, source summary
        badges, data table, and footer.

        Args:
            items: List of scored SignalItem objects.
            title: Report title.

        Returns:
            Complete HTML document as a string.
        """
        html_parts: List[str] = []

        # HTML head
        html_parts.append(self._render_head(title))

        # Header
        html_parts.append(self._render_header(title, len(items)))

        # Source summary badges
        source_counts: Dict[str, int] = {}
        for item in items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
        html_parts.append(self._render_source_badges(source_counts))

        # Items table
        html_parts.append(self._render_table(items))

        # Detailed listings
        html_parts.append(self._render_details(items))

        # Footer
        html_parts.append(self._render_footer())

        # Close body/html
        html_parts.append("</body>\n</html>")

        return "\n".join(html_parts)

    def render_briefing(self, briefing: str) -> str:
        """Render an AI briefing as an HTML document.

        Converts the Markdown briefing to basic HTML for display.

        Args:
            briefing: Markdown-formatted briefing text.

        Returns:
            Complete HTML document with the briefing.
        """
        html_parts: List[str] = []
        html_parts.append(self._render_head("AI Intelligence Briefing"))
        html_parts.append(self._render_header("AI Intelligence Briefing", None))

        # Convert basic markdown to HTML
        briefing_html = self._markdown_to_html(briefing)
        html_parts.append(
            f'<div class="briefing-section">{briefing_html}</div>'
        )

        html_parts.append(self._render_footer())
        html_parts.append("</body>\n</html>")
        return "\n".join(html_parts)

    def render_full_report(
        self, items: List[SignalItem], briefing: Optional[str] = None
    ) -> str:
        """Render a complete report with items and optional AI briefing.

        Args:
            items: List of scored SignalItem objects.
            briefing: Optional AI briefing text.

        Returns:
            Complete HTML report document.
        """
        report = self.render_items(
            items, title="SignalPulse Intelligence Report"
        )

        if briefing:
            briefing_html = self._markdown_to_html(briefing)
            report += (
                f'\n<div class="briefing-section">\n'
                f'<h2>AI Intelligence Briefing</h2>\n'
                f'{briefing_html}\n'
                f'</div>\n'
            )

        return report

    def _render_head(self, title: str) -> str:
        """Render the HTML head section with embedded CSS.

        Args:
            title: Page title.

        Returns:
            HTML head element string.
        """
        return (
            f"<!DOCTYPE html>\n"
            f'<html lang="en">\n'
            f"<head>\n"
            f'<meta charset="UTF-8">\n'
            f'<meta name="viewport" content="width=device-width, '
            f'initial-scale=1.0">\n'
            f"<title>{self._escape_html(title)}</title>\n"
            f"<style>\n{CSS_STYLES}\n</style>\n"
            f"</head>\n"
            f"<body>\n"
        )

    def _render_header(
        self, title: str, count: Optional[int]
    ) -> str:
        """Render the report header section.

        Args:
            title: Header title.
            count: Number of items, or None for briefings.

        Returns:
            HTML header div string.
        """
        meta = ""
        if count is not None:
            meta = f"{count} signals aggregated | "
        meta += utc_now().strftime("%Y-%m-%d %H:%M UTC")

        return (
            f'<div class="header">\n'
            f"<h1>{self._escape_html(title)}</h1>\n"
            f'<div class="meta">{meta}</div>\n'
            f"</div>\n"
        )

    def _render_source_badges(
        self, source_counts: Dict[str, int]
    ) -> str:
        """Render source summary as colored badges.

        Args:
            source_counts: Mapping of source name to item count.

        Returns:
            HTML div with source badges.
        """
        if not source_counts:
            return ""

        badges: List[str] = []
        for source, count in sorted(
            source_counts.items(), key=lambda x: -x[1]
        ):
            label = source.capitalize()
            badges.append(
                f'<span class="source-badge {source}">'
                f"{label}: {count}</span>"
            )

        return (
            f'<div class="source-summary">\n'
            + "\n".join(badges)
            + "\n</div>\n"
        )

    def _render_table(self, items: List[SignalItem]) -> str:
        """Render items as an HTML table.

        Args:
            items: List of SignalItem objects.

        Returns:
            HTML table element string.
        """
        rows: List[str] = []

        # Table header
        rows.append(
            "<table>\n<thead>\n<tr>"
            "<th>#</th>"
            "<th>Source</th>"
            "<th>Score</th>"
            "<th>Title</th>"
            "<th>Domain</th>"
            "<th>Age</th>"
            "<th>Comments</th>"
            "</tr>\n</thead>\n<tbody>"
        )

        # Table rows
        for i, item in enumerate(items, 1):
            source = item.source.capitalize()
            score_pct = item.normalized_score * 100
            score_class = (
                "score-high" if item.normalized_score >= 0.7
                else "score-medium" if item.normalized_score >= 0.4
                else "score-low"
            )
            title = self._escape_html(item.title[:100])
            url = self._escape_html(item.url or "")
            domain = self._escape_html(
                extract_domain(item.url) if item.url else "-"
            )
            age = format_relative_time(item.created_at)
            comments = format_number(item.comments)

            rows.append(
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><span class='source-badge {item.source}' "
                f"style='padding: 3px 8px; font-size: 11px;'>"
                f"{source}</span></td>"
                f"<td>"
                f'<div class="score-bar {score_class}" '
                f'style="width: {max(score_pct, 10)}px"></div> '
                f"{score_pct:.0f}%"
                f"</td>"
                f'<td class="title-cell">'
                f'<a href="{url}" target="_blank" rel="noopener">'
                f"{title}</a></td>"
                f'<td class="domain">{domain}</td>'
                f'<td class="age">{age}</td>'
                f"<td>{comments}</td>"
                f"</tr>"
            )

        rows.append("</tbody>\n</table>")
        return "\n".join(rows)

    def _render_details(self, items: List[SignalItem]) -> str:
        """Render detailed item listings as HTML sections.

        Args:
            items: List of SignalItem objects.

        Returns:
            HTML string with detailed item cards.
        """
        sections: List[str] = []
        sections.append('<h2 style="margin-top: 30px;">Detailed Listings</h2>')

        for i, item in enumerate(items, 1):
            title = self._escape_html(item.title)
            url = self._escape_html(item.url or "#")
            domain = self._escape_html(
                extract_domain(item.url) if item.url else ""
            )

            details_parts = [
                f'<div class="briefing-section">',
                f'<h3>{i}. <a href="{url}" target="_blank" '
                f'rel="noopener">{title}</a></h3>',
                f'<p><strong>Source:</strong> {item.source.capitalize()} | '
                f'<strong>Score:</strong> {item.normalized_score:.1%} | '
                f'<strong>Comments:</strong> {item.comments} | '
                f'<strong>Age:</strong> {format_relative_time(item.created_at)}',
            ]

            if item.author:
                details_parts.append(
                    f' | <strong>Author:</strong> {self._escape_html(item.author)}'
                )

            details_parts.append("</p>")

            # Source-specific metadata
            if item.source == "github":
                lang = item.metadata.get("language", "Unknown")
                stars = item.metadata.get("stars", 0)
                forks = item.metadata.get("forks", 0)
                details_parts.append(
                    f'<p>Language: {self._escape_html(lang)} | '
                    f'Stars: {format_number(stars)} | '
                    f'Forks: {format_number(forks)}</p>'
                )
            elif item.source == "reddit":
                subreddit = item.metadata.get("subreddit", "")
                if subreddit:
                    details_parts.append(
                        f'<p>Subreddit: r/{self._escape_html(subreddit)}</p>'
                    )
            elif item.source == "producthunt":
                topics = item.metadata.get("topics", [])
                if topics:
                    topics_str = ", ".join(
                        self._escape_html(t) for t in topics[:5]
                    )
                    details_parts.append(f"<p>Topics: {topics_str}</p>")

            details_parts.append("</div>")
            sections.append("\n".join(details_parts))

        return "\n".join(sections)

    def _render_footer(self) -> str:
        """Render the page footer.

        Returns:
            HTML footer element string.
        """
        return (
            f'<div class="footer">\n'
            f"Generated by SignalPulse-CLI | "
            f"{utc_now().strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"</div>\n"
        )

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape special HTML characters.

        Args:
            text: Raw text to escape.

        Returns:
            HTML-safe string.
        """
        replacements = [
            ("&", "&amp;"),
            ("<", "&lt;"),
            (">", "&gt;"),
            ('"', "&quot;"),
            ("'", "&#x27;"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    @staticmethod
    def _markdown_to_html(md_text: str) -> str:
        """Convert basic Markdown to HTML.

        Handles headings (##, ###), bold, italic, lists, and
        paragraphs. Not a full Markdown parser but covers the
        common elements used in AI briefings.

        Args:
            md_text: Markdown-formatted text.

        Returns:
            HTML-formatted text.
        """
        import re

        html = md_text
        lines = html.split("\n")
        result: List[str] = []
        in_list = False

        for line in lines:
            stripped = line.strip()

            # Headings
            if stripped.startswith("### "):
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(
                    f"<h3>{stripped[4:]}</h3>"
                )
                continue
            elif stripped.startswith("## "):
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(
                    f"<h2>{stripped[3:]}</h2>"
                )
                continue
            elif stripped.startswith("# "):
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append(
                    f"<h1>{stripped[2:]}</h1>"
                )
                continue

            # List items
            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    result.append("<ul>")
                    in_list = True
                content = stripped[2:]
                result.append(f"<li>{content}</li>")
                continue
            elif re.match(r"^\d+\.\s", stripped):
                if not in_list:
                    result.append("<ol>")
                    in_list = True
                content = re.sub(r"^\d+\.\s", "", stripped)
                result.append(f"<li>{content}</li>")
                continue

            # Close list if we hit a non-list line
            if in_list and stripped:
                result.append("</ul>" if not re.match(r"^\d+\.\s", stripped) else "</ol>")
                in_list = False

            # Horizontal rule
            if stripped in ("---", "***", "___"):
                result.append("<hr>")
                continue

            # Empty line
            if not stripped:
                if in_list:
                    result.append("</ul>")
                    in_list = False
                continue

            # Regular paragraph
            # Apply inline formatting
            content = re.sub(
                r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped
            )
            content = re.sub(
                r"\*(.+?)\*", r"<em>\1</em>", content
            )
            content = re.sub(
                r"`(.+?)`", r"<code>\1</code>", content
            )
            result.append(f"<p>{content}</p>")

        if in_list:
            result.append("</ul>")

        return "\n".join(result)
