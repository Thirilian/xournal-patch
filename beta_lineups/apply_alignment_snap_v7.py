#!/usr/bin/env python3
"""
Sous-patch 7/7 du systeme d'ancrage entre objets (style Canva/Figma). Ajoute :
  1) Les traits (Stroke) sont TOUJOURS juges via leurs bornes "hampe seule"
     (getShaftBounds(), premier+dernier point), dans les DEUX paliers, pas
     seulement le palier bleu. Une fleche ne propose donc plus aucun point
     d'ancrage lie a sa pointe, dans aucun cas de figure.
  2) TEXT_Y_CENTER_FRACTION : 0.2 -> 0.6.
  3) Quand une paire (objet deplace, autre objet) est eligible au palier
     bleu sur un axe, cet "autre objet" est desormais ignore par le palier
     ordinaire de l'AUTRE axe (croise) - evite qu'un match vert/rose
     redondant (ex: le centre le long d'une grande fleche) apparaisse en
     plus du bleu.

NECESSITE apply_alignment_snap_v1.py a v6.py deja appliques, dans cet ordre.
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "getShaftBounds" not in content:
        print("[ECHEC] getShaftBounds introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 à v6.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        cpp,
        old='constexpr double TEXT_Y_CENTER_FRACTION = 0.2;',
        new='constexpr double TEXT_Y_CENTER_FRACTION = 0.6;',
        label="EditSelection.cpp: TEXT_Y_CENTER_FRACTION 0.2 -> 0.6",
    )

    ok &= apply_edit(
        cpp,
        old='        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
            '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n'
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
            '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);',
        new='        xoj::util::Rectangle<double> snapped = getShaftBounds(el);\n'
            '        // An element eligible for the boosted (blue) perpendicular-cross relationship with this\n'
            '        // selection is skipped here entirely: its along-axis center (e.g. a long arrow\'s own\n'
            '        // vertical mid-point, on the crossed axis) shouldn\'t also offer a separate ordinary match.\n'
            '        if (isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height) &&\n'
            '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
            '            continue;\n'
            '        }\n'
            '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n'
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
            '        xoj::util::Rectangle<double> snapped = getShaftBounds(el);\n'
            '        if (isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height) &&\n'
            '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
            '            continue;\n'
            '        }\n'
            '        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);',
        label="EditSelection.cpp: findAlignmentY palier ordinaire (bornes hampe + exclusion croisée)",
    )

    ok &= apply_edit(
        cpp,
        old='        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
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
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);',
        new='        xoj::util::Rectangle<double> snapped = getShaftBounds(el);\n'
            '        // An element eligible for the boosted (blue) perpendicular-cross relationship with this\n'
            '        // selection is skipped here entirely: its along-axis center (e.g. a long arrow\'s own\n'
            '        // horizontal mid-point, on the crossed axis) shouldn\'t also offer a separate ordinary match.\n'
            '        if (isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height) &&\n'
            '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
            '            continue;\n'
            '        }\n'
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
            '        xoj::util::Rectangle<double> snapped = getShaftBounds(el);\n'
            '        if (isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height) &&\n'
            '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);',
        label="EditSelection.cpp: findAlignmentX palier ordinaire (bornes hampe + exclusion croisée)",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
