#!/usr/bin/env python3
"""
Sous-patch 6/6 du systeme d'ancrage entre objets (style Canva/Figma). Ajoute :
  1) Corrige buildCandidates() pour que centerFraction s'applique aussi a la
     branche normale (3 candidats) - c'est ce qui empechait
     TEXT_Y_CENTER_FRACTION d'avoir le moindre effet au patch 5.
  2) Fusionne les paliers vert et rose (recherche du plus proche parmi tous
     les candidats, centre ou bord confondus). Seul le bleu reste exclusif.
  3) Plusieurs lignes de guidage peuvent maintenant s'afficher simultanement
     sur un meme axe si plusieurs points d'ancrage sont d'accord avec le
     meme decalage (uniquement pour le palier fusionne vert/rose - si un
     match bleu existe, une seule ligne bleue est affichee).
  4) Pour le palier bleu specifiquement : utilise une boite "hampe seule"
     (getShaftBounds(), basee sur le premier et dernier point du trace) au
     lieu des bornes completes, pour ignorer les pointes de fleche.

NECESSITE apply_alignment_snap_v1.py, v2.py, v3.py, v4.py et v5.py deja
appliques, dans cet ordre.
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

NEW_BLOCK = """/**
 * Result of a successful alignment match: `offset` is the amount to shift the moving object's
 * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide
 * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the
 * moving object and the matched object, so the drawn guide line visually connects the two.
 * `isCenter` is true if either of the two matched candidates was a center point (rather than an
 * edge); `isBoosted` is true for the special "small stroke crossing a big perpendicular stroke,
 * center-to-center" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.
 */
struct AlignmentMatch {
    double offset;
    double coordinate;
    double extentFrom;
    double extentTo;
    bool isCenter;
    bool isBoosted;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line
/// (AlignmentGuide) consistent with that same offset - there can be more than one when several
/// anchor points happen to agree at once (see findAlignmentX/Y()).
struct AlignmentSearchResult {
    double offset;
    std::vector<AlignmentMatch> guides;
};

/// A single candidate coordinate for alignment, tagged with whether it is a center point.
struct AlignmentCandidate {
    double value;
    bool isCenter;
};

/**
 * Below this size (in document points), a box is considered to have no meaningful "thickness axis"
 * of its own (e.g. a horizontal or vertical straight line) - see buildCandidates().
 */
constexpr double THIN_AXIS_THRESHOLD = 3.0;

/**
 * When a small line-like element is moved across a much bigger perpendicular line-like element
 * (e.g. a short axis tick dragged onto a long axis line), a center-to-center match between the two
 * gets an extended tolerance (this factor), takes exclusive priority over any other match on that
 * axis (only the blue guide is shown, even if other alignments would also be in tolerance), and is
 * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 1.5;

/**
 * The "small stroke crossing a big perpendicular stroke" boost only applies if the small stroke's
 * own length (its extent along its own axis, e.g. a vertical tick's height) is at most this many
 * document points - the same unit used for arrow-key nudging.
 */
constexpr double PERPENDICULAR_CROSS_MAX_SELF_LENGTH = 15.0;

/**
 * Fraction (0 to 1, from the top) of a Text element's height used as its horizontal-alignment (Y)
 * anchor, instead of the true geometric center (0.5). Text bounding boxes include descender space
 * below the baseline, which pulls the geometric center lower than where a horizontal alignment
 * "feels" visually centered on the text - this constant lets that be tuned independently of
 * everything else. Deliberately left at an easily-noticeable default; tune to taste.
 */
constexpr double TEXT_Y_CENTER_FRACTION = 0.2;

/**
 * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis. If the
 * box is "thin" on that axis (size <= THIN_AXIS_THRESHOLD, e.g. the thickness of a horizontal or
 * vertical line), only the center candidate is returned: offering top/bottom (or left/right)
 * candidates as well would produce two near-identical, confusingly close guide lines for a simple
 * straight line. `centerFraction` (0 to 1) chooses where the center candidate sits within the box,
 * in *both* branches (e.g. TEXT_Y_CENTER_FRACTION only has any effect because of this).
 */
static auto buildCandidates(double from, double size, double centerFraction = 0.5) -> std::vector<AlignmentCandidate> {
    if (size <= THIN_AXIS_THRESHOLD) {
        return {{from + size * centerFraction, true}};
    }
    return {{from, false}, {from + size * centerFraction, true}, {from + size, false}};
}

/// True if the two given [x, x+w] x [y, y+h] boxes intersect at all.
static auto boxesIntersect(double x1, double y1, double w1, double h1, double x2, double y2, double w2, double h2)
        -> bool {
    return x1 <= x2 + w2 && x2 <= x1 + w1 && y1 <= y2 + h2 && y2 <= y1 + h1;
}

/// True if the two given ranges [a1, a2] and [b1, b2] overlap at all.
static auto rangesOverlap(double a1, double a2, double b1, double b2) -> bool { return a1 <= b2 && b1 <= a2; }

/**
 * True if `self` (width x height) and `other` (width x height) are two line-like boxes (one is
 * "thin", per THIN_AXIS_THRESHOLD, on one axis while the other is thin on the *perpendicular* axis -
 * i.e. one roughly horizontal, one roughly vertical), `self` is shorter, along its own length, than
 * `other` is along its own length, AND `self`'s own length is at most PERPENDICULAR_CROSS_MAX_SELF_LENGTH
 * - i.e. a small stroke crossing a much bigger perpendicular one, such as a short axis tick being
 * placed onto a long axis line. Does NOT check whether they actually currently overlap in position -
 * see rangesOverlap(), checked separately by the caller, which has the position information.
 */
static auto isSmallCrossingBigPerpendicular(double selfWidth, double selfHeight, double otherWidth,
                                             double otherHeight) -> bool {
    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;
    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;
    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;
    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;

    if (selfVertical && otherHorizontal) {
        return selfHeight < otherWidth && selfHeight <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;
    }
    if (selfHorizontal && otherVertical) {
        return selfWidth < otherHeight && selfWidth <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;
    }
    return false;
}

/**
 * For the blue "perpendicular cross" tier only: returns a bounding box built from just the first
 * and last point of `el` (padded by half its stroke width), instead of its full snapped bounds.
 * For a plain 2-point straight line this is identical to the normal bounds. For a shape with extra
 * decorative points along the way - most notably an arrow, whose arrowhead "wings" are real points
 * in the stroke, flaring out perpendicular to the shaft (see ArrowHandler::createShape()) - this
 * instead reflects just the true shaft, so a small stroke crossing an arrow's shaft is recognized as
 * crossing a thin perpendicular line, exactly like it would for a plain straight line. Elements that
 * aren't a Stroke, or have fewer than 2 points, fall back to the normal snapped bounds.
 */
static auto getShaftBounds(const Element* el) -> xoj::util::Rectangle<double> {
    if (const auto* stroke = dynamic_cast<const Stroke*>(el)) {
        size_t n = stroke->getPointCount();
        if (n >= 2) {
            const Point* pts = stroke->getPoints();
            double halfThick = stroke->getWidth() / 2;
            double minX = std::min(pts[0].x, pts[n - 1].x) - halfThick;
            double minY = std::min(pts[0].y, pts[n - 1].y) - halfThick;
            double maxX = std::max(pts[0].x, pts[n - 1].x) + halfThick;
            double maxY = std::max(pts[0].y, pts[n - 1].y) + halfThick;
            return xoj::util::Rectangle<double>(minX, minY, maxX - minX, maxY - minY);
        }
    }
    return el->getSnappedBounds();
}

/**
 * Searches for alignment matches of the moving box's y-candidates (see buildCandidates()) against
 * every other element on `layer` (elements in `excluded` are always skipped, i.e. the elements
 * currently being moved; elements whose *visual* bounding box doesn't currently intersect
 * `visibleRect` are ignored, i.e. scrolled out of view).
 *
 * First looks for a "boosted" perpendicular-cross center match (see isSmallCrossingBigPerpendicular()
 * and getShaftBounds()); if one is found, it is returned alone (a single blue guide), ignoring every
 * other possible match on this axis entirely.
 *
 * Otherwise, finds the single closest ordinary match (center or edge, computed from each element's
 * *snapped* bounds - Element::getSnappedBounds() - rather than its visual bounds, so a selected
 * element's own candidates line up exactly with an identical, unselected element's; a Text element's
 * center candidate uses TEXT_Y_CENTER_FRACTION instead of the true geometric center). Once that
 * match's offset is known, a second pass collects every other match - possibly against different
 * elements too - that the *same* offset would also satisfy, so e.g. two identically-sized objects
 * whose top, center and bottom all align at once are all drawn, not just one of them.
 *
 * xLeft/xRight are the moving box's horizontal extent, used both for the crossing/overlap check and
 * to compute each guide line's span (perpendicular axis).
 */
static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = getShaftBounds(el);
        bool crossEligible = isSmallCrossingBigPerpendicular(xRight - xLeft, height, shaft.width, shaft.height) &&
                              rangesOverlap(xLeft, xRight, shaft.x, shaft.x + shaft.width);
        if (!crossEligible) {
            continue;
        }
        double coValue = shaft.y + shaft.height / 2;
        double dist = std::abs((y + height / 2) - coValue);
        if (dist < bestBoostedDist) {
            bestBoostedDist = dist;
            bestBoosted = AlignmentMatch{coValue - (y + height / 2),
                                          coValue,
                                          std::min(xLeft, shaft.x),
                                          std::max(xRight, shaft.x + shaft.width),
                                          true,
                                          true};
        }
    }
    if (bestBoosted) {
        return AlignmentSearchResult{bestBoosted->offset, {*bestBoosted}};
    }

    // --- ordinary tier: single closest match, any kind ---
    std::optional<AlignmentMatch> bestAny;
    double bestAnyDist = tolerance;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              std::min(xLeft, snapped.x),
                                              std::max(xRight, snapped.x + snapped.width),
                                              cs.isCenter || co.isCenter,
                                              false};
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
    std::vector<AlignmentMatch> guides;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(xLeft, snapped.x),
                                                     std::max(xRight, snapped.x + snapped.width),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
}

/// Same as findAlignmentY(), but for the horizontal candidates (left / horizontal-center / right).
/// yTop/yBottom are the moving box's vertical extent, used for the crossing/overlap check and the
/// guide line's span. Unlike findAlignmentY(), there is no Text-specific center fraction here.
static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
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
        xoj::util::Rectangle<double> shaft = getShaftBounds(el);
        bool crossEligible = isSmallCrossingBigPerpendicular(width, yBottom - yTop, shaft.width, shaft.height) &&
                              rangesOverlap(yTop, yBottom, shaft.y, shaft.y + shaft.height);
        if (!crossEligible) {
            continue;
        }
        double coValue = shaft.x + shaft.width / 2;
        double dist = std::abs((x + width / 2) - coValue);
        if (dist < bestBoostedDist) {
            bestBoostedDist = dist;
            bestBoosted = AlignmentMatch{coValue - (x + width / 2),
                                          coValue,
                                          std::min(yTop, shaft.y),
                                          std::max(yBottom, shaft.y + shaft.height),
                                          true,
                                          true};
        }
    }
    if (bestBoosted) {
        return AlignmentSearchResult{bestBoosted->offset, {*bestBoosted}};
    }

    // --- ordinary tier: single closest match, any kind ---
    std::optional<AlignmentMatch> bestAny;
    double bestAnyDist = tolerance;
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
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              std::min(yTop, snapped.y),
                                              std::max(yBottom, snapped.y + snapped.height),
                                              cs.isCenter || co.isCenter,
                                              false};
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
    std::vector<AlignmentMatch> guides;
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
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(yTop, snapped.y),
                                                     std::max(yBottom, snapped.y + snapped.height),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
}"""

START_MARKER = "/**\n * Result of a successful alignment match: `offset`"
END_MARKER = "\nvoid EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {"


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


def splice_big_block(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if NEW_BLOCK.strip() in text:
        print("[SKIP]  EditSelection.cpp: gros bloc findAlignmentX/Y deja remplace.")
        return True
    start_idx = text.find(START_MARKER)
    end_idx = text.find(END_MARKER, start_idx if start_idx != -1 else 0)
    if start_idx == -1 or end_idx == -1:
        print("[ECHEC] EditSelection.cpp: ancres de debut/fin introuvables pour le gros bloc.")
        print("        Assurez-vous d'avoir applique v1 a v5 au prealable.")
        return False
    new_text = text[:start_idx] + NEW_BLOCK + text[end_idx:]
    path.write_text(new_text, encoding="utf-8")
    print("[OK]    EditSelection.cpp: reecriture findAlignmentX/Y (paliers fusionnes + guides multiples + hampe)")
    return True


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    h = Path("src/core/control/tools/EditSelection.h")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "PERPENDICULAR_CROSS_BOOST_FACTOR" not in content:
        print("[ECHEC] PERPENDICULAR_CROSS_BOOST_FACTOR introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1/v2/v3/v4/v5.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        cpp,
        old='#include "model/Point.h"                          // for Point\n'
            '#include "model/Text.h"                           // for Text\n',
        new='#include "model/Point.h"                          // for Point\n'
            '#include "model/Stroke.h"                         // for Stroke\n'
            '#include "model/Text.h"                           // for Text\n',
        label="EditSelection.cpp: include model/Stroke.h",
    )

    ok &= apply_edit(
        h,
        old='    /// Vertical guide line (constant x), set during mouseMove() while dragging, if any.\n'
            '    std::optional<AlignmentGuide> activeGuideX;\n'
            '    /// Horizontal guide line (constant y), set during mouseMove() while dragging, if any.\n'
            '    std::optional<AlignmentGuide> activeGuideY;',
        new='    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a\n'
            '    /// single line, but can hold several simultaneously when multiple anchor points agree on the\n'
            '    /// same alignment (e.g. two identically-sized objects whose top, center and bottom all line up\n'
            '    /// at once) - see findAlignmentX/Y() in EditSelection.cpp.\n'
            '    std::vector<AlignmentGuide> activeGuidesX;\n'
            '    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.\n'
            '    std::vector<AlignmentGuide> activeGuidesY;',
        label="EditSelection.h: activeGuideX/Y -> activeGuidesX/Y (vecteurs)",
    )

    ok &= splice_big_block(cpp)

    ok &= apply_edit(
        cpp,
        old='                if (matchX) {\n'
            '                    dx += matchX->offset;\n'
            '                    objectSnappedX = true;\n'
            '                    this->activeGuideX = AlignmentGuide{matchX->coordinate, matchX->extentFrom, matchX->extentTo,\n'
            '                                                         matchX->isCenter, matchX->isBoosted};\n'
            '                } else {\n'
            '                    this->activeGuideX.reset();\n'
            '                }\n'
            '                if (matchY) {\n'
            '                    dy += matchY->offset;\n'
            '                    objectSnappedY = true;\n'
            '                    this->activeGuideY = AlignmentGuide{matchY->coordinate, matchY->extentFrom, matchY->extentTo,\n'
            '                                                         matchY->isCenter, matchY->isBoosted};\n'
            '                } else {\n'
            '                    this->activeGuideY.reset();\n'
            '                }',
        new='                if (matchX) {\n'
            '                    dx += matchX->offset;\n'
            '                    objectSnappedX = true;\n'
            '                    this->activeGuidesX.clear();\n'
            '                    for (auto& g: matchX->guides) {\n'
            '                        this->activeGuidesX.push_back(\n'
            '                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});\n'
            '                    }\n'
            '                } else {\n'
            '                    this->activeGuidesX.clear();\n'
            '                }\n'
            '                if (matchY) {\n'
            '                    dy += matchY->offset;\n'
            '                    objectSnappedY = true;\n'
            '                    this->activeGuidesY.clear();\n'
            '                    for (auto& g: matchY->guides) {\n'
            '                        this->activeGuidesY.push_back(\n'
            '                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});\n'
            '                    }\n'
            '                } else {\n'
            '                    this->activeGuidesY.clear();\n'
            '                }',
        label="EditSelection.cpp: mouseMove() utilise les vecteurs de guides",
    )

    ok &= apply_edit(
        cpp,
        old='        } else {\n'
            '            this->activeGuideX.reset();\n'
            '            this->activeGuideY.reset();\n'
            '        }\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position',
        new='        } else {\n'
            '            this->activeGuidesX.clear();\n'
            '            this->activeGuidesY.clear();\n'
            '        }\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position',
        label="EditSelection.cpp: branche else externe (clear)",
    )

    ok &= apply_edit(
        cpp,
        old='    this->mouseDownType = CURSOR_SELECTION_NONE;\n'
            '    this->activeGuideX.reset();\n'
            '    this->activeGuideY.reset();',
        new='    this->mouseDownType = CURSOR_SELECTION_NONE;\n'
            '    this->activeGuidesX.clear();\n'
            '    this->activeGuidesY.clear();',
        label="EditSelection.cpp: mouseUp() (clear)",
    )

    ok &= apply_edit(
        cpp,
        old='    if (this->activeGuideX || this->activeGuideY) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n\n'
            '        if (this->activeGuideX) {\n'
            '            if (this->activeGuideX->isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (this->activeGuideX->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = this->activeGuideX->coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, this->activeGuideX->from * zoom);\n'
            '            cairo_line_to(cr, gx, this->activeGuideX->to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        if (this->activeGuideY) {\n'
            '            if (this->activeGuideY->isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (this->activeGuideY->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gy = this->activeGuideY->coordinate * zoom;\n'
            '            cairo_move_to(cr, this->activeGuideY->from * zoom, gy);\n'
            '            cairo_line_to(cr, this->activeGuideY->to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }',
        new='    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n\n'
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, guide.from * zoom, gy);\n'
            '            cairo_line_to(cr, guide.to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }',
        label="EditSelection.cpp: paint() dessine toutes les lignes de la liste",
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
