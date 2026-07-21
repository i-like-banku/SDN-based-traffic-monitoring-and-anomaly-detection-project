import json, re, subprocess, sys

PDF = "/home/claude/sdn_ids/docs/Project_Report.pdf"
MAIN = "/home/claude/sdn_ids/scripts/doc/main.js"
OUT = "/home/claude/sdn_ids/scripts/doc/tocpages.json"

txt = subprocess.check_output(["pdftotext", "-layout", PDF, "-"]).decode("utf-8", "ignore")
pages = txt.split("\f")

def norm(s):
    # normalise unicode punctuation and whitespace but PRESERVE CASE, so an
    # ALL-CAPS heading is not matched by a title-case prose mention of it.
    s = s.replace("\u2019", "'").replace("\u2014", ",").replace("\u2013", "-")
    return re.sub(r"\s+", " ", s).strip()

npages = [norm(p) for p in pages]

def is_toc_page(raw):
    if "TABLE OF CONTENTS" in norm(raw):
        return True
    return len(re.findall(r"\.{5,}", raw)) >= 12   # dot-leader density

toc_pages = set(i for i, raw in enumerate(pages) if is_toc_page(raw))

src = open(MAIN, encoding="utf-8").read()
block = src.split("const TOC = [", 1)[1].split("];", 1)[0]
entries = re.findall(r'\["((?:[^"\\]|\\.)*)",\s*(\d)\]', block)
entries = [(e[0].encode().decode("unicode_escape"), int(e[1])) for e in entries]

result = {}
for text, level in entries:
    key = norm(text)
    found = ""
    for i, p in enumerate(npages):
        if i in toc_pages:
            continue
        if key in p:
            found = i + 1
            break
    if found == "":
        print("NOT FOUND:", text, file=sys.stderr)
    result[text] = found

json.dump(result, open(OUT, "w"), indent=0)
print("wrote", OUT, "-", len([v for v in result.values() if v != ""]),
      "of", len(entries), "found")
