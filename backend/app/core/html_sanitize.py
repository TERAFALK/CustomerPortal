"""HTML-sanitering av otillförlitligt innehåll (t.ex. inkommande e-post).

Inkommande supportmail innehåller godtycklig HTML och renderas sedan i portalen.
Utan sanering är det en lagrad XSS-vektor. All HTML från externa källor ska
passera `sanitize_html` innan den sparas.
"""

import bleach

# Tillåtna taggar — räcker för normal mailformatering, inga script/style/iframe.
_ALLOWED_TAGS = [
    "p", "br", "div", "span", "b", "strong", "i", "em", "u", "s", "strike",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "a", "img", "table", "thead", "tbody", "tr", "td", "th",
    "hr", "small", "sub", "sup",
]

_ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "*": ["style"],
}

# Endast säkra URL-scheman (blockerar bl.a. javascript:).
_ALLOWED_PROTOCOLS = ["http", "https", "mailto", "cid", "data"]

# Begränsa inline-style till ofarliga egenskaper.
_ALLOWED_CSS = [
    "color", "background-color", "font-weight", "font-style", "text-align",
    "text-decoration", "font-size", "margin", "padding", "border",
]

try:
    from bleach.css_sanitizer import CSSSanitizer
    _CSS_SANITIZER = CSSSanitizer(allowed_css_properties=_ALLOWED_CSS)
except Exception:  # äldre bleach utan css_sanitizer
    _CSS_SANITIZER = None


def sanitize_html(raw: str | None) -> str:
    """Returnerar en saniterad version av godtycklig HTML. Tom sträng om None."""
    if not raw:
        return ""
    kwargs = dict(
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    if _CSS_SANITIZER is not None:
        kwargs["css_sanitizer"] = _CSS_SANITIZER
    return bleach.clean(raw, **kwargs)
