#!/usr/bin/env python3
"""
Patch 8.5 (depend de 8.4, 8.4.2, 8.4.3, 8.4.4) : point d'ancrage pour
egaliser largeur et hauteur pendant le trace d'une ellipse (cercle
parfait), avec deux guidelines vertes le long des bords du carre englobant
les plus proches du curseur. Le curseur peut continuer a naviguer
librement sur la diagonale tant que le snap est actif ; si les dimensions
redeviennent trop differentes, le snap et les guidelines disparaissent.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v8_4.py
  3) apply_alignment_snap_v8_4_2.py
  4) apply_alignment_snap_v8_4_3.py
  5) apply_alignment_snap_v8_4_4.py

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
    cpp = Path("src/core/control/tools/BaseShapeHandler.cpp")
    ellipse = Path("src/core/control/tools/EllipseHandler.cpp")
    view = Path("src/core/view/overlays/ShapeToolView.cpp")
    for p in (h, cpp, ellipse, view):
        if not p.exists():
            print(f"[ECHEC] {p} introuvable. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "applyLineCrossingSnap" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] applyLineCrossingSnap introuvable dans BaseShapeHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_4.py (+ v8_4_2/3/4.py), puis relancez ce script.")
        sys.exit(1)
    if "DiagonalSnapGuide" in h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 8.5 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ BaseShapeHandler.h ============
    ok &= apply_edit(
        h,
        old='    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }',
        new='    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }\n\n'
            '    /**\n'
            '     * Two green guide lines shown when a shape\'s bounding box has been snapped to a square (equal\n'
            '     * width and height) - see EllipseHandler::createShape(). `corner1` and `corner2` are the two\n'
            '     * opposite corners of the (now square) bounding box; the two lines are drawn along the edges\n'
            '     * meeting at `corner2` (the one nearer the cursor), from `corner2` to each adjacent corner.\n'
            '     */\n'
            '    struct DiagonalSnapGuide {\n'
            '        Point corner1;\n'
            '        Point corner2;\n'
            '    };\n'
            '    const std::optional<DiagonalSnapGuide>& getDiagonalSnapGuide() const { return diagonalSnapGuide; }',
        label="BaseShapeHandler.h: struct DiagonalSnapGuide + getter",
    )

    ok &= apply_edit(
        h,
        old='    std::optional<LineCrossingGuide> lineCrossingGuide;\n\n'
            '    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;',
        new='    std::optional<LineCrossingGuide> lineCrossingGuide;\n'
            '    std::optional<DiagonalSnapGuide> diagonalSnapGuide;\n\n'
            '    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;',
        label="BaseShapeHandler.h: membre diagonalSnapGuide",
    )

    # ============ BaseShapeHandler.cpp ============
    ok &= apply_edit(
        cpp,
        old='void BaseShapeHandler::cancelStroke() {\n'
            '    this->shape.clear();\n'
            '    this->lineCrossingGuide.reset();\n',
        new='void BaseShapeHandler::cancelStroke() {\n'
            '    this->shape.clear();\n'
            '    this->lineCrossingGuide.reset();\n'
            '    this->diagonalSnapGuide.reset();\n',
        label="BaseShapeHandler.cpp: nettoyage dans cancelStroke()",
    )

    ok &= apply_edit(
        cpp,
        old='    stroke->setPointVector(this->shape, &lastSnappingRange);\n'
            '    stroke->setArrowKind(this->getArrowKind());\n'
            '    this->lineCrossingGuide.reset();\n',
        new='    stroke->setPointVector(this->shape, &lastSnappingRange);\n'
            '    stroke->setArrowKind(this->getArrowKind());\n'
            '    this->lineCrossingGuide.reset();\n'
            '    this->diagonalSnapGuide.reset();\n',
        label="BaseShapeHandler.cpp: nettoyage dans onButtonReleaseEvent()",
    )

    ok &= apply_edit(
        cpp,
        old='    if (this->lineCrossingGuide) {\n'
            '        for (const Point& center: {this->lineCrossingGuide->nearCenter, this->lineCrossingGuide->farCenter}) {\n'
            '            rg.addPoint(center.x - LINE_CROSS_MARKER_HALF_SIZE, center.y - LINE_CROSS_MARKER_HALF_SIZE);\n'
            '            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);\n'
            '        }\n'
            '    }\n'
            '    Range repaintRange = rg.unite(lastSnappingRange);',
        new='    if (this->lineCrossingGuide) {\n'
            '        for (const Point& center: {this->lineCrossingGuide->nearCenter, this->lineCrossingGuide->farCenter}) {\n'
            '            rg.addPoint(center.x - LINE_CROSS_MARKER_HALF_SIZE, center.y - LINE_CROSS_MARKER_HALF_SIZE);\n'
            '            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);\n'
            '        }\n'
            '    }\n'
            '    if (this->diagonalSnapGuide) {\n'
            '        // The two green lines run along the square\'s own edges, already covered by the shape\'s own\n'
            '        // bounding box in the vast majority of cases - but unite them in anyway for safety (e.g. an\n'
            '        // ellipse\'s Range is computed from its own points, which is a good approximation of the\n'
            '        // bounding box but not necessarily pixel-exact at the corners).\n'
            '        rg.addPoint(this->diagonalSnapGuide->corner1.x, this->diagonalSnapGuide->corner1.y);\n'
            '        rg.addPoint(this->diagonalSnapGuide->corner2.x, this->diagonalSnapGuide->corner2.y);\n'
            '    }\n'
            '    Range repaintRange = rg.unite(lastSnappingRange);',
        label="BaseShapeHandler.cpp: updateShape() invalide aussi la zone du carre",
    )

    # ============ EllipseHandler.cpp ============
    ok &= apply_edit(
        ellipse,
        old='    if (this->modShift) {\n'
            '        // make circle\n'
            '        width = (this->modControl) ? std::hypot(width, height) :\n'
            '                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);\n'
            '        height = std::copysign(width, height);\n'
            '    }',
        new='    if (this->modShift) {\n'
            '        // make circle\n'
            '        width = (this->modControl) ? std::hypot(width, height) :\n'
            '                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);\n'
            '        height = std::copysign(width, height);\n'
            '    } else {\n'
            '        // Diagonal snap assist: if width and height are already close, snap them to be exactly\n'
            '        // equal (a perfect circle\'s bounding box becomes a square), and show two green guide lines\n'
            '        // along the edges nearest the cursor. The cursor can keep moving freely along the diagonal\n'
            '        // while snapped, since both dimensions grow/shrink together; if they drift too far apart\n'
            '        // again, the snap (and the guide) releases.\n'
            '        this->diagonalSnapGuide.reset();\n'
            '        constexpr double DIAGONAL_SNAP_TOLERANCE_PX = 6.0;\n'
            '        double tolerance = DIAGONAL_SNAP_TOLERANCE_PX / this->lastZoom;\n'
            '        if (std::abs(std::abs(width) - std::abs(height)) < tolerance) {\n'
            '            double snappedSize = std::max(std::abs(width), std::abs(height));\n'
            '            width = std::copysign(snappedSize, width);\n'
            '            height = std::copysign(snappedSize, height);\n'
            '            this->diagonalSnapGuide =\n'
            '                    DiagonalSnapGuide{this->startPoint, Point(this->startPoint.x + width, this->startPoint.y + height)};\n'
            '        }\n'
            '    }',
        label="EllipseHandler.cpp: assistant de snap diagonal",
    )

    # ============ ShapeToolView.cpp ============
    ok &= apply_edit(
        view,
        old='            cairo_stroke(cr);\n'
            '        }\n'
            '    }\n'
            '}',
        new='            cairo_stroke(cr);\n'
            '        }\n'
            '    }\n\n'
            '    // Diagonal (equal width/height) snap assist for ellipses (see EllipseHandler::createShape()):\n'
            '    // two green lines along the two edges of the (now square) bounding box that meet at the corner\n'
            '    // nearest the cursor.\n'
            '    if (auto guide = this->toolHandler->getDiagonalSnapGuide()) {\n'
            '        cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green, matching the alignment-snapping system\n'
            '        cairo_set_line_width(cr, 1.0);\n'
            '        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);\n'
            '        cairo_line_to(cr, guide->corner2.x, guide->corner2.y);\n'
            '        cairo_line_to(cr, guide->corner1.x, guide->corner2.y);\n'
            '        cairo_stroke(cr);\n'
            '    }\n'
            '}',
        label="ShapeToolView.cpp: rendu des deux lignes vertes",
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
