#!/usr/bin/env python3
"""
Patch 13.4 ("completion LaTeX") : un terme qui contient deja au moins
un placeholder ("•") en recoit desormais toujours un de plus, ajoute
apres une espace a la toute fin. Une fois que l'utilisateur a navigue
(Tab) a travers les placeholders propres au terme, il dispose ainsi
d'un point d'atterrissage naturel pour continuer a taper juste apres
le terme, sans avoir a deplacer le curseur manuellement.

Les termes sans aucun placeholder (ex: "\\alpha") ne sont pas modifies.

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_3.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """    std::string term = this->currentMatches[this->selectedMatchIndex];
    std::string word = this->getCurrentLatexWord();
"""
NEW_1 = """    std::string term = this->currentMatches[this->selectedMatchIndex];
    // Patch 13.4: a term that already contains at least one \"•\" placeholder always gets one more,
    // appended after a space - once the user has tabbed through the term's own placeholders, this
    // gives them a natural landing spot to keep typing right after the term, rather than having to
    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
    // untouched.
    if (term.find(\"\\xe2\\x80\\xa2\") != std::string::npos) {
        term += \" \\xe2\\x80\\xa2\";
    }
    std::string word = this->getCurrentLatexWord();
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "navigatePlaceholder" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion_13_3.py, puis relancez ce script.")
        sys.exit(1)
    if "Patch 13.4" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.4 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: placeholder final ajoute apres les termes a placeholders")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
