#!/usr/bin/env python3
"""
Patch 8.7 (nouvelle fonctionnalite, phase 8) du systeme d'ancrage entre
objets. Ajoute un point d'ancrage pour centrer une Text, TexImage ou Image
entre deux lignes/fleches paralleles de meme longueur (verticales ou
horizontales), qui delimitent une colonne ou une rangee de tableau (leur
propre etendue doit depasser celle de l'objet des deux cotes).

Ligne de guidage JAUNE (dore), parallele aux deux lignes de reference,
s'etendant sur leur portion commune. Le jaune a la PRIORITE ABSOLUE sur
son axe (remplace entierement rose/vert s'il y en avait), mais n'affecte
pas l'autre axe s'il n'y a pas de jaune dessus ; ne prend jamais le pas
sur le bleu (palier boost).

Ce script utilise des ancres robustes (insensibles a la presence des
patches 8.1/8.1.2/8.1.3/8.2/8.2.2/8.3/8.6/8.6.2/8.6.3/9.1), et fonctionne
donc aussi bien seul (sur la base v1-v7.9) qu'avec tous les patches
anterieurs deja appliques.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)

Independant des autres patches 8.X (compatible dans les deux sens).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    h = Path("src/core/control/tools/EditSelection.h")
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)

    cpp_text = cpp.read_text(encoding="utf-8")
    h_text = h.read_text(encoding="utf-8")

    if "CrossAxis" not in cpp_text:
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 a v7_9.py, puis relancez ce script.")
        sys.exit(1)
    if "findTableCenterX" in cpp_text:
        print("[SKIP] Le patch 8.7 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. AlignmentMatch (cpp): champ isTableCenter, ancre robuste ============
    anchor1 = "    bool isCenter;\n    bool isBoosted;\n"
    if cpp_text.count(anchor1) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre AlignmentMatch trouvee {cpp_text.count(anchor1)} fois (attendu 1).")
        ok = False
    else:
        new1 = ("    bool isCenter;\n    bool isBoosted;\n"
                "    /// For the \"table center\" feature (see findTableCenterX/Y()): true when a Text/TexImage/Image is\n"
                "    /// centered between two same-length parallel lines, drawn in yellow with top priority on its axis.\n"
                "    bool isTableCenter = false;\n")
        cpp_text = cpp_text.replace(anchor1, new1, 1)
        print("[OK]    EditSelection.cpp: champ isTableCenter sur AlignmentMatch")

    # ============ 2. AlignmentGuide (h): meme champ, ancre robuste ============
    anchor2 = "        bool isCenter;\n        bool isBoosted;\n"
    if h_text.count(anchor2) != 1:
        print(f"[ECHEC] EditSelection.h: ancre AlignmentGuide trouvee {h_text.count(anchor2)} fois (attendu 1).")
        ok = False
    else:
        new2 = "        bool isCenter;\n        bool isBoosted;\n        bool isTableCenter = false;\n"
        h_text = h_text.replace(anchor2, new2, 1)
        print("[OK]    EditSelection.h: champ isTableCenter sur AlignmentGuide")

    # ============ 3. includes manquants ============
    if '#include "model/Image.h"' not in cpp_text:
        cpp_text = cpp_text.replace(
            '#include "model/Text.h"                           // for Text',
            '#include "model/Image.h"                          // for Image\n'
            '#include "model/Text.h"                           // for Text\n'
            '#include "model/TexImage.h"                       // for TexImage',
            1,
        )
        print("[OK]    EditSelection.cpp: includes Image.h / TexImage.h")
    else:
        print("[SKIP]  EditSelection.cpp: includes deja presents.")

    # ============ 4. gros bloc: findTableCenterX/Y, insere avant findAlignmentY ============
    anchor4 = "static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"
    if cpp_text.count(anchor4) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre findAlignmentY trouvee {cpp_text.count(anchor4)} fois (attendu 1).")
        ok = False
    else:
        new_functions = '''/**
 * If the moving text box, placed at x (width wide) with Y-extent [yTop, yBottom], has two vertical
 * lines/arrows of the same length on `layer` whose own Y-extent fully contains [yTop, yBottom] (i.e.
 * they bound a table column, extending past the textbox on both ends), returns a match centering the
 * textbox horizontally between them. The guide is drawn in yellow, parallel to the two lines (i.e.
 * vertical), spanning the shared (overlapping) length of the two lines. Only ever called when the
 * moving selection is a single Text, TexImage, or Image.
 */
static auto findTableCenterX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<xoj::util::Rectangle<double>> verticalLines;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isVerticalLine = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
        if (!isVerticalLine) {
            continue;
        }
        if (shaft.y > yTop || shaft.y + shaft.height < yBottom) {
            continue;  // must extend past the textbox on both ends
        }
        verticalLines.push_back(shaft);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;
    double selfCenter = x + width / 2;
    for (size_t i = 0; i < verticalLines.size(); ++i) {
        for (size_t j = 0; j < verticalLines.size(); ++j) {
            if (i == j) {
                continue;
            }
            const auto& left = verticalLines[i];
            const auto& right = verticalLines[j];
            if (!(left.x < right.x)) {
                continue;  // only consider "left" strictly left of "right" (each pair handled once)
            }
            if (std::abs(left.height - right.height) > tolerance) {
                continue;  // same length, within the usual tolerance
            }
            double midpoint = (left.x + right.x) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {
                bestDist = dist;
                double spanFrom = std::max(left.y, right.y);
                double spanTo = std::min(left.y + left.height, right.y + right.height);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }
    return best;
}

/// Same as findTableCenterX(), but for two horizontal lines bounding a table row, centering the
/// textbox vertically between them.
static auto findTableCenterY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<xoj::util::Rectangle<double>> horizontalLines;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isHorizontalLine = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
        if (!isHorizontalLine) {
            continue;
        }
        if (shaft.x > xLeft || shaft.x + shaft.width < xRight) {
            continue;
        }
        horizontalLines.push_back(shaft);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;
    double selfCenter = y + height / 2;
    for (size_t i = 0; i < horizontalLines.size(); ++i) {
        for (size_t j = 0; j < horizontalLines.size(); ++j) {
            if (i == j) {
                continue;
            }
            const auto& top = horizontalLines[i];
            const auto& bottom = horizontalLines[j];
            if (!(top.y < bottom.y)) {
                continue;
            }
            if (std::abs(top.width - bottom.width) > tolerance) {
                continue;
            }
            double midpoint = (top.y + bottom.y) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {
                bestDist = dist;
                double spanFrom = std::max(top.x, bottom.x);
                double spanTo = std::min(top.x + top.width, bottom.x + bottom.width);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }
    return best;
}

'''
        idx = cpp_text.find(anchor4)
        cpp_text = cpp_text[:idx] + new_functions + cpp_text[idx:]
        print("[OK]    EditSelection.cpp: ajout de findTableCenterX/Y")

    # ============ 5. mouseMove(): integration, ancre robuste sur "if (matchX) {" ============
    anchor5 = "                if (matchX) {"
    if cpp_text.count(anchor5) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre 'if (matchX)' trouvee {cpp_text.count(anchor5)} fois (attendu 1).")
        ok = False
    else:
        new5 = '''                // "Table center" (see findTableCenterX/Y()): only relevant when the moving selection is
                // a single Text, TexImage, or Image. Takes strict priority over whatever pink/green
                // match (ordinary tier, equidistant) already exists on its own axis - if found, it
                // fully replaces it, rather than competing on closeness like equidistant does. Never
                // overrides a boosted (blue) match; does not affect the other axis at all.
                auto selfElements = this->getElementsView();
                bool selfIsTableTarget = selfElements.size() == 1 &&
                                          (dynamic_cast<const Text*>(*selfElements.begin()) != nullptr ||
                                           dynamic_cast<const TexImage*>(*selfElements.begin()) != nullptr ||
                                           dynamic_cast<const Image*>(*selfElements.begin()) != nullptr);
                if (selfIsTableTarget) {
                    bool matchXIsBoostedForTable = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                    bool matchYIsBoostedForTable = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                    if (!matchXIsBoostedForTable) {
                        if (auto tableX = findTableCenterX(candidateX, width, candidateY, candidateY + height,
                                                            tolerance, this->sourceLayer, excluded)) {
                            matchX = AlignmentSearchResult{tableX->offset, {*tableX}};
                        }
                    }
                    if (!matchYIsBoostedForTable) {
                        if (auto tableY = findTableCenterY(candidateY, height, candidateX, candidateX + width,
                                                            tolerance, this->sourceLayer, excluded)) {
                            matchY = AlignmentSearchResult{tableY->offset, {*tableY}};
                        }
                    }
                }

                if (matchX) {'''
        cpp_text = cpp_text.replace(anchor5, new5, 1)
        print("[OK]    EditSelection.cpp: mouseMove() integre findTableCenterX/Y (priorite absolue)")

    # ============ 6. guide conversion: ancre robuste "g.isCenter, g.isBoosted" ============
    anchor6 = "g.isCenter, g.isBoosted"
    n6 = cpp_text.count(anchor6)
    if n6 != 2:
        print(f"[ECHEC] EditSelection.cpp: ancre de conversion trouvee {n6} fois (attendu 2).")
        ok = False
    else:
        cpp_text = cpp_text.replace(anchor6, "g.isCenter, g.isBoosted, g.isTableCenter")
        print(f"[OK]    EditSelection.cpp: mouseMove() copie isTableCenter ({n6} occurrences)")

    # ============ 7. paint(): passage de rendu jaune independant, ancre robuste ============
    anchor7 = "        cairo_restore(cr);\n    }\n\n    GdkRGBA selectionColor = view->getSelectionColor();\n"
    if cpp_text.count(anchor7) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre de paint() trouvee {cpp_text.count(anchor7)} fois (attendu 1).")
        ok = False
    else:
        new7 = '''        cairo_restore(cr);
    }

    // "Table center" guides (see findTableCenterX/Y()) always render on top in yellow, regardless of
    // how the main guide loop above colored them (they also satisfy isCenter, so that loop draws them
    // too - this separate pass paints over in yellow, giving them priority on their axis without
    // needing to touch that loop's own, more intricate color-selection logic).
    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {
        cairo_save(cr);
        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_set_source_rgb(cr, 0.9, 0.75, 0.0);  // gold/yellow
        for (auto& guide: this->activeGuidesX) {
            if (!guide.isTableCenter) {
                continue;
            }
            double gx = guide.coordinate * zoom;
            cairo_move_to(cr, gx, guide.from * zoom);
            cairo_line_to(cr, gx, guide.to * zoom);
            cairo_stroke(cr);
        }
        for (auto& guide: this->activeGuidesY) {
            if (!guide.isTableCenter) {
                continue;
            }
            double gy = guide.coordinate * zoom;
            cairo_move_to(cr, guide.from * zoom, gy);
            cairo_line_to(cr, guide.to * zoom, gy);
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }

    GdkRGBA selectionColor = view->getSelectionColor();
'''
        cpp_text = cpp_text.replace(anchor7, new7, 1)
        print("[OK]    EditSelection.cpp: paint() passage de rendu jaune independant")

    cpp.write_text(cpp_text, encoding="utf-8")
    h.write_text(h_text, encoding="utf-8")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
