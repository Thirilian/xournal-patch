#!/usr/bin/env python3
"""
Redefinit les niveaux de finesse du deplacement d'une selection aux fleches :
  - Fleche seule : 3 points (inchange)
  - Ctrl+Fleche  : 1 point (nouveau)
  - Alt+Fleche   : 0.5 point (avant : 1 point)
  - Shift+Fleche : 10 points (inchange)

Patch independant, un seul fichier touche : src/core/gui/XournalView.cpp.
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    f = Path("src/core/gui/XournalView.cpp")
    if not f.exists():
        print(f"[ECHEC] {f} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        f,
        old='constexpr int REGULAR_MOVE_AMOUNT = 3;\n'
            'constexpr int SMALL_MOVE_AMOUNT = 1;\n'
            'constexpr int LARGE_MOVE_AMOUNT = 10;\n',
        new='constexpr double REGULAR_MOVE_AMOUNT = 3;\n'
            'constexpr double FINE_MOVE_AMOUNT = 1;      // Ctrl+Arrow\n'
            'constexpr double SMALL_MOVE_AMOUNT = 0.5;   // Alt+Arrow\n'
            'constexpr double LARGE_MOVE_AMOUNT = 10;    // Shift+Arrow\n',
        label="XournalView.cpp: constantes de déplacement (double + FINE_MOVE_AMOUNT)",
    )

    ok &= apply_edit(
        f,
        old='        int d = REGULAR_MOVE_AMOUNT;\n'
            '        if (state == GDK_MOD1_MASK) {\n'
            '            d = SMALL_MOVE_AMOUNT;\n'
            '        } else if (state == GDK_SHIFT_MASK) {\n'
            '            d = LARGE_MOVE_AMOUNT;\n'
            '        }\n',
        new='        double d = REGULAR_MOVE_AMOUNT;\n'
            '        if (state == GDK_MOD1_MASK) {\n'
            '            d = SMALL_MOVE_AMOUNT;\n'
            '        } else if (state == GDK_CONTROL_MASK) {\n'
            '            d = FINE_MOVE_AMOUNT;\n'
            '        } else if (state == GDK_SHIFT_MASK) {\n'
            '            d = LARGE_MOVE_AMOUNT;\n'
            '        }\n',
        label="XournalView.cpp: branche Ctrl+Flèche (déplacement fin)",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
