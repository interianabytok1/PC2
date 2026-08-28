"""Small, bounded web extractor used as a first connector."""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ExtractionResult:
    url: str
    title: str
    description: str
    matched_terms: tuple[str, ...]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.description = ""
        self.text_parts: list[str] = []
        self._in_title = False
        self._in_script_or_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "noscript"}:
            self._in_script_or_style = True
        if tag == "meta":
            attributes = dict(attrs)
            if attributes.get("name", "").lower() == "description":
                self.description = attributes.get("content", "") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript"}:
            self._in_script_or_style = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if not self._in_script_or_style:
            self.text_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())


def extract_page(url: str, terms: list[str], timeout: float = 15.0) -> ExtractionResult:
    """Fetch one page with a hard timeout and report matching search terms."""
    request = Request(url, headers={"User-Agent": "OberonItemExtractor/0.1"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"Zdroj nie je HTML ({content_type}).")
        page = response.read(5_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")

    parser = _PageParser()
    parser.feed(page)
    searchable_text = f"{parser.title} {parser.description} {parser.text}".lower()
    matched_terms = tuple(term for term in terms if term.lower() in searchable_text)
    return ExtractionResult(url, parser.title or url, parser.description, matched_terms)


def extract_html_document(document: str, source_label: str, terms: list[str]) -> ExtractionResult:
    """Parse pasted HTML code and report matching terms."""
    parser = _PageParser()
    parser.feed(document)
    searchable_text = f"{parser.title} {parser.description} {parser.text}".lower()
    matched_terms = tuple(term for term in terms if term.lower() in searchable_text)
    return ExtractionResult(source_label, parser.title or source_label, parser.description, matched_terms)
