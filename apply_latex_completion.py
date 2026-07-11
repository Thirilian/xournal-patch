#!/usr/bin/env python3
"""
apply_latex_completion.py : version consolidee, fusionnant
l'integralite de la serie "completion LaTeX" (patchs 13.1 a 13.11) en
un seul script.

Implemente un compleeur LaTeX de style Texmaker pour le dialogue
d'edition interne : charge des termes complets depuis
<dossier de config>/LaTeX_completion.txt (un par ligne, "•" pour
marquer un placeholder), propose jusqu'a 4 correspondances dans un
popover filtrant en direct des que l'utilisateur tape un backslash
suivi d'au moins deux lettres. Fleches Haut/Bas pour naviguer, Entree
pour valider, F1 pour fermer sans rien changer. Selection automatique
du premier placeholder a la validation, navigation Tab/Maj+Tab entre
placeholders (bloque leur action normale tant qu'il en reste). Chaque
placeholder non rempli est automatiquement rendu par \text{•} dans le
PDF de sortie (via une substitution avant compilation, sans toucher au
template).

Nouveau cadre "Autocompletion" dans l'onglet LaTeX des Preferences
(case a cocher + bouton "Ouvrir le dictionnaire"), traduit en anglais,
francais et allemand.

Contenu (patchs fusionnes, dans l'ordre) :
  13.1    : compleeur de base (popover, filtrage, navigation)
  13.1.1  : creation automatique du fichier de dictionnaire
  13.2    : selection automatique du premier placeholder
  13.3    : navigation Tab/Maj+Tab entre placeholders
  13.4    : placeholder final ajoute apres un terme a placeholders
  13.5    : correctif de crash (use-after-free du popover)
  13.6    : correctif du correctif (double liberation)
  13.8    : cadre "Autocompletion" dans les Preferences + touche F1
            (patch 13.7, fondu ici)
  13.9    : reordonnancement et reformulation du cadre
  13.10   : placeholder "@" (temporaire, remplace par 13.11)
  13.11   : retour a "•", rendu via \text{•} avant compilation -
            solution finale confirmee fonctionnelle par l'utilisateur

NE PAS confondre avec le patch 14.1 (suppression des popups pendant la
frappe) - explicitement exclu de cette consolidation a la demande de
l'utilisateur, et applicable separement.

Modifie :
  - po/de.po, po/fr.po, po/xournalpp.pot
  - src/core/control/latex/LatexGenerator.cpp
  - src/core/control/settings/LatexSettings.h
  - src/core/control/settings/Settings.cpp
  - src/core/gui/dialog/IntEdLatexDialog.cpp / .h
  - src/core/gui/dialog/LatexSettingsPanel.cpp / .h
  - src/util/PathUtil.cpp
  - src/util/include/util/PathUtil.h
  - ui/latexSettings.glade

Independant des series alignment_snap et table_writing_assist.

A lancer depuis la racine du depot xournalpp, sur un depot vierge (ou
tout du moins sans qu'aucun patch individuel de cette serie n'ait deja
ete applique).
"""
import sys
from pathlib import Path

DE_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""
DE_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:541
msgid \"Enable autocompletion\"
msgstr \"Autovervollständigung aktivieren\"

#: ../ui/latexSettings.glade:558
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Das Wörterbuch kann bearbeitet werden, um eigene Begriffe hinzuzufügen - \"
\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""
FR_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
FR_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:541
msgid \"Enable autocompletion\"
msgstr \"Activer le compléteur automatique\"

#: ../ui/latexSettings.glade:558
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Le dictionnaire peut être modifié pour ajouter vos propres termes - plus \"
\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
POT_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"\""""
POT_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:541
msgid \"Enable autocompletion\"
msgstr \"\"

#: ../ui/latexSettings.glade:558
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"\""""
GEN_OLD0 = """        strippedBody += l;
    }

    vars[\"TOOL_INPUT\"] = strippedBody;
    vars[\"TEXT_COLOR\"] = Util::rgb_to_hex_string(textColor).substr(1);
"""
GEN_NEW0 = """        strippedBody += l;
    }

    // Patch 13.11: replace every unfilled \"•\" placeholder (left over from the LaTeX completion
    // feature, patch 13.1 onwards) with \"\\text{•}\" before compilation - this way it still renders
    // visibly in the output PDF (matching Texmaker's own behavior, which the user preferred over the
    // plain \"@\" fallback of patch 13.10) rather than triggering a \"Missing character\" warning from
    // pdflatex's default fonts, which don't have a glyph for the raw Unicode bullet character on its
    // own outside of \\text{} (a plain amsmath macro, already available via the default template).
    {
        const std::string bullet = \"\\xe2\\x80\\xa2\";
        const std::string replacement = \"\\\\text{\\xe2\\x80\\xa2}\";
        size_t pos = 0;
        while ((pos = strippedBody.find(bullet, pos)) != std::string::npos) {
            strippedBody.replace(pos, bullet.size(), replacement);
            pos += replacement.size();
        }
    }

    vars[\"TOOL_INPUT\"] = strippedBody;
    vars[\"TEXT_COLOR\"] = Util::rgb_to_hex_string(textColor).substr(1);
"""
LS_H_OLD0 = """    bool externalEditorAutoConfirm{false};
    std::string externalEditorCmd{};
    std::string temporaryFileExt{\"tex\"};
};"""
LS_H_NEW0 = """    bool externalEditorAutoConfirm{false};
    std::string externalEditorCmd{};
    std::string temporaryFileExt{\"tex\"};

    /**
     * Patch 13.8: whether the LaTeX_completion.txt-based autocompletion popup (patch 13.1 onwards) is
     * offered while typing in the internal editor.
     */
    bool autocompletionEnabled{true};
};"""
SETTINGS_OLD0 = """        this->latexSettings.externalEditorCmd = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.temporaryFileExt\")) == 0) {
        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_NEW0 = """        this->latexSettings.externalEditorCmd = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.temporaryFileExt\")) == 0) {
        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionEnabled\")) == 0) {
        this->latexSettings.autocompletionEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_OLD1 = """    SAVE_BOOL_PROP(latexSettings.externalEditorAutoConfirm);
    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
SETTINGS_NEW1 = """    SAVE_BOOL_PROP(latexSettings.externalEditorAutoConfirm);
    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);
    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
IED_CPP_OLD0 = """
#include \"IntEdLatexDialog.h\"

#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move
"""
IED_CPP_NEW0 = """
#include \"IntEdLatexDialog.h\"

#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move
"""
IED_CPP_OLD1 = """#include \"control/settings/LatexSettings.h\"  // for LatexSettings
#include \"gui/Builder.h\"
#include \"model/Font.h\"        // for XojFont
#include \"util/StringUtils.h\"  // for replace_pair, StringUtils
#include \"util/raii/CStringWrapper.h\"
"""
IED_CPP_NEW1 = """#include \"control/settings/LatexSettings.h\"  // for LatexSettings
#include \"gui/Builder.h\"
#include \"model/Font.h\"        // for XojFont
#include \"util/PathUtil.h\"     // for getConfigFolder
#include \"util/StringUtils.h\"  // for replace_pair, StringUtils
#include \"util/raii/CStringWrapper.h\"
"""
IED_CPP_OLD2 = """                     }),
                     texCtrl.get());

    g_signal_connect(this->getWindow(), \"delete-event\", G_CALLBACK(+[](GtkWidget*, GdkEvent*, gpointer d) -> gboolean {
                         auto self = static_cast<IntEdLatexDialog*>(d);
                         /**"""
IED_CPP_NEW2 = """                     }),
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
                         if (!self->currentMatches.empty()) {
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
                                 // Patch 13.7: F1, not Escape - the LaTeX dialog's Cancel button has
                                 // its own Escape accelerator (bound in intEdTexDialog.glade), which
                                 // operates at the window level and could close the whole dialog
                                 // instead of (or in addition to) just this popup.
                                 case GDK_KEY_F1:
                                     self->hideCompletionPopup();
                                     return true;
                                 default:
                                     break;
                             }
                         }
                         // Patch 13.3: Tab/Shift+Tab placeholder navigation - independent of whether
                         // the completion popup is currently shown, since placeholders from a
                         // previously-committed completion may still be present in the buffer. Shift
                         // is conventionally delivered as GDK_KEY_ISO_Left_Tab on its own (not
                         // GDK_KEY_Tab plus a modifier), so both spellings of \"Tab\" are checked here.
                         if (event->keyval == GDK_KEY_Tab || event->keyval == GDK_KEY_KP_Tab ||
                             event->keyval == GDK_KEY_ISO_Left_Tab) {
                             bool shiftHeld = (event->state & GDK_SHIFT_MASK) != 0 ||
                                              event->keyval == GDK_KEY_ISO_Left_Tab;
                             return self->navigatePlaceholder(!shiftHeld);
                         }
                         return false;
                     }),
                     this);

    g_signal_connect(this->getWindow(), \"delete-event\", G_CALLBACK(+[](GtkWidget*, GdkEvent*, gpointer d) -> gboolean {
                         auto self = static_cast<IntEdLatexDialog*>(d);
                         /**"""
IED_CPP_OLD3 = """                          * dereferencing `self` after its destruction
                          */
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self->texCtrl.get());
                         return false;  // Let the callback from PopupWindowWrapper delete the dialog
                     }),
                     this);"""
IED_CPP_NEW3 = """                          * dereferencing `self` after its destruction
                          */
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self->texCtrl.get());
                         // Patch 13.1: the completion \"changed\" handler is tied to `self` (not
                         // texCtrl.get()) - disconnect it too, for the same reason as above.
                         g_signal_handlers_disconnect_by_data(self->getTextBuffer(), self);
                         return false;  // Let the callback from PopupWindowWrapper delete the dialog
                     }),
                     this);"""
IED_CPP_OLD4 = """                     texCtrl.get());
}

IntEdLatexDialog::~IntEdLatexDialog() = default;


auto IntEdLatexDialog::getTextBuffer() -> GtkTextBuffer* { return this->textBuffer; }"""
IED_CPP_NEW4 = """                     texCtrl.get());
}

IntEdLatexDialog::~IntEdLatexDialog() {
    // Patch 13.5: CRASH FIX - gtk_widget_destroy() properly severs every internal GTK bookkeeping
    // link the popover has (in particular its \"relative_to\" association with texBox), which a plain
    // g_object_unref() (as completionPopover's own destructor would otherwise be the only thing to
    // do, right after this destructor's body finishes) does not. Without this, texBox/the window
    // being destroyed afterwards (in AbstractLatexDialog::~AbstractLatexDialog(), called right after
    // this destructor returns) could still reach for the popover through that stale association,
    // after our own reference to it has already been dropped and the object freed - a use-after-free
    // crash deep inside GTK's widget teardown cascade.
    //
    // Patch 13.6: CRASH FIX (continued) - gtk_widget_destroy() itself already fully finalizes the
    // popover here (it isn't merely \"disconnected\" - GTK drops its own internal reference to it as
    // part of severing the \"relative_to\" association, and that was the only reference besides ours).
    // completionPopover.release() drops OUR OWN tracking of the pointer without a matching
    // g_object_unref(), which would otherwise run on that already-finalized object once this
    // destructor returns (member destruction happens right after the destructor body finishes) -
    // this is exactly the \"g_object_unref: assertion 'G_IS_OBJECT (object)' failed\" GLib critical
    // the user reported after patch 13.5 alone.
    if (this->completionPopover) {
        gtk_widget_destroy(this->completionPopover.get());
        this->completionPopover.release();
    }
}


auto IntEdLatexDialog::getTextBuffer() -> GtkTextBuffer* { return this->textBuffer; }"""
IED_CPP_OLD5 = """            xoj::util::OwnedCString::assumeOwnership(gtk_text_buffer_get_text(this->textBuffer, &start, &end, false));
    return content.get();
}"""
IED_CPP_NEW5 = """            xoj::util::OwnedCString::assumeOwnership(gtk_text_buffer_get_text(this->textBuffer, &start, &end, false));
    return content.get();
}

// Patch 13.1 (\"LaTeX completion\")

void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    // Patch 13.8: file creation logic moved to Util::getOrCreateLatexCompletionFile(), now shared with
    // LatexSettingsPanel's \"Open dictionary\" button.
    auto completionFile = Util::getOrCreateLatexCompletionFile();
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // Still couldn't be read (e.g. permissions) - not a hard error, just means no completions are
        // offered.
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
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer
    // (from an earlier completion, or typed by hand) is unaffected either way.
    if (!this->texCtrl->settings.autocompletionEnabled) {
        this->hideCompletionPopup();
        return;
    }
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
    // `word` is backslash + ASCII letters only, so its length in characters equals its length in bytes.
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
    }

    GtkTextIter selStart;
    GtkTextIter selEnd;
    // Always fills selStart/selEnd, even without a selection (both are then set to the cursor).
    gtk_text_buffer_get_selection_bounds(this->textBuffer, &selStart, &selEnd);

    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    bool found;
    if (forward) {
        GtkTextIter searchFrom = selEnd;
        found = gtk_text_iter_forward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                              &placeholderStart, &placeholderEnd, &bufEnd);
    } else {
        GtkTextIter searchFrom = selStart;
        found = gtk_text_iter_backward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                               &placeholderStart, &placeholderEnd, &bufStart);
    }
    if (found) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    }
    // Tab/Shift+Tab is blocked either way, since at least one placeholder exists somewhere.
    return true;
}"""
IED_H_OLD0 = """#pragma once

#include <string>  // for string

#include <cairo.h>               // for cairo_t
#include <gtk/gtk.h>             // for GtkWidget, GtkTextBuffer, GtkWindow"""
IED_H_NEW0 = """#pragma once

#include <string>  // for string
#include <vector>  // for vector

#include <cairo.h>               // for cairo_t
#include <gtk/gtk.h>             // for GtkWidget, GtkTextBuffer, GtkWindow"""
IED_H_OLD1 = """    std::string finalLatex;

    std::function<void()> callback;
};"""
IED_H_NEW1 = """    std::string finalLatex;

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
    /// Patch 13.3: on Tab (forward=true) or Shift+Tab (forward=false), selects the next/previous \"•\"
    /// placeholder found looking right/left from the cursor (or current selection). Returns true if
    /// Tab/Shift+Tab's normal action should be blocked (i.e. at least one placeholder exists anywhere
    /// in the buffer), regardless of whether one was actually found in the searched direction.
    bool navigatePlaceholder(bool forward);
};"""
LSP_CPP_OLD0 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_NEW0 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_OLD1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

#ifdef ENABLE_GTK_SOURCEVIEW
    GtkBox* themeSelectionBox = GTK_BOX(builder.get(\"bxThemeSelectionContainer\"));
    this->sourceViewThemeSelector = gtk_source_style_scheme_chooser_button_new();"""
LSP_CPP_NEW1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

    // Patch 13.8: \"Open dictionary\" - opens LaTeX_completion.txt (creating it first if needed) with
    // the system's default application for .txt files. g_app_info_launch_default_for_uri() is used
    // rather than a platform-specific command (xdg-open, ShellExecute, ...) since it is GLib's own
    // cross-platform abstraction over exactly that, working the same way on Linux, macOS and Windows.
    g_signal_connect_swapped(
            builder.get(\"btnOpenLatexCompletionFile\"), \"clicked\",
            G_CALLBACK(+[](LatexSettingsPanel* self) {
                auto completionFile = Util::getOrCreateLatexCompletionFile();
                auto uri = xoj::util::OwnedCString::assumeOwnership(
                        g_file_get_uri(Util::toGFile(completionFile).get()));
                GError* error = nullptr;
                if (!g_app_info_launch_default_for_uri(uri.get(), nullptr, &error)) {
                    std::string msg = error != nullptr ? error->message : \"\";
                    if (error != nullptr) {
                        g_error_free(error);
                    }
                    GtkWindow* win = GTK_WINDOW(gtk_widget_get_toplevel(GTK_WIDGET(self->panel)));
                    XojMsgBox::showMessageToUser(win, msg, GTK_MESSAGE_ERROR);
                }
            }),
            this);

#ifdef ENABLE_GTK_SOURCEVIEW
    GtkBox* themeSelectionBox = GTK_BOX(builder.get(\"bxThemeSelectionContainer\"));
    this->sourceViewThemeSelector = gtk_source_style_scheme_chooser_button_new();"""
LSP_CPP_OLD2 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_NEW2 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    // Patch 13.8
    gtk_check_button_set_active(this->cbLatexAutocompletion, settings.autocompletionEnabled);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_OLD3 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));
}

void LatexSettingsPanel::checkDeps() {"""
LSP_CPP_NEW3 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));

    // Patch 13.8
    settings.autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);
}

void LatexSettingsPanel::checkDeps() {"""
LSP_H_OLD0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
};"""
LSP_H_NEW0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
    /// Patch 13.8: \"Enable autocompletion\" checkbox in the new \"Autocompletion\" frame.
    GtkCheckButton* cbLatexAutocompletion;
};"""
PU_CPP_OLD0 = """    return Util::ensureFolderExists(p);
}

auto Util::getCacheSubfolder(const fs::path& subfolder) -> fs::path {
    auto p = GFilename(g_get_user_cache_dir()).toPath().value_or(fs::path());
    p /= CONFIG_FOLDER_NAME;"""
PU_CPP_NEW0 = """    return Util::ensureFolderExists(p);
}

auto Util::getOrCreateLatexCompletionFile() -> fs::path {
    Util::ensureFolderExists(Util::getConfigFolder());
    auto completionFile = Util::getConfigFolder() / \"LaTeX_completion.txt\";
    if (!fs::exists(completionFile)) {
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
    return completionFile;
}

auto Util::getCacheSubfolder(const fs::path& subfolder) -> fs::path {
    auto p = GFilename(g_get_user_cache_dir()).toPath().value_or(fs::path());
    p /= CONFIG_FOLDER_NAME;"""
PU_H_OLD0 = """ */
[[maybe_unused]] [[nodiscard]] fs::path getConfigFolder();
[[maybe_unused]] [[nodiscard]] fs::path getConfigSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getCacheSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getDataSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getStateSubfolder(const fs::path& subfolder = \"\");"""
PU_H_NEW0 = """ */
[[maybe_unused]] [[nodiscard]] fs::path getConfigFolder();
[[maybe_unused]] [[nodiscard]] fs::path getConfigSubfolder(const fs::path& subfolder = \"\");

/**
 * Patch 13.8: returns the path to <config folder>/LaTeX_completion.txt, creating it (with a short
 * explanatory header and an example term) first if it doesn't exist yet - shared between
 * IntEdLatexDialog (which reads the terms) and LatexSettingsPanel (whose \"Open dictionary\" button
 * opens this same file with the system's default application).
 */
[[maybe_unused]] fs::path getOrCreateLatexCompletionFile();
[[maybe_unused]] [[nodiscard]] fs::path getCacheSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getDataSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getStateSubfolder(const fs::path& subfolder = \"\");"""
GLADE_OLD0 = """                      </packing>
                    </child>
                    <child>
                      <object class=\"GtkFrame\" id=\"frameExternalEditorSettings\">
                        <property name=\"visible\">True</property>
                        <property name=\"can-focus\">False</property>"""
GLADE_NEW0 = """                      </packing>
                    </child>
                    <child>
                      <object class=\"GtkFrame\" id=\"frameLatexCompletionSettings\">
                        <property name=\"visible\">True</property>
                        <property name=\"can-focus\">False</property>
                        <property name=\"label-xalign\">0.009999999776482582</property>
                        <child>
                          <object class=\"GtkBox\">
                            <property name=\"visible\">True</property>
                            <property name=\"can-focus\">False</property>
                            <property name=\"orientation\">vertical</property>
                            <property name=\"margin-start\">12</property>
                            <property name=\"margin-end\">12</property>
                            <property name=\"margin-bottom\">8</property>
                            <property name=\"spacing\">6</property>
                            <child>
                              <object class=\"GtkCheckButton\" id=\"cbLatexAutocompletion\">
                                <property name=\"label\" translatable=\"yes\">Enable autocompletion</property>
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">True</property>
                                <property name=\"receives-default\">False</property>
                                <property name=\"draw-indicator\">True</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkLabel\" id=\"lbLatexCompletionDescription\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"halign\">start</property>
                                <property name=\"label\" translatable=\"yes\">The dictionary can be edited to add your own terms - the higher up a term appears in the file, the higher its priority during completion.</property>
                                <property name=\"wrap\">True</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">1</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkButton\" id=\"btnOpenLatexCompletionFile\">
                                <property name=\"label\" translatable=\"yes\">Open dictionary</property>
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">True</property>
                                <property name=\"receives-default\">True</property>
                                <property name=\"halign\">start</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">2</property>
                              </packing>
                            </child>
                          </object>
                        </child>
                        <child type=\"label\">
                          <object class=\"GtkLabel\">
                            <property name=\"visible\">True</property>
                            <property name=\"can-focus\">False</property>
                            <property name=\"label\" translatable=\"yes\">Autocompletion</property>
                          </object>
                        </child>
                      </object>
                      <packing>
                        <property name=\"expand\">False</property>
                        <property name=\"fill\">True</property>
                        <property name=\"position\">3</property>
                      </packing>
                    </child>
                    <child>
                      <object class=\"GtkFrame\" id=\"frameExternalEditorSettings\">
                        <property name=\"visible\">True</property>
                        <property name=\"can-focus\">False</property>"""


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
        "de": Path("po/de.po"),
        "fr": Path("po/fr.po"),
        "pot": Path("po/xournalpp.pot"),
        "gen": Path("src/core/control/latex/LatexGenerator.cpp"),
        "ls_h": Path("src/core/control/settings/LatexSettings.h"),
        "settings": Path("src/core/control/settings/Settings.cpp"),
        "ied_cpp": Path("src/core/gui/dialog/IntEdLatexDialog.cpp"),
        "ied_h": Path("src/core/gui/dialog/IntEdLatexDialog.h"),
        "lsp_cpp": Path("src/core/gui/dialog/LatexSettingsPanel.cpp"),
        "lsp_h": Path("src/core/gui/dialog/LatexSettingsPanel.h"),
        "pu_cpp": Path("src/util/PathUtil.cpp"),
        "pu_h": Path("src/util/include/util/PathUtil.h"),
        "glade": Path("ui/latexSettings.glade"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "navigatePlaceholder" in paths["ied_h"].read_text(encoding="utf-8"):
        print("[SKIP] Ce patch (apply_latex_completion) semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["de"], DE_OLD0, DE_NEW0, "de: zone 1/1")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/1")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/1")
    ok &= apply_edit(paths["gen"], GEN_OLD0, GEN_NEW0, "gen: zone 1/1")
    ok &= apply_edit(paths["ls_h"], LS_H_OLD0, LS_H_NEW0, "ls_h: zone 1/1")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD0, SETTINGS_NEW0, "settings: zone 1/2")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD1, SETTINGS_NEW1, "settings: zone 2/2")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD0, IED_CPP_NEW0, "ied_cpp: zone 1/6")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD1, IED_CPP_NEW1, "ied_cpp: zone 2/6")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD2, IED_CPP_NEW2, "ied_cpp: zone 3/6")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD3, IED_CPP_NEW3, "ied_cpp: zone 4/6")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD4, IED_CPP_NEW4, "ied_cpp: zone 5/6")
    ok &= apply_edit(paths["ied_cpp"], IED_CPP_OLD5, IED_CPP_NEW5, "ied_cpp: zone 6/6")
    ok &= apply_edit(paths["ied_h"], IED_H_OLD0, IED_H_NEW0, "ied_h: zone 1/2")
    ok &= apply_edit(paths["ied_h"], IED_H_OLD1, IED_H_NEW1, "ied_h: zone 2/2")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD0, LSP_CPP_NEW0, "lsp_cpp: zone 1/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD1, LSP_CPP_NEW1, "lsp_cpp: zone 2/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD2, LSP_CPP_NEW2, "lsp_cpp: zone 3/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD3, LSP_CPP_NEW3, "lsp_cpp: zone 4/4")
    ok &= apply_edit(paths["lsp_h"], LSP_H_OLD0, LSP_H_NEW0, "lsp_h: zone 1/1")
    ok &= apply_edit(paths["pu_cpp"], PU_CPP_OLD0, PU_CPP_NEW0, "pu_cpp: zone 1/1")
    ok &= apply_edit(paths["pu_h"], PU_H_OLD0, PU_H_NEW0, "pu_h: zone 1/1")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
