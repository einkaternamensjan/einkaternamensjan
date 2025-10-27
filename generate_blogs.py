from pathlib import Path
import re
import html
import sys

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
TEMPLATE = ROOT / "blog_template.html"
OUT = ROOT / "blogs.html"

def read_text_safe(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def slugify(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "-", name).strip("-").lower()
    return s or "post"

def compile_markdown(md: str) -> str:
    s = md.replace("\r\n", "\n").replace("\r", "\n")
    def repl_code(m):
        lang = (m.group(1) or "").strip()
        code = html.escape(m.group(2))
        if lang:
            return f"<pre><code class='language-{html.escape(lang)}'>{code}</code></pre>"
        return f"<pre><code>{code}</code></pre>"
    s = re.sub(r"```(\w*)\n(.*?)\n```", repl_code, s, flags=re.DOTALL)
    s = re.sub(r"^###\s*(.+)$", r"<h4>\1</h4>", s, flags=re.MULTILINE)
    s = re.sub(r"^##\s*(.+)$", r"<h3>\1</h3>", s, flags=re.MULTILINE)
    s = re.sub(r"^#\s*(.+)$", r"<h2>\1</h2>", s, flags=re.MULTILINE)
    s = re.sub(r"(https?://[^\s<]+)", r"<a href='\1'>\1</a>", s)
    parts = re.split(r"\n\s*\n", s)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if re.match(r"^<(h\d|pre|ul|ol|blockquote|p|div)", p, flags=re.I):
            out.append(p)
        else:
            p = p.replace("\n", "<br>")
            out.append(f"<p>{p}</p>")
    return "\n\n".join(out)

def extract_title(md: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", md, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^##\s+(.+)$", md, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()
    return fallback

def main():
    print("Running generate_blogs.py")
    if not BLOGS_DIR.exists():
        print(f"ERROR: blogs directory not found: {BLOGS_DIR}", file=sys.stderr)
        sys.exit(1)

    # discover markdown files
    md_files = [p for p in BLOGS_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".md" and not p.name.startswith("_")]
    if not md_files:
        print("No markdown files found in blogs/ — will write template with no posts.")
    else:
        print("Found markdown files:")
        for p in sorted(md_files):
            print(" -", p.name)

    # sort newest first
    md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    posts_fragments = []
    contents = []

    for p in md_files:
        raw = read_text_safe(p)
        title = extract_title(raw, p.stem)
        compiled = compile_markdown(raw)
        anchor = slugify(p.stem)
        fragment = f"<a id='{anchor}'></a>\n<article class='post' id='{anchor}'>\n{compiled}\n</article>"
        posts_fragments.append(fragment)
        contents.append(f"<a href='#{anchor}'>- {html.escape(title)}</a>")
        print(f"Added: {p.name} -> anchor #{anchor}")

    posts_block = "\n<hr>\n".join(posts_fragments) if posts_fragments else '<p class="translatable" data-en="No posts yet." data-de="Noch keine Beiträge.">No posts yet.</p>'
    contents_block = "<br>".join(contents)

    if not TEMPLATE.exists():
        print(f"ERROR: Template file not found: {TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    tpl = read_text_safe(TEMPLATE)

    # deterministic insertion: replace marker ###BLOGS### if present, else replace contents between
    if "###BLOGS###" in tpl:
        out_html = tpl.replace("###BLOGS###", posts_block)
    else:
        # try to replace existing previous generated block between markers if present
        if "<!-- BLOGS-START -->" in tpl and "<!-- BLOGS-END -->" in tpl:
            out_html = re.sub(r"<!-- BLOGS-START -->[\s\S]*?<!-- BLOGS-END -->", f"<!-- BLOGS-START -->\n{posts_block}\n<!-- BLOGS-END -->", tpl, count=1)
        elif "</main>" in tpl:
            out_html = tpl.replace("</main>", f"{posts_block}\n</main>")
        else:
            out_html = tpl + "\n\n" + posts_block

    if "###BLOG-CONTENTS###" in out_html:
        out_html = out_html.replace("###BLOG-CONTENTS###", contents_block)
    elif "<nav" in out_html and "</nav>" in out_html:
        out_html = re.sub(r"(<nav\b[^>]*>)([\s\S]*?)(</nav>)", lambda m: m.group(1) + "\n" + contents_block + "\n" + m.group(3), out_html, count=1)
    else:
        out_html = contents_block + "\n\n" + out_html

    # write out deterministically (overwrite)
    OUT.write_text(out_html, encoding="utf-8", errors="replace")
    print(f"Wrote {OUT} with {len(posts_fragments)} posts.")
    # show final anchors for verification
    if posts_fragments:
        print("Generated anchors:", ", ".join(re.sub(r\"^.*id='([^']+)'.*$\", r\"\\1\", frag) for frag in posts_fragments))

if __name__ == "__main__":
    main()
