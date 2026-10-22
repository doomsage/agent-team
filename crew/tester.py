"""Tester: LLM nahi, asli checks. Website files exist karti hain? HTML theek hai?
Local server pe sab pages 200 dete hain? Placeholder text to nahi?"""
import functools
import http.server
import os
import re
import threading
import urllib.request
from html.parser import HTMLParser

PROJECT = os.path.join("workspace", "project")
REPORT = os.path.join("workspace", "test-report.md")


class _RefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("src", "href") and v:
                self.refs.append(v)


def _is_local(ref):
    return not re.match(r"^(https?:)?//|^data:|^mailto:|^#|^javascript:", ref)


def run_tests():
    failures = []
    notes = []

    if not os.path.isdir(PROJECT) or not os.listdir(PROJECT):
        failures.append("workspace/project/ khaali hai - coder ne koi file nahi likhi")
        _write_report(failures, notes)
        return failures

    html_files = []
    for root, _, files in os.walk(PROJECT):
        for fn in files:
            if fn.lower().endswith(".html"):
                html_files.append(os.path.join(root, fn))

    index = os.path.join(PROJECT, "index.html")
    if not os.path.exists(index):
        failures.append("index.html missing hai project folder me")
    elif html_files:
        # har HTML file parse karo + local refs check karo
        for hf in html_files:
            rel = os.path.relpath(hf, PROJECT)
            try:
                with open(hf, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                failures.append(f"{rel}: UTF-8 text nahi hai")
                continue
            parser = _RefParser()
            try:
                parser.feed(content)
            except Exception as e:
                failures.append(f"{rel}: HTML parse error: {e}")
            for ref in parser.refs:
                if _is_local(ref):
                    target = os.path.normpath(os.path.join(os.path.dirname(hf), ref.split("#")[0].split("?")[0]))
                    if ref.split("#")[0] and not os.path.exists(target):
                        failures.append(f"{rel}: '{ref}' file maujood nahi hai")
            low = content.lower()
            for bad in ("lorem ipsum", "todo:", "placeholder text"):
                if bad in low:
                    failures.append(f"{rel}: placeholder text mila ('{bad}')")
        notes.append(f"{len(html_files)} HTML file(s) parse ho gayi")

    # local server pe sab HTML pages 200 dete hain?
    if html_files:
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=PROJECT
        )
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            for hf in html_files:
                rel = os.path.relpath(hf, PROJECT).replace("\\", "/")
                url = f"http://127.0.0.1:{port}/{rel}"
                try:
                    with urllib.request.urlopen(url, timeout=10) as r:
                        if r.status != 200:
                            failures.append(f"{rel}: server ne status {r.status} diya")
                except Exception as e:
                    failures.append(f"{rel}: server se khul nahi paya ({e})")
            notes.append(f"local server pe {len(html_files)} page(s) 200 OK")
        finally:
            server.shutdown()
            server.server_close()

    _write_report(failures, notes)
    return failures


def _write_report(failures, notes):
    lines = ["# Test Report\n"]
    lines.extend(f"- PASS: {n}" for n in notes)
    if failures:
        lines.append("\n## FAILURES (coder ko fix karne hain)\n")
        lines.extend(f"- FAIL: {f}" for f in failures)
    else:
        lines.append("\n## RESULT: ALL PASS\n")
    os.makedirs("workspace", exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
