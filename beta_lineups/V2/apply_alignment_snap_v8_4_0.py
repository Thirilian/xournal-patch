#!/usr/bin/env python3
"""
Patch 8.4.0 : fusion des patchs 8.4, 8.4.2, 8.4.3, 8.4.4 (assistant de
croisement de ligne pendant le trace) en un seul, applicable PAR-DESSUS
d'autres patchs - modifications CIBLEES par ancres de texte (pas de
reecriture de fichier entier), exactement comme le reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_4.py
    apply_alignment_snap_v8_4_2.py
    apply_alignment_snap_v8_4_3.py
    apply_alignment_snap_v8_4_4.py
(dans cet ordre, SANS le patch 8.4.5 - non demande dans cette fusion),
sans jamais reecrire un fichier entier - seules les zones reellement
modifiees par cette chaine sont touchees, avec assez de contexte autour
de chacune pour garantir un ancrage unique (verifie lors de la creation
de ce patch, sur une base v7.10 + 8.1.0 + 8.2.0 + 8.3.0).

Fichiers concernes :
  - src/core/control/tools/ArrowHandler.cpp\n  - src/core/control/tools/BaseShapeHandler.cpp\n  - src/core/control/tools/BaseShapeHandler.h\n  - src/core/control/tools/RulerHandler.cpp\n  - src/core/view/overlays/ShapeToolView.cpp\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py), OU v7_10.py

Independant des autres patches 8.X (ne touche pas EditSelection.cpp).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/ArrowHandler.cpp", [
        ("""auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    const double thickness = control->getToolHandler()->getThickness();
    const ArrowKind kind = this->doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE;
""", """auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    c = applyLineCrossingSnap(c);
    const double thickness = control->getToolHandler()->getThickness();
    const ArrowKind kind = this->doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE;
"""),
    ]),
    ("src/core/control/tools/BaseShapeHandler.cpp", [
        ("""#include \"BaseShapeHandler.h\"

#include <cmath>   // for pow, NAN
#include <memory>  // for make_unique, __share...
""", """#include \"BaseShapeHandler.h\"

#include <algorithm>  // for min, max
#include <cmath>   // for pow, NAN
#include <memory>  // for make_unique, __share...
"""),
        ("""#include \"view/overlays/ShapeToolView.h\"           // for ShapeToolView


BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):
        InputHandler(control, page),
        flipShift(flipShift),""", """#include \"view/overlays/ShapeToolView.h\"           // for ShapeToolView


/**
 * Below this length (in document points), a segment isn't considered eligible for the \"line
 * crossing\" snap assist - neither the line being drawn nor the line/arrow it might cross.
 */
constexpr double LINE_CROSS_MIN_LENGTH = 50.0;

/// How close to perfectly horizontal/vertical (in document points, on the perpendicular coordinate)
/// a segment must be to count as axis-aligned for the \"line crossing\" snap assist.
constexpr double LINE_CROSS_AXIS_TOLERANCE = 3.0;

/// Half the length, in document points, of each 15pt marker drawn by the \"line crossing\" snap assist.
constexpr double LINE_CROSS_MARKER_HALF_SIZE = 7.5;

/// Same tolerance (in screen pixels, converted via zoom) as the rest of the alignment-snapping
/// system, so this feels consistent with every other kind of snap in the app.
constexpr double LINE_CROSS_SNAP_TOLERANCE_PX = 6.0;

BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):
        InputHandler(control, page),
        flipShift(flipShift),"""),
        ("""void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {
    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);
    std::swap(shape, this->shape);
    Range repaintRange = rg.unite(lastSnappingRange);
    lastSnappingRange = rg;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());""", """void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {
    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);
    std::swap(shape, this->shape);
    // The line-crossing snap assist's markers (see applyLineCrossingSnap()) can sit outside the
    // shape's own bounding box - most notably the \"far\" marker, before the line has actually reached
    // it. Without this, the dirty-region tracking below would never invalidate their pixels,
    // leaving stale markers on screen from a previous frame (wrong position, or shown when no
    // longer relevant).
    if (this->lineCrossingGuide) {
        for (const Point& center: {this->lineCrossingGuide->nearCenter, this->lineCrossingGuide->farCenter}) {
            rg.addPoint(center.x - LINE_CROSS_MARKER_HALF_SIZE, center.y - LINE_CROSS_MARKER_HALF_SIZE);
            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);
        }
    }
    Range repaintRange = rg.unite(lastSnappingRange);
    lastSnappingRange = rg;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""),
        ("""
void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);""", """
void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    this->lineCrossingGuide.reset();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);"""),
        ("""        return true;
    }
    this->currPoint = newPoint;

    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());
""", """        return true;
    }
    this->currPoint = newPoint;
    this->lastZoom = zoom;

    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());
"""),
        ("""
    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());""", """
    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());
    this->lineCrossingGuide.reset();

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""),
        ("""    }
}

auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }

auto BaseShapeHandler::createView(xoj::view::Repaintable* parent) const -> std::unique_ptr<xoj::view::OverlayView> {""", """    }
}

/**
 * If `el` is a Stroke with at least 2 points, returns its two \"shaft\" endpoints: for a plain
 * straight line, its only two points; for an arrow (single or double-ended - see
 * ArrowHandler::createShape()), its first and last point specifically, which are always the true
 * shaft start and tip regardless of however many arrowhead \"wing\" points lie in between. Returns
 * nullopt for anything else (not a Stroke, or fewer than 2 points).
 */
static auto getLineShaftEndpoints(const Element* el) -> std::optional<std::pair<Point, Point>> {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getPointCount() < 2) {
        return std::nullopt;
    }
    const Point* pts = stroke->getPoints();
    return std::make_pair(pts[0], pts[stroke->getPointCount() - 1]);
}

auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    double dx = rawEnd.x - this->startPoint.x;
    double dy = rawEnd.y - this->startPoint.y;
    bool drawingVertical = std::abs(dx) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dy) > LINE_CROSS_MIN_LENGTH;
    bool drawingHorizontal = std::abs(dy) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dx) > LINE_CROSS_MIN_LENGTH;
    if (!drawingVertical && !drawingHorizontal) {
        return rawEnd;
    }

    Layer* layer = this->page->getSelectedLayer();
    if (layer == nullptr) {
        return rawEnd;
    }

    double currentLength = drawingVertical ? std::abs(dy) : std::abs(dx);
    double tolerance = LINE_CROSS_SNAP_TOLERANCE_PX / this->lastZoom;

    bool found = false;
    double bestTargetLength = 0;
    double bestDistFromCurrent = 0;

    for (auto& elPtr: layer->getElements()) {
        auto shaft = getLineShaftEndpoints(elPtr.get());
        if (!shaft) {
            continue;
        }
        double odx = shaft->second.x - shaft->first.x;
        double ody = shaft->second.y - shaft->first.y;
        double targetLength = std::hypot(odx, ody);
        if (targetLength <= LINE_CROSS_MIN_LENGTH) {
            continue;
        }
        bool targetIsVertical = std::abs(odx) <= LINE_CROSS_AXIS_TOLERANCE;
        bool targetIsHorizontal = std::abs(ody) <= LINE_CROSS_AXIS_TOLERANCE;

        if (drawingVertical) {
            if (!targetIsHorizontal) {
                continue;
            }
            double minX = std::min(shaft->first.x, shaft->second.x);
            double maxX = std::max(shaft->first.x, shaft->second.x);
            if (this->startPoint.x < minX || this->startPoint.x > maxX) {
                continue;
            }
            // The target must actually lie in the direction being drawn (above if drawing upward,
            // below if drawing downward) - otherwise it could never really be \"crossed\" by extending
            // the current line further, no matter how far it goes.
            double targetY = shaft->first.y;  // either endpoint works: nearly equal for a horizontal target
            if ((dy > 0 && targetY < this->startPoint.y) || (dy < 0 && targetY > this->startPoint.y)) {
                continue;
            }
            // The markers only appear once the line being drawn has ALREADY crossed the target's
            // height, not in anticipation of reaching it - i.e. targetY must already lie between the
            // origin and the current (raw, pre-snap) endpoint.
            if (targetY < std::min(this->startPoint.y, rawEnd.y) || targetY > std::max(this->startPoint.y, rawEnd.y)) {
                continue;
            }
        } else {
            if (!targetIsVertical) {
                continue;
            }
            double minY = std::min(shaft->first.y, shaft->second.y);
            double maxY = std::max(shaft->first.y, shaft->second.y);
            if (this->startPoint.y < minY || this->startPoint.y > maxY) {
                continue;
            }
            double targetX = shaft->first.x;
            if ((dx > 0 && targetX < this->startPoint.x) || (dx < 0 && targetX > this->startPoint.x)) {
                continue;
            }
            if (targetX < std::min(this->startPoint.x, rawEnd.x) || targetX > std::max(this->startPoint.x, rawEnd.x)) {
                continue;
            }
        }

        double distFromCurrent = std::abs(currentLength - targetLength);
        if (!found || distFromCurrent < bestDistFromCurrent) {
            found = true;
            bestDistFromCurrent = distFromCurrent;
            bestTargetLength = targetLength;
        }
    }

    if (!found || currentLength > bestTargetLength + tolerance) {
        return rawEnd;
    }

    double sign = drawingVertical ? (dy >= 0 ? 1.0 : -1.0) : (dx >= 0 ? 1.0 : -1.0);
    Point farCenter = drawingVertical ? Point(this->startPoint.x, this->startPoint.y + sign * bestTargetLength)
                                       : Point(this->startPoint.x + sign * bestTargetLength, this->startPoint.y);
    this->lineCrossingGuide = LineCrossingGuide{this->startPoint, farCenter, drawingVertical};

    if (bestDistFromCurrent < tolerance) {
        return drawingVertical ? Point(rawEnd.x, this->startPoint.y + sign * bestTargetLength)
                                : Point(this->startPoint.x + sign * bestTargetLength, rawEnd.y);
    }
    return rawEnd;
}

auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }

auto BaseShapeHandler::createView(xoj::view::Repaintable* parent) const -> std::unique_ptr<xoj::view::OverlayView> {"""),
    ]),
    ("src/core/control/tools/BaseShapeHandler.h", [
        ("""#pragma once

#include <memory>  // for shared_ptr
#include <utility>  // for pair
#include <vector>   // for vector
""", """#pragma once

#include <memory>  // for shared_ptr
#include <optional> // for optional
#include <utility>  // for pair
#include <vector>   // for vector
"""),
        ("""     */
    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }

private:
    /**
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in""", """     */
    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }

    /**
     * Two 15pt markers, drawn perpendicular to the line/arrow currently being drawn, illustrating a
     * matching length found on another line/arrow already on the page - see applyLineCrossingSnap().
     * `nearCenter` sits at the fixed origin point of the line being drawn; `farCenter` sits at the
     * target distance away, in the direction being drawn. `perpendicularIsHorizontal` is true when
     * the line being drawn is vertical (so the markers themselves are drawn as short horizontal
     * segments), false when it is horizontal (markers drawn as short vertical segments).
     */
    struct LineCrossingGuide {
        Point nearCenter;
        Point farCenter;
        bool perpendicularIsHorizontal;
    };
    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }

private:
    /**
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in"""),
        ("""     */
    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);

protected:
    std::vector<Point> shape;
""", """     */
    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);

    /**
     * If the segment from `this->startPoint` to `rawEnd` is axis-aligned (horizontal or vertical,
     * within a small tolerance) and longer than 50pt, and another sufficiently long, perpendicular
     * line/arrow already on the page crosses its path, updates `lineCrossingGuide` with two 15pt
     * markers illustrating that other line's length, and returns `rawEnd` snapped to match that exact
     * length if it is already close enough (same tolerance as the rest of the alignment-snapping
     * system). Otherwise clears `lineCrossingGuide` and returns `rawEnd` unchanged. Meant to be called
     * by a line-like shape's own createShape() (RulerHandler, ArrowHandler) right after computing its
     * own raw endpoint - not used by shapes like Rectangle or Ellipse. A Stroke with an ArrowKind
     * (single or double) is treated purely by its own shaft (first/last point), ignoring any
     * arrowhead \"wing\" points, on both ends of the comparison - a fresh arrow being drawn, and an
     * existing arrow being crossed.
     */
    Point applyLineCrossingSnap(Point rawEnd);

protected:
    std::vector<Point> shape;
"""),
        ("""    Point buttonDownPoint;  // used for tapSelect and filtering - never snapped to grid.
    Point startPoint;       // May be snapped to grid

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};""", """    Point buttonDownPoint;  // used for tapSelect and filtering - never snapped to grid.
    Point startPoint;       // May be snapped to grid

    /// Last zoom level seen in onMotionNotifyEvent() - createShape() has no zoom parameter of its
    /// own, but applyLineCrossingSnap() needs one to convert its pixel-based tolerance.
    double lastZoom = 1.0;

    std::optional<LineCrossingGuide> lineCrossingGuide;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};"""),
    ]),
    ("src/core/control/tools/RulerHandler.cpp", [
        ("""auto RulerHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    Range rg(this->startPoint.x, this->startPoint.y);
    rg.addPoint(secondPoint.x, secondPoint.y);
    return {{this->startPoint, secondPoint}, rg};""", """auto RulerHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    secondPoint = applyLineCrossingSnap(secondPoint);
    Range rg(this->startPoint.x, this->startPoint.y);
    rg.addPoint(secondPoint.x, secondPoint.y);
    return {{this->startPoint, secondPoint}, rg};"""),
    ]),
    ("src/core/view/overlays/ShapeToolView.cpp", [
        ("""#include <vector>

#include \"control/tools/BaseShapeHandler.h\"
#include \"util/raii/CairoWrappers.h\"
#include \"view/Repaintable.h\"
#include \"view/StrokeViewHelper.h\"""", """#include <vector>

#include \"control/tools/BaseShapeHandler.h\"
#include \"model/Point.h\"
#include \"util/raii/CairoWrappers.h\"
#include \"view/Repaintable.h\"
#include \"view/StrokeViewHelper.h\""""),
        ("""    StrokeViewHelper::pathToCairo(effCr, pts);

    this->commitDrawing(cr);
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }""", """    StrokeViewHelper::pathToCairo(effCr, pts);

    this->commitDrawing(cr);

    // \"Line crossing\" snap assist (see BaseShapeHandler::applyLineCrossingSnap()): two short pink
    // markers, perpendicular to the line/arrow being drawn, illustrating a matching length found on
    // another line/arrow already on the page. Drawn in document-space coordinates, same as `pts`
    // above - no manual zoom scaling needed here.
    if (auto guide = this->toolHandler->getLineCrossingGuide()) {
        constexpr double MARKER_HALF_SIZE = 7.5;  // 15pt marker, centered on the guide point
        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink, matching the alignment-snapping system
        cairo_set_line_width(cr, 1.0);
        for (const Point& center: {guide->nearCenter, guide->farCenter}) {
            if (guide->perpendicularIsHorizontal) {
                cairo_move_to(cr, center.x - MARKER_HALF_SIZE, center.y);
                cairo_line_to(cr, center.x + MARKER_HALF_SIZE, center.y);
            } else {
                cairo_move_to(cr, center.x, center.y - MARKER_HALF_SIZE);
                cairo_line_to(cr, center.x, center.y + MARKER_HALF_SIZE);
            }
            cairo_stroke(cr);
        }
    }
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }"""),
    ]),
]


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
    base_h = Path("src/core/control/tools/BaseShapeHandler.h")
    if not base_h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)

    ok = True
    for rel_path, edits in EDITS:
        path = Path(rel_path)
        if not path.exists():
            print(f"[ECHEC] Fichier introuvable : {rel_path}")
            ok = False
            continue
        for i, (old, new) in enumerate(edits, 1):
            label = f"{rel_path} (zone {i}/{len(edits)})"
            ok &= apply_edit(path, old, new, label)

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
