#!/usr/bin/env python3
"""
Patch 8.2 (compatible avec ou sans les patches 8.1 / 8.1.2 deja appliques)
du systeme d'ancrage entre objets. Ajoute la scission de la ligne de
guidage en deux moities colorees independamment : la moitie cote objet
deplace et la moitie cote objet cible, chacune rose (bord) ou verte
(centre) selon son propre match. Le cas boosté (bleu) et le cas
equidistant (patch 8.1, fleches doubles) ne sont jamais scindes.

Ce script detecte automatiquement si apply_alignment_snap_v8_1.py a deja
ete applique (presence de "equidistantGaps") et adapte ses modifications
en consequence, pour que 8.1 et 8.2 puissent cohabiter sur le meme depot,
dans n'importe quel ordre.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py
  4) (optionnel) apply_alignment_snap_v8_1.py + v8_1_2.py

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
    if "CrossAxis" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 a v7_9.py, puis relancez ce script.")
        sys.exit(1)

    has_8_1 = "equidistantGaps" in cpp.read_text(encoding="utf-8")
    print(f"[INFO]  Patch 8.1 detecte : {'oui' if has_8_1 else 'non'}")

    ok = True

    # ============ 1. AlignmentMatch struct (EditSelection.cpp) ============
    if not has_8_1:
        old1 = (
            '/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' * `isCenter` is true if either of the two matched candidates was a center point (rather than an\n'
            ' * edge); `isBoosted` is true for the special "small stroke crossing a big perpendicular stroke,\n'
            ' * center-to-center" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '};\n'
        )
        new1 = (
            '/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' * `isCenter` is true if either of the two matched candidates was a center point (rather than an\n'
            ' * edge); `isBoosted` is true for the special "small stroke crossing a big perpendicular stroke,\n'
            ' * center-to-center" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.\n'
            ' * `selfIsCenter`/`otherIsCenter`/`selfOnFromSide` : see AlignmentGuide in EditSelection.h.\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    bool selfIsCenter = false;\n'
            '    bool otherIsCenter = false;\n'
            '    bool selfOnFromSide = true;\n'
            '};\n'
        )
    else:
        old1 = (
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    std::vector<std::pair<double, double>> equidistantGaps;\n'
            '    double equidistantPlacement = 0;\n'
            '};\n'
        )
        new1 = (
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    bool selfIsCenter = false;\n'
            '    bool otherIsCenter = false;\n'
            '    bool selfOnFromSide = true;\n'
            '    std::vector<std::pair<double, double>> equidistantGaps;\n'
            '    double equidistantPlacement = 0;\n'
            '};\n'
        )
    ok &= apply_edit(cpp, old1, new1, "EditSelection.cpp: nouveaux champs sur AlignmentMatch")

    # ============ 2. AlignmentGuide struct (EditSelection.h) ============
    if not has_8_1:
        old2 = (
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '    };\n'
        )
        new2 = (
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        bool selfIsCenter = false;\n'
            '        bool otherIsCenter = false;\n'
            '        bool selfOnFromSide = true;\n'
            '    };\n'
        )
    else:
        old2 = (
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        std::vector<std::pair<double, double>> equidistantGaps;\n'
            '        double equidistantPlacement = 0;\n'
            '    };\n'
        )
        new2 = (
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        bool selfIsCenter = false;\n'
            '        bool otherIsCenter = false;\n'
            '        bool selfOnFromSide = true;\n'
            '        std::vector<std::pair<double, double>> equidistantGaps;\n'
            '        double equidistantPlacement = 0;\n'
            '    };\n'
        )
    ok &= apply_edit(h, old2, new2, "EditSelection.h: nouveaux champs sur AlignmentGuide")

    # ============ 3. findAlignmentY : pass 1 (bestAny) + pass 2 (guides) ============
    # Inchange par le patch 8.1 (qui ne touche pas ces fonctions) : un seul cas necessaire.
    old3 = (
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                double dist = std::abs(cs.value - co.value);\n'
        '                if (dist < bestAnyDist) {\n'
        '                    bestAnyDist = dist;\n'
        '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
        '                                              co.value,\n'
        '                                              std::min(xLeft, snapped.x),\n'
        '                                              std::max(xRight, snapped.x + snapped.width),\n'
        '                                              cs.isCenter || co.isCenter,\n'
        '                                              false};\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    if (!bestAny) {\n'
        '        return std::nullopt;\n'
        '    }\n\n'
        '    // --- second pass: collect every match consistent with the chosen offset ---\n'
        '    double offset = bestAny->offset;\n'
        '    std::vector<AlignmentMatch> guides;\n'
        '    for (auto& elPtr: layer->getElements()) {\n'
        '        const Element* el = elPtr.get();\n'
        '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
        '            continue;\n'
        '        }\n'
        '        double eh = el->getElementHeight();\n'
        '        double ey = el->getY();\n'
        '        double ew = el->getElementWidth();\n'
        '        double ex = el->getX();\n'
        '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
        '        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X) ||\n'
        '             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
        '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
        '            continue;\n'
        '        }\n'
        '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
        '                    guides.push_back(AlignmentMatch{offset, co.value, std::min(xLeft, snapped.x),\n'
        '                                                     std::max(xRight, snapped.x + snapped.width),\n'
        '                                                     cs.isCenter || co.isCenter, false});\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    return AlignmentSearchResult{offset, guides};\n'
        '}\n\n'
        '/// Same as findAlignmentY(), but for the horizontal candidates'
    )
    new3 = (
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                double dist = std::abs(cs.value - co.value);\n'
        '                if (dist < bestAnyDist) {\n'
        '                    bestAnyDist = dist;\n'
        '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
        '                                              co.value,\n'
        '                                              std::min(xLeft, snapped.x),\n'
        '                                              std::max(xRight, snapped.x + snapped.width),\n'
        '                                              cs.isCenter || co.isCenter,\n'
        '                                              false};\n'
        '                    bestAny->selfIsCenter = cs.isCenter;\n'
        '                    bestAny->otherIsCenter = co.isCenter;\n'
        '                    bestAny->selfOnFromSide = xLeft <= snapped.x;\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    if (!bestAny) {\n'
        '        return std::nullopt;\n'
        '    }\n\n'
        '    // --- second pass: collect every match consistent with the chosen offset ---\n'
        '    double offset = bestAny->offset;\n'
        '    std::vector<AlignmentMatch> guides;\n'
        '    for (auto& elPtr: layer->getElements()) {\n'
        '        const Element* el = elPtr.get();\n'
        '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
        '            continue;\n'
        '        }\n'
        '        double eh = el->getElementHeight();\n'
        '        double ey = el->getY();\n'
        '        double ew = el->getElementWidth();\n'
        '        double ex = el->getX();\n'
        '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
        '        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X) ||\n'
        '             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
        '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
        '            continue;\n'
        '        }\n'
        '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
        '                    AlignmentMatch guide{offset, co.value, std::min(xLeft, snapped.x),\n'
        '                                         std::max(xRight, snapped.x + snapped.width),\n'
        '                                         cs.isCenter || co.isCenter, false};\n'
        '                    guide.selfIsCenter = cs.isCenter;\n'
        '                    guide.otherIsCenter = co.isCenter;\n'
        '                    guide.selfOnFromSide = xLeft <= snapped.x;\n'
        '                    guides.push_back(guide);\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    return AlignmentSearchResult{offset, guides};\n'
        '}\n\n'
        '/// Same as findAlignmentY(), but for the horizontal candidates'
    )
    ok &= apply_edit(cpp, old3, new3, "EditSelection.cpp: findAlignmentY - suivi self/other/fromSide")

    # ============ 4. findAlignmentX : pass 1 (bestAny) + pass 2 (guides) ============
    old4 = (
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                double dist = std::abs(cs.value - co.value);\n'
        '                if (dist < bestAnyDist) {\n'
        '                    bestAnyDist = dist;\n'
        '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
        '                                              co.value,\n'
        '                                              std::min(yTop, snapped.y),\n'
        '                                              std::max(yBottom, snapped.y + snapped.height),\n'
        '                                              cs.isCenter || co.isCenter,\n'
        '                                              false};\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    if (!bestAny) {\n'
        '        return std::nullopt;\n'
        '    }\n\n'
        '    // --- second pass: collect every match consistent with the chosen offset ---\n'
        '    double offset = bestAny->offset;\n'
        '    std::vector<AlignmentMatch> guides;\n'
        '    for (auto& elPtr: layer->getElements()) {\n'
        '        const Element* el = elPtr.get();\n'
        '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
        '            continue;\n'
        '        }\n'
        '        double ew = el->getElementWidth();\n'
        '        double ex = el->getX();\n'
        '        double eh = el->getElementHeight();\n'
        '        double ey = el->getY();\n'
        '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
        '        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) ||\n'
        '             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
        '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
        '                    guides.push_back(AlignmentMatch{offset, co.value, std::min(yTop, snapped.y),\n'
        '                                                     std::max(yBottom, snapped.y + snapped.height),\n'
        '                                                     cs.isCenter || co.isCenter, false});\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
    )
    new4 = (
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                double dist = std::abs(cs.value - co.value);\n'
        '                if (dist < bestAnyDist) {\n'
        '                    bestAnyDist = dist;\n'
        '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
        '                                              co.value,\n'
        '                                              std::min(yTop, snapped.y),\n'
        '                                              std::max(yBottom, snapped.y + snapped.height),\n'
        '                                              cs.isCenter || co.isCenter,\n'
        '                                              false};\n'
        '                    bestAny->selfIsCenter = cs.isCenter;\n'
        '                    bestAny->otherIsCenter = co.isCenter;\n'
        '                    bestAny->selfOnFromSide = yTop <= snapped.y;\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
        '    if (!bestAny) {\n'
        '        return std::nullopt;\n'
        '    }\n\n'
        '    // --- second pass: collect every match consistent with the chosen offset ---\n'
        '    double offset = bestAny->offset;\n'
        '    std::vector<AlignmentMatch> guides;\n'
        '    for (auto& elPtr: layer->getElements()) {\n'
        '        const Element* el = elPtr.get();\n'
        '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
        '            continue;\n'
        '        }\n'
        '        double ew = el->getElementWidth();\n'
        '        double ex = el->getX();\n'
        '        double eh = el->getElementHeight();\n'
        '        double ey = el->getY();\n'
        '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
        '        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) ||\n'
        '             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
        '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
        '            continue;\n'
        '        }\n'
        '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n'
        '        for (auto& cs: candidatesSelf) {\n'
        '            for (auto& co: candidatesOther) {\n'
        '                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
        '                    AlignmentMatch guide{offset, co.value, std::min(yTop, snapped.y),\n'
        '                                         std::max(yBottom, snapped.y + snapped.height),\n'
        '                                         cs.isCenter || co.isCenter, false};\n'
        '                    guide.selfIsCenter = cs.isCenter;\n'
        '                    guide.otherIsCenter = co.isCenter;\n'
        '                    guide.selfOnFromSide = yTop <= snapped.y;\n'
        '                    guides.push_back(guide);\n'
        '                }\n'
        '            }\n'
        '        }\n'
        '    }\n'
    )
    ok &= apply_edit(cpp, old4, new4, "EditSelection.cpp: findAlignmentX - suivi self/other/fromSide")

    # ============ 5. mouseMove(): copie des nouveaux champs (2 occurrences) ============
    text = cpp.read_text(encoding="utf-8")
    if not has_8_1:
        old5 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted}'
        new5 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide}'
    else:
        old5 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement}'
        new5 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement}'
    n5 = text.count(old5)
    if n5 == 2:
        text = text.replace(old5, new5)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: mouseMove() copie selfIsCenter/otherIsCenter/selfOnFromSide ({n5} occurrences)")
    elif text.count(new5) > 0:
        print("[SKIP]  EditSelection.cpp: mouseMove() deja a jour.")
    else:
        print(f"[ECHEC] EditSelection.cpp: mouseMove() - motif trouve {n5} fois (attendu 2)")
        ok = False

    # ============ 6. paint(): scission de la ligne en deux moities colorees ============
    if not has_8_1:
        old6 = (
            '    // Smart alignment guides: a bounded line connecting the moving selection to whichever element(s)\n'
            '    // it is currently aligned with. Pink for an edge alignment, green if either matched anchor was a\n'
            '    // center point, blue for the special "small stroke crossing a big perpendicular stroke" case.\n'
            '    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {\n'
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
            '    }'
        )
        new6 = (
            '    // Smart alignment guides: a bounded line connecting the moving selection to whichever element(s)\n'
            '    // it is currently aligned with. For a boosted (blue) match, drawn as a single line. Otherwise,\n'
            '    // split into two halves at the midpoint, each independently pink (edge match on that side) or\n'
            '    // green (center match on that side).\n'
            '    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n\n'
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
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, guide.from * zoom, gy);\n'
            '                cairo_line_to(cr, guide.to * zoom, gy);\n'
            '                cairo_stroke(cr);\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, guide.from * zoom, gy);\n'
            '                cairo_line_to(cr, mid, gy);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, mid, gy);\n'
            '                cairo_line_to(cr, guide.to * zoom, gy);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }'
        )
    else:
        old6 = (
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
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            if (!guide.equidistantGaps.empty()) {\n'
            '                // Equidistant match: one double-headed arrow per gap in the chain, drawn vertically\n'
            '                // (this is a vertical column being equally spaced along Y) at a fixed X offset\n'
            '                // (equidistantPlacement) to the right of the column.\n'
            '                double px = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);\n'
            '                }\n'
            '                continue;\n'
            '            }\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, guide.from * zoom, gy);\n'
            '            cairo_line_to(cr, guide.to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
        )
        new6 = (
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
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '                cairo_move_to(cr, guide.from * zoom, gy);\n'
            '                cairo_line_to(cr, guide.to * zoom, gy);\n'
            '                cairo_stroke(cr);\n'
            '            } else if (!guide.equidistantGaps.empty()) {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '                double px = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);\n'
            '                }\n'
            '            } else {\n'
            '                double mid = (guide.from + guide.to) / 2 * zoom;\n'
            '                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;\n'
            '                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;\n'
            '                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     firstHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, guide.from * zoom, gy);\n'
            '                cairo_line_to(cr, mid, gy);\n'
            '                cairo_stroke(cr);\n'
            '                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,\n'
            '                                     secondHalfIsCenter ? 0.2 : 0.8);\n'
            '                cairo_move_to(cr, mid, gy);\n'
            '                cairo_line_to(cr, guide.to * zoom, gy);\n'
            '                cairo_stroke(cr);\n'
            '            }\n'
            '        }\n'
        )
    ok &= apply_edit(cpp, old6, new6, "EditSelection.cpp: paint() scinde la ligne en deux moities colorees")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
