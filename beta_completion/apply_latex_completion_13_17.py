#!/usr/bin/env python3
"""
Patch 13.17 ("completion LaTeX") : deux nouveaux parametres dans le
cadre "Compleeur automatique" des Preferences, entre la case a cocher
"Activer le completeur automatique" et le texte explicatif sur le
dictionnaire.

1. "Trigger after [N] letter(s) typed" : nombre de lettres apres le
   backslash necessaires avant que le popup de completion puisse
   s'ouvrir (2 par defaut, valeur actuelle confirmee). Clampe a un
   minimum de 1 au moment du "Appliquer" des Preferences (le
   spinbutton a deja lower=1 dans le glade, mais un clamp explicite
   supplementaire est fait cote code par securite).

2. "Trailing placeholder after completion:" (menu deroulant, 4
   options) : caractere ajoute apres un terme qui contient deja un ou
   plusieurs placeholders, une fois la completion validee - "None"
   (rien n'est ajoute, ni caractere ni espace), "•" (bullet,
   U+2022), "◯" (grand cercle, U+25EF - option par defaut, egale au
   comportement fixe du patch 13.16), "…" (points de suspension,
   U+2026). La detection du terme "contient deja un placeholder"
   continue de se baser exclusivement sur le bullet propre du
   dictionnaire, inchangee. La navigation Tab/Maj+Tab reconnait
   desormais les 3 caracteres possibles (bullet, cercle, points de
   suspension) quel que soit le parametre ACTUEL, pour que des
   placeholders inseres sous un ancien reglage restent navigables.

Modifie :
  - src/core/control/settings/LatexSettings.h / Settings.cpp (deux
    nouveaux parametres)
  - src/core/gui/dialog/LatexSettingsPanel.h / .cpp (spinbutton +
    combo box)
  - src/core/gui/dialog/IntEdLatexDialog.cpp (seuil parametrable,
    caractere de fin parametrable, recherche etendue a 3 caracteres)
  - ui/latexSettings.glade (deux nouvelles lignes dans le cadre)
  - po/xournalpp.pot, po/fr.po, po/de.po (traductions - la chaine
    "None" deja existante ailleurs dans l'app est reutilisee sans
    dupliquer son msgid, conformement aux conventions gettext)

NECESSITE : apply_latex_completion.py, puis
apply_latex_completion_13_12.py a apply_latex_completion_13_16.py
(deja appliques).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

LS_H_OLD0 = """     * offered while typing in the internal editor.
     */
    bool autocompletionEnabled{true};
};"""
LS_H_NEW0 = """     * offered while typing in the internal editor.
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
};"""
SETTINGS_OLD0 = """        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionEnabled\")) == 0) {
        this->latexSettings.autocompletionEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_NEW0 = """        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
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
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_OLD1 = """    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);
    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
SETTINGS_NEW1 = """    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);
    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);
    SAVE_INT_PROP(latexSettings.autocompletionTriggerLength);
    SAVE_INT_PROP(latexSettings.autocompletionTrailingPlaceholder);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
LSP_H_OLD0 = """    GtkCheckButton* cbUseSystemFont;
    /// Patch 13.8: \"Enable autocompletion\" checkbox in the new \"Autocompletion\" frame.
    GtkCheckButton* cbLatexAutocompletion;
};"""
LSP_H_NEW0 = """    GtkCheckButton* cbUseSystemFont;
    /// Patch 13.8: \"Enable autocompletion\" checkbox in the new \"Autocompletion\" frame.
    GtkCheckButton* cbLatexAutocompletion;
    /// Patch 13.17: minimum letters typed after the backslash before the popup can open.
    GtkSpinButton* spLatexTriggerLength;
    /// Patch 13.17: which character (if any) is appended after a term with a placeholder of its own.
    GtkComboBoxText* cbxLatexTrailingPlaceholder;
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
LSP_CPP_OLD1 = """        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_NEW1 = """        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))),
        spLatexTriggerLength(GTK_SPIN_BUTTON(builder.get(\"spLatexTriggerLength\"))),
        cbxLatexTrailingPlaceholder(GTK_COMBO_BOX_TEXT(builder.get(\"cbxLatexTrailingPlaceholder\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_OLD2 = """    // Patch 13.8
    gtk_check_button_set_active(this->cbLatexAutocompletion, settings.autocompletionEnabled);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_NEW2 = """    // Patch 13.8
    gtk_check_button_set_active(this->cbLatexAutocompletion, settings.autocompletionEnabled);

    // Patch 13.17
    gtk_spin_button_set_value(this->spLatexTriggerLength, settings.autocompletionTriggerLength);
    gtk_combo_box_set_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder),
                             settings.autocompletionTrailingPlaceholder);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_OLD3 = """
    // Patch 13.8
    settings.autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);
}

void LatexSettingsPanel::checkDeps() {"""
LSP_CPP_NEW3 = """
    // Patch 13.8
    settings.autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);

    // Patch 13.17: explicitly clamped to a minimum of 1 here (in addition to the spin button's own
    // lower bound in the .glade adjustment) - a value below 1 wouldn't correspond to anything typable
    // right after a lone backslash.
    settings.autocompletionTriggerLength =
            std::max(1, static_cast<int>(gtk_spin_button_get_value_as_int(this->spLatexTriggerLength)));
    settings.autocompletionTrailingPlaceholder =
            gtk_combo_box_get_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder));
}

void LatexSettingsPanel::checkDeps() {"""
IED_OLD0 = """#include <algorithm>  // for min
#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <utility>  // for move

#include <glib.h>              // for g_free, gpointer, guint"""
IED_NEW0 = """#include <algorithm>  // for min
#include <fstream>  // for ifstream
#include <sstream>  // for operator<<, basic_ostream
#include <string_view>  // for string_view
#include <utility>  // for move

#include <glib.h>              // for g_free, gpointer, guint"""
IED_OLD1 = """ */
constexpr const char* PLACEHOLDER_BULLET = \"\\xe2\\x80\\xa2\";
constexpr const char* PLACEHOLDER_CIRCLE = \"\\xe2\\x97\\xaf\";

/**
 * Searches forward from `start` (up to `limit`) for the EARLIEST occurrence of either placeholder
 * character. Returns true and fills outStart/outEnd if one was found.
 */
static auto forwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                        GtkTextIter* outEnd) -> bool {
    GtkTextIter bulletSearch = *start;
    GtkTextIter bulletStart;
    GtkTextIter bulletEnd;
    bool foundBullet = gtk_text_iter_forward_search(&bulletSearch, PLACEHOLDER_BULLET, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                     &bulletStart, &bulletEnd, limit);
    GtkTextIter circleSearch = *start;
    GtkTextIter circleStart;
    GtkTextIter circleEnd;
    bool foundCircle = gtk_text_iter_forward_search(&circleSearch, PLACEHOLDER_CIRCLE, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                     &circleStart, &circleEnd, limit);
    if (foundBullet && (!foundCircle || gtk_text_iter_compare(&bulletStart, &circleStart) <= 0)) {
        *outStart = bulletStart;
        *outEnd = bulletEnd;
        return true;
    }
    if (foundCircle) {
        *outStart = circleStart;
        *outEnd = circleEnd;
        return true;
    }
    return false;
}

/**
 * Searches backward from `start` (down to `limit`) for the LATEST (closest to `start`) occurrence of
 * either placeholder character. Returns true and fills outStart/outEnd if one was found.
 */
static auto backwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                         GtkTextIter* outEnd) -> bool {
    GtkTextIter bulletSearch = *start;
    GtkTextIter bulletStart;
    GtkTextIter bulletEnd;
    bool foundBullet = gtk_text_iter_backward_search(&bulletSearch, PLACEHOLDER_BULLET, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                      &bulletStart, &bulletEnd, limit);
    GtkTextIter circleSearch = *start;
    GtkTextIter circleStart;
    GtkTextIter circleEnd;
    bool foundCircle = gtk_text_iter_backward_search(&circleSearch, PLACEHOLDER_CIRCLE, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                      &circleStart, &circleEnd, limit);
    if (foundBullet && (!foundCircle || gtk_text_iter_compare(&bulletStart, &circleStart) >= 0)) {
        *outStart = bulletStart;
        *outEnd = bulletEnd;
        return true;
    }
    if (foundCircle) {
        *outStart = circleStart;
        *outEnd = circleEnd;
        return true;
    }
    return false;
}

void IntEdLatexDialog::updateCompletionPopup(bool isNavigation) {"""
IED_NEW1 = """ */
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

void IntEdLatexDialog::updateCompletionPopup(bool isNavigation) {"""
IED_OLD2 = """        return;
    }
    std::string word = this->getCurrentLatexWord();
    // A backslash plus at least the term's own first two letters, i.e. 3 characters minimum.
    if (word.size() < 3) {
        this->hideCompletionPopup();
        return;
    }"""
IED_NEW2 = """        return;
    }
    std::string word = this->getCurrentLatexWord();
    // Patch 13.17: a backslash plus at least autocompletionTriggerLength letters (2 by default,
    // matching the original hardcoded threshold this replaces).
    if (word.size() < 1 + static_cast<size_t>(std::max(1, this->texCtrl->settings.autocompletionTriggerLength))) {
        this->hideCompletionPopup();
        return;
    }"""
IED_OLD3 = """    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
    // untouched.
    //
    // Patch 13.16: the character appended here is now the large circle (PLACEHOLDER_CIRCLE), not
    // another bullet - the detection check above still looks for the dictionary's own bullet
    // character, unaffected. This distinct character lets an auto-appended trailing placeholder be
    // told apart from the term's own placeholder(s) if ever needed later, while every
    // placeholder-searching function below treats both characters with fully identical properties.
    if (term.find(PLACEHOLDER_BULLET) != std::string::npos) {
        term += \" \";
        term += PLACEHOLDER_CIRCLE;
    }
    std::string word = this->getCurrentLatexWord();
"""
IED_NEW3 = """    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
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
"""
GLADE_OLD0 = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!-- Generated with glade 3.40.0 -->
<interface>
  <requires lib=\"gtk+\" version=\"3.24\"/>
  <object class=\"GtkFileFilter\" id=\"filefilter1\">
    <mime-types>
      <mime-type>application/x-latex</mime-type>
      <mime-type>text/x-tex</mime-type>
    </mime-types>
  </object>"""
GLADE_NEW0 = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!-- Generated with glade 3.40.0 -->
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
      <mime-type>application/x-latex</mime-type>
      <mime-type>text/x-tex</mime-type>
    </mime-types>
  </object>"""
GLADE_OLD1 = """                                <property name=\"expand\">False</property>
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
                                <property name=\"visible\">True</property>"""
GLADE_NEW1 = """                                <property name=\"expand\">False</property>
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
                                <property name=\"position\">3</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkButton\" id=\"btnOpenLatexCompletionFile\">
                                <property name=\"label\" translatable=\"yes\">Open dictionary</property>
                                <property name=\"visible\">True</property>"""
GLADE_OLD2 = """                                <property name=\"receives-default\">True</property>
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
                          <object class=\"GtkLabel\">"""
GLADE_NEW2 = """                                <property name=\"receives-default\">True</property>
                                <property name=\"halign\">start</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">4</property>
                              </packing>
                            </child>
                          </object>
                        </child>
                        <child type=\"label\">
                          <object class=\"GtkLabel\">"""
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
"""
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

#: ../ui/latexSettings.glade:661
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"

#: ../ui/latexSettings.glade:672
msgid \"Open dictionary\"
msgstr \"\"

#: ../ui/latexSettings.glade:690
msgid \"Autocompletion\"
msgstr \"\"
"""
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

#: ../ui/latexSettings.glade:541
msgid \"Enable autocompletion\"
msgstr \"Activer le compléteur automatique\"

#: ../ui/latexSettings.glade:558
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
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

#: ../ui/latexSettings.glade:661
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
FR_OLD2 = """\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"
"""
FR_NEW2 = """\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:672
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:690
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"
"""
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

#: ../ui/latexSettings.glade:541
msgid \"Enable autocompletion\"
msgstr \"Autovervollständigung aktivieren\"

#: ../ui/latexSettings.glade:558
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
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

#: ../ui/latexSettings.glade:661
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
DE_OLD2 = """\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"
"""
DE_NEW2 = """\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:672
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:690
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"
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
    paths = {
        "ls_h": Path("src/core/control/settings/LatexSettings.h"),
        "settings": Path("src/core/control/settings/Settings.cpp"),
        "lsp_h": Path("src/core/gui/dialog/LatexSettingsPanel.h"),
        "lsp_cpp": Path("src/core/gui/dialog/LatexSettingsPanel.cpp"),
        "ied": Path("src/core/gui/dialog/IntEdLatexDialog.cpp"),
        "glade": Path("ui/latexSettings.glade"),
        "pot": Path("po/xournalpp.pot"),
        "fr": Path("po/fr.po"),
        "de": Path("po/de.po"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "getFullLatexWordAroundCursor" not in paths["ied"].read_text(encoding="utf-8"):
        print("[ECHEC] getFullLatexWordAroundCursor introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion.py puis les patchs 13.12 a 13.16.")
        sys.exit(1)
    if "autocompletionTriggerLength" in paths["ls_h"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.17 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["ls_h"], LS_H_OLD0, LS_H_NEW0, "ls_h: zone 1/1")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD0, SETTINGS_NEW0, "settings: zone 1/2")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD1, SETTINGS_NEW1, "settings: zone 2/2")
    ok &= apply_edit(paths["lsp_h"], LSP_H_OLD0, LSP_H_NEW0, "lsp_h: zone 1/1")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD0, LSP_CPP_NEW0, "lsp_cpp: zone 1/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD1, LSP_CPP_NEW1, "lsp_cpp: zone 2/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD2, LSP_CPP_NEW2, "lsp_cpp: zone 3/4")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD3, LSP_CPP_NEW3, "lsp_cpp: zone 4/4")
    ok &= apply_edit(paths["ied"], IED_OLD0, IED_NEW0, "ied: zone 1/4")
    ok &= apply_edit(paths["ied"], IED_OLD1, IED_NEW1, "ied: zone 2/4")
    ok &= apply_edit(paths["ied"], IED_OLD2, IED_NEW2, "ied: zone 3/4")
    ok &= apply_edit(paths["ied"], IED_OLD3, IED_NEW3, "ied: zone 4/4")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/3")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/3")
    ok &= apply_edit(paths["glade"], GLADE_OLD2, GLADE_NEW2, "glade: zone 3/3")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/2")
    ok &= apply_edit(paths["pot"], POT_OLD1, POT_NEW1, "pot: zone 2/2")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/3")
    ok &= apply_edit(paths["fr"], FR_OLD1, FR_NEW1, "fr: zone 2/3")
    ok &= apply_edit(paths["fr"], FR_OLD2, FR_NEW2, "fr: zone 3/3")
    ok &= apply_edit(paths["de"], DE_OLD0, DE_NEW0, "de: zone 1/3")
    ok &= apply_edit(paths["de"], DE_OLD1, DE_NEW1, "de: zone 2/3")
    ok &= apply_edit(paths["de"], DE_OLD2, DE_NEW2, "de: zone 3/3")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
