#!/usr/bin/env python3
"""
Patch 8.4.3 (depend de 8.4) : ajoute une verification directionnelle
manquante dans l'eligibilite d'une cible pour l'assistant de snap
"croisement de ligne".

Jusqu'ici, seule la position PERPENDICULAIRE de la cible etait verifiee
(ex : pour une ligne verticale en cours de trace, seule sa colonne X etait
comparee a l'etendue X de la cible horizontale) - jamais que la cible se
trouve reellement dans la DIRECTION du trace (au-dessus si on tire vers le
haut, en dessous si on tire vers le bas). Une ligne/fleche horizontale
n'importe ou ailleurs sur la page, meme dans la direction opposee ou hors
de portee, pouvait donc etre acceptee comme cible valide - expliquant les
marqueurs apparaissant sans intersection reelle, et potentiellement les
hauteurs de snap multiples/incoherentes en presence de plusieurs objets
candidats sur la page.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v8_4.py
  3) apply_alignment_snap_v8_4_2.py

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
    cpp = Path("src/core/control/tools/BaseShapeHandler.cpp")
    if not cpp.exists():
        print("[ECHEC] BaseShapeHandler.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "applyLineCrossingSnap" not in content:
        print("[ECHEC] applyLineCrossingSnap introuvable dans BaseShapeHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_4.py (+ v8_4_2.py), puis relancez ce script.")
        sys.exit(1)
    if "must actually lie in the direction being drawn" in content:
        print("[SKIP] Le patch 8.4.3 semble deja applique.")
        sys.exit(0)

    ok = apply_edit(
        cpp,
        old='        if (drawingVertical) {\n'
            '            if (!targetIsHorizontal) {\n'
            '                continue;\n'
            '            }\n'
            '            double minX = std::min(shaft->first.x, shaft->second.x);\n'
            '            double maxX = std::max(shaft->first.x, shaft->second.x);\n'
            '            if (this->startPoint.x < minX || this->startPoint.x > maxX) {\n'
            '                continue;\n'
            '            }\n'
            '        } else {\n'
            '            if (!targetIsVertical) {\n'
            '                continue;\n'
            '            }\n'
            '            double minY = std::min(shaft->first.y, shaft->second.y);\n'
            '            double maxY = std::max(shaft->first.y, shaft->second.y);\n'
            '            if (this->startPoint.y < minY || this->startPoint.y > maxY) {\n'
            '                continue;\n'
            '            }\n'
            '        }\n\n'
            '        double distFromCurrent = std::abs(currentLength - targetLength);',
        new='        if (drawingVertical) {\n'
            '            if (!targetIsHorizontal) {\n'
            '                continue;\n'
            '            }\n'
            '            double minX = std::min(shaft->first.x, shaft->second.x);\n'
            '            double maxX = std::max(shaft->first.x, shaft->second.x);\n'
            '            if (this->startPoint.x < minX || this->startPoint.x > maxX) {\n'
            '                continue;\n'
            '            }\n'
            '            // The target must actually lie in the direction being drawn (above if drawing upward,\n'
            '            // below if drawing downward) - otherwise it could never really be "crossed" by extending\n'
            '            // the current line further, no matter how far it goes.\n'
            '            double targetY = shaft->first.y;  // either endpoint works: nearly equal for a horizontal target\n'
            '            if ((dy > 0 && targetY < this->startPoint.y) || (dy < 0 && targetY > this->startPoint.y)) {\n'
            '                continue;\n'
            '            }\n'
            '        } else {\n'
            '            if (!targetIsVertical) {\n'
            '                continue;\n'
            '            }\n'
            '            double minY = std::min(shaft->first.y, shaft->second.y);\n'
            '            double maxY = std::max(shaft->first.y, shaft->second.y);\n'
            '            if (this->startPoint.y < minY || this->startPoint.y > maxY) {\n'
            '                continue;\n'
            '            }\n'
            '            double targetX = shaft->first.x;\n'
            '            if ((dx > 0 && targetX < this->startPoint.x) || (dx < 0 && targetX > this->startPoint.x)) {\n'
            '                continue;\n'
            '            }\n'
            '        }\n\n'
            '        double distFromCurrent = std::abs(currentLength - targetLength);',
        label="BaseShapeHandler.cpp: verification directionnelle de la cible",
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
