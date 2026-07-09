#!/usr/bin/env python3
"""
Patch 11.3 : CORRECTIF - la regle "si 3+ lignes sont accrochees a une
grande ligne mais ne sont pas equidistantes, 'graduation assist' cesse
d'agir et les lignes de meme taille peuvent glisser librement le long
de la grande ligne (mais l'ancrage aux extremites fonctionne encore)"
avait disparu (confirmee comme cassee suite a une question de
l'utilisateur).

CAUSE : deux mecanismes distincts, ajoutes a des moments differents,
ne communiquaient pas entre eux :
  1. computeBlueGridX/Y() (patch 8.6) verifie correctement que les
     lignes forment une grille reguliere (tous les ecarts sont des
     multiples exacts du plus petit ecart) - sinon, retourne nullopt
     (aucun marqueur, aucun forcage).
  2. Le verrouillage "Lock X/Y to start" (patch 8.6.8), qui s'execute
     AVANT l'appel a computeBlueGridX/Y, se declenchait uniquement sur
     `existingCount > 2` (nombre de lignes) SANS jamais verifier si ces
     lignes formaient reellement une grille valide. Resultat : la
     ligne selectionnee restait bloquee meme quand computeBlueGridX/Y
     determinait ensuite qu'il n'y avait pas de grille valide - et
     l'ancrage aux extremites (mutuellement exclusif avec le
     verrouillage) ne se declenchait jamais non plus dans ce cas.

CORRECTIF : avant de verrouiller, appelle desormais computeBlueGridX/Y
pour verifier qu'une grille valide existe reellement. Si ce n'est pas
le cas, retombe sur l'ancrage aux extremites (exactement comme si
existingCount <= 2) - la ligne peut alors glisser librement le long de
la grande ligne (sauf a ses extremites, qui restent accrochees).

Modifie : src/core/control/tools/EditSelection.cpp (2 occurrences,
branches X-boosted et Y-boosted)

NECESSITE : apply_alignment_snap_v90.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_X = """                        // Endpoint anchoring applies whenever there are at most 2 small lines
                        // (self included) crossing the big line - matching the \"1 or 2 small lines\"
                        // intent of patch 8.6.5 (existingCount counts self too, so this is
                        // existingCount <= 2, not <= 1 as originally miscoded). If \"Graduation
                        // assist\" (patch 10.6A) is disabled, this restriction is lifted entirely:
                        // endpoint anchoring then always applies, regardless of how many lines are
                        // already boosted on the big line, since there is no family/grid concept to
                        // protect from conflicting with in that case.
                        if (!settings->isGraduationAssistEnabled() || existingCount <= 2) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                bestOffset = leftEnd - selfCenterX;
                                found = true;
                            }
                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                bestOffset = rightEnd - selfCenterX;
                                found = true;
                            }
                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X. Only reached when \"Graduation
                            // assist\" is enabled (see the condition above) - it only makes sense
                            // together with the graduation/family grid preview (patch 10.6A).
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
"""
NEW_X = """                        // Endpoint anchoring applies whenever there are at most 2 small lines
                        // (self included) crossing the big line - matching the \"1 or 2 small lines\"
                        // intent of patch 8.6.5 (existingCount counts self too, so this is
                        // existingCount <= 2, not <= 1 as originally miscoded). If \"Graduation
                        // assist\" (patch 10.6A) is disabled, this restriction is lifted entirely:
                        // endpoint anchoring then always applies, regardless of how many lines are
                        // already boosted on the big line, since there is no family/grid concept to
                        // protect from conflicting with in that case.
                        //
                        // Patch 11.3: with 3+ lines AND Graduation assist enabled, the \"Lock X to
                        // start\" branch below only makes sense if those lines actually form a valid,
                        // regular grid (see computeBlueGridX()'s own return value) - if they don't
                        // (e.g. irregularly spaced), there is no family to protect either, so this
                        // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                bestOffset = leftEnd - selfCenterX;
                                found = true;
                            }
                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                bestOffset = rightEnd - selfCenterX;
                                found = true;
                            }
                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, forming a valid regular grid (see the condition
                            // above), the line-end anchors don't apply - during a Top/Middle/Below
                            // mode transition, self's X position (along the big line's length) should
                            // stay exactly where it was when the drag started, rather than drifting
                            // with the raw mouse X. Only reached when \"Graduation assist\" is enabled
                            // and a valid grid was found - it only makes sense together with the
                            // graduation/family grid preview (patch 10.6A).
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
"""
OLD_Y = """                        // See the Y-boosted branch above for the full explanation of this condition.
                        if (!settings->isGraduationAssistEnabled() || existingCount <= 2) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                bestOffset = topEnd - selfCenterY;
                                found = true;
                            }
                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                bestOffset = bottomEnd - selfCenterY;
                                found = true;
                            }
                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only reached when \"Graduation assist\" is enabled (see the condition
                            // above).
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
"""
NEW_Y = """                        // See the Y-boosted branch above for the full explanation of this condition.
                        // Patch 11.3: see the Y-boosted branch above for the full explanation.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                bestOffset = topEnd - selfCenterY;
                                found = true;
                            }
                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                bestOffset = bottomEnd - selfCenterY;
                                found = true;
                            }
                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only reached when \"Graduation assist\" is enabled and a valid grid was
                            // found (see the condition above).
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
"""


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
    if "computeBlueGridX" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py, puis relancez ce script.")
        sys.exit(1)
    if "tryEndpointAnchor" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.3 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_X, NEW_X, "EditSelection.cpp: verrou X conditionne a une grille valide (branche Y-boosted)")
    ok &= apply_edit(cpp, OLD_Y, NEW_Y, "EditSelection.cpp: verrou Y conditionne a une grille valide (branche X-boosted)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
