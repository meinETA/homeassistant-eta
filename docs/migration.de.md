# Umzug auf ETA Heating

[English version](migration.md)

Diese Anleitung ist für Installationen, die noch das bisherige Repository `Tidone/homeassistant_eta_integration` nutzen. Version 1.4.3 dieses Repositorys sichert die Einrichtung automatisch, sodass ETA Heating sie ohne neuen Scan wiederherstellen kann.

Die bisherige Version funktioniert weiter, erhält aber keine Updates mehr. Du kannst jederzeit wechseln.

## Was erhalten bleibt

- Ausgewählte Entitäten und Einstellungen
- Entity-IDs und Geräte-IDs
- Namen, Bereiche, Labels sowie der Status deaktiviert oder ausgeblendet
- Verlauf

## Bevor du startest

1. Erstelle ein Home-Assistant-Backup.
2. Aktualisiere die bisherige Integration auf **1.4.3**.
3. Starte Home Assistant einmal neu. Dabei wird die Einrichtung in `.storage/eta_webservices.migration` gesichert.

Nur Version 1.4.3 sichert deine Einrichtung. Wechselst du direkt von 1.4.2 oder älter, ist nichts gesichert. Dann musst du ETA Heating komplett neu einrichten, inklusive Scan und Auswahl.

## Home Assistant 2026.11 und neuer

Der Marketplace erlaubt keine zwei installierten Repositorys mit derselben Domain, deshalb muss die bisherige Integration zuerst entfernt werden.

1. Gehe zu **Einstellungen → Marketplace** und öffne die installierte Integration **ETA**.
2. Öffne das Drei-Punkte-Menü, wähle **Uninstall** und bestätige **Delete and uninstall**.
3. Öffne in der Marketplace-Übersicht das Drei-Punkte-Menü, wähle **Custom repositories** und entferne das bisherige Repository.
4. Suche nach **ETA Heating**, wähle **Install** und starte Home Assistant neu.
5. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und suche nach **ETA Heating**.
6. Wähle **Vorherige Einrichtung wiederherstellen**.

## Home Assistant 2026.10 und älter

1. Gehe zu **Einstellungen → Geräte & Dienste**, öffne die ETA-Integration und lösche sie.
2. Deinstalliere die bisherige Integration in **HACS** und entferne ihr benutzerdefiniertes Repository.
3. Suche in HACS nach **ETA Heating**, wähle **Download** und starte Home Assistant neu.
4. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen** und suche nach **ETA Heating**.
5. Wähle **Vorherige Einrichtung wiederherstellen**.

## Nach dem Wechsel

Der Eintrag wird automatisch migriert und die gesicherte Einrichtung gelöscht. Prüfe, ob die Entitäten Werte anzeigen und deine Automationen und Dashboards wie gewohnt funktionieren.

Nach der Wiederherstellung kann ein Reparaturhinweis zum Benennungsschema der Entitäten erscheinen. Er dient nur zur Information, du musst nichts tun.

## Fehlerbehebung

**Vorherige Einrichtung wiederherstellen wird nicht angeboten.** Die Einrichtung wurde nicht gesichert, oder dieselbe Adresse ist bereits eingerichtet. Prüfe, ob Version 1.4.3 lief und Home Assistant vor dem Wechsel neu gestartet wurde.

**Der Marketplace meldet, dass das Verzeichnis zu einem anderen Repository gehört.** Die bisherige Integration ist noch installiert. Führe die Schritte 1 bis 3 für deine Home-Assistant-Version aus.
