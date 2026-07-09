#!/usr/bin/env python3
"""
Patch 10.9.2 : CORRECTIF d'une erreur de compilation introduite par le
patch 10.9.

erreur : error: invalid use of incomplete type 'class Settings'

CAUSE : SplineHandler.cpp appelle desormais
control->getSettings()->isSplineSnappingEnabled(), mais n'incluait que
Control.h (qui se contente probablement d'une declaration anticipee de
Settings) - jamais control/settings/Settings.h lui-meme. Sans la
definition complete de la classe, le compilateur ne peut pas resoudre
l'appel a une methode membre.

CORRECTIF : ajoute l'include manquant.

Modifie : src/core/control/tools/SplineHandler.cpp

NECESSITE : apply_alignment_snap_v10_9.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_BLOCK = """#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
"""
NEW_BLOCK = """#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/settings/Settings.h\"             // for Settings
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
"""


def main():
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] SplineHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)

    text = cpp.read_text(encoding="utf-8")
    if "isSplineSnappingEnabled" not in text:
        print("[ECHEC] isSplineSnappingEnabled introuvable dans SplineHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v10_9.py, puis relancez ce script.")
        sys.exit(1)

    count = text.count(OLD_BLOCK)
    if count == 0:
        if text.count(NEW_BLOCK) > 0:
            print("[SKIP] Le patch 10.9.2 semble deja applique.")
            sys.exit(0)
        print("[ECHEC] Motif introuvable dans SplineHandler.cpp.")
        sys.exit(1)
    if count > 1:
        print(f"[ECHEC] Motif trouve {count} fois dans SplineHandler.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    SplineHandler.cpp: ajout de l'include control/settings/Settings.h")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
