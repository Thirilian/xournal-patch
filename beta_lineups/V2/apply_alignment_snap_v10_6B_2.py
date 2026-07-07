#!/usr/bin/env python3
"""
Patch 10.6B.2 : CORRECTIF de deux problemes lies a l'ancrage aux
extremites de la grande ligne (patch 8.6.5), signales par l'utilisateur.

1) DECALAGE D'UN CRAN (bug preexistant depuis le patch 8.6.5 lui-meme,
   masque jusqu'ici par le verrouillage systematique) : le commentaire
   du code disait "1 or 2 small lines crossing it (self included)", mais
   la condition verifiait `existingCount <= 1` - alors que existingCount
   compte self lui-meme (seule la grande ligne est exclue). "1 ou 2
   lignes, self inclus" correspond donc a existingCount <= 2, pas <= 1.
   Consequence : des qu'il y avait exactement 2 lignes (self + 1 autre),
   l'ancrage aux extremites ne se declenchait JAMAIS - remplace par le
   verrouillage (patch 8.6.8), qui donnait l'illusion d'un ancrage
   stable jusqu'a ce que "Graduation assist" (patch 10.6A) puisse le
   desactiver.

2) NOUVELLE REGLE explicitement demandee par l'utilisateur : si
   "Graduation assist" est desactivee, la restriction du nombre de
   lignes disparait entierement - l'ancrage aux extremites doit alors
   TOUJOURS s'appliquer, quel que soit le nombre de lignes deja
   accrochees a la grande ligne (puisqu'il n'y a alors aucune notion de
   "famille"/grille a proteger d'un conflit).

CORRECTIF : la condition devient
`!settings->isGraduationAssistEnabled() || existingCount <= 2` - le
verrouillage (branche else) n'est desormais atteint QUE si "Graduation
assist" est active ET qu'il y a 3 lignes ou plus.

Modifie : src/core/control/tools/EditSelection.cpp (2 occurrences,
branches X-boosted et Y-boosted)

NECESSITE : apply_alignment_snap_v10_6B.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_X = """                        if (existingCount <= 1) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
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
                        } else if (settings->isGraduationAssistEnabled()) {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X. Only makes sense together with
                            // the graduation/family grid preview (patch 10.6A) - if that's disabled,
                            // self is left free to slide along the big line instead of being locked.
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
                        if (!settings->isGraduationAssistEnabled() || existingCount <= 2) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
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
OLD_Y = """                        if (existingCount <= 1) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
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
                        } else if (settings->isGraduationAssistEnabled()) {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only makes sense together with the graduation/family grid preview (patch
                            // 10.6A) - if that's disabled, self is left free to slide along the big
                            // line instead of being locked.
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
"""
NEW_Y = """                        // See the Y-boosted branch above for the full explanation of this condition.
                        if (!settings->isGraduationAssistEnabled() || existingCount <= 2) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * LINE_END_ANCHOR_TOLERANCE_FACTOR;
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
    if "isGraduationAssistEnabled" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] isGraduationAssistEnabled introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v10_6B.py, puis relancez ce script.")
        sys.exit(1)

    ok = True
    ok &= apply_edit(cpp, OLD_X, NEW_X, "EditSelection.cpp: ancrage aux extremites (branche X-boosted, existingCount <= 2)")
    ok &= apply_edit(cpp, OLD_Y, NEW_Y, "EditSelection.cpp: ancrage aux extremites (branche Y-boosted, existingCount <= 2)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
