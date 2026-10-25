# -*- coding: utf-8 -*-
# J11 Watching proxy: browse Operation Movie WebDAV + stream mp4 + Feishu progress
# Usage: python video_proxy.py  (listens on 127.0.0.1:8790)
import http.server, urllib.request, urllib.parse, ssl, base64, os, json, subprocess, tempfile, time
import xml.etree.ElementTree as ET

USER = "webdav_music"
PASS = "Hks11801!"
BASE = "https://harrypublicnas.myqnapcloud.com:5001/"
AUTH = "Basic " + base64.b64encode((USER + ":" + PASS).encode()).decode()
ROOT = "Main Operation Centre/Operation Movie"
HERE = os.path.dirname(os.path.abspath(__file__))

# Feishu base for viewing progress
PROGRESS_BASE = "ARBFbl0TJaQ8nlsefNIcZJ1CnNd"
PROGRESS_TABLE = "tblx75IpPDl9BeYb"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Cache for NAS anime folders
_nas_cache = {"time": 0, "folders": []}

def webdav_list(target_path):
    target = BASE + urllib.parse.quote(target_path, safe="/") + "/"
    req = urllib.request.Request(target, method="PROPFIND")
    req.add_header("Authorization", AUTH)
    req.add_header("Depth", "1")
    req.add_header("Content-Type", "application/xml")
    with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    ns = {"d": "DAV:"}
    entries = []
    target_short = target_path.split("/")[-1]
    for r in root.findall("d:response", ns):
        href = r.findtext("d:href", "", ns)
        if not href: continue
        decoded = urllib.parse.unquote(href).rstrip("/")
        name = decoded.split("/")[-1]
        # Skip self entry
        if name == target_short and decoded.endswith(target_path.split("/")[-2] + "/" + name): continue
        if "@recycle" in name or ".syncing" in name or name.startswith("."): continue
        is_dir = href.endswith("/")
        cl = r.findtext("d:propstat/d:prop/d:getcontentlength", "", ns)
        ext = os.path.splitext(name)[1].lower()
        if not is_dir and ext not in (".mp4", ".mkv", ".srt"): continue
        entries.append({
            "name": name,
            "path": decoded.lstrip("/"),
            "is_dir": is_dir,
            "size": int(cl) if cl and cl.isdigit() else 0
        })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries

def scan_nas_anime_folders():
    """Scan all category dirs under Operation Movie, return flat list of anime folder paths."""
    now = time.time()
    if now - _nas_cache["time"] < 300 and _nas_cache["folders"]:
        return _nas_cache["folders"]
    # List root categories
    cats = webdav_list(ROOT)
    folders = []
    for cat in cats:
        if not cat["is_dir"]: continue
        cat_path = cat["path"]
        try:
            sub = webdav_list(cat_path)
            for s in sub:
                if s["is_dir"]:
                    rel = s["path"].replace(ROOT + "/", "")
                    folders.append({"name": s["name"], "path": rel})
        except: pass
    _nas_cache["time"] = now
    _nas_cache["folders"] = folders
    return folders

def run_lark(args):
    cmd = ["lark-cli"] + args + ["--as", "user"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8")
    if r.returncode != 0:
        raise Exception(r.stderr[:300])
    return json.loads(r.stdout)

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)

            if u.path == "/list":
                sub = q.get("path", [""])[0]
                entries = webdav_list(ROOT + ("/" + sub if sub else ""))
                self._json({"path": sub, "entries": entries})

            elif u.path == "/proxy":
                path = q.get("path", [""])[0]
                if not path:
                    self.send_error(400, "missing path"); return
                target = BASE + urllib.parse.quote(path, safe="/")
                req = urllib.request.Request(target, method="GET")
                req.add_header("Authorization", AUTH)
                req.add_header("User-Agent", "Mozilla/5.0 J11Proxy")
                if "Range" in self.headers:
                    req.add_header("Range", self.headers["Range"])
                with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                    st = resp.getcode()
                    is_srt = path.lower().endswith(".srt")
                    ct = resp.headers.get("Content-Type", "application/octet-stream")
                    self.send_response(st)
                    self.send_header("Content-Type", ct if not is_srt else "text/vtt; charset=utf-8")
                    for k in ("Accept-Ranges", "Content-Range", "Last-Modified", "ETag"):
                        v = resp.headers.get(k)
                        if v: self.send_header(k, v)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    if is_srt:
                        raw = resp.read()
                        try:
                            text = raw.decode("utf-8", errors="replace").lstrip("\ufeff")
                            lines = text.replace("\r\n", "\n").split("\n")
                            out = ["WEBVTT", ""]
                            for line in lines:
                                if "-->" in line: line = line.replace(",", ".")
                                out.append(line)
                            self.wfile.write("\n".join(out).encode("utf-8"))
                        except: self.wfile.write(raw)
                    else:
                        chunk = resp.read(65536)
                        while chunk:
                            try: self.wfile.write(chunk)
                            except: break
                            chunk = resp.read(65536)

            elif u.path == "/nas-find":
                name = q.get("name", [""])[0].strip().lower()
                folders = scan_nas_anime_folders()
                matches = []
                for f in folders:
                    fn = f["name"].lower()
                    if name in fn or fn in name:
                        matches.append(f)
                self._json({"matches": matches})

            elif u.path == "/progress":
                tmp = os.path.join(tempfile.gettempdir(), "j11_progress.ndjson")
                r = subprocess.run(["lark-cli", "base", "+record-list",
                    "--base-token", PROGRESS_BASE,
                    "--table-id", PROGRESS_TABLE,
                    "--limit", "100",
                    "--format", "ndjson",
                    "--output", tmp,
                    "--overwrite",
                    "--as", "user"], capture_output=True, text=True, timeout=30, encoding="utf-8")
                records = []
                with open(tmp, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("{") and "manifest" in line[:50]: continue
                        try:
                            rec = json.loads(line)
                            records.append({
                                "record_id": rec.get("record_id"),
                                "name": rec.get("動畫名", ""),
                                "progress": rec.get("觀看進度") or "",
                                "downloaded": rec.get("Downloaded") or 0,
                                "latest": rec.get("最後更新集數") or 0,
                                "total": rec.get("原作總編集") or 0,
                                "status": rec.get("下載狀態") or [],
                            })
                        except: pass
                self._json({"records": records})

            elif u.path == "/progress-update":
                rid = q.get("record_id", [""])[0]
                prog = q.get("progress", [""])[0]
                if not rid:
                    self._json({"error": "missing record_id"}, 400); return
                jf = os.path.join(tempfile.gettempdir(), "j11_upd.json")
                with open(jf, "w", encoding="utf-8") as f:
                    json.dump({"fields": {"觀看進度": prog}}, f, ensure_ascii=False)
                r = subprocess.run(["lark-cli", "base", "+record-upsert",
                    "--base-token", PROGRESS_BASE,
                    "--table-id", PROGRESS_TABLE,
                    "--record-id", rid,
                    "--json", "@" + jf,
                    "--as", "user"], capture_output=True, text=True, timeout=30, encoding="utf-8")
                ok = r.returncode == 0 and '"ok": true' in r.stdout
                self._json({"ok": ok, "stdout": r.stdout[:300], "stderr": r.stderr[:300]})

            else:
                p = u.path
                if p in ("", "/"): p = "/index.html"
                fp = os.path.join(HERE, p.lstrip("/"))
                if ".." in p or not os.path.isfile(fp):
                    self.send_error(404); return
                ct = {".html":"text/html; charset=utf-8",".js":"application/javascript",
                      ".css":"text/css",".json":"application/json",
                      ".jpg":"image/jpeg",".png":"image/png"}.get(os.path.splitext(fp)[1].lower(), "application/octet-stream")
                with open(fp, "rb") as f: body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except Exception as e:
            try: self.send_error(502, str(e)[:200])
            except: pass

if __name__ == "__main__":
    print("J11 Watching proxy on http://127.0.0.1:8790")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8790), H).serve_forever()
