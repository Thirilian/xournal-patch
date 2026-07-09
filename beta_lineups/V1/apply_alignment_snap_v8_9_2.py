#!/usr/bin/env python3
"""
Patch 8.9.2 (depend de 8.9 + 8.9.1) : corrige une erreur de conception du
patch 8.9 signalee par l'utilisateur.

L'accroche d'alignement ordinaire (vert/rose) pour le point mobile de
l'outil spline devait REMPLACER le systeme d'angle/distance existant
(snappingHandler.snap), pas simplement rivaliser avec lui ("le plus
proche gagne", comme initialement concu dans le patch 8.9). Desormais,
des qu'un match d'alignement est trouve sur un axe (dans la tolerance),
il l'emporte sans condition sur cet axe, remplacant entierement ce que le
snap d'angle/distance aurait produit.

NECESSITE : apply_alignment_snap_v8_9.py + apply_alignment_snap_v8_9_1.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD1 = """            // Ordinary (green/pink) alignment for the moving point (patch 8.9): competes, axis by
            // axis, with the angle/distance snap just computed above - whichever is closer to the
            // raw cursor position wins for that axis. Never considers the spline's own knots so far,
            // only other elements already on the page."""
NEW1 = """            // Ordinary (green/pink) alignment for the moving point (patch 8.9, corrected in 8.9.2):
            // on any axis where a match is found, it REPLACES the angle/distance snap computed just
            // above outright - it does not merely compete with it. Never considers the spline's own
            // knots so far, only other elements already on the page."""
OLD2 = """                    matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, tolerance, layer, visibleRect);
                    if (matchX && std::abs(matchX->offset) >= std::abs(snapped.x - this->buttonDownPoint.x)) {
                        matchX.reset();
                    }
                    matchY = findSplinePointAlignmentY(this->buttonDownPoint.y, tolerance, layer, visibleRect);
                    if (matchY && std::abs(matchY->offset) >= std::abs(snapped.y - this->buttonDownPoint.y)) {
                        matchY.reset();
                    }"""
NEW2 = """                    // Ordinary (green/pink) alignment now REPLACES the angle/distance snap on any
                    // axis where a match is found (patch 8.9.2, correcting the original \"closest
                    // wins\" design of patch 8.9) - it no longer competes with it, it simply takes
                    // priority outright.
                    matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, tolerance, layer, visibleRect);
                    matchY = findSplinePointAlignmentY(this->buttonDownPoint.y, tolerance, layer, visibleRect);"""


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: deja applique.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouve {count} fois dans {path} (doit etre unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] SplineHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    text = cpp.read_text(encoding="utf-8")
    if "splineGuideRange" not in text:
        print("[ECHEC] splineGuideRange introuvable dans SplineHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_9.py + v8_9_1.py, puis relancez ce script.")
        sys.exit(1)
    if "REPLACES the angle/distance snap on any" in text:
        print("[SKIP] Le patch 8.9.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD1, NEW1, "SplineHandler.cpp: mise a jour du commentaire (priorite, pas competition)")
    ok &= apply_edit(cpp, OLD2, NEW2, "SplineHandler.cpp: l'alignement remplace desormais l'angle/distance")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
