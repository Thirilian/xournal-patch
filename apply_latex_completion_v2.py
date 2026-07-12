#!/usr/bin/env python3
"""
apply_latex_completion_v2.py : version consolidee, fusionnant
l'integralite de la serie "completion LaTeX" (patchs 13.1 a 13.19) en
un seul script.

Implemente un compleeur LaTeX de style Texmaker complet et robuste
pour le dialogue d'edition interne : charge des termes complets
depuis <dossier de config>/LaTeX_completion.txt (un par ligne, "•"
pour marquer un placeholder), propose jusqu'a 4 correspondances dans
un popover filtrant en direct des que l'utilisateur tape un backslash
suivi d'au moins N lettres (seuil configurable, 2 par defaut).
Detection fine des termes deja complets (y compris curseur au milieu
du mot), navigation Tab/Maj+Tab entre placeholders, placeholder final
configurable (aucun / bullet / cercle / points de suspension) ajoute
apres un terme qui en contient deja, rendu visible dans le PDF de
sortie via une substitution avant compilation.

Cadre "Autocompletion" complet dans les Preferences : activation
globale (grise le reste du cadre si desactivee), seuil de
declenchement, caractere de fin configurable, controle de la
navigation seule, bouton "Ouvrir le dictionnaire". Traduit en
anglais, francais et allemand.

Contenu (patchs fusionnes, dans l'ordre) :
  13.1 a 13.11  : voir apply_latex_completion.py (deja consolide) -
                  compleeur de base, placeholders, cadre Preferences
                  initial, correctifs de crash, rendu PDF du bullet
  13.12  : signal mark-set (fermeture pendant navigation) + accolades
           acceptees sans fermer le popup
  13.13  : exclusion des termes deja exactement complets
  13.14  : correctif - seule la droite du curseur est reecrite
  13.15  : detection des termes complets avec curseur au milieu
  13.16  : exclusion des termes a placeholders pendant la navigation +
           placeholder final = grand cercle (au lieu d'un bullet)
  13.17  : seuil de declenchement configurable + caractere de fin
           configurable (menu deroulant 4 options)
  13.18  : case a cocher pour desactiver le declenchement par simple
           navigation au curseur
  13.19  : grisage complet du cadre si le compleeur est desactive

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

Independant des series alignment_snap et table_writing_assist, et du
patch 14.1 (suppression des popups pendant la saisie).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus) :

  git clone https://github.com/xournalpp/xournalpp.git
  cd xournalpp
  git checkout 209481caee183798fcae151d125c1ea2d0317b3b
  python3 apply_latex_completion_v2.py

Sur un depot vierge (ou tout du moins sans qu'aucun patch individuel
de cette serie n'ait deja ete applique).
"""
import sys
from pathlib import Path

DE_OLD0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
msgid \"None\"
msgstr \"Keine\"
"""
DE_NEW0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
#: ../ui/latexSettings.glade:636
msgid \"None\"
msgstr \"Keine\"
"""
DE_OLD1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""
DE_NEW1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:548
msgid \"Enable autocompletion\"
msgstr \"Autovervollständigung aktivieren\"

#: ../ui/latexSettings.glade:570
msgid \"Trigger after\"
msgstr \"Auslösung nach\"

#: ../ui/latexSettings.glade:598
msgid \"letter(s) typed\"
msgstr \"getippten Buchstaben\"

#: ../ui/latexSettings.glade:623
msgid \"Trailing placeholder after completion:\"
msgstr \"Nachgestellter Platzhalter nach Vervollständigung:\"

#: ../ui/latexSettings.glade:658
msgid \"Allow cursor navigation alone to trigger the popup\"
msgstr \"Reine Cursor-Navigation kann das Popup auslösen\"

#: ../ui/latexSettings.glade:675
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Das Wörterbuch kann bearbeitet werden, um eigene Begriffe hinzuzufügen - \"
\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:686
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:704
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""
FR_OLD0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
msgid \"None\"
msgstr \"Aucune\"
"""
FR_NEW0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
#: ../ui/latexSettings.glade:636
msgid \"None\"
msgstr \"Aucune\"
"""
FR_OLD1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
FR_NEW1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:548
msgid \"Enable autocompletion\"
msgstr \"Activer le compléteur automatique\"

#: ../ui/latexSettings.glade:570
msgid \"Trigger after\"
msgstr \"Déclenchement après\"

#: ../ui/latexSettings.glade:598
msgid \"letter(s) typed\"
msgstr \"lettre(s) tapée(s)\"

#: ../ui/latexSettings.glade:623
msgid \"Trailing placeholder after completion:\"
msgstr \"Repère ajouté en fin de complétion :\"

#: ../ui/latexSettings.glade:658
msgid \"Allow cursor navigation alone to trigger the popup\"
msgstr \"Autoriser la simple navigation au curseur à déclencher le popup\"

#: ../ui/latexSettings.glade:675
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Le dictionnaire peut être modifié pour ajouter vos propres termes - plus \"
\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:686
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:704
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
POT_OLD0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
msgid \"None\"
msgstr \"\"
"""
POT_NEW0 = """
#: ../ui/exportSettings.glade:53 ../ui/settings.glade:260
#: ../ui/settings.glade:277 ../ui/settings.glade:3816
#: ../ui/latexSettings.glade:636
msgid \"None\"
msgstr \"\"
"""
POT_OLD1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"\""""
POT_NEW1 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:548
msgid \"Enable autocompletion\"
msgstr \"\"

#: ../ui/latexSettings.glade:570
msgid \"Trigger after\"
msgstr \"\"

#: ../ui/latexSettings.glade:598
msgid \"letter(s) typed\"
msgstr \"\"

#: ../ui/latexSettings.glade:623
msgid \"Trailing placeholder after completion:\"
msgstr \"\"

#: ../ui/latexSettings.glade:658
msgid \"Allow cursor navigation alone to trigger the popup\"
msgstr \"\"

#: ../ui/latexSettings.glade:675
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"

#: ../ui/latexSettings.glade:686
msgid \"Open dictionary\"
msgstr \"\"

#: ../ui/latexSettings.glade:704
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
    //
    // Patch 13.16: the large circle placeholder character (\"◯\", U+25EF - see IntEdLatexDialog.cpp's
    // own comment on it) gets exactly the same treatment, for exactly the same reason - it is just as
    // absent from pdflatex's default fonts outside of \\text{}.
    {
        const std::string bullet = \"\\xe2\\x80\\xa2\";
        const std::string bulletReplacement = \"\\\\text{\\xe2\\x80\\xa2}\";
        size_t pos = 0;
        while ((pos = strippedBody.find(bullet, pos)) != std::string::npos) {
            strippedBody.replace(pos, bullet.size(), bulletReplacement);
            pos += bulletReplacement.size();
        }
        const std::string circle = \"\\xe2\\x97\\xaf\";
        const std::string circleReplacement = \"\\\\text{\\xe2\\x97\\xaf}\";
        pos = 0;
        while ((pos = strippedBody.find(circle, pos)) != std::string::npos) {
            strippedBody.replace(pos, circle.size(), circleReplacement);
            pos += circleReplacement.size();
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

    /**
     * Patch 13.17: how many letters after the backslash must be typed before the completion popup can
     * open (e.g. 2 means \"\\df\" is enough). Always clamped to at least 1 when Preferences are applied
     * (see LatexSettingsPanel::save()) - a value below 1 wouldn't correspond to anything typable right
     * after a lone backslash.
     */
    int autocompletionTriggerLength{2};

    /**
     * Patch 13.17: which character (if any) commitCompletion() appends after a term that already
     * contains a placeholder of its own (see IntEdLatexDialog.cpp's own PLACEHOLDER_* constants for
     * the exact set) - 0 = none (nothing is appended at all, not even a trailing space), 1 = bullet
     * (U+2022, \"\\u2022\"), 2 = large circle (U+25EF, \"\\u25ef\", the default, matching patch 13.16's prior
     * hardcoded behavior), 3 = ellipsis (U+2026, \"\\u2026\"). Matches the row order of the combo box in
     * Preferences.
     */
    int autocompletionTrailingPlaceholder{2};

    /**
     * Patch 13.18: whether the completion popup can be triggered by cursor navigation alone (arrow
     * keys, mouse click - see the \"mark-set\" signal handler and updateCompletionPopup()'s own
     * isNavigation parameter in IntEdLatexDialog.cpp), with no actual typing involved. Typing itself
     * is entirely unaffected either way - only navigation-only triggers are gated by this.
     */
    bool autocompletionOnNavigation{true};
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
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionTriggerLength\")) ==
               0) {
        this->latexSettings.autocompletionTriggerLength =
                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(
                                       \"latexSettings.autocompletionTrailingPlaceholder\")) == 0) {
        this->latexSettings.autocompletionTrailingPlaceholder =
                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionOnNavigation\")) ==
               0) {
        this->latexSettings.autocompletionOnNavigation =
                xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
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
    SAVE_INT_PROP(latexSettings.autocompletionTriggerLength);
    SAVE_INT_PROP(latexSettings.autocompletionTrailingPlaceholder);
    SAVE_BOOL_PROP(latexSettings.autocompletionOnNavigation);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
IED_CPP_OLD0 = """
#include \"IntEdLatexDialog.h\"

#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move

#include <glib.h>              // for g_free, gpointer, guint"""
IED_CPP_NEW0 = """
#include \"IntEdLatexDialog.h\"

#include <algorithm>  // for min
#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <string_view>  // for string_view
#include <utility>  // for move

#include <glib.h>              // for g_free, gpointer, guint"""
IED_CPP_OLD1 = """#include \"model/Font.h\"        // for XojFont\n"""
IED_CPP_NEW1 = """#include \"model/Font.h\"        // for XojFont\n#include \"util/PathUtil.h\"     // for getConfigFolder\n"""
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
                         // Patch 13.13: any actual typing resets the F1 suppression (see the field's
                         // own doc comment in the header).
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         self->completionSuppressedByF1 = false;
                         self->updateCompletionPopup();
                     }),
                     this);
    // Patch 13.12: the popup must also close as soon as the cursor is no longer \"stuck\" to a
    // matching word (between its letters, or at either end) - e.g. clicking elsewhere in the text, or
    // moving the cursor with the arrow keys, without any text actually changing. \"mark-set\" fires for
    // every mark move, so it's filtered down to the \"insert\" mark (the cursor) specifically.
    // updateCompletionPopup() already does exactly the right thing when called: re-checks the current
    // word at the (now new) cursor position and closes the popup if it no longer qualifies.
    //
    // Patch 13.13: skipped entirely while completionSuppressedByF1 is set - navigating around the
    // text must never reopen a popup the user just explicitly dismissed with F1.
    //
    // Patch 13.16: CORRECTIF - also skipped entirely while a click-and-drag text selection is active
    // (or otherwise exists) - \"mark-set\" fires continuously as the selection grows/shrinks during a
    // drag, and updating the popup on every single one of those movements interfered with the
    // selection process itself. Called with isNavigation=true, since this can only ever be a cursor
    // move without any actual typing - see updateCompletionPopup()'s own doc comment for what that
    // does.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         GtkTextIter selStart;
                         GtkTextIter selEnd;
                         bool hasSelection = gtk_text_buffer_get_selection_bounds(buffer, &selStart, &selEnd);
                         if (mark == gtk_text_buffer_get_insert(buffer) && !self->completionSuppressedByF1 &&
                             !hasSelection) {
                             self->updateCompletionPopup(true);
                         }
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
                                     // Patch 13.13: remember that F1 explicitly dismissed the popup,
                                     // so mere navigation doesn't reopen it - see the field's own doc
                                     // comment in the header.
                                     self->completionSuppressedByF1 = true;
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

/**
 * Patch 13.16: two distinct characters now act as placeholders with identical properties - the
 * dictionary's own \"\\u2022\" (U+2022, bullet), and \"\\u25ef\" (U+25EF, large circle), which is what
 * commitCompletion() appends after a term that already contains a \"\\u2022\" of its own (see that
 * function). All placeholder-searching logic below checks for both, always treating them completely
 * interchangeably.
 */
constexpr const char* PLACEHOLDER_BULLET = \"\\xe2\\x80\\xa2\";
constexpr const char* PLACEHOLDER_CIRCLE = \"\\xe2\\x97\\xaf\";
/// Patch 13.17: the third possible trailing placeholder character (U+2026, horizontal ellipsis).
constexpr const char* PLACEHOLDER_ELLIPSIS = \"\\xe2\\x80\\xa6\";

/**
 * Patch 13.17: returns the trailing placeholder character selected in Preferences (see
 * LatexSettings::autocompletionTrailingPlaceholder's own doc comment for the row order), or an empty
 * string_view for \"None\" (row 0).
 */
static auto trailingPlaceholderFor(int settingValue) -> std::string_view {
    switch (settingValue) {
        case 1:
            return PLACEHOLDER_BULLET;
        case 3:
            return PLACEHOLDER_ELLIPSIS;
        case 0:
            return \"\";
        case 2:
        default:
            return PLACEHOLDER_CIRCLE;
    }
}

/**
 * Searches forward from `start` (up to `limit`) for the EARLIEST occurrence of any placeholder
 * character (the dictionary's own bullet, or any of the 3 possible trailing characters - see
 * PLACEHOLDER_BULLET/PLACEHOLDER_CIRCLE/PLACEHOLDER_ELLIPSIS above; all 3 possible trailing
 * characters are always searched for here, regardless of the CURRENT Preferences selection, so that
 * a placeholder inserted under a since-changed setting is still found). Returns true and fills
 * outStart/outEnd if one was found.
 */
static auto forwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                        GtkTextIter* outEnd) -> bool {
    bool found = false;
    for (const char* marker: {PLACEHOLDER_BULLET, PLACEHOLDER_CIRCLE, PLACEHOLDER_ELLIPSIS}) {
        GtkTextIter searchFrom = *start;
        GtkTextIter candidateStart;
        GtkTextIter candidateEnd;
        if (gtk_text_iter_forward_search(&searchFrom, marker, GTK_TEXT_SEARCH_TEXT_ONLY, &candidateStart,
                                         &candidateEnd, limit) &&
            (!found || gtk_text_iter_compare(&candidateStart, outStart) < 0)) {
            *outStart = candidateStart;
            *outEnd = candidateEnd;
            found = true;
        }
    }
    return found;
}

/**
 * Searches backward from `start` (down to `limit`) for the LATEST (closest to `start`) occurrence of
 * any placeholder character - see forwardSearchAnyPlaceholder()'s own comment above for the full
 * explanation, mirrored here. Returns true and fills outStart/outEnd if one was found.
 */
static auto backwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                         GtkTextIter* outEnd) -> bool {
    bool found = false;
    for (const char* marker: {PLACEHOLDER_BULLET, PLACEHOLDER_CIRCLE, PLACEHOLDER_ELLIPSIS}) {
        GtkTextIter searchFrom = *start;
        GtkTextIter candidateStart;
        GtkTextIter candidateEnd;
        if (gtk_text_iter_backward_search(&searchFrom, marker, GTK_TEXT_SEARCH_TEXT_ONLY, &candidateStart,
                                          &candidateEnd, limit) &&
            (!found || gtk_text_iter_compare(&candidateStart, outStart) > 0)) {
            *outStart = candidateStart;
            *outEnd = candidateEnd;
            found = true;
        }
    }
    return found;
}

void IntEdLatexDialog::updateCompletionPopup(bool isNavigation) {
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer
    // (from an earlier completion, or typed by hand) is unaffected either way.
    if (!this->texCtrl->settings.autocompletionEnabled) {
        this->hideCompletionPopup();
        return;
    }
    // Patch 13.18: cursor navigation alone (no typing) never OPENS the popup if disabled in
    // Preferences - but an ALREADY-open popup (e.g. from typing just before) still updates/closes
    // normally as the cursor keeps moving, exactly as before; only the \"closed -> open\" transition
    // is prevented here. Typing itself (isNavigation=false) is entirely unaffected either way.
    if (isNavigation && this->currentMatches.empty() && !this->texCtrl->settings.autocompletionOnNavigation) {
        return;
    }
    std::string word = this->getCurrentLatexWord();
    // Patch 13.17: a backslash plus at least autocompletionTriggerLength letters (2 by default,
    // matching the original hardcoded threshold this replaces).
    if (word.size() < 1 + static_cast<size_t>(std::max(1, this->texCtrl->settings.autocompletionTriggerLength))) {
        this->hideCompletionPopup();
        return;
    }

    // Patch 13.15: CORRECTIF - if the cursor merely sits somewhere WITHIN an already-complete term
    // (e.g. navigating with the arrow keys into the middle of \"\\alpha\", cursor between \"al\" and
    // \"pha\"), `word` alone (which only sees the LEFT-hand portion, \"\\al\" here) doesn't reveal that the
    // FULL word is already an exact, complete term - \"\\alpha\" would still look like a valid prefix of
    // itself and get offered again. getFullLatexWordAroundCursor() spans both sides of the cursor to
    // catch this: if it exactly matches some term, there is nothing to complete, full stop - checked
    // before the ordinary prefix-matching loop below, taking priority over it.
    //
    // Patch 13.16: CORRECTIF - this exact-match check alone never actually fires for a term
    // containing a placeholder, since commitCompletion() always appends an extra trailing one to it
    // (see PLACEHOLDER_CIRCLE above) - the text actually present in the buffer therefore never
    // matches completionTerms' own, unmodified copy of that term. Such terms are instead excluded
    // outright while merely navigating (isNavigation), a few lines below.
    std::string fullWord = this->getFullLatexWordAroundCursor();
    for (const auto& term: this->completionTerms) {
        if (term == fullWord) {
            this->hideCompletionPopup();
            return;
        }
    }

    this->currentMatches.clear();
    for (const auto& term: this->completionTerms) {
        // Patch 13.13: a term STRICTLY longer than the current word only - an exact match means the
        // word is already a complete term on its own, with nothing left to complete, so it must never
        // be offered (and the popup must not reopen while merely navigating through it either - see
        // this same check's effect once currentMatches ends up empty below).
        if (term.size() > word.size() && term.compare(0, word.size(), word) == 0) {
            // Patch 13.16: CORRECTIF - while merely navigating (not typing), a term containing a
            // placeholder is never offered - see this function's own doc comment in the header.
            if (isNavigation && term.find(PLACEHOLDER_BULLET) != std::string::npos) {
                continue;
            }
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
    //
    // Patch 13.16/13.17: the character appended here (if any) is configurable in Preferences
    // (autocompletionTrailingPlaceholder) - the detection check above still looks for the
    // dictionary's own bullet character, unaffected. \"None\" means nothing at all is appended, not
    // even the separating space.
    std::string_view trailing = trailingPlaceholderFor(this->texCtrl->settings.autocompletionTrailingPlaceholder);
    if (!trailing.empty() && term.find(PLACEHOLDER_BULLET) != std::string::npos) {
        term += \" \";
        term += trailing;
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
    if (forwardSearchAnyPlaceholder(&insertStart, &termEnd, &placeholderStart, &placeholderEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    } else {
        // Patch 13.13: no placeholder in this term - place the cursor at its true end, exactly as if
        // the whole term had just been typed by hand in one go, regardless of where the cursor
        // originally was or how many characters were actually missing.
        gtk_text_buffer_place_cursor(this->textBuffer, &termEnd);
    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}

auto IntEdLatexDialog::navigatePlaceholder(bool forward) -> bool {
    // Patch 13.3: Tab/Shift+Tab's normal action is blocked outright as soon as at least one
    // placeholder exists ANYWHERE in the buffer - regardless of whether one is actually found in the
    // specific direction being searched. Patch 13.16: checks for either placeholder character.
    GtkTextIter bufStart;
    GtkTextIter bufEnd;
    gtk_text_buffer_get_bounds(this->textBuffer, &bufStart, &bufEnd);
    GtkTextIter anyStart;
    GtkTextIter anyEnd;
    if (!forwardSearchAnyPlaceholder(&bufStart, &bufEnd, &anyStart, &anyEnd)) {
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
        found = forwardSearchAnyPlaceholder(&selEnd, &bufEnd, &placeholderStart, &placeholderEnd);
    } else {
        found = backwardSearchAnyPlaceholder(&selStart, &bufStart, &placeholderStart, &placeholderEnd);
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

    /// Patch 13.13: set when F1 explicitly dismisses the popup, so that mere cursor navigation
    /// (mark-set) doesn't immediately reopen it - any actual typing (changed) resets it back to
    /// false, restoring normal behavior.
    bool completionSuppressedByF1 = false;

    void loadCompletionTerms();
    /// Returns the \"\\XX...\" word ending at the cursor (backslash included), or an empty string if the
    /// cursor isn't immediately preceded by such a word (letters only after the backslash).
    std::string getCurrentLatexWord() const;
    /// Patch 13.15: like getCurrentLatexWord(), but spans BOTH sides of the cursor - the full
    /// \"\\XX...\" word the cursor currently sits somewhere within, regardless of exactly where in it.
    /// Used specifically to detect an already-complete term while merely navigating through its
    /// middle (getCurrentLatexWord() alone only sees the left-hand portion in that case).
    std::string getFullLatexWordAroundCursor() const;
    /// Patch 13.16: `isNavigation` is true when called from cursor-movement-only triggers (the
    /// \"mark-set\" signal) rather than actual typing (the \"changed\" signal). In that case, any term
    /// containing a placeholder is excluded from the suggestions entirely: such a term can never be
    /// reliably identified as \"already complete\" (commitCompletion() always appends an extra trailing
    /// placeholder to it, so a plain text match against the dictionary's own copy never succeeds),
    /// so it must not be offered while merely navigating through it (see point 1 raised by the user).
    void updateCompletionPopup(bool isNavigation = false);
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
LSP_CPP_OLD0 = """#include \"LatexSettingsPanel.h\"

#include <fstream>   // for ifstream, basic_istream
#include <iterator>  // for istreambuf_iterator, ope...
#include <string>    // for allocator, string"""
LSP_CPP_NEW0 = """#include \"LatexSettingsPanel.h\"

#include <algorithm>  // for max
#include <fstream>   // for ifstream, basic_istream
#include <iterator>  // for istreambuf_iterator, ope...
#include <string>    // for allocator, string"""
LSP_CPP_OLD1 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_NEW1 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))),
        spLatexTriggerLength(GTK_SPIN_BUTTON(builder.get(\"spLatexTriggerLength\"))),
        cbxLatexTrailingPlaceholder(GTK_COMBO_BOX_TEXT(builder.get(\"cbxLatexTrailingPlaceholder\"))),
        cbLatexAutocompletionOnNavigation(
                GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletionOnNavigation\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_OLD2 = """                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);
    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

#ifdef ENABLE_GTK_SOURCEVIEW
    GtkBox* themeSelectionBox = GTK_BOX(builder.get(\"bxThemeSelectionContainer\"));"""
LSP_CPP_NEW2 = """                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);
    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);
    // Patch 13.19
    g_signal_connect_swapped(this->cbLatexAutocompletion, \"toggled\",
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
    GtkBox* themeSelectionBox = GTK_BOX(builder.get(\"bxThemeSelectionContainer\"));"""
LSP_CPP_OLD3 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_NEW3 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    // Patch 13.8
    gtk_check_button_set_active(this->cbLatexAutocompletion, settings.autocompletionEnabled);

    // Patch 13.17
    gtk_spin_button_set_value(this->spLatexTriggerLength, settings.autocompletionTriggerLength);
    gtk_combo_box_set_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder),
                             settings.autocompletionTrailingPlaceholder);

    // Patch 13.18
    gtk_check_button_set_active(this->cbLatexAutocompletionOnNavigation, settings.autocompletionOnNavigation);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_OLD4 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));
}

void LatexSettingsPanel::checkDeps() {"""
LSP_CPP_NEW4 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));

    // Patch 13.8
    settings.autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);

    // Patch 13.17: explicitly clamped to a minimum of 1 here (in addition to the spin button's own
    // lower bound in the .glade adjustment) - a value below 1 wouldn't correspond to anything typable
    // right after a lone backslash.
    settings.autocompletionTriggerLength =
            std::max(1, static_cast<int>(gtk_spin_button_get_value_as_int(this->spLatexTriggerLength)));
    settings.autocompletionTrailingPlaceholder =
            gtk_combo_box_get_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder));

    // Patch 13.18
    settings.autocompletionOnNavigation = gtk_check_button_get_active(this->cbLatexAutocompletionOnNavigation);
}

void LatexSettingsPanel::checkDeps() {"""
LSP_CPP_OLD5 = """    gtk_widget_set_sensitive(builder.get(\"cbExternalEditorAutoConfirm\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexExternalEditorCmd\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexTemporaryFileExt\"), useExternalEditor);
}"""
LSP_CPP_NEW5 = """    gtk_widget_set_sensitive(builder.get(\"cbExternalEditorAutoConfirm\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexExternalEditorCmd\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexTemporaryFileExt\"), useExternalEditor);

    // Patch 13.19: every other widget in the \"Autocompletion\" frame is greyed out while the feature
    // itself is disabled - only the checkbox and its own label stay active, so it can be turned back
    // on.
    bool autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);
    gtk_widget_set_sensitive(builder.get(\"boxLatexTriggerLength\"), autocompletionEnabled);
    gtk_widget_set_sensitive(builder.get(\"boxLatexTrailingPlaceholder\"), autocompletionEnabled);
    gtk_widget_set_sensitive(GTK_WIDGET(this->cbLatexAutocompletionOnNavigation), autocompletionEnabled);
    gtk_widget_set_sensitive(builder.get(\"lbLatexCompletionDescription\"), autocompletionEnabled);
    gtk_widget_set_sensitive(builder.get(\"btnOpenLatexCompletionFile\"), autocompletionEnabled);
}"""
LSP_H_OLD0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
};"""
LSP_H_NEW0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
    /// Patch 13.8: \"Enable autocompletion\" checkbox in the new \"Autocompletion\" frame.
    GtkCheckButton* cbLatexAutocompletion;
    /// Patch 13.17: minimum letters typed after the backslash before the popup can open.
    GtkSpinButton* spLatexTriggerLength;
    /// Patch 13.17: which character (if any) is appended after a term with a placeholder of its own.
    GtkComboBoxText* cbxLatexTrailingPlaceholder;
    /// Patch 13.18: \"Allow cursor navigation alone to trigger the popup\" checkbox.
    GtkCheckButton* cbLatexAutocompletionOnNavigation;
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
GLADE_OLD0 = """<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib=\"gtk+\" version=\"3.24\"/>
  <object class=\"GtkFileFilter\" id=\"filefilter1\">
    <mime-types>
      <mime-type>application/x-latex</mime-type>"""
GLADE_NEW0 = """<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib=\"gtk+\" version=\"3.24\"/>
  <object class=\"GtkAdjustment\" id=\"adjLatexTriggerLength\">
    <property name=\"lower\">1</property>
    <property name=\"upper\">9</property>
    <property name=\"value\">2</property>
    <property name=\"step-increment\">1</property>
    <property name=\"page-increment\">1</property>
  </object>
  <object class=\"GtkFileFilter\" id=\"filefilter1\">
    <mime-types>
      <mime-type>application/x-latex</mime-type>"""
GLADE_OLD1 = """                      </packing>
                    </child>
                    <child>
                      <object class=\"GtkFrame\" id=\"frameExternalEditorSettings\">
                        <property name=\"visible\">True</property>
                        <property name=\"can-focus\">False</property>"""
GLADE_NEW1 = """                      </packing>
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
                              <object class=\"GtkBox\" id=\"boxLatexTriggerLength\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"orientation\">horizontal</property>
                                <property name=\"spacing\">6</property>
                                <child>
                                  <object class=\"GtkLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Trigger after</property>
                                  </object>
                                  <packing>
                                    <property name=\"expand\">False</property>
                                    <property name=\"fill\">True</property>
                                    <property name=\"position\">0</property>
                                  </packing>
                                </child>
                                <child>
                                  <object class=\"GtkSpinButton\" id=\"spLatexTriggerLength\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">True</property>
                                    <property name=\"text\">2</property>
                                    <property name=\"input-purpose\">digits</property>
                                    <property name=\"adjustment\">adjLatexTriggerLength</property>
                                    <property name=\"numeric\">True</property>
                                    <property name=\"value\">2</property>
                                  </object>
                                  <packing>
                                    <property name=\"expand\">False</property>
                                    <property name=\"fill\">True</property>
                                    <property name=\"position\">1</property>
                                  </packing>
                                </child>
                                <child>
                                  <object class=\"GtkLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">letter(s) typed</property>
                                  </object>
                                  <packing>
                                    <property name=\"expand\">False</property>
                                    <property name=\"fill\">True</property>
                                    <property name=\"position\">2</property>
                                  </packing>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">1</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkBox\" id=\"boxLatexTrailingPlaceholder\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"orientation\">horizontal</property>
                                <property name=\"spacing\">6</property>
                                <child>
                                  <object class=\"GtkLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Trailing placeholder after completion:</property>
                                  </object>
                                  <packing>
                                    <property name=\"expand\">False</property>
                                    <property name=\"fill\">True</property>
                                    <property name=\"position\">0</property>
                                  </packing>
                                </child>
                                <child>
                                  <object class=\"GtkComboBoxText\" id=\"cbxLatexTrailingPlaceholder\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <items>
                                      <item translatable=\"yes\">None</item>
                                      <item>&#8226;</item>
                                      <item>&#9711;</item>
                                      <item>&#8230;</item>
                                    </items>
                                    <property name=\"active\">2</property>
                                  </object>
                                  <packing>
                                    <property name=\"expand\">False</property>
                                    <property name=\"fill\">True</property>
                                    <property name=\"position\">1</property>
                                  </packing>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">2</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkCheckButton\" id=\"cbLatexAutocompletionOnNavigation\">
                                <property name=\"label\" translatable=\"yes\">Allow cursor navigation alone to trigger the popup</property>
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">True</property>
                                <property name=\"receives-default\">False</property>
                                <property name=\"draw-indicator\">True</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">3</property>
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
                                <property name=\"position\">4</property>
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
                                <property name=\"position\">5</property>
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
    if "autocompletionOnNavigation" in paths["ls_h"].read_text(encoding="utf-8"):
        print("[SKIP] Ce patch (apply_latex_completion_v2) semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["de"], DE_OLD0, DE_NEW0, "de: zone 1/2")
    ok &= apply_edit(paths["de"], DE_OLD1, DE_NEW1, "de: zone 2/2")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/2")
    ok &= apply_edit(paths["fr"], FR_OLD1, FR_NEW1, "fr: zone 2/2")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/2")
    ok &= apply_edit(paths["pot"], POT_OLD1, POT_NEW1, "pot: zone 2/2")
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
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD0, LSP_CPP_NEW0, "lsp_cpp: zone 1/6")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD1, LSP_CPP_NEW1, "lsp_cpp: zone 2/6")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD2, LSP_CPP_NEW2, "lsp_cpp: zone 3/6")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD3, LSP_CPP_NEW3, "lsp_cpp: zone 4/6")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD4, LSP_CPP_NEW4, "lsp_cpp: zone 5/6")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD5, LSP_CPP_NEW5, "lsp_cpp: zone 6/6")
    ok &= apply_edit(paths["lsp_h"], LSP_H_OLD0, LSP_H_NEW0, "lsp_h: zone 1/1")
    ok &= apply_edit(paths["pu_cpp"], PU_CPP_OLD0, PU_CPP_NEW0, "pu_cpp: zone 1/1")
    ok &= apply_edit(paths["pu_h"], PU_H_OLD0, PU_H_NEW0, "pu_h: zone 1/1")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/2")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/2")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
