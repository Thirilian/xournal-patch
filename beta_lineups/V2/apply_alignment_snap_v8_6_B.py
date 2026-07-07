#!/usr/bin/env python3
"""
Patch 8.6.B (v2, reconstruit pour etre compatible avec une base incluant
le patch 9.1 - voir apply_alignment_snap_v7_11.py) : fusion des patchs
8.6.4, 8.6.4.2, 8.6.4.3, 8.6.4.4, 8.6.4.5, 8.6.4.6, 8.6.5, 8.6.6, 8.6.7,
8.6.8 en un seul, applicable PAR-DESSUS d'autres patchs - modifications
CIBLEES par ancres de texte (pas de reecriture de fichier entier),
exactement comme le reste de cette serie.

IMPORTANT : cette version remplace la version precedente de 8.6.B, dont
les ancres avaient ete extraites sur une base SANS le patch 9.1 (via
v7_10.py). Depuis que 9.1 a ete integre dans v7_11.py (qui remplace
v7_10.py), certaines zones de EditSelection.cpp ont un texte legerement
different (buildCandidates()/candidatesOther modifies par 9.1), ce qui
faisait echouer 4 des 16 zones de l'ancienne version. Cette version est
reconstruite specifiquement pour la chaine v7_11 + 8.1.0 + ... + 8.6.A.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_6_4.py
    apply_alignment_snap_v8_6_4_2.py
    apply_alignment_snap_v8_6_4_3.py
    apply_alignment_snap_v8_6_4_4.py
    apply_alignment_snap_v8_6_4_5.py
    apply_alignment_snap_v8_6_4_6.py
    apply_alignment_snap_v8_6_5.py
    apply_alignment_snap_v8_6_6.py
    apply_alignment_snap_v8_6_7.py
    apply_alignment_snap_v8_6_8.py
(dans cet ordre).

Note importante : cette chaine cree PUIS supprime un mecanisme
intermediaire (LineHalfDoubleUndoAction.h/.cpp, "coupe/double" - patchs
8.6.4 a 8.6.4.4), remplace par un mecanisme de translation pure
(LineRepositionUndoAction.h/.cpp - patch 8.6.4.5). Ce patch fusionne va
directement au resultat final : seuls LineRepositionUndoAction.h/.cpp
sont crees, LineHalfDoubleUndoAction n'existe jamais.

Fichiers MODIFIES par ancres de texte :
  - src/core/control/tools/EditSelection.cpp\n  - src/core/control/tools/EditSelection.h\n
Fichiers CREES integralement (contenu final directement embarque) :
  - src/core/undo/LineRepositionUndoAction.h\n  - src/core/undo/LineRepositionUndoAction.cpp\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v7_11.py (v1-v7.9 + 9.1 fusionnes) - OU la
     chaine individuelle equivalente v1.py a v7_9.py + v9_1.py
  3) apply_alignment_snap_v8_6_A.py (ou v8_6.py a v8_6_3_3.py)

Comme les autres patches de la serie qui creent des fichiers, n'oubliez
pas de relancer 'cmake ..' (pas seulement cmake --build .) apres avoir
applique ce patch, pour que CMake (GLOB_RECURSE) detecte les nouveaux
fichiers.

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/EditSelection.cpp", [
        ("""#include \"model/XojPage.h\"                        // for XojPage
#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction
#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction
#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler
#include \"util/Range.h\"                           // for Range
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector""", """#include \"model/XojPage.h\"                        // for XojPage
#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction
#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction
#include \"undo/LineRepositionUndoAction.h\"        // for LineRepositionUndoAction
#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler
#include \"util/Range.h\"                           // for Range
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector"""),
        (""" * Finish the current movement
 * (should be called in the mouse-button-released event handler)
 */
void EditSelection::mouseUp() {
    if (this->mouseDownType == CURSOR_SELECTION_DELETE) {
        this->view->getXournal()->deleteSelection();""", """ * Finish the current movement
 * (should be called in the mouse-button-released event handler)
 */
// \"Line reposition on release\" (patch 8.6.4.5) - defined later in this file (after its
// dependencies like THIN_AXIS_THRESHOLD/rangesOverlap/BLUE_GRID_LENGTH_EPS), forward-declared here
// so EditSelection::mouseUp() below can call it.
static void applyLineRepositionOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements);

void EditSelection::mouseUp() {
    if (this->mouseDownType == CURSOR_SELECTION_DELETE) {
        this->view->getXournal()->deleteSelection();"""),
        ("""    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();
    this->activeBlueGridMarkers.clear();

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);""", """    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    // \"Line reposition on release\" (patch 8.6.4.5) - only for an actual move (not a resize/rotate),
    // and only if a boosted (blue) match was active when the drag ended; activeBoostedTarget could
    // otherwise be a stale leftover from an earlier move gesture during this same selection.
    if (this->mouseDownType == CURSOR_SELECTION_MOVE && this->activeBoostedTarget != nullptr) {
        applyLineRepositionOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,
                                     this->activeBoostedIsXAxis, this->activeBoostedZone,
                                     this->getElementsView().clone());
    }

    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();
    this->activeBlueGridMarkers.clear();
    this->activeBoostedTarget = nullptr;

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);"""),
        ("""    }
}

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();
""", """    }
}

// \"Starting zone\" detection (patch 8.6.4.6) - defined later in this file (after its dependencies
// like THIN_AXIS_THRESHOLD/rangesOverlap and findAlignmentX/Y themselves), forward-declared here so
// EditSelection::mouseDown() below can call it.
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                bool& outWasBoosted);

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();
"""),
        ("""    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;
}

/**""", """    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;

    // \"Blue grid\" starting zone (patch 8.6.4.6): capture, once at the start of this drag, which zone
    // self was already in (Middle if not boosted at all) - see computeStartingZone(). Used later in
    // mouseMove()/paint() to shift the whole grid preview by the right amount as the zone changes.
    this->startingBoostedZone = 0;
    this->startingWasBoosted = false;
    {
        std::vector<const Element*> excludedForStart = this->getElementsView().clone();
        xoj::util::Rectangle<double>* visibleRectPtrForStart = this->view->getXournal()->getVisibleRect(this->view);
        if (visibleRectPtrForStart != nullptr) {
            xoj::util::Rectangle<double> visibleRectForStart = *visibleRectPtrForStart;
            delete visibleRectPtrForStart;
            constexpr double startingToleranceHardcodedPx = 6.0;  // matches ALIGNMENT_SNAP_TOLERANCE_PX
            double toleranceForStart = startingToleranceHardcodedPx / zoom;
            this->startingBoostedZone =
                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,
                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,
                                         visibleRectForStart, toleranceForStart, this->startingWasBoosted);
        }
    }
}

/**"""),
        (""" * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 2.25;

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's""", """ * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0;
/// Tolerance factor for snapping a small line to one of the big line's own two endpoints (patch
/// 8.6.5) - deliberately much smaller than PERPENDICULAR_CROSS_BOOST_FACTOR, since this snap is a
/// precise \"line up exactly with the end\" gesture rather than the generous perpendicular-cross
/// boost. Edit this value directly to tune how eagerly the endpoints grab a nearby small line.
constexpr double LINE_END_ANCHOR_TOLERANCE_FACTOR = 0.9;

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's"""),
        ("""    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {""", """    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

/**
 * \"Line reposition on release\" (patch 8.6.4.5): if the moving line was boost-snapped (blue) to
 * `bigLine` when the drag ended, every OTHER plain line of the exact same length crossing `bigLine`
 * the same way (see the eligibility rule below) - the moving line included - is translated (never
 * resized) so that the point matching the current zone lands exactly on `bigLine`: its bottom edge
 * for the \"negative\" zone (e.g. above a horizontal big line), its center for the middle zone, its
 * top edge for the \"positive\" zone (e.g. below it). `isXAxis` says whether the crossing is on the X
 * or Y axis (i.e. whether \"family\" lines are horizontal or vertical). Registers a single
 * LineRepositionUndoAction covering every line actually moved (elements already exactly at their
 * target position are skipped, so releasing without any real zone change is a no-op). Only plain
 * lines (no ArrowKind) ever participate - see patch 8.6.3.2. The currently-selected element(s) are
 * checked separately from `layer->getElements()`, since they are physically removed from the layer
 * for the duration of the selection (see createFromElementOnActiveLayer()) and would otherwise never
 * take part in their own family's transformation.
 */
static void applyLineRepositionOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements) {
    if (bigLine == nullptr) {
        return;
    }
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);

    // Determine self's own length (the \"same length as the moving line\" filter) from whichever of
    // the selected elements is itself an eligible plain line.
    double selfLength = -1;
    for (const Element* el: selfElements) {
        const auto* stroke = dynamic_cast<const Stroke*>(el);
        if (stroke != nullptr && stroke->getArrowKind() == ArrowKind::NONE && stroke->getPointCount() == 2) {
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            selfLength = isXAxis ? shaft.width : shaft.height;
            break;
        }
    }
    if (selfLength < 0) {
        return;
    }

    auto isEligibleFamilyMember = [&](const Element* el) -> bool {
        if (el == bigLine) {
            return false;
        }
        const auto* stroke = dynamic_cast<const Stroke*>(el);
        if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
            return false;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool matchesOrientation = isXAxis ? (shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD)
                                           : (shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD);
        if (!matchesOrientation) {
            return false;
        }
        double length = isXAxis ? shaft.width : shaft.height;
        if (std::abs(length - selfLength) > BLUE_GRID_LENGTH_EPS) {
            return false;
        }
        if (isXAxis) {
            return rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) &&
                   crossingCoord >= shaft.x && crossingCoord <= shaft.x + shaft.width;
        }
        return rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) &&
               crossingCoord >= shaft.y && crossingCoord <= shaft.y + shaft.height;
    };

    // The currently-selected line is deliberately NOT added to `family` here (patch 8.6.7): it was
    // already dynamically anchored to the correct zone-specific reference point live during the drag
    // (see the \"Dynamic anchor\" code in mouseMove()), and its final position was already committed by
    // updateContent() just before this function runs. Repositioning it again here would move it a
    // second time, off of its already-correct spot. selfElements is still used above purely to learn
    // self's own length.
    std::vector<Element*> family;
    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (isEligibleFamilyMember(el)) {
            family.push_back(el);
        }
    }
    if (family.empty()) {
        return;
    }

    std::vector<std::pair<Element*, double>> elementsWithDelta;
    constexpr double MOVE_EPS = 0.01;  // skip elements already exactly at their target position
    for (Element* el: family) {
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        double refPoint;
        if (zone < 0) {
            refPoint = isXAxis ? (shaft.x + shaft.width) : (shaft.y + shaft.height);  // far edge
        } else if (zone > 0) {
            refPoint = isXAxis ? shaft.x : shaft.y;  // near edge
        } else {
            refPoint = isXAxis ? (shaft.x + shaft.width / 2) : (shaft.y + shaft.height / 2);  // center
        }
        double delta = crossingCoord - refPoint;
        if (std::abs(delta) > MOVE_EPS) {
            elementsWithDelta.emplace_back(el, delta);
        }
    }
    if (elementsWithDelta.empty()) {
        return;
    }

    auto action = std::make_unique<LineRepositionUndoAction>(page, elementsWithDelta, isXAxis);
    action->redo(control);
    control->getUndoRedoHandler()->addUndoAction(std::move(action));
}


/**
 * \"Ordinary anchor point depends on mode\" (patch 8.6.8, point 2): determines which single point
 * should represent a plain small line `el` for the ORDINARY (green/pink) tier's own candidate list,
 * instead of the usual three (near edge, center, far edge). Purely geometric, deduced fresh each
 * time from `el`'s own current shape and any big perpendicular line it happens to cross right now -
 * nothing is stored. Returns -1 if `el`'s far edge (e.g. bottom, for a vertical line) coincides with
 * a crossing big line's center (i.e. el is in \"Top\" mode), +1 if its near edge does (\"Below\" mode),
 * or 0 for every other case (not a plain line, not crossing any big line at all, or crossing one but
 * still centered on it, i.e. \"Middle\") - 0 means \"use the ordinary center\", matching the same value
 * used elsewhere for Middle.
 */
static std::optional<int> detectLineZoneForOrdinaryAnchor(const Element* el, Layer* layer,
                                                            const std::vector<const Element*>& excluded) {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
        return std::nullopt;
    }
    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
    for (auto& bigPtr: layer->getElements()) {
        const Element* big = bigPtr.get();
        if (big == el || std::find(excluded.begin(), excluded.end(), big) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> bigShaft = big->getSnappedBounds();
        if (isVertical) {
            bool bigIsHorizontal = bigShaft.height <= THIN_AXIS_THRESHOLD && bigShaft.width > THIN_AXIS_THRESHOLD;
            if (!bigIsHorizontal ||
                !rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width)) {
                continue;
            }
            double bigCenter = bigShaft.y + bigShaft.height / 2;
            double farEdge = shaft.y + shaft.height;
            double nearEdge = shaft.y;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        } else {
            bool bigIsVertical = bigShaft.width <= THIN_AXIS_THRESHOLD && bigShaft.height > THIN_AXIS_THRESHOLD;
            if (!bigIsVertical ||
                !rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height)) {
                continue;
            }
            double bigCenter = bigShaft.x + bigShaft.width / 2;
            double farEdge = shaft.x + shaft.width;
            double nearEdge = shaft.x;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        }
    }
    return 0;
}

/// Given a plain small line's own zone (see detectLineZoneForOrdinaryAnchor()), builds the single
/// forced ordinary-tier candidate representing it: its far edge for Top (-1), near edge for Below
/// (+1), or its ordinary center for Middle (0) - matching the \"family\" anchor conventions used
/// throughout the rest of this feature (patch 8.6.8).
static auto buildForcedLineCandidate(double from, double size, int zone) -> std::vector<AlignmentCandidate> {
    if (zone < 0) {
        return {{from + size, false}};
    }
    if (zone > 0) {
        return {{from, false}};
    }
    return {{from + size / 2, true}};
}


static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {"""),
        ("""            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.y, snapped.height, otherCenterFraction,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);""", """            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.y, snapped.height, otherCenterFraction,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);"""),
        ("""            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.y, snapped.height, otherCenterFraction,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {""", """            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.y, snapped.height, otherCenterFraction,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {"""),
        ("""            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.x, snapped.width, 0.5,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);""", """            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.x, snapped.width, 0.5,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);"""),
        ("""            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.x, snapped.width, 0.5,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {""", """            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.x, snapped.width, 0.5,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {"""),
        ("""        }
    }
    return AlignmentSearchResult{offset, guides};
}
void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {
    double zoom = this->view->getXournal()->getZoom();
""", """        }
    }
    return AlignmentSearchResult{offset, guides};
}/**
 * \"Starting zone\" detection (patch 8.6.4.6): mirrors the \"already repositioned\" virtual-center trick
 * used during dragging (see EditSelection::mouseMove()), but applied ONCE, at the very start of a
 * drag (see EditSelection::mouseDown()), to self's own pre-drag geometry [x, y, width, height]. Tries
 * self's true center first (Middle, zone 0), then each of its own edges as a virtual center: if
 * self's own top edge is the one actually touching a big line (i.e. self extends downward from it),
 * that's the \"Below\" zone (+1); if self's own bottom edge is the anchor (self extends upward), that's
 * the \"Top\" zone (-1). Checks both axes (Y first, then X). Returns 0 (Middle) if self isn't currently
 * boosted at all.
 */
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                bool& outWasBoosted) {
    outWasBoosted = false;
    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"
    }
    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"
    }

    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXReal && !matchXReal->guides.empty() && matchXReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchXLeft = findAlignmentX(x - width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXLeft && !matchXLeft->guides.empty() && matchXLeft->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;
    }
    auto matchXRight = findAlignmentX(x + width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXRight && !matchXRight->guides.empty() && matchXRight->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;
    }
    return 0;
}

void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {
    double zoom = this->view->getXournal()->getZoom();
"""),
        ("""                    }
                }


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.""", """                    }
                }

                // \"Already halved\" self detection (patch 8.6.4, point 3): if self doesn't already have
                // a boosted match using its own true center, try treating each of its own edges as a
                // \"virtual center\" instead (by searching with a same-size box centered on that edge) -
                // this lets a line that was previously halved by the \"half/double on release\" feature
                // (now anchored at one edge rather than truly centered) still find and reconnect to the
                // big line it was cut from. Whichever of the three (real center, virtual near-edge
                // center, virtual far-edge center) gives the closest boosted match wins; offsets are
                // translated back to the real candidateX/candidateY frame before use. Arrows are
                // excluded here too, matching the \"only plain lines\" scope of the whole feature.
                //
                // selfAnchorY/selfAnchorX track which point should stand in for \"self's position\" when
                // computing the Top/Middle/Below zone further below: self's true center by default, or
                // whichever edge just won a virtual match above (the point actually touching the big
                // line right now).
                double selfAnchorY = candidateY + height / 2;
                double selfAnchorX = candidateX + width / 2;
                {
                    bool selfIsArrowForVirtualCheck = false;
                    auto selfElementsForVirtualCheck = this->getElementsView();
                    if (selfElementsForVirtualCheck.size() == 1) {
                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForVirtualCheck.begin())) {
                            selfIsArrowForVirtualCheck = selfStroke->getArrowKind() != ArrowKind::NONE;
                        }
                    }
                    if (!selfIsArrowForVirtualCheck) {
                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                        if (!matchYAlreadyBoosted) {
                            auto matchYVirtualTop =
                                    findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,
                                                   tolerance, this->sourceLayer, excluded, visibleRect);
                            auto matchYVirtualBottom =
                                    findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,
                                                   tolerance, this->sourceLayer, excluded, visibleRect);
                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&
                                                 matchYVirtualTop->guides.front().isBoosted;
                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&
                                                    matchYVirtualBottom->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetY;
                            if (topIsBoosted) {
                                double realOffset = matchYVirtualTop->offset - height / 2;
                                bestRealOffsetY = realOffset;
                                matchY = AlignmentSearchResult{realOffset, matchYVirtualTop->guides};
                                selfAnchorY = candidateY;  // the top edge (raw, pre-snap, like the default case)
                            }
                            if (bottomIsBoosted) {
                                double realOffset = matchYVirtualBottom->offset + height / 2;
                                if (!bestRealOffsetY || std::abs(realOffset) < std::abs(*bestRealOffsetY)) {
                                    matchY = AlignmentSearchResult{realOffset, matchYVirtualBottom->guides};
                                    selfAnchorY = candidateY + height;  // the bottom edge (raw, pre-snap)
                                }
                            }
                        }
                        bool matchXAlreadyBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                        if (!matchXAlreadyBoosted) {
                            auto matchXVirtualLeft =
                                    findAlignmentX(candidateX - width / 2, width, candidateY, candidateY + height,
                                                   tolerance, this->sourceLayer, excluded, visibleRect);
                            auto matchXVirtualRight =
                                    findAlignmentX(candidateX + width / 2, width, candidateY, candidateY + height,
                                                   tolerance, this->sourceLayer, excluded, visibleRect);
                            bool leftIsBoosted = matchXVirtualLeft && !matchXVirtualLeft->guides.empty() &&
                                                  matchXVirtualLeft->guides.front().isBoosted;
                            bool rightIsBoosted = matchXVirtualRight && !matchXVirtualRight->guides.empty() &&
                                                   matchXVirtualRight->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetX;
                            if (leftIsBoosted) {
                                double realOffset = matchXVirtualLeft->offset - width / 2;
                                bestRealOffsetX = realOffset;
                                matchX = AlignmentSearchResult{realOffset, matchXVirtualLeft->guides};
                                selfAnchorX = candidateX;  // the left edge (raw, pre-snap, like the default case)
                            }
                            if (rightIsBoosted) {
                                double realOffset = matchXVirtualRight->offset + width / 2;
                                if (!bestRealOffsetX || std::abs(realOffset) < std::abs(*bestRealOffsetX)) {
                                    matchX = AlignmentSearchResult{realOffset, matchXVirtualRight->guides};
                                    selfAnchorX = candidateX + width;  // the right edge (raw, pre-snap)
                                }
                            }
                        }
                    }
                }


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match."""),
        ("""                // true here makes the existing equidistant-blending code skip it automatically.
                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;
                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;
                this->activeBlueGridMarkers.clear();
                if (matchYIsBoosted && yBoostedTarget != nullptr) {
                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is""", """                // true here makes the existing equidistant-blending code skip it automatically.
                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;
                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;

                // \"Half/double on release\" (see EditSelection::mouseUp(), patch 8.6.4): tracks which
                // third of the boosted snap zone the moving line currently sits in (-1 = the \"negative\"
                // side, e.g. above a horizontal big line; 0 = middle; +1 = the \"positive\" side, e.g.
                // below it), purely for live visual feedback (truncating the blue grid markers below)
                // and for EditSelection::mouseUp() to read once the drag ends.
                this->activeBoostedTarget = nullptr;
                this->activeBoostedIsXAxis = false;
                this->activeBoostedZone = 0;
                // \"Line-end anchors\" (patch 8.6.5): flags/coordinates for the self-shaped blue overlay
                // guide, set below when self snaps to one of the big line's own two endpoints.
                bool endpointGuideActiveX = false;
                double endpointGuideCoordX = 0;
                double endpointGuideFromX = 0;
                double endpointGuideToX = 0;
                bool endpointGuideActiveY = false;
                double endpointGuideCoordY = 0;
                double endpointGuideFromY = 0;
                double endpointGuideToY = 0;
                if (yBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already
                    // boost-snapped to ANY big line when this drag started (this->startingWasBoosted
                    // == false) may not settle into Top/Below on its own just because the cursor
                    // dragged it into that zone - it must default to Middle, UNLESS other same-size,
                    // same-orientation lines are already established on THIS big line, in which case
                    // it follows their mode instead. A line that WAS already attached somewhere at
                    // mouseDown keeps full free transition between zones, as before.
                    if (!this->startingWasBoosted) {
                        int familyMode = 0;
                        bool familyFound = false;
                        double selfLengthForFamily = height;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == yBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isVerticalShaft =
                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                            if (!isVerticalShaft || std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                continue;
                            }
                            if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                shaft.x + shaft.width)) {
                                continue;
                            }
                            double shaftCenterY = shaft.y + shaft.height / 2;
                            if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            double farEdge = shaft.y + shaft.height;
                            double nearEdge = shaft.y;
                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = -1;
                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = 1;
                            } else {
                                familyMode = 0;
                            }
                            familyFound = true;
                            break;
                        }
                        this->activeBoostedZone = familyFound ? familyMode : 0;
                    }

                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever
                    // reference point matches the CURRENT zone (bottom edge for -1, center for 0, top
                    // edge for +1), not always its true center - so self visually moves together with
                    // the \"family\" grid preview as the zone changes mid-drag. Guides are left as-is
                    // (still correctly flagged boosted), only the offset is replaced.
                    double refPointY;
                    if (this->activeBoostedZone < 0) {
                        refPointY = candidateY + height;
                    } else if (this->activeBoostedZone > 0) {
                        refPointY = candidateY;
                    } else {
                        refPointY = candidateY + height / 2;
                    }
                    matchY->offset = targetCenter - refPointY;

                    // \"Line-end anchors\" (patch 8.6.5): while this big line has only 1 or 2 small
                    // lines crossing it (self included), its own two endpoints become additional
                    // anchor points for self's OTHER axis (the one along the big line's length) -
                    // letting self snap so it crosses right at one end. Independent of the Y offset
                    // above; only touches matchX.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == yBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isVerticalShaft =
                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                            if (!isVerticalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x,
                                                shaft.x + shaft.width)) {
                                continue;
                            }
                            double shaftCenterY = shaft.y + shaft.height / 2;
                            if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            existingCount++;
                        }
                        if (existingCount <= 1) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                bestOffset = leftEnd - selfCenterX;
                                found = true;
                            }
                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                bestOffset = rightEnd - selfCenterX;
                                found = true;
                            }
                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X.
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
                    }
                } else if (xBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case - see
                    // the Y-branch above for the full explanation.
                    if (!this->startingWasBoosted) {
                        int familyMode = 0;
                        bool familyFound = false;
                        double selfLengthForFamily = width;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == xBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isHorizontalShaft =
                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                            if (!isHorizontalShaft || std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                continue;
                            }
                            if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                shaft.y + shaft.height)) {
                                continue;
                            }
                            double shaftCenterX = shaft.x + shaft.width / 2;
                            if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            double farEdge = shaft.x + shaft.width;
                            double nearEdge = shaft.x;
                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = -1;
                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = 1;
                            } else {
                                familyMode = 0;
                            }
                            familyFound = true;
                            break;
                        }
                        this->activeBoostedZone = familyFound ? familyMode : 0;
                    }

                    double refPointX;
                    if (this->activeBoostedZone < 0) {
                        refPointX = candidateX + width;
                    } else if (this->activeBoostedZone > 0) {
                        refPointX = candidateX;
                    } else {
                        refPointX = candidateX + width / 2;
                    }
                    matchX->offset = targetCenter - refPointX;

                    // \"Line-end anchors\" (patch 8.6.5), mirrored for the X-boosted case (self
                    // horizontal, big line vertical): its own two endpoints (top/bottom) become
                    // additional anchor points for self's Y position.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == xBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isHorizontalShaft =
                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                            if (!isHorizontalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y,
                                                shaft.y + shaft.height)) {
                                continue;
                            }
                            double shaftCenterX = shaft.x + shaft.width / 2;
                            if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            existingCount++;
                        }
                        if (existingCount <= 1) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                bestOffset = topEnd - selfCenterY;
                                found = true;
                            }
                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                bestOffset = bottomEnd - selfCenterY;
                                found = true;
                            }
                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
                    }
                }
                this->activeBlueGridMarkers.clear();
                if (matchYIsBoosted && yBoostedTarget != nullptr) {
                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is"""),
        ("""                } else {
                    this->activeGuidesY.clear();
                }
            }
        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
            this->activeBlueGridMarkers.clear();
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position""", """                } else {
                    this->activeGuidesY.clear();
                }

                // \"Line-end anchors\" (patch 8.6.5): push the self-shaped blue overlay guide(s), if
                // any were found above. Uses designated initializers so this compiles regardless of
                // how many extra trailing fields AlignmentGuide has picked up from other patches.
                if (endpointGuideActiveX) {
                    this->activeGuidesX.push_back(AlignmentGuide{.coordinate = endpointGuideCoordX,
                                                                  .from = endpointGuideFromX,
                                                                  .to = endpointGuideToX,
                                                                  .isCenter = false,
                                                                  .isBoosted = true});
                }
                if (endpointGuideActiveY) {
                    this->activeGuidesY.push_back(AlignmentGuide{.coordinate = endpointGuideCoordY,
                                                                  .from = endpointGuideFromY,
                                                                  .to = endpointGuideToY,
                                                                  .isCenter = false,
                                                                  .isBoosted = true});
                }
            }
        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
            this->activeBlueGridMarkers.clear();
            this->activeBoostedTarget = nullptr;
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position"""),
        ("""        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue, matching the boosted tier
        for (auto& marker: this->activeBlueGridMarkers) {
            double mx = marker.x * zoom;
            double my = marker.y * zoom;
            double half = marker.halfLength * zoom;
            if (marker.isVertical) {
                cairo_move_to(cr, mx, my - half);
                cairo_line_to(cr, mx, my + half);
            } else {
                cairo_move_to(cr, mx - half, my);
                cairo_line_to(cr, mx + half, my);
            }
            cairo_stroke(cr);
        }""", """        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue, matching the boosted tier
        // Shift the whole grid preview along its own axis based on how the CURRENT zone differs from
        // the STARTING zone (the one self was already in when this drag began - see
        // EditSelection::mouseDown()/computeStartingZone()): delta = (current - starting) * halfLength,
        // per line. This matches, for example, Middle -> Top shifting everything by -halfLength (half
        // the line's own length, toward the \"negative\" direction), and Below -> Top by a full length.
        for (auto& marker: this->activeBlueGridMarkers) {
            double shift = (this->activeBoostedZone - this->startingBoostedZone) * marker.halfLength * zoom;
            double mx = marker.x * zoom;
            double my = marker.y * zoom;
            double half = marker.halfLength * zoom;
            if (marker.isVertical) {
                double shiftedY = my + shift;
                cairo_move_to(cr, mx, shiftedY - half);
                cairo_line_to(cr, mx, shiftedY + half);
            } else {
                double shiftedX = mx + shift;
                cairo_move_to(cr, shiftedX - half, my);
                cairo_line_to(cr, shiftedX + half, my);
            }
            cairo_stroke(cr);
        }"""),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        ("""    /// set during mouseMove() while dragging, if any.
    std::vector<BlueGridMarker> activeBlueGridMarkers;

    /**
     * The contents of the selection
     */""", """    /// set during mouseMove() while dragging, if any.
    std::vector<BlueGridMarker> activeBlueGridMarkers;

    /// The \"big line\" element the moving object is currently boost-snapped to, or nullptr if not
    /// currently boosted - set during mouseMove(), read by mouseUp() for the \"half/double on
    /// release\" feature (see patch 8.6.4) and by paint() to truncate the blue grid markers.
    const Element* activeBoostedTarget = nullptr;
    /// True if activeBoostedTarget's crossing is on the X axis (self horizontal, big line vertical),
    /// false if on Y. Only meaningful when activeBoostedTarget is not nullptr.
    bool activeBoostedIsXAxis = false;
    /// Which third of the boosted snap zone the moving line currently sits in: -1 for the \"negative\"
    /// side (e.g. above a horizontal big line), 0 for the middle third, +1 for the \"positive\" side
    /// (e.g. below it). Only meaningful when activeBoostedTarget is not nullptr.
    int activeBoostedZone = 0;
    /// The zone (see activeBoostedZone) self was already in when the current drag started - computed
    /// once in mouseDown() via computeStartingZone(). Used to shift the whole \"blue grid\" preview by
    /// the right amount as the zone changes mid-drag (patch 8.6.4.6).
    int startingBoostedZone = 0;
    /// True if self was already boost-snapped to SOME big line at the moment this drag started (see
    /// startingBoostedZone/computeStartingZone(), patch 8.6.4.6). When false (self is a \"fresh\" line,
    /// not previously attached anywhere), Top/Below zone transitions are disabled for this drag - see
    /// the \"fresh line\" override in mouseMove() (patch 8.6.6): a fresh line can only settle into
    /// Middle, unless other same-size/orientation lines are already established on the big line it
    /// is approaching, in which case it follows their mode instead.
    bool startingWasBoosted = false;

    /**
     * The contents of the selection
     */"""),
    ]),
]

NEW_FILES = {
    "src/core/undo/LineRepositionUndoAction.h": """/*
 * Xournal++
 *
 * Undo action for the \"line reposition on release\" feature (see EditSelection.cpp, patch 8.6.4.5):
 * translates a set of elements, each by its own individual delta along a single axis (X or Y),
 * without ever changing their size. Used to move every same-length line crossing a big perpendicular
 * line so that the correct edge (or center) - depending on the current Top/Middle/Below zone - lands
 * exactly on that big line.
 *
 * @author Xournal++ Team
 * https://github.com/xournalpp/xournalpp
 *
 * @license GNU GPLv2 or later
 */

#pragma once

#include <string>   // for string
#include <utility>  // for pair
#include <vector>   // for vector

#include \"model/PageRef.h\"  // for PageRef

#include \"UndoAction.h\"  // for UndoAction

class Control;
class Document;
class Element;

class LineRepositionUndoAction: public UndoAction {
public:
    LineRepositionUndoAction(const PageRef& page, std::vector<std::pair<Element*, double>> elementsWithDelta,
                              bool isXAxis);
    ~LineRepositionUndoAction() override;

public:
    bool undo(Control* control) override;
    bool redo(Control* control) override;
    std::string getText() override;

private:
    void apply(double sign);

private:
    std::vector<std::pair<Element*, double>> elementsWithDelta;
    bool isXAxis;
};
""",
    "src/core/undo/LineRepositionUndoAction.cpp": """#include \"LineRepositionUndoAction.h\"

#include <utility>  // for move

#include \"control/Control.h\"
#include \"model/Document.h\"
#include \"model/Element.h\"  // for Element
#include \"model/PageRef.h\"  // for PageRef
#include \"model/XojPage.h\"  // for XojPage
#include \"util/Range.h\"     // for Range
#include \"util/i18n.h\"      // for _

LineRepositionUndoAction::LineRepositionUndoAction(const PageRef& page,
                                                    std::vector<std::pair<Element*, double>> elementsWithDelta,
                                                    bool isXAxis):
        UndoAction(\"LineRepositionUndoAction\"), elementsWithDelta(std::move(elementsWithDelta)), isXAxis(isXAxis) {
    this->page = page;
}

LineRepositionUndoAction::~LineRepositionUndoAction() { this->page = nullptr; }

auto LineRepositionUndoAction::undo(Control* control) -> bool {
    apply(-1.0);
    this->undone = true;
    return true;
}

auto LineRepositionUndoAction::redo(Control* control) -> bool {
    apply(1.0);
    this->undone = false;
    return true;
}

void LineRepositionUndoAction::apply(double sign) {
    if (this->elementsWithDelta.empty()) {
        return;
    }

    Range r(elementsWithDelta.front().first->getX(), elementsWithDelta.front().first->getY());

    for (auto& [element, delta]: this->elementsWithDelta) {
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
        if (isXAxis) {
            element->move(sign * delta, 0);
        } else {
            element->move(0, sign * delta);
        }
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
    }

    this->page->fireRangeChanged(r);
}

auto LineRepositionUndoAction::getText() -> std::string { return _(\"Reposition aligned line\"); }
""",
}


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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "computeBlueGridX" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord toute la chaine 8.6 (v8_6.py a v8_6_3_3.py, ou v8_6_A.py), puis relancez ce script.")
        sys.exit(1)

    ok = True

    for rel_path, content in NEW_FILES.items():
        path = Path(rel_path)
        if path.exists():
            print(f"[SKIP]  Creation de {rel_path}: le fichier existe deja.")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[OK]    Creation de {rel_path}")
    print("[INFO]  N'oubliez pas de relancer 'cmake ..' (pas seulement cmake --build .) pour que")
    print("        CMake (GLOB_RECURSE) detecte ces nouveaux fichiers.")

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
