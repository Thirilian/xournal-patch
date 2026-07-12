#!/usr/bin/env python3
"""
Patch 13.12 ("completion LaTeX") : deux correctifs demandes par
l'utilisateur.

1. Si le curseur n'est plus "colle" a un terme (entre ses lettres, ou
   a l'une de ses extremites) - par exemple apres un clic ailleurs
   dans le texte, ou un deplacement au clavier (fleches), SANS aucun
   changement de texte - le popup de completion doit desormais se
   fermer. Auparavant, seul le signal "changed" (changement de texte)
   declenchait la reevaluation ; le signal "mark-set" est maintenant
   egalement ecoute (filtre sur la marque "insert", c'est-a-dire le
   curseur specifiquement), et reutilise directement
   updateCompletionPopup() qui fait deja exactement ce qu'il faut.

2. Taper le caractere "{" ou "}" ne doit plus fermer le popup - de
   nombreux termes de LaTeX_completion.txt contiennent des accolades
   litterales dans leur propre syntaxe (ex: "\\dfrac{\u2022}{\u2022}"), et les
   taper a la main doit garder le popup ouvert et filtrant, plutot que
   de le fermer immediatement des qu'un caractere non-lettre apparait.

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (2 zones)

NECESSITE : apply_latex_completion.py (deja applique).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """    g_signal_connect(this->getTextBuffer(), \"changed\", G_CALLBACK(+[](GtkTextBuffer*, gpointer d) {
                         static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                     }),
                     this);
    g_signal_connect(this->texBox, \"key-press-event\",
"""
NEW_1 = """    g_signal_connect(this->getTextBuffer(), \"changed\", G_CALLBACK(+[](GtkTextBuffer*, gpointer d) {
                         static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                     }),
                     this);
    // Patch 13.12: the popup must also close as soon as the cursor is no longer \"stuck\" to a
    // matching word (between its letters, or at either end) - e.g. clicking elsewhere in the text, or
    // moving the cursor with the arrow keys, without any text actually changing. \"mark-set\" fires for
    // every mark move, so it's filtered down to the \"insert\" mark (the cursor) specifically.
    // updateCompletionPopup() already does exactly the right thing when called: re-checks the current
    // word at the (now new) cursor position and closes the popup if it no longer qualifies.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         if (mark == gtk_text_buffer_get_insert(buffer)) {
                             static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                         }
                     }),
                     this);
    g_signal_connect(this->texBox, \"key-press-event\",
"""
OLD_2 = """auto IntEdLatexDialog::getCurrentLatexWord() const -> std::string {
    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    while (true) {
        GtkTextIter prev = wordStart;
        if (!gtk_text_iter_backward_char(&prev)) {
            break;
        }
        gunichar c = gtk_text_iter_get_char(&prev);
        if (c > 127 || !g_ascii_isalpha(static_cast<gchar>(c))) {
            break;
        }
        wordStart = prev;
    }
    GtkTextIter beforeWord = wordStart;
    if (!gtk_text_iter_backward_char(&beforeWord)) {
        return \"\";
    }
    if (gtk_text_iter_get_char(&beforeWord) != '\\\\') {
        return \"\";
    }
    auto text = xoj::util::OwnedCString::assumeOwnership(
            gtk_text_buffer_get_text(this->textBuffer, &beforeWord, &cursor, false));
    return text.get();
}
"""
NEW_2 = """auto IntEdLatexDialog::getCurrentLatexWord() const -> std::string {
    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    while (true) {
        GtkTextIter prev = wordStart;
        if (!gtk_text_iter_backward_char(&prev)) {
            break;
        }
        gunichar c = gtk_text_iter_get_char(&prev);
        // Patch 13.12: \"{\" and \"}\" are accepted too (not just letters) - many terms in
        // LaTeX_completion.txt contain literal braces as part of their own syntax (e.g.
        // \"\\dfrac{\\u2022}{\\u2022}\"), and typing them by hand should keep the completion popup open and
        // filtering, rather than immediately closing it as soon as a non-letter character appears.
        bool isWordChar = c <= 127 && (g_ascii_isalpha(static_cast<gchar>(c)) || c == '{' || c == '}');
        if (!isWordChar) {
            break;
        }
        wordStart = prev;
    }
    GtkTextIter beforeWord = wordStart;
    if (!gtk_text_iter_backward_char(&beforeWord)) {
        return \"\";
    }
    if (gtk_text_iter_get_char(&beforeWord) != '\\\\') {
        return \"\";
    }
    auto text = xoj::util::OwnedCString::assumeOwnership(
            gtk_text_buffer_get_text(this->textBuffer, &beforeWord, &cursor, false));
    return text.get();
}
"""


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
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "navigatePlaceholder" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion.py, puis relancez ce script.")
        sys.exit(1)
    if "Patch 13.12" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.12 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "IntEdLatexDialog.cpp: zone 1/2 (signal mark-set)")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "IntEdLatexDialog.cpp: zone 2/2 (accolades acceptees)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
