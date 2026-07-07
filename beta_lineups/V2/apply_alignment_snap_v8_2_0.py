#!/usr/bin/env python3
"""
Patch 8.2.0 : fusion des patchs 8.2 et 8.2.2 (guides bicolores) en un
seul, applicable PAR-DESSUS d'autres patchs - modifications CIBLEES par
ancres de texte (pas de reecriture de fichier entier), exactement comme
le reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_2.py
    apply_alignment_snap_v8_2_2.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch, sur une base v7.10 + 8.1.0).

Fichiers concernes :
  - src/core/control/tools/EditSelection.cpp\n  - src/core/control/tools/EditSelection.h\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py), OU v7_10.py

Independant de 8.1 (mais s'y adapte si present, comme le patch 8.2
d'origine).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/EditSelection.cpp", [
        ("""    double extentTo;
    bool isCenter;
    bool isBoosted;
    std::vector<std::pair<double, double>> equidistantGaps;
    double equidistantPlacement = 0;
};""", """    double extentTo;
    bool isCenter;
    bool isBoosted;
    bool selfIsCenter = false;
    bool otherIsCenter = false;
    bool selfOnFromSide = true;
    std::vector<std::pair<double, double>> equidistantGaps;
    double equidistantPlacement = 0;
};"""),
        (""" * xLeft/xRight are the moving box's horizontal extent, used both for the crossing/overlap check and
 * to compute each guide line's span (perpendicular axis).
 */
static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {""", """ * xLeft/xRight are the moving box's horizontal extent, used both for the crossing/overlap check and
 * to compute each guide line's span (perpendicular axis).
 */
/**
 * Below this gap (in document points) between the moving object's own extent and the matched
 * element's own extent (on the perpendicular axis), the guide line still spans their full union, as
 * before - the objects are close enough (or overlapping) that trimming wouldn't help. Above it, the
 * line is trimmed to just the empty gap between their two nearest edges, so it no longer runs on top
 * of either object's body (most noticeable when aligning two objects that are long on the
 * perpendicular axis, e.g. two perpendicular lines).
 */
constexpr double GUIDE_TRIM_MIN_GAP = 5.0;

/**
 * Computes the [from, to] span (perpendicular axis) for a guide line connecting an object spanning
 * [selfLo, selfHi] to another spanning [otherLo, otherHi]. If the two don't overlap and the gap
 * between their nearest edges exceeds GUIDE_TRIM_MIN_GAP, the line is trimmed to exactly that gap
 * (the empty space between them). Otherwise (overlapping, or too close to bother trimming), the
 * line spans their full union, as it always did before this trimming was added.
 */
static void computeGuideExtent(double selfLo, double selfHi, double otherLo, double otherHi, double& outFrom,
                                double& outTo) {
    if (selfHi <= otherLo && otherLo - selfHi > GUIDE_TRIM_MIN_GAP) {
        outFrom = selfHi;
        outTo = otherLo;
        return;
    }
    if (otherHi <= selfLo && selfLo - otherHi > GUIDE_TRIM_MIN_GAP) {
        outFrom = otherHi;
        outTo = selfLo;
        return;
    }
    outFrom = std::min(selfLo, otherLo);
    outTo = std::max(selfHi, otherHi);
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {"""),
        ("""                double dist = std::abs(cs.value - co.value);
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
        }""", """                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              guideFrom,
                                              guideTo,
                                              cs.isCenter || co.isCenter,
                                              false};
                    bestAny->selfIsCenter = cs.isCenter;
                    bestAny->otherIsCenter = co.isCenter;
                    bestAny->selfOnFromSide = xLeft <= snapped.x;
                }
            }
        }"""),
        ("""        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(xLeft, snapped.x),
                                                     std::max(xRight, snapped.x + snapped.width),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }""", """        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);
                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};
                    guide.selfIsCenter = cs.isCenter;
                    guide.otherIsCenter = co.isCenter;
                    guide.selfOnFromSide = xLeft <= snapped.x;
                    guides.push_back(guide);
                }
            }
        }"""),
        ("""                double dist = std::abs(cs.value - co.value);
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
        }""", """                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              guideFrom,
                                              guideTo,
                                              cs.isCenter || co.isCenter,
                                              false};
                    bestAny->selfIsCenter = cs.isCenter;
                    bestAny->otherIsCenter = co.isCenter;
                    bestAny->selfOnFromSide = yTop <= snapped.y;
                }
            }
        }"""),
        ("""        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(yTop, snapped.y),
                                                     std::max(yBottom, snapped.y + snapped.height),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }""", """        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);
                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};
                    guide.selfIsCenter = cs.isCenter;
                    guide.otherIsCenter = co.isCenter;
                    guide.selfOnFromSide = yTop <= snapped.y;
                    guides.push_back(guide);
                }
            }
        }"""),
        ("""                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesX.clear();""", """                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesX.clear();"""),
        ("""                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesY.clear();""", """                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement});
                    }
                } else {
                    this->activeGuidesY.clear();"""),
        ("""        cairo_set_dash(cr, nullptr, 0, 0);

        for (auto& guide: this->activeGuidesX) {
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
            } else if (guide.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
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
            cairo_line_to(cr, gx, guide.to * zoom);
            cairo_stroke(cr);
        }
        for (auto& guide: this->activeGuidesY) {
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
            } else if (guide.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
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
            cairo_line_to(cr, guide.to * zoom, gy);
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }""", """        cairo_set_dash(cr, nullptr, 0, 0);

        for (auto& guide: this->activeGuidesX) {
            double gx = guide.coordinate * zoom;
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            } else if (!guide.equidistantGaps.empty()) {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
                double py = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);
                }
            } else {
                double mid = (guide.from + guide.to) / 2 * zoom;
                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;
                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;
                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,
                                     firstHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, mid);
                cairo_stroke(cr);
                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,
                                     secondHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, gx, mid);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            }
        }
        for (auto& guide: this->activeGuidesY) {
            double gy = guide.coordinate * zoom;
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);
            } else if (!guide.equidistantGaps.empty()) {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
                double px = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);
                }
            } else {
                double mid = (guide.from + guide.to) / 2 * zoom;
                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;
                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;
                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,
                                     firstHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, mid, gy);
                cairo_stroke(cr);
                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,
                                     secondHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, mid, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);
            }
        }
        cairo_restore(cr);
    }"""),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        ("""        double to;
        bool isCenter;
        bool isBoosted;
        std::vector<std::pair<double, double>> equidistantGaps;
        double equidistantPlacement = 0;
    };""", """        double to;
        bool isCenter;
        bool isBoosted;
        bool selfIsCenter = false;
        bool otherIsCenter = false;
        bool selfOnFromSide = true;
        std::vector<std::pair<double, double>> equidistantGaps;
        double equidistantPlacement = 0;
    };"""),
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
