#!/usr/bin/env python3
"""
Patch 13.13 ("completion LaTeX") : trois correctifs demandes par
l'utilisateur.

1. Si le curseur se trouve entre les caracteres d'un terme DEJA
   COMPLET (correspondance EXACTE avec un terme du dictionnaire, pas
   seulement un prefixe), ce terme n'est plus propose - il n'y a rien
   a completer. Consequence naturelle : le popup ne s'ouvre plus
   pendant la simple navigation (fleches, clic) a l'interieur d'un
   terme deja entierement tape.

2. Si la popup a ete fermee explicitement avec F1, elle ne se
   rouvrira plus tant que l'utilisateur navigue seulement (sans
   taper) - un nouveau champ completionSuppressedByF1 bloque la
   reouverture via mark-set (navigation), mais est reinitialise des
   que l'utilisateur tape a nouveau (signal changed).

3. Si le curseur se trouve au milieu d'un terme partiellement tape
   (ex: "\\begin{{alig|}}", curseur juste avant l'accolade fermante),
   valider la completion n'ajoute desormais que les caracteres
   REELLEMENT manquants (au lieu de reinserer tout le terme, ce qui
   dupliquait ce qui suivait deja le curseur) - et place le curseur
   (ou le placeholder s'il y en a un) exactement a la fin du terme
   complet, comme si celui-ci venait d'etre tape entierement d'un
   coup, quelle qu'ait ete la position initiale du curseur.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.h (nouveau champ
    completionSuppressedByF1)
  - src/core/gui/dialog/IntEdLatexDialog.cpp (les 3 correctifs)

NECESSITE : apply_latex_completion_13_12.py (deja applique).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """    int selectedMatchIndex = 0;
    xoj::util::GObjectSPtr<GtkWidget> completionPopover;

    void loadCompletionTerms();
    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash)."""
H_NEW0 = """    int selectedMatchIndex = 0;
    xoj::util::GObjectSPtr<GtkWidget> completionPopover;

    /// Patch 13.13: set when F1 explicitly dismisses the popup, so that mere cursor navigation
    /// (mark-set) doesn't immediately reopen it - any actual typing (changed) resets it back to
    /// false, restoring normal behavior.
    bool completionSuppressedByF1 = false;

    void loadCompletionTerms();
    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash)."""
CPP_OLD0 = """
#include \"IntEdLatexDialog.h\"

#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move"""
CPP_NEW0 = """
#include \"IntEdLatexDialog.h\"

#include <algorithm>  // for min
#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move"""
CPP_OLD1 = """    // them (e.g. Enter would otherwise insert a newline).
    this->loadCompletionTerms();
    g_signal_connect(this->getTextBuffer(), \"changed\", G_CALLBACK(+[](GtkTextBuffer*, gpointer d) {
                         static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                     }),
                     this);
    // Patch 13.12: the popup must also close as soon as the cursor is no longer \"stuck\" to a"""
CPP_NEW1 = """    // them (e.g. Enter would otherwise insert a newline).
    this->loadCompletionTerms();
    g_signal_connect(this->getTextBuffer(), \"changed\", G_CALLBACK(+[](GtkTextBuffer*, gpointer d) {
                         // Patch 13.13: any actual typing resets the F1 suppression (see the field's
                         // own doc comment in the header).
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         self->completionSuppressedByF1 = false;
                         self->updateCompletionPopup();
                     }),
                     this);
    // Patch 13.12: the popup must also close as soon as the cursor is no longer \"stuck\" to a"""
CPP_OLD2 = """    // every mark move, so it's filtered down to the \"insert\" mark (the cursor) specifically.
    // updateCompletionPopup() already does exactly the right thing when called: re-checks the current
    // word at the (now new) cursor position and closes the popup if it no longer qualifies.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         if (mark == gtk_text_buffer_get_insert(buffer)) {
                             static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                         }
                     }),
                     this);"""
CPP_NEW2 = """    // every mark move, so it's filtered down to the \"insert\" mark (the cursor) specifically.
    // updateCompletionPopup() already does exactly the right thing when called: re-checks the current
    // word at the (now new) cursor position and closes the popup if it no longer qualifies.
    //
    // Patch 13.13: skipped entirely while completionSuppressedByF1 is set - navigating around the
    // text must never reopen a popup the user just explicitly dismissed with F1.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         if (mark == gtk_text_buffer_get_insert(buffer) && !self->completionSuppressedByF1) {
                             self->updateCompletionPopup();
                         }
                     }),
                     this);"""
CPP_OLD3 = """                                 // operates at the window level and could close the whole dialog
                                 // instead of (or in addition to) just this popup.
                                 case GDK_KEY_F1:
                                     self->hideCompletionPopup();
                                     return true;
                                 default:"""
CPP_NEW3 = """                                 // operates at the window level and could close the whole dialog
                                 // instead of (or in addition to) just this popup.
                                 case GDK_KEY_F1:
                                     // Patch 13.13: remember that F1 explicitly dismissed the popup,
                                     // so mere navigation doesn't reopen it - see the field's own doc
                                     // comment in the header.
                                     self->completionSuppressedByF1 = true;
                                     self->hideCompletionPopup();
                                     return true;
                                 default:"""
CPP_OLD4 = """    }
    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        if (term.size() >= word.size() && term.compare(0, word.size(), word) == 0) {
            this->currentMatches.push_back(term);
            if (this->currentMatches.size() >= 4) {
                // completionTerms is in file order, so the first 4 matches found are already the"""
CPP_NEW4 = """    }
    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        // Patch 13.13: a term STRICTLY longer than the current word only - an exact match means the
        // word is already a complete term on its own, with nothing left to complete, so it must never
        // be offered (and the popup must not reopen while merely navigating through it either - see
        // this same check's effect once currentMatches ends up empty below).
        if (term.size() > word.size() && term.compare(0, word.size(), word) == 0) {
            this->currentMatches.push_back(term);
            if (this->currentMatches.size() >= 4) {
                // completionTerms is in file order, so the first 4 matches found are already the"""
CPP_OLD5 = """    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    // `word` is backslash + ASCII letters only, so its length in characters equals its length in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    // Patch 13.2: a left-gravity mark at the insertion point survives the upcoming edit (unlike
    // GtkTextIters, which are invalidated by any buffer modification), so the exact start of the
    // freshly-inserted text can be found again afterwards."""
CPP_NEW5 = """    GtkTextIter cursor;
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
    // freshly-inserted text can be found again afterwards."""
CPP_OLD6 = """
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
}"""
CPP_NEW6 = """
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
}"""


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
    if "navigatePlaceholder" not in paths["cpp"].read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion.py et 13_12, puis relancez ce script.")
        sys.exit(1)
    if "completionSuppressedByF1" in paths["h"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.13 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["h"], H_OLD0, H_NEW0, "h: zone 1/1")
    ok &= apply_edit(paths["cpp"], CPP_OLD0, CPP_NEW0, "cpp: zone 1/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD1, CPP_NEW1, "cpp: zone 2/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD2, CPP_NEW2, "cpp: zone 3/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD3, CPP_NEW3, "cpp: zone 4/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD4, CPP_NEW4, "cpp: zone 5/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD5, CPP_NEW5, "cpp: zone 6/7")
    ok &= apply_edit(paths["cpp"], CPP_OLD6, CPP_NEW6, "cpp: zone 7/7")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
