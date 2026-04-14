#!/usr/bin/env python3
"""Static site generator for Fluffy blog."""

import os
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
THEME_DIR = ROOT / "theme"
OUTPUT_DIR = ROOT / "output"
POSTS_DIR = BLOG_DIR / "posts"
PAGES_DIR = BLOG_DIR / "pages"
IMAGES_DIR = BLOG_DIR / "images"


def load_config():
    with open(BLOG_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


def parse_post(path: Path):
    """Parse a markdown file with YAML frontmatter. Returns None for drafts."""
    text = path.read_text(encoding="utf-8")

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1])
            body = parts[2].strip()
        else:
            return None
    else:
        meta = {}
        body = text

    if meta.get("status", "published") == "draft":
        return None

    md = markdown.Markdown(extensions=["extra", "codehilite", "toc", "smarty"])
    html = md.convert(body)

    # Auto-linkify bare URLs not already inside an href or src attribute
    html = re.sub(
        r'(?<= )(https?://[^\s<>"\']+)',
        r'<a href="\1" class="auto-link">\1</a>',
        html,
    )

    # Extract excerpt: first paragraph of plain text, max 300 chars
    plain = re.sub(r"<[^>]+>", "", html)
    excerpt = plain[:300].rsplit(" ", 1)[0] + "…" if len(plain) > 300 else plain

    date = meta.get("date")
    if isinstance(date, str):
        date = datetime.fromisoformat(date)
    elif not isinstance(date, datetime):
        date = datetime(2000, 1, 1)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)

    slug = meta.get("slug") or path.stem
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    known_keys = {"title", "date", "slug", "status", "feature_image", "disqus_id", "tags"}
    extra = {k: v for k, v in meta.items() if k not in known_keys}

    return {
        "title": meta.get("title", slug),
        "date": date,
        "slug": slug,
        "status": meta.get("status", "published"),
        "feature_image": meta.get("feature_image"),
        "disqus_id": meta.get("disqus_id", slug),
        "tags": tags,
        "html": html,
        "excerpt": excerpt,
        "path": path,
        **extra,
    }


def post_url(post: dict, base_url: str) -> str:
    return f"{base_url}/{post['slug']}/"


def build(verbose=True, local=False):
    config = load_config()
    base_url = "" if local else config["base_url"].rstrip("/")
    posts_per_page = config.get("posts_per_page", 10)

    out_dir = ROOT / "output-local" if local else OUTPUT_DIR

    # Provide a patched config to templates with the effective base_url
    tmpl_config = dict(config, base_url=base_url)

    env = Environment(loader=FileSystemLoader(str(THEME_DIR / "templates")))
    env.globals["now"] = datetime.now(tz=timezone.utc)
    env.globals["config"] = tmpl_config

    # Clean and recreate output
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Copy static assets
    if (THEME_DIR / "static").exists():
        shutil.copytree(THEME_DIR / "static", out_dir / "static")
    if IMAGES_DIR.exists():
        shutil.copytree(IMAGES_DIR, out_dir / "images")

    # Load and sort posts
    posts = []
    for md_path in sorted(POSTS_DIR.rglob("*.md")):
        post = parse_post(md_path)
        if post:
            post["url"] = post_url(post, base_url)
            posts.append(post)

    posts.sort(key=lambda p: p["date"], reverse=True)

    if verbose:
        print(f"Building {len(posts)} posts...")

    # Render individual posts
    post_tmpl = env.get_template("post.html")
    for i, post in enumerate(posts):
        # posts are sorted newest-first, so next=newer=lower index, prev=older=higher index
        next_post = posts[i - 1] if i > 0 else None
        prev_post = posts[i + 1] if i < len(posts) - 1 else None
        post_out = out_dir / post["slug"] / "index.html"
        post_out.parent.mkdir(parents=True, exist_ok=True)
        post_out.write_text(post_tmpl.render(post=post, next_post=next_post, prev_post=prev_post), encoding="utf-8")
        if verbose:
            print(f"  {post['date'].strftime('%Y-%m-%d')} {post['title']}")

    # Render paginated index
    index_tmpl = env.get_template("index.html")
    total_pages = max(1, (len(posts) + posts_per_page - 1) // posts_per_page)
    for page_num in range(1, total_pages + 1):
        chunk = posts[(page_num - 1) * posts_per_page : page_num * posts_per_page]
        if page_num == 1:
            out_path = out_dir / "index.html"
        else:
            out_path = out_dir / "page" / str(page_num) / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            index_tmpl.render(posts=chunk, page=page_num, has_next=page_num < total_pages),
            encoding="utf-8",
        )

    # Render tag pages
    tags: dict[str, list] = {}
    for post in posts:
        for tag in post["tags"]:
            tags.setdefault(tag, []).append(post)

    tag_tmpl = env.get_template("tag.html")
    for tag, tag_posts in tags.items():
        tag_slug = tag.lower().replace(" ", "-")
        tag_out = out_dir / "tag" / tag_slug / "index.html"
        tag_out.parent.mkdir(parents=True, exist_ok=True)
        tag_out.write_text(tag_tmpl.render(tag=tag, posts=tag_posts), encoding="utf-8")

    # Render pages
    if PAGES_DIR.exists():
        page_tmpl = env.get_template("page.html")
        for md_path in PAGES_DIR.glob("*.md"):
            pg = parse_post(md_path)
            if pg:
                pg["url"] = f"{base_url}/{pg['slug']}/"
                pg_out = out_dir / pg["slug"] / "index.html"
                pg_out.parent.mkdir(parents=True, exist_ok=True)
                pg_out.write_text(page_tmpl.render(page=pg, post_count=len(posts)), encoding="utf-8")

    # Generate RSS feed
    _build_rss(posts, tmpl_config, base_url, out_dir)

    if verbose:
        print(f"Done. Output in {out_dir}/")

    return posts


def _build_rss(posts, config, base_url, out_dir=None):
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = config["title"]
    ET.SubElement(channel, "link").text = base_url + "/"
    ET.SubElement(channel, "description").text = config.get("description", config["title"])
    ET.SubElement(channel, "language").text = "en-us"
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.set("href", base_url + "/rss.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for post in posts[:20]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = post["title"]
        ET.SubElement(item, "link").text = post["url"]
        ET.SubElement(item, "guid", isPermaLink="true").text = post["url"]
        ET.SubElement(item, "pubDate").text = post["date"].strftime("%a, %d %b %Y %H:%M:%S +0000")
        ET.SubElement(item, "description").text = post["excerpt"]

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    dest = (out_dir or OUTPUT_DIR) / "rss.xml"
    dest.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode").encode("utf-8")
    )


if __name__ == "__main__":
    import sys
    local = "--local" in sys.argv
    build(local=local)
