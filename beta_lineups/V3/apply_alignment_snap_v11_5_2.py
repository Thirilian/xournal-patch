#!/usr/bin/env python3
"""
Patch 11.5.2 : CORRECTIF - dans certains cas, la guideline bleue de
croisement sur la grande ligne apparaissait ROUGE alors que la grille
etait parfaitement valide (tous les marqueurs affiches), confirme par
une capture d'ecran de l'utilisateur.

CAUSE : le patch 11.3 avait introduit une inversion largeur/hauteur.
Deux appels distincts a computeBlueGridX existent dans le code :
  1. Celui du patch 11.3 (verification de validite de la grille, pour
     decider verrouillage vs ancrage aux extremites) - utilisait par
     erreur `width` comme longueur de self.
  2. Celui, preexistant, qui calcule les marqueurs affiches a l'ecran -
     utilise correctement `height` (self est vertical dans la branche
     Y-boostee, donc sa longueur pertinente pour le regroupement en
     famille est sa hauteur, pas sa largeur/epaisseur).
Cette divergence pouvait faire echouer la verification de validite du
patch 11.3 alors meme que la grille etait bel et bien valide (comme le
prouvent les marqueurs affiches) - declenchant a tort le repere rouge
du patch 11.5. Meme bug, inverse, dans la branche X-boostee (miroir).

CORRECTIF : les deux appels utilisent desormais le meme parametre que
le calcul des marqueurs (height pour la branche Y-boostee, width pour
la branche X-boostee).

Modifie : src/core/control/tools/EditSelection.cpp (2 occurrences)

NECESSITE : apply_alignment_snap_v90.py + apply_alignment_snap_v11_5.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
"""
NEW_1 = """                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            // Patch 11.5.2: fixed a parameter mix-up from patch 11.3 - self is
                            // vertical here (crossing a horizontal big line), so its relevant length
                            // for family/grid matching is `height`, not `width` (matching the
                            // existing marker-computing call further below, which already used
                            // `height` correctly). The mismatch could make this check see an invalid
                            // grid even when a perfectly valid one (shown via markers) existed,
                            // wrongly triggering patch 11.5's red guide.
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
"""
OLD_2 = """                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
"""
NEW_2 = """                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            // Patch 11.5.2: see the Y-boosted branch above for the full explanation -
                            // self is horizontal here, so its relevant length is `width`, not `height`.
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
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
    if "isBoostedButFree" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] isBoostedButFree introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_5.py, puis relancez ce script.")
        sys.exit(1)
    if "11.5.2" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.5.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "EditSelection.cpp: parametre corrige (branche Y-boostee)")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "EditSelection.cpp: parametre corrige (branche X-boostee)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
