#!/usr/bin/env python3
"""
Patch 11.1 : CORRECTIF - les guides des assistants "coordinate system"
(patch 8.4) et "circle assist" (patch 8.5) heritaient du style de trait
(pointille/points) de l'outil courant au lieu d'etre toujours en trait
plein.

CAUSE : ShapeToolView::draw() dessine ces deux guides (le repere rose de
croisement de ligne, le repere vert du cercle parfait) sur le MEME
contexte cairo `cr` que la forme principale. `prepareContext(cr)`
applique le motif de tirets de l'outil courant (this->lineStyle) sur
`cr` via cairo_set_dash_from_vector() - et rien ne le reinitialise
avant que les guides ne soient traces a leur tour, puisqu'ils partagent
le meme contexte.

CORRECTIF : ajoute un cairo_set_dash(cr, nullptr, 0, 0) (motif plein)
juste avant le trace de chacun des deux guides. Les epaisseurs de trait
(cairo_set_line_width) ne sont PAS modifiees, comme demande.

Modifie : src/core/view/overlays/ShapeToolView.cpp (2 occurrences)

NECESSITE : apply_alignment_snap_v90.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD1 = """        constexpr double MARKER_HALF_SIZE = 7.5;  // 15pt marker, centered on the guide point
        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink, matching the alignment-snapping system
        cairo_set_line_width(cr, 1.0);
        for (const Point& center: {guide->nearCenter, guide->farCenter}) {
"""
NEW1 = """        constexpr double MARKER_HALF_SIZE = 7.5;  // 15pt marker, centered on the guide point
        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink, matching the alignment-snapping system
        cairo_set_line_width(cr, 1.0);
        // Patch 11.1: this assist's guide must always be a solid line, regardless of the current
        // tool's own line style (e.g. dashed/dotted) - prepareContext() above applies that style to
        // `cr`, and it would otherwise still be active here since guides are drawn on the same
        // context, after the main shape.
        cairo_set_dash(cr, nullptr, 0, 0);
        for (const Point& center: {guide->nearCenter, guide->farCenter}) {
"""
OLD2 = """        cairo_set_line_width(cr, 1.5 / this->toolHandler->getLastZoom());
        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);
"""
NEW2 = """        cairo_set_line_width(cr, 1.5 / this->toolHandler->getLastZoom());
        // Patch 11.1: same reasoning as the line-crossing guide above - always solid, regardless of
        // the current tool's own line style.
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);
"""


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
    cpp = Path("src/core/view/overlays/ShapeToolView.cpp")
    if not cpp.exists():
        print("[ECHEC] ShapeToolView.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "getLineCrossingGuide" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] getLineCrossingGuide introuvable dans ShapeToolView.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py, puis relancez ce script.")
        sys.exit(1)

    ok = True
    ok &= apply_edit(cpp, OLD1, NEW1, "ShapeToolView.cpp: guide rose (coordinate system assist) toujours plein")
    ok &= apply_edit(cpp, OLD2, NEW2, "ShapeToolView.cpp: guide vert (circle assist) toujours plein")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
