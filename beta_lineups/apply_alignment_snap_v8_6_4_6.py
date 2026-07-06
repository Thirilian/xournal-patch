#!/usr/bin/env python3
"""
Patch 8.6.4.6 (depend de 8.6.4.5) : corrige la mise a jour des reperes de
la grille bleue et rend le trait selectionne coherent avec elle.

1) Zone de depart : au moment ou on clique sur un trait deja accroche
   (mouseDown), on determine dans quelle zone (Top/Middle/Below) il se
   trouve DEJA (via computeStartingZone(), meme logique que la detection
   "deja repositionne" utilisee pendant le glissement). Stockee dans le
   nouveau membre startingBoostedZone.

2) Les reperes de la grille bleue sont maintenant DEPLACES (pas
   tronques) d'une quantite = (zone actuelle - zone de depart) x
   (longueur/2) le long de leur propre axe, reproduisant exactement les
   5 cas donnes : Middle->Top (-l/2), Top->Middle (+l/2), Middle->Below
   (+l/2), Below->Top (-l), Top->Below (+l) - en convention Y-bas.

3) Le trait selectionne lui-meme s'accroche desormais dynamiquement selon
   la zone courante (bord bas pour Top, centre pour Middle, bord haut
   pour Below), au lieu de toujours s'accrocher par son centre - il
   "suit" donc visuellement la grille pendant l'apercu.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  5) apply_alignment_snap_v8_6_4_5.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_MOUSEDOWN = """void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is not modified
    this->relMousePosX = x / zoom - this->snappedBounds.x;
    this->relMousePosY = y / zoom - this->snappedBounds.y;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is rotated to make bounding
    // box edges horizontal/vertical
    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;
}"""
NEW_MOUSEDOWN = """// "Starting zone" detection (patch 8.6.4.6) - defined later in this file (after its dependencies
// like THIN_AXIS_THRESHOLD/rangesOverlap and findAlignmentX/Y themselves), forward-declared here so
// EditSelection::mouseDown() below can call it.
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance);

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is not modified
    this->relMousePosX = x / zoom - this->snappedBounds.x;
    this->relMousePosY = y / zoom - this->snappedBounds.y;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is rotated to make bounding
    // box edges horizontal/vertical
    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;

    // "Blue grid" starting zone (patch 8.6.4.6): capture, once at the start of this drag, which zone
    // self was already in (Middle if not boosted at all) - see computeStartingZone(). Used later in
    // mouseMove()/paint() to shift the whole grid preview by the right amount as the zone changes.
    this->startingBoostedZone = 0;
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
                                         visibleRectForStart, toleranceForStart);
        }
    }
}"""
OLD_ZONE = """                if (yBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);
                } else if (xBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);
                }
"""
NEW_ZONE = """                if (yBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever
                    // reference point matches the CURRENT zone (bottom edge for -1, center for 0, top
                    // edge for +1), not always its true center - so self visually moves together with
                    // the "family" grid preview as the zone changes mid-drag. Guides are left as-is
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
                } else if (xBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    double refPointX;
                    if (this->activeBoostedZone < 0) {
                        refPointX = candidateX + width;
                    } else if (this->activeBoostedZone > 0) {
                        refPointX = candidateX;
                    } else {
                        refPointX = candidateX + width / 2;
                    }
                    matchX->offset = targetCenter - refPointX;
                }
"""
OLD_MARKER = """        for (auto& marker: this->activeBlueGridMarkers) {
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
        }
"""
NEW_MARKER = """        // Shift the whole grid preview along its own axis based on how the CURRENT zone differs from
        // the STARTING zone (the one self was already in when this drag began - see
        // EditSelection::mouseDown()/computeStartingZone()): delta = (current - starting) * halfLength,
        // per line. This matches, for example, Middle -> Top shifting everything by -halfLength (half
        // the line's own length, toward the "negative" direction), and Below -> Top by a full length.
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
        }
"""
NEW_CSZ = """/**
 * "Starting zone" detection (patch 8.6.4.6): mirrors the "already repositioned" virtual-center trick
 * used during dragging (see EditSelection::mouseMove()), but applied ONCE, at the very start of a
 * drag (see EditSelection::mouseDown()), to self's own pre-drag geometry [x, y, width, height]. Tries
 * self's true center first (Middle, zone 0), then each of its own edges as a virtual center: if
 * self's own top edge is the one actually touching a big line (i.e. self extends downward from it),
 * that's the "Below" zone (+1); if self's own bottom edge is the anchor (self extends upward), that's
 * the "Top" zone (-1). Checks both axes (Y first, then X). Returns 0 (Middle) if self isn't currently
 * boosted at all.
 */
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance) {
    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {
        return 0;
    }
    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {
        return 1;  // top edge is the anchor -> self extends downward -> "Below"
    }
    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);
    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {
        return -1;  // bottom edge is the anchor -> self extends upward -> "Top"
    }

    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXReal && !matchXReal->guides.empty() && matchXReal->guides.front().isBoosted) {
        return 0;
    }
    auto matchXLeft = findAlignmentX(x - width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXLeft && !matchXLeft->guides.empty() && matchXLeft->guides.front().isBoosted) {
        return 1;
    }
    auto matchXRight = findAlignmentX(x + width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);
    if (matchXRight && !matchXRight->guides.empty() && matchXRight->guides.front().isBoosted) {
        return -1;
    }
    return 0;
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
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "applyLineRepositionOnRelease" not in content:
        print("[ECHEC] applyLineRepositionOnRelease introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_4_5.py, puis relancez ce script.")
        sys.exit(1)
    if "computeStartingZone" in content:
        print("[SKIP] Le patch 8.6.4.6 semble deja applique.")
        sys.exit(0)

    ok = True

    ok &= apply_edit(cpp, OLD_MOUSEDOWN, NEW_MOUSEDOWN, "EditSelection.cpp: mouseDown() calcule la zone de depart")
    ok &= apply_edit(cpp, OLD_ZONE, NEW_ZONE, "EditSelection.cpp: ancrage dynamique du trait selectionne")
    ok &= apply_edit(cpp, OLD_MARKER, NEW_MARKER, "EditSelection.cpp: deplacement (au lieu de troncature) des reperes")

    # gros bloc: computeStartingZone(), insere juste avant mouseMove()
    text = cpp.read_text(encoding="utf-8")
    anchor = "\nvoid EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {"
    if "static int computeStartingZone(double x, double y, double width, double height, Layer* layer,\n                                const std::vector<const Element*>& excluded,\n                                const xoj::util::Rectangle<double>& visibleRect, double tolerance) {" in text:
        print("[SKIP]  EditSelection.cpp: computeStartingZone() (definition complete) deja presente.")
    elif text.count(anchor) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre mouseMove trouvee {text.count(anchor)} fois (attendu 1).")
        ok = False
    else:
        idx = text.find(anchor)
        text = text[:idx] + NEW_CSZ + text[idx:]
        cpp.write_text(text, encoding="utf-8")
        print("[OK]    EditSelection.cpp: ajout de la definition complete de computeStartingZone()")

    # EditSelection.h: nouveau membre
    ok &= apply_edit(
        h,
        old="    int activeBoostedZone = 0;\n",
        new="    int activeBoostedZone = 0;\n"
            "    /// The zone (see activeBoostedZone) self was already in when the current drag started - computed\n"
            "    /// once in mouseDown() via computeStartingZone(). Used to shift the whole \"blue grid\" preview by\n"
            "    /// the right amount as the zone changes mid-drag (patch 8.6.4.6).\n"
            "    int startingBoostedZone = 0;\n",
        label="EditSelection.h: nouveau membre startingBoostedZone",
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
