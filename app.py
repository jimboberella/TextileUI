import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

# Keepalive tracking
_active_connections = {}
_shutdown_event = threading.Event()
_server = None


def _connection_timer(conn_id):
    """Reset timer on each ping; shut down when no active connections."""
    timer = threading.Timer(15.0, _check_shutdown)
    timer.start()
    with _active_connections_lock:
        _active_connections[conn_id] = timer


def _check_shutdown():
    """Called when last connection drops. Wait a moment, then shut down."""
    time.sleep(3)  # grace period
    with _active_connections_lock:
        if not _active_connections:
            print("No active connections — shutting down server.")
            if _server:
                threading.Thread(target=_server.shutdown, daemon=True).start()


def _keepalive_stream(conn_id):
    """Send periodic pings; clean up on client disconnect."""
    try:
        interval = 3
        while not _shutdown_event.is_set():
            yield ": keepalive\n\n"
            _connection_timer(conn_id)
            time.sleep(interval)
    finally:
        with _active_connections_lock:
            timer = _active_connections.pop(conn_id, None)
        if timer:
            timer.cancel()
        _check_shutdown()


_active_connections_lock = threading.Lock()

CONFIG_PATH = Path(__file__).parent / "config" / "settings.json"
FABRIC_CMD = ["fabric"]


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def resolve_path(p):
    return os.path.expanduser(os.path.expandvars(p))


def run_fabric(pattern, input_text, variables=None, **kwargs):
    cmd = FABRIC_CMD[:]
    if pattern:
        cmd.extend(["-p", pattern])
    if variables:
        for k, v in variables.items():
            cmd.extend(["-v", f"#{k}:{v}"])
    if kwargs.get("model"):
        cmd.extend(["-m", kwargs["model"]])
    if kwargs.get("context"):
        cmd.extend(["-C", kwargs["context"]])
    if kwargs.get("temperature") is not None:
        cmd.extend(["-t", str(kwargs["temperature"])])
    if kwargs.get("topp") is not None:
        cmd.extend(["-T", str(kwargs["topp"])])
    if kwargs.get("presence_penalty") is not None:
        cmd.extend(["-P", str(kwargs["presence_penalty"])])
    if kwargs.get("frequency_penalty") is not None:
        cmd.extend(["-F", str(kwargs["frequency_penalty"])])
    if kwargs.get("stream"):
        cmd.append("-s")
    if kwargs.get("raw"):
        cmd.append("-r")
    if kwargs.get("dry_run"):
        cmd.append("--dry-run")
    if kwargs.get("output"):
        cmd.extend(["-o", kwargs["output"]])
    if kwargs.get("scrape_url"):
        cmd.extend(["-u", kwargs["scrape_url"]])
    if kwargs.get("youtube"):
        cmd.extend(["-y", kwargs["youtube"]])
    if kwargs.get("language"):
        cmd.extend(["-g", kwargs["language"]])
    if kwargs.get("attachment"):
        cmd.extend(["-a", kwargs["attachment"]])
    if kwargs.get("model_context_length"):
        cmd.extend(["--modelContextLength", str(kwargs["model_context_length"])])

    result = subprocess.run(
        cmd, input=input_text if input_text else None,
        capture_output=True, text=True, timeout=300
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def get_pattern_variables(pattern_name):
    """Extract variable definitions from a fabric pattern file."""
    try:
        res = subprocess.run(
            ["fabric", "--readpattern", pattern_name],
            capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            # Look for variable definitions like #role:, #points:, etc.
            import re
            variables = re.findall(r"#(\w[\w-]*):", res.stdout)
            return list(set(variables))
    except Exception:
        pass
    return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/patterns")
def list_patterns():
    res = subprocess.run(
        ["fabric", "-l"], capture_output=True, text=True, timeout=15
    )
    patterns = [p.strip() for p in res.stdout.strip().split("\n") if p.strip()]
    return jsonify({"patterns": patterns})


@app.route("/api/patterns/<name>/info")
def pattern_info(name):
    res = subprocess.run(
        ["fabric", "--readpattern", name],
        capture_output=True, text=True, timeout=10
    )
    variables = get_pattern_variables(name)
    return jsonify({
        "name": name,
        "content": res.stdout if res.returncode == 0 else "",
        "variables": variables,
    })


@app.route("/api/read-file", methods=["POST"])
def read_file():
    data = request.json
    filepath = resolve_path(data.get("path", ""))
    try:
        with open(filepath, "r") as f:
            content = f.read()
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"content": "", "error": str(e)}), 400


@app.route("/api/models")
def list_models():
    res = subprocess.run(
        ["fabric", "-L"], capture_output=True, text=True, timeout=15
    )
    lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
    return jsonify({"models": lines})


@app.route("/api/contexts")
def list_contexts():
    res = subprocess.run(
        ["fabric", "-x"], capture_output=True, text=True, timeout=15
    )
    lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
    return jsonify({"contexts": lines})


@app.route("/api/run", methods=["POST"])
def run_pattern():
    data = request.json
    config = load_config()

    pattern = data.get("pattern")
    input_text = data.get("input", "")
    variables = data.get("variables", {})
    model = data.get("model") or config.get("default_model")
    context = data.get("context")
    temperature = data.get("temperature", config.get("default_temperature"))
    topp = data.get("topp", config.get("default_topp"))
    presence_penalty = data.get("presence_penalty", config.get("default_presence_penalty"))
    frequency_penalty = data.get("frequency_penalty", config.get("default_frequency_penalty"))
    stream = data.get("stream", False)
    raw = data.get("raw", False)
    dry_run = data.get("dry_run", False)
    output_file = data.get("output_file")
    scrape_url = data.get("scrape_url")
    youtube = data.get("youtube")
    language = data.get("language")
    attachment = data.get("attachment")
    model_context_length = data.get("model_context_length")

    if output_file:
        output_file = resolve_path(output_file)

    result = run_fabric(
        pattern=pattern,
        input_text=input_text,
        variables=variables,
        model=model,
        context=context,
        temperature=temperature,
        topp=topp,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        stream=stream,
        raw=raw,
        dry_run=dry_run,
        output=output_file,
        scrape_url=scrape_url,
        youtube=youtube,
        language=language,
        attachment=attachment,
        model_context_length=model_context_length,
    )

    return jsonify(result)


@app.route("/api/save-obsidian", methods=["POST"])
def save_to_obsidian():
    data = request.json
    content = data.get("content", "")
    title = data.get("title", "Untitled")
    vault_path = resolve_path(data.get("vault_path", load_config().get("obsidian_vault_path", "~/Documents/Notes")))
    folder = data.get("folder", "")

    # Create folder if specified
    if folder:
        folder_path = os.path.join(vault_path, folder)
        os.makedirs(folder_path, exist_ok=True)
    else:
        folder_path = vault_path

    # Sanitize title for filename
    safe_title = "".join(c if c.isalnum() or c in "-_" else "-" for c in title)
    safe_title = safe_title.strip("-") or "untitled"

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    filename = f"{timestamp}-{safe_title}.md"
    filepath = os.path.join(folder_path, filename)

    # Build markdown with frontmatter
    pattern_used = data.get("pattern", "")
    md = f"""---
title: {title}
date: {timestamp}
pattern: {pattern_used}
source: {data.get('source', 'manual')}
---

{content}
"""

    with open(filepath, "w") as f:
        f.write(md)

    return jsonify({"success": True, "path": filepath, "filename": filename})


@app.route("/api/save-file", methods=["POST"])
def save_to_file():
    data = request.json
    content = data.get("content", "")
    filepath = resolve_path(data.get("filepath", ""))

    if not filepath:
        return jsonify({"success": False, "error": "No filepath specified"}), 400

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)

    return jsonify({"success": True, "path": filepath})


def get_pattern_summary(pattern_name):
    """Extract a short summary from a pattern's content."""
    try:
        res = subprocess.run(
            ["fabric", "--readpattern", pattern_name],
            capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            content = res.stdout
            # First non-empty line after frontmatter-like lines is typically the description
            lines = content.split("\n")
            desc_lines = []
            in_header = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("---") and not in_header:
                    in_header = True
                    continue
                if in_header and stripped.startswith("---"):
                    in_header = False
                    continue
                if in_header:
                    desc_lines.append(stripped)
            if desc_lines:
                return " ".join(l for l in desc_lines if l)[:200]
            # Fallback: first non-empty line
            for line in lines:
                if line.strip():
                    return line.strip()[:200]
    except Exception:
        pass
    return ""


def get_favorites():
    config = load_config()
    return config.get("favorites", [])


def set_favorites(favorites):
    config = load_config()
    config["favorites"] = favorites
    save_config(config)


def get_presets():
    config = load_config()
    return config.get("presets", [])


def set_presets(presets):
    config = load_config()
    config["presets"] = presets
    save_config(config)


@app.route("/api/patterns/<name>/summary")
def pattern_summary(name):
    return jsonify({"summary": get_pattern_summary(name)})


@app.route("/api/favorites")
def get_favorites_endpoint():
    return jsonify({"favorites": get_favorites()})


@app.route("/api/favorites", methods=["POST"])
def update_favorites():
    data = request.json
    set_favorites(data.get("favorites", []))
    return jsonify({"favorites": get_favorites()})


@app.route("/api/presets")
def get_presets_endpoint():
    return jsonify({"presets": get_presets()})


@app.route("/api/presets", methods=["POST"])
def save_preset():
    data = request.json
    presets = get_presets()
    preset = {
        "id": data.get("id", f"preset_{int(time.time())}"),
        "name": data.get("name", "Untitled Preset"),
        "pattern": data.get("pattern", ""),
        "model": data.get("model", ""),
        "context": data.get("context", ""),
        "temperature": data.get("temperature", 0.7),
        "topp": data.get("topp", 0.9),
        "presence_penalty": data.get("presence_penalty", 0.0),
        "frequency_penalty": data.get("frequency_penalty", 0.0),
        "stream": data.get("stream", False),
        "raw": data.get("raw", False),
        "dry_run": data.get("dry_run", False),
        "language": data.get("language", ""),
        "created_at": data.get("created_at", time.strftime("%Y-%m-%d %H:%M")),
    }
    # Check if preset with same id exists, update it
    found = False
    for i, p in enumerate(presets):
        if p.get("id") == preset["id"]:
            presets[i] = preset
            found = True
            break
    if not found:
        presets.append(preset)
    set_presets(presets)
    return jsonify({"presets": presets})


@app.route("/api/presets/<preset_id>", methods=["DELETE"])
def delete_preset(preset_id):
    presets = get_presets()
    presets = [p for p in presets if p.get("id") != preset_id]
    set_presets(presets)
    return jsonify({"presets": presets})



# Obsidian config (last used vault path and folder)
def get_obsidian_config():
    config = load_config()
    return {
        "vault_path": config.get("obsidian_vault_path", "~/Documents/Notes"),
        "folder": config.get("last_obsidian_folder", ""),
    }


def set_obsidian_config(vault_path, folder):
    config = load_config()
    config["obsidian_vault_path"] = vault_path
    config["last_obsidian_folder"] = folder
    save_config(config)


@app.route("/api/obsidian-config")
def get_obsidian_config_endpoint():
    return jsonify(get_obsidian_config())


@app.route("/api/obsidian-config", methods=["POST"])
def update_obsidian_config():
    data = request.json
    set_obsidian_config(data.get("vault_path", ""), data.get("folder", ""))
    return jsonify(get_obsidian_config())
@app.route("/api/keepalive", methods=["GET"])
def keepalive():
    conn_id = request.args.get("id", "")
    return Response(
        _keepalive_stream(conn_id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )




if __name__ == "__main__":
    config = load_config()
    port = 5050
    print(f"Fabric Web Interface running at http://localhost:{port}")
    print("Server will auto-shutdown when all browser tabs are closed.")

    # Open browser automatically
    import platform
    import webbrowser
    url = f"http://localhost:{port}"
    
    # Try different methods depending on platform
    try:
        if platform.system() == "Darwin":  # macOS
            import subprocess
            subprocess.Popen(["open", url])
        elif platform.system() == "Linux":
            # Try desktop-notification-aware openers first
            import subprocess
            for cmd in ["xdg-open", "gnome-open", "x-www-browser", "firefox", "chromium"]:
                try:
                    subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
                except FileNotFoundError:
                    continue
            else:
                # Fallback to generic open
                webbrowser.open(url)
        else:
            webbrowser.open(url)
    except Exception as e:
        print(f"Note: Could not auto-open browser: {e}")
        print(f"Please open: {url}")

    from werkzeug.serving import make_server
    _server = make_server("0.0.0.0", port, app, threaded=True)
    try:
        _server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown_event.set()
        _server.shutdown()
