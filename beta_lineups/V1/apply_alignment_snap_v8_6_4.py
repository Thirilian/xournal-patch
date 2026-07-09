#!/usr/bin/env python3
"""
Patch 8.6.4 (depend de 8.6 + 8.6.2 + 8.6.3 + 8.6.3.2 + 8.6.3.3) : "demi-
longueur / double-longueur au relachement" pour le palier bleu.

1) PERPENDICULAR_CROSS_BOOST_FACTOR : 2.25 -> 4.0.

2) Pendant le glissement d'un petit trait deja boost-snappe (bleu) a une
   grande ligne perpendiculaire, la zone de snap est divisee en trois
   tiers (via R = tolerance * 4.0) : negatif (< -R/3), milieu, positif
   (> +R/3). Les reperes de la grille bleue (patch 8.6) sont affiches
   tronques a leur moitie correspondante quand on est hors du tiers du
   milieu (purement visuel, aucune modification du document pendant le
   glissement - le trait continue de s'accrocher normalement en son
   centre).

3) Au relachement du clic, si la zone finale est negative ou positive :
   tous les traits de meme taille (ou de longueur double, s'ils
   rejoignent un groupe deja reduit) deja accroches sur cette meme grande
   ligne sont reellement coupes en deux, leur nouveau point d'ancrage
   devenant leur bord le plus proche de la grande ligne. Si la zone
   finale est le milieu et qu'un groupe reduit existe (longueur courte +
   longueur double exacte), les traits courts doublent de longueur,
   retrouvant un ancrage centre. Action annulable (nouvelle classe
   LineHalfDoubleUndoAction).

Seules les lignes simples (pas les fleches) participent - voir le patch
8.6.3.2, qui les exclut deja entierement du palier bleu.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

LHD_HEADER = """/*
 * Xournal++
 *
 * Undo action for the "blue grid" half/double resize on release (see EditSelection.cpp, patch 8.6.4):
 * applies a fixed scale factor to a set of elements, each around its own individual origin point (the
 * edge that stays fixed - the one touching the big line), rather than one shared origin the way
 * ScaleUndoAction does. Used both to halve a line (factor 0.5, keeping the far edge fixed relative to
 * the crossing point) and to double it back (factor 2.0).
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
#include "model/Point.h"    // for Point

#include "UndoAction.h"  // for UndoAction

class Control;
class Document;
class Element;

class LineHalfDoubleUndoAction: public UndoAction {
public:
    LineHalfDoubleUndoAction(const PageRef& page, std::vector<std::pair<Element*, Point>> elementsWithOrigin,
                              double factor);
    ~LineHalfDoubleUndoAction() override;

public:
    bool undo(Control* control) override;
    bool redo(Control* control) override;
    std::string getText() override;

private:
    void apply(double factor, Document* doc);

private:
    std::vector<std::pair<Element*, Point>> elementsWithOrigin;
    double factor;
};
"""

LHD_CPP = """#include "LineHalfDoubleUndoAction.h"

#include <memory>  // for allocator, __shared_ptr_access, __share...
#include <utility> // for move

#include "control/Control.h"
#include "model/Document.h"
#include "model/Element.h"    // for Element
#include "model/PageRef.h"    // for PageRef
#include "model/XojPage.h"    // for XojPage
#include "undo/UndoAction.h"  // for UndoAction
#include "util/Range.h"       // for Range
#include "util/i18n.h"        // for _

LineHalfDoubleUndoAction::LineHalfDoubleUndoAction(const PageRef& page,
                                                    std::vector<std::pair<Element*, Point>> elementsWithOrigin,
                                                    double factor):
        UndoAction("LineHalfDoubleUndoAction"), elementsWithOrigin(std::move(elementsWithOrigin)), factor(factor) {
    this->page = page;
}

LineHalfDoubleUndoAction::~LineHalfDoubleUndoAction() { this->page = nullptr; }

auto LineHalfDoubleUndoAction::undo(Control* control) -> bool {
    apply(1.0 / this->factor, control->getDocument());
    this->undone = true;
    return true;
}

auto LineHalfDoubleUndoAction::redo(Control* control) -> bool {
    apply(this->factor, control->getDocument());
    this->undone = false;
    return true;
}

void LineHalfDoubleUndoAction::apply(double f, Document* doc) {
    if (this->elementsWithOrigin.empty()) {
        return;
    }

    doc->lock();
    Range r(elementsWithOrigin.front().first->getX(), elementsWithOrigin.front().first->getY());

    for (auto& [element, origin]: this->elementsWithOrigin) {
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
        element->scale(origin.x, origin.y, f, f, 0, false);
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
    }
    doc->unlock();

    this->page->fireRangeChanged(r);
}

auto LineHalfDoubleUndoAction::getText() -> std::string { return _("Resize aligned line"); }
"""

HELPER_BLOCK = """/**
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
                                          const Element* bigLine, bool isXAxis, int zone) {
    if (bigLine == nullptr) {
        return;
    }
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);

    std::vector<Element*> family;
    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (el == bigLine) {
            continue;
        }
        auto* stroke = dynamic_cast<Stroke*>(el);
        if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool matchesOrientation = isXAxis ? (shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD)
                                           : (shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD);
        if (!matchesOrientation) {
            continue;
        }
        if (isXAxis) {
            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) ||
                crossingCoord < shaft.x || crossingCoord > shaft.x + shaft.width) {
                continue;
            }
        } else {
            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) ||
                crossingCoord < shaft.y || crossingCoord > shaft.y + shaft.height) {
                continue;
            }
        }
        family.push_back(el);
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
    h = Path("src/core/control/tools/EditSelection.h")
    undo_h = Path("src/core/undo/LineHalfDoubleUndoAction.h")
    undo_cpp = Path("src/core/undo/LineHalfDoubleUndoAction.cpp")
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "computeBlueGridX" not in content:
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord toute la chaine 8.6 (v8_6 a v8_6_3_3), puis relancez ce script.")
        sys.exit(1)
    if "applyLineHalfDoubleOnRelease" in content:
        print("[SKIP] Le patch 8.6.4 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. nouveaux fichiers d'annulation ============
    if not undo_h.exists():
        undo_h.write_text(LHD_HEADER, encoding="utf-8")
        print("[OK]    Creation de src/core/undo/LineHalfDoubleUndoAction.h")
    else:
        print("[SKIP]  LineHalfDoubleUndoAction.h existe deja.")
    if not undo_cpp.exists():
        undo_cpp.write_text(LHD_CPP, encoding="utf-8")
        print("[OK]    Creation de src/core/undo/LineHalfDoubleUndoAction.cpp")
    else:
        print("[SKIP]  LineHalfDoubleUndoAction.cpp existe deja.")
    print("[INFO]  N'oubliez pas de relancer \'cmake ..\' (pas seulement cmake --build .) pour que")
    print("        CMake (GLOB_RECURSE) detecte ces nouveaux fichiers.")

    # ============ 2. augmentation du boost (point 1) ============
    ok &= apply_edit(
        cpp,
        old="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 2.25;",
        new="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0;",
        label="EditSelection.cpp: PERPENDICULAR_CROSS_BOOST_FACTOR 2.25 -> 4.0",
    )

    # ============ 3. includes ============
    ok &= apply_edit(
        cpp,
        old="#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction\n"
            "#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction\n"
            "#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler",
        new="#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction\n"
            "#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction\n"
            "#include \"undo/LineHalfDoubleUndoAction.h\"        // for LineHalfDoubleUndoAction\n"
            "#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler",
        label="EditSelection.cpp: include LineHalfDoubleUndoAction.h",
    )

    # ============ 4. EditSelection.h: nouveaux membres ============
    ok &= apply_edit(
        h,
        old="    std::vector<BlueGridMarker> activeBlueGridMarkers;\n",
        new="    std::vector<BlueGridMarker> activeBlueGridMarkers;\n\n"
            "    /// The \"big line\" element the moving object is currently boost-snapped to, or nullptr if not\n"
            "    /// currently boosted - set during mouseMove(), read by mouseUp() for the \"half/double on\n"
            "    /// release\" feature (see patch 8.6.4) and by paint() to truncate the blue grid markers.\n"
            "    const Element* activeBoostedTarget = nullptr;\n"
            "    /// True if activeBoostedTarget\'s crossing is on the X axis (self horizontal, big line vertical),\n"
            "    /// false if on Y. Only meaningful when activeBoostedTarget is not nullptr.\n"
            "    bool activeBoostedIsXAxis = false;\n"
            "    /// Which third of the boosted snap zone the moving line currently sits in: -1 for the \"negative\"\n"
            "    /// side (e.g. above a horizontal big line), 0 for the middle third, +1 for the \"positive\" side\n"
            "    /// (e.g. below it). Only meaningful when activeBoostedTarget is not nullptr.\n"
            "    int activeBoostedZone = 0;\n",
        label="EditSelection.h: nouveaux membres activeBoostedTarget/IsXAxis/Zone",
    )

    # ============ 5. mouseMove(): calcul de la zone, ancre robuste ============
    ok &= apply_edit(
        cpp,
        old="                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;\n"
            "                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;\n",
        new="                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;\n"
            "                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;\n\n"
            "                // \"Half/double on release\" (see EditSelection::mouseUp(), patch 8.6.4): tracks which\n"
            "                // third of the boosted snap zone the moving line currently sits in (-1 = the \"negative\"\n"
            "                // side, e.g. above a horizontal big line; 0 = middle; +1 = the \"positive\" side, e.g.\n"
            "                // below it), purely for live visual feedback (truncating the blue grid markers below)\n"
            "                // and for EditSelection::mouseUp() to read once the drag ends.\n"
            "                this->activeBoostedTarget = nullptr;\n"
            "                this->activeBoostedIsXAxis = false;\n"
            "                this->activeBoostedZone = 0;\n"
            "                if (yBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.y + targetShaft.height / 2;\n"
            "                    double signedOffset = (candidateY + height / 2) - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = yBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = false;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                } else if (xBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.x + targetShaft.width / 2;\n"
            "                    double signedOffset = (candidateX + width / 2) - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = xBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = true;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                }\n",
        label="EditSelection.cpp: mouseMove() calcule la zone (patch 8.6.4)",
    )

    # ============ 6. paint(): troncature des reperes de la grille bleue ============
    ok &= apply_edit(
        cpp,
        old="        for (auto& marker: this->activeBlueGridMarkers) {\n"
            "            double mx = marker.x * zoom;\n"
            "            double my = marker.y * zoom;\n"
            "            double half = marker.halfLength * zoom;\n"
            "            if (marker.isVertical) {\n"
            "                cairo_move_to(cr, mx, my - half);\n"
            "                cairo_line_to(cr, mx, my + half);\n"
            "            } else {\n"
            "                cairo_move_to(cr, mx - half, my);\n"
            "                cairo_line_to(cr, mx + half, my);\n"
            "            }\n"
            "            cairo_stroke(cr);\n"
            "        }\n",
        new="        for (auto& marker: this->activeBlueGridMarkers) {\n"
            "            double mx = marker.x * zoom;\n"
            "            double my = marker.y * zoom;\n"
            "            double half = marker.halfLength * zoom;\n"
            "            if (marker.isVertical) {\n"
            "                double topY = (this->activeBoostedZone > 0) ? my : my - half;\n"
            "                double bottomY = (this->activeBoostedZone < 0) ? my : my + half;\n"
            "                cairo_move_to(cr, mx, topY);\n"
            "                cairo_line_to(cr, mx, bottomY);\n"
            "            } else {\n"
            "                double leftX = (this->activeBoostedZone > 0) ? mx : mx - half;\n"
            "                double rightX = (this->activeBoostedZone < 0) ? mx : mx + half;\n"
            "                cairo_move_to(cr, leftX, my);\n"
            "                cairo_line_to(cr, rightX, my);\n"
            "            }\n"
            "            cairo_stroke(cr);\n"
            "        }\n",
        label="EditSelection.cpp: paint() tronque les reperes selon la zone",
    )

    # ============ 7. gros bloc: applyLineHalfDoubleOnRelease(), insere avant mouseUp() ============
    anchor7 = "void EditSelection::mouseUp() {"
    text = cpp.read_text(encoding="utf-8")
    if "applyLineHalfDoubleOnRelease" in text:
        print("[SKIP]  EditSelection.cpp: applyLineHalfDoubleOnRelease deja presente.")
    elif text.count(anchor7) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre mouseUp() trouvee {text.count(anchor7)} fois (attendu 1).")
        ok = False
    else:
        idx = text.find(anchor7)
        text = text[:idx] + HELPER_BLOCK + text[idx:]
        cpp.write_text(text, encoding="utf-8")
        print("[OK]    EditSelection.cpp: ajout de applyLineHalfDoubleOnRelease()")

    # ============ 8. mouseUp(): appel + nettoyage ============
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
            "    // \"Half/double on release\" (patch 8.6.4) - only for an actual move (not a resize/rotate), and\n"
            "    // only if a boosted (blue) match was active when the drag ended; activeBoostedTarget could\n"
            "    // otherwise be a stale leftover from an earlier move gesture during this same selection.\n"
            "    if (this->mouseDownType == CURSOR_SELECTION_MOVE && this->activeBoostedTarget != nullptr) {\n"
            "        applyLineHalfDoubleOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,\n"
            "                                     this->activeBoostedIsXAxis, this->activeBoostedZone);\n"
            "    }\n\n"
            "    this->mouseDownType = CURSOR_SELECTION_NONE;\n"
            "    this->activeGuidesX.clear();\n"
            "    this->activeGuidesY.clear();\n"
            "    this->activeBlueGridMarkers.clear();\n"
            "    this->activeBoostedTarget = nullptr;\n",
        label="EditSelection.cpp: mouseUp() appelle applyLineHalfDoubleOnRelease()",
    )

    # ============ 9. nettoyage dans la branche else externe ============
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
