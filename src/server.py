#!/usr/bin/env python3
"""Local development server and split-pane editor UI for Fluffy blog."""

import os
import re
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from flask import Flask, abort, jsonify, render_template_string, request, send_from_directory

ROOT = Path(__file__).parent.parent
BLOG_DIR = ROOT / "blog"
POSTS_DIR = BLOG_DIR / "posts"
PAGES_DIR = BLOG_DIR / "pages"
IMAGES_DIR = BLOG_DIR / "images"
OUTPUT_DIR = ROOT / "output"

app = Flask(__name__, static_folder=None)


def load_config():
    with open(BLOG_DIR / "config.yaml") as f:
        return yaml.safe_load(f)


def render_markdown(text: str) -> str:
    md = markdown.Markdown(extensions=["extra", "codehilite", "toc", "smarty"])
    return md.convert(text)


def parse_frontmatter(text: str):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return meta, body
    return {}, text


def write_post(path: Path, meta: dict, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    frontmatter = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{frontmatter}---\n\n{body}"
    path.write_text(content, encoding="utf-8")


def list_posts():
    posts = []
    for md_path in sorted(POSTS_DIR.rglob("*.md"), reverse=True):
        text = md_path.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(text)
        posts.append({
            "path": str(md_path.relative_to(ROOT)),
            "title": meta.get("title", md_path.stem),
            "date": str(meta.get("date", "")),
            "status": meta.get("status", "published"),
            "slug": meta.get("slug", md_path.stem),
        })
    return posts


EDITOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fluffy Editor</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Merriweather:300,700,700italic,300italic|Open+Sans:700,400">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400&display=swap">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/themes/prism.min.css">
  <style>
    html, body { height: 100%; margin: 0; }
    .editor-layout { display: flex; height: calc(100vh - 52px); }
    .sidebar {
      width: 260px; min-width: 220px; background: #fafafa;
      border-right: 1px solid #dbdbdb; overflow-y: auto; flex-shrink: 0;
    }
    .editor-pane { flex: 1; display: flex; flex-direction: column; }
    .preview-pane {
      flex: 1; border-left: 1px solid #dbdbdb;
      overflow-y: auto; background: #fff;
    }
    #markdown-input {
      flex: 1; resize: none; border: none; outline: none;
      padding: 1rem; font-family: 'Source Code Pro', monospace;
      font-size: 15px; line-height: 1.7;
    }
    #preview-frame { width: 100%; height: 100%; border: none; }
    .sidebar-post {
      padding: 0.5rem 0.75rem; cursor: pointer;
      border-bottom: 1px solid #efefef; font-size: 0.85rem;
    }
    .sidebar-post:hover { background: #f0f0f0; }
    .sidebar-post.active { background: #e8f4fd; border-left: 3px solid #3273dc; }
    .sidebar-post .post-status-draft { color: #f14668; font-size: 0.7rem; }
    .toolbar { display: flex; gap: 0.5rem; align-items: center; padding: 0.4rem 0.75rem; background: #f5f5f5; border-bottom: 1px solid #dbdbdb; }
    .pane-split { display: flex; flex: 1; overflow: hidden; }
    .edit-area { display: flex; flex-direction: column; overflow: hidden; }
    .divider {
      width: 5px; background: #dbdbdb; cursor: col-resize; flex-shrink: 0;
      transition: background 0.15s;
    }
    .divider:hover, .divider.dragging { background: #3273dc; }
    #title-input { border: none; border-bottom: 1px solid #dbdbdb; padding: 0.5rem 1rem; font-size: 1.2rem; font-weight: 600; outline: none; width: 100%; }
    .post-meta { display: flex; gap: 1rem; padding: 0.4rem 1rem; font-size: 0.8rem; background: #fafafa; border-bottom: 1px solid #efefef; flex-wrap: wrap; align-items: center; }
    .post-meta input { border: none; border-bottom: 1px solid #dbdbdb; font-size: 0.8rem; padding: 0.1rem 0.3rem; min-width: 100px; outline: none; }
    .preview-pane iframe { width: 100%; height: 100%; border: none; }
    #status-bar { font-size: 0.8rem; color: #666; margin-left: auto; }
  </style>
</head>
<body>

<nav class="navbar is-dark" style="height:52px;">
  <div class="navbar-brand">
    <span class="navbar-item has-text-white has-text-weight-bold" style="margin-left:7px;">
      <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 4362 2825" width="44" height="29" style="margin-right:4px;vertical-align:middle;fill-rule:evenodd;clip-rule:evenodd;">
        <g transform="matrix(0.640433,0,0,0.653679,-739.656,-1841.96)">
          <g transform="matrix(1.44329,0,0,1.41725,-1567,-2442.86)"><circle cx="2700.85" cy="5709.37" r="751.747" style="fill:rgb(246,157,203);"/></g>
          <g transform="matrix(3.62248,0,0,0.792471,-5252.23,1903.64)"><circle cx="2700.85" cy="5709.37" r="751.747" style="fill:rgb(246,157,203);"/></g>
          <g transform="matrix(2.23001,0,0,2.28246,-1604.87,-8370.28)"><circle cx="2700.85" cy="5709.37" r="751.747" style="fill:rgb(246,157,203);"/></g>
          <g transform="matrix(1.96129,0,0,1.92155,1106.84,-5586.63)"><circle cx="2700.85" cy="5709.37" r="751.747" style="fill:rgb(246,157,203);"/></g>
        </g>
      </svg>Fluffy</span>
  </div>
  <div class="navbar-menu">
    <div class="navbar-start">
      <div class="navbar-item" style="padding-left:2rem;"><button class="button is-small is-primary" onclick="newPost()">+ New Post</button></div>
    </div>
    <div class="navbar-end" style="padding-right:1rem; align-items:center; display:flex;">
      <span id="status-bar"></span>
    </div>
  </div>
</nav>

<div class="editor-layout">
  <div class="sidebar" id="sidebar">
    <div style="padding:0.5rem 0.75rem; font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.05em;">Posts</div>
    <div id="post-list"></div>
  </div>

  <div class="editor-pane">
    <input type="hidden" id="current-path" value="">
    <input id="title-input" type="text" placeholder="Post title..." oninput="onMetaChange(); schedulePreview()">
    <div class="post-meta">
      <label>Date: <input id="meta-date" type="date" oninput="onMetaChange(); schedulePreview()"></label>
      <label>Slug: <input id="meta-slug" type="text" placeholder="url-slug" oninput="onMetaChange(); if(currentStatus==='published') updateLiveLink('published')"></label>
      <label>Tags: <input id="meta-tags" type="text" placeholder="tag1, tag2" oninput="onMetaChange(); schedulePreview()"></label>
      <label>Feature image: <input id="meta-image" type="text" placeholder="/images/header.jpg" style="min-width:180px;" oninput="onMetaChange(); schedulePreview()"></label>
      <label style="cursor:pointer;">
        <span class="button is-small is-info" onclick="document.getElementById('image-upload').click()">Upload image</span>
        <input id="image-upload" type="file" accept="image/*" style="display:none;" onchange="uploadImage(this)">
      </label>
    </div>
    <div class="toolbar">
      <button class="button is-small is-light" style="border: 1px solid #aaa;" onclick="saveDraft()">Save Draft</button>
      <button class="button is-small is-success" onclick="publish()">Publish</button>
      <button class="button is-small is-warning" id="unpublish-btn" style="display:none;" onclick="unpublish()">Unpublish</button>
      <a id="live-link" href="" target="_blank" class="button is-small is-link is-light" style="display:none;">View on site ↗</a>
    </div>
    <div class="pane-split" id="pane-split">
      <div class="edit-area" id="edit-area">
        <textarea id="markdown-input" placeholder="Write your post in Markdown..." oninput="schedulePreview()"></textarea>
      </div>
      <div class="divider" id="divider"></div>
      <div class="preview-pane" id="preview-pane">
        <iframe id="preview-iframe"></iframe>
      </div>
    </div>
  </div>
</div>

<script>
let previewTimer = null;
let dirty = false;
let currentStatus = 'draft';

function setUnpublishBtn(status) {
  currentStatus = status;
  document.getElementById('unpublish-btn').style.display = (status === 'published') ? '' : 'none';
  updateLiveLink(status);
}

function updateLiveLink(status) {
  const link = document.getElementById('live-link');
  if (status === 'published') {
    const slug = document.getElementById('meta-slug').value;
    link.href = 'https://startupnextdoor.com/' + slug + '/';
    link.style.display = '';
  } else {
    link.style.display = 'none';
  }
}


function setStatus(msg, color) {
  const el = document.getElementById('status-bar');
  el.textContent = msg;
  el.style.color = color || '#666';
}

function schedulePreview() {
  dirty = true;
  clearTimeout(previewTimer);
  previewTimer = setTimeout(updatePreview, 300);
}

function uploadImage(input) {
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file);
  setStatus('Uploading image...', '#3273dc');
  fetch('/api/upload-image', {method: 'POST', body: form})
    .then(r => r.json())
    .then(data => {
      if (data.path) {
        document.getElementById('meta-image').value = data.path;
        onMetaChange();
        schedulePreview();
        setStatus('Image uploaded', '#48c78e');
      } else {
        setStatus('Upload failed: ' + data.error, '#f14668');
      }
    });
  input.value = '';
}

function formatPreviewDate(val) {
  if (!val) return '';
  const [y, m, d] = val.split('-').map(Number);
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  return months[m - 1] + ' ' + d + ', ' + y;
}

function updatePreview() {
  const md = document.getElementById('markdown-input').value;
  const title = document.getElementById('title-input').value;
  const image = document.getElementById('meta-image').value.trim();
  const dateVal = document.getElementById('meta-date').value;
  const tagsVal = document.getElementById('meta-tags').value;
  const theme = document.documentElement.getAttribute('data-theme') || 'light';
  fetch('/api/preview', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({markdown: md})
  })
  .then(r => r.json())
  .then(data => {
    const tags = tagsVal.split(',').map(t => t.trim()).filter(Boolean);
    const doc = `<!DOCTYPE html>
<html lang="en" data-theme="${theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.2/css/bulma.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/themes/prism.min.css">
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  ${image ? `<section class="hero is-medium" style="background-image:url('${image}');background-size:cover;background-position:center;"><div class="hero-body" style="background:rgba(0,0,0,0.35);"><div class="container has-text-centered"><p class="title has-text-white">${title}</p></div></div></section>` : ''}
  <section class="section">
    <div class="container">
      <div class="columns is-centered">
        <div class="column is-8">
          ${!image && title ? `<h1 class="title is-2">${title}</h1>` : ''}
          <p class="is-size-7 has-text-grey mb-3">
            <time>${dateVal ? formatPreviewDate(dateVal) : '(date TBD)'}</time>
          </p>
          ${tags.length ? `<div class="tags mb-4">${tags.map(t => `<span class="tag is-info is-light">${t}</span>`).join('')}</div>` : ''}
          <hr>
          <div class="content post-content">${data.html}</div>
        </div>
      </div>
    </div>
  </section>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/prism.min.js"><\\/script>
</body>
</html>`;
    document.getElementById('preview-iframe').srcdoc = doc;
  });
}

function onMetaChange() {
  dirty = true;
}

function collectPost() {
  const title = document.getElementById('title-input').value;
  const date = document.getElementById('meta-date').value;
  const slug = document.getElementById('meta-slug').value || slugify(title);
  const tags = document.getElementById('meta-tags').value;
  const image = document.getElementById('meta-image').value;
  const body = document.getElementById('markdown-input').value;
  return { title, date, slug, tags, image, body };
}

function slugify(s) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function saveDraft() {
  const p = collectPost();
  const path = document.getElementById('current-path').value;
  fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...p, status: 'draft', path})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('current-path').value = data.path;
    setStatus('Draft saved', '#48c78e');
    dirty = false;
    loadPostList();
  });
}

function publish() {
  const p = collectPost();
  const path = document.getElementById('current-path').value;
  setStatus('Publishing...', '#3273dc');
  fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...p, status: 'published', path})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('current-path').value = data.path;
    dirty = false;
    loadPostList();
    return fetch('/api/publish', {method: 'POST'});
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      setUnpublishBtn('published');
      setStatus('Published! ' + data.uploaded + ' file(s) uploaded', '#48c78e');
    } else {
      setStatus('Build ok, upload failed: ' + data.error, '#f14668');
    }
  });
}

function unpublish() {
  if (!confirm('Move this post back to draft and remove it from the live site?')) return;
  const p = collectPost();
  const path = document.getElementById('current-path').value;
  setStatus('Unpublishing...', '#3273dc');
  fetch('/api/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({...p, status: 'draft', path})
  })
  .then(r => r.json())
  .then(data => {
    document.getElementById('current-path').value = data.path;
    dirty = false;
    setUnpublishBtn('draft');
    loadPostList();
    return fetch('/api/publish', {method: 'POST'});
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      setStatus('Unpublished — removed from live site', '#48c78e');
    } else {
      setStatus('Saved as draft, but S3 removal failed: ' + data.error, '#f14668');
    }
  });
}

function newPost() {
  document.getElementById('current-path').value = '';
  document.getElementById('title-input').value = '';
  document.getElementById('meta-date').value = new Date().toISOString().slice(0,10);
  document.getElementById('meta-slug').value = '';
  document.getElementById('meta-tags').value = '';
  document.getElementById('meta-image').value = '';
  document.getElementById('markdown-input').value = '';
  document.getElementById('preview-iframe').srcdoc = '';
  setUnpublishBtn('draft');
  document.querySelectorAll('.sidebar-post').forEach(el => el.classList.remove('active'));
  setStatus('');
}

function loadPost(path) {
  fetch('/api/load?path=' + encodeURIComponent(path))
  .then(r => r.json())
  .then(data => {
    document.getElementById('current-path').value = path;
    document.getElementById('title-input').value = data.meta.title || '';
    document.getElementById('meta-date').value = data.meta.date || '';
    document.getElementById('meta-slug').value = data.meta.slug || '';
    document.getElementById('meta-tags').value = (data.meta.tags || []).join(', ');
    document.getElementById('meta-image').value = data.meta.feature_image || '';
    document.getElementById('markdown-input').value = data.body;
    setUnpublishBtn(data.meta.status || 'draft');
    updatePreview();
    document.querySelectorAll('.sidebar-post').forEach(el => el.classList.remove('active'));
    document.querySelector('[data-path="' + path + '"]')?.classList.add('active');
    setStatus('');
    dirty = false;
  });
}

function loadPostList() {
  fetch('/api/posts')
  .then(r => r.json())
  .then(posts => {
    const container = document.getElementById('post-list');
    container.innerHTML = posts.map(p => `
      <div class="sidebar-post" data-path="${p.path}" onclick="loadPost('${p.path}')">
        <div style="font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${p.title || p.slug}</div>
        <div style="color:#aaa; font-size:0.75rem;">${p.date}
          ${p.status === 'draft' ? '<span class="post-status-draft"> DRAFT</span>' : ''}
        </div>
      </div>
    `).join('');
    const currentPath = document.getElementById('current-path').value;
    if (currentPath) {
      document.querySelector('[data-path="' + currentPath + '"]')?.classList.add('active');
    }
  });
}

// Auto-save draft every 60s if dirty
setInterval(() => { if (dirty) saveDraft(); }, 60000);

document.addEventListener('keydown', e => {
  if ((e.metaKey || e.ctrlKey) && e.key === 's') { e.preventDefault(); saveDraft(); }
});

loadPostList();

// Resizable divider
(function() {
  const divider = document.getElementById('divider');
  const editArea = document.getElementById('edit-area');
  const previewPane = document.getElementById('preview-pane');
  const split = document.getElementById('pane-split');
  let dragging = false;

  // Set initial widths as percentages
  editArea.style.width = '50%';
  previewPane.style.flex = 'none';
  previewPane.style.width = 'calc(50% - 5px)';

  divider.addEventListener('mousedown', function(e) {
    dragging = true;
    divider.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    const rect = split.getBoundingClientRect();
    const offset = e.clientX - rect.left;
    const total = rect.width - 5; // subtract divider width
    const leftPct = Math.min(Math.max(offset / rect.width * 100, 15), 85);
    editArea.style.width = leftPct + '%';
    previewPane.style.width = (100 - leftPct) + '%';
  });

  document.addEventListener('mouseup', function() {
    if (!dragging) return;
    dragging = false;
    divider.classList.remove('dragging');
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
})();
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/components/prism-core.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.30.0/plugins/autoloader/prism-autoloader.min.js"></script>
</body>
</html>
"""


@app.route("/")
def editor():
    return render_template_string(EDITOR_HTML)


@app.route("/api/preview", methods=["POST"])
def api_preview():
    data = request.get_json()
    html = render_markdown(data.get("markdown", ""))
    return jsonify({"html": html})


@app.route("/api/posts")
def api_posts():
    return jsonify(list_posts())


@app.route("/api/load")
def api_load():
    rel_path = request.args.get("path", "")
    path = ROOT / rel_path
    if not path.exists() or not path.suffix == ".md":
        abort(404)
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    # Normalize tags
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    meta["tags"] = tags
    # Normalize date
    date_val = meta.get("date")
    if isinstance(date_val, datetime):
        meta["date"] = date_val.date().isoformat()
    elif date_val:
        meta["date"] = str(date_val)
    return jsonify({"meta": meta, "body": body})


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json()
    title = data.get("title", "Untitled")
    date_str = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    slug = data.get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    status = data.get("status", "draft")
    body = data.get("body", "")
    tags_raw = data.get("tags", "")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else tags_raw
    image = data.get("image", "")
    provided_path = data.get("path", "")

    try:
        date = datetime.fromisoformat(date_str)
    except ValueError:
        date = datetime.now()

    if provided_path:
        path = ROOT / provided_path
    else:
        path = POSTS_DIR / str(date.year) / f"{date.month:02d}" / f"{slug}.md"

    meta = {
        "title": title,
        "date": date.date().isoformat(),
        "slug": slug,
        "status": status,
    }
    if tags:
        meta["tags"] = tags
    if image:
        meta["feature_image"] = image
    meta["disqus_id"] = slug

    write_post(path, meta, body)
    return jsonify({"path": str(path.relative_to(ROOT)), "slug": slug})


@app.route("/api/publish", methods=["POST"])
def api_publish():
    try:
        from builder import build
        build(verbose=False)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Build failed: {e}"})

    try:
        from publisher import publish
        result = publish(verbose=False)
        return jsonify({"ok": True, "uploaded": result.get("uploaded", 0)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/upload-image", methods=["POST"])
def api_upload_image():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no file"})
    filename = Path(f.filename).name  # strip any path components
    dest = IMAGES_DIR / filename
    f.save(dest)
    return jsonify({"path": f"/images/{filename}"})


@app.route("/static/<path:filename>")
def static_files(filename):
    static_dir = OUTPUT_DIR / "static"
    return send_from_directory(static_dir, filename)


@app.route("/images/<path:filename>")
def image_files(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route("/preview-page/<path:filepath>")
def preview_page(filepath):
    # Serve built HTML from output/
    html_path = OUTPUT_DIR / filepath / "index.html"
    if not html_path.exists():
        html_path = OUTPUT_DIR / filepath
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    abort(404)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    port = int(os.environ.get("PORT", 8080))
    print(f"Fluffy editor running at http://localhost:{port}")
    app.run(debug=True, port=port)
