#!/usr/bin/env python3
"""
Sous-patch 7.9 du systeme d'ancrage entre objets (style Canva/Figma).

Corrige un effet de bord du patch 7.8 : en rendant
isSmallCrossingBigPerpendicular() specifique a un axe, l'exclusion du
palier ordinaire sur l'axe CROISE ne se declenchait plus que si CET axe
avait lui-meme l'orientation valide - alors qu'elle doit se declencher des
qu'une eligibilite existe sur N'IMPORTE LEQUEL des deux axes (le bleu peut
tres bien s'afficher sur l'autre axe que celui qu'on est en train
d'examiner).

Les 4 verifications d'exclusion du palier ordinaire testent desormais les
DEUX orientations (CrossAxis::X OU CrossAxis::Y), alors que le palier bleu
lui-meme reste strictement limite a un seul axe (sinon on retombe sur le
bug du double-bleu deja corrige au patch 7.8).

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py
  4) apply_alignment_snap_v7_6.py
  5) apply_alignment_snap_v7_8.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    text = cpp.read_text(encoding="utf-8")
    if "CrossAxis" not in text:
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v7_8.py, puis relancez ce script.")
        sys.exit(1)

    replacements = [
        (
            'if (isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y) &&\n'
            '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
            '            continue;\n'
            '        }',
            'if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X) ||\n'
            '             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
            '            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {\n'
            '            continue;\n'
            '        }',
            "findAlignmentY: exclusion palier ordinaire (X OU Y)",
        ),
        (
            'if (isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) &&\n'
            '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
            '            continue;\n'
            '        }',
            'if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) ||\n'
            '             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y)) &&\n'
            '            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {\n'
            '            continue;\n'
            '        }',
            "findAlignmentX: exclusion palier ordinaire (X OU Y)",
        ),
    ]

    ok = True
    for old, new, label in replacements:
        n = text.count(old)
        if n == 0:
            if text.count(new) > 0:
                print(f"[SKIP]  {label}: déjà appliqué.")
                continue
            print(f"[ECHEC] {label}: motif introuvable")
            ok = False
            continue
        if n != 2:
            print(f"[ECHEC] {label}: motif trouvé {n} fois (attendu 2)")
            ok = False
            continue
        text = text.replace(old, new)
        print(f"[OK]    {label}: {n} occurrence(s) mise(s) à jour")

    cpp.write_text(text, encoding="utf-8")

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
