#!/usr/bin/env python3
"""
Patch 13.1.1 : CORRECTIF - signale par l'utilisateur : le fichier
~/.config/xournalpp/LaTeX_completion.txt n'existait jamais apres
application du patch 13.1, puisque le code ne faisait que LIRE le
fichier s'il existait deja, sans jamais le CREER.

CORRECTIF : si le fichier n'existe pas, il est desormais cree
automatiquement (avec un court en-tete explicatif en commentaire, et
un exemple concret : "\\dfrac{\u2022}{\u2022}") avant la tentative de
lecture - l'utilisateur a ainsi un fichier reel a ouvrir et modifier
tout de suite, plutot que de devoir le creer lui-meme de zero (avec le
bon nom, le bon emplacement et le bon format).

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_1.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    auto completionFile = Util::getConfigFolder() / \"LaTeX_completion.txt\";
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // No completion file yet - not an error, just means no completions are offered.
        return;
    }
"""
NEW_1 = """void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    Util::ensureFolderExists(Util::getConfigFolder());
    auto completionFile = Util::getConfigFolder() / \"LaTeX_completion.txt\";
    if (!fs::exists(completionFile)) {
        // Patch 13.1.1: create the file, with a short explanatory header, so the user has an actual
        // file to open and edit right away - rather than silently doing nothing until they create it
        // themselves from scratch (with the exact right name, location and format).
        std::ofstream ofs(completionFile);
        if (ofs.is_open()) {
            ofs << \"# LaTeX_completion.txt - one full LaTeX term per line.\\n\";
            ofs << \"# Use the bullet character (\\xe2\\x80\\xa2) to mark a placeholder the cursor can jump to\\n\";
            ofs << \"# once the term has been inserted. Lines not starting with a backslash (like this one)\\n\";
            ofs << \"# are ignored, so feel free to leave yourself comments.\\n\";
            ofs << \"#\\n\";
            ofs << \"# Example - typing \\\\df would offer this term below the cursor:\\n\";
            ofs << \"\\\\dfrac{\\xe2\\x80\\xa2}{\\xe2\\x80\\xa2}\\n\";
        }
    }
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // Still couldn't be read (e.g. permissions) - not a hard error, just means no completions are
        // offered.
        return;
    }
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "completionTerms" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] completionTerms introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion_13_1.py, puis relancez ce script.")
        sys.exit(1)
    if "13.1.1" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.1.1 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: le fichier LaTeX_completion.txt est desormais cree automatiquement")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
