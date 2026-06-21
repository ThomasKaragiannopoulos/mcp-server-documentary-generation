"""
Research tool — fetches Wikipedia content on a topic and builds a structured outline.
Saves output to research/{slug}/outline.txt and returns the content.
"""

import re
import os
import wikipediaapi

WIKI_LANG = "el"  # Greek Wikipedia first
WIKI_LANG_FALLBACK = "en"
MAX_SECTIONS = 12


def _slug(topic: str) -> str:
    return re.sub(r"[^\w]", "_", topic.strip().lower())[:60]


def _fetch_article(topic: str, lang: str) -> wikipediaapi.WikipediaPage | None:
    wiki = wikipediaapi.Wikipedia(
        language=lang,
        user_agent="mcp-server-documentary-generation/0.1"
    )
    page = wiki.page(topic)
    return page if page.exists() else None


def _build_outline(page: wikipediaapi.WikipediaPage, lang: str) -> str:
    lines = [
        f"# {page.title}",
        f"Source: {page.fullurl} (Wikipedia/{lang.upper()})",
        "",
        "## Summary",
        page.summary[:1500],
        "",
        "## Sections",
    ]

    count = 0
    for section in page.sections:
        if count >= MAX_SECTIONS:
            break
        if not section.text.strip():
            continue
        lines.append(f"\n### {section.title}")
        lines.append(section.text[:800])
        count += 1

    return "\n".join(lines)


def research(topic: str) -> dict:
    """
    Fetch Wikipedia content for a topic and save structured outline to disk.
    Tries Greek Wikipedia first, falls back to English.

    Returns:
        {"path": str, "outline": str, "lang": str}
    """
    page = _fetch_article(topic, WIKI_LANG)
    lang = WIKI_LANG

    if not page:
        page = _fetch_article(topic, WIKI_LANG_FALLBACK)
        lang = WIKI_LANG_FALLBACK

    if not page:
        return {"error": f"No Wikipedia article found for: {topic}"}

    outline = _build_outline(page, lang)

    slug = _slug(topic)
    out_dir = os.path.join("research", slug)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "outline.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(outline)

    return {
        "path": out_path,
        "lang": lang,
        "title": page.title,
        "outline": outline,
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    topic = " ".join(sys.argv[1:]) or "Άλωση της Κωνσταντινούπολης"
    result = research(topic)
    if "error" in result:
        print(result["error"])
    else:
        print(f"Saved to: {result['path']} (Wikipedia/{result['lang'].upper()})")
        print(result["outline"][:500])
