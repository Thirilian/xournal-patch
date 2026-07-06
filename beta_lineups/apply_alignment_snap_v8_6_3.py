#!/usr/bin/env python3
"""
Patch 8.6.3 (depend de 8.6 + 8.6.2) : trois corrections.

1) Le patch 8.1 (equidistant generique) est desormais desactive de facon
   inconditionnelle sur l'axe de glissement des qu'un axe est boost -
   meme si computeBlueGridX/Y ne trouve aucun candidat (premiere petite
   ligne de sa taille sur la grande ligne).
2) PERPENDICULAR_CROSS_BOOST_FACTOR : 1.5 -> 2.25 (augmentation de 50%).
3) Cas A ("un seul autre trait de meme taille trouve") : nouvelle distance
   minimale BLUE_GRID_MIN_SPACING (5pt, ajustable) entre le trait
   selectionne et le trait fixe. En dessous de cette distance, le trait
   selectionne se fige a exactement cette distance (cote actuel), jusqu'a
   ce que le curseur passe au-dela de cette meme distance de l'autre
   cote - il "teleporte" alors sous le curseur et le suit a nouveau.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py

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
    if "computeBlueGridX" not in content:
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6.py + v8_6_2.py, puis relancez ce script.")
        sys.exit(1)
    if "BLUE_GRID_MIN_SPACING" in content:
        print("[SKIP] Le patch 8.6.3 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. augmentation du boost (point 2) ============
    ok &= apply_edit(
        cpp,
        old="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 1.5;",
        new="constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 2.25;",
        label="EditSelection.cpp: PERPENDICULAR_CROSS_BOOST_FACTOR 1.5 -> 2.25",
    )

    # ============ 2. nouvelle constante BLUE_GRID_MIN_SPACING ============
    ok &= apply_edit(
        cpp,
        old="constexpr double BLUE_GRID_LENGTH_EPS = 0.5;",
        new="constexpr double BLUE_GRID_LENGTH_EPS = 0.5;\n\n"
            "/**\n"
            " * Minimum allowed distance (in document points) between the moving object and the one fixed\n"
            " * same-size line found in the \"blue grid\" Case A (see computeBlueGridX/Y()). Trying to bring them\n"
            " * closer than this freezes the moving object at exactly this distance (on whichever side it\n"
            " * currently approaches from), until the cursor's raw position would put it further than this same\n"
            " * distance on the *other* side, at which point it jumps straight to the cursor's actual position and\n"
            " * resumes following it normally.\n"
            " */\n"
            "constexpr double BLUE_GRID_MIN_SPACING = 5.0;",
        label="EditSelection.cpp: nouvelle constante BLUE_GRID_MIN_SPACING",
    )

    # ============ 3. Cas A : zone morte de distance minimale (point 3), 2 occurrences ============
    # ============    identiques (computeBlueGridX et computeBlueGridY)                       ============
    old_case_a = (
        "    if (otherPositions.size() == 1) {\n"
        "        double fixedPos = otherPositions[0];\n"
        "        double d = std::abs(selfPos - fixedPos);\n"
        "        if (d < 1e-6) {\n"
        "            return std::nullopt;\n"
        "        }\n"
        "        double sign = (selfPos >= fixedPos) ? 1.0 : -1.0;\n"
        "        std::vector<double> markers;\n"
        "        for (double p = selfPos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {\n"
        "            markers.push_back(p);\n"
        "        }\n"
        "        if (markers.empty()) {\n"
        "            return std::nullopt;\n"
        "        }\n"
        "        return BlueGridResult{std::nullopt, markers, perpendicular, selfLength / 2};\n"
    )
    new_case_a = (
        "    if (otherPositions.size() == 1) {\n"
        "        double fixedPos = otherPositions[0];\n"
        "        double signedD = selfPos - fixedPos;\n"
        "        double effectivePos = selfPos;\n"
        "        std::optional<double> forceOffset;\n"
        "        if (std::abs(signedD) < BLUE_GRID_MIN_SPACING) {\n"
        "            double clampSign = (signedD >= 0) ? 1.0 : -1.0;\n"
        "            effectivePos = fixedPos + clampSign * BLUE_GRID_MIN_SPACING;\n"
        "            forceOffset = effectivePos;\n"
        "        }\n"
        "        double d = std::abs(effectivePos - fixedPos);\n"
        "        if (d < 1e-6) {\n"
        "            return std::nullopt;\n"
        "        }\n"
        "        double sign = (effectivePos >= fixedPos) ? 1.0 : -1.0;\n"
        "        std::vector<double> markers;\n"
        "        for (double p = effectivePos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {\n"
        "            markers.push_back(p);\n"
        "        }\n"
        "        if (markers.empty()) {\n"
        "            return std::nullopt;\n"
        "        }\n"
        "        return BlueGridResult{forceOffset, markers, perpendicular, selfLength / 2};\n"
    )
    text = cpp.read_text(encoding="utf-8")
    n = text.count(old_case_a)
    if n == 2:
        text = text.replace(old_case_a, new_case_a)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: zone morte de distance minimale (Cas A, {n} occurrences)")
    elif text.count(new_case_a) > 0:
        print("[SKIP]  EditSelection.cpp: zone morte deja presente.")
    else:
        print(f"[ECHEC] EditSelection.cpp: Cas A - motif trouve {n} fois (attendu 2)")
        ok = False

    # ============ 4. suppression inconditionnelle de 8.1 (point 1) ============
    ok &= apply_edit(
        cpp,
        old="                if (matchYIsBoosted && yBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});\n"
            "                        }\n"
            "                        matchX = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateX + width / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                        matchXIsBoosted = true;\n"
            "                    }\n"
            "                }\n"
            "                if (matchXIsBoosted && xBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});\n"
            "                        }\n"
            "                        matchY = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateY + height / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                        matchYIsBoosted = true;\n"
            "                    }\n"
            "                }\n",
        new="                if (matchYIsBoosted && yBoostedTarget != nullptr) {\n"
            "                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is\n"
            "                    // boosted, even if no same-size crossing line is found below (e.g. self is the\n"
            "                    // first small line of its size on this big line) - the blue tier's own semantics\n"
            "                    // should never be second-guessed by the generic equidistant search.\n"
            "                    matchXIsBoosted = true;\n"
            "                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});\n"
            "                        }\n"
            "                        matchX = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateX + width / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                    }\n"
            "                }\n"
            "                if (matchXIsBoosted && xBoostedTarget != nullptr) {\n"
            "                    matchYIsBoosted = true;\n"
            "                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,\n"
            "                                                      this->sourceLayer, excluded)) {\n"
            "                        for (double pos: grid->markerPositions) {\n"
            "                            this->activeBlueGridMarkers.push_back(\n"
            "                                    BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});\n"
            "                        }\n"
            "                        matchY = grid->forceOffset\n"
            "                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{\n"
            "                                                   *grid->forceOffset - (candidateY + height / 2), {}}}\n"
            "                                         : std::nullopt;\n"
            "                    }\n"
            "                }\n",
        label="EditSelection.cpp: suppression inconditionnelle de 8.1 quand un axe est boost",
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
