#!/usr/bin/env python3
"""
Patch 8.4 (independant du systeme d'ancrage EditSelection - un fichier
different) : assistant de snap "croisement de ligne" pendant le trace en
direct d'une ligne ou d'une fleche.

Si la ligne/fleche en cours de trace (verticale ou horizontale, >50pt) a
une origine (point fixe) qui croise une autre ligne/fleche deja tracee,
perpendiculaire et >50pt, deux reperes roses de 15pt s'affichent : un au
point d'origine, un a la distance exacte de la ligne existante. Si la
ligne en cours atteint ce second repere (a la meme tolerance que le reste
du systeme d'ancrage, 6px), elle s'accroche a cette longueur exacte - et y
reste tant que le curseur ne depasse pas le repere de plus que cette
tolerance. Fonctionne dans les 4 sens (haut/bas/gauche/droite), et traite
les fleches simples et doubles exactement comme de simples lignes, cote
trace ET cote cible (grace a ArrowKind, prealable requis).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py (fournit ArrowKind/getArrowKind())

Independant de tous les patches de la serie apply_alignment_snap_v*.py
(ceux-ci touchent EditSelection.cpp, ce patch touche BaseShapeHandler et
consorts - fichiers totalement differents).

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
    ruler = Path("src/core/control/tools/RulerHandler.cpp")
    arrow = Path("src/core/control/tools/ArrowHandler.cpp")
    view = Path("src/core/view/overlays/ShapeToolView.cpp")
    for p in (h, cpp, ruler, arrow, view):
        if not p.exists():
            print(f"[ECHEC] {p} introuvable. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "getArrowKind" not in h.read_text(encoding="utf-8"):
        print("[ECHEC] getArrowKind introuvable dans BaseShapeHandler.h.")
        print("        Appliquez d'abord apply_arrow_resize_fix_v2.py, puis relancez ce script.")
        sys.exit(1)
    if "applyLineCrossingSnap" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 8.4 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ BaseShapeHandler.h ============
    ok &= apply_edit(
        h,
        old='#include <memory>  // for shared_ptr\n'
            '#include <utility>  // for pair\n'
            '#include <vector>   // for vector',
        new='#include <memory>  // for shared_ptr\n'
            '#include <optional> // for optional\n'
            '#include <utility>  // for pair\n'
            '#include <vector>   // for vector',
        label="BaseShapeHandler.h: include <optional>",
    )

    ok &= apply_edit(
        h,
        old='    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }',
        new='    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }\n\n'
            '    /**\n'
            '     * Two 15pt markers, drawn perpendicular to the line/arrow currently being drawn, illustrating a\n'
            '     * matching length found on another line/arrow already on the page - see applyLineCrossingSnap().\n'
            '     * `nearCenter` sits at the fixed origin point of the line being drawn; `farCenter` sits at the\n'
            '     * target distance away, in the direction being drawn. `perpendicularIsHorizontal` is true when\n'
            '     * the line being drawn is vertical (so the markers themselves are drawn as short horizontal\n'
            '     * segments), false when it is horizontal (markers drawn as short vertical segments).\n'
            '     */\n'
            '    struct LineCrossingGuide {\n'
            '        Point nearCenter;\n'
            '        Point farCenter;\n'
            '        bool perpendicularIsHorizontal;\n'
            '    };\n'
            '    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }',
        label="BaseShapeHandler.h: getLineCrossingGuide() + struct",
    )

    ok &= apply_edit(
        h,
        old='    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);',
        new='    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);\n\n'
            '    /**\n'
            '     * If the segment from `this->startPoint` to `rawEnd` is axis-aligned (horizontal or vertical,\n'
            '     * within a small tolerance) and longer than 50pt, and another sufficiently long, perpendicular\n'
            '     * line/arrow already on the page crosses its path, updates `lineCrossingGuide` with two 15pt\n'
            '     * markers illustrating that other line\'s length, and returns `rawEnd` snapped to match that exact\n'
            '     * length if it is already close enough (same tolerance as the rest of the alignment-snapping\n'
            '     * system). Otherwise clears `lineCrossingGuide` and returns `rawEnd` unchanged. Meant to be called\n'
            '     * by a line-like shape\'s own createShape() (RulerHandler, ArrowHandler) right after computing its\n'
            '     * own raw endpoint - not used by shapes like Rectangle or Ellipse. A Stroke with an ArrowKind\n'
            '     * (single or double) is treated purely by its own shaft (first/last point), ignoring any\n'
            '     * arrowhead "wing" points, on both ends of the comparison - a fresh arrow being drawn, and an\n'
            '     * existing arrow being crossed.\n'
            '     */\n'
            '    Point applyLineCrossingSnap(Point rawEnd);',
        label="BaseShapeHandler.h: declaration applyLineCrossingSnap()",
    )

    ok &= apply_edit(
        h,
        old='    Point startPoint;       // May be snapped to grid\n\n'
            '    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;\n'
            '};',
        new='    Point startPoint;       // May be snapped to grid\n\n'
            '    /// Last zoom level seen in onMotionNotifyEvent() - createShape() has no zoom parameter of its\n'
            '    /// own, but applyLineCrossingSnap() needs one to convert its pixel-based tolerance.\n'
            '    double lastZoom = 1.0;\n\n'
            '    std::optional<LineCrossingGuide> lineCrossingGuide;\n\n'
            '    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;\n'
            '};',
        label="BaseShapeHandler.h: membres lastZoom / lineCrossingGuide",
    )

    # ============ BaseShapeHandler.cpp ============
    ok &= apply_edit(
        cpp,
        old='#include <cmath>   // for pow, NAN',
        new='#include <algorithm>  // for min, max\n'
            '#include <cmath>   // for pow, NAN',
        label="BaseShapeHandler.cpp: include <algorithm>",
    )

    ok &= apply_edit(
        cpp,
        old='    this->currPoint = newPoint;\n\n'
            '    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());',
        new='    this->currPoint = newPoint;\n'
            '    this->lastZoom = zoom;\n\n'
            '    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());',
        label="BaseShapeHandler.cpp: memorisation du zoom",
    )

    ok &= apply_edit(
        cpp,
        old='void BaseShapeHandler::cancelStroke() {\n'
            '    this->shape.clear();\n'
            '    Range repaintRange = this->lastSnappingRange;',
        new='void BaseShapeHandler::cancelStroke() {\n'
            '    this->shape.clear();\n'
            '    this->lineCrossingGuide.reset();\n'
            '    Range repaintRange = this->lastSnappingRange;',
        label="BaseShapeHandler.cpp: nettoyage du guide dans cancelStroke()",
    )

    ok &= apply_edit(
        cpp,
        old='    stroke->setPointVector(this->shape, &lastSnappingRange);\n'
            '    stroke->setArrowKind(this->getArrowKind());',
        new='    stroke->setPointVector(this->shape, &lastSnappingRange);\n'
            '    stroke->setArrowKind(this->getArrowKind());\n'
            '    this->lineCrossingGuide.reset();',
        label="BaseShapeHandler.cpp: nettoyage du guide dans onButtonReleaseEvent()",
    )

    ok &= apply_edit(
        cpp,
        old='auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }',
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
            '/**\n'
            ' * If `el` is a Stroke with at least 2 points, returns its two "shaft" endpoints: for a plain\n'
            ' * straight line, its only two points; for an arrow (single or double-ended - see\n'
            ' * ArrowHandler::createShape()), its first and last point specifically, which are always the true\n'
            ' * shaft start and tip regardless of however many arrowhead "wing" points lie in between. Returns\n'
            ' * nullopt for anything else (not a Stroke, or fewer than 2 points).\n'
            ' */\n'
            'static auto getLineShaftEndpoints(const Element* el) -> std::optional<std::pair<Point, Point>> {\n'
            '    const auto* stroke = dynamic_cast<const Stroke*>(el);\n'
            '    if (stroke == nullptr || stroke->getPointCount() < 2) {\n'
            '        return std::nullopt;\n'
            '    }\n'
            '    const Point* pts = stroke->getPoints();\n'
            '    return std::make_pair(pts[0], pts[stroke->getPointCount() - 1]);\n'
            '}\n\n'
            'auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {\n'
            '    this->lineCrossingGuide.reset();\n\n'
            '    double dx = rawEnd.x - this->startPoint.x;\n'
            '    double dy = rawEnd.y - this->startPoint.y;\n'
            '    bool drawingVertical = std::abs(dx) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dy) > LINE_CROSS_MIN_LENGTH;\n'
            '    bool drawingHorizontal = std::abs(dy) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dx) > LINE_CROSS_MIN_LENGTH;\n'
            '    if (!drawingVertical && !drawingHorizontal) {\n'
            '        return rawEnd;\n'
            '    }\n\n'
            '    Layer* layer = this->page->getSelectedLayer();\n'
            '    if (layer == nullptr) {\n'
            '        return rawEnd;\n'
            '    }\n\n'
            '    double currentLength = drawingVertical ? std::abs(dy) : std::abs(dx);\n'
            '    double tolerance = LINE_CROSS_SNAP_TOLERANCE_PX / this->lastZoom;\n\n'
            '    bool found = false;\n'
            '    double bestTargetLength = 0;\n'
            '    double bestDistFromCurrent = 0;\n\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        auto shaft = getLineShaftEndpoints(elPtr.get());\n'
            '        if (!shaft) {\n'
            '            continue;\n'
            '        }\n'
            '        double odx = shaft->second.x - shaft->first.x;\n'
            '        double ody = shaft->second.y - shaft->first.y;\n'
            '        double targetLength = std::hypot(odx, ody);\n'
            '        if (targetLength <= LINE_CROSS_MIN_LENGTH) {\n'
            '            continue;\n'
            '        }\n'
            '        bool targetIsVertical = std::abs(odx) <= LINE_CROSS_AXIS_TOLERANCE;\n'
            '        bool targetIsHorizontal = std::abs(ody) <= LINE_CROSS_AXIS_TOLERANCE;\n\n'
            '        if (drawingVertical) {\n'
            '            if (!targetIsHorizontal) {\n'
            '                continue;\n'
            '            }\n'
            '            double minX = std::min(shaft->first.x, shaft->second.x);\n'
            '            double maxX = std::max(shaft->first.x, shaft->second.x);\n'
            '            if (this->startPoint.x < minX || this->startPoint.x > maxX) {\n'
            '                continue;\n'
            '            }\n'
            '        } else {\n'
            '            if (!targetIsVertical) {\n'
            '                continue;\n'
            '            }\n'
            '            double minY = std::min(shaft->first.y, shaft->second.y);\n'
            '            double maxY = std::max(shaft->first.y, shaft->second.y);\n'
            '            if (this->startPoint.y < minY || this->startPoint.y > maxY) {\n'
            '                continue;\n'
            '            }\n'
            '        }\n\n'
            '        double distFromCurrent = std::abs(currentLength - targetLength);\n'
            '        if (!found || distFromCurrent < bestDistFromCurrent) {\n'
            '            found = true;\n'
            '            bestDistFromCurrent = distFromCurrent;\n'
            '            bestTargetLength = targetLength;\n'
            '        }\n'
            '    }\n\n'
            '    if (!found || currentLength > bestTargetLength + tolerance) {\n'
            '        return rawEnd;\n'
            '    }\n\n'
            '    double sign = drawingVertical ? (dy >= 0 ? 1.0 : -1.0) : (dx >= 0 ? 1.0 : -1.0);\n'
            '    Point farCenter = drawingVertical ? Point(this->startPoint.x, this->startPoint.y + sign * bestTargetLength)\n'
            '                                       : Point(this->startPoint.x + sign * bestTargetLength, this->startPoint.y);\n'
            '    this->lineCrossingGuide = LineCrossingGuide{this->startPoint, farCenter, drawingVertical};\n\n'
            '    if (bestDistFromCurrent < tolerance) {\n'
            '        return drawingVertical ? Point(rawEnd.x, this->startPoint.y + sign * bestTargetLength)\n'
            '                                : Point(this->startPoint.x + sign * bestTargetLength, rawEnd.y);\n'
            '    }\n'
            '    return rawEnd;\n'
            '}\n\n'
            'auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }',
        label="BaseShapeHandler.cpp: implementation applyLineCrossingSnap()",
    )

    # ============ RulerHandler.cpp ============
    ok &= apply_edit(
        ruler,
        old='    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    Range rg(this->startPoint.x, this->startPoint.y);',
        new='    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    secondPoint = applyLineCrossingSnap(secondPoint);\n'
            '    Range rg(this->startPoint.x, this->startPoint.y);',
        label="RulerHandler.cpp: appel applyLineCrossingSnap()",
    )

    # ============ ArrowHandler.cpp ============
    ok &= apply_edit(
        arrow,
        old='    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    const double thickness = control->getToolHandler()->getThickness();',
        new='    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    c = applyLineCrossingSnap(c);\n'
            '    const double thickness = control->getToolHandler()->getThickness();',
        label="ArrowHandler.cpp: appel applyLineCrossingSnap()",
    )

    # ============ ShapeToolView.cpp ============
    ok &= apply_edit(
        view,
        old='#include "control/tools/BaseShapeHandler.h"\n'
            '#include "util/raii/CairoWrappers.h"',
        new='#include "control/tools/BaseShapeHandler.h"\n'
            '#include "model/Point.h"\n'
            '#include "util/raii/CairoWrappers.h"',
        label="ShapeToolView.cpp: include model/Point.h",
    )

    ok &= apply_edit(
        view,
        old='    StrokeViewHelper::pathToCairo(effCr, pts);\n\n'
            '    this->commitDrawing(cr);\n'
            '}',
        new='    StrokeViewHelper::pathToCairo(effCr, pts);\n\n'
            '    this->commitDrawing(cr);\n\n'
            '    // "Line crossing" snap assist (see BaseShapeHandler::applyLineCrossingSnap()): two short pink\n'
            '    // markers, perpendicular to the line/arrow being drawn, illustrating a matching length found on\n'
            '    // another line/arrow already on the page. Drawn in document-space coordinates, same as `pts`\n'
            '    // above - no manual zoom scaling needed here.\n'
            '    if (auto guide = this->toolHandler->getLineCrossingGuide()) {\n'
            '        constexpr double MARKER_HALF_SIZE = 7.5;  // 15pt marker, centered on the guide point\n'
            '        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink, matching the alignment-snapping system\n'
            '        cairo_set_line_width(cr, 1.0);\n'
            '        for (const Point& center: {guide->nearCenter, guide->farCenter}) {\n'
            '            if (guide->perpendicularIsHorizontal) {\n'
            '                cairo_move_to(cr, center.x - MARKER_HALF_SIZE, center.y);\n'
            '                cairo_line_to(cr, center.x + MARKER_HALF_SIZE, center.y);\n'
            '            } else {\n'
            '                cairo_move_to(cr, center.x, center.y - MARKER_HALF_SIZE);\n'
            '                cairo_line_to(cr, center.x, center.y + MARKER_HALF_SIZE);\n'
            '            }\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '    }\n'
            '}',
        label="ShapeToolView.cpp: rendu des reperes roses",
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
