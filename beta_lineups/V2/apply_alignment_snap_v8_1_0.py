#!/usr/bin/env python3
"""
Patch 8.1.0 : fusion des patchs 8.1, 8.1.2, 8.1.3 (accroche equidistante)
en un seul, applicable PAR-DESSUS d'autres patchs - modifications CIBLEES
par ancres de texte (pas de reecriture de fichier entier), exactement
comme le reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_1.py
    apply_alignment_snap_v8_1_2.py
    apply_alignment_snap_v8_1_3.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch, sur une base v7.10).

Fichiers concernes :
  - src/core/control/tools/EditSelection.cpp\n  - src/core/control/tools/EditSelection.h\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py), OU le patch
     fusionne equivalent apply_alignment_snap_v7_10.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/EditSelection.cpp", [
        (""" * `isCenter` is true if either of the two matched candidates was a center point (rather than an
 * edge); `isBoosted` is true for the special \"small stroke crossing a big perpendicular stroke,
 * center-to-center\" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.
 */
struct AlignmentMatch {
    double offset;""", """ * `isCenter` is true if either of the two matched candidates was a center point (rather than an
 * edge); `isBoosted` is true for the special \"small stroke crossing a big perpendicular stroke,
 * center-to-center\" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.
 * `equidistantGaps`/`equidistantPlacement` are only set for an equidistant (\"equal spacing\") match
 * (see findEquidistantX/Y()): each pair in `equidistantGaps` is a (from, to) span, in primary-axis
 * document coordinates, of one gap in the chain to be drawn as a double-headed arrow; all of them
 * are drawn at the same `equidistantPlacement` coordinate on the perpendicular axis. Empty/0 (their
 * default) for every other kind of match, which just draws the plain coordinate/extentFrom/extentTo
 * line instead - see paint().
 */
struct AlignmentMatch {
    double offset;"""),
        ("""    double extentTo;
    bool isCenter;
    bool isBoosted;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line""", """    double extentTo;
    bool isCenter;
    bool isBoosted;
    std::vector<std::pair<double, double>> equidistantGaps;
    double equidistantPlacement = 0;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line"""),
        ("""}

/**
 * Searches for alignment matches of the moving box's y-candidates (see buildCandidates()) against
 * every other element on `layer` (elements in `excluded` are always skipped, i.e. the elements
 * currently being moved; elements whose *visual* bounding box doesn't currently intersect""", """}

/**
 * Vertical (for a horizontal chain) or horizontal (for a vertical chain) offset, in document
 * points, between the row/column of objects being equally spaced and the double-arrow chain drawn
 * to illustrate it - see findEquidistantX/Y() and paint(). The chain is drawn on the \"outside\" of
 * the objects (below a horizontal row, to the right of a vertical column).
 */
constexpr double EQUIDISTANT_ARROW_MARGIN = 10.0;

/**
 * Equidistant (\"equal spacing\") snapping: if the moving box, placed at x (width wide), would end up
 * adjacent to one of two other elements B and C on `layer`, at exactly the same gap that already
 * separates B and C from each other, returns the match (offset to apply, and a guide spanning from
 * the moving box to the far element). Covers extending an existing rhythm at either end (self-B-C or
 * B-C-self); does not cover inserting self *between* B and C by bisecting their gap. B and C are only
 * considered together if a single horizontal line could pass through the moving box and both of them
 * (their Y-extents, together with [yTop, yBottom], must have a common intersection) - same
 * \"overlap on the perpendicular axis\" rule used elsewhere, not requiring perfect alignment.
 * Always renders pink (this is not an edge/center anchor match, just reused for visual consistency).
 */
static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded,
                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        candidates.push_back(el);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.x + bb.width > cb.x) {
                continue;  // only consider b strictly to the left of c (each pair handled once)
            }
            double gap = cb.x - (bb.x + bb.width);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({yTop, bb.y, cb.y});
            double minEnd = std::min({yBottom, bb.y + bb.height, cb.y + cb.height});
            if (maxStart > minEnd) {
                continue;
            }

            // self extends the row on the left: self, b, c
            double unionFrom = std::min({yTop, bb.y, cb.y});
            double unionTo = std::max({yBottom, bb.y + bb.height, cb.y + cb.height});
            double placement = std::max({yBottom, bb.y + bb.height, cb.y + cb.height}) + EQUIDISTANT_ARROW_MARGIN;
            double targetLeft = bb.x - gap - width;
            double distLeft = std::abs(targetLeft - x);
            if (distLeft < bestDist) {
                bestDist = distLeft;
                best = AlignmentMatch{targetLeft - x, targetLeft, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{targetLeft + width, bb.x}, {bb.x + bb.width, cb.x}};
                best->equidistantPlacement = placement;
            }
            // self extends the row on the right: b, c, self
            double targetRight = cb.x + cb.width + gap;
            double distRight = std::abs(targetRight - x);
            if (distRight < bestDist) {
                bestDist = distRight;
                best = AlignmentMatch{targetRight - x, targetRight, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{bb.x + bb.width, cb.x}, {cb.x + cb.width, targetRight}};
                best->equidistantPlacement = placement;
            }
        }
    }
    return best;
}

/// Same as findEquidistantX(), but along the vertical axis (stacking a row top-to-bottom).
static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded,
                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        candidates.push_back(el);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.y + bb.height > cb.y) {
                continue;
            }
            double gap = cb.y - (bb.y + bb.height);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({xLeft, bb.x, cb.x});
            double minEnd = std::min({xRight, bb.x + bb.width, cb.x + cb.width});
            if (maxStart > minEnd) {
                continue;
            }

            double unionFrom = std::min({xLeft, bb.x, cb.x});
            double unionTo = std::max({xRight, bb.x + bb.width, cb.x + cb.width});
            double placement = std::max({xRight, bb.x + bb.width, cb.x + cb.width}) + EQUIDISTANT_ARROW_MARGIN;
            double targetTop = bb.y - gap - height;
            double distTop = std::abs(targetTop - y);
            if (distTop < bestDist) {
                bestDist = distTop;
                best = AlignmentMatch{targetTop - y, targetTop, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{targetTop + height, bb.y}, {bb.y + bb.height, cb.y}};
                best->equidistantPlacement = placement;
            }
            double targetBottom = cb.y + cb.height + gap;
            double distBottom = std::abs(targetBottom - y);
            if (distBottom < bestDist) {
                bestDist = distBottom;
                best = AlignmentMatch{targetBottom - y, targetBottom, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{bb.y + bb.height, cb.y}, {cb.y + cb.height, targetBottom}};
                best->equidistantPlacement = placement;
            }
        }
    }
    return best;
}

/**
 * Searches for alignment matches of the moving box's y-candidates (see buildCandidates()) against
 * every other element on `layer` (elements in `excluded` are always skipped, i.e. the elements
 * currently being moved; elements whose *visual* bounding box doesn't currently intersect"""),
        ("""                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              this->sourceLayer, excluded, visibleRect);

                if (matchX) {
                    dx += matchX->offset;
                    objectSnappedX = true;
                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});
                    }
                } else {
                    this->activeGuidesX.clear();""", """                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              this->sourceLayer, excluded, visibleRect);

                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.
                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;

                if (!matchXIsBoosted) {
                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchX || std::abs(equidistantX->offset) < std::abs(matchX->offset)) {
                            matchX = AlignmentSearchResult{equidistantX->offset, {*equidistantX}};
                        }
                    }
                }
                if (!matchYIsBoosted) {
                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchY || std::abs(equidistantY->offset) < std::abs(matchY->offset)) {
                            matchY = AlignmentSearchResult{equidistantY->offset, {*equidistantY}};
                        }
                    }
                }

                if (matchX) {
                    dx += matchX->offset;
                    objectSnappedX = true;
                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesX.clear();"""),
        ("""                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});
                    }
                } else {
                    this->activeGuidesY.clear();""", """                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesY.clear();"""),
        (""" * Paints the selection to cr, with the given zoom factor. The coordinates of cr
 * should be relative to the provided view by getView() (use translateEvent())
 */
void EditSelection::paint(cairo_t* cr, double zoom) {
    double x = this->x;
    double y = this->y;""", """ * Paints the selection to cr, with the given zoom factor. The coordinates of cr
 * should be relative to the provided view by getView() (use translateEvent())
 */
/**
 * Draws a double-headed arrow from (x1, y1) to (x2, y2) (already in screen/pixel coordinates, i.e.
 * pre-multiplied by zoom) on `cr`, using whatever source color/line width is currently set. Used to
 * illustrate an equidistant (\"equal spacing\") match - see findEquidistantX/Y() and paint().
 */
static void drawDoubleArrow(cairo_t* cr, double x1, double y1, double x2, double y2) {
    constexpr double ARROW_HEAD_LENGTH_PX = 7.0;
    constexpr double ARROW_HEAD_ANGLE = M_PI / 7.0;  // ~25 degrees between each wing and the shaft

    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x2, y2);
    cairo_stroke(cr);

    double angle = std::atan2(y2 - y1, x2 - x1);

    // Head at (x1, y1), wings pointing back along the shaft (towards (x2, y2)'s opposite direction).
    double back1 = angle + M_PI;
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 - ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 + ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 + ARROW_HEAD_ANGLE));

    // Head at (x2, y2), wings pointing back along the shaft towards (x1, y1).
    double back2 = angle;
    cairo_move_to(cr, x2, y2);
    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 - ARROW_HEAD_ANGLE),
                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x2, y2);
    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 + ARROW_HEAD_ANGLE),
                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 + ARROW_HEAD_ANGLE));
    cairo_stroke(cr);
}

void EditSelection::paint(cairo_t* cr, double zoom) {
    double x = this->x;
    double y = this->y;"""),
        ("""            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            double gx = guide.coordinate * zoom;
            cairo_move_to(cr, gx, guide.from * zoom);
            cairo_line_to(cr, gx, guide.to * zoom);""", """            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            if (!guide.equidistantGaps.empty()) {
                // Equidistant match: one double-headed arrow per gap in the chain, drawn horizontally
                // (this is a horizontal row being equally spaced along X) at a fixed Y offset
                // (equidistantPlacement) below the row.
                double py = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);
                }
                continue;
            }
            double gx = guide.coordinate * zoom;
            cairo_move_to(cr, gx, guide.from * zoom);
            cairo_line_to(cr, gx, guide.to * zoom);"""),
        ("""            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            double gy = guide.coordinate * zoom;
            cairo_move_to(cr, guide.from * zoom, gy);
            cairo_line_to(cr, guide.to * zoom, gy);""", """            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            if (!guide.equidistantGaps.empty()) {
                // Equidistant match: one double-headed arrow per gap in the chain, drawn vertically
                // (this is a vertical column being equally spaced along Y) at a fixed X offset
                // (equidistantPlacement) to the right of the column.
                double px = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);
                }
                continue;
            }
            double gy = guide.coordinate * zoom;
            cairo_move_to(cr, guide.from * zoom, gy);
            cairo_line_to(cr, guide.to * zoom, gy);"""),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        ("""     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line
     * visually connects the two.
     */
    struct AlignmentGuide {
        double coordinate;""", """     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line
     * visually connects the two. `equidistantGaps`/`equidistantPlacement`, if non-empty, mean this
     * guide is an equidistant (\"equal spacing\") match instead: each pair is one gap in the chain to
     * draw as a double-headed arrow (in primary-axis coordinates), all at `equidistantPlacement` on
     * the perpendicular axis - see paint().
     */
    struct AlignmentGuide {
        double coordinate;"""),
        ("""        double to;
        bool isCenter;
        bool isBoosted;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a""", """        double to;
        bool isCenter;
        bool isBoosted;
        std::vector<std::pair<double, double>> equidistantGaps;
        double equidistantPlacement = 0;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a"""),
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
