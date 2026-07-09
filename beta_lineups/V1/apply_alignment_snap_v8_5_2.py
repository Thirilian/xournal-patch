#!/usr/bin/env python3
"""
Patch 8.5.2 (depend de 8.5) : corrige l'epaisseur des deux guidelines
vertes du patch 8.5 (assistant de snap diagonal ellipse) pour qu'elle soit
constante a 1.5 pixel ecran, quel que soit le zoom - identique aux
guidelines d'EditSelection.cpp. Ne touche PAS aux reperes roses du patch
8.4 (assistant de croisement de ligne), qui restent inchanges.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v8_4.py (+ v8_4_2/3/4.py)
  3) apply_alignment_snap_v8_5.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


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
    h = Path("src/core/control/tools/BaseShapeHandler.h")
    view = Path("src/core/view/overlays/ShapeToolView.cpp")
    for p in (h, view):
        if not p.exists():
            print(f"[ECHEC] {p} introuvable. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "DiagonalSnapGuide" not in h.read_text(encoding="utf-8"):
        print("[ECHEC] DiagonalSnapGuide introuvable dans BaseShapeHandler.h.")
        print("        Appliquez d'abord apply_alignment_snap_v8_5.py, puis relancez ce script.")
        sys.exit(1)
    if "getLastZoom" in h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 8.5.2 semble deja applique.")
        sys.exit(0)

    ok = True

    ok &= apply_edit(
        h,
        old='    const std::vector<Point>& getShape() const;',
        new='    const std::vector<Point>& getShape() const;\n\n'
            '    /**\n'
            '     * Last zoom level seen in onMotionNotifyEvent(), exposed so views (e.g. ShapeToolView) can draw\n'
            '     * overlay guides at a constant on-screen thickness, matching EditSelection\'s alignment guides,\n'
            '     * regardless of the actual zoom level - see lastZoom\'s own doc comment below for why it exists.\n'
            '     */\n'
            '    double getLastZoom() const { return lastZoom; }',
        label="BaseShapeHandler.h: getter getLastZoom()",
    )

    ok &= apply_edit(
        view,
        old='    if (auto guide = this->toolHandler->getDiagonalSnapGuide()) {\n'
            '        cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green, matching the alignment-snapping system\n'
            '        cairo_set_line_width(cr, 1.0);\n'
            '        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);',
        new='    if (auto guide = this->toolHandler->getDiagonalSnapGuide()) {\n'
            '        cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green, matching the alignment-snapping system\n'
            '        // Drawn in document-space coordinates (like everything else here), so the line width must be\n'
            '        // divided by zoom to render at a constant 1.5 screen pixels - matching the thickness of\n'
            '        // EditSelection\'s own alignment guides, which are drawn in already-zoomed pixel coordinates.\n'
            '        cairo_set_line_width(cr, 1.5 / this->toolHandler->getLastZoom());\n'
            '        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);',
        label="ShapeToolView.cpp: epaisseur constante pour les guidelines du 8.5",
    )

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
