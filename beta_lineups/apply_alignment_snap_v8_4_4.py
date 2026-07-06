#!/usr/bin/env python3
"""
Patch 8.4.4 (depend de 8.4, 8.4.2, 8.4.3) : les reperes ne s'affichent
desormais que si la ligne en cours de trace a DEJA croise la ligne
perpendiculaire cible, plutot que de l'anticiper avant de l'atteindre.

Ajoute la condition : la position de la cible (Y pour une cible
horizontale, X pour une cible verticale) doit deja se trouver entre
l'origine du trace et son extremite actuelle (min/max des deux, quel que
soit le sens de trace).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v8_4.py
  3) apply_alignment_snap_v8_4_2.py
  4) apply_alignment_snap_v8_4_3.py

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
    if "must actually lie in the direction being drawn" not in content:
        print("[ECHEC] Verification directionnelle (8.4.3) introuvable dans BaseShapeHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_4.py, v8_4_2.py et v8_4_3.py.")
        sys.exit(1)
    if "ALREADY crossed the target's" in content:
        print("[SKIP] Le patch 8.4.4 semble deja applique.")
        sys.exit(0)

    ok = True

    ok &= apply_edit(
        cpp,
        old='            if ((dy > 0 && targetY < this->startPoint.y) || (dy < 0 && targetY > this->startPoint.y)) {\n'
            '                continue;\n'
            '            }\n'
            '        } else {',
        new='            if ((dy > 0 && targetY < this->startPoint.y) || (dy < 0 && targetY > this->startPoint.y)) {\n'
            '                continue;\n'
            '            }\n'
            '            // The markers only appear once the line being drawn has ALREADY crossed the target\'s\n'
            '            // height, not in anticipation of reaching it - i.e. targetY must already lie between the\n'
            '            // origin and the current (raw, pre-snap) endpoint.\n'
            '            if (targetY < std::min(this->startPoint.y, rawEnd.y) || targetY > std::max(this->startPoint.y, rawEnd.y)) {\n'
            '                continue;\n'
            '            }\n'
            '        } else {',
        label="BaseShapeHandler.cpp: condition 'deja croise' - branche verticale",
    )

    ok &= apply_edit(
        cpp,
        old='            if ((dx > 0 && targetX < this->startPoint.x) || (dx < 0 && targetX > this->startPoint.x)) {\n'
            '                continue;\n'
            '            }\n'
            '        }\n\n'
            '        double distFromCurrent = std::abs(currentLength - targetLength);',
        new='            if ((dx > 0 && targetX < this->startPoint.x) || (dx < 0 && targetX > this->startPoint.x)) {\n'
            '                continue;\n'
            '            }\n'
            '            if (targetX < std::min(this->startPoint.x, rawEnd.x) || targetX > std::max(this->startPoint.x, rawEnd.x)) {\n'
            '                continue;\n'
            '            }\n'
            '        }\n\n'
            '        double distFromCurrent = std::abs(currentLength - targetLength);',
        label="BaseShapeHandler.cpp: condition 'deja croise' - branche horizontale",
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
