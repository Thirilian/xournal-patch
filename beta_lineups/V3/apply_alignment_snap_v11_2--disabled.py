#!/usr/bin/env python3
"""
Patch 11.2 : CORRECTIF - dans le repere equidistant (patch 8.1.0), la
premiere fleche de la double fleche pointait dans le mauvais sens (mais
avec la bonne origine, comme signale par l'utilisateur).

CAUSE (confirmee algebriquement et numeriquement) : drawDoubleArrow()
calcule `angle` comme la direction du point 1 vers le point 2. Pour la
seconde tete de fleche (au point 2), les ailes utilisent correctement
`x2 - LENGTH*cos(angle +/- ANGLE)` - repli vers l'arriere, en direction
du point 1. Mais pour la PREMIERE tete de fleche (au point 1), le code
introduisait une variable `back1 = angle + PI` puis calculait
`x1 + LENGTH*cos(back1 +/- ANGLE)` - ce qui, algebriquement
(cos(theta+PI) = -cos(theta)), equivaut a `x1 - LENGTH*cos(angle +/- ANGLE)` :
exactement l'OPPOSE de ce qu'il fallait. Les ailes se retrouvaient donc
prolongees vers l'exterieur, au-dela de la pointe, au lieu de revenir
vers le corps de la fleche (vers le point 2) - donnant l'impression que
la fleche "regarde" dans le mauvais sens tout en ayant sa pointe (origine)
correctement placee.

CORRECTIF : retire la variable `back1` et utilise directement `angle`
(la meme direction 1->2 que pour la logique de la seconde tete), avec
un signe `+` (au lieu de `-`) puisque le repli s'effectue depuis le
point 1 vers le point 2, dans le sens de `angle`.

Modifie : src/core/control/tools/EditSelection.cpp (1 occurrence)

NECESSITE : apply_alignment_snap_v90.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_BLOCK = """    // Head at (x1, y1), wings pointing back along the shaft (towards (x2, y2)'s opposite direction).
    double back1 = angle + M_PI;
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 - ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 + ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 + ARROW_HEAD_ANGLE));
"""
NEW_BLOCK = """    // Head at (x1, y1), wings pointing back along the shaft (towards (x2, y2)).
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(angle - ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(angle - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(angle + ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(angle + ARROW_HEAD_ANGLE));
"""


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "drawDoubleArrow" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] drawDoubleArrow introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py, puis relancez ce script.")
        sys.exit(1)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_BLOCK)
    if count == 0:
        if text.count(NEW_BLOCK) > 0:
            print("[SKIP] Le patch 11.2 semble deja applique.")
            sys.exit(0)
        print("[ECHEC] Motif introuvable dans EditSelection.cpp.")
        sys.exit(1)
    if count > 1:
        print(f"[ECHEC] Motif trouve {count} fois dans EditSelection.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    EditSelection.cpp: drawDoubleArrow() - premiere tete de fleche corrigee")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
