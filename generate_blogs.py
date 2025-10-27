import os
import re
from pathlib import Path

ROOT = Path(__file__).parent
BLOGS_DIR = ROOT / "blogs"
TEMPLATE_FILE = ROOT / "blog_template.html"
OUT_FILE = ROOT / "blogs.html"

# Get all markdown files in the blogs folder,
# ignoring those which start with underscore.
if not BLOGS_DIR.exists():
    print(f"blogs folder not found: {BLOGS_DIR}")
    raise SystemExit(1)

blog_paths = [p.name for p in BLOGS_DIR.iterdir()
              if p.suffix == ".md" and not p.name.startswith("_")]

# Start with the latest blog
blog_paths = list(reversed(blog_paths))

blogs = []
for blog_path in blog_paths:
    path = BLOGS_DIR / blog_path
    # read as utf-8 and replace invalid bytes rather than crashing
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    blogs.append(content)

if not TEMPLATE_FILE.exists():
    print(f"Template not found: {TEMPLATE_FILE}")
    raise SystemExit(1)

with TEMPLATE_FILE.open("r", encoding="utf-8", errors="replace") as fh:
    template = fh.read()

# Replace markdown with HTML tags
def compile_markdown(markdown: str):
    out = markdown
    out = re.sub(r"### (.+?)\n", r"<h4>\1</h4>\n", out)
    out = re.sub(r"## (.+?)\n", r"<h3>\1</h3>\n", out)
    out = re.sub(r"https://([^\s<]+)(\s)", r"<a href='https://\1'>https://\1</a>\2", out)
    # handle fenced code blocks before turning newlines into <br>
    out = re.sub(r"```hs\n(.*?)```", r"<pre><code class='language-haskell'>\1</code></pre>", out, flags=re.DOTALL)
    out = re.sub(r"```(.*?)```", lambda m: "<pre><code>{}</code></pre>".format(m.group(1)), out, flags=re.DOTALL)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = out.replace("\n", "<br>")
    return out

# Inline testing
assert compile_markdown("```hello```") == "<pre><code>hello</code></pre>"
# function replaces trailing newline with <br>, adjust expected strings accordingly
assert compile_markdown("## Title\n") == "<h3>Title</h3><br>"
assert compile_markdown("### Subtitle\n") == "<h4>Subtitle</h4><br>"

blogs_compiled = list(map(compile_markdown, blogs))

# Create the contents page at the top of the
# blog which links to each blog on the page
blog_contents = [f"<a href='#{name}'>- {name}</a>" for name in blog_paths]
blogs_with_anchors = [f"<a name='{name}'></a>{blog}"
                       for (name, blog) in zip(blog_paths, blogs_compiled)]

blog_html = template.replace("###BLOGS###", "\n<hr>\n".join(blogs_with_anchors))
blog_html = blog_html.replace("###BLOG-CONTENTS###", "<br>".join(blog_contents))

with OUT_FILE.open("w", encoding="utf-8", errors="replace") as fh:
    fh.write(blog_html)

print(f"Wrote {OUT_FILE} with {len(blogs_compiled)} posts.")
