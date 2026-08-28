"""Local web application entry point for the OBERON item extraction tool."""

from __future__ import annotations

import html
import json
import re
import threading
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from web_extractor import ExtractionResult, extract_html_document, extract_page


APP_TITLE = "Polozky pre OBERON"
PROFILES_PATH = Path.home() / ".polozky-oberon" / "suppliers.json"


@dataclass
class AppState:
    profiles: dict[str, dict[str, str]] = field(default_factory=dict)
    latest_export_html: str = ""
    latest_message: str = "Pripravené na spracovanie vstupu."


def load_profiles() -> dict[str, dict[str, str]]:
    try:
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_profiles(profiles: dict[str, dict[str, str]]) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_terms(raw_text: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,\n;]+", raw_text) if item.strip()]


def build_export_document(result: ExtractionResult, product_ids: list[str], keywords: list[str]) -> str:
    matches = ", ".join(result.matched_terms) if result.matched_terms else "bez zhody"
    ids = ", ".join(product_ids) if product_ids else "neuvedené"
    terms = ", ".join(keywords) if keywords else "neuvedené"
    return f"""<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <title>{html.escape(result.title)}</title>
</head>
<body>
  <h1>{html.escape(result.title)}</h1>
  <p><strong>Zdroj:</strong> {html.escape(result.url)}</p>
  <p><strong>Popis:</strong> {html.escape(result.description or 'Bez popisu')}</p>
  <p><strong>ID položiek:</strong> {html.escape(ids)}</p>
  <p><strong>Kľúčové slová:</strong> {html.escape(terms)}</p>
  <p><strong>Nájdené zhody:</strong> {html.escape(matches)}</p>
</body>
</html>
"""


def render_page(state: AppState, form: dict[str, str] | None = None) -> bytes:
    data = {
        "input_mode": "web",
        "supplier": "",
        "url": "",
        "product_ids": "",
        "keywords": "",
        "html_code": "",
    }
    if form:
        data.update(form)

    profile_options = ['<option value="">Vyberte profil</option>']
    for name in sorted(state.profiles):
        selected = " selected" if data["supplier"] == name else ""
        profile_options.append(f'<option value="{html.escape(name)}"{selected}>{html.escape(name)}</option>')

    result_block = ""
    if state.latest_export_html:
        result_block = f"""
        <section class="panel result-panel">
          <h2>Výsledok</h2>
          <p>{html.escape(state.latest_message)}</p>
          <p><a class="button secondary" href="/download/latest.html">Stiahnuť HTML výstup</a></p>
        </section>
        """

    page = f"""<!doctype html>
<html lang="sk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_TITLE}</title>
  <style>
    :root {{ color-scheme: light; --bg: #f3efe6; --panel: #fffdfa; --line: #d1c7b8; --text: #213032; --muted: #617073; --accent: #1d6b67; --accent-2: #dd8b3c; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Tahoma, sans-serif; background: radial-gradient(circle at top, #fff9ef, var(--bg) 45%); color: var(--text); }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 28px 18px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 32px; }}
    .lead {{ margin: 0 0 24px; color: var(--muted); }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 18px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(38, 50, 56, 0.06); }}
    .grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
    label {{ display: block; margin-bottom: 6px; font-weight: 600; }}
    input, select, textarea {{ width: 100%; border: 1px solid var(--line); border-radius: 10px; background: #fff; padding: 10px 12px; font: inherit; color: var(--text); }}
    textarea {{ min-height: 110px; resize: vertical; }}
    .actions {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; }}
    .button {{ display: inline-block; border: none; border-radius: 10px; padding: 11px 16px; background: var(--accent); color: #fff; font-weight: 700; cursor: pointer; text-decoration: none; }}
    .button.secondary {{ background: #e7ddce; color: var(--text); }}
    .note {{ color: var(--muted); font-size: 14px; }}
    .message {{ padding: 12px 14px; border-radius: 10px; background: #eef6f4; border: 1px solid #c8e0db; margin-bottom: 18px; }}
    .hidden {{ display: none; }}
    @media (max-width: 640px) {{ h1 {{ font-size: 26px; }} .wrap {{ padding: 20px 14px 32px; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Extrahovanie položiek pre OBERON</h1>
    <p class="lead">Aplikácia beží lokálne v prehliadači, ale spúšťa sa jedným .exe súborom.</p>

    <div class="message">{html.escape(state.latest_message)}</div>

    <form method="post" action="/run" class="panel">
      <div class="grid">
        <div>
          <label for="input_mode">Typ vstupu</label>
          <select id="input_mode" name="input_mode" onchange="toggleMode()">
            <option value="web"{' selected' if data['input_mode'] == 'web' else ''}>Webová stránka</option>
            <option value="html"{' selected' if data['input_mode'] == 'html' else ''}>HTML kód / HTML súbor</option>
          </select>
        </div>
        <div id="profile-group">
          <label for="supplier">Profil dodávateľa</label>
          <select id="supplier" name="supplier">{''.join(profile_options)}</select>
        </div>
      </div>

      <div class="grid">
        <div id="url-group">
          <label for="url">Adresa stránky</label>
          <input id="url" name="url" value="{html.escape(data['url'])}" placeholder="https://www.example.sk">
        </div>
        <div>
          <label for="supplier_name">Názov profilu</label>
          <input id="supplier_name" name="supplier_name" value="{html.escape(data['supplier'])}" placeholder="napr. Demos">
        </div>
      </div>

      <div id="html-group" class="{'hidden' if data['input_mode'] != 'html' else ''}">
        <label for="html_code">HTML kód</label>
        <textarea id="html_code" name="html_code" placeholder="Sem vložte HTML kód stránky">{html.escape(data['html_code'])}</textarea>
      </div>

      <div class="grid">
        <div>
          <label for="product_ids">ID položiek</label>
          <textarea id="product_ids" name="product_ids" placeholder="ABC-100&#10;ABC-101">{html.escape(data['product_ids'])}</textarea>
        </div>
        <div>
          <label for="keywords">Kľúčové slová</label>
          <textarea id="keywords" name="keywords" placeholder="úchytka&#10;drez">{html.escape(data['keywords'])}</textarea>
        </div>
      </div>

      <p class="note">Výstup aktuálne vytvára HTML súbor. CSV a Excel doplníme neskôr.</p>

      <div class="actions">
        <button class="button" type="submit">Spustiť spracovanie</button>
        <button class="button secondary" type="submit" formaction="/save-profile">Uložiť profil</button>
        <a class="button secondary" href="/download/latest.html">Stiahnuť posledný HTML výstup</a>
        <button class="button secondary" type="submit" formaction="/shutdown">Ukončiť aplikáciu</button>
      </div>
    </form>

    {result_block}
  </div>
  <script>
    function toggleMode() {{
      var mode = document.getElementById('input_mode').value;
      document.getElementById('html-group').className = mode === 'html' ? '' : 'hidden';
      document.getElementById('url-group').className = mode === 'web' ? '' : 'hidden';
      document.getElementById('profile-group').className = mode === 'web' ? '' : 'hidden';
    }}
    toggleMode();
  </script>
</body>
</html>
"""
    return page.encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    state: AppState

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html(render_page(self.state))
            return
        if self.path == "/download/latest.html":
            if not self.state.latest_export_html:
                self._send_html(render_page(self.state), status=HTTPStatus.NOT_FOUND)
                return
            payload = self.state.latest_export_html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="oberon-export.html"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        form = self._read_form()
        if self.path == "/save-profile":
            self._save_profile(form)
            return
        if self.path == "/run":
            self._run_extraction(form)
            return
        if self.path == "/shutdown":
            self.state.latest_message = "Aplikácia sa ukončuje. Toto okno môžete zavrieť."
            self._send_html(render_page(self.state))
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(body, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def _save_profile(self, form: dict[str, str]) -> None:
        supplier_name = form.get("supplier_name", "").strip()
        url = form.get("url", "").strip()
        if not supplier_name or not url:
            self.state.latest_message = "Na uloženie profilu treba názov profilu a adresu stránky."
            self._send_html(render_page(self.state, form), status=HTTPStatus.BAD_REQUEST)
            return
        self.state.profiles[supplier_name] = {
            "url": url,
            "keywords": form.get("keywords", ""),
            "product_ids": form.get("product_ids", ""),
        }
        save_profiles(self.state.profiles)
        form["supplier"] = supplier_name
        self.state.latest_message = f"Profil '{supplier_name}' bol uložený."
        self._send_html(render_page(self.state, form))

    def _run_extraction(self, form: dict[str, str]) -> None:
        input_mode = form.get("input_mode", "web")
        keywords = parse_terms(form.get("keywords", ""))
        product_ids = parse_terms(form.get("product_ids", ""))
        terms = keywords + product_ids
        try:
            if input_mode == "html":
                html_code = form.get("html_code", "").strip()
                if not html_code:
                    raise ValueError("Pri HTML režime vložte HTML kód.")
                result = extract_html_document(html_code, "Lokálny HTML vstup", terms)
            else:
                url = form.get("url", "").strip()
                if not url:
                    raise ValueError("Zadajte adresu stránky dodávateľa.")
                result = extract_page(url, terms)
            self.state.latest_export_html = build_export_document(result, product_ids, keywords)
            match_text = ", ".join(result.matched_terms) if result.matched_terms else "žiadne zhody"
            self.state.latest_message = f"Spracovanie úspešné: {result.title} | {match_text}"
            self._send_html(render_page(self.state, form))
        except Exception as error:
            self.state.latest_message = f"Spracovanie zlyhalo: {error}"
            self._send_html(render_page(self.state, form), status=HTTPStatus.BAD_REQUEST)

    def _send_html(self, payload: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> int:
    state = AppState(profiles=load_profiles())
    handler = type("BoundAppHandler", (AppHandler,), {"state": state})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    webbrowser.open(url)
    server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())