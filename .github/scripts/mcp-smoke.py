#!/usr/bin/env python3
"""MCP-Smoke-Test — startet einen Server und spricht das Protokoll mit ihm.

Beantwortet die Frage, die ein Import-Test NICHT beantwortet:
    Startet dieser Server nach einer Frischinstallation und liefert er Tools?

WARUM ES DEN GIBT (2026-07-31):
Am 30.07. wurden sechs eigene MCP-Server auf ein neues SDK umgestellt und
gemerged. Am 31.07. waren fuenf davon tot — die CI hatte nichts gemerkt,
weil sie nur `pytest` laeuft. Ein Server, dessen Tools in Dekoratoren
registriert werden, laesst sich importieren, ohne zu starten; und ein
Import-Test sagt nichts darueber, ob der Handshake funktioniert.

WARUM NICHT NUR "importiert der Server":
Genau dieser zu schwache Test steht am 30.07. im Lernprotokoll
("Import-Test zu schwach — Dekoratoren in Funktionen"). Hier wird deshalb
das echte Protokoll gesprochen: initialize -> initialized -> tools/list.
Erst eine nicht-leere Tool-Liste ist ein bestandener Smoke-Test.

Aufruf:
    python3 mcp-smoke.py -- <serverbefehl...>
    python3 mcp-smoke.py --min-tools 3 -- uv run --directory /pfad wetter-mcp

Exit: 0 = Handshake ok und Tools geliefert
      1 = Server antwortet nicht / falsch / zu wenige Tools
      2 = Aufruffehler
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import threading

PROTOKOLL = "2025-06-18"


def _leser(strom, ziel_json, ziel_roh):
    """Einen Strom zeilenweise einsammeln, in einem eigenen Thread.

    ⚠️ Bewusst `readline()` statt `for zeile in strom`: Die Iteration ueber
    eine Pipe liest im Voraus und blockiert, bis der interne Puffer voll
    ist — bei einem Server, der genau drei kurze Zeilen antwortet und dann
    schweigt, kommt nie etwas an. Genau daran ist der erste Entwurf am
    31.07. haengengeblieben, obwohl derselbe Server auf der Kommandozeile
    (`printf … | uv run …`) sofort korrekt antwortete.
    """
    try:
        while True:
            zeile = strom.readline()
            if not zeile:
                break
            zeile = zeile.strip()
            if not zeile:
                continue
            if ziel_roh is not None:
                ziel_roh.append(zeile)
            if ziel_json is None:
                continue
            try:
                ziel_json.append(json.loads(zeile))
            except json.JSONDecodeError:
                # Server, die Logzeilen nach stdout schreiben, sind haeufig.
                # Kein Fehler, solange die JSON-Antwort auch kommt.
                pass
    except Exception:
        pass


def smoke(befehl: list[str], timeout: float, min_tools: int) -> int:
    umgebung = dict(os.environ)
    # Unbuffered, sonst haengt die Antwort im Puffer und der Timeout
    # schlaegt zu, obwohl der Server laengst geantwortet hat.
    umgebung["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.Popen(
            befehl, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=umgebung,
        )
    except FileNotFoundError as e:
        print(f"⛔ Befehl nicht ausfuehrbar: {e}")
        return 2

    antworten: list[dict] = []
    stderr_zeilen: list[str] = []
    # ⚠️ stderr MUSS parallel mitgelesen werden. FastMCP-Server schreiben
    # beim Start ein Banner dorthin; wird die Pipe erst am Ende geleert,
    # blockiert der Server, sobald der Puffer voll ist — und antwortet nie.
    threading.Thread(target=_leser, args=(proc.stdout, antworten, None), daemon=True).start()
    threading.Thread(target=_leser, args=(proc.stderr, None, stderr_zeilen), daemon=True).start()

    def sende(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    try:
        sende({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOKOLL,
            "capabilities": {},
            "clientInfo": {"name": "mcp-smoke", "version": "1.0"},
        }})
        sende({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        sende({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    except BrokenPipeError:
        time.sleep(0.5)
        fehler = "\n".join(stderr_zeilen)
        print("⛔ Server hat die Verbindung sofort geschlossen — er startet nicht.")
        if fehler:
            print("   stderr (letzte Zeilen):")
            for z in fehler.splitlines()[-8:]:
                print(f"     {z}")
        return 1

    # ⚠️ NICHT auf das Ende des Reader-Threads warten: ein laufender Server
    # schliesst stdout nie, das Event kaeme also erst beim Timeout. Der erste
    # Entwurf tat genau das und blockierte volle 45s pro Server, auch wenn die
    # Antwort nach 200 ms da war. Stattdessen pollen, bis beide Antworten
    # vorliegen — oder der Prozess stirbt.
    start = time.monotonic()
    frist = start + timeout
    while time.monotonic() < frist:
        habe_init = any(a.get("id") == 1 for a in antworten)
        habe_tools = any(a.get("id") == 2 for a in antworten)
        if habe_init and habe_tools:
            break
        if proc.poll() is not None:
            break  # Server beendet — weiteres Warten bringt nichts
        time.sleep(0.05)

    dauer = time.monotonic() - start
    init = next((a for a in antworten if a.get("id") == 1), None)
    tools_antwort = next((a for a in antworten if a.get("id") == 2), None)

    fehler = "\n".join(stderr_zeilen)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    def stderr_zeigen():
        if fehler:
            print("   stderr (letzte Zeilen):")
            for z in fehler.splitlines()[-10:]:
                print(f"     {z}")

    if init is None:
        print(f"⛔ Keine Antwort auf 'initialize' nach {dauer:.1f}s "
              f"(Timeout {timeout:.0f}s, Prozess-Exit {proc.returncode}).")
        stderr_zeigen()
        return 1
    if "error" in init:
        print(f"⛔ 'initialize' abgelehnt: {init['error']}")
        stderr_zeigen()
        return 1

    server = init.get("result", {}).get("serverInfo", {})
    version = init.get("result", {}).get("protocolVersion", "?")
    print(f"  ✔ initialize   {server.get('name','?')} {server.get('version','')} "
          f"(Protokoll {version})")

    if tools_antwort is None:
        print(f"⛔ Keine Antwort auf 'tools/list' nach {dauer:.1f}s "
              f"(Timeout {timeout:.0f}s).")
        stderr_zeigen()
        return 1
    if "error" in tools_antwort:
        print(f"⛔ 'tools/list' abgelehnt: {tools_antwort['error']}")
        stderr_zeigen()
        return 1

    tools = tools_antwort.get("result", {}).get("tools", [])
    print(f"  ✔ tools/list   {len(tools)} Tools")

    # Eine leere Tool-Liste ist die heimtueckischste Variante: der Server
    # laeuft, der Handshake klappt, und er kann nichts. Ohne diese Schwelle
    # waere das ein bestandener Test — ein gruenes Haekchen aus null Inhalt.
    if len(tools) < min_tools:
        print(f"⛔ Zu wenige Tools: {len(tools)} < {min_tools} erwartet.")
        print("   Der Server laeuft, registriert aber (fast) nichts —"
              " typisch nach einem SDK-Wechsel, bei dem die Dekoratoren"
              " nicht mehr greifen.")
        return 1

    namen = ", ".join(t.get("name", "?") for t in tools[:6])
    if len(tools) > 6:
        namen += f", … (+{len(tools)-6})"
    print(f"    {namen}")
    print(f"✅ Smoke bestanden ({dauer:.1f}s).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--timeout", type=float, default=45.0)
    ap.add_argument("--min-tools", type=int, default=1,
                    help="Mindestzahl Tools (Default 1 — 0 waere kein Test)")
    ap.add_argument("befehl", nargs=argparse.REMAINDER)
    a = ap.parse_args()

    befehl = a.befehl[1:] if a.befehl and a.befehl[0] == "--" else a.befehl
    if not befehl:
        print("⛔ Kein Serverbefehl. Aufruf: mcp-smoke.py -- <befehl...>")
        return 2

    print(f"── MCP-Smoke: {' '.join(befehl)}")
    return smoke(befehl, a.timeout, a.min_tools)


if __name__ == "__main__":
    sys.exit(main())
