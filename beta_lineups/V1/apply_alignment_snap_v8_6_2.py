#!/usr/bin/env python3
"""
Patch 8.6.2 (depend de 8.6) : corrige une inversion de dimensions dans
l'appel a computeBlueGridX/Y depuis mouseMove(), qui empechait la "grille
bleue" de trouver le moindre trait de meme taille (et donc n'affichait
jamais aucun repere, meme dans le cas le plus simple a deux traits).

Le trait selectionne, quand l'axe Y est boost (donc le trait est VERTICAL,
fin en X et long en Y), a sa vraie "longueur" dans `height`, pas `width`
(qui est son epaisseur). L'appel passait `width` par erreur. Meme
inversion, symetrique, pour le cas ou l'axe X est boost (trait horizontal :
la longueur est `width`, pas `height`).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py

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
        print("        Appliquez d'abord apply_alignment_snap_v8_6.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        cpp,
        old="                if (matchYIsBoosted && yBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,\n",
        new="                if (matchYIsBoosted && yBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,\n",
        label="EditSelection.cpp: correction dimension (self vertical -> height)",
    )
    ok &= apply_edit(
        cpp,
        old="                if (matchXIsBoosted && xBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,\n",
        new="                if (matchXIsBoosted && xBoostedTarget != nullptr) {\n"
            "                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,\n",
        label="EditSelection.cpp: correction dimension (self horizontal -> width)",
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
