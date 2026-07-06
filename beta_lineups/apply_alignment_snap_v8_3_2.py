#!/usr/bin/env python3
"""
Patch 8.3 (compatible avec ou sans les patches 8.1/8.1.2 et 8.2/8.2.2 deja
appliques, dans n'importe quelle combinaison) du systeme d'ancrage entre
objets. Ajoute un point d'ancrage pour centrer un objet en abscisse par
rapport a la PAGE (pas par rapport a d'autres objets). Ligne de guidage
GRISE, traversant tout l'ecran visible.

Subtilite fond de page "Lined" (regle + ligne de marge verticale,
PageTypeFormat::Lined) : le centrage se fait par rapport a la zone
utilisable (entre la marge et le bord de page), pas la page entiere. Une
deuxieme ligne grise est aussi tracee a la position de la marge elle-meme.

Ce script detecte automatiquement la presence de 8.1 (equidistantGaps) et
de 8.2 (selfIsCenter) et adapte ses 4 points de modification les plus
sensibles (structures AlignmentMatch/AlignmentGuide, integration dans
mouseMove(), conversion de guide, rendu dans paint()) a la combinaison
detectee.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py
  4) (optionnel, dans n'importe quelle combinaison) v8_1.py + v8_1_2.py,
     et/ou v8_2.py + v8_2_2.py

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
    if "CrossAxis" not in content:
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 a v7_9.py, puis relancez ce script.")
        sys.exit(1)
    if "static auto computePageCenterX" in content:
        print("[SKIP] Le patch 8.3 semble deja applique.")
        sys.exit(0)

    has_8_1 = "equidistantGaps" in content
    has_8_2 = "selfIsCenter" in content
    has_8_1_3 = "findEquidistantY(candidateY, height, candidateX, candidateX + width,\n                                                              tolerance, this->sourceLayer, excluded, visibleRect)" in content
    print(f"[INFO]  Patch 8.1 detecte : {'oui' if has_8_1 else 'non'}")
    print(f"[INFO]  Patch 8.2 detecte : {'oui' if has_8_2 else 'non'}")
    print(f"[INFO]  Patch 8.1.3 (visibilite equidistant) detecte : {'oui' if has_8_1_3 else 'non'}")

    ok = True

    # ============ 1. includes ============
    ok &= apply_edit(
        cpp,
        old='#include "model/Point.h"                          // for Point',
        new='#include "model/BackgroundConfig.h"                // for BackgroundConfig\n'
            '#include "model/PageType.h"                        // for PageType, PageTypeFormat\n'
            '#include "model/Point.h"                          // for Point',
        label="EditSelection.cpp: includes BackgroundConfig/PageType",
    )

    # ============ 2. AlignmentMatch struct : 4 variantes selon 8.1/8.2 ============
    tail_variants = {
        (False, False): (
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '};\n'
        ),
        (True, False): (
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    std::vector<std::pair<double, double>> equidistantGaps;\n'
            '    double equidistantPlacement = 0;\n'
            '};\n'
        ),
        (False, True): (
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    bool selfIsCenter = false;\n'
            '    bool otherIsCenter = false;\n'
            '    bool selfOnFromSide = true;\n'
            '};\n'
        ),
        (True, True): (
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    bool selfIsCenter = false;\n'
            '    bool otherIsCenter = false;\n'
            '    bool selfOnFromSide = true;\n'
            '    std::vector<std::pair<double, double>> equidistantGaps;\n'
            '    double equidistantPlacement = 0;\n'
            '};\n'
        ),
    }
    old_tail = tail_variants[(has_8_1, has_8_2)]
    old2 = 'struct AlignmentMatch {\n    double offset;\n    double coordinate;\n    double extentFrom;\n    double extentTo;\n' + old_tail
    new2 = old2[:-len('};\n')] + '    bool isPageCenter = false;\n    bool hasPageMargin = false;\n    double pageMarginX = 0;\n};\n'
    ok &= apply_edit(cpp, old2, new2, "EditSelection.cpp: nouveaux champs sur AlignmentMatch")

    # ============ 3. AlignmentGuide struct (EditSelection.h) : 4 variantes ============
    tail_variants_h = {
        (False, False): (
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '    };\n'
        ),
        (True, False): (
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        std::vector<std::pair<double, double>> equidistantGaps;\n'
            '        double equidistantPlacement = 0;\n'
            '    };\n'
        ),
        (False, True): (
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        bool selfIsCenter = false;\n'
            '        bool otherIsCenter = false;\n'
            '        bool selfOnFromSide = true;\n'
            '    };\n'
        ),
        (True, True): (
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        bool selfIsCenter = false;\n'
            '        bool otherIsCenter = false;\n'
            '        bool selfOnFromSide = true;\n'
            '        std::vector<std::pair<double, double>> equidistantGaps;\n'
            '        double equidistantPlacement = 0;\n'
            '    };\n'
        ),
    }
    old_tail_h = tail_variants_h[(has_8_1, has_8_2)]
    old3 = '    struct AlignmentGuide {\n        double coordinate;\n        double from;\n        double to;\n' + old_tail_h
    new3 = old3[:-len('    };\n')] + '        bool isPageCenter = false;\n        bool hasPageMargin = false;\n        double pageMarginX = 0;\n    };\n'
    ok &= apply_edit(h, old3, new3, "EditSelection.h: nouveaux champs sur AlignmentGuide")

    # ============ 4. computePageCenterX(), insere via ancre (evite de perdre une ligne) ============
    start_marker = "static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"
    content = cpp.read_text(encoding="utf-8")
    if "static auto computePageCenterX" in content:
        print("[SKIP]  EditSelection.cpp: computePageCenterX deja present.")
    else:
        idx = content.find(start_marker)
        if idx == -1 or content.count(start_marker) > 1:
            print("[ECHEC] EditSelection.cpp: ancre de findAlignmentY introuvable ou ambigue.")
            ok = False
        else:
            helper = (
                "/**\n"
                " * Result of computePageCenterX(): `centerX` is the horizontal center to snap to; `marginX`, if set,\n"
                " * is the position of the page's own vertical margin line (only for a Lined background), drawn as an\n"
                " * extra guide alongside the center line - see paint().\n"
                " */\n"
                "struct PageCenterInfo {\n"
                "    double centerX;\n"
                "    std::optional<double> marginX;\n"
                "};\n\n"
                "/**\n"
                " * Computes where \"horizontally centered on the page\" means for `page`. For a plain page, this is\n"
                " * simply half the page width. For a Lined background (ruled paper with a vertical margin line -\n"
                " * see LinedBackgroundView), the margin splits the page into a usable area on one side and a margin\n"
                " * strip on the other; centering is done within that usable area instead of the full page width, and\n"
                " * the margin's own position is also returned, matching the same \"margin < 0 means the line goes on\n"
                " * the right\" convention as LinedBackgroundView itself.\n"
                " */\n"
                "static auto computePageCenterX(const XojPage* page) -> PageCenterInfo {\n"
                "    double pageWidth = page->getWidth();\n"
                "    PageType bg = page->getBackgroundType();\n"
                "    if (bg.format == PageTypeFormat::Lined) {\n"
                "        BackgroundConfig config(bg.config);\n"
                "        double margin = 72.0;  // matches LinedBackgroundView's own default\n"
                "        config.loadValue(background_config_strings::CFG_MARGIN, margin);\n"
                "        bool marginOnRight = margin < 0;\n"
                "        if (marginOnRight) {\n"
                "            margin += pageWidth;\n"
                "        }\n"
                "        double centerX = marginOnRight ? margin / 2.0 : (margin + pageWidth) / 2.0;\n"
                "        return {centerX, margin};\n"
                "    }\n"
                "    return {pageWidth / 2.0, std::nullopt};\n"
                "}\n\n"
            )
            new_content = content[:idx] + helper + content[idx:]
            cpp.write_text(new_content, encoding="utf-8")
            print("[OK]    EditSelection.cpp: ajout de PageCenterInfo/computePageCenterX()")

    # ============ 5. mouseMove(): integration, 2 variantes selon 8.1 ============
    page_center_block = (
        '                // Snap to the page\'s own horizontal center (accounting for a Lined background\'s\n'
        '                // margin, if any). Competes with the ordinary X match on closeness, like equidistant\n'
        '                // snapping does, but never overrides a boosted (blue) match.\n'
        '                bool matchXIsBoostedForPageCenter = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n'
        '                if (!matchXIsBoostedForPageCenter && this->sourcePage) {\n'
        '                    PageCenterInfo pageCenter = computePageCenterX(this->sourcePage.get());\n'
        '                    double pageCenterOffset = pageCenter.centerX - (candidateX + width / 2.0);\n'
        '                    if (std::abs(pageCenterOffset) < tolerance &&\n'
        '                        (!matchX || std::abs(pageCenterOffset) < std::abs(matchX->offset))) {\n'
        '                        AlignmentMatch pageMatch{pageCenterOffset,\n'
        '                                                  pageCenter.centerX,\n'
        '                                                  visibleRect.y,\n'
        '                                                  visibleRect.y + visibleRect.height,\n'
        '                                                  false,\n'
        '                                                  false};\n'
        '                        pageMatch.isPageCenter = true;\n'
        '                        if (pageCenter.marginX) {\n'
        '                            pageMatch.hasPageMargin = true;\n'
        '                            pageMatch.pageMarginX = *pageCenter.marginX;\n'
        '                        }\n'
        '                        matchX = AlignmentSearchResult{pageCenterOffset, {pageMatch}};\n'
        '                    }\n'
        '                }\n\n'
    )
    if not has_8_1:
        old5 = (
            '                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n'
            '                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n\n'
        )
        new5 = old5 + page_center_block
    else:
        equidistant_call_args = "excluded, visibleRect))" if has_8_1_3 else "excluded))"
        old5 = (
            '                if (!matchYIsBoosted) {\n'
            '                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,\n'
            f'                                                              tolerance, this->sourceLayer, {equidistant_call_args} {{\n'
            '                        if (!matchY || std::abs(equidistantY->offset) < std::abs(matchY->offset)) {\n'
            '                            matchY = AlignmentSearchResult{equidistantY->offset, {*equidistantY}};\n'
            '                        }\n'
            '                    }\n'
            '                }\n\n'
        )
        new5 = old5 + page_center_block
    ok &= apply_edit(cpp, old5, new5, "EditSelection.cpp: mouseMove() integre le snap centre-de-page")

    # ============ 6. mouseMove(): copie des nouveaux champs (4 variantes selon 8.1/8.2) ============
    guide_old_variants = {
        (False, False): 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted}',
        (True, False): 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement}',
        (False, True): 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide}',
        (True, True): 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement}',
    }
    old6 = guide_old_variants[(has_8_1, has_8_2)]
    new6 = old6[:-1] + ', g.isPageCenter, g.hasPageMargin, g.pageMarginX}'
    text = cpp.read_text(encoding="utf-8")
    n6 = text.count(old6)
    if n6 == 2:
        text = text.replace(old6, new6)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: mouseMove() copie isPageCenter/hasPageMargin/pageMarginX ({n6} occurrences)")
    elif text.count(new6) > 0:
        print("[SKIP]  EditSelection.cpp: mouseMove() deja a jour.")
    else:
        print(f"[ECHEC] EditSelection.cpp: mouseMove() - motif trouve {n6} fois (attendu 2)")
        ok = False

    # ============ 7. paint(): 4 variantes selon 8.1/8.2 ============
    paint_variants = {
        (False, False): (
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
            '        }\n',
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isPageCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);  // gray\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '            if (guide.isPageCenter && guide.hasPageMargin) {\n'
            '                double mx = guide.pageMarginX * zoom;\n'
            '                cairo_move_to(cr, mx, guide.from * zoom);\n'
            '                cairo_line_to(cr, mx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
        ),
        (True, False): (
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            if (!guide.equidistantGaps.empty()) {\n'
            '                // Equidistant match: one double-headed arrow per gap in the chain, drawn horizontally\n'
            '                // (this is a horizontal row being equally spaced along X) at a fixed Y offset\n'
            '                // (equidistantPlacement) below the row.\n'
            '                double py = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);\n'
            '                }\n'
            '                continue;\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n',
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isPageCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);  // gray\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            if (!guide.equidistantGaps.empty()) {\n'
            '                // Equidistant match: one double-headed arrow per gap in the chain, drawn horizontally\n'
            '                // (this is a horizontal row being equally spaced along X) at a fixed Y offset\n'
            '                // (equidistantPlacement) below the row.\n'
            '                double py = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);\n'
            '                }\n'
            '                continue;\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '            if (guide.isPageCenter && guide.hasPageMargin) {\n'
            '                double mx = guide.pageMarginX * zoom;\n'
            '                cairo_move_to(cr, mx, guide.from * zoom);\n'
            '                cairo_line_to(cr, mx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
        ),
        (False, True): (
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, mid);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, mid);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            } else if (guide.isPageCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);  // gray\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '                if (guide.hasPageMargin) {\n'
            '                    double mx = guide.pageMarginX * zoom;\n'
            '                    cairo_move_to(cr, mx, guide.from * zoom);\n'
            '                    cairo_line_to(cr, mx, guide.to * zoom);\n'
            '                    cairo_stroke(cr);\n'
            '                }\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, mid);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, mid);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
        ),
        (True, True): (
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            } else if (!guide.equidistantGaps.empty()) {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '                double py = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);\n'
            '                }\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, mid);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, mid);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
            '        for (auto& guide: this->activeGuidesX) {\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            } else if (guide.isPageCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);  // gray\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '                if (guide.hasPageMargin) {\n'
            '                    double mx = guide.pageMarginX * zoom;\n'
            '                    cairo_move_to(cr, mx, guide.from * zoom);\n'
            '                    cairo_line_to(cr, mx, guide.to * zoom);\n'
            '                    cairo_stroke(cr);\n'
            '                }\n'
            '            } else if (!guide.equidistantGaps.empty()) {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '                double py = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);\n'
            '                }\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, guide.from * zoom);\n'
            '                cairo_line_to(cr, gx, mid);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, gx, mid);\n'
            '                cairo_line_to(cr, gx, guide.to * zoom);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n',
        ),
    }
    old7, new7 = paint_variants[(has_8_1, has_8_2)]
    ok &= apply_edit(cpp, old7, new7, "EditSelection.cpp: paint() rendu gris + ligne de marge")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
