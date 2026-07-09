#!/usr/bin/env python3
"""
Patch 8.6.3.3 (depend de 8.6.3.2) : re-simplifie l'exclusion des fleches
du palier bleu. Annule le threading du parametre selfIsArrow a travers
findAlignmentX/Y (retour aux signatures d'origine, boucle inconditionnelle),
remplace par un simple filtre apres coup dans mouseMove() : si le
resultat trouve est boost (bleu) ET que l'objet deplace est une fleche,
le match est simplement jete (matchX/matchY = nullopt) - la fleche n'a
alors aucun snap d'alignement du tout sur cet axe dans ce cas precis
(comportement accepte, plus simple que de retomber sur le palier
ordinaire).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_6_3_2.py

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
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "selfIsArrow" not in content:
        print("[ECHEC] selfIsArrow introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_3_2.py, puis relancez ce script.")
        sys.exit(1)
    if "self simply gets no alignment snap at all" in content:
        print("[SKIP] Le patch 8.6.3.3 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. findAlignmentY: retrait du parametre selfIsArrow ============
    ok &= apply_edit(
        cpp,
        old='static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect,\n'
            '                            bool selfIsArrow = false) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    if (!selfIsArrow)\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        new='static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        label="EditSelection.cpp: findAlignmentY - retrait du parametre selfIsArrow",
    )

    # ============ 2. findAlignmentX: retrait du parametre selfIsArrow ============
    ok &= apply_edit(
        cpp,
        old='static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect,\n'
            '                            bool selfIsArrow = false) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    if (!selfIsArrow)\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        new='static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        label="EditSelection.cpp: findAlignmentX - retrait du parametre selfIsArrow",
    )

    # ============ 3. mouseMove(): filtre apres coup au lieu du threading ============
    ok &= apply_edit(
        cpp,
        old='                // An arrow or double arrow, however small, is never eligible to be the "small"\n'
            '                // crossing side of a boosted (blue) match - only plain lines are.\n'
            '                bool selfIsArrow = false;\n'
            '                {\n'
            '                    auto selfElementsForArrowCheck = this->getElementsView();\n'
            '                    if (selfElementsForArrowCheck.size() == 1) {\n'
            '                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForArrowCheck.begin())) {\n'
            '                            selfIsArrow = selfStroke->getArrowKind() != ArrowKind::NONE;\n'
            '                        }\n'
            '                    }\n'
            '                }\n\n'
            '                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect, selfIsArrow);\n'
            '                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect, selfIsArrow);\n',
        new='                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n'
            '                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n\n'
            '                // An arrow or double arrow, however small, is never eligible to be the "small"\n'
            '                // crossing side of a boosted (blue) match - only plain lines are. If self is an\n'
            '                // arrow and the search above found one anyway, discard it outright: on that axis,\n'
            '                // self simply gets no alignment snap at all in that case (not even the ordinary\n'
            '                // tier), rather than threading an extra flag through findAlignmentX/Y themselves.\n'
            '                {\n'
            '                    auto selfElementsForArrowCheck = this->getElementsView();\n'
            '                    if (selfElementsForArrowCheck.size() == 1) {\n'
            '                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForArrowCheck.begin())) {\n'
            '                            if (selfStroke->getArrowKind() != ArrowKind::NONE) {\n'
            '                                if (matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted) {\n'
            '                                    matchX = std::nullopt;\n'
            '                                }\n'
            '                                if (matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted) {\n'
            '                                    matchY = std::nullopt;\n'
            '                                }\n'
            '                            }\n'
            '                        }\n'
            '                    }\n'
            '                }\n\n',
        label="EditSelection.cpp: mouseMove() - filtre apres coup au lieu du threading",
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
