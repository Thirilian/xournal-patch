#!/usr/bin/env python3
"""
Patch 8.6.7 (depend de 8.6.5, compatible avec 8.6.6) : corrige un bug reel
signale par l'utilisateur.

La ligne selectionnee, pendant le glissement, s'accroche desormais
dynamiquement au point de reference correspondant a la zone courante
(patch 8.6.4.6/8.6.6) - elle est donc DEJA a sa position finale correcte
au moment du relachement. Mais applyLineRepositionOnRelease() (patch
8.6.5) l'incluait aussi dans la liste des lignes a repositionner,
provoquant un second deplacement (visible seulement APRES la
deselection, puisque pendant que la ligne est selectionnee, son rendu
suit le deplacement en cours et masque le probleme).

Corrige en retirant la ligne selectionnee de la liste des lignes
deplacees au relachement - elle continue de servir uniquement a
determiner la longueur de reference ("meme taille que la ligne
deplacee").

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  4) apply_alignment_snap_v8_6_4_5.py + v8_6_4_6.py
  5) apply_alignment_snap_v8_6_5.py

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
    if "applyLineRepositionOnRelease" not in content:
        print("[ECHEC] applyLineRepositionOnRelease introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_5.py, puis relancez ce script.")
        sys.exit(1)
    if "deliberately NOT added to `family`" in content:
        print("[SKIP] Le patch 8.6.7 semble deja applique.")
        sys.exit(0)

    ok = apply_edit(
        cpp,
        old="    std::vector<Element*> family;\n"
            "    for (const Element* el: selfElements) {\n"
            "        if (isEligibleFamilyMember(el)) {\n"
            "            family.push_back(const_cast<Element*>(el));\n"
            "        }\n"
            "    }\n"
            "    for (auto& elPtr: layer->getElements()) {\n"
            "        Element* el = elPtr.get();\n"
            "        if (isEligibleFamilyMember(el)) {\n"
            "            family.push_back(el);\n"
            "        }\n"
            "    }\n"
            "    if (family.empty()) {\n"
            "        return;\n"
            "    }\n",
        new="    // The currently-selected line is deliberately NOT added to `family` here (patch 8.6.7): it was\n"
            "    // already dynamically anchored to the correct zone-specific reference point live during the drag\n"
            "    // (see the \"Dynamic anchor\" code in mouseMove()), and its final position was already committed by\n"
            "    // updateContent() just before this function runs. Repositioning it again here would move it a\n"
            "    // second time, off of its already-correct spot. selfElements is still used above purely to learn\n"
            "    // self's own length.\n"
            "    std::vector<Element*> family;\n"
            "    for (auto& elPtr: layer->getElements()) {\n"
            "        Element* el = elPtr.get();\n"
            "        if (isEligibleFamilyMember(el)) {\n"
            "            family.push_back(el);\n"
            "        }\n"
            "    }\n"
            "    if (family.empty()) {\n"
            "        return;\n"
            "    }\n",
        label="EditSelection.cpp: exclusion de la ligne selectionnee du repositionnement au relachement",
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
