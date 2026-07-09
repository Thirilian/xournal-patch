#!/usr/bin/env python3
"""
Patch 8.6.4.4 (depend de 8.6.4.3) - VERSION COMPLETE, remplace la version
precedente du meme nom.

1) Corrige une erreur de compilation reelle : getElementsView().clone()
   renvoie en realite std::vector<const Element*> (pas
   std::vector<Element*>), corrige avec un const_cast cible.

2) Implemente le point 3 signale par l'utilisateur : quand on saisit un
   trait deja "reduit" (mode Top/Below, ancre a une de ses extremites au
   lieu de son centre), le palier bleu cherchait toujours a accrocher son
   CENTRE geometrique vrai a la grande ligne - ce qui est incorrect pour
   un trait deja coupe. Desormais, si le centre reel ne donne pas de match
   boost, on essaie aussi de traiter chacune des deux extremites du trait
   comme un "centre virtuel" (recherche avec une boite de meme taille
   centree sur cette extremite) ; le meilleur des trois (centre reel,
   extremite haute, extremite basse) l'emporte. Le calcul de zone
   (Top/Middle/Below) est aussi ajuste pour utiliser ce point d'ancrage
   reel plutot que le centre geometrique vrai, pour rester coherent avec
   ce nouveau mecanisme.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  5) apply_alignment_snap_v8_6_4.py + v8_6_4_2.py + v8_6_4_3.py

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
    if "const std::vector<Element*>& selfElements" not in content and "already halved" not in content.lower():
        # both the type-fix and the "already halved" logic are absent - fresh state expected from 8.6.4.3
        if "const std::vector<const Element*>& selfElements" not in content:
            print("[ECHEC] Signature attendue introuvable dans EditSelection.cpp.")
            print("        Appliquez d'abord apply_alignment_snap_v8_6_4_3.py, puis relancez ce script.")
            sys.exit(1)
    if "Already halved" in content:
        print("[SKIP] Le patch 8.6.4.4 (version complete) semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. correction de type (si pas deja appliquee) ============
    if "const std::vector<Element*>& selfElements" in content:
        ok &= apply_edit(
            cpp,
            old="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
                "                                          const Element* bigLine, bool isXAxis, int zone,\n"
                "                                          const std::vector<Element*>& selfElements);",
            new="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
                "                                          const Element* bigLine, bool isXAxis, int zone,\n"
                "                                          const std::vector<const Element*>& selfElements);",
            label="EditSelection.cpp: declaration anticipee - correction du type",
        )
        ok &= apply_edit(
            cpp,
            old="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
                "                                          const Element* bigLine, bool isXAxis, int zone,\n"
                "                                          const std::vector<Element*>& selfElements) {\n"
                "    if (bigLine == nullptr) {\n"
                "        return;\n"
                "    }\n"
                "    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();\n"
                "    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);\n\n"
                "    auto isEligibleFamilyMember = [&](Element* el) -> bool {\n"
                "        if (el == bigLine) {\n"
                "            return false;\n"
                "        }\n"
                "        auto* stroke = dynamic_cast<Stroke*>(el);\n",
            new="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
                "                                          const Element* bigLine, bool isXAxis, int zone,\n"
                "                                          const std::vector<const Element*>& selfElements) {\n"
                "    if (bigLine == nullptr) {\n"
                "        return;\n"
                "    }\n"
                "    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();\n"
                "    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);\n\n"
                "    auto isEligibleFamilyMember = [&](const Element* el) -> bool {\n"
                "        if (el == bigLine) {\n"
                "            return false;\n"
                "        }\n"
                "        const auto* stroke = dynamic_cast<const Stroke*>(el);\n",
            label="EditSelection.cpp: definition - correction du type de la lambda",
        )
        ok &= apply_edit(
            cpp,
            old="    // take part in its own family's transformation.\n"
                "    for (Element* el: selfElements) {\n"
                "        if (isEligibleFamilyMember(el)) {\n"
                "            family.push_back(el);\n"
                "        }\n"
                "    }\n",
            new="    // take part in its own family's transformation. getElementsView() only exposes const pointers,\n"
                "    // but these elements are indeed ours to mutate (they are about to be scaled below).\n"
                "    for (const Element* el: selfElements) {\n"
                "        if (isEligibleFamilyMember(el)) {\n"
                "            family.push_back(const_cast<Element*>(el));\n"
                "        }\n"
                "    }\n",
            label="EditSelection.cpp: boucle self - const_cast cible",
        )
    else:
        print("[SKIP]  EditSelection.cpp: correction de type deja presente.")

    # ============ 2. "already halved" self detection (point 3) ============
    old_arrow_block = (
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
        '                }\n\n'
        '\n'
        '                // Equidistant ("equal spacing") snapping competes with the ordinary alignment match on\n'
        '                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.\n'
        '                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n'
        '                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n'
    )
    new_block = (
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
        '                }\n\n'
        '                // "Already halved" self detection (patch 8.6.4, point 3): if self doesn\'t already have\n'
        '                // a boosted match using its own true center, try treating each of its own edges as a\n'
        '                // "virtual center" instead (by searching with a same-size box centered on that edge) -\n'
        '                // this lets a line that was previously halved by the "half/double on release" feature\n'
        '                // (now anchored at one edge rather than truly centered) still find and reconnect to the\n'
        '                // big line it was cut from. Whichever of the three (real center, virtual near-edge\n'
        '                // center, virtual far-edge center) gives the closest boosted match wins; offsets are\n'
        '                // translated back to the real candidateX/candidateY frame before use. Arrows are\n'
        '                // excluded here too, matching the "only plain lines" scope of the whole feature.\n'
        '                //\n'
        '                // selfAnchorY/selfAnchorX track which point should stand in for "self\'s position" when\n'
        '                // computing the Top/Middle/Below zone further below: self\'s true center by default, or\n'
        '                // whichever edge just won a virtual match above (the point actually touching the big\n'
        '                // line right now).\n'
        '                double selfAnchorY = candidateY + height / 2;\n'
        '                double selfAnchorX = candidateX + width / 2;\n'
        '                {\n'
        '                    bool selfIsArrowForVirtualCheck = false;\n'
        '                    auto selfElementsForVirtualCheck = this->getElementsView();\n'
        '                    if (selfElementsForVirtualCheck.size() == 1) {\n'
        '                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForVirtualCheck.begin())) {\n'
        '                            selfIsArrowForVirtualCheck = selfStroke->getArrowKind() != ArrowKind::NONE;\n'
        '                        }\n'
        '                    }\n'
        '                    if (!selfIsArrowForVirtualCheck) {\n'
        '                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n'
        '                        if (!matchYAlreadyBoosted) {\n'
        '                            auto matchYVirtualTop =\n'
        '                                    findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,\n'
        '                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n'
        '                            auto matchYVirtualBottom =\n'
        '                                    findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,\n'
        '                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n'
        '                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&\n'
        '                                                 matchYVirtualTop->guides.front().isBoosted;\n'
        '                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&\n'
        '                                                    matchYVirtualBottom->guides.front().isBoosted;\n'
        '                            std::optional<double> bestRealOffsetY;\n'
        '                            if (topIsBoosted) {\n'
        '                                double realOffset = matchYVirtualTop->offset - height / 2;\n'
        '                                bestRealOffsetY = realOffset;\n'
        '                                matchY = AlignmentSearchResult{realOffset, matchYVirtualTop->guides};\n'
        '                                selfAnchorY = candidateY;  // the top edge (raw, pre-snap, like the default case)\n'
        '                            }\n'
        '                            if (bottomIsBoosted) {\n'
        '                                double realOffset = matchYVirtualBottom->offset + height / 2;\n'
        '                                if (!bestRealOffsetY || std::abs(realOffset) < std::abs(*bestRealOffsetY)) {\n'
        '                                    matchY = AlignmentSearchResult{realOffset, matchYVirtualBottom->guides};\n'
        '                                    selfAnchorY = candidateY + height;  // the bottom edge (raw, pre-snap)\n'
        '                                }\n'
        '                            }\n'
        '                        }\n'
        '                        bool matchXAlreadyBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n'
        '                        if (!matchXAlreadyBoosted) {\n'
        '                            auto matchXVirtualLeft =\n'
        '                                    findAlignmentX(candidateX - width / 2, width, candidateY, candidateY + height,\n'
        '                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n'
        '                            auto matchXVirtualRight =\n'
        '                                    findAlignmentX(candidateX + width / 2, width, candidateY, candidateY + height,\n'
        '                                                   tolerance, this->sourceLayer, excluded, visibleRect);\n'
        '                            bool leftIsBoosted = matchXVirtualLeft && !matchXVirtualLeft->guides.empty() &&\n'
        '                                                  matchXVirtualLeft->guides.front().isBoosted;\n'
        '                            bool rightIsBoosted = matchXVirtualRight && !matchXVirtualRight->guides.empty() &&\n'
        '                                                   matchXVirtualRight->guides.front().isBoosted;\n'
        '                            std::optional<double> bestRealOffsetX;\n'
        '                            if (leftIsBoosted) {\n'
        '                                double realOffset = matchXVirtualLeft->offset - width / 2;\n'
        '                                bestRealOffsetX = realOffset;\n'
        '                                matchX = AlignmentSearchResult{realOffset, matchXVirtualLeft->guides};\n'
        '                                selfAnchorX = candidateX;  // the left edge (raw, pre-snap, like the default case)\n'
        '                            }\n'
        '                            if (rightIsBoosted) {\n'
        '                                double realOffset = matchXVirtualRight->offset + width / 2;\n'
        '                                if (!bestRealOffsetX || std::abs(realOffset) < std::abs(*bestRealOffsetX)) {\n'
        '                                    matchX = AlignmentSearchResult{realOffset, matchXVirtualRight->guides};\n'
        '                                    selfAnchorX = candidateX + width;  // the right edge (raw, pre-snap)\n'
        '                                }\n'
        '                            }\n'
        '                        }\n'
        '                    }\n'
        '                }\n\n'
        '\n'
        '                // Equidistant ("equal spacing") snapping competes with the ordinary alignment match on\n'
        '                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.\n'
        '                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n'
        '                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n'
    )
    ok &= apply_edit(cpp, old_arrow_block, new_block, "EditSelection.cpp: ajout de la detection 'deja reduit' (point 3)")

    # ============ 3. calcul de zone : utiliser le point d'ancrage reel ============
    ok &= apply_edit(
        cpp,
        old="                if (yBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.y + targetShaft.height / 2;\n"
            "                    double signedOffset = (candidateY + height / 2) - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = yBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = false;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                } else if (xBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.x + targetShaft.width / 2;\n"
            "                    double signedOffset = (candidateX + width / 2) - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = xBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = true;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                }\n",
        new="                if (yBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.y + targetShaft.height / 2;\n"
            "                    double signedOffset = selfAnchorY - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = yBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = false;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                } else if (xBoostedTarget != nullptr) {\n"
            "                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();\n"
            "                    double targetCenter = targetShaft.x + targetShaft.width / 2;\n"
            "                    double signedOffset = selfAnchorX - targetCenter;\n"
            "                    double zoneR = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;\n"
            "                    this->activeBoostedTarget = xBoostedTarget;\n"
            "                    this->activeBoostedIsXAxis = true;\n"
            "                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);\n"
            "                }\n",
        label="EditSelection.cpp: calcul de zone utilise le point d'ancrage reel",
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
