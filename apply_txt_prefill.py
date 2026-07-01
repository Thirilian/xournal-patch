#!/usr/bin/env python3
"""
Remplace le préremplissage \\text{...} par le format "%txt\\n..." lorsqu'on
clique avec l'outil équation sur une textbox existante.
A lancer depuis la racine du dépôt xournalpp.
"""
import sys
from pathlib import Path

def main():
    path = Path("src/core/control/LatexController.cpp")
    if not path.exists():
        print(f"[ECHEC] {path} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")

    old = '            self->initialTex = "\\\\text{" + txt->getText() + "}";'
    new = '            self->initialTex = "%txt\\n" + txt->getText();'

    count = text.count(old)
    if count == 0:
        if text.count(new) == 1:
            print("[SKIP] Déjà appliqué.")
            sys.exit(0)
        print("[ECHEC] Motif introuvable. Le fichier a peut-être trop divergé pour ce patch automatique.")
        sys.exit(1)
    if count > 1:
        print(f"[ECHEC] Motif trouvé {count} fois (doit être unique).")
        sys.exit(1)

    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("[OK] Préremplissage %txt appliqué avec succès.")

if __name__ == "__main__":
    main()
