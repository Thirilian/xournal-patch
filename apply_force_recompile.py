#!/usr/bin/env python3
"""
Force une recompilation systematique a l'ouverture de la fenetre d'edition
LaTeX, meme quand on edite une formule deja existante (utile pour que la
couleur - ou tout autre reglage dependant du template - soit toujours a jour).
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

def main():
    path = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not path.exists():
        print(f"[ECHEC] {path} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    text = path.read_text(encoding="utf-8")

    old = (
        '    g_signal_connect(this->getWindow(), "show", G_CALLBACK(+[](GtkWidget*, gpointer d) {\n'
        '                         auto texCtrl = static_cast<LatexController*>(d);\n'
        '                         if (!texCtrl->temporaryRender) {\n'
        '                             // Trigger an asynchronous compilation if we are not using a preexisting TexImage\n'
        '                             // Keep this after popup.show() so that if an error message is to be displayed (e.g.\n'
        '                             // missing Tex executable), it\'ll appear on top of the LatexDialog.\n'
        '                             LatexController::handleTexChanged(texCtrl);\n'
        '                         }\n'
        '                     }),\n'
        '                     texCtrl.get());'
    )
    new = (
        '    g_signal_connect(this->getWindow(), "show", G_CALLBACK(+[](GtkWidget*, gpointer d) {\n'
        '                         auto texCtrl = static_cast<LatexController*>(d);\n'
        '                         // Always trigger an asynchronous compilation on open, even when editing a\n'
        '                         // preexisting TexImage: its cached render may use a stale color (or other\n'
        '                         // template-dependent setting) that only gets baked in at compile time.\n'
        '                         // Keep this after popup.show() so that if an error message is to be displayed\n'
        '                         // (e.g. missing Tex executable), it\'ll appear on top of the LatexDialog.\n'
        '                         LatexController::handleTexChanged(texCtrl);\n'
        '                     }),\n'
        '                     texCtrl.get());'
    )

    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print("[SKIP] Déjà appliqué.")
            sys.exit(0)
        print("[ECHEC] Motif introuvable. Le fichier a peut-être trop divergé pour ce patch automatique.")
        sys.exit(1)
    if count > 1:
        print(f"[ECHEC] Motif trouvé {count} fois (doit être unique).")
        sys.exit(1)

    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("[OK] Recompilation forcée à l'ouverture appliquée avec succès.")

if __name__ == "__main__":
    main()
