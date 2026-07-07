#!/usr/bin/env python3
"""
Patch 8.6.6 (depend de 8.6.5) : trois corrections.

1) Nouveau facteur dedie LINE_END_ANCHOR_TOLERANCE_FACTOR = 0.9 (au lieu
   de reutiliser PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0) pour la force de
   snapping aux DEUX EXTREMITES de la grande ligne (patch 8.6.5) - modifiable
   directement dans EditSelection.cpp si besoin.

2) Le repere bleu affiche sur la petite ligne quand elle est snappee a une
   extremite ne suit plus la position brute de la souris : il utilise
   desormais la position DEJA accrochee (candidateY + matchY->offset, ou
   l'equivalent en X), donc il reste parfaitement fixe tant qu'on ne
   change pas de zone.

3) Une petite ligne qui n'etait PAS deja accrochee a une grande ligne au
   moment du clic (mouseDown) ne peut plus basculer en mode Top/Below
   simplement parce qu'on la fait glisser dans cette zone : elle reste en
   mode Middle par defaut, SAUF si d'autres lignes de meme taille et
   orientation sont deja etablies sur cette grande ligne, auquel cas elle
   adopte directement leur mode. Une ligne DEJA accrochee (a n'importe
   quelle grande ligne) au moment du clic garde la transition libre entre
   zones, comme avant.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  4) apply_alignment_snap_v8_6_4_5.py + v8_6_4_6.py
  5) apply_alignment_snap_v8_6_5.py

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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    h = Path("src/core/control/tools/EditSelection.h")
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "endpointGuideActiveX" not in content:
        print("[ECHEC] endpointGuideActiveX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_5.py, puis relancez ce script.")
        sys.exit(1)
    if "LINE_END_ANCHOR_TOLERANCE_FACTOR" in content:
        print("[SKIP] Le patch 8.6.6 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ Correction 1a: nouveau facteur dedie ============
    ok &= apply_edit(
        cpp,
        old="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0;\n",
        new="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 4.0;\n"
            "/// Tolerance factor for snapping a small line to one of the big line's own two endpoints (patch\n"
            "/// 8.6.5) - deliberately much smaller than PERPENDICULAR_CROSS_BOOST_FACTOR, since this snap is a\n"
            "/// precise \"line up exactly with the end\" gesture rather than the generous perpendicular-cross\n"
            "/// boost. Edit this value directly to tune how eagerly the endpoints grab a nearby small line.\n"
            "constexpr double LINE_END_ANCHOR_TOLERANCE_FACTOR = 0.9;\n",
        label="EditSelection.cpp: nouveau facteur LINE_END_ANCHOR_TOLERANCE_FACTOR",
    )

    # ============ Correction 1b: utiliser le nouveau facteur (2 occurrences) ============
    text = cpp.read_text(encoding="utf-8")
    old_tol = "double endpointTolerance = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;"
    new_tol = "double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;"
    n = text.count(old_tol)
    if n == 2:
        text = text.replace(old_tol, new_tol)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: endpointTolerance utilise le nouveau facteur ({n} occurrences)")
    elif text.count(new_tol) == 2:
        print("[SKIP]  EditSelection.cpp: endpointTolerance deja corrige.")
    else:
        print(f"[ECHEC] EditSelection.cpp: endpointTolerance trouve {n} fois (attendu 2).")
        ok = False

    # ============ Correction 2: le repere ne suit plus la souris (2 branches) ============
    ok &= apply_edit(
        cpp,
        old="                                endpointGuideFromX = candidateY;\n"
            "                                endpointGuideToX = candidateY + height;\n",
        new="                                endpointGuideFromX = candidateY + matchY->offset;\n"
            "                                endpointGuideToX = candidateY + height + matchY->offset;\n",
        label="EditSelection.cpp: repere fixe (branche Y)",
    )
    ok &= apply_edit(
        cpp,
        old="                                endpointGuideFromY = candidateX;\n"
            "                                endpointGuideToY = candidateX + width;\n",
        new="                                endpointGuideFromY = candidateX + matchX->offset;\n"
            "                                endpointGuideToY = candidateX + width + matchX->offset;\n",
        label="EditSelection.cpp: repere fixe (branche X)",
    )

    # ============ Correction 3a: nouveau membre startingWasBoosted ============
    ok &= apply_edit(
        h,
        old="    int startingBoostedZone = 0;\n",
        new="    int startingBoostedZone = 0;\n"
            "    /// True if self was already boost-snapped to SOME big line at the moment this drag started (see\n"
            "    /// startingBoostedZone/computeStartingZone(), patch 8.6.4.6). When false (self is a \"fresh\" line,\n"
            "    /// not previously attached anywhere), Top/Below zone transitions are disabled for this drag - see\n"
            "    /// the \"fresh line\" override in mouseMove() (patch 8.6.6): a fresh line can only settle into\n"
            "    /// Middle, unless other same-size/orientation lines are already established on the big line it\n"
            "    /// is approaching, in which case it follows their mode instead.\n"
            "    bool startingWasBoosted = false;\n",
        label="EditSelection.h: nouveau membre startingWasBoosted",
    )

    # ============ Correction 3b: signature de computeStartingZone (declaration anticipee) ============
    ok &= apply_edit(
        cpp,
        old="static int computeStartingZone(double x, double y, double width, double height, Layer* layer,\n"
            "                                const std::vector<const Element*>& excluded,\n"
            "                                const xoj::util::Rectangle<double>& visibleRect, double tolerance);\n",
        new="static int computeStartingZone(double x, double y, double width, double height, Layer* layer,\n"
            "                                const std::vector<const Element*>& excluded,\n"
            "                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,\n"
            "                                bool& outWasBoosted);\n",
        label="EditSelection.cpp: declaration anticipee - nouveau parametre outWasBoosted",
    )

    # ============ Correction 3c: definition complete de computeStartingZone ============
    ok &= apply_edit(
        cpp,
        old="static int computeStartingZone(double x, double y, double width, double height, Layer* layer,\n"
            "                                const std::vector<const Element*>& excluded,\n"
            "                                const xoj::util::Rectangle<double>& visibleRect, double tolerance) {\n"
            "    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {\n"
            "        return 0;\n"
            "    }\n"
            "    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {\n"
            "        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"\n"
            "    }\n"
            "    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {\n"
            "        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"\n"
            "    }\n"
            "\n"
            "    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXReal && !matchXReal->guides.empty() && matchXReal->guides.front().isBoosted) {\n"
            "        return 0;\n"
            "    }\n"
            "    auto matchXLeft = findAlignmentX(x - width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXLeft && !matchXLeft->guides.empty() && matchXLeft->guides.front().isBoosted) {\n"
            "        return 1;\n"
            "    }\n"
            "    auto matchXRight = findAlignmentX(x + width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXRight && !matchXRight->guides.empty() && matchXRight->guides.front().isBoosted) {\n"
            "        return -1;\n"
            "    }\n"
            "    return 0;\n"
            "}\n",
        new="static int computeStartingZone(double x, double y, double width, double height, Layer* layer,\n"
            "                                const std::vector<const Element*>& excluded,\n"
            "                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,\n"
            "                                bool& outWasBoosted) {\n"
            "    outWasBoosted = false;\n"
            "    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return 0;\n"
            "    }\n"
            "    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"\n"
            "    }\n"
            "    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"\n"
            "    }\n"
            "\n"
            "    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXReal && !matchXReal->guides.empty() && matchXReal->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return 0;\n"
            "    }\n"
            "    auto matchXLeft = findAlignmentX(x - width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXLeft && !matchXLeft->guides.empty() && matchXLeft->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return 1;\n"
            "    }\n"
            "    auto matchXRight = findAlignmentX(x + width / 2, width, y, y + height, tolerance, layer, excluded, visibleRect);\n"
            "    if (matchXRight && !matchXRight->guides.empty() && matchXRight->guides.front().isBoosted) {\n"
            "        outWasBoosted = true;\n"
            "        return -1;\n"
            "    }\n"
            "    return 0;\n"
            "}\n",
        label="EditSelection.cpp: definition complete - outWasBoosted sur tous les chemins",
    )

    # ============ Correction 3d: point d'appel dans mouseDown() ============
    ok &= apply_edit(
        cpp,
        old="    this->startingBoostedZone = 0;\n"
            "    {\n"
            "        std::vector<const Element*> excludedForStart = this->getElementsView().clone();\n"
            "        xoj::util::Rectangle<double>* visibleRectPtrForStart = this->view->getXournal()->getVisibleRect(this->view);\n"
            "        if (visibleRectPtrForStart != nullptr) {\n"
            "            xoj::util::Rectangle<double> visibleRectForStart = *visibleRectPtrForStart;\n"
            "            delete visibleRectPtrForStart;\n"
            "            constexpr double startingToleranceHardcodedPx = 6.0;  // matches ALIGNMENT_SNAP_TOLERANCE_PX\n"
            "            double toleranceForStart = startingToleranceHardcodedPx / zoom;\n"
            "            this->startingBoostedZone =\n"
            "                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,\n"
            "                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,\n"
            "                                         visibleRectForStart, toleranceForStart);\n"
            "        }\n"
            "    }\n",
        new="    this->startingBoostedZone = 0;\n"
            "    this->startingWasBoosted = false;\n"
            "    {\n"
            "        std::vector<const Element*> excludedForStart = this->getElementsView().clone();\n"
            "        xoj::util::Rectangle<double>* visibleRectPtrForStart = this->view->getXournal()->getVisibleRect(this->view);\n"
            "        if (visibleRectPtrForStart != nullptr) {\n"
            "            xoj::util::Rectangle<double> visibleRectForStart = *visibleRectPtrForStart;\n"
            "            delete visibleRectPtrForStart;\n"
            "            constexpr double startingToleranceHardcodedPx = 6.0;  // matches ALIGNMENT_SNAP_TOLERANCE_PX\n"
            "            double toleranceForStart = startingToleranceHardcodedPx / zoom;\n"
            "            this->startingBoostedZone =\n"
            "                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,\n"
            "                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,\n"
            "                                         visibleRectForStart, toleranceForStart, this->startingWasBoosted);\n"
            "        }\n"
            "    }\n",
        label="EditSelection.cpp: mouseDown() capture startingWasBoosted",
    )

    # ============ Correction 3e: remplacement de zone (branche Y) ============
    ok &= apply_edit(
        cpp,
        old="                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n\n"
            "                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever\n",
        new="                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n\n"
            "                    // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already\n"
            "                    // boost-snapped to ANY big line when this drag started (this->startingWasBoosted\n"
            "                    // == false) may not settle into Top/Below on its own just because the cursor\n"
            "                    // dragged it into that zone - it must default to Middle, UNLESS other same-size,\n"
            "                    // same-orientation lines are already established on THIS big line, in which case\n"
            "                    // it follows their mode instead. A line that WAS already attached somewhere at\n"
            "                    // mouseDown keeps full free transition between zones, as before.\n"
            "                    if (!this->startingWasBoosted) {\n"
            "                        int familyMode = 0;\n"
            "                        bool familyFound = false;\n"
            "                        double selfLengthForFamily = height;\n"
            "                        for (auto& elPtr: this->sourceLayer->getElements()) {\n"
            "                            Element* el = elPtr.get();\n"
            "                            if (el == yBoostedTarget) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            auto* otherStroke = dynamic_cast<Stroke*>(el);\n"
            "                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "                            bool isVerticalShaft =\n"
            "                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;\n"
            "                            if (!isVerticalShaft || std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,\n"
            "                                                shaft.x + shaft.width)) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double shaftCenterY = shaft.y + shaft.height / 2;\n"
            "                            if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double farEdge = shaft.y + shaft.height;\n"
            "                            double nearEdge = shaft.y;\n"
            "                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {\n"
            "                                familyMode = -1;\n"
            "                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {\n"
            "                                familyMode = 1;\n"
            "                            } else {\n"
            "                                familyMode = 0;\n"
            "                            }\n"
            "                            familyFound = true;\n"
            "                            break;\n"
            "                        }\n"
            "                        this->activeBoostedZone = familyFound ? familyMode : 0;\n"
            "                    }\n\n"
            "                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever\n",
        label="EditSelection.cpp: remplacement de zone pour ligne fraiche (branche Y)",
    )

    # ============ Correction 3f: remplacement de zone (branche X) ============
    ok &= apply_edit(
        cpp,
        old="                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n\n"
            "                    double refPointX;\n",
        new="                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n\n"
            "                    // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case - see\n"
            "                    // the Y-branch above for the full explanation.\n"
            "                    if (!this->startingWasBoosted) {\n"
            "                        int familyMode = 0;\n"
            "                        bool familyFound = false;\n"
            "                        double selfLengthForFamily = width;\n"
            "                        for (auto& elPtr: this->sourceLayer->getElements()) {\n"
            "                            Element* el = elPtr.get();\n"
            "                            if (el == xBoostedTarget) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            auto* otherStroke = dynamic_cast<Stroke*>(el);\n"
            "                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "                            bool isHorizontalShaft =\n"
            "                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;\n"
            "                            if (!isHorizontalShaft || std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,\n"
            "                                                shaft.y + shaft.height)) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double shaftCenterX = shaft.x + shaft.width / 2;\n"
            "                            if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double farEdge = shaft.x + shaft.width;\n"
            "                            double nearEdge = shaft.x;\n"
            "                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {\n"
            "                                familyMode = -1;\n"
            "                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {\n"
            "                                familyMode = 1;\n"
            "                            } else {\n"
            "                                familyMode = 0;\n"
            "                            }\n"
            "                            familyFound = true;\n"
            "                            break;\n"
            "                        }\n"
            "                        this->activeBoostedZone = familyFound ? familyMode : 0;\n"
            "                    }\n\n"
            "                    double refPointX;\n",
        label="EditSelection.cpp: remplacement de zone pour ligne fraiche (branche X)",
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
