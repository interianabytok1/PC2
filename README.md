# Extrahovanie položiek pre import do OBERON-u

Desktopová aplikácia na získanie vybraných položiek z webových stránok dodávateľov alebo z HTML kódu a ich prípravu na import do systému OBERON.

## Schválený princíp

### Vstup 1: webová stránka

Používateľ vyberie dodávateľa a zadá ID položiek a voliteľné pole kľúčových slov.

### Vstup 2: HTML

Používateľ vloží HTML kód alebo načíta HTML súbor. Tento režim je určený aj pre uložené stránky dodávateľov.

### Výstup

Oba vstupy budú spracované do HTML podľa šablóny OBERON-u. Výstup CSV a Excel je plánovaný na neskoršiu etapu.

## Stav projektu

Aktuálne je pripravený základ desktopového rozhrania, výber oboch vstupných režimov a bezpečné spúšťanie webových požiadaviek mimo hlavného okna. Spracovanie HTML šablóny OBERON doplníme po dodaní šablóny.

## Spustenie

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Na Windows aktivácia virtuálneho prostredia používa `.venv\\Scripts\\activate`.

## Vytvorenie samostatnej aplikácie

Na počítači, ktorý zodpovedá cieľovému operačnému systému, spustite:

Windows:

```bat
build_windows.bat
```

Pre vytvorenie aplikácie a odkazu na ploche spustite vo Windows:

```bat
install_windows.bat
```

Skript vytvorí aplikáciu v `%USERPROFILE%\PolozkyPreOberon` a odkaz `PolozkyPreOberon.lnk` na ploche. Zdrojový projekt ostáva oddelený, aby sa pri aktualizáciách neprepísali používateľské profily a nastavenia.

Linux:

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Výsledná aplikácia bude v priečinku `release`. Na cieľovom počítači už nebude potrebné inštalovať Python ani PySide6. Balík treba vytvoriť samostatne pre Windows, Linux a macOS; PyInstaller nevytvára jeden univerzálny súbor pre všetky operačné systémy.

### Windows bez Pythonu

Pre počítač používateľa sa nepoužíva `install_windows.bat`, pretože ten slúži na vytvorenie aplikácie a vyžaduje Python. Najjednoduchší výsledok je súbor `PolozkyPreOberon-Setup.exe`:

1. Na GitHube otvor repozitár a kartu **Actions**.
2. Vyber **Build Windows application**.
3. Klikni **Run workflow** a potvrď spustenie.
4. Po dokončení otvor hotový beh workflow a v časti **Artifacts** stiahni `PolozkyPreOberon-Windows`.
5. Z balíka vyber `PolozkyPreOberon-Setup.exe`.
6. Dvakrát klikni na `PolozkyPreOberon-Setup.exe` a prejdi inštaláciou.
7. Inštalátor vytvorí aplikáciu aj odkaz na ploche. Python nebude potrebný.

Na cieľovom počítači nebude potrebný Python, PySide6 ani VS Code. Pri každej novej verzii workflow vytvorí nový jednoklikový inštalátor.

Aktualizácie sa najprv vykonajú v zdrojovom projekte a následným opätovným spustením `install_windows.bat` sa vytvorí nová verzia `.exe`. Automatické ukladanie zmien zdrojového kódu rieši Git alebo synchronizácia projektu, nie samotná nainštalovaná aplikácia.

## Ďalšie kroky

1. Dodať HTML šablónu OBERON a ukážkové údaje položky.
2. Implementovať extrakciu z HTML kódu alebo súboru.
3. Pridať prvý konektor pre konkrétneho dodávateľa.
4. Implementovať náhľad a generovanie HTML podľa šablóny.
5. Doplniť CSV/Excel.