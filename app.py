"""Desktop entry point for the OBERON item extraction tool."""

import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from web_extractor import extract_page


class ExtractionWorker(QObject):
    """Runs extraction work away from the GUI thread."""

    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, keywords: list[str], product_ids: list[str]) -> None:
        super().__init__()
        self.url = url
        self.keywords = keywords
        self.product_ids = product_ids

    @Slot()
    def run(self) -> None:
        try:
            terms = self.keywords + self.product_ids
            result = extract_page(self.url, terms)
            if result.matched_terms:
                matches = ", ".join(result.matched_terms)
                self.finished.emit(f"Nájdená stránka: {result.title} | Zhody: {matches}")
            else:
                self.finished.emit(f"Stránka načítaná: {result.title} | Žiadna zhoda filtrov")
        except Exception as error:  # Keep unexpected connector errors in the UI.
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    """First application shell; extraction is added in the next iteration."""

    def __init__(self) -> None:
        super().__init__()
        self.thread = None
        self.worker = None
        self.profiles_path = Path.home() / ".polozky-oberon" / "suppliers.json"
        self.profiles = self._load_profiles()
        self.setWindowTitle("Položky pre OBERON")
        self.resize(980, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        heading = QLabel("Extrahovanie položiek pre import do OBERON-u")
        heading.setObjectName("heading")
        root.addWidget(heading)

        subtitle = QLabel("Definujte zdroj, vyberte položky a pripravte kontrolovaný export.")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        source_box = QGroupBox("1  Zdroj údajov")
        source_form = QFormLayout(source_box)
        self.input_mode = QComboBox()
        self.input_mode.addItems(["Webová stránka", "HTML kód / HTML súbor"])
        self.input_mode.currentIndexChanged.connect(self._change_input_mode)
        source_form.addRow("Typ vstupu", self.input_mode)
        self.supplier = QComboBox()
        self.supplier.addItem("Nový dodávateľ")
        self.supplier.addItems(self.profiles.keys())
        self.supplier.currentTextChanged.connect(self._load_selected_profile)
        source_form.addRow("Profil dodávateľa", self.supplier)
        self.supplier_name = QLineEdit()
        self.supplier_name.setPlaceholderText("napr. Demos")
        source_form.addRow("Názov profilu", self.supplier_name)
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://www.example.sk")
        self.url_label = QLabel("Adresa stránky")
        source_form.addRow(self.url_label, self.url)
        self.html_code = QTextEdit()
        self.html_code.setPlaceholderText("Vložte HTML kód alebo vyberte HTML súbor")
        self.html_code.setMinimumHeight(100)
        self.html_code.setVisible(False)
        self.html_code_label = QLabel("HTML kód")
        self.html_code_label.setVisible(False)
        source_form.addRow(self.html_code_label, self.html_code)
        save_profile = QPushButton("Uložiť profil")
        save_profile.clicked.connect(self._save_profile)
        source_form.addRow("", save_profile)
        root.addWidget(source_box)

        filters = QHBoxLayout()
        filter_box = QGroupBox("2  Čo extrahovať")
        filter_form = QFormLayout(filter_box)
        self.keywords = QTextEdit()
        self.keywords.setPlaceholderText("napr. stolička, kancelársky nábytok\nJedna hodnota na riadok")
        self.keywords.setFixedHeight(90)
        filter_form.addRow("Kľúčové slová", self.keywords)
        self.product_ids = QTextEdit()
        self.product_ids.setPlaceholderText("napr. ABC-100\nABC-101\n(alebo oddeľte čiarkou)")
        self.product_ids.setFixedHeight(90)
        filter_form.addRow("ID položiek", self.product_ids)
        filters.addWidget(filter_box, 1)

        fields_box = QGroupBox("3  Údaje do výstupu")
        fields_layout = QVBoxLayout(fields_box)
        self.fields = QListWidget()
        for field in ("Kód položky", "Názov", "EAN", "Cena", "DPH", "Dostupnosť", "Popis", "URL"):
            item = QListWidgetItem(field)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if field in {"Kód položky", "Názov", "Cena"} else Qt.Unchecked)
            self.fields.addItem(item)
        fields_layout.addWidget(self.fields)
        filters.addWidget(fields_box, 1)
        root.addLayout(filters)

        export_box = QGroupBox("4  Výstup")
        export_layout = QHBoxLayout(export_box)
        self.html = QRadioButton("HTML podľa šablóny OBERON")
        self.html.setChecked(True)
        self.html.setEnabled(False)
        export_layout.addWidget(self.html)
        export_layout.addWidget(QLabel("CSV a Excel budú doplnené neskôr."))
        export_layout.addStretch()
        root.addWidget(export_box)

        actions = QHBoxLayout()
        actions.addStretch()
        self.preview_button = QPushButton("Zobraziť náhľad")
        self.preview_button.clicked.connect(self._start_extraction)
        actions.addWidget(self.preview_button)
        self.extract_button = QPushButton("Spustiť extrakciu")
        self.extract_button.setObjectName("primaryButton")
        self.extract_button.clicked.connect(self._start_extraction)
        actions.addWidget(self.extract_button)
        root.addLayout(actions)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Pripravené na nastavenie prvej extrakcie")

    def _start_extraction(self) -> None:
        if self.input_mode.currentIndex() == 1:
            self.statusBar().showMessage("HTML vstup je pripravený; spracovanie šablóny OBERON doplníme v ďalšom kroku.")
            return
        url = self.url.text().strip()
        keywords = [line.strip() for line in self.keywords.toPlainText().splitlines() if line.strip()]
        product_ids = [item.strip() for item in re.split(r"[,\n;]+", self.product_ids.toPlainText()) if item.strip()]
        if not url:
            self.statusBar().showMessage("Zadajte adresu stránky dodávateľa.")
            self.url.setFocus()
            return
        if not keywords and not product_ids:
            self.statusBar().showMessage("Zadajte aspoň jedno kľúčové slovo alebo ID položky.")
            self.keywords.setFocus()
            return

        self.preview_button.setEnabled(False)
        self.extract_button.setEnabled(False)
        self.statusBar().showMessage("Spracovanie prebieha na pozadí; okno zostáva aktívne...")

        self.thread = QThread(self)
        self.worker = ExtractionWorker(url, keywords, product_ids)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._extraction_finished)
        self.worker.failed.connect(self._extraction_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)
        self.thread.start()

    def _load_profiles(self) -> dict[str, dict[str, str]]:
        try:
            return json.loads(self.profiles_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _load_selected_profile(self, name: str) -> None:
        if name == "Nový dodávateľ":
            self.supplier_name.clear()
            self.url.clear()
            return
        profile = self.profiles.get(name, {})
        self.supplier_name.setText(name)
        self.url.setText(profile.get("url", ""))
        self.keywords.setPlainText(profile.get("keywords", ""))
        self.product_ids.setPlainText(profile.get("product_ids", ""))

    def _change_input_mode(self, index: int) -> None:
        is_html = index == 1
        self.supplier.setEnabled(not is_html)
        self.supplier_name.setEnabled(not is_html)
        self.url.setVisible(not is_html)
        self.url_label.setVisible(not is_html)
        self.html_code.setVisible(is_html)
        self.html_code_label.setVisible(is_html)

    def _save_profile(self) -> None:
        name = self.supplier_name.text().strip()
        url = self.url.text().strip()
        if not name or not url:
            self.statusBar().showMessage("Na uloženie profilu zadajte názov a adresu stránky.")
            return
        self.profiles[name] = {
            "url": url,
            "keywords": self.keywords.toPlainText(),
            "product_ids": self.product_ids.toPlainText(),
        }
        try:
            self.profiles_path.parent.mkdir(parents=True, exist_ok=True)
            self.profiles_path.write_text(json.dumps(self.profiles, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as error:
            self.statusBar().showMessage(f"Profil sa nepodarilo uložiť: {error}")
            return
        if self.supplier.findText(name) == -1:
            self.supplier.addItem(name)
        self.supplier.setCurrentText(name)
        self.statusBar().showMessage(f"Profil dodávateľa '{name}' bol uložený.")

    @Slot(str)
    def _extraction_finished(self, message: str) -> None:
        self.statusBar().showMessage(message)

    @Slot(str)
    def _extraction_failed(self, message: str) -> None:
        self.statusBar().showMessage(f"Extrakcia zlyhala: {message}")

    @Slot()
    def _thread_finished(self) -> None:
        self.preview_button.setEnabled(True)
        self.extract_button.setEnabled(True)
        self.worker = None
        self.thread = None


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QWidget { background: #f4f1eb; color: #263238; font-size: 14px; }
        QMainWindow { background: #f4f1eb; }
        QLabel#heading { color: #173f43; font-size: 26px; font-weight: 700; }
        QLabel#subtitle { color: #657276; font-size: 15px; }
        QGroupBox { border: 1px solid #d6d0c6; border-radius: 6px; margin-top: 10px; padding: 16px 12px 12px; font-weight: 700; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #287271; }
        QLineEdit, QTextEdit, QComboBox, QListWidget { background: #fffdfa; border: 1px solid #c9c2b8; border-radius: 4px; padding: 7px; }
        QPushButton { background: #e7dfd2; border: 1px solid #c9c2b8; border-radius: 4px; padding: 10px 16px; font-weight: 600; }
        QPushButton:hover { background: #dcd0c0; }
        QPushButton#primaryButton { background: #287271; color: white; border: none; }
        QPushButton#primaryButton:hover { background: #1f5c5c; }
        QStatusBar { color: #657276; }
        """
    )
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())