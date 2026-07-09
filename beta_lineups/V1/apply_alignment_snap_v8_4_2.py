#!/usr/bin/env python3
"""
Patch 8.4.2 (depend de 8.4) : corrige un bug d'invalidation d'affichage
qui causait les 4 symptomes rapportes (reperes qui restent affiches apres
relachement, mal positionnes, dedoubles a des hauteurs differentes, ou
visibles sans intersection).

Cause racine : la zone de rafraichissement (`rg`) calculee dans
updateShape() ne couvrait que le trace de la ligne elle-meme, jamais la
position des reperes roses - qui peuvent se trouver EN DEHORS de cette
zone tant que le snap n'est pas encore actif (le repere "loin" avant que
la ligne ne l'ait atteint). Resultat : les pixels de l'ancien repere
n'etaient jamais effaces, laissant des reperes fantomes a l'ecran.

Correctif : la zone de rafraichissement inclut desormais aussi la position
des deux reperes (avec leur demi-taille) des que lineCrossingGuide est
actif, avant d'etre a la fois utilisee pour le rafraichissement ET
memorisee pour le prochain calcul (donc l'ancien repere est aussi
correctement efface au prochain mouvement, ou au relachement).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v8_4.py

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
    cpp = Path("src/core/control/tools/BaseShapeHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] BaseShapeHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "applyLineCrossingSnap" not in content:
        print("[ECHEC] applyLineCrossingSnap introuvable dans BaseShapeHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_4.py, puis relancez ce script.")
        sys.exit(1)
    if "LINE_CROSS_MARKER_HALF_SIZE = 7.5;\n\nBaseShapeHandler::BaseShapeHandler" in content:
        print("[SKIP] Le patch 8.4.2 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. deplacer les constantes avant le constructeur ============
    ok &= apply_edit(
        cpp,
        old='/**\n'
            ' * Below this length (in document points), a segment isn\'t considered eligible for the "line\n'
            ' * crossing" snap assist - neither the line being drawn nor the line/arrow it might cross.\n'
            ' */\n'
            'constexpr double LINE_CROSS_MIN_LENGTH = 50.0;\n\n'
            '/// How close to perfectly horizontal/vertical (in document points, on the perpendicular coordinate)\n'
            '/// a segment must be to count as axis-aligned for the "line crossing" snap assist.\n'
            'constexpr double LINE_CROSS_AXIS_TOLERANCE = 3.0;\n\n'
            '/// Half the length, in document points, of each 15pt marker drawn by the "line crossing" snap assist.\n'
            'constexpr double LINE_CROSS_MARKER_HALF_SIZE = 7.5;\n\n'
            '/// Same tolerance (in screen pixels, converted via zoom) as the rest of the alignment-snapping\n'
            '/// system, so this feels consistent with every other kind of snap in the app.\n'
            'constexpr double LINE_CROSS_SNAP_TOLERANCE_PX = 6.0;\n\n'
            '/**\n'
            ' * If `el` is a Stroke with at least 2 points, returns its two "shaft" endpoints: for a plain\n'
            ' * straight line, its only two points; for an arrow (single or double-ended - see',
        new='/**\n'
            ' * If `el` is a Stroke with at least 2 points, returns its two "shaft" endpoints: for a plain\n'
            ' * straight line, its only two points; for an arrow (single or double-ended - see',
        label="BaseShapeHandler.cpp: retrait des constantes de leur ancien emplacement",
    )

    ok &= apply_edit(
        cpp,
        old='BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):',
        new='/**\n'
            ' * Below this length (in document points), a segment isn\'t considered eligible for the "line\n'
            ' * crossing" snap assist - neither the line being drawn nor the line/arrow it might cross.\n'
            ' */\n'
            'constexpr double LINE_CROSS_MIN_LENGTH = 50.0;\n\n'
            '/// How close to perfectly horizontal/vertical (in document points, on the perpendicular coordinate)\n'
            '/// a segment must be to count as axis-aligned for the "line crossing" snap assist.\n'
            'constexpr double LINE_CROSS_AXIS_TOLERANCE = 3.0;\n\n'
            '/// Half the length, in document points, of each 15pt marker drawn by the "line crossing" snap assist.\n'
            'constexpr double LINE_CROSS_MARKER_HALF_SIZE = 7.5;\n\n'
            '/// Same tolerance (in screen pixels, converted via zoom) as the rest of the alignment-snapping\n'
            '/// system, so this feels consistent with every other kind of snap in the app.\n'
            'constexpr double LINE_CROSS_SNAP_TOLERANCE_PX = 6.0;\n\n'
            'BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):',
        label="BaseShapeHandler.cpp: constantes deplacees avant le constructeur",
    )

    # ============ 2. etendre la zone de rafraichissement dans updateShape() ============
    ok &= apply_edit(
        cpp,
        old='void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {\n'
            '    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);\n'
            '    std::swap(shape, this->shape);\n'
            '    Range repaintRange = rg.unite(lastSnappingRange);\n'
            '    lastSnappingRange = rg;\n'
            '    repaintRange.addPadding(0.5 * this->stroke->getWidth());\n'
            '    viewPool->dispatch(xoj::view::ShapeToolView::FLAG_DIRTY_REGION, repaintRange);\n'
            '}',
        new='void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {\n'
            '    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);\n'
            '    std::swap(shape, this->shape);\n'
            '    // The line-crossing snap assist\'s markers (see applyLineCrossingSnap()) can sit outside the\n'
            '    // shape\'s own bounding box - most notably the "far" marker, before the line has actually reached\n'
            '    // it. Without this, the dirty-region tracking below would never invalidate their pixels,\n'
            '    // leaving stale markers on screen from a previous frame (wrong position, or shown when no\n'
            '    // longer relevant).\n'
            '    if (this->lineCrossingGuide) {\n'
            '        for (const Point& center: {this->lineCrossingGuide->nearCenter, this->lineCrossingGuide->farCenter}) {\n'
            '            rg.addPoint(center.x - LINE_CROSS_MARKER_HALF_SIZE, center.y - LINE_CROSS_MARKER_HALF_SIZE);\n'
            '            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);\n'
            '        }\n'
            '    }\n'
            '    Range repaintRange = rg.unite(lastSnappingRange);\n'
            '    lastSnappingRange = rg;\n'
            '    repaintRange.addPadding(0.5 * this->stroke->getWidth());\n'
            '    viewPool->dispatch(xoj::view::ShapeToolView::FLAG_DIRTY_REGION, repaintRange);\n'
            '}',
        label="BaseShapeHandler.cpp: updateShape() invalide aussi la zone des reperes",
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
