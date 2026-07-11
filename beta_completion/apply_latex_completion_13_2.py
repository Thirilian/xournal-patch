#!/usr/bin/env python3
"""
Patch 13.2 ("completion LaTeX") : a la validation d'une completion,
si le terme insere contient un placeholder ("•"), le premier est
desormais automatiquement selectionne - l'utilisateur peut alors taper
directement par-dessus.

La recherche du placeholder est strictement limitee au texte qui vient
d'etre insere (via un GtkTextMark, qui survit a la modification du
buffer contrairement aux GtkTextIter), pour ne jamais confondre avec un
"•" laisse par une completion precedente ailleurs dans le document.

La navigation Tab/Maj+Tab entre plusieurs placeholders n'est pas
encore implementee (prevue pour un patch ulterieur).

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_1_1.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """    // `word` is backslash + ASCII letters only, so its length in characters equals its length in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &wordStart, &cursor);
    gtk_text_buffer_insert(this->textBuffer, &wordStart, term.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();
    // Patch 13.2 will add: automatically select the first \"•\" placeholder here, and wire up
    // Tab/Shift+Tab to navigate between any remaining ones.
}
"""
NEW_1 = """    // `word` is backslash + ASCII letters only, so its length in characters equals its length in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    // Patch 13.2: a left-gravity mark at the insertion point survives the upcoming edit (unlike
    // GtkTextIters, which are invalidated by any buffer modification), so the exact start of the
    // freshly-inserted text can be found again afterwards.
    GtkTextMark* insertStartMark = gtk_text_buffer_create_mark(this->textBuffer, nullptr, &wordStart, true);

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &wordStart, &cursor);
    gtk_text_buffer_insert(this->textBuffer, &wordStart, term.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();

    // Patch 13.2: if the inserted term contains a \"•\" placeholder, select the first one (searched for
    // strictly within the just-inserted range, so an unrelated \"•\" left over from an earlier
    // completion elsewhere in the buffer is never picked up by mistake) so the user can type straight
    // over it. Tab/Shift+Tab navigation between further placeholders is handled elsewhere.
    GtkTextIter insertStart;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &insertStart, insertStartMark);
    GtkTextIter insertEnd = insertStart;
    gtk_text_iter_forward_chars(&insertEnd, static_cast<gint>(g_utf8_strlen(term.c_str(), -1)));

    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &insertEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "completionTerms" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] completionTerms introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion_13_1.py et 13_1_1, puis relancez ce script.")
        sys.exit(1)
    if "insertStartMark" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.2 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: selection automatique du premier placeholder")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
