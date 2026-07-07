#!/usr/bin/env python3
"""
Patch 8.9.0 : fusion des patchs 8.9, 8.9.1, 8.9.2 (alignement pour
l'outil spline) en un seul, applicable PAR-DESSUS d'autres patchs -
modifications CIBLEES par ancres de texte (pas de reecriture de fichier
entier), exactement comme le reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_9.py
    apply_alignment_snap_v8_9_1.py
    apply_alignment_snap_v8_9_2.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch).

Fichiers concernes :
  - src/core/control/tools/SplineHandler.cpp\n  - src/core/control/tools/SplineHandler.h\n  - src/core/view/overlays/SplineToolView.cpp\n
Independant de toute la chaine 8.X precedente (ne touche pas
EditSelection.cpp) - applicable directement sur un depot xournalpp
vierge, comme le patch 8.9 d'origine.

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/SplineHandler.cpp", [
        ("""#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
#include \"gui/XournalppCursor.h\"                 // for XournalppCursor
#include \"gui/inputdevices/InputEvents.h\"        // for KeyEvent
#include \"gui/inputdevices/PositionInputData.h\"  // for PositionInputData
#include \"model/Document.h\"                      // for Document
#include \"model/Layer.h\"                         // for Layer
#include \"model/SplineSegment.h\"                 // for SplineSegment
#include \"model/Stroke.h\"                        // for Stroke""", """#include \"control/tools/InputHandler.h\"            // for InputHandler
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
#include \"model/Stroke.h\"                        // for Stroke"""),
        ("""#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"view/overlays/SplineToolView.h\"

SplineHandler::SplineHandler(Control* control, const PageRef& page):""", """#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"util/Rectangle.h\"                      // for Rectangle
#include \"view/overlays/SplineToolView.h\"

SplineHandler::SplineHandler(Control* control, const PageRef& page):"""),
        ("""}

constexpr double SHIFT_AMOUNT = 1.0;
constexpr double ROTATE_AMOUNT = 5.0;
constexpr double SCALE_AMOUNT = 1.05;
constexpr double MAX_TANGENT_LENGTH = 2000.0;""", """}

constexpr double SHIFT_AMOUNT = 1.0;
/// Tolerance, in points, for the moving point's ordinary (green/pink) alignment snap (patch 8.9) -
/// matches EditSelection.cpp's own ALIGNMENT_SNAP_TOLERANCE_PX, kept as a separate constant here
/// since the two files don't share this value.
constexpr double ALIGNMENT_SNAP_TOLERANCE_PX = 6.0;
constexpr double ROTATE_AMOUNT = 5.0;
constexpr double SCALE_AMOUNT = 1.05;
constexpr double MAX_TANGENT_LENGTH = 2000.0;"""),
        ("""    return false;
}

auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;""", """    return false;
}

/**
 * \"Ordinary\" (green/pink) alignment guide for the spline's moving point (patch 8.9): finds the
 * closest edge or center, on a single axis, among every element on `layer` that is currently
 * visible, within `tolerance` of `value`. Mirrors the \"ordinary tier\" of EditSelection's own
 * alignment system (see EditSelection.cpp), but simplified for a single point rather than a moving
 * box - only three candidates per element (near edge, center, far edge), no boosted/equidistant/etc.
 * tiers. `getAxisRange` extracts an element's own [from, from+size] range on the axis being matched;
 * `getPerpFrom`/`getPerpTo` extract its range on the OTHER axis. The matched element's own
 * perpendicular range (otherPerpFrom/otherPerpTo) is returned as-is, NOT yet combined with any point
 * - the caller combines it with the FINAL, fully-resolved point once known (patch 8.9.1), since at
 * the time this search runs the other axis may not have been resolved yet.
 */
struct SplinePointAlignmentMatch {
    double offset;
    double coordinate;
    double otherPerpFrom;
    double otherPerpTo;
    bool isCenter;
};

template <typename AxisRangeFn, typename PerpFromFn, typename PerpToFn>
static auto findSplinePointAlignment(double value, double tolerance, Layer* layer,
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
                best = SplinePointAlignmentMatch{candidates[i] - value, candidates[i], getPerpFrom(snapped),
                                                  getPerpTo(snapped), candidateIsCenter[i]};
            }
        }
    }
    return best;
}

static auto findSplinePointAlignmentX(double x, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            x, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.x, r.width}; },
            [](const xoj::util::Rectangle<double>& r) { return r.y; },
            [](const xoj::util::Rectangle<double>& r) { return r.y + r.height; });
}

static auto findSplinePointAlignmentY(double y, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            y, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.y, r.height}; },
            [](const xoj::util::Rectangle<double>& r) { return r.x; },
            [](const xoj::util::Rectangle<double>& r) { return r.x + r.width; });
}

/// Bounding Range of a single alignment guide (patch 8.9.1), so its area can be included in the
/// repaint range whenever it appears, moves, or disappears - fixing the same kind of \"ghosting\" bug
/// already fixed for the blue grid markers in patch 8.4.2.
static auto splineGuideRange(const std::optional<SplineAlignmentGuide>& guide, bool isVertical) -> Range {
    if (!guide) {
        return Range();
    }
    if (isVertical) {
        return Range(guide->coordinate, guide->from, guide->coordinate, guide->to);
    }
    return Range(guide->from, guide->coordinate, guide->to, guide->coordinate);
}


auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;"""),
        ("""
    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;""", """
    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        this->activeGuideX.reset();
        this->activeGuideY.reset();
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;"""),
        ("""        bool nowInAttractionZone =
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
    }""", """        bool nowInAttractionZone =
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

            // Ordinary (green/pink) alignment for the moving point (patch 8.9, corrected in 8.9.2):
            // on any axis where a match is found, it REPLACES the angle/distance snap computed just
            // above outright - it does not merely compete with it. Never considers the spline's own
            // knots so far, only other elements already on the page.
            //
            // Guides are only finalized (patch 8.9.1) once BOTH axes are resolved, using the FINAL
            // snapped point rather than the raw cursor position, so a guide always connects the other
            // element's anchor to the spline preview's actual anchor point, not to the mouse cursor.
            // The previous frame's guides (if any) are kept aside so their old area, along with the
            // new one, gets included in the repaint range below - fixing the same kind of \"ghosting\"
            // bug already fixed for the blue grid markers in patch 8.4.2.
            std::optional<SplineAlignmentGuide> oldGuideX = this->activeGuideX;
            std::optional<SplineAlignmentGuide> oldGuideY = this->activeGuideY;
            this->activeGuideX.reset();
            this->activeGuideY.reset();

            std::optional<SplinePointAlignmentMatch> matchX;
            std::optional<SplinePointAlignmentMatch> matchY;
            Layer* layer = this->page->getSelectedLayer();
            if (layer != nullptr) {
                xoj::util::Rectangle<double>* visibleRectPtr =
                        this->control->getWindow()->getXournal()->getVisibleRect(this->control->getCurrentPageNo());
                if (visibleRectPtr != nullptr) {
                    xoj::util::Rectangle<double> visibleRect = *visibleRectPtr;
                    delete visibleRectPtr;
                    double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;

                    // Ordinary (green/pink) alignment now REPLACES the angle/distance snap on any
                    // axis where a match is found (patch 8.9.2, correcting the original \"closest
                    // wins\" design of patch 8.9) - it no longer competes with it, it simply takes
                    // priority outright.
                    matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, tolerance, layer, visibleRect);
                    matchY = findSplinePointAlignmentY(this->buttonDownPoint.y, tolerance, layer, visibleRect);
                }
            }
            if (matchX) {
                snapped.x = this->buttonDownPoint.x + matchX->offset;
            }
            if (matchY) {
                snapped.y = this->buttonDownPoint.y + matchY->offset;
            }
            // Now that `snapped` is final, build the guides so they connect to it rather than to the
            // raw cursor position.
            if (matchX) {
                this->activeGuideX = SplineAlignmentGuide{matchX->coordinate,
                                                           std::min(matchX->otherPerpFrom, snapped.y),
                                                           std::max(matchX->otherPerpTo, snapped.y),
                                                           matchX->isCenter};
            }
            if (matchY) {
                this->activeGuideY = SplineAlignmentGuide{matchY->coordinate,
                                                           std::min(matchY->otherPerpFrom, snapped.x),
                                                           std::max(matchY->otherPerpTo, snapped.x),
                                                           matchY->isCenter};
            }

            double guidePadding = std::max(1.5 / zoom, this->stroke->getWidth());
            Range guidesRg = splineGuideRange(oldGuideX, true);
            guidesRg = guidesRg.unite(splineGuideRange(oldGuideY, false));
            guidesRg = guidesRg.unite(splineGuideRange(this->activeGuideX, true));
            guidesRg = guidesRg.unite(splineGuideRange(this->activeGuideY, false));
            if (guidesRg.isValid()) {
                guidesRg.addPadding(guidePadding);
                rg = rg.unite(guidesRg);
            }

            this->currPoint = snapped;
        }
        this->inFirstKnotAttractionZone = nowInAttractionZone;
    }"""),
        ("""    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots, this->tangents, this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone};
}

auto SplineHandler::linearizeSpline(const SplineHandler::Data& data) -> std::vector<Point> {""", """    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots,       this->tangents,   this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone, this->activeGuideX, this->activeGuideY};
}

auto SplineHandler::linearizeSpline(const SplineHandler::Data& data) -> std::vector<Point> {"""),
    ]),
    ("src/core/control/tools/SplineHandler.h", [
        ("""};  // namespace xoj::view

/**
 * @brief Helper structure for communication with the views
 */
struct SplineHandlerData {""", """};  // namespace xoj::view

/**
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
struct SplineHandlerData {"""),
        ("""    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
};

/**""", """    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
    const std::optional<SplineAlignmentGuide>& guideX;
    const std::optional<SplineAlignmentGuide>& guideY;
};

/**"""),
        ("""    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::SplineToolView>> viewPool;

    static constexpr double KNOTS_ATTRACTION_RADIUS_IN_PIXELS = 10.0;  // for circling the spline's knots""", """    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

    /// Active ordinary (green/pink) alignment guides for currPoint (patch 8.9), if any - competes,
    /// axis by axis, with the angle/distance snap already provided by snappingHandler; whichever is
    /// closer to the raw cursor position wins for that axis.
    std::optional<SplineAlignmentGuide> activeGuideX;
    std::optional<SplineAlignmentGuide> activeGuideY;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::SplineToolView>> viewPool;

    static constexpr double KNOTS_ATTRACTION_RADIUS_IN_PIXELS = 10.0;  // for circling the spline's knots"""),
    ]),
    ("src/core/view/overlays/SplineToolView.cpp", [
        ("""    }
    cairo_stroke(cr);

    this->drawSpline(cr, data.value());
}
""", """    }
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
"""),
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
    h = Path("src/core/control/tools/SplineHandler.h")
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    view = Path("src/core/view/overlays/SplineToolView.cpp")
    if not h.exists() or not cpp.exists() or not view.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "SplineAlignmentGuide" in h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 8.9.0 semble deja applique.")
        sys.exit(0)

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
