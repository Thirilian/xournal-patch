#!/usr/bin/env python3
"""
Patch 8.6.4.2 (depend de 8.6.4) : corrige une erreur de compilation
reelle du patch 8.6.4. La fonction applyLineHalfDoubleOnRelease() avait
ete inseree AVANT la definition de THIN_AXIS_THRESHOLD, rangesOverlap et
BLUE_GRID_LENGTH_EPS (toutes definies plus loin dans le fichier), ce qui
empeche la compilation ("was not declared in this scope").

Ce script deplace le corps complet de la fonction juste apres
computeBlueGridY() (ou toutes ses dependances sont deja definies), et
laisse une declaration anticipee (forward declaration) a son ancien
emplacement pour que EditSelection::mouseUp() puisse toujours l'appeler.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  5) apply_alignment_snap_v8_6_4.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    text = cpp.read_text(encoding="utf-8")
    if "applyLineHalfDoubleOnRelease" not in text:
        print("[ECHEC] applyLineHalfDoubleOnRelease introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_4.py, puis relancez ce script.")
        sys.exit(1)
    if "forward-declared here so" in text:
        print("[SKIP] Le patch 8.6.4.2 semble deja applique.")
        sys.exit(0)

    start_marker = '/**\n * "Half/double on release" (patch 8.6.4):'
    end_marker_after = '\nvoid EditSelection::mouseUp() {'
    new_location_anchor = ('static auto findAlignmentY(double y, double height, double xLeft, double xRight, '
                            'double tolerance, Layer* layer,')

    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker_after)
    if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
        print("[ECHEC] Ancres de la fonction a deplacer introuvables ou dans le mauvais ordre.")
        sys.exit(1)
    if text.count(new_location_anchor) != 1:
        print(f"[ECHEC] Ancre findAlignmentY trouvee {text.count(new_location_anchor)} fois (attendu 1).")
        sys.exit(1)

    full_block = text[start_idx:end_idx]

    forward_decl = (
        "// \"Half/double on release\" (patch 8.6.4) - defined later in this file (after its dependencies\n"
        "// like THIN_AXIS_THRESHOLD/rangesOverlap/BLUE_GRID_LENGTH_EPS), forward-declared here so\n"
        "// EditSelection::mouseUp() below can call it.\n"
        "static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
        "                                          const Element* bigLine, bool isXAxis, int zone);\n"
    )

    text = text[:start_idx] + forward_decl + text[end_idx:]

    idx2 = text.find(new_location_anchor)
    text = text[:idx2] + full_block.lstrip("\n") + "\n\n" + text[idx2:]

    cpp.write_text(text, encoding="utf-8")
    print("[OK]    EditSelection.cpp: applyLineHalfDoubleOnRelease() deplacee apres ses dependances,")
    print("        declaration anticipee laissee a son ancien emplacement.")
    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
