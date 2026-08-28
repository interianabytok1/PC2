# Extrahovanie položiek pre import do OBERON-u

Jednoduchá desktop aplikácia na získanie vybraných položiek z webových stránok dodávateľov alebo z HTML kódu a ich prípravu na import do systému OBERON.

## Schválený princíp

### Vstup 1: webová stránka

Používateľ vyberie dodávateľa a zadá ID položiek a voliteľné pole kľúčových slov.

### Vstup 2: HTML

Používateľ vloží HTML kód alebo načíta HTML súbor. Tento režim je určený aj pre uložené stránky dodávateľov.

### Výstup

Oba vstupy budú spracované do HTML podľa šablóny OBERON-u. Výstup CSV a Excel je plánovaný na neskoršiu etapu.

## Stav projektu

Aktuálne je pripravená jednoduchá desktop aplikácia spúšťaná jedným `.exe` súborom. Po štarte otvorí jedno okno aplikácie bez prehliadača a bez lokálneho servera.

## Spustenie vo vývoji

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

Výsledná aplikácia bude v priečinku `release`. Na cieľovom počítači už nebude potrebné inštalovať Python. Balík treba vytvoriť samostatne pre Windows, Linux a macOS; PyInstaller nevytvára jeden univerzálny súbor pre všetky operačné systémy.

### Windows bez Pythonu

Najjednoduchší výsledok pre Windows 10 a 11 je jeden inštalátor `PolozkyPreOberon-Setup.exe` alebo jeden prenosný súbor `PolozkyPreOberon.exe`.

1. Na GitHube otvor repozitár a kartu **Actions**.
2. Vyber **Build Windows application**.
3. Klikni **Run workflow** a potvrď spustenie.
4. Po dokončení otvor hotový beh workflow a v časti **Artifacts** stiahni `PolozkyPreOberon-Windows`.
5. Z balíka vyber `PolozkyPreOberon-Setup.exe` pre klasickú inštaláciu alebo `PolozkyPreOberon.exe` pre prenosnú verziu.
6. Dvakrát klikni na zvolený súbor.
7. Aplikácia otvorí svoje vlastné okno. Python nebude potrebný.

Ak otvárate portable ZIP, najprv ho celý rozbaľte do priečinka a až potom spustite `PolozkyPreOberon.exe`. Nespúšťajte ho priamo z WinRARu alebo z náhľadu ZIP archívu, pretože aplikácia potrebuje aj sprievodné súbory z priečinka `_internal`.

Na cieľovom počítači nebude potrebný Python ani VS Code. Pri každej novej verzii workflow vytvorí nový jednoklikový inštalátor aj novú prenosnú verziu.

Aktualizácie sa najprv vykonajú v zdrojovom projekte a následným opätovným spustením `install_windows.bat` sa vytvorí nová verzia `.exe`. Automatické ukladanie zmien zdrojového kódu rieši Git alebo synchronizácia projektu, nie samotná nainštalovaná aplikácia.

## Ďalšie kroky

1. Dodať HTML šablónu OBERON a ukážkové údaje položky.
2. Implementovať extrakciu z HTML kódu alebo súboru.
3. Pridať prvý konektor pre konkrétneho dodávateľa.
4. Implementovať náhľad a generovanie HTML podľa šablóny.
5. Doplniť CSV/Excel.