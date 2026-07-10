#!/usr/bin/env python3
"""
Patch 11.8 : CORRECTIF - bug de snapping pendant le trace d'une
spline, signale par l'utilisateur.

CAUSE : SplineHandler::onMotionNotifyEvent() calcule correctement
this->currPoint en tenant compte de l'alignment_snap complet (guides
vert/rose inclus, patch 8.9/8.9.2). Mais
SplineHandler::onButtonPressEvent() (declenche au clic, pour
COMMITTER le point) ecrasait cette valeur en la recalculant via
snappingHandler.snap() seul - un mecanisme bien plus simple
(grille/angle/distance uniquement, SANS les guides d'alignement).
Resultat : si le point mobile etait snape au moment du clic, il
"sautait" visiblement a la position brute du curseur juste avant que
le segment ne soit trace definitivement.

CORRECTIF : this->currPoint n'est plus recalcule dans
onButtonPressEvent() - le clic committe desormais directement la
valeur deja calculee par le dernier onMotionNotifyEvent(), snapee ou
non. Le segment suivant continue de re-evaluer normalement l'accroche
a chaque mouvement de souris (comportement inchange).

Modifie : src/core/control/tools/SplineHandler.cpp (1 zone)

NECESSITE : apply_alignment_snap_v90_4.py (ou apply_alignment_snap_v90.py
+ 11.1 a 11.7 selon votre process)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """        xoj_assert(!this->knots.empty());
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        this->currPoint = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());
        double dist = this->buttonDownPoint.lineLengthTo(this->knots.front());
"""
NEW_1 = """        xoj_assert(!this->knots.empty());
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        // Patch 11.8: `this->currPoint` is NOT recomputed here anymore - it already holds the correct
        // value set by the preceding onMotionNotifyEvent() call, which (unlike snappingHandler.snap()
        // alone) also accounts for the full ordinary (green/pink) alignment guide matching. Discarding
        // that and recomputing via snappingHandler.snap() here (as before) meant a snapped moving
        // point would visibly jump back to the raw cursor position right as the segment got committed
        // - the click should always commit whatever was actually being previewed, snapped or not.
        double dist = this->buttonDownPoint.lineLengthTo(this->knots.front());
"""


def main():
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] SplineHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "isSplineSnappingEnabled" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] isSplineSnappingEnabled introuvable dans SplineHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py (ou v90_4), puis relancez ce script.")
        sys.exit(1)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count == 0:
        if text.count(NEW_1) > 0:
            print("[SKIP] Le patch 11.8 semble deja applique.")
            sys.exit(0)
        print("[ECHEC] Motif introuvable dans SplineHandler.cpp.")
        sys.exit(1)
    if count > 1:
        print(f"[ECHEC] Motif trouve {count} fois dans SplineHandler.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    SplineHandler.cpp: currPoint n'est plus ecrase au clic")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
