#!/usr/bin/env python3
"""
Patch 8.6.3.2 (depend de la logique du palier bleu, presente depuis les
patches 6/7 - fonctionne avec ou sans 8.6/8.6.2/8.6.3) : exclut
definitivement les fleches et doubles fleches (quelle que soit leur
taille) du role "petit trait" du palier bleu. Seules les lignes simples
peuvent desormais declencher le palier bleu en tant qu'objet deplace.

Necessaire avant le patch 8.6.4 (division/fusion de traits au relachement)
pour eliminer tout besoin de gerer le cas d'une fleche coupee en deux.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py (fournit ArrowKind/getArrowKind())
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)

Independant des autres patches 8.X (ne touche que la signature et le
declenchement de la boucle du palier bleu, jamais son contenu interne
modifie par 8.6).

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
    if "CrossAxis" not in content:
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 a v7_9.py, puis relancez ce script.")
        sys.exit(1)
    if "selfIsArrow" in content:
        print("[SKIP] Le patch 8.6.3.2 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. findAlignmentY: parametre selfIsArrow ============
    ok &= apply_edit(
        cpp,
        old='static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        new='static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
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
        label="EditSelection.cpp: findAlignmentY - parametre selfIsArrow",
    )

    # ============ 2. findAlignmentX: parametre selfIsArrow ============
    ok &= apply_edit(
        cpp,
        old='static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);\n\n'
            '    // --- boosted (blue) tier: exclusive, uses shaft bounds ---\n'
            '    std::optional<AlignmentMatch> bestBoosted;\n'
            '    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();',
        new='static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
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
        label="EditSelection.cpp: findAlignmentX - parametre selfIsArrow",
    )

    # ============ 3. mouseMove(): calcul de selfIsArrow et transmission ============
    ok &= apply_edit(
        cpp,
        old='                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n'
            '                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n'
            '                                              this->sourceLayer, excluded, visibleRect);\n',
        new='                // An arrow or double arrow, however small, is never eligible to be the "small"\n'
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
        label="EditSelection.cpp: mouseMove() calcule et transmet selfIsArrow",
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
