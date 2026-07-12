#!/usr/bin/env python3
"""
Patch 13.15 ("completion LaTeX") : deux correctifs supplementaires
demandes par l'utilisateur.

1. Si le curseur navigue (fleches, clic) au MILIEU d'un terme DEJA
   COMPLET (ex: "\\al|pha", curseur entre "al" et "pha", ou "\\alpha"
   correspond exactement a un terme du dictionnaire), ce terme n'est
   TOUJOURS PAS propose. Le patch 13.13 ne verifiait que le prefixe a
   GAUCHE du curseur (getCurrentLatexWord()), qui ne voit PAS le mot
   COMPLET si le curseur est au milieu - nouvelle fonction
   getFullLatexWordAroundCursor() qui scanne des DEUX cotes du
   curseur, verifiee en PRIORITE dans updateCompletionPopup().

2. Lors d'une completion, certains caracteres speciaux (pour
   l'instant, seulement l'accolade fermante) ne sont plus jamais
   effaces si ils se trouvent directement a droite du curseur. Plutot
   que d'essayer de le predire a l'avance (ce qui risquait de manger
   du texte non lie, comme signale precedemment), le terme manquant
   est desormais insere integralement, puis tout caractere protege
   DEVENU en double juste apres est supprime a la place - repete pour
   plusieurs caracteres proteges consecutifs si necessaire.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.h (nouvelle declaration
    getFullLatexWordAroundCursor)
  - src/core/gui/dialog/IntEdLatexDialog.cpp (implementation +
    verification prioritaire + logique de completion revue)

NECESSITE : apply_latex_completion_13_14.py (deja applique).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash).
    std::string getCurrentLatexWord() const;
    void updateCompletionPopup();
    void showOrRefreshCompletionPopup();
    void hideCompletionPopup();"""
H_NEW0 = """    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash).
    std::string getCurrentLatexWord() const;
    /// Patch 13.15: like getCurrentLatexWord(), but spans BOTH sides of the cursor - the full
    /// \"\\XX...\" word the cursor currently sits somewhere within, regardless of exactly where in it.
    /// Used specifically to detect an already-complete term while merely navigating through its
    /// middle (getCurrentLatexWord() alone only sees the left-hand portion in that case).
    std::string getFullLatexWordAroundCursor() const;
    void updateCompletionPopup();
    void showOrRefreshCompletionPopup();
    void hideCompletionPopup();"""
CPP_OLD0 = """    return text.get();
}

void IntEdLatexDialog::updateCompletionPopup() {
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer"""
CPP_NEW0 = """    return text.get();
}

auto IntEdLatexDialog::getFullLatexWordAroundCursor() const -> std::string {
    auto isWordChar = [](gunichar c) { return c <= 127 && (g_ascii_isalpha(static_cast<gchar>(c)) || c == '{' || c == '}'); };

    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));

    GtkTextIter wordStart = cursor;
    while (true) {
        GtkTextIter prev = wordStart;
        if (!gtk_text_iter_backward_char(&prev) || !isWordChar(gtk_text_iter_get_char(&prev))) {
            break;
        }
        wordStart = prev;
    }
    GtkTextIter beforeWord = wordStart;
    if (!gtk_text_iter_backward_char(&beforeWord) || gtk_text_iter_get_char(&beforeWord) != '\\\\') {
        return \"\";
    }

    GtkTextIter wordEnd = cursor;
    while (isWordChar(gtk_text_iter_get_char(&wordEnd))) {
        if (!gtk_text_iter_forward_char(&wordEnd)) {
            break;
        }
    }

    auto text = xoj::util::OwnedCString::assumeOwnership(
            gtk_text_buffer_get_text(this->textBuffer, &beforeWord, &wordEnd, false));
    return text.get();
}

void IntEdLatexDialog::updateCompletionPopup() {
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer"""
CPP_OLD1 = """        this->hideCompletionPopup();
        return;
    }
    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        // Patch 13.13: a term STRICTLY longer than the current word only - an exact match means the"""
CPP_NEW1 = """        this->hideCompletionPopup();
        return;
    }

    // Patch 13.15: CORRECTIF - if the cursor merely sits somewhere WITHIN an already-complete term
    // (e.g. navigating with the arrow keys into the middle of \"\\alpha\", cursor between \"al\" and
    // \"pha\"), `word` alone (which only sees the LEFT-hand portion, \"\\al\" here) doesn't reveal that the
    // FULL word is already an exact, complete term - \"\\alpha\" would still look like a valid prefix of
    // itself and get offered again. getFullLatexWordAroundCursor() spans both sides of the cursor to
    // catch this: if it exactly matches some term, there is nothing to complete, full stop - checked
    // before the ordinary prefix-matching loop below, taking priority over it.
    std::string fullWord = this->getFullLatexWordAroundCursor();
    for (const auto& term: this->completionTerms) {
        if (term == fullWord) {
            this->hideCompletionPopup();
            return;
        }
    }

    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        // Patch 13.13: a term STRICTLY longer than the current word only - an exact match means the"""
CPP_OLD2 = """    // first: those right-hand characters are the ones about to be entirely rewritten by the
    // completion, not the left-hand ones.
    std::string remainingSuffix = term.substr(word.size());
    GtkTextIter rightEnd = cursor;
    gtk_text_iter_forward_chars(&rightEnd, static_cast<gint>(remainingSuffix.size()));

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &cursor, &rightEnd);
    gtk_text_buffer_insert(this->textBuffer, &cursor, remainingSuffix.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();"""
CPP_NEW2 = """    // first: those right-hand characters are the ones about to be entirely rewritten by the
    // completion, not the left-hand ones.
    std::string remainingSuffix = term.substr(word.size());

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_insert(this->textBuffer, &cursor, remainingSuffix.c_str(), -1);

    // Patch 13.15: some characters, currently just the closing curly brace (extensible later), must
    // never be deleted if they were already directly at the cursor. Rather than trying to predict
    // this beforehand (which risks deleting into unrelated text that happens to follow, as previously
    // reported), the full remainingSuffix is inserted unconditionally above, and any now-duplicated
    // protected character immediately following it is removed afterwards instead - repeated for as
    // many consecutive protected characters as actually match (normally at most one, but this handles
    // a run of several in a row too).
    auto isProtectedChar = [](char c) { return c == '}'; };
    while (!remainingSuffix.empty() && isProtectedChar(remainingSuffix.back())) {
        GtkTextIter afterInsert = cursor;
        GtkTextIter oneMore = afterInsert;
        if (!gtk_text_iter_forward_char(&oneMore)) {
            break;
        }
        gunichar next = gtk_text_iter_get_char(&afterInsert);
        if (next > 127 || static_cast<char>(next) != remainingSuffix.back()) {
            break;
        }
        gtk_text_buffer_delete(this->textBuffer, &afterInsert, &oneMore);
        remainingSuffix.pop_back();
    }
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();"""


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
        "h": Path("src/core/gui/dialog/IntEdLatexDialog.h"),
        "cpp": Path("src/core/gui/dialog/IntEdLatexDialog.cpp"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "completionSuppressedByF1" not in paths["h"].read_text(encoding="utf-8"):
        print("[ECHEC] completionSuppressedByF1 introuvable dans IntEdLatexDialog.h.")
        print("        Appliquez d'abord apply_latex_completion_13_14.py, puis relancez ce script.")
        sys.exit(1)
    if "getFullLatexWordAroundCursor" in paths["h"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.15 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["h"], H_OLD0, H_NEW0, "h: zone 1/1")
    ok &= apply_edit(paths["cpp"], CPP_OLD0, CPP_NEW0, "cpp: zone 1/3")
    ok &= apply_edit(paths["cpp"], CPP_OLD1, CPP_NEW1, "cpp: zone 2/3")
    ok &= apply_edit(paths["cpp"], CPP_OLD2, CPP_NEW2, "cpp: zone 3/3")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
