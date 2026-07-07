#!/usr/bin/env python3
"""
Patch 8.9.1 (depend de 8.9) : corrige deux problemes signales par
l'utilisateur.

1) Meme type de bug de "fantome" (ghosting) que celui corrige dans le
   patch 8.4.2 pour les reperes de la grille bleue : la zone de
   rafraichissement calculee ne couvrait pas la zone du repere
   d'alignement lui-meme (qui peut s'etendre loin du trace de la spline,
   jusqu'a l'objet auquel il se connecte). Corrige en incluant la zone de
   l'ANCIEN et du NOUVEAU repere (sur chaque axe) dans le rafraichissement.

2) La ligne du repere devait relier le point d'ancrage de l'AUTRE objet au
   point d'ancrage de l'apercu de la spline (currPoint, une fois
   pleinement resolu sur les deux axes), pas a la position brute du
   curseur de la souris. Corrige en reportant la construction du repere
   apres la resolution complete du point (X et Y).

NECESSITE : apply_alignment_snap_v8_9.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD1 = """/**
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
"""
NEW1 = """/**
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
"""
OLD2 = """auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
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
NEW2 = """auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
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

                    matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, tolerance, layer, visibleRect);
                    if (matchX && std::abs(matchX->offset) >= std::abs(snapped.x - this->buttonDownPoint.x)) {
                        matchX.reset();
                    }
                    matchY = findSplinePointAlignmentY(this->buttonDownPoint.y, tolerance, layer, visibleRect);
                    if (matchY && std::abs(matchY->offset) >= std::abs(snapped.y - this->buttonDownPoint.y)) {
                        matchY.reset();
                    }
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
    }
    rg = rg.unite(this->computeLastSegmentRepaintRange());

    this->viewPool->dispatch(xoj::view::SplineToolView::FLAG_DIRTY_REGION, rg);
    return true;
}"""


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
    cpp = Path("src/core/control/tools/SplineHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] SplineHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    text = cpp.read_text(encoding="utf-8")
    if "SplinePointAlignmentMatch" not in text:
        print("[ECHEC] SplinePointAlignmentMatch introuvable dans SplineHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_9.py, puis relancez ce script.")
        sys.exit(1)
    if "splineGuideRange" in text:
        print("[SKIP] Le patch 8.9.1 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD1, NEW1, "SplineHandler.cpp: recherche d'alignement - report du calcul des extremites")
    ok &= apply_edit(cpp, OLD2, NEW2, "SplineHandler.cpp: onMotionNotifyEvent() - point final + zone de rafraichissement")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
