#!/usr/bin/env python3
"""
Patch 8.6.A : fusion des patchs 8.6, 8.6.2, 8.6.3, 8.6.3.2, 8.6.3.3
(grille bleue + exclusion des fleches du palier bleu) en un seul,
applicable PAR-DESSUS d'autres patchs - modifications CIBLEES par ancres
de texte (pas de reecriture de fichier entier), exactement comme le
reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_6.py
    apply_alignment_snap_v8_6_2.py
    apply_alignment_snap_v8_6_3.py
    apply_alignment_snap_v8_6_3_2.py
    apply_alignment_snap_v8_6_3_3.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch, sur une base v7.10 + 8.1.0 + 8.2.0 + 8.3.0 +
8.4.0 + 8.5.0).

Fichiers concernes :
  - src/core/control/tools/EditSelection.cpp\n  - src/core/control/tools/EditSelection.h\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py), OU v7_10.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/EditSelection.cpp", [
        ("""    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);""", """    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();
    this->activeBlueGridMarkers.clear();

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);"""),
        ("""    double extentTo;
    bool isCenter;
    bool isBoosted;
    bool selfIsCenter = false;
    bool otherIsCenter = false;
    bool selfOnFromSide = true;""", """    double extentTo;
    bool isCenter;
    bool isBoosted;
    /// For a boosted (blue) match only: the \"big line\" element that was matched, needed by the
    /// \"blue grid\" feature (see computeBlueGrid()) to search for other small crossing lines on it.
    const Element* boostedTarget = nullptr;
    bool selfIsCenter = false;
    bool otherIsCenter = false;
    bool selfOnFromSide = true;"""),
        (""" * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 1.5;

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's""", """ * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 2.25;

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's"""),
        ("""    return {pageWidth / 2.0, std::nullopt};
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {""", """    return {pageWidth / 2.0, std::nullopt};
}

/**
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
 * Below this (document points), two positions are considered \"exactly\" the same length/spacing for
 * the \"blue grid\" feature - a tiny epsilon for floating-point safety, not a real user-facing
 * tolerance (which is deliberately zero for the grid-spacing check, per design).
 */
constexpr double BLUE_GRID_LENGTH_EPS = 0.5;

/**
 * Minimum allowed distance (in document points) between the moving object and the one fixed
 * same-size line found in the \"blue grid\" Case A (see computeBlueGridX/Y()). Trying to bring them
 * closer than this freezes the moving object at exactly this distance (on whichever side it
 * currently approaches from), until the cursor's raw position would put it further than this same
 * distance on the *other* side, at which point it jumps straight to the cursor's actual position and
 * resumes following it normally.
 */
constexpr double BLUE_GRID_MIN_SPACING = 5.0;

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
        double signedD = selfPos - fixedPos;
        double effectivePos = selfPos;
        std::optional<double> forceOffset;
        if (std::abs(signedD) < BLUE_GRID_MIN_SPACING) {
            double clampSign = (signedD >= 0) ? 1.0 : -1.0;
            effectivePos = fixedPos + clampSign * BLUE_GRID_MIN_SPACING;
            forceOffset = effectivePos;
        }
        double d = std::abs(effectivePos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (effectivePos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = effectivePos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{forceOffset, markers, perpendicular, selfLength / 2};
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
        double signedD = selfPos - fixedPos;
        double effectivePos = selfPos;
        std::optional<double> forceOffset;
        if (std::abs(signedD) < BLUE_GRID_MIN_SPACING) {
            double clampSign = (signedD >= 0) ? 1.0 : -1.0;
            effectivePos = fixedPos + clampSign * BLUE_GRID_MIN_SPACING;
            forceOffset = effectivePos;
        }
        double d = std::abs(effectivePos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (effectivePos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = effectivePos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{forceOffset, markers, perpendicular, selfLength / 2};
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

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {"""),
        ("""                                          std::max(xRight, shaft.x + shaft.width),
                                          true,
                                          true};
        }
    }
    if (bestBoosted) {""", """                                          std::max(xRight, shaft.x + shaft.width),
                                          true,
                                          true};
            bestBoosted->boostedTarget = el;
        }
    }
    if (bestBoosted) {"""),
        ("""                                          std::max(yBottom, shaft.y + shaft.height),
                                          true,
                                          true};
        }
    }
    if (bestBoosted) {""", """                                          std::max(yBottom, shaft.y + shaft.height),
                                          true,
                                          true};
            bestBoosted->boostedTarget = el;
        }
    }
    if (bestBoosted) {"""),
        ("""                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              this->sourceLayer, excluded, visibleRect);

                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.
                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;

                if (!matchXIsBoosted) {
                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {""", """                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              this->sourceLayer, excluded, visibleRect);

                // An arrow or double arrow, however small, is never eligible to be the \"small\"
                // crossing side of a boosted (blue) match - only plain lines are. If self is an
                // arrow and the search above found one anyway, discard it outright: on that axis,
                // self simply gets no alignment snap at all in that case (not even the ordinary
                // tier), rather than threading an extra flag through findAlignmentX/Y themselves.
                {
                    auto selfElementsForArrowCheck = this->getElementsView();
                    if (selfElementsForArrowCheck.size() == 1) {
                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForArrowCheck.begin())) {
                            if (selfStroke->getArrowKind() != ArrowKind::NONE) {
                                if (matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted) {
                                    matchX = std::nullopt;
                                }
                                if (matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted) {
                                    matchY = std::nullopt;
                                }
                            }
                        }
                    }
                }


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.
                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;

                // \"Blue grid\" (see computeBlueGridX/Y()): if one axis is boosted, look on the OTHER
                // (sliding) axis for other same-size small lines/arrows already crossing the same big
                // line. If found, this entirely replaces whatever the ordinary/equidistant search
                // below would otherwise do for that axis - setting matchXIsBoosted/matchYIsBoosted to
                // true here makes the existing equidistant-blending code skip it automatically.
                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;
                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;
                this->activeBlueGridMarkers.clear();
                if (matchYIsBoosted && yBoostedTarget != nullptr) {
                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is
                    // boosted, even if no same-size crossing line is found below (e.g. self is the
                    // first small line of its size on this big line) - the blue tier's own semantics
                    // should never be second-guessed by the generic equidistant search.
                    matchXIsBoosted = true;
                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,
                                                      this->sourceLayer, excluded)) {
                        for (double pos: grid->markerPositions) {
                            this->activeBlueGridMarkers.push_back(
                                    BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});
                        }
                        matchX = grid->forceOffset
                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                   *grid->forceOffset - (candidateX + width / 2), {}}}
                                         : std::nullopt;
                    }
                }
                if (matchXIsBoosted && xBoostedTarget != nullptr) {
                    matchYIsBoosted = true;
                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,
                                                      this->sourceLayer, excluded)) {
                        for (double pos: grid->markerPositions) {
                            this->activeBlueGridMarkers.push_back(
                                    BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});
                        }
                        matchY = grid->forceOffset
                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                   *grid->forceOffset - (candidateY + height / 2), {}}}
                                         : std::nullopt;
                    }
                }

                if (!matchXIsBoosted) {
                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {"""),
        ("""        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position""", """        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
            this->activeBlueGridMarkers.clear();
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position"""),
        ("""        }
        cairo_restore(cr);
    }

    GdkRGBA selectionColor = view->getSelectionColor();
""", """        }
        cairo_restore(cr);
    }

    // \"Blue grid\" markers (see computeBlueGridX/Y() in EditSelection.cpp): short segments, parallel
    // to the moving object's own small line/arrow, at each candidate position along the big line it
    // is boost-snapped to.
    if (!this->activeBlueGridMarkers.empty()) {
        cairo_save(cr);
        cairo_set_line_width(cr, 1.5);
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
        }
        cairo_restore(cr);
    }

    GdkRGBA selectionColor = view->getSelectionColor();
"""),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        ("""    const Settings* settings{};

    /**
     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line""", """    const Settings* settings{};

    /**
     * A single marker of the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp):
     * a short segment, parallel to the moving selection's own small line/arrow, at one candidate
     * position along the big line it is boost-snapped to. `x`/`y` is the marker's center;
     * `halfLength` is half of the moving object's own length; `isVertical` says whether it should be
     * drawn as a short vertical segment (moving object is vertical) or horizontal (moving object is
     * horizontal).
     */
    struct BlueGridMarker {
        double x;
        double y;
        double halfLength;
        bool isVertical;
    };

    /**
     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line"""),
        ("""    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.
    std::vector<AlignmentGuide> activeGuidesY;

    /**
     * The contents of the selection
     */""", """    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.
    std::vector<AlignmentGuide> activeGuidesY;

    /// Active markers for the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp),
    /// set during mouseMove() while dragging, if any.
    std::vector<BlueGridMarker> activeBlueGridMarkers;

    /**
     * The contents of the selection
     */"""),
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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "CrossAxis" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1.py a v7_9.py (ou v7_10.py), puis relancez ce script.")
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
