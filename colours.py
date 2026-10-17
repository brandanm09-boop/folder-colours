#!/usr/bin/env python3
"""Folder Colours: give each VS Code folder its own colours.

Run it, a page opens, click a look. It saves into <folder>/.vscode/settings.json and VS Code
repaints that folder's window straight away. Works with the Claude Code chat panel too.

  python3 colours.py                  colour the folder you are in
  python3 colours.py ~/Work/*OS       colour several folders from one page
  python3 colours.py --no-open ...    do not open the browser, just print the link

Only three settings are touched: workbench.colorCustomizations, chat.fontFamily and
chat.fontSize. Every other setting in the file is kept. The first time it edits a settings
file it did not make, it keeps a copy alongside as settings.before-folder-colours.json.
Needs Python 3 and nothing else. Stop it with Ctrl+C.
"""
import http.server, json, os, re, sys, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = "// Folder Colours: "
OURS = ("workbench.colorCustomizations", "chat.fontFamily", "chat.fontSize")
HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")
FONT = re.compile(r"^[A-Za-z0-9 ._-]{1,60}$")
PORT = 7317
HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')


def load_jsonc(text):
    """Read a VS Code settings file: allows // and /* */ comments and trailing commas."""
    out, i, n, quote = [], 0, len(text), False
    while i < n:
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if ch == '"': quote = False
            i += 1; continue
        if ch == '"':
            quote = True; out.append(ch); i += 1; continue
        if text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j; continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        out.append(ch); i += 1
    clean = re.sub(r",(\s*[}\]])", r"\1", "".join(out)).strip()
    data = json.loads(clean) if clean else {}
    if not isinstance(data, dict): raise ValueError("settings.json is not a {...} object")
    return data


def settings_file(folder):
    return os.path.join(folder, ".vscode", "settings.json")


def read_folder(folder):
    path, picks = settings_file(folder), None
    if os.path.exists(path):
        m = re.search(r"^// Folder Colours: (\{.*\})\s*$", open(path, encoding="utf-8").read(), re.M)
        if m:
            try: picks = json.loads(m.group(1))
            except ValueError: picks = None
    return {"name": os.path.basename(folder.rstrip("/")) or folder, "path": folder, "picks": picks}


def clean_picks(p):
    if p is None: return None
    for k in ("border", "bg", "hl"):
        if not HEX.match(str(p.get(k, ""))): raise ValueError(f"bad colour for {k}")
    if p.get("text") != "auto" and not HEX.match(str(p.get("text", ""))): raise ValueError("bad text colour")
    lines = str(p.get("lines", "auto")).lower()
    if lines != "auto" and not HEX.match(lines): raise ValueError("bad lines colour")
    font, size = str(p.get("font", "default")), int(p.get("size", 13))
    if not FONT.match(font): raise ValueError("bad font name")
    if not 8 <= size <= 40: raise ValueError("bad text size")
    return {"look": p.get("look") if isinstance(p.get("look"), str) else None, "border": p["border"].lower(),
            "bg": p["bg"].lower(), "text": p["text"].lower(), "lines": lines, "hl": p["hl"].lower(), "font": font, "size": size}


def write_folder(folder, picks, colours):
    """Save picks (or remove our settings when picks is None). Never overwrites a file it cannot read."""
    path = settings_file(folder)
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    try: settings = load_jsonc(text)
    except ValueError: raise ValueError("Could not read this folder's .vscode/settings.json, so nothing was changed. "
                                        "Fix or remove that file, then try again.")
    if text.strip() and TAG not in text:
        backup = os.path.join(os.path.dirname(path), "settings.before-folder-colours.json")
        if not os.path.exists(backup): open(backup, "w", encoding="utf-8").write(text)
    for k in OURS: settings.pop(k, None)
    head = ""
    if picks:
        if not isinstance(colours, dict) or not colours or len(colours) > 200 or not all(
                isinstance(k, str) and isinstance(v, str) and HEX.match(v) for k, v in colours.items()):
            raise ValueError("bad colour list")
        settings["workbench.colorCustomizations"] = colours
        if picks["font"] != "default": settings["chat.fontFamily"] = f"'{picks['font']}', -apple-system, sans-serif"
        if picks["size"] != 13: settings["chat.fontSize"] = picks["size"]
        head = TAG + json.dumps(picks, separators=(",", ":")) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(head + json.dumps(settings, indent=2) + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    folders, origin = [], ""

    def log_message(self, *args): pass

    def reply(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)

    def local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.local_only(): return self.reply(403, {"error": "local use only"})
        route = self.path.split("?")[0]
        if route in ("/", "/index.html"):
            page = open(os.path.join(HERE, "picker.html"), encoding="utf-8").read()
            return self.reply(200, (HEAD + page + "</html>").encode(), "text/html")
        if route == "/api/folders":
            return self.reply(200, {"folders": [read_folder(f) for f in self.folders]})
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        # Only this page may save: same host, same origin, JSON body. Stops other websites writing files.
        if not self.local_only() or self.headers.get("Origin") != self.origin \
                or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.reply(403, {"error": "not allowed"})
        if self.path != "/api/save": return self.reply(404, {"error": "not found"})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length") or 0), 200_000)) or b"{}")
            if body.get("path") not in self.folders: raise ValueError("unknown folder")
            write_folder(body["path"], clean_picks(body.get("picks")), body.get("colours"))
        except (ValueError, KeyError, TypeError, OSError) as e:
            return self.reply(400, {"error": str(e) or "could not save"})
        self.reply(200, {"ok": True})


def main():
    args = sys.argv[1:]
    no_open = "--no-open" in args
    args = [a for a in args if a != "--no-open"] or ["."]
    folders = []
    for a in args:
        p = os.path.realpath(os.path.expanduser(a))
        if not os.path.isdir(p): sys.exit(f"Not a folder: {a}")
        if p not in folders: folders.append(p)
    server = None
    for port in (PORT, 0):
        try: server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler); break
        except OSError: continue
    url = f"http://127.0.0.1:{server.server_address[1]}"
    Handler.folders, Handler.origin = folders, url
    print(f"Folder Colours is running: {url}")
    print("Colouring: " + ", ".join(os.path.basename(f) or f for f in folders))
    print("Keep this open while you pick. Press Ctrl+C to stop.", flush=True)
    if not no_open: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopped.")


if __name__ == "__main__":
    main()
