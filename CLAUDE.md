# QTalsim — CLAUDE.md

## Kurzbeschreibung
QGIS-Plugin (Package `QTalsim/`), das räumliche Eingangsdaten (Landnutzung,
Bodenarten, Teilgebiete) zu Eingabedateien für das Wasserhaushaltsmodell
Talsim (http://www.talsim.de) aufbereitet — im Kern die Berechnung
Hydrologischer Response Units (HRUs).

## Fachlicher Kontext
Fünf Hauptfunktionen (siehe `initGui()` in `qtalsim.py`):
1. HRU-Berechnung (Verschneidung Landuse × Soil × Subbasin)
2. Direkte Verbindung zu einer Talsim-SQLite-Datenbank (System-Elemente,
   Teilgebiete, Transportstrecken bearbeiten)
3. Teilgebiets-Vorverarbeitung + längster Fließweg (Whitebox Tools)
4. ISRIC-Bodendaten-Download → Bodenart-/Lagerungsdichteklassen
5. Landnutzungs-Mapping (deutsche ATKIS/LBM-Daten oder ESA WorldCover
   → Talsim-Landnutzungsklassen)

## Architektur / Datenfluss
Landuse-Dialog, Soil-Dialog und Subbasin-Dialog erzeugen jeweils
eigenständig aufbereitete Layer (Talsim-Landnutzung, Bodenart+Lagerungsdichte,
Teilgebiet mit Höhe/Fläche/Flowpath). Die eigentliche HRU-Verschneidung
(`performIntersect`, `qtalsim.py:2658`) läuft in der Hauptplugin-Klasse, nicht
in den Dialogen. Attribut-Schema und Wertebereiche kommen aus
`talsim_parameter/*.csv` (landuseParameter, soilParameter,
landuseParameterValues, `*_talsim_zuordnung`-Mapping-Tabellen). Die
SQLite-DB-Anbindung (`qtalsim_sqllite_dialog.py`) zum Bearbeiten bestehender
Szenarien (System-Elemente/Teilgebiete/Transportstrecken) ist ein separater,
unabhängiger Pfad — sie hat keinen Bezug zu `talsim_parameter/`.

## Zwei endgültige Datei-Outputs — Talsim 5 (DB) vs. Talsim 4 (ASCII)

Am Ende der HRU-Berechnung entscheidet der Nutzer per Checkbox in
`qtalsim.py::saveFiles()` (Z.4166), welche(s) Zielformat(e) geschrieben
werden — `groupboxDBExport` bzw. `groupboxASCIIExport`. Beide Pfade sind
unabhängig von der GeoPackage-Sicherung, die `saveFiles()` immer zusätzlich
anlegt.

### Talsim 5 — SQLite-Datenbank
Reihenfolge ist zwingend, **erst Sub-basin-Preprocessing, dann HRU
Calculation**:

1. `qtalsim_subbasin_dialog.py::DBExport()` (Z.974) — erzeugt die DB
   überhaupt erst: kopiert die leere Schema-Vorlage `QTalsim/DB/QTalsim.db`
   nach `outputFolder/<dbName>.db`, legt darin `ScenarioFolder` + `Scenario`
   an und schreibt die vorverarbeiteten Teilgebiete als `SystemElement`
   /`SubBasin`-Zeilen (inkl. Transformation des ZOUT-Punkts nach EPSG:4326).
2. `qtalsim.py::DBExport()` (Z.3687) — verbindet sich mit einer
   **bereits existierenden** DB (`self.file_path_db`, vom Nutzer
   ausgewählt — i.d.R. genau die in Schritt 1 erzeugte Datei), prüft/löscht
   ggf. vorhandene Einträge für das Scenario (mit Rückfrage) und fügt
   `Landuse`/`SoilTexture`/`SoilType`/`HydrologicalResponseUnit`/`Pattern`
   -Zeilen für dieselbe `ScenarioId` ein.

   **Achtung, Verwechslungsgefahr**: Es gibt zwei Methoden mit demselben
   Namen `DBExport()` in zwei verschiedenen Dateien/Klassen mit
   unterschiedlicher Aufgabe (DB *anlegen* vs. DB *befüllen*) — beim
   Navigieren/Suchen im Code immer die Datei mitprüfen, nicht nur den
   Methodennamen.

### Talsim 4 — ASCII/Text-Dateien
Kein bekannter Ordering-Zwang zwischen den beiden folgenden Exporten
(nicht tief geprüft):

1. `qtalsim_subbasin_dialog.py::asciiExport()` (Z.1092) — schreibt
   `.EZG` (Teilgebiets-Attribute: ID, Fläche, Versiegelung, Höhe min/max,
   Flowpath-Länge) basierend auf `talsim_parameter/template.EZG`.
2. `qtalsim.py::saveASCII()` (Z.3302) — schreibt weitere Talsim-4-Textdateien
   (u. a. `.EFL`) über ein generisches Parsen der Feldlängen-Definitionszeile
   (`<---->`-Syntax) in den `talsim_parameter/template.*`-Dateien.

## Modulübersicht
| Datei | Zeilen | Rolle |
|---|---|---|
| `__init__.py` | 36 | `classFactory` |
| `qtalsim.py` | ~4600 | Plugin-Lifecycle (initGui/unload) **+** HRU-Kernlogik (`performIntersect`), Geometrie-Helfer, beide Talsim-5/Talsim-4-Exportpfade der HRU Calculation (`DBExport`, `saveASCII`, `saveFiles`) |
| `qtalsim_dialog.py` | 44 | reines UI-Boilerplate für den Haupt-HRU-Dialog |
| `qtalsim_subbasin_dialog.py` | ~1250 | Teilgebiets-Vorverarbeitung, Flowpath (Whitebox); erzeugt die Talsim-5-DB (`DBExport`) bzw. schreibt `.EZG` (`asciiExport`) |
| `qtalsim_soil_dialog.py` | ~1500 | ISRIC-Download, Bodenart-/BDOD-Klassifikation |
| `qtalsim_landuse_dialog.py` | ~950 | ATKIS/LBM/ESA-Mapping auf Talsim-Landnutzung |
| `qtalsim_sqllite_dialog.py` | ~1500 | Direkter SQLite-CRUD gegen ein **bestehendes** Talsim-Szenario (System-Elemente/Teilgebiete/Transportstrecken bearbeiten) — kein Bezug zu `talsim_parameter/` |
| `resources.py` | 7222 (autogeneriert) | `pyrcc5`-Output aus `resources.qrc` — nie von Hand editieren |
| `talsim_parameter/` | — | CSV-Mappings + Talsim-4-ASCII-Template-Dateien (`template.EZG/.EFL/.TRS/.SYS/.BOD/.BOA/.LNZ`) |
| `DB/QTalsim.db` | — | Leere Schema-Vorlage-Datenbank, die bei jedem Talsim-5-Export (`qtalsim_subbasin_dialog.py::DBExport`) kopiert und befüllt wird |

## ⚠️ Stub-Version ≠ Minimum-Version
`metadata.txt` deklariert `qgisMinimumVersion=3.34`, `qgisMaximumVersion`
ist **nicht gesetzt**. Die einzigen lokal verfügbaren `.pyi`-Stubs
(`C:\Program Files\QGIS 3.44.11\apps\qgis-ltr\python\qgis\_core.pyi` /
`_gui.pyi` / `_analysis.pyi`) stammen aber von **QGIS 3.44**, zehn Minor-
Versionen später. Vor jeder Nutzung/Empfehlung einer PyQGIS-API:
1. Signatur im Stub nachschlagen und Datei:Zeile zitieren — niemals raten.
2. Bei Unsicherheit, ob die API schon in 3.34 existierte, auf
   api.qgis.org gegenprüfen ("Added in QGIS x.x").
3. `@deprecated(...)`-Marker im Stub bedeuten "veraltet in 3.44", nicht
   zwangsläufig "existierte nicht in 3.34" — beides separat prüfen.

## Python-Interpreter
Kein globales `python`/`python3` verwenden — das unter Windows per
`where python` gefundene Executable ist nur der Windows-Store-Alias-Stub,
ohne `qgis`-Modul.
- **Für PyQGIS-Code (lokal, Windows)**: über
  `C:\Program Files\QGIS 3.44.11\bin\python-qgis-ltr.bat` ausführen
  (setzt `OSGEO4W_ROOT`, `PYTHONPATH` auf `apps\qgis-ltr\python`, ruft
  dann den mitgelieferten Python 3.12 unter `apps\Python312` auf).
  Das `.bat` ist eine cmd-Batchdatei — unter Git Bash nicht direkt
  ausführbar, nur über echtes `cmd.exe`/PowerShell.
- **Für Tests (Docker/CI)**: `/opt/venv/bin/python` innerhalb des
  `qgis/qgis:latest`-Containers (siehe `Dockerfile`), `--system-site-packages`
  für Zugriff auf die im Image installierten `qgis`-Module.

## Build / Reload / Test
- Reload während Entwicklung: Plugin-Reloader-Plugin in QGIS verwenden,
  ODER QGIS neu starten — `unload()` trennt aktuell keine Signale und
  schließt keine offenen Fenster (siehe TODOs), Reload kann also alte
  Fenster hinterlassen.
- Deploy/Packen: primär `qgis-plugin-ci package <version>` (siehe
  `.qgis-plugin-ci`, `.github/workflows/release.yaml`). **Nicht**
  `pb_tool`/`make deploy` verwenden — `pb_tool.cfg`/`Makefile` listen nur
  `qtalsim.py`+`qtalsim_dialog.py`, die vier weiteren Dialogmodule und
  `talsim_parameter/`, `symbology/`, `DB/` fehlen dort.
- Tests lokal/CI: `docker compose run --rm qtalsim-tests` (führt
  `tests_runner.sh` aus) → aktuell **nur** `pytest test/test_qtalsim_dialog.py`,
  die übrigen Testdateien unter `test/` laufen in CI nicht mit.
- PyQt6-Kompatibilitätscheck vorhanden, aber ungenutzt:
  `run_pyqt_checker.bat` (Docker-Image `ghcr.io/qgis/pyqgis4-checker`) →
  schreibt nach `pyqt6_checker.log` (aktuell leer/nie ausgeführt).

## Git-Workflow (Commits, Releases)
Siehe @.claude/git.md

## TODOs aus der Analyse
- [ ] `unload()` in `qtalsim.py` (Z.296-310): alle `.connect()`-Verbindungen
      trennen und `self.dlg`/`sqlConnectDock`/`subBasinWindow`/`soilWindow`/
      `landuseWindow` schließen.
- [ ] `test/test_qtalsim_dialog.py:4` — `from PyQt6.QtCore import QSettings`
      klären/entfernen (Mischung mit `qgis.PyQt`-Shim in derselben Datei).
- [ ] `qtalsim_subbasin_dialog.py:965` — `writeAsVectorFormat` (voll
      deprecated) auf `writeAsVectorFormatV2` migrieren, konsistent zum
      Rest des Codes.
- [ ] `pb_tool.cfg`/`Makefile` Dateilisten vervollständigen oder als
      unbenutzt markieren/entfernen, falls `qgis-plugin-ci` der einzige
      echte Release-Pfad ist.
- [ ] `qgisMaximumVersion` in `metadata.txt` setzen, bevor eine
      QGIS-Version mit Qt6-Standard erscheint.
- [ ] `tests_runner.sh` um die übrigen `test/*.py`-Dateien erweitern oder
      begründen, warum sie ausgeschlossen sind.
- [ ] Die beiden gleichnamigen `DBExport()`-Methoden (`qtalsim.py:3687` und
      `qtalsim_subbasin_dialog.py:974`) umbenennen oder zumindest im
      Docstring klar auf die jeweils andere verweisen, um Verwechslung
      vorzubeugen.
