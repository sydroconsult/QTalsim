# Git-Workflow

## Commits
- Vor jedem `git commit`: erst die vorgesehenen Dateien (git status/diff),
  die vollständige Commit-Message und die zu verwendende git-Identität im
  Klartext zeigen und auf explizite Bestätigung des Nutzers warten —
  nicht direkt committen.
- Git-Identität: **nicht** hardcoden, sondern vor jedem Commit den lokal
  bereits konfigurierten `git config user.name`/`user.email` auslesen und
  anzeigen (die Werte sind personenabhängig — pro Rechner/Mitwirkendem
  unterschiedlich — und gehören daher nicht fest in eine geteilte Datei).
  Fällt das lokale Config leer oder unerwartet aus (siehe die fälschlich
  autogenerierte Identität in Commit `0a433ff` als Negativbeispiel), erst
  beim Nutzer nachfragen statt zu raten oder zu überschreiben.
- Von Claude Code erstellte Commits enthalten am Ende der Commit-Message
  eine `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`-Zeile.
- Nur explizit angeforderte Dateien stagen (kein `git add -A`/`git add .`)
  — z. B. `notes.md` (untracked, lokale Analysenotizen) soll nicht
  automatisch mitcommittet werden, wenn es nicht Teil der besprochenen
  Änderung ist.

## Releases
- Vor Beginn: den Nutzer explizit nach der Versionsnummer fragen — nie
  selbst festlegen/raten (auch nicht "naheliegend" aus SemVer ableiten und
  direkt verwenden). Vorschlagen darf man einen Kandidaten (z. B. anhand
  der Art der Änderungen seit dem letzten Tag: nur Fixes → Patch, neue
  Funktionalität → Minor), aber die Bestätigung/Entscheidung kommt vom
  Nutzer.
- Zu aktualisierende Dateien (alle drei müssen dieselbe Versionsnummer
  tragen):
  - `QTalsim/metadata.txt` — Feld `version=`
  - `QTalsim/CHANGELOG.md` — neuer Eintrag oben (siehe Format unten)
  - `docs/conf.py` — Feld `release =`
- Vor dem Vorschlag: `docs/` gegen die Commits seit dem letzten Tag
  prüfen (`git log <letzter-tag>..HEAD --stat`) — sind alle
  nutzer-sichtbaren Änderungen (neue Features, geänderte Abläufe) in den
  betroffenen `.rst`-Dateien nachgezogen? Falls nicht: fehlende
  Doku-Updates explizit benennen, nicht stillschweigend übergehen oder
  selbst nachdichten.
- CHANGELOG-Format exakt wie bisherige Einträge in `QTalsim/CHANGELOG.md`
  beibehalten:
  ```
  ## \[X.Y.Z] - YYYY-MM-DD

  * Fixes

    * <Bereich, z. B. "HRU Calculation">
      * <Fix-Beschreibung>

  * Enhancements

    * <Bereich>
      * <Enhancement-Beschreibung>
  ```
  (Reihenfolge Fixes vor Enhancements, zweistufige Bullet-Verschachtelung
  nach Bereich, Datum im ISO-Format.)
- Immer einen konkreten Vorschlag für **beides** liefern, bevor etwas
  geändert wird: (a) den CHANGELOG-Eintrag im obigen Format, (b) eine
  Release-Message (analog zur Commit-Message bei normalen Commits) —
  und auf Bestätigung warten, wie bei normalen Commits (siehe oben).
- Vor dem eigentlichen Tag/Release zusätzlich:
  - Testsuite lokal laufen lassen (siehe Haupt-`CLAUDE.md`,
    `docker compose run --rm qtalsim-tests` bzw. lokale
    QGIS-Python-Route, falls Docker nicht verfügbar ist) und Ergebnis
    zeigen, nicht nur annehmen, dass es passt.
  - Arbeitsverzeichnis auf unerwartete/unbesprochene uncommittete
    Änderungen prüfen (`git status`), bevor getaggt wird.
  - Prüfen, ob die vorgeschlagene Versionsnummer nicht bereits als Tag
    existiert (`git tag --list`).
  - Nach leftover TODO/Debug-Kommentaren oder offensichtlich
    unfertigem Code in den seit dem letzten Release geänderten Dateien
    schauen und explizit melden (nicht automatisch entfernen, außer
    abgesprochen).
- Das eigentliche Tag-Erstellen/Pushen und Anlegen des GitHub-Release
  (was den `release.yaml`-Workflow auslöst — `qgis-plugin-ci package`
  + Upload ins OSGeo-Plugin-Repository, also eine echte, kaum
  rückgängig zu machende Veröffentlichung) ist ein separater,
  eigens zu bestätigender Schritt — nicht automatisch an die
  Datei-Updates oben anschließen.
