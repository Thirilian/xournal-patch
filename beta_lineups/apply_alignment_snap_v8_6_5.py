#!/usr/bin/env python3
"""
Patch 8.6.5 (depend de toute la chaine 8.6, testable avec tous les
patches disponibles appliques en amont) : ajoute deux points d'ancrage
speciaux aux deux extremites d'une grande ligne, actifs uniquement
lorsqu'elle n'a que 1 ou 2 petites lignes (le trait deplace inclus) qui
la croisent.

Une petite ligne peut desormais, en plus de l'accrochage habituel au
centre de la grande ligne (palier bleu), egalement accrocher sa PROPRE
position le long de la grande ligne pour tomber exactement sur l'une de
ses deux extremites - chaque extremite fonctionnant comme un point
d'ancrage independant. Quand ca arrive, un repere bleu de la MEME forme
que la petite ligne (meme orientation, meme etendue) s'affiche par-dessus
elle.

Ce script utilise des ancres COURTES basees sur du code (pas du texte de
commentaire), pour rester robuste face aux variations mineures de
formulation entre les differents chemins d'application possibles des
patches 8.6.4.x anterieurs.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  4) apply_alignment_snap_v8_6_4_5.py + v8_6_4_6.py

Independant des autres patches 8.X (8.1, 8.2, 8.3, 8.7, 8.8, 9.1) -
utilise des initialiseurs designes C++20 pour AlignmentGuide, robustes
quel que soit le nombre de champs supplementaires ajoutes par ces
patches.

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
    if "computeStartingZone" not in content:
        print("[ECHEC] computeStartingZone introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord toute la chaine 8.6 a 8.6.4.6, puis relancez ce script.")
        sys.exit(1)
    if "endpointGuideActiveX" in content:
        print("[SKIP] Le patch 8.6.5 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. declaration des drapeaux (ancre courte) ============
    ok &= apply_edit(
        cpp,
        old="                this->activeBoostedZone = 0;\n",
        new="                this->activeBoostedZone = 0;\n"
            "                // \"Line-end anchors\" (patch 8.6.5): flags/coordinates for the self-shaped blue overlay\n"
            "                // guide, set below when self snaps to one of the big line's own two endpoints.\n"
            "                bool endpointGuideActiveX = false;\n"
            "                double endpointGuideCoordX = 0;\n"
            "                double endpointGuideFromX = 0;\n"
            "                double endpointGuideToX = 0;\n"
            "                bool endpointGuideActiveY = false;\n"
            "                double endpointGuideCoordY = 0;\n"
            "                double endpointGuideFromY = 0;\n"
            "                double endpointGuideToY = 0;\n",
        label="EditSelection.cpp: declaration des drapeaux de reperes",
    )

    # ============ 2. detection Y (ancre courte : matchY->offset = ...) ============
    ok &= apply_edit(
        cpp,
        old="                    matchY->offset = targetCenter - refPointY;\n",
        new="                    matchY->offset = targetCenter - refPointY;\n\n"
            "                    // \"Line-end anchors\" (patch 8.6.5): while this big line has only 1 or 2 small\n"
            "                    // lines crossing it (self included), its own two endpoints become additional\n"
            "                    // anchor points for self's OTHER axis (the one along the big line's length) -\n"
            "                    // letting self snap so it crosses right at one end. Independent of the Y offset\n"
            "                    // above; only touches matchX.\n"
            "                    {\n"
            "                        xoj::util::Rectangle<double> bigShaft = targetShaft;\n"
            "                        int existingCount = 0;\n"
            "                        for (auto& elPtr: this->sourceLayer->getElements()) {\n"
            "                            Element* el = elPtr.get();\n"
            "                            if (el == yBoostedTarget) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            auto* otherStroke = dynamic_cast<Stroke*>(el);\n"
            "                            if (otherStroke == nullptr) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "                            bool isVerticalShaft =\n"
            "                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;\n"
            "                            if (!isVerticalShaft) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x,\n"
            "                                                shaft.x + shaft.width)) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double shaftCenterY = shaft.y + shaft.height / 2;\n"
            "                            if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            existingCount++;\n"
            "                        }\n"
            "                        if (existingCount <= 1) {\n"
            "                            double selfCenterX = candidateX + width / 2;\n"
            "                            double leftEnd = bigShaft.x;\n"
            "                            double rightEnd = bigShaft.x + bigShaft.width;\n"
            "                            double endpointTolerance = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                            double bestOffset = 0;\n"
            "                            bool found = false;\n"
            "                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {\n"
            "                                bestOffset = leftEnd - selfCenterX;\n"
            "                                found = true;\n"
            "                            }\n"
            "                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&\n"
            "                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {\n"
            "                                bestOffset = rightEnd - selfCenterX;\n"
            "                                found = true;\n"
            "                            }\n"
            "                            if (found) {\n"
            "                                matchX = AlignmentSearchResult{bestOffset, {}};\n"
            "                                endpointGuideActiveX = true;\n"
            "                                endpointGuideCoordX = selfCenterX + bestOffset;\n"
            "                                endpointGuideFromX = candidateY;\n"
            "                                endpointGuideToX = candidateY + height;\n"
            "                            }\n"
            "                        }\n"
            "                    }\n",
        label="EditSelection.cpp: detection des ancrages d'extremite (axe Y)",
    )

    # ============ 3. detection X (ancre courte : matchX->offset = ...) ============
    ok &= apply_edit(
        cpp,
        old="                    matchX->offset = targetCenter - refPointX;\n",
        new="                    matchX->offset = targetCenter - refPointX;\n\n"
            "                    // \"Line-end anchors\" (patch 8.6.5), mirrored for the X-boosted case (self\n"
            "                    // horizontal, big line vertical): its own two endpoints (top/bottom) become\n"
            "                    // additional anchor points for self's Y position.\n"
            "                    {\n"
            "                        xoj::util::Rectangle<double> bigShaft = targetShaft;\n"
            "                        int existingCount = 0;\n"
            "                        for (auto& elPtr: this->sourceLayer->getElements()) {\n"
            "                            Element* el = elPtr.get();\n"
            "                            if (el == xBoostedTarget) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            auto* otherStroke = dynamic_cast<Stroke*>(el);\n"
            "                            if (otherStroke == nullptr) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "                            bool isHorizontalShaft =\n"
            "                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;\n"
            "                            if (!isHorizontalShaft) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y,\n"
            "                                                shaft.y + shaft.height)) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            double shaftCenterX = shaft.x + shaft.width / 2;\n"
            "                            if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {\n"
            "                                continue;\n"
            "                            }\n"
            "                            existingCount++;\n"
            "                        }\n"
            "                        if (existingCount <= 1) {\n"
            "                            double selfCenterY = candidateY + height / 2;\n"
            "                            double topEnd = bigShaft.y;\n"
            "                            double bottomEnd = bigShaft.y + bigShaft.height;\n"
            "                            double endpointTolerance = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                            double bestOffset = 0;\n"
            "                            bool found = false;\n"
            "                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {\n"
            "                                bestOffset = topEnd - selfCenterY;\n"
            "                                found = true;\n"
            "                            }\n"
            "                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&\n"
            "                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {\n"
            "                                bestOffset = bottomEnd - selfCenterY;\n"
            "                                found = true;\n"
            "                            }\n"
            "                            if (found) {\n"
            "                                matchY = AlignmentSearchResult{bestOffset, {}};\n"
            "                                endpointGuideActiveY = true;\n"
            "                                endpointGuideCoordY = selfCenterY + bestOffset;\n"
            "                                endpointGuideFromY = candidateX;\n"
            "                                endpointGuideToY = candidateX + width;\n"
            "                            }\n"
            "                        }\n"
            "                    }\n",
        label="EditSelection.cpp: detection des ancrages d'extremite (axe X)",
    )

    # ============ 4. affichage du repere (ancre courte, structure de fermeture) ============
    ok &= apply_edit(
        cpp,
        old="                } else {\n"
            "                    this->activeGuidesY.clear();\n"
            "                }\n"
            "            }\n"
            "        } else {\n"
            "            this->activeGuidesX.clear();\n"
            "            this->activeGuidesY.clear();\n"
            "            this->activeBlueGridMarkers.clear();\n"
            "            this->activeBoostedTarget = nullptr;\n"
            "        }\n",
        new="                } else {\n"
            "                    this->activeGuidesY.clear();\n"
            "                }\n\n"
            "                // \"Line-end anchors\" (patch 8.6.5): push the self-shaped blue overlay guide(s), if\n"
            "                // any were found above. Uses designated initializers so this compiles regardless of\n"
            "                // how many extra trailing fields AlignmentGuide has picked up from other patches.\n"
            "                if (endpointGuideActiveX) {\n"
            "                    this->activeGuidesX.push_back(AlignmentGuide{.coordinate = endpointGuideCoordX,\n"
            "                                                                  .from = endpointGuideFromX,\n"
            "                                                                  .to = endpointGuideToX,\n"
            "                                                                  .isCenter = false,\n"
            "                                                                  .isBoosted = true});\n"
            "                }\n"
            "                if (endpointGuideActiveY) {\n"
            "                    this->activeGuidesY.push_back(AlignmentGuide{.coordinate = endpointGuideCoordY,\n"
            "                                                                  .from = endpointGuideFromY,\n"
            "                                                                  .to = endpointGuideToY,\n"
            "                                                                  .isCenter = false,\n"
            "                                                                  .isBoosted = true});\n"
            "                }\n"
            "            }\n"
            "        } else {\n"
            "            this->activeGuidesX.clear();\n"
            "            this->activeGuidesY.clear();\n"
            "            this->activeBlueGridMarkers.clear();\n"
            "            this->activeBoostedTarget = nullptr;\n"
            "        }\n",
        label="EditSelection.cpp: affichage du repere bleu en forme de petite ligne",
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
