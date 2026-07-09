#!/usr/bin/env python3
"""
Patch 8.6.4.5 (depend de 8.6.3.3 - remplace entierement le mecanisme des
patches 8.6.4 a 8.6.4.4, qu'il retire automatiquement s'ils sont deja
appliques) : nouveau comportement pour les petites lignes accrochees au
palier bleu.

Au lieu de couper/doubler les lignes (ancien mecanisme, retire), le
nouveau mecanisme deplace (translation pure, AUCUN changement de taille)
toutes les petites lignes de meme taille que celle deplacee, deja
accrochees a la meme grande ligne :

  - Mode "negatif" (ex : au-dessus d'une grande ligne horizontale) :
    le point d'ancrage de toutes les lignes devient leur EXTREMITE BASSE.
  - Mode "milieu" : le point d'ancrage redevient leur CENTRE.
  - Mode "positif" (ex : en dessous) : le point d'ancrage devient leur
    EXTREMITE HAUTE.

Les reperes bleus de previsualisation gardent la taille REELLE de chaque
ligne (pas de troncature, puisqu'on ne coupe plus rien).

Ce script detecte si les patches 8.6.4/8.6.4.2/8.6.4.3/8.6.4.4 sont deja
appliques (presence de applyLineHalfDoubleOnRelease) et, si oui, retire
proprement leurs modifications specifiques (fonction, appel, fichiers
d'annulation) avant d'appliquer le nouveau mecanisme - le reste (membres,
detection de zone, detection "deja repositionne") est identique entre les
deux versions et n'a pas besoin d'etre touche.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py

Applicable directement sur cette base (8.6.3.3), OU sur la meme base avec
en plus 8.6.4 a 8.6.4.4 deja appliques (ils seront alors retires).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

LRU_H = """/*
 * Xournal++
 *
 * Undo action for the "line reposition on release" feature (see EditSelection.cpp, patch 8.6.4.5):
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

#include "model/PageRef.h"  // for PageRef

#include "UndoAction.h"  // for UndoAction

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
"""

LRU_CPP = """#include "LineRepositionUndoAction.h"

#include <utility>  // for move

#include "control/Control.h"
#include "model/Document.h"
#include "model/Element.h"  // for Element
#include "model/PageRef.h"  // for PageRef
#include "model/XojPage.h"  // for XojPage
#include "util/Range.h"     // for Range
#include "util/i18n.h"      // for _

LineRepositionUndoAction::LineRepositionUndoAction(const PageRef& page,
                                                    std::vector<std::pair<Element*, double>> elementsWithDelta,
                                                    bool isXAxis):
        UndoAction("LineRepositionUndoAction"), elementsWithDelta(std::move(elementsWithDelta)), isXAxis(isXAxis) {
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

auto LineRepositionUndoAction::getText() -> std::string { return _("Reposition aligned line"); }
"""

OLD_FWD = """// "Half/double on release" (patch 8.6.4) - defined later in this file (after its dependencies
// like THIN_AXIS_THRESHOLD/rangesOverlap/BLUE_GRID_LENGTH_EPS), forward-declared here so
// EditSelection::mouseUp() below can call it.
static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements);
"""
NEW_FWD = """// "Line reposition on release" (patch 8.6.4.5) - defined later in this file (after its
// dependencies like THIN_AXIS_THRESHOLD/rangesOverlap/BLUE_GRID_LENGTH_EPS), forward-declared here
// so EditSelection::mouseUp() below can call it.
static void applyLineRepositionOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements);
"""
OLD_DEF = """/**
 * "Half/double on release" (patch 8.6.4): if the moving line was boost-snapped (blue) to `bigLine`
 * when the drag ended, and it ended in the "negative" or "positive" third of the snap zone (see
 * EditSelection::activeBoostedZone), this halves every same-length-family line crossing `bigLine`
 * (see the detection rule below), anchoring each one to its far edge instead of its center. If it
 * ended in the middle third, and there is a family whose lengths split into a "short" and "long"
 * cluster (long = exactly double short), doubles every line at the short length back to full size,
 * re-centering them. Registers a single LineHalfDoubleUndoAction covering every line actually
 * changed. `isXAxis` says whether the crossing is on the X or Y axis (i.e. whether "family" lines
 * are horizontal or vertical). Only plain lines (no ArrowKind) ever participate - see patch 8.6.3.2.
 *
 * Detection rule: gather every plain-line element crossing `bigLine` the same way a boosted match
 * would (same shaft-based eligibility), and look at their lengths. If they're all the same length,
 * halving applies to everyone. If there are exactly two distinct lengths with one being exactly
 * double the other, halving applies only to the longer ones (the shorter ones are assumed to
 * already be in the halved state) - and, symmetrically, doubling (in the middle zone) applies only
 * to the shorter ones. Any other configuration (more than two distinct lengths, or no exact double
 * ratio) is left untouched.
 */
static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements) {
    if (bigLine == nullptr) {
        return;
    }
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);

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
        if (isXAxis) {
            return rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) &&
                   crossingCoord >= shaft.x && crossingCoord <= shaft.x + shaft.width;
        }
        return rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) &&
               crossingCoord >= shaft.y && crossingCoord <= shaft.y + shaft.height;
    };

    std::vector<Element*> family;
    // The currently-selected element(s) are NOT in `layer->getElements()` while selected (they are
    // physically removed from the layer for the duration of the selection - see
    // createFromElementOnActiveLayer()/createFromElementsOnActiveLayer() - and only reinserted once
    // deselected), so they must be checked separately here, or the moving line itself would never
    // take part in its own family's transformation. getElementsView() only exposes const pointers,
    // but these elements are indeed ours to mutate (they are about to be scaled below).
    for (const Element* el: selfElements) {
        if (isEligibleFamilyMember(el)) {
            family.push_back(const_cast<Element*>(el));
        }
    }
    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (isEligibleFamilyMember(el)) {
            family.push_back(el);
        }
    }
    if (family.empty()) {
        return;
    }

    auto familyLength = [isXAxis](Element* el) {
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        return isXAxis ? shaft.width : shaft.height;
    };

    double minLen = familyLength(family.front());
    double maxLen = minLen;
    for (Element* el: family) {
        double l = familyLength(el);
        minLen = std::min(minLen, l);
        maxLen = std::max(maxLen, l);
    }
    bool uniform = std::abs(maxLen - minLen) < BLUE_GRID_LENGTH_EPS;
    bool doubledPair = std::abs(maxLen - 2 * minLen) < BLUE_GRID_LENGTH_EPS;

    std::vector<Element*> toHalve;
    std::vector<Element*> toDouble;
    if (zone != 0) {
        if (uniform) {
            toHalve = family;
        } else if (doubledPair) {
            for (Element* el: family) {
                if (std::abs(familyLength(el) - maxLen) < BLUE_GRID_LENGTH_EPS) {
                    toHalve.push_back(el);
                }
            }
        }
    } else if (!uniform && doubledPair) {
        for (Element* el: family) {
            if (std::abs(familyLength(el) - minLen) < BLUE_GRID_LENGTH_EPS) {
                toDouble.push_back(el);
            }
        }
    }
    if (toHalve.empty() && toDouble.empty()) {
        return;
    }

    std::vector<std::pair<Element*, Point>> elementsWithOrigin;
    double factor;
    if (!toHalve.empty()) {
        factor = 0.5;
        for (Element* el: toHalve) {
            auto* stroke = dynamic_cast<Stroke*>(el);
            const Point* pts = stroke->getPoints();
            double c0 = isXAxis ? pts[0].x : pts[0].y;
            double c1 = isXAxis ? pts[1].x : pts[1].y;
            // Keep whichever point is farther in the direction the zone points away from the
            // crossing line - the other point moves in to meet the crossing coordinate.
            bool p0IsFar = (zone < 0) ? (c0 < c1) : (c0 > c1);
            elementsWithOrigin.emplace_back(el, p0IsFar ? pts[0] : pts[1]);
        }
    } else {
        factor = 2.0;
        for (Element* el: toDouble) {
            auto* stroke = dynamic_cast<Stroke*>(el);
            const Point* pts = stroke->getPoints();
            double c0 = isXAxis ? pts[0].x : pts[0].y;
            double c1 = isXAxis ? pts[1].x : pts[1].y;
            // The anchor point is whichever one currently sits at the crossing coordinate; scale
            // from it to push the other (far) point back out to double the current distance.
            bool p0IsAnchor = std::abs(c0 - crossingCoord) < std::abs(c1 - crossingCoord);
            elementsWithOrigin.emplace_back(el, p0IsAnchor ? pts[1] : pts[0]);
        }
    }
    if (elementsWithOrigin.empty()) {
        return;
    }

    auto action = std::make_unique<LineHalfDoubleUndoAction>(page, elementsWithOrigin, factor);
    action->redo(control);
    control->getUndoRedoHandler()->addUndoAction(std::move(action));
}

"""
NEW_DEF = """/**
 * "Line reposition on release" (patch 8.6.4.5): if the moving line was boost-snapped (blue) to
 * `bigLine` when the drag ended, every OTHER plain line of the exact same length crossing `bigLine`
 * the same way (see the eligibility rule below) - the moving line included - is translated (never
 * resized) so that the point matching the current zone lands exactly on `bigLine`: its bottom edge
 * for the "negative" zone (e.g. above a horizontal big line), its center for the middle zone, its
 * top edge for the "positive" zone (e.g. below it). `isXAxis` says whether the crossing is on the X
 * or Y axis (i.e. whether "family" lines are horizontal or vertical). Registers a single
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

    // Determine self's own length (the "same length as the moving line" filter) from whichever of
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

    std::vector<Element*> family;
    for (const Element* el: selfElements) {
        if (isEligibleFamilyMember(el)) {
            family.push_back(const_cast<Element*>(el));
        }
    }
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

"""
OLD_CALL = """    // "Half/double on release" (patch 8.6.4) - only for an actual move (not a resize/rotate), and
    // only if a boosted (blue) match was active when the drag ended; activeBoostedTarget could
    // otherwise be a stale leftover from an earlier move gesture during this same selection.
    if (this->mouseDownType == CURSOR_SELECTION_MOVE && this->activeBoostedTarget != nullptr) {
        applyLineHalfDoubleOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,
                                     this->activeBoostedIsXAxis, this->activeBoostedZone,
                                     this->getElementsView().clone());
    }

"""
NEW_CALL = """    // "Line reposition on release" (patch 8.6.4.5) - only for an actual move (not a resize/rotate),
    // and only if a boosted (blue) match was active when the drag ended; activeBoostedTarget could
    // otherwise be a stale leftover from an earlier move gesture during this same selection.
    if (this->mouseDownType == CURSOR_SELECTION_MOVE && this->activeBoostedTarget != nullptr) {
        applyLineRepositionOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,
                                     this->activeBoostedIsXAxis, this->activeBoostedZone,
                                     this->getElementsView().clone());
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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    old_undo_h = Path("src/core/undo/LineHalfDoubleUndoAction.h")
    old_undo_cpp = Path("src/core/undo/LineHalfDoubleUndoAction.cpp")
    new_undo_h = Path("src/core/undo/LineRepositionUndoAction.h")
    new_undo_cpp = Path("src/core/undo/LineRepositionUndoAction.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "computeBlueGridX" not in content:
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord toute la chaine 8.6 a 8.6.3.3, puis relancez ce script.")
        sys.exit(1)
    if "applyLineRepositionOnRelease" in content:
        print("[SKIP] Le patch 8.6.4.5 semble deja applique.")
        sys.exit(0)

    has_old_chain = "applyLineHalfDoubleOnRelease" in content
    print(f"[INFO]  Ancien mecanisme (8.6.4 a 8.6.4.4) detecte : {'oui' if has_old_chain else 'non'}")

    ok = True

    # ============ 1. fichiers d'annulation ============
    if has_old_chain:
        if old_undo_h.exists():
            old_undo_h.unlink()
            print("[OK]    Suppression de src/core/undo/LineHalfDoubleUndoAction.h")
        if old_undo_cpp.exists():
            old_undo_cpp.unlink()
            print("[OK]    Suppression de src/core/undo/LineHalfDoubleUndoAction.cpp")
    if not new_undo_h.exists():
        new_undo_h.write_text(LRU_H, encoding="utf-8")
        print("[OK]    Creation de src/core/undo/LineRepositionUndoAction.h")
    else:
        print("[SKIP]  LineRepositionUndoAction.h existe deja.")
    if not new_undo_cpp.exists():
        new_undo_cpp.write_text(LRU_CPP, encoding="utf-8")
        print("[OK]    Creation de src/core/undo/LineRepositionUndoAction.cpp")
    else:
        print("[SKIP]  LineRepositionUndoAction.cpp existe deja.")
    print("[INFO]  N'oubliez pas de relancer 'cmake ..' (pas seulement cmake --build .) pour que")
    print("        CMake (GLOB_RECURSE) detecte les fichiers.")

    if has_old_chain:
        # ============ 2a. include: remplacement ============
        ok &= apply_edit(
            cpp,
            old='#include "undo/LineHalfDoubleUndoAction.h"        // for LineHalfDoubleUndoAction',
            new='#include "undo/LineRepositionUndoAction.h"        // for LineRepositionUndoAction',
            label="EditSelection.cpp: remplacement de l'include",
        )
        # ============ 2b. declaration anticipee: remplacement ============
        ok &= apply_edit(cpp, OLD_FWD, NEW_FWD, "EditSelection.cpp: remplacement de la declaration anticipee")
        # ============ 2c. definition complete: remplacement ============
        ok &= apply_edit(cpp, OLD_DEF, NEW_DEF, "EditSelection.cpp: remplacement de la fonction complete")
        # ============ 2d. appel dans mouseUp(): remplacement ============
        ok &= apply_edit(cpp, OLD_CALL, NEW_CALL, "EditSelection.cpp: remplacement de l'appel dans mouseUp()")
        # Revert the marker-truncation code the old mechanism added to paint() - the new mechanism
        # never resizes anything, so the blue grid markers should always show at full length.
        ok &= apply_edit(
            cpp,
            old="            if (marker.isVertical) {\n"
                "                double topY = (this->activeBoostedZone > 0) ? my : my - half;\n"
                "                double bottomY = (this->activeBoostedZone < 0) ? my : my + half;\n"
                "                cairo_move_to(cr, mx, topY);\n"
                "                cairo_line_to(cr, mx, bottomY);\n"
                "            } else {\n"
                "                double leftX = (this->activeBoostedZone > 0) ? mx : mx - half;\n"
                "                double rightX = (this->activeBoostedZone < 0) ? mx : mx + half;\n"
                "                cairo_move_to(cr, leftX, my);\n"
                "                cairo_line_to(cr, rightX, my);\n",
            new="            if (marker.isVertical) {\n"
                "                cairo_move_to(cr, mx, my - half);\n"
                "                cairo_line_to(cr, mx, my + half);\n"
                "            } else {\n"
                "                cairo_move_to(cr, mx - half, my);\n"
                "                cairo_line_to(cr, mx + half, my);\n",
            label="EditSelection.cpp: retrait de la troncature des reperes (taille reelle desormais)",
        )
    else:
        # ============ base fraiche (8.6.3.3 uniquement) : tout ajouter depuis zero ============
        ok &= apply_edit(
            cpp,
            old='#include "undo/ArrangeUndoAction.h"               // for ArrangeUndoAction',
            new='#include "undo/ArrangeUndoAction.h"               // for ArrangeUndoAction\n'
                '#include "undo/LineRepositionUndoAction.h"        // for LineRepositionUndoAction',
            label="EditSelection.cpp: ajout de l'include",
        )
        ok &= apply_edit(
            cpp,
            old="void EditSelection::mouseUp() {",
            new=NEW_FWD + "\n\nvoid EditSelection::mouseUp() {",
            label="EditSelection.cpp: ajout de la declaration anticipee",
        )
        content = cpp.read_text(encoding="utf-8")
        anchor_def = "static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"
        if content.count(anchor_def) != 1:
            print(f"[ECHEC] EditSelection.cpp: ancre findAlignmentY trouvee {content.count(anchor_def)} fois (attendu 1).")
            ok = False
        else:
            idx = content.find(anchor_def)
            content = content[:idx] + NEW_DEF.lstrip("\n") + "\n\n" + content[idx:]
            cpp.write_text(content, encoding="utf-8")
            print("[OK]    EditSelection.cpp: ajout de applyLineRepositionOnRelease()")

        old_zone_anchor = (
            "                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;\n"
            "                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;\n"
            "                this->activeBlueGridMarkers.clear();\n"
        )
        new_zone_block = (
            "                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;\n"
            "                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;\n\n"
            "                // \"Line reposition on release\" (see EditSelection::mouseUp(), patch 8.6.4.5): tracks\n"
            "                // which third of the boosted snap zone the moving line currently sits in (-1 = the\n"
            "                // \"negative\" side, e.g. above a horizontal big line; 0 = middle; +1 = the \"positive\"\n"
            "                // side, e.g. below it), purely for live visual feedback (truncating the blue grid\n"
            "                // markers below) and for EditSelection::mouseUp() to read once the drag ends.\n"
            "                this->activeBoostedTarget = nullptr;\n"
            "                this->activeBoostedIsXAxis = false;\n"
            "                this->activeBoostedZone = 0;\n"
            "                if (yBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.y + targetShaft.height / 2;\n"
            "                    double signedOffset = selfAnchorY - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = yBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = false;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                } else if (xBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.x + targetShaft.width / 2;\n"
            "                    double signedOffset = selfAnchorX - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = xBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = true;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                }\n"
            "                this->activeBlueGridMarkers.clear();\n"
        )
        ok &= apply_edit(cpp, old_zone_anchor, new_zone_block, "EditSelection.cpp: ajout du calcul de zone")

        ok &= apply_edit(
            cpp,
            old="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 2.25;",
            new="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0;",
            label="EditSelection.cpp: PERPENDICULAR_CROSS_BOOST_FACTOR 2.25 -> 4.0",
        )

        old_arrow_block = (
            "                {\n"
            "                    auto selfElementsForArrowCheck = this->getElementsView();\n"
            "                    if (selfElementsForArrowCheck.size() == 1) {\n"
            "                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForArrowCheck.begin())) {\n"
            "                            if (selfStroke->getArrowKind() != ArrowKind::NONE) {\n"
            "                                if (matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted) {\n"
            "                                    matchX = std::nullopt;\n"
            "                                }\n"
            "                                if (matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted) {\n"
            "                                    matchY = std::nullopt;\n"
            "                                }\n"
            "                            }\n"
            "                        }\n"
            "                    }\n"
            "                }\n\n\n"
            "                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on\n"
            "                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.\n"
            "                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n"
        )
        new_arrow_and_virtual_block = (
            "                {\n"
            "                    auto selfElementsForArrowCheck = this->getElementsView();\n"
            "                    if (selfElementsForArrowCheck.size() == 1) {\n"
            "                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForArrowCheck.begin())) {\n"
            "                            if (selfStroke->getArrowKind() != ArrowKind::NONE) {\n"
            "                                if (matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted) {\n"
            "                                    matchX = std::nullopt;\n"
            "                                }\n"
            "                                if (matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted) {\n"
            "                                    matchY = std::nullopt;\n"
            "                                }\n"
            "                            }\n"
            "                        }\n"
            "                    }\n"
            "                }\n\n"
            "                // \"Already repositioned\" self detection (patch 8.6.4.5): if self doesn\'t already have\n"
            "                // a boosted match using its own true center, try treating each of its own edges as a\n"
            "                // \"virtual center\" instead (by searching with a same-size box centered on that edge) -\n"
            "                // this lets a line that was previously moved to Top/Below by this same feature (now\n"
            "                // anchored at one edge rather than truly centered) still find and reconnect to the big\n"
            "                // line it came from. Whichever of the three (real center, virtual near-edge center,\n"
            "                // virtual far-edge center) gives the closest boosted match wins; offsets are translated\n"
            "                // back to the real candidateX/candidateY frame before use. Arrows are excluded here\n"
            "                // too, matching the \"only plain lines\" scope of the whole feature.\n"
            "                //\n"
            "                // selfAnchorY/selfAnchorX track which point should stand in for \"self\'s position\" when\n"
            "                // computing the Top/Middle/Below zone further below: self\'s true center by default, or\n"
            "                // whichever edge just won a virtual match above (the point actually touching the big\n"
            "                // line right now).\n"
            "                double selfAnchorY = candidateY + height / 2;\n"
            "                double selfAnchorX = candidateX + width / 2;\n"
            "                {\n"
            "                    bool selfIsArrowForVirtualCheck = false;\n"
            "                    auto selfElementsForVirtualCheck = this->getElementsView();\n"
            "                    if (selfElementsForVirtualCheck.size() == 1) {\n"
            "                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForVirtualCheck.begin())) {\n"
            "                            selfIsArrowForVirtualCheck = selfStroke->getArrowKind() != ArrowKind::NONE;\n"
            "                        }\n"
            "                    }\n"
            "                    if (!selfIsArrowForVirtualCheck) {\n"
            "                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n"
            "                        if (!matchYAlreadyBoosted) {\n"
            "                            auto matchYVirtualTop =\n"
            "                                    findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,\n"
            "                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n"
            "                            auto matchYVirtualBottom =\n"
            "                                    findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,\n"
            "                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n"
            "                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&\n"
            "                                                 matchYVirtualTop->guides.front().isBoosted;\n"
            "                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&\n"
            "                                                    matchYVirtualBottom->guides.front().isBoosted;\n"
            "                            std::optional<double> bestRealOffsetY;\n"
            "                            if (topIsBoosted) {\n"
            "                                double realOffset = matchYVirtualTop->offset - height / 2;\n"
            "                                bestRealOffsetY = realOffset;\n"
            "                                matchY = AlignmentSearchResult{realOffset, matchYVirtualTop->guides};\n"
            "                                selfAnchorY = candidateY;  // the top edge (raw, pre-snap, like the default case)\n"
            "                            }\n"
            "                            if (bottomIsBoosted) {\n"
            "                                double realOffset = matchYVirtualBottom->offset + height / 2;\n"
            "                                if (!bestRealOffsetY || std::abs(realOffset) < std::abs(*bestRealOffsetY)) {\n"
            "                                    matchY = AlignmentSearchResult{realOffset, matchYVirtualBottom->guides};\n"
            "                                    selfAnchorY = candidateY + height;  // the bottom edge (raw, pre-snap)\n"
            "                                }\n"
            "                            }\n"
            "                        }\n"
            "                        bool matchXAlreadyBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                        if (!matchXAlreadyBoosted) {\n"
            "                            auto matchXVirtualLeft =\n"
            "                                    findAlignmentX(candidateX - width / 2, width, candidateY, candidateY + height,\n"
            "                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n"
            "                            auto matchXVirtualRight =\n"
            "                                    findAlignmentX(candidateX + width / 2, width, candidateY, candidateY + height,\n"
            "                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n"
            "                            bool leftIsBoosted = matchXVirtualLeft && !matchXVirtualLeft->guides.empty() &&\n"
            "                                                  matchXVirtualLeft->guides.front().isBoosted;\n"
            "                            bool rightIsBoosted = matchXVirtualRight && !matchXVirtualRight->guides.empty() &&\n"
            "                                                   matchXVirtualRight->guides.front().isBoosted;\n"
            "                            std::optional<double> bestRealOffsetX;\n"
            "                            if (leftIsBoosted) {\n"
            "                                double realOffset = matchXVirtualLeft->offset - width / 2;\n"
            "                                bestRealOffsetX = realOffset;\n"
            "                                matchX = AlignmentSearchResult{realOffset, matchXVirtualLeft->guides};\n"
            "                                selfAnchorX = candidateX;  // the left edge (raw, pre-snap, like the default case)\n"
            "                            }\n"
            "                            if (rightIsBoosted) {\n"
            "                                double realOffset = matchXVirtualRight->offset + width / 2;\n"
            "                                if (!bestRealOffsetX || std::abs(realOffset) < std::abs(*bestRealOffsetX)) {\n"
            "                                    matchX = AlignmentSearchResult{realOffset, matchXVirtualRight->guides};\n"
            "                                    selfAnchorX = candidateX + width;  // the right edge (raw, pre-snap)\n"
            "                                }\n"
            "                            }\n"
            "                        }\n"
            "                    }\n"
            "                }\n\n\n"
            "                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on\n"
            "                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.\n"
            "                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n"
        )
        ok &= apply_edit(cpp, old_arrow_block, new_arrow_and_virtual_block,
                          "EditSelection.cpp: ajout de la detection 'deja repositionne' (point 3)")

        h_path = Path("src/core/control/tools/EditSelection.h")
        ok &= apply_edit(
            h_path,
            old="    std::vector<BlueGridMarker> activeBlueGridMarkers;\n",
            new="    std::vector<BlueGridMarker> activeBlueGridMarkers;\n\n"
                "    /// The \"big line\" element the moving object is currently boost-snapped to, or nullptr if not\n"
                "    /// currently boosted - set during mouseMove(), read by mouseUp() for the \"line reposition on\n"
                "    /// release\" feature (see patch 8.6.4.5) and by paint() to truncate the blue grid markers.\n"
                "    const Element* activeBoostedTarget = nullptr;\n"
                "    /// True if activeBoostedTarget\'s crossing is on the X axis (self horizontal, big line vertical),\n"
                "    /// false if on Y. Only meaningful when activeBoostedTarget is not nullptr.\n"
                "    bool activeBoostedIsXAxis = false;\n"
                "    /// Which third of the boosted snap zone the moving line currently sits in: -1 for the \"negative\"\n"
                "    /// side (e.g. above a horizontal big line), 0 for the middle third, +1 for the \"positive\" side\n"
                "    /// (e.g. below it). Only meaningful when activeBoostedTarget is not nullptr.\n"
                "    int activeBoostedZone = 0;\n",
            label="EditSelection.h: nouveaux membres",
        )
        h = Path("src/core/control/tools/EditSelection.h")
        # (edit applied to cpp above targeted the wrong file variable name; fix below)
    if not has_old_chain:
        ok &= apply_edit(
            cpp,
            old="    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,\n"
                "                                  layer, page, this->undo, this->mouseDownType);\n\n"
                "    this->mouseDownType = CURSOR_SELECTION_NONE;\n"
                "    this->activeGuidesX.clear();\n"
                "    this->activeGuidesY.clear();\n"
                "    this->activeBlueGridMarkers.clear();\n",
            new="    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,\n"
                "                                  layer, page, this->undo, this->mouseDownType);\n\n"
                + NEW_CALL +
                "\n    this->mouseDownType = CURSOR_SELECTION_NONE;\n"
                "    this->activeGuidesX.clear();\n"
                "    this->activeGuidesY.clear();\n"
                "    this->activeBlueGridMarkers.clear();\n"
                "    this->activeBoostedTarget = nullptr;\n",
            label="EditSelection.cpp: ajout de l'appel dans mouseUp()",
        )
        ok &= apply_edit(
            cpp,
            old="        } else {\n"
                "            this->activeGuidesX.clear();\n"
                "            this->activeGuidesY.clear();\n"
                "            this->activeBlueGridMarkers.clear();\n"
                "        }",
            new="        } else {\n"
                "            this->activeGuidesX.clear();\n"
                "            this->activeGuidesY.clear();\n"
                "            this->activeBlueGridMarkers.clear();\n"
                "            this->activeBoostedTarget = nullptr;\n"
                "        }",
            label="EditSelection.cpp: nettoyage dans la branche else externe",
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
