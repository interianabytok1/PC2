"""Simple desktop application for OBERON item extraction."""

from __future__ import annotations

import html
import json
import queue
import re
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from web_extractor import ExtractionResult, extract_html_document, extract_page


APP_TITLE = "Polozky pre OBERON"
PROFILES_PATH = Path.home() / ".polozky-oberon" / "suppliers.json"


@dataclass
class TaskResult:
  export_html: str
  message: str


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


class App:
  def __init__(self, root: tk.Tk) -> None:
    self.root = root
    self.root.title(APP_TITLE)
    self.root.geometry("980x760")
    self.root.minsize(860, 640)

    self.profiles = load_profiles()
    self.latest_export_html = ""
    self.result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
    self.worker_thread: threading.Thread | None = None

    self.input_mode = tk.StringVar(value="web")
    self.supplier_var = tk.StringVar()
    self.supplier_name_var = tk.StringVar()
    self.url_var = tk.StringVar()
    self.status_var = tk.StringVar(value="Pripravené na spracovanie vstupu.")

    self._build_ui()
    self._refresh_profiles()
    self._toggle_input_mode()
    self.root.after(150, self._poll_queue)

  def _build_ui(self) -> None:
    style = ttk.Style()
    style.configure("TLabel", padding=2)
    style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
    style.configure("Panel.TLabelframe", padding=12)

    wrapper = ttk.Frame(self.root, padding=18)
    wrapper.pack(fill=tk.BOTH, expand=True)
    wrapper.columnconfigure(0, weight=1)
    wrapper.rowconfigure(3, weight=1)

    ttk.Label(wrapper, text="Extrahovanie položiek pre OBERON", style="Header.TLabel").grid(
      row=0, column=0, sticky="w"
    )
    ttk.Label(
      wrapper,
      text="Jednoduchá desktop aplikácia: zadáš zdroj, položky a uložíš HTML výstup.",
    ).grid(row=1, column=0, sticky="w", pady=(4, 12))

    source_frame = ttk.LabelFrame(wrapper, text="1. Zdroj údajov", style="Panel.TLabelframe")
    source_frame.grid(row=2, column=0, sticky="ew")
    source_frame.columnconfigure(1, weight=1)
    source_frame.columnconfigure(3, weight=1)

    ttk.Label(source_frame, text="Typ vstupu").grid(row=0, column=0, sticky="w")
    self.mode_combo = ttk.Combobox(
      source_frame,
      textvariable=self.input_mode,
      values=["web", "html"],
      state="readonly",
      width=22,
    )
    self.mode_combo.grid(row=0, column=1, sticky="ew", padx=(8, 12), pady=4)
    self.mode_combo.bind("<<ComboboxSelected>>", lambda _event: self._toggle_input_mode())

    ttk.Label(source_frame, text="Profil dodávateľa").grid(row=0, column=2, sticky="w")
    self.supplier_combo = ttk.Combobox(source_frame, textvariable=self.supplier_var, state="readonly")
    self.supplier_combo.grid(row=0, column=3, sticky="ew", pady=4)
    self.supplier_combo.bind("<<ComboboxSelected>>", lambda _event: self._load_selected_profile())

    ttk.Label(source_frame, text="Názov profilu").grid(row=1, column=0, sticky="w")
    ttk.Entry(source_frame, textvariable=self.supplier_name_var).grid(
      row=1, column=1, sticky="ew", padx=(8, 12), pady=4
    )

    self.url_label = ttk.Label(source_frame, text="Adresa stránky")
    self.url_label.grid(row=1, column=2, sticky="w")
    self.url_entry = ttk.Entry(source_frame, textvariable=self.url_var)
    self.url_entry.grid(row=1, column=3, sticky="ew", pady=4)

    self.html_label = ttk.Label(source_frame, text="HTML kód")
    self.html_text = ScrolledText(source_frame, wrap=tk.WORD, height=8)

    filter_frame = ttk.LabelFrame(wrapper, text="2. Položky na spracovanie", style="Panel.TLabelframe")
    filter_frame.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
    filter_frame.columnconfigure(0, weight=1)
    filter_frame.columnconfigure(1, weight=1)
    filter_frame.rowconfigure(1, weight=1)

    ttk.Label(filter_frame, text="ID položiek").grid(row=0, column=0, sticky="w")
    ttk.Label(filter_frame, text="Kľúčové slová").grid(row=0, column=1, sticky="w")

    self.product_ids_text = ScrolledText(filter_frame, wrap=tk.WORD, height=12)
    self.product_ids_text.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=4)
    self.product_ids_text.insert("1.0", "ABC-100\nABC-101")

    self.keywords_text = ScrolledText(filter_frame, wrap=tk.WORD, height=12)
    self.keywords_text.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=4)
    self.keywords_text.insert("1.0", "úchytka\ndrez")

    output_frame = ttk.LabelFrame(wrapper, text="3. Výstup", style="Panel.TLabelframe")
    output_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))
    ttk.Label(output_frame, text="Aktuálne sa vytvára HTML výstup. CSV a Excel doplníme neskôr.").pack(
      anchor="w"
    )

    actions = ttk.Frame(wrapper)
    actions.grid(row=5, column=0, sticky="ew", pady=(14, 0))
    for index in range(4):
      actions.columnconfigure(index, weight=1)

    self.run_button = ttk.Button(actions, text="Spustiť spracovanie", command=self._start_processing)
    self.run_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

    ttk.Button(actions, text="Uložiť profil", command=self._save_profile).grid(
      row=0, column=1, sticky="ew", padx=8
    )
    ttk.Button(actions, text="Načítať HTML súbor", command=self._load_html_file).grid(
      row=0, column=2, sticky="ew", padx=8
    )

    self.export_button = ttk.Button(actions, text="Uložiť HTML výstup", command=self._save_output_html)
    self.export_button.grid(row=0, column=3, sticky="ew", padx=(8, 0))
    self.export_button.state(["disabled"])

    status_bar = ttk.Label(wrapper, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
    status_bar.grid(row=6, column=0, sticky="ew", pady=(14, 0))

  def _refresh_profiles(self) -> None:
    profile_names = ["Nový dodávateľ", *sorted(self.profiles.keys())]
    self.supplier_combo.configure(values=profile_names)
    self.supplier_combo.current(0)

  def _toggle_input_mode(self) -> None:
    is_html = self.input_mode.get() == "html"
    if is_html:
      self.url_label.grid_remove()
      self.url_entry.grid_remove()
      self.html_label.grid(row=2, column=0, sticky="nw", pady=(8, 4))
      self.html_text.grid(row=2, column=1, columnspan=3, sticky="nsew", pady=(8, 4))
      self.supplier_combo.state(["disabled"])
    else:
      self.html_label.grid_remove()
      self.html_text.grid_remove()
      self.url_label.grid()
      self.url_entry.grid()
      self.supplier_combo.state(["!disabled"])

  def _load_selected_profile(self) -> None:
    name = self.supplier_var.get()
    if name in {"", "Nový dodávateľ"}:
      return
    profile = self.profiles.get(name, {})
    self.supplier_name_var.set(name)
    self.url_var.set(profile.get("url", ""))
    self._replace_text(self.product_ids_text, profile.get("product_ids", ""))
    self._replace_text(self.keywords_text, profile.get("keywords", ""))

  def _save_profile(self) -> None:
    supplier_name = self.supplier_name_var.get().strip()
    url = self.url_var.get().strip()
    if not supplier_name:
      messagebox.showwarning(APP_TITLE, "Zadajte názov profilu.")
      return
    if self.input_mode.get() == "web" and not url:
      messagebox.showwarning(APP_TITLE, "Pri webovom režime zadajte adresu stránky.")
      return
    self.profiles[supplier_name] = {
      "url": url,
      "product_ids": self.product_ids_text.get("1.0", tk.END).strip(),
      "keywords": self.keywords_text.get("1.0", tk.END).strip(),
    }
    save_profiles(self.profiles)
    self._refresh_profiles()
    self.supplier_var.set(supplier_name)
    self.status_var.set(f"Profil '{supplier_name}' bol uložený.")

  def _load_html_file(self) -> None:
    file_path = filedialog.askopenfilename(
      title="Vyberte HTML súbor",
      filetypes=[("HTML files", "*.html;*.htm"), ("All files", "*.*")],
    )
    if not file_path:
      return
    content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    self.input_mode.set("html")
    self._toggle_input_mode()
    self._replace_text(self.html_text, content)
    self.status_var.set(f"HTML súbor načítaný: {file_path}")

  def _start_processing(self) -> None:
    if self.worker_thread and self.worker_thread.is_alive():
      self.status_var.set("Spracovanie už prebieha.")
      return

    payload = {
      "mode": self.input_mode.get(),
      "url": self.url_var.get().strip(),
      "html_code": self.html_text.get("1.0", tk.END).strip(),
      "product_ids": parse_terms(self.product_ids_text.get("1.0", tk.END)),
      "keywords": parse_terms(self.keywords_text.get("1.0", tk.END)),
    }

    if payload["mode"] == "web" and not payload["url"]:
      messagebox.showwarning(APP_TITLE, "Zadajte adresu stránky dodávateľa.")
      return
    if payload["mode"] == "html" and not payload["html_code"]:
      messagebox.showwarning(APP_TITLE, "Vložte HTML kód alebo načítajte HTML súbor.")
      return
    if not payload["product_ids"] and not payload["keywords"]:
      messagebox.showwarning(APP_TITLE, "Zadajte aspoň jedno ID položky alebo kľúčové slovo.")
      return

    self.run_button.state(["disabled"])
    self.status_var.set("Spracovanie prebieha...")
    self.worker_thread = threading.Thread(target=self._run_processing, args=(payload,), daemon=True)
    self.worker_thread.start()

  def _run_processing(self, payload: dict[str, object]) -> None:
    try:
      product_ids = list(payload["product_ids"])
      keywords = list(payload["keywords"])
      terms = keywords + product_ids
      if payload["mode"] == "html":
        result = extract_html_document(str(payload["html_code"]), "Lokálny HTML vstup", terms)
      else:
        result = extract_page(str(payload["url"]), terms)
      export_html = build_export_document(result, product_ids, keywords)
      matches = ", ".join(result.matched_terms) if result.matched_terms else "žiadne zhody"
      self.result_queue.put(("success", TaskResult(export_html, f"Hotovo: {result.title} | {matches}")))
    except Exception as error:
      self.result_queue.put(("error", str(error)))

  def _poll_queue(self) -> None:
    try:
      while True:
        status, payload = self.result_queue.get_nowait()
        if status == "success":
          result = payload
          assert isinstance(result, TaskResult)
          self.latest_export_html = result.export_html
          self.status_var.set(result.message)
          self.export_button.state(["!disabled"])
        else:
          self.status_var.set(f"Spracovanie zlyhalo: {payload}")
          messagebox.showerror(APP_TITLE, f"Spracovanie zlyhalo:\n{payload}")
        self.run_button.state(["!disabled"])
    except queue.Empty:
      pass
    self.root.after(150, self._poll_queue)

  def _save_output_html(self) -> None:
    if not self.latest_export_html:
      messagebox.showinfo(APP_TITLE, "Zatiaľ neexistuje žiadny výstup na uloženie.")
      return
    file_path = filedialog.asksaveasfilename(
      title="Uložiť HTML výstup",
      defaultextension=".html",
      initialfile="oberon-export.html",
      filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
    )
    if not file_path:
      return
    Path(file_path).write_text(self.latest_export_html, encoding="utf-8")
    self.status_var.set(f"HTML výstup uložený: {file_path}")

  @staticmethod
  def _replace_text(widget: ScrolledText, value: str) -> None:
    widget.delete("1.0", tk.END)
    widget.insert("1.0", value)


def main() -> int:
  root = tk.Tk()
  App(root)
  root.mainloop()
  return 0


if __name__ == "__main__":
  raise SystemExit(main())