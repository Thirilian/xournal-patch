#!/usr/bin/env python3
"""
Patch 8.6 (depend de 8.1 et 8.1.2 - OBLIGATOIRE ; compatible avec 8.2/8.2.2
et 8.3, presents ou non, dans n'importe quelle combinaison) du systeme
d'ancrage entre objets.

La "grille bleue" : quand un petit trait/fleche est deja accroche (palier
bleu actif) au centre d'un grand trait/fleche perpendiculaire, et que ce
grand trait a deja UN AUTRE petit trait de la MEME taille qui le croise
(non selectionne), le systeme trace des reperes bleus indicatifs,
espaces de la distance actuelle entre les deux petits traits, prolonges
au-dela du trait selectionne, jusqu'au bout du grand trait (purement
indicatif, pas de snap force sur cette position).

Si le grand trait a DEUX petits traits de meme taille ou plus, deja
espaces regulierement (tolerance stricte, ou multiples exacts du plus
petit ecart), le systeme affiche TOUTE la grille (dans les deux
directions) et FORCE le trait selectionne a s'accrocher a la position de
grille la plus proche du curseur, en temps reel pendant le glissement.

Dans les deux cas, le comportement du patch 8.1 (equidistant generique)
est desactive sur cet axe tant que la grille bleue est active.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py
  4) apply_alignment_snap_v8_1.py + v8_1_2.py (OBLIGATOIRE)
  5) (optionnel, dans n'importe quelle combinaison) v8_2.py + v8_2_2.py,
     et/ou v8_3.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

NEW_BLOCK = """/**
 * Result of computeBlueGridX/Y(): if `forceOffset` is set, the moving object's position along the
 * sliding axis MUST snap to it (there are 2+ equally-spaced same-size crossing lines already on the
 * big line - a real grid). Otherwise (exactly one same-size crossing line found), `forceOffset` is
 * unset and the result is purely indicative: self can keep moving freely along the sliding axis.
 * `markerPositions` are the sliding-axis coordinates of every marker to draw (one short segment each,
 * parallel to self); `perpendicular` is the coordinate shared by all of them (the axis already fixed
 * by the boosted match); `markerHalfLength` is half of self's own length.
 */
struct BlueGridResult {
    std::optional<double> forceOffset;
    std::vector<double> markerPositions;
    double perpendicular;
    double markerHalfLength;
};

/**
 * Below this (document points), two positions are considered "exactly" the same length/spacing for
 * the "blue grid" feature - a tiny epsilon for floating-point safety, not a real user-facing
 * tolerance (which is deliberately zero for the grid-spacing check, per design).
 */
constexpr double BLUE_GRID_LENGTH_EPS = 0.5;

/**
 * If `bigLine` (already the target of an active boosted/blue match on the Y axis, i.e. `bigLine` is
 * horizontal and self is a small vertical line/arrow centered on it) has exactly one *other* small
 * vertical line/arrow of the same length as `selfLength` also crossing it, returns markers
 * extending the self-to-that-line spacing beyond self, in the direction away from it, all the way to
 * the end of `bigLine`'s shaft - purely indicative, `forceOffset` unset. If it has two or more such
 * lines, and they are spaced by exact multiples (including 1x) of their smallest mutual gap (strictly,
 * no tolerance), returns markers for the entire grid in both directions across the whole shaft, and
 * forces self to the grid position closest to `selfPos`. Otherwise (2+ found but not a valid regular
 * grid) returns nullopt - no markers, no forced offset. `selfPos` is self's current raw (pre-snap)
 * center position along X.
 */
static auto computeBlueGridX(const Element* bigLine, double selfPos, double selfLength, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<BlueGridResult> {
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double shaftLo = bigShaft.x;
    double shaftHi = bigShaft.x + bigShaft.width;
    double perpendicular = bigShaft.y + bigShaft.height / 2;

    std::vector<double> otherPositions;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (el == bigLine || std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isVerticalLike = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
        if (!isVerticalLike || std::abs(shaft.height - selfLength) > BLUE_GRID_LENGTH_EPS) {
            continue;
        }
        if (!rangesOverlap(shaftLo, shaftHi, shaft.x, shaft.x + shaft.width) ||
            perpendicular < shaft.y || perpendicular > shaft.y + shaft.height) {
            continue;
        }
        otherPositions.push_back(shaft.x + shaft.width / 2);
    }
    if (otherPositions.empty()) {
        return std::nullopt;
    }
    std::sort(otherPositions.begin(), otherPositions.end());

    if (otherPositions.size() == 1) {
        double fixedPos = otherPositions[0];
        double d = std::abs(selfPos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (selfPos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = selfPos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{std::nullopt, markers, perpendicular, selfLength / 2};
    }

    std::vector<double> gaps;
    for (size_t i = 1; i < otherPositions.size(); ++i) {
        gaps.push_back(otherPositions[i] - otherPositions[i - 1]);
    }
    double minGap = *std::min_element(gaps.begin(), gaps.end());
    if (minGap <= BLUE_GRID_LENGTH_EPS) {
        return std::nullopt;
    }
    for (double g: gaps) {
        double rounded = std::round(g / minGap);
        if (rounded < 1.0 || std::abs(g - rounded * minGap) > BLUE_GRID_LENGTH_EPS) {
            return std::nullopt;
        }
    }

    std::vector<double> markers;
    double p = otherPositions[0];
    while (p - minGap >= shaftLo - BLUE_GRID_LENGTH_EPS) {
        p -= minGap;
    }
    for (; p <= shaftHi + BLUE_GRID_LENGTH_EPS; p += minGap) {
        markers.push_back(p);
    }
    if (markers.empty()) {
        return std::nullopt;
    }
    double closest = markers[0];
    for (double m: markers) {
        if (std::abs(selfPos - m) < std::abs(selfPos - closest)) {
            closest = m;
        }
    }
    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

/// Same as computeBlueGridX(), but for a Y-axis boosted match: `bigLine` is vertical, self is a
/// small horizontal line/arrow, and the grid runs along Y instead of X.
static auto computeBlueGridY(const Element* bigLine, double selfPos, double selfLength, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<BlueGridResult> {
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double shaftLo = bigShaft.y;
    double shaftHi = bigShaft.y + bigShaft.height;
    double perpendicular = bigShaft.x + bigShaft.width / 2;

    std::vector<double> otherPositions;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (el == bigLine || std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isHorizontalLike = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
        if (!isHorizontalLike || std::abs(shaft.width - selfLength) > BLUE_GRID_LENGTH_EPS) {
            continue;
        }
        if (!rangesOverlap(shaftLo, shaftHi, shaft.y, shaft.y + shaft.height) ||
            perpendicular < shaft.x || perpendicular > shaft.x + shaft.width) {
            continue;
        }
        otherPositions.push_back(shaft.y + shaft.height / 2);
    }
    if (otherPositions.empty()) {
        return std::nullopt;
    }
    std::sort(otherPositions.begin(), otherPositions.end());

    if (otherPositions.size() == 1) {
        double fixedPos = otherPositions[0];
        double d = std::abs(selfPos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (selfPos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = selfPos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{std::nullopt, markers, perpendicular, selfLength / 2};
    }

    std::vector<double> gaps;
    for (size_t i = 1; i < otherPositions.size(); ++i) {
        gaps.push_back(otherPositions[i] - otherPositions[i - 1]);
    }
    double minGap = *std::min_element(gaps.begin(), gaps.end());
    if (minGap <= BLUE_GRID_LENGTH_EPS) {
        return std::nullopt;
    }
    for (double g: gaps) {
        double rounded = std::round(g / minGap);
        if (rounded < 1.0 || std::abs(g - rounded * minGap) > BLUE_GRID_LENGTH_EPS) {
            return std::nullopt;
        }
    }

    std::vector<double> markers;
    double p = otherPositions[0];
    while (p - minGap >= shaftLo - BLUE_GRID_LENGTH_EPS) {
        p -= minGap;
    }
    for (; p <= shaftHi + BLUE_GRID_LENGTH_EPS; p += minGap) {
        markers.push_back(p);
    }
    if (markers.empty()) {
        return std::nullopt;
    }
    double closest = markers[0];
    for (double m: markers) {
        if (std::abs(selfPos - m) < std::abs(selfPos - closest)) {
            closest = m;
        }
    }
    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

"""

FIND_ALIGNMENT_Y_ANCHOR = """static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"""


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


def insert_before_anchor(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "computeBlueGridX" in text:
        print("[SKIP]  EditSelection.cpp: computeBlueGridX/Y deja presentes.")
        return True
    idx = text.find(FIND_ALIGNMENT_Y_ANCHOR)
    if idx == -1:
        print("[ECHEC] EditSelection.cpp: ancre de findAlignmentY introuvable.")
        return False
    if text.count(FIND_ALIGNMENT_Y_ANCHOR) > 1:
        print("[ECHEC] EditSelection.cpp: ancre trouvee plusieurs fois (devrait etre unique).")
        return False
    new_text = text[:idx] + NEW_BLOCK + text[idx:]
    path.write_text(new_text, encoding="utf-8")
    print("[OK]    EditSelection.cpp: ajout de computeBlueGridX/Y")
    return True


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    h = Path("src/core/control/tools/EditSelection.h")
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "equidistantGaps" not in content:
        print("[ECHEC] Le patch 8.1 (equidistantGaps) est introuvable dans EditSelection.cpp.")
        print("        Le patch 8.6 DEPEND de 8.1 + 8.1.2 (obligatoire). Appliquez-les d'abord.")
        sys.exit(1)
    if "boostedTarget" in content:
        print("[SKIP] Le patch 8.6 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. AlignmentMatch (cpp): champ boostedTarget, insere juste apres ============
    # ============    "bool isBoosted;" - insensible a l'ordre/presence des autres champs   ============
    # ============    ajoutes par 8.2/8.3 (tous ont des valeurs par defaut).                ============
    ok &= apply_edit(
        cpp,
        old="    bool isCenter;\n"
            "    bool isBoosted;\n",
        new="    bool isCenter;\n"
            "    bool isBoosted;\n"
            "    /// For a boosted (blue) match only: the \"big line\" element that was matched, needed by the\n"
            "    /// \"blue grid\" feature (see computeBlueGrid()) to search for other small crossing lines on it.\n"
            "    const Element* boostedTarget = nullptr;\n",
        label="EditSelection.cpp: champ boostedTarget sur AlignmentMatch",
    )

    # ============ 2. set boostedTarget in both boosted constructions ============
    ok &= apply_edit(
        cpp,
        old="            bestBoosted = AlignmentMatch{coValue - (y + height / 2),\n"
            "                                          coValue,\n"
            "                                          std::min(xLeft, shaft.x),\n"
            "                                          std::max(xRight, shaft.x + shaft.width),\n"
            "                                          true,\n"
            "                                          true};\n"
            "        }\n"
            "    }",
        new="            bestBoosted = AlignmentMatch{coValue - (y + height / 2),\n"
            "                                          coValue,\n"
            "                                          std::min(xLeft, shaft.x),\n"
            "                                          std::max(xRight, shaft.x + shaft.width),\n"
            "                                          true,\n"
            "                                          true};\n"
            "            bestBoosted->boostedTarget = el;\n"
            "        }\n"
            "    }",
        label="EditSelection.cpp: boostedTarget dans findAlignmentY",
    )
    ok &= apply_edit(
        cpp,
        old="            bestBoosted = AlignmentMatch{coValue - (x + width / 2),\n"
            "                                          coValue,\n"
            "                                          std::min(yTop, shaft.y),\n"
            "                                          std::max(yBottom, shaft.y + shaft.height),\n"
            "                                          true,\n"
            "                                          true};\n"
            "        }\n"
            "    }\n"
            "    if (bestBoosted) {",
        new="            bestBoosted = AlignmentMatch{coValue - (x + width / 2),\n"
            "                                          coValue,\n"
            "                                          std::min(yTop, shaft.y),\n"
            "                                          std::max(yBottom, shaft.y + shaft.height),\n"
            "                                          true,\n"
            "                                          true};\n"
            "            bestBoosted->boostedTarget = el;\n"
            "        }\n"
            "    }\n"
            "    if (bestBoosted) {",
        label="EditSelection.cpp: boostedTarget dans findAlignmentX",
    )

    # ============ 3. gros bloc: computeBlueGridX/Y ============
    ok &= insert_before_anchor(cpp)

    # ============ 4. EditSelection.h: struct BlueGridMarker (aucun champ requis sur       ============
    # ============    AlignmentGuide - boostedTarget est lu directement sur l'AlignmentMatch,     ============
    # ============    avant sa conversion en AlignmentGuide, donc pas besoin de le propager)       ============

    ok &= apply_edit(
        h,
        old="    /**\n"
            "     * A single active alignment guide line",
        new="    /**\n"
            "     * A single marker of the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp):\n"
            "     * a short segment, parallel to the moving selection\'s own small line/arrow, at one candidate\n"
            "     * position along the big line it is boost-snapped to. `x`/`y` is the marker\'s center;\n"
            "     * `halfLength` is half of the moving object\'s own length; `isVertical` says whether it should be\n"
            "     * drawn as a short vertical segment (moving object is vertical) or horizontal (moving object is\n"
            "     * horizontal).\n"
            "     */\n"
            "    struct BlueGridMarker {\n"
            "        double x;\n"
            "        double y;\n"
            "        double halfLength;\n"
            "        bool isVertical;\n"
            "    };\n\n"
            "    /**\n"
            "     * A single active alignment guide line",
        label="EditSelection.h: struct BlueGridMarker",
    )

    ok &= apply_edit(
        h,
        old="    std::vector<AlignmentGuide> activeGuidesX;\n"
            "    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.\n"
            "    std::vector<AlignmentGuide> activeGuidesY;\n",
        new="    std::vector<AlignmentGuide> activeGuidesX;\n"
            "    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.\n"
            "    std::vector<AlignmentGuide> activeGuidesY;\n\n"
            "    /// Active markers for the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp),\n"
            "    /// set during mouseMove() while dragging, if any.\n"
            "    std::vector<BlueGridMarker> activeBlueGridMarkers;\n",
        label="EditSelection.h: membre activeBlueGridMarkers",
    )

    # ============ 5. mouseMove(): integration (anchor stable regardless of 8.2/8.3) ============
    ok &= apply_edit(
        cpp,
        old="                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n\n"
            "                if (!matchXIsBoosted) {",
        new="                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n\n"
            "                // \"Blue grid\" (see computeBlueGridX/Y()): if one axis is boosted, look on the OTHER\n"
            "                // (sliding) axis for other same-size small lines/arrows already crossing the same big\n"
            "                // line. If found, this entirely replaces whatever the ordinary/equidistant search\n"
            "                // below would otherwise do for that axis - setting matchXIsBoosted/matchYIsBoosted to\n"
            "                // true here makes the existing equidistant-blending code skip it automatically.\n"
            "                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;\n"
            "                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;\n"
            "                this->activeBlueGridMarkers.clear();\n"
            "                if (matchYIsBoosted && yBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});\n"
            "                        }\n"
            "                        matchX = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateX + width / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                        matchXIsBoosted = true;\n"
            "                    }\n"
            "                }\n"
            "                if (matchXIsBoosted && xBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});\n"
            "                        }\n"
            "                        matchY = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateY + height / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                        matchYIsBoosted = true;\n"
            "                    }\n"
            "                }\n\n"
            "                if (!matchXIsBoosted) {",
        label="EditSelection.cpp: integration grille bleue dans mouseMove()",
    )

    # ============ 6. nettoyage lifecycle (anchors stable regardless of 8.2/8.3) ============
    ok &= apply_edit(
        cpp,
        old="    this->mouseDownType = CURSOR_SELECTION_NONE;\n"
            "    this->activeGuidesX.clear();\n"
            "    this->activeGuidesY.clear();\n",
        new="    this->mouseDownType = CURSOR_SELECTION_NONE;\n"
            "    this->activeGuidesX.clear();\n"
            "    this->activeGuidesY.clear();\n"
            "    this->activeBlueGridMarkers.clear();\n",
        label="EditSelection.cpp: nettoyage dans mouseUp()",
    )
    ok &= apply_edit(
        cpp,
        old="        } else {\n"
            "            this->activeGuidesX.clear();\n"
            "            this->activeGuidesY.clear();\n"
            "        }",
        new="        } else {\n"
            "            this->activeGuidesX.clear();\n"
            "            this->activeGuidesY.clear();\n"
            "            this->activeBlueGridMarkers.clear();\n"
            "        }",
        label="EditSelection.cpp: nettoyage dans la branche else externe",
    )

    # ============ 7. paint(): rendu des reperes, ancre stable avant "GdkRGBA selectionColor" ============
    ok &= apply_edit(
        cpp,
        old="        cairo_restore(cr);\n"
            "    }\n\n"
            "    GdkRGBA selectionColor = view->getSelectionColor();\n",
        new="        cairo_restore(cr);\n"
            "    }\n\n"
            "    // \"Blue grid\" markers (see computeBlueGridX/Y() in EditSelection.cpp): short segments, parallel\n"
            "    // to the moving object\'s own small line/arrow, at each candidate position along the big line it\n"
            "    // is boost-snapped to.\n"
            "    if (!this->activeBlueGridMarkers.empty()) {\n"
            "        cairo_save(cr);\n"
            "        cairo_set_line_width(cr, 1.5);\n"
            "        cairo_set_dash(cr, nullptr, 0, 0);\n"
            "        cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue, matching the boosted tier\n"
            "        for (auto& marker: this->activeBlueGridMarkers) {\n"
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
            "        }\n"
            "        cairo_restore(cr);\n"
            "    }\n\n"
            "    GdkRGBA selectionColor = view->getSelectionColor();\n",
        label="EditSelection.cpp: rendu des reperes de la grille bleue",
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
