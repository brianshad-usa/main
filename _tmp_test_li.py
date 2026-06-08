import linkedin_post

# 1) Escaper: reserved chars escaped, '#' preserved for hashtags, newlines kept
s = "Costs (a lot) for SMBs [really] {yes} <now> @ ~ _ * | \\ end\n#ManagedIT #LA"
esc = linkedin_post._escape_commentary(s)
print("ESCAPED:", repr(esc))
assert "\\(" in esc and "\\)" in esc and "\\[" in esc and "\\<" in esc
assert "\\@" in esc and "\\~" in esc and "\\_" in esc and "\\*" in esc and "\\|" in esc
assert "\\\\" in esc                 # backslash doubled
assert "#ManagedIT" in esc          # hashtag NOT escaped
assert "\n" in esc                  # newline preserved

# 2) Parser: replicate the exact logic from generate_blog.py
sample = """TITLE: Managed IT in LA 2026
META: A short meta description about managed IT services for LA businesses here.
LINKEDIN:
Tired of IT that only reacts after something breaks?

Here is why LA businesses are switching to managed IT in 2026.

#ManagedIT #Cybersecurity #LosAngeles
CONTENT:
<p>First paragraph.</p>
<h2>A heading</h2>
<p>Second paragraph.</p>"""

lines = sample.strip().split('\n')
title = ""; meta = ""; caption_lines = []; content_lines = []; state = None
for line in lines:
    if line.startswith("TITLE:"):
        title = line.split("TITLE:", 1)[1].strip(); state = None
    elif line.startswith("META:"):
        meta = line.split("META:", 1)[1].strip(); state = None
    elif line.startswith("LINKEDIN:"):
        first = line.split("LINKEDIN:", 1)[1].strip()
        if first: caption_lines.append(first)
        state = "linkedin"
    elif line.startswith("CONTENT:"):
        state = "content"
    elif state == "content":
        content_lines.append(line)
    elif state == "linkedin":
        caption_lines.append(line)
caption = '\n'.join(caption_lines).strip()
content = '\n'.join(content_lines).strip()

print("TITLE:", repr(title))
print("META :", repr(meta))
print("CAPTION:\n" + caption)
print("CONTENT:\n" + content)

assert title == "Managed IT in LA 2026"
assert meta.startswith("A short meta")
assert caption.startswith("Tired of IT")
assert caption.rstrip().endswith("#LosAngeles")
assert "Here is why LA businesses" in caption
assert content.startswith("<p>First paragraph.</p>")
assert content.endswith("<p>Second paragraph.</p>")
assert "LINKEDIN" not in content and "CONTENT" not in caption

# 3) Body builder shape
body = linkedin_post._build_post_body("urn:li:organization:999", caption, "https://x/y.html", "T", meta)
assert body["author"] == "urn:li:organization:999"
assert body["content"]["article"]["source"].endswith("y.html")
assert body["lifecycleState"] == "PUBLISHED"

print("\nALL_TESTS_PASSED")
