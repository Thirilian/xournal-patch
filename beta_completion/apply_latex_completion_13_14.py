#!/usr/bin/env python3
"""
Patch 13.14 : CORRECTIF - l'utilisateur a signale que suite au patch
13.13, les caracteres du terme situes a GAUCHE du curseur lors de la
completion etaient touches (effaces puis reinseres), alors qu'ils ne
devraient jamais l'etre - ce sont au contraire ceux a DROITE du
curseur qui devraient etre reecrits, puisque ce sont eux qui vont etre
remplaces par la suite du terme.

CAUSE : le patch 13.13 supprimait puis reinserait toute la zone
[wordStart, curseur] (le prefixe deja tape a gauche), pour n'y
reinserer que les caracteres "manquants" detectes par un algorithme de
chevauchement - mais cet algorithme de chevauchement etait applique du
mauvais cote : le prefixe gauche (deja verifie comme correspondant
correctement au debut du terme) etait efface inutilement, ce qui
constitue le bug reellement signale.

CORRECTIF, plus simple que la version precedente : le prefixe a gauche
du curseur (`word`) n'est desormais plus jamais touche. Seule la
partie du terme pas encore tapee (remainingSuffix) est inseree, AU
curseur - et le texte qui suit deja le curseur, jusqu'a la longueur de
cette partie manquante, est simplement efface au prealable (ce sont
bien CES caracteres-la, a droite, qui sont "reecrits"). Plus besoin de
l'algorithme de detection de chevauchement (supprime) ni de sa
verification anti-coupure UTF-8 associee.

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_13.py (deja applique).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """void IntEdLatexDialog::commitCompletion() {
    if (this->currentMatches.empty()) {
        return;
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

    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    // `word` is backslash + ASCII letters/braces only, so its length in characters equals its length
    // in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    // Patch 13.13: if the cursor sits somewhere in the middle of an already-partially-typed term (e.g.
    // typing \"\\begin\" then \"align\" inside an existing pair of curly braces, cursor right before the
    // closing brace), only the characters actually MISSING from the term should be inserted -
    // inserting the whole term again would otherwise duplicate whatever already follows the cursor and
    // happens to match the term's own tail. `remainingSuffix` is the part of the term not accounted
    // for by `word` (the part before the cursor); the longest tail of it that already matches the text
    // right after the cursor is treated as \"already there\" and left untouched, instead of being
    // reinserted.
    std::string remainingSuffix = term.substr(word.size());
    GtkTextIter afterCursorEnd = cursor;
    gtk_text_iter_forward_chars(&afterCursorEnd, static_cast<gint>(remainingSuffix.size()));
    auto afterCursorOwned = xoj::util::OwnedCString::assumeOwnership(
            gtk_text_buffer_get_text(this->textBuffer, &cursor, &afterCursorEnd, false));
    std::string afterCursor = afterCursorOwned.get();
    size_t overlapLen = 0;
    for (size_t k = std::min(remainingSuffix.size(), afterCursor.size()); k > 0; --k) {
        // Never split a multi-byte UTF-8 character (the placeholder \"•\" is 3 bytes) - a genuine match
        // must start on a proper character boundary, not a continuation byte (0x80-0xBF).
        auto splitByte = static_cast<unsigned char>(remainingSuffix[remainingSuffix.size() - k]);
        if ((splitByte & 0xC0) == 0x80) {
            continue;
        }
        if (remainingSuffix.compare(remainingSuffix.size() - k, k, afterCursor, 0, k) == 0) {
            overlapLen = k;
            break;
        }
    }
    std::string toInsert = remainingSuffix.substr(0, remainingSuffix.size() - overlapLen);

    // Patch 13.2: a left-gravity mark at the insertion point survives the upcoming edit (unlike
    // GtkTextIters, which are invalidated by any buffer modification), so the exact start of the
    // freshly-inserted text can be found again afterwards.
    GtkTextMark* insertStartMark = gtk_text_buffer_create_mark(this->textBuffer, nullptr, &wordStart, true);

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &wordStart, &cursor);
    gtk_text_buffer_insert(this->textBuffer, &wordStart, toInsert.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();

    // Patch 13.2/13.13: search the FULL term's range - from the start of `word` to the true end of
    // the complete term, which now correctly spans both what was just inserted and whatever tail was
    // already present after the cursor - for a placeholder (searched strictly within this range, so
    // an unrelated \"•\" left over from an earlier completion elsewhere in the buffer is never picked up
    // by mistake) so the user can type straight over it. Tab/Shift+Tab navigation between further
    // placeholders is handled elsewhere.
    GtkTextIter insertStart;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &insertStart, insertStartMark);
    GtkTextIter termEnd = insertStart;
    gtk_text_iter_forward_chars(&termEnd, static_cast<gint>(g_utf8_strlen(term.c_str(), -1)));

    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &termEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    } else {
        // Patch 13.13: no placeholder in this term - place the cursor at its true end (past any
        // already-there tail characters that were left untouched above), exactly as if the whole term
        // had just been typed by hand in one go, regardless of where the cursor originally was or how
        // many characters were actually missing.
        gtk_text_buffer_place_cursor(this->textBuffer, &termEnd);
    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}
"""
NEW_1 = """void IntEdLatexDialog::commitCompletion() {
    if (this->currentMatches.empty()) {
        return;
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

    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    // `word` is backslash + ASCII letters/braces only, so its length in characters equals its length
    // in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    // Patch 13.2: a left-gravity mark at the insertion point survives the upcoming edit (unlike
    // GtkTextIters, which are invalidated by any buffer modification), so the exact start of the
    // freshly-inserted text can be found again afterwards.
    GtkTextMark* insertStartMark = gtk_text_buffer_create_mark(this->textBuffer, nullptr, &wordStart, true);

    // Patch 13.14: CORRECTIF - the characters to the LEFT of the cursor (`word`, already verified to
    // correctly match the start of the term) must never be touched at all - the previous version of
    // this code deleted and reinserted them unnecessarily, which was the actual bug reported by the
    // user (the left-hand prefix was being wiped out instead of the completion simply being appended
    // in place). Only the remaining, not-yet-typed part of the term is inserted, AT the cursor - and
    // whatever text already follows the cursor, up to that remaining part's own length, is discarded
    // first: those right-hand characters are the ones about to be entirely rewritten by the
    // completion, not the left-hand ones.
    std::string remainingSuffix = term.substr(word.size());
    GtkTextIter rightEnd = cursor;
    gtk_text_iter_forward_chars(&rightEnd, static_cast<gint>(remainingSuffix.size()));

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &cursor, &rightEnd);
    gtk_text_buffer_insert(this->textBuffer, &cursor, remainingSuffix.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();

    // Patch 13.2/13.13: search the FULL term's range - from the start of `word` (left-hand side,
    // untouched) to the true end of the complete term - for a placeholder (searched strictly within
    // this range, so an unrelated \"•\" left over from an earlier completion elsewhere in the buffer is
    // never picked up by mistake) so the user can type straight over it. Tab/Shift+Tab navigation
    // between further placeholders is handled elsewhere.
    GtkTextIter insertStart;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &insertStart, insertStartMark);
    GtkTextIter termEnd = insertStart;
    gtk_text_iter_forward_chars(&termEnd, static_cast<gint>(g_utf8_strlen(term.c_str(), -1)));

    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &termEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    } else {
        // Patch 13.13: no placeholder in this term - place the cursor at its true end, exactly as if
        // the whole term had just been typed by hand in one go, regardless of where the cursor
        // originally was or how many characters were actually missing.
        gtk_text_buffer_place_cursor(this->textBuffer, &termEnd);
    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "completionSuppressedByF1" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] completionSuppressedByF1 introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion_13_13.py, puis relancez ce script.")
        sys.exit(1)
    if "Patch 13.14" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.14 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: prefixe gauche jamais touche, seule la droite est reecrite")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
