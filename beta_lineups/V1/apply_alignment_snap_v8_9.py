#!/usr/bin/env python3
"""
Patch 8.9 (independant de toute la chaine 8.X precedente - touche des
fichiers completement differents, applicable directement sur un depot
xournalpp vierge) : ajoute l'accroche d'alignement ordinaire (palier
vert/rose) au point mobile de l'outil spline.

Pendant le trace d'une spline (avant d'appuyer le bouton pour placer le
prochain noeud), le point qui suit la souris (currPoint) essaie desormais
de s'aligner sur les bords/centres des AUTRES elements deja presents sur
la page - independamment pour chaque axe, en concurrence avec l'accroche
angle/distance deja existante (snappingHandler.snap) : celui qui tire le
moins loin de la position brute du curseur l'emporte pour cet axe. Les
points deja poses de la spline en cours de trace NE sont PAS des points
d'ancrage possibles. Un repere visuel (vert pour un centre, rose pour un
bord - meme convention que EditSelection.cpp) s'affiche pendant l'accroche.

Modifie :
  - src/core/control/tools/SplineHandler.h
  - src/core/control/tools/SplineHandler.cpp
  - src/core/view/overlays/SplineToolView.cpp

Aucun prerequis - applicable directement sur un depot xournalpp fraichement
clone.

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """/**
 * @brief Helper structure for communication with the views
 */
struct SplineHandlerData {
    const std::vector<Point>& knots;
    const std::vector<Point>& tangents;
    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
};

"""
NEW_H1 = """/**
 * @brief A single alignment guide line for the spline's moving point (patch 8.9): connects `currPoint`
 * to whichever other element's edge or center it is currently aligned with, on one axis.
 */
struct SplineAlignmentGuide {
    double coordinate;
    double from;
    double to;
    bool isCenter;
};

/**
 * @brief Helper structure for communication with the views
 */
struct SplineHandlerData {
    const std::vector<Point>& knots;
    const std::vector<Point>& tangents;
    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
    const std::optional<SplineAlignmentGuide>& guideX;
    const std::optional<SplineAlignmentGuide>& guideY;
};

"""
OLD_H2 = """    bool isButtonPressed = false;
    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

"""
NEW_H2 = """    bool isButtonPressed = false;
    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

    /// Active ordinary (green/pink) alignment guides for currPoint (patch 8.9), if any - competes,
    /// axis by axis, with the angle/distance snap already provided by snappingHandler; whichever is
    /// closer to the raw cursor position wins for that axis.
    std::optional<SplineAlignmentGuide> activeGuideX;
    std::optional<SplineAlignmentGuide> activeGuideY;

"""
OLD_INC = """#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
#include \"gui/XournalppCursor.h\"                 // for XournalppCursor
#include \"gui/inputdevices/InputEvents.h\"        // for KeyEvent
#include \"gui/inputdevices/PositionInputData.h\"  // for PositionInputData
#include \"model/Document.h\"                      // for Document
#include \"model/Layer.h\"                         // for Layer
#include \"model/SplineSegment.h\"                 // for SplineSegment
#include \"model/Stroke.h\"                        // for Stroke
#include \"model/XojPage.h\"                       // for XojPage
#include \"undo/InsertUndoAction.h\"               // for InsertUndoAction
#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"view/overlays/SplineToolView.h\""""
NEW_INC = """#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
#include \"gui/MainWindow.h\"                      // for MainWindow
#include \"gui/XournalView.h\"                     // for XournalView
#include \"gui/XournalppCursor.h\"                 // for XournalppCursor
#include \"gui/inputdevices/InputEvents.h\"        // for KeyEvent
#include \"gui/inputdevices/PositionInputData.h\"  // for PositionInputData
#include \"model/Document.h\"                      // for Document
#include \"model/Element.h\"                       // for Element
#include \"model/Layer.h\"                         // for Layer
#include \"model/SplineSegment.h\"                 // for SplineSegment
#include \"model/Stroke.h\"                        // for Stroke
#include \"model/XojPage.h\"                       // for XojPage
#include \"undo/InsertUndoAction.h\"               // for InsertUndoAction
#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"util/Rectangle.h\"                      // for Rectangle
#include \"view/overlays/SplineToolView.h\""""
OLD_CONST = """constexpr double SHIFT_AMOUNT = 1.0;"""
NEW_CONST = """constexpr double SHIFT_AMOUNT = 1.0;
/// Tolerance, in points, for the moving point's ordinary (green/pink) alignment snap (patch 8.9) -
/// matches EditSelection.cpp's own ALIGNMENT_SNAP_TOLERANCE_PX, kept as a separate constant here
/// since the two files don't share this value.
constexpr double ALIGNMENT_SNAP_TOLERANCE_PX = 6.0;"""
OLD_OMNE = """auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;
    }

    xoj_assert(!this->knots.empty() && this->knots.size() == this->tangents.size());

    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;
        }
        Point newTangent = Point(pos.x / zoom - this->currPoint.x, pos.y / zoom - this->currPoint.y);
        if (validMotion(newTangent, this->tangents.back())) {
            this->modifyLastTangent(newTangent);
        }
    } else {
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        bool nowInAttractionZone =
                this->buttonDownPoint.lineLengthTo(this->knots.front()) < this->knotsAttractionRadius;
        if (nowInAttractionZone) {
            if (this->inFirstKnotAttractionZone) {
                // No need to update anything while staying in the attraction zone
                return true;
            }
        } else {
            this->currPoint = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());
        }
        this->inFirstKnotAttractionZone = nowInAttractionZone;
    }
    rg = rg.unite(this->computeLastSegmentRepaintRange());

    this->viewPool->dispatch(xoj::view::SplineToolView::FLAG_DIRTY_REGION, rg);
    return true;
}"""
NEW_OMNE = """/**
 * \"Ordinary\" (green/pink) alignment guide for the spline's moving point (patch 8.9): finds the
 * closest edge or center, on a single axis, among every element on `layer` that is currently
 * visible, within `tolerance` of `value`. Mirrors the \"ordinary tier\" of EditSelection's own
 * alignment system (see EditSelection.cpp), but simplified for a single point rather than a moving
 * box - only three candidates per element (near edge, center, far edge), no boosted/equidistant/etc.
 * tiers. `getAxisRange` extracts an element's own [from, from+size] range on the axis being matched;
 * `getPerpFrom`/`getPerpTo` extract its range on the OTHER axis, used to size the guide line.
 */
struct SplinePointAlignmentMatch {
    double offset;
    SplineAlignmentGuide guide;
};

template <typename AxisRangeFn, typename PerpFromFn, typename PerpToFn>
static auto findSplinePointAlignment(double value, double perpValue, double tolerance, Layer* layer,
                                      const xoj::util::Rectangle<double>& visibleRect, AxisRangeFn getAxisRange,
                                      PerpFromFn getPerpFrom, PerpToFn getPerpTo)
        -> std::optional<SplinePointAlignmentMatch> {
    std::optional<SplinePointAlignmentMatch> best;
    double bestDist = tolerance;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!(ex <= visibleRect.x + visibleRect.width && visibleRect.x <= ex + ew &&
              ey <= visibleRect.y + visibleRect.height && visibleRect.y <= ey + eh)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        auto [from, size] = getAxisRange(snapped);
        double candidates[3] = {from, from + size / 2, from + size};
        bool candidateIsCenter[3] = {false, true, false};
        for (int i = 0; i < 3; ++i) {
            double dist = std::abs(value - candidates[i]);
            if (dist < bestDist) {
                bestDist = dist;
                double perpFrom = std::min(getPerpFrom(snapped), perpValue);
                double perpTo = std::max(getPerpTo(snapped), perpValue);
                best = SplinePointAlignmentMatch{
                        candidates[i] - value,
                        SplineAlignmentGuide{candidates[i], perpFrom, perpTo, candidateIsCenter[i]}};
            }
        }
    }
    return best;
}

static auto findSplinePointAlignmentX(double x, double y, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            x, y, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.x, r.width}; },
            [](const xoj::util::Rectangle<double>& r) { return r.y; },
            [](const xoj::util::Rectangle<double>& r) { return r.y + r.height; });
}

static auto findSplinePointAlignmentY(double x, double y, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            y, x, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.y, r.height}; },
            [](const xoj::util::Rectangle<double>& r) { return r.x; },
            [](const xoj::util::Rectangle<double>& r) { return r.x + r.width; });
}


auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;
    }

    xoj_assert(!this->knots.empty() && this->knots.size() == this->tangents.size());

    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        this->activeGuideX.reset();
        this->activeGuideY.reset();
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;
        }
        Point newTangent = Point(pos.x / zoom - this->currPoint.x, pos.y / zoom - this->currPoint.y);
        if (validMotion(newTangent, this->tangents.back())) {
            this->modifyLastTangent(newTangent);
        }
    } else {
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        bool nowInAttractionZone =
                this->buttonDownPoint.lineLengthTo(this->knots.front()) < this->knotsAttractionRadius;
        if (nowInAttractionZone) {
            this->activeGuideX.reset();
            this->activeGuideY.reset();
            if (this->inFirstKnotAttractionZone) {
                // No need to update anything while staying in the attraction zone
                return true;
            }
        } else {
            Point snapped = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());

            // Ordinary (green/pink) alignment for the moving point (patch 8.9): competes, axis by
            // axis, with the angle/distance snap just computed above - whichever is closer to the
            // raw cursor position wins for that axis. Never considers the spline's own knots so far,
            // only other elements already on the page.
            this->activeGuideX.reset();
            this->activeGuideY.reset();
            Layer* layer = this->page->getSelectedLayer();
            if (layer != nullptr) {
                xoj::util::Rectangle<double>* visibleRectPtr =
                        this->control->getWindow()->getXournal()->getVisibleRect(this->control->getCurrentPageNo());
                if (visibleRectPtr != nullptr) {
                    xoj::util::Rectangle<double> visibleRect = *visibleRectPtr;
                    delete visibleRectPtr;
                    double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;

                    if (auto matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, this->buttonDownPoint.y,
                                                                 tolerance, layer, visibleRect)) {
                        if (std::abs(matchX->offset) < std::abs(snapped.x - this->buttonDownPoint.x)) {
                            snapped.x = this->buttonDownPoint.x + matchX->offset;
                            this->activeGuideX = matchX->guide;
                        }
                    }
                    if (auto matchY = findSplinePointAlignmentY(this->buttonDownPoint.x, this->buttonDownPoint.y,
                                                                 tolerance, layer, visibleRect)) {
                        if (std::abs(matchY->offset) < std::abs(snapped.y - this->buttonDownPoint.y)) {
                            snapped.y = this->buttonDownPoint.y + matchY->offset;
                            this->activeGuideY = matchY->guide;
                        }
                    }
                }
            }

            this->currPoint = snapped;
        }
        this->inFirstKnotAttractionZone = nowInAttractionZone;
    }
    rg = rg.unite(this->computeLastSegmentRepaintRange());

    this->viewPool->dispatch(xoj::view::SplineToolView::FLAG_DIRTY_REGION, rg);
    return true;
}"""
OLD_GETDATA = """auto SplineHandler::getData() const -> std::optional<Data> {
    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots, this->tangents, this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone};
}"""
NEW_GETDATA = """auto SplineHandler::getData() const -> std::optional<Data> {
    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots,       this->tangents,   this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone, this->activeGuideX, this->activeGuideY};
}"""
OLD_VIEW = """    Util::cairo_set_source_argb(cr, TANGENT_VECTOR_COLOR);
    // draw dynamically changing tangent vector
    cairo_move_to(cr, lastKnot.x - lastTangent.x, lastKnot.y - lastTangent.y);
    cairo_line_to(cr, lastKnot.x + lastTangent.x, lastKnot.y + lastTangent.y);

    // draw other tangent vectors
    for (size_t i = 0; i < data->knots.size() - 1; i++) {
        cairo_move_to(cr, data->knots[i].x - data->tangents[i].x, data->knots[i].y - data->tangents[i].y);
        cairo_line_to(cr, data->knots[i].x + data->tangents[i].x, data->knots[i].y + data->tangents[i].y);
    }
    cairo_stroke(cr);

    this->drawSpline(cr, data.value());
}

"""
NEW_VIEW = """    Util::cairo_set_source_argb(cr, TANGENT_VECTOR_COLOR);
    // draw dynamically changing tangent vector
    cairo_move_to(cr, lastKnot.x - lastTangent.x, lastKnot.y - lastTangent.y);
    cairo_line_to(cr, lastKnot.x + lastTangent.x, lastKnot.y + lastTangent.y);

    // draw other tangent vectors
    for (size_t i = 0; i < data->knots.size() - 1; i++) {
        cairo_move_to(cr, data->knots[i].x - data->tangents[i].x, data->knots[i].y - data->tangents[i].y);
        cairo_line_to(cr, data->knots[i].x + data->tangents[i].x, data->knots[i].y + data->tangents[i].y);
    }
    cairo_stroke(cr);

    // Ordinary (green/pink) alignment guide(s) for the moving point (patch 8.9) - green for a
    // center match, pink for an edge match, matching EditSelection's own color convention.
    if (data->guideX || data->guideY) {
        cairo_save(cr);
        cairo_set_line_width(cr, lineWidth);
        if (data->guideX) {
            const auto& g = *data->guideX;
            if (g.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            cairo_move_to(cr, g.coordinate, g.from);
            cairo_line_to(cr, g.coordinate, g.to);
            cairo_stroke(cr);
        }
        if (data->guideY) {
            const auto& g = *data->guideY;
            if (g.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            cairo_move_to(cr, g.from, g.coordinate);
            cairo_line_to(cr, g.to, g.coordinate);
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }

    this->drawSpline(cr, data.value());
}

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
    h = Path("src/core/control/tools/SplineHandler.h")
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    view = Path("src/core/view/overlays/SplineToolView.cpp")
    if not h.exists() or not cpp.exists() or not view.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "SplineAlignmentGuide" in h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 8.9 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h, OLD_H1, NEW_H1, "SplineHandler.h: struct SplineAlignmentGuide + SplineHandlerData")
    ok &= apply_edit(h, OLD_H2, NEW_H2, "SplineHandler.h: membres activeGuideX/Y")
    ok &= apply_edit(cpp, OLD_INC, NEW_INC, "SplineHandler.cpp: includes")
    ok &= apply_edit(cpp, OLD_CONST, NEW_CONST, "SplineHandler.cpp: constante de tolerance")
    ok &= apply_edit(cpp, OLD_OMNE, NEW_OMNE, "SplineHandler.cpp: recherche d'alignement + integration")
    ok &= apply_edit(cpp, OLD_GETDATA, NEW_GETDATA, "SplineHandler.cpp: getData() transmet les reperes")
    ok &= apply_edit(view, OLD_VIEW, NEW_VIEW, "SplineToolView.cpp: affichage des reperes vert/rose")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
