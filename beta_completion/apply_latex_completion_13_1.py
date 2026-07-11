#!/usr/bin/env python3
"""
Patch 13.1 ("completion LaTeX") : premiere partie d'un compleeur
LaTeX de style Texmaker pour la boite de dialogue d'edition interne.

Charge des termes complets (ex: "\\dfrac{\u2022}{\u2022}", ou "\u2022" marque un
emplacement de type placeholder) depuis <dossier de config>/LaTeX_completion.txt
(un terme par ligne, non genere automatiquement - l'utilisateur y ajoute
ses propres termes lui-meme).

Des que l'utilisateur tape un backslash suivi d'au moins deux lettres
qui correspondent au debut d'un ou plusieurs termes du fichier, un
popover apparait sous le curseur, listant jusqu'a 4 correspondances
(classees par ordre d'apparition dans le fichier, la premiere en gras/
selectionnee par defaut). Le filtrage se poursuit en direct a chaque
frappe supplementaire, et le popover se ferme automatiquement des que
plus aucun terme ne correspond.

Fleches Haut/Bas : changent la selection. Entree : remplace le mot tape
par le terme complet. Echap : ferme le popover sans rien modifier.

NOTE : ce patch (13.1) n'implemente PAS encore la selection automatique
du premier placeholder ni la navigation Tab/Maj+Tab entre placeholders
- prevu pour un patch 13.2 separe.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.h
  - src/core/gui/dialog/IntEdLatexDialog.cpp

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """#pragma once

#include <string>  // for string

#include <cairo.h>               // for cairo_t
#include <gtk/gtk.h>             // for GtkWidget, GtkTextBuffer, GtkWindow"""
H_NEW0 = """#pragma once

#include <string>  // for string
#include <vector>  // for vector

#include <cairo.h>               // for cairo_t
#include <gtk/gtk.h>             // for GtkWidget, GtkTextBuffer, GtkWindow"""
H_OLD1 = """    std::string finalLatex;

    std::function<void()> callback;
};"""
H_NEW1 = """    std::string finalLatex;

    std::function<void()> callback;

    // Patch 13.1 (\"LaTeX completion\"): user-defined autocompletion, loaded from
    // <config folder>/LaTeX_completion.txt. Each non-empty line is a full LaTeX term (e.g.
    // \"\\dfrac{•}{•}\") to offer whenever the user types a backslash followed by at least the term's
    // own first two letters as a prefix.
    std::vector<std::string> completionTerms;  ///< All terms loaded from the file, in file order
    std::vector<std::string> currentMatches;   ///< Up to 4 terms currently matching the typed prefix
    int selectedMatchIndex = 0;
    xoj::util::GObjectSPtr<GtkWidget> completionPopover;

    void loadCompletionTerms();
    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash).
    std::string getCurrentLatexWord() const;
    void updateCompletionPopup();
    void showOrRefreshCompletionPopup();
    void hideCompletionPopup();
    void commitCompletion();
    void moveCompletionSelection(int delta);
};"""
CPP_OLD0 = """
#include \"IntEdLatexDialog.h\"

#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move
"""
CPP_NEW0 = """
#include \"IntEdLatexDialog.h\"

#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move
"""
CPP_OLD1 = """#include \"control/settings/LatexSettings.h\"  // for LatexSettings
#include \"gui/Builder.h\"
#include \"model/Font.h\"        // for XojFont
#include \"util/StringUtils.h\"  // for replace_pair, StringUtils
#include \"util/raii/CStringWrapper.h\"
"""
CPP_NEW1 = """#include \"control/settings/LatexSettings.h\"  // for LatexSettings
#include \"gui/Builder.h\"
#include \"model/Font.h\"        // for XojFont
#include \"util/PathUtil.h\"     // for getConfigFolder
#include \"util/StringUtils.h\"  // for replace_pair, StringUtils
#include \"util/raii/CStringWrapper.h\"
"""
CPP_OLD2 = """                     }),
                     texCtrl.get());

    g_signal_connect(this->getWindow(), \"delete-event\", G_CALLBACK(+[](GtkWidget*, GdkEvent*, gpointer d) -> gboolean {
                         auto self = static_cast<IntEdLatexDialog*>(d);
                         /**"""
CPP_NEW2 = """                     }),
                     texCtrl.get());

    // Patch 13.1 (\"LaTeX completion\"): load the user's custom terms once, then keep the completion
    // popup in sync with every edit, and intercept the few keys it needs while active (Up/Down to
    // move the selection, Enter to commit, Escape to dismiss) before GtkTextView's own handling of
    // them (e.g. Enter would otherwise insert a newline).
    this->loadCompletionTerms();
    g_signal_connect(this->getTextBuffer(), \"changed\", G_CALLBACK(+[](GtkTextBuffer*, gpointer d) {
                         static_cast<IntEdLatexDialog*>(d)->updateCompletionPopup();
                     }),
                     this);
    g_signal_connect(this->texBox, \"key-press-event\",
                     G_CALLBACK(+[](GtkWidget*, GdkEventKey* event, gpointer d) -> gboolean {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         if (self->currentMatches.empty()) {
                             return false;
                         }
                         switch (event->keyval) {
                             case GDK_KEY_Up:
                                 self->moveCompletionSelection(-1);
                                 return true;
                             case GDK_KEY_Down:
                                 self->moveCompletionSelection(1);
                                 return true;
                             case GDK_KEY_Return:
                             case GDK_KEY_KP_Enter:
                                 self->commitCompletion();
                                 return true;
                             case GDK_KEY_Escape:
                                 self->hideCompletionPopup();
                                 return true;
                             default:
                                 return false;
                         }
                     }),
                     this);

    g_signal_connect(this->getWindow(), \"delete-event\", G_CALLBACK(+[](GtkWidget*, GdkEvent*, gpointer d) -> gboolean {
                         auto self = static_cast<IntEdLatexDialog*>(d);
                         /**"""
CPP_OLD3 = """                          * dereferencing `self` after its destruction
                          */
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self->texCtrl.get());
                         return false;  // Let the callback from PopupWindowWrapper delete the dialog
                     }),
                     this);"""
CPP_NEW3 = """                          * dereferencing `self` after its destruction
                          */
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self->texCtrl.get());
                         // Patch 13.1: the completion \"changed\" handler is tied to `self` (not
                         // texCtrl.get()) - disconnect it too, for the same reason as above.
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self);
                         return false;  // Let the callback from PopupWindowWrapper delete the dialog
                     }),
                     this);"""
CPP_OLD4 = """            xoj::util::OwnedCString::assumeOwnership(gtk_text_buffer_get_text(this->textBuffer, &start, &end, false));
    return content.get();
}"""
CPP_NEW4 = """            xoj::util::OwnedCString::assumeOwnership(gtk_text_buffer_get_text(this->textBuffer, &start, &end, false));
    return content.get();
}

// Patch 13.1 (\"LaTeX completion\")

void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    auto completionFile = Util::getConfigFolder() / \"LaTeX_completion.txt\";
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // No completion file yet - not an error, just means no completions are offered.
        return;
    }
    std::string line;
    while (std::getline(ifs, line)) {
        while (!line.empty() && (line.back() == '\\r' || line.back() == '\\n')) {
            line.pop_back();
        }
        if (line.empty() || line[0] != '\\\\') {
            continue;
        }
        this->completionTerms.push_back(line);
    }
}

auto IntEdLatexDialog::getCurrentLatexWord() const -> std::string {
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

void IntEdLatexDialog::updateCompletionPopup() {
    std::string word = this->getCurrentLatexWord();
    // A backslash plus at least the term's own first two letters, i.e. 3 characters minimum.
    if (word.size() < 3) {
        this->hideCompletionPopup();
        return;
    }
    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        if (term.size() >= word.size() && term.compare(0, word.size(), word) == 0) {
            this->currentMatches.push_back(term);
            if (this->currentMatches.size() >= 4) {
                // completionTerms is in file order, so the first 4 matches found are already the
                // correct top-4 (earliest lines first).
                break;
            }
        }
    }
    if (this->currentMatches.empty()) {
        this->hideCompletionPopup();
        return;
    }
    this->selectedMatchIndex = 0;
    this->showOrRefreshCompletionPopup();
}

void IntEdLatexDialog::showOrRefreshCompletionPopup() {
#if GTK_MAJOR_VERSION == 3
    if (!this->completionPopover) {
        GtkWidget* popover = gtk_popover_new(this->texBox);
        gtk_popover_set_position(GTK_POPOVER(popover), GTK_POS_BOTTOM);
        gtk_widget_set_can_focus(popover, false);
        gtk_popover_set_modal(GTK_POPOVER(popover), false);
        this->completionPopover.reset(popover, xoj::util::adopt);
    }
    GtkWidget* popover = this->completionPopover.get();
    if (GtkWidget* oldChild = gtk_bin_get_child(GTK_BIN(popover))) {
        gtk_container_remove(GTK_CONTAINER(popover), oldChild);
    }
    GtkWidget* box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    for (size_t i = 0; i < this->currentMatches.size(); i++) {
        GtkWidget* label = gtk_label_new(nullptr);
        gtk_label_set_xalign(GTK_LABEL(label), 0.0);
        gtk_widget_set_margin_start(label, 8);
        gtk_widget_set_margin_end(label, 8);
        gtk_widget_set_margin_top(label, 4);
        gtk_widget_set_margin_bottom(label, 4);
        auto escaped =
                xoj::util::OwnedCString::assumeOwnership(g_markup_escape_text(this->currentMatches[i].c_str(), -1));
        // Patch 13.1: the selected row is simply shown in bold - a simple, theme-agnostic way to
        // highlight it without needing a dedicated CSS provider.
        if (static_cast<int>(i) == this->selectedMatchIndex) {
            std::string markup = std::string(\"<b>\") + escaped.get() + \"</b>\";
            gtk_label_set_markup(GTK_LABEL(label), markup.c_str());
        } else {
            gtk_label_set_markup(GTK_LABEL(label), escaped.get());
        }
        gtk_box_pack_start(GTK_BOX(box), label, false, false, 0);
    }
    gtk_container_add(GTK_CONTAINER(popover), box);
    gtk_widget_show_all(box);

    // Position the popover right below the text cursor.
    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GdkRectangle cursorRect;
    gtk_text_view_get_iter_location(GTK_TEXT_VIEW(this->texBox), &cursor, &cursorRect);
    int winX = 0;
    int winY = 0;
    gtk_text_view_buffer_to_window_coords(GTK_TEXT_VIEW(this->texBox), GTK_TEXT_WINDOW_WIDGET, cursorRect.x,
                                           cursorRect.y, &winX, &winY);
    GdkRectangle pointTo{winX, winY, 1, cursorRect.height};
    gtk_popover_set_pointing_to(GTK_POPOVER(popover), &pointTo);

    gtk_popover_popup(GTK_POPOVER(popover));
#endif
}

void IntEdLatexDialog::hideCompletionPopup() {
    this->currentMatches.clear();
    this->selectedMatchIndex = 0;
    if (this->completionPopover) {
        gtk_popover_popdown(GTK_POPOVER(this->completionPopover.get()));
    }
}

void IntEdLatexDialog::moveCompletionSelection(int delta) {
    if (this->currentMatches.empty()) {
        return;
    }
    int count = static_cast<int>(this->currentMatches.size());
    this->selectedMatchIndex = ((this->selectedMatchIndex + delta) % count + count) % count;
    this->showOrRefreshCompletionPopup();
}

void IntEdLatexDialog::commitCompletion() {
    if (this->currentMatches.empty()) {
        return;
    }
    std::string term = this->currentMatches[this->selectedMatchIndex];
    std::string word = this->getCurrentLatexWord();

    GtkTextIter cursor;
    gtk_text_buffer_get_iter_at_mark(this->textBuffer, &cursor, gtk_text_buffer_get_insert(this->textBuffer));
    GtkTextIter wordStart = cursor;
    // `word` is backslash + ASCII letters only, so its length in characters equals its length in bytes.
    gtk_text_iter_backward_chars(&wordStart, static_cast<gint>(word.size()));

    gtk_text_buffer_begin_user_action(this->textBuffer);
    gtk_text_buffer_delete(this->textBuffer, &wordStart, &cursor);
    gtk_text_buffer_insert(this->textBuffer, &wordStart, term.c_str(), -1);
    gtk_text_buffer_end_user_action(this->textBuffer);

    this->hideCompletionPopup();
    // Patch 13.2 will add: automatically select the first \"•\" placeholder here, and wire up
    // Tab/Shift+Tab to navigate between any remaining ones.
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
    h_file = Path("src/core/gui/dialog/IntEdLatexDialog.h")
    cpp_file = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    for p in (h_file, cpp_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "completionTerms" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.1 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H_OLD0, H_NEW0, "h: zone 1/2")
    ok &= apply_edit(h_file, H_OLD1, H_NEW1, "h: zone 2/2")
    ok &= apply_edit(cpp_file, CPP_OLD0, CPP_NEW0, "cpp: zone 1/5")
    ok &= apply_edit(cpp_file, CPP_OLD1, CPP_NEW1, "cpp: zone 2/5")
    ok &= apply_edit(cpp_file, CPP_OLD2, CPP_NEW2, "cpp: zone 3/5")
    ok &= apply_edit(cpp_file, CPP_OLD3, CPP_NEW3, "cpp: zone 4/5")
    ok &= apply_edit(cpp_file, CPP_OLD4, CPP_NEW4, "cpp: zone 5/5")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        print()
        print("N'oubliez pas de creer ~/.config/xournalpp/LaTeX_completion.txt")
        print("(un terme LaTeX complet par ligne, '\u2022' pour marquer un placeholder).")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
