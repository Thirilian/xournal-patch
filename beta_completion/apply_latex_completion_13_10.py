#!/usr/bin/env python3
"""
Patch 13.10 ("completion LaTeX") : CORRECTIF - le caractere de
placeholder "•" (bullet, U+2022) provoquait parfois une erreur au
moment de la generation LaTeX ("Invalid UTF-8 in child stdout..."),
signalee par l'utilisateur avec le message d'erreur exact.

CAUSE : le template LaTeX par defaut de Xournal++
(resources/default_template.tex) n'inclut aucun package de support
Unicode/glyphes etendus (pas de fontenc/textcomp, ni de moteur Unicode
natif). Avec les polices Computer Modern par defaut de pdflatex, le
caractere "•" brut n'a pas de glyphe correspondant - pdflatex
produit un avertissement "Missing character" dont la sortie brute
n'est pas un UTF-8 propre, ce qui casse le parsing de Xournal++.
Texmaker fonctionne probablement parce que son propre moteur/template
gere nativement ce genre de caracteres.

CORRECTIF (approche choisie par l'utilisateur - changer le caractere
plutot que corriger le template, pour rester local a cette
fonctionnalite) : le caractere de placeholder est desormais "@" - un
caractere ASCII simple, sans signification speciale en LaTeX standard,
qui compile proprement avec n'importe quel moteur/police sans package
supplementaire.

Ne touche QUE des fichiers NOUVELLEMENT crees - un
LaTeX_completion.txt deja existant (cree par un patch precedent, ou
edite par l'utilisateur) n'est jamais modifie retroactivement.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.cpp
  - src/core/gui/dialog/IntEdLatexDialog.h
  - src/util/PathUtil.cpp

NECESSITE : apply_latex_completion_13_9.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

CPP1_OLD0 = """        return;
    }
    std::string term = this->currentMatches[this->selectedMatchIndex];
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
CPP1_NEW0 = """        return;
    }
    std::string term = this->currentMatches[this->selectedMatchIndex];
    // Patch 13.4: a term that already contains at least one \"@\" placeholder always gets one more,
    // appended after a space - once the user has tabbed through the term's own placeholders, this
    // gives them a natural landing spot to keep typing right after the term, rather than having to
    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
    // untouched.
    if (term.find(\"@\") != std::string::npos) {
        term += \" @\";
    }
    std::string word = this->getCurrentLatexWord();
"""
CPP1_OLD1 = """
    this->hideCompletionPopup();

    // Patch 13.2: if the inserted term contains a \"•\" placeholder, select the first one (searched for
    // strictly within the just-inserted range, so an unrelated \"•\" left over from an earlier
    // completion elsewhere in the buffer is never picked up by mistake) so the user can type straight
    // over it. Tab/Shift+Tab navigation between further placeholders is handled elsewhere.
    GtkTextIter insertStart;"""
CPP1_NEW1 = """
    this->hideCompletionPopup();

    // Patch 13.2: if the inserted term contains a \"@\" placeholder, select the first one (searched for
    // strictly within the just-inserted range, so an unrelated \"@\" left over from an earlier
    // completion elsewhere in the buffer is never picked up by mistake) so the user can type straight
    // over it. Tab/Shift+Tab navigation between further placeholders is handled elsewhere.
    GtkTextIter insertStart;"""
CPP1_OLD2 = """
    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &insertEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    }"""
CPP1_NEW2 = """
    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"@\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &insertEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    }"""
CPP1_OLD3 = """}

auto IntEdLatexDialog::navigatePlaceholder(bool forward) -> bool {
    // Patch 13.3: Tab/Shift+Tab's normal action is blocked outright as soon as at least one \"•\"
    // placeholder exists ANYWHERE in the buffer - regardless of whether one is actually found in the
    // specific direction being searched.
    GtkTextIter bufStart;
    GtkTextIter bufEnd;
    gtk_text_buffer_get_bounds(this->textBuffer, &bufStart, &bufEnd);
    GtkTextIter searchLimitStart = bufStart;
    if (!gtk_text_iter_forward_search(&searchLimitStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, nullptr, nullptr,
                                       &bufEnd)) {
        return false;  // no placeholders left at all - let Tab/Shift+Tab behave normally
    }"""
CPP1_NEW3 = """}

auto IntEdLatexDialog::navigatePlaceholder(bool forward) -> bool {
    // Patch 13.3: Tab/Shift+Tab's normal action is blocked outright as soon as at least one \"@\"
    // placeholder exists ANYWHERE in the buffer - regardless of whether one is actually found in the
    // specific direction being searched.
    GtkTextIter bufStart;
    GtkTextIter bufEnd;
    gtk_text_buffer_get_bounds(this->textBuffer, &bufStart, &bufEnd);
    GtkTextIter searchLimitStart = bufStart;
    if (!gtk_text_iter_forward_search(&searchLimitStart, \"@\", GTK_TEXT_SEARCH_TEXT_ONLY, nullptr, nullptr,
                                       &bufEnd)) {
        return false;  // no placeholders left at all - let Tab/Shift+Tab behave normally
    }"""
CPP1_OLD4 = """    bool found;
    if (forward) {
        GtkTextIter searchFrom = selEnd;
        found = gtk_text_iter_forward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                              &placeholderStart, &placeholderEnd, &bufEnd);
    } else {
        GtkTextIter searchFrom = selStart;
        found = gtk_text_iter_backward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                               &placeholderStart, &placeholderEnd, &bufStart);
    }
    if (found) {"""
CPP1_NEW4 = """    bool found;
    if (forward) {
        GtkTextIter searchFrom = selEnd;
        found = gtk_text_iter_forward_search(&searchFrom, \"@\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                              &placeholderStart, &placeholderEnd, &bufEnd);
    } else {
        GtkTextIter searchFrom = selStart;
        found = gtk_text_iter_backward_search(&searchFrom, \"@\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                               &placeholderStart, &placeholderEnd, &bufStart);
    }
    if (found) {"""
H1_OLD0 = """
    // Patch 13.1 (\"LaTeX completion\"): user-defined autocompletion, loaded from
    // <config folder>/LaTeX_completion.txt. Each non-empty line is a full LaTeX term (e.g.
    // \"\\dfrac{•}{•}\") to offer whenever the user types a backslash followed by at least the term's
    // own first two letters as a prefix.
    std::vector<std::string> completionTerms;  ///< All terms loaded from the file, in file order
    std::vector<std::string> currentMatches;   ///< Up to 4 terms currently matching the typed prefix"""
H1_NEW0 = """
    // Patch 13.1 (\"LaTeX completion\"): user-defined autocompletion, loaded from
    // <config folder>/LaTeX_completion.txt. Each non-empty line is a full LaTeX term (e.g.
    // \"\\dfrac{@}{@}\") to offer whenever the user types a backslash followed by at least the term's
    // own first two letters as a prefix.
    std::vector<std::string> completionTerms;  ///< All terms loaded from the file, in file order
    std::vector<std::string> currentMatches;   ///< Up to 4 terms currently matching the typed prefix"""
H1_OLD1 = """    void hideCompletionPopup();
    void commitCompletion();
    void moveCompletionSelection(int delta);
    /// Patch 13.3: on Tab (forward=true) or Shift+Tab (forward=false), selects the next/previous \"•\"
    /// placeholder found looking right/left from the cursor (or current selection). Returns true if
    /// Tab/Shift+Tab's normal action should be blocked (i.e. at least one placeholder exists anywhere
    /// in the buffer), regardless of whether one was actually found in the searched direction."""
H1_NEW1 = """    void hideCompletionPopup();
    void commitCompletion();
    void moveCompletionSelection(int delta);
    /// Patch 13.3: on Tab (forward=true) or Shift+Tab (forward=false), selects the next/previous \"@\"
    /// placeholder found looking right/left from the cursor (or current selection). Returns true if
    /// Tab/Shift+Tab's normal action should be blocked (i.e. at least one placeholder exists anywhere
    /// in the buffer), regardless of whether one was actually found in the searched direction."""
CPP2_OLD0 = """        std::ofstream ofs(completionFile);
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
    return completionFile;"""
CPP2_NEW0 = """        std::ofstream ofs(completionFile);
        if (ofs.is_open()) {
            ofs << \"# LaTeX_completion.txt - one full LaTeX term per line.\\n\";
            ofs << \"# Use \\\"@\\\" to mark a placeholder the cursor can jump to once the term has been\\n\";
            ofs << \"# inserted. Lines not starting with a backslash (like this one) are ignored, so\\n\";
            ofs << \"# feel free to leave yourself comments.\\n\";
            ofs << \"#\\n\";
            ofs << \"# Example - typing \\\\df would offer this term below the cursor:\\n\";
            ofs << \"\\\\dfrac{@}{@}\\n\";
        }
    }
    return completionFile;"""


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
    paths = {
        "cpp1": Path("src/core/gui/dialog/IntEdLatexDialog.cpp"),
        "h1": Path("src/core/gui/dialog/IntEdLatexDialog.h"),
        "cpp2": Path("src/util/PathUtil.cpp"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "navigatePlaceholder" not in paths["cpp1"].read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord les patchs 13.1 a 13.9, puis relancez ce script.")
        sys.exit(1)
    if 'Use "@" to mark a placeholder' in paths["cpp2"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.10 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["cpp1"], CPP1_OLD0, CPP1_NEW0, "cpp1: zone 1/5")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD1, CPP1_NEW1, "cpp1: zone 2/5")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD2, CPP1_NEW2, "cpp1: zone 3/5")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD3, CPP1_NEW3, "cpp1: zone 4/5")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD4, CPP1_NEW4, "cpp1: zone 5/5")
    ok &= apply_edit(paths["h1"], H1_OLD0, H1_NEW0, "h1: zone 1/2")
    ok &= apply_edit(paths["h1"], H1_OLD1, H1_NEW1, "h1: zone 2/2")
    ok &= apply_edit(paths["cpp2"], CPP2_OLD0, CPP2_NEW0, "cpp2: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
