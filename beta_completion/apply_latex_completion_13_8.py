#!/usr/bin/env python3
"""
Patch 13.8 ("completion LaTeX") : nouveau cadre "Compl\u00e9teur automatique"
("Autocompletion") dans l'onglet LaTeX des Preferences, dans le cadre
"Parametres de l'editeur" ("Editor settings"), entre les cadres "Police"
("Font") et "Editeur externe (experts seulement)".

Contenu du nouveau cadre :
  - Un texte explicatif : le fichier peut etre modifie pour ajouter ses
    propres termes, et plus un terme est haut dans le fichier, plus il
    est prioritaire lors de la completion.
  - Une case a cocher "Activer le completeur automatique"
    (autocompletionEnabled, nouveau parametre LatexSettings, active par
    defaut) - controle si le popup de suggestion (patch 13.1 et
    suivants) s'affiche pendant la frappe. La navigation Tab/Maj+Tab a
    travers des placeholders deja presents dans le buffer n'est jamais
    affectee par ce parametre.
  - Un bouton "Ouvrir le dictionnaire", qui ouvre
    LaTeX_completion.txt (le creant d'abord si absent) avec
    l'application par defaut du systeme, via
    g_app_info_launch_default_for_uri() - l'abstraction cross-platform
    propre de GLib (Linux/macOS/Windows), pas une commande specifique a
    une plateforme (xdg-open, ShellExecute...).

Le tout est traduisible : chaines ajoutees a po/xournalpp.pot, avec
traductions francaises (po/fr.po) et allemandes (po/de.po) fournies.

Note sur la portabilite Windows (question posee par l'utilisateur) :
le fichier LaTeX_completion.txt est place via Util::getConfigFolder(),
qui repose sur g_get_user_config_dir() (GLib) - deja portable sans
modification, puisque cette fonction resout automatiquement le bon
dossier de configuration selon la plateforme (dont Windows).

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.cpp (touche F1 au lieu
    d'Echap pour fermer le popup - evite le conflit avec
    l'accelerateur Echap du bouton Annuler du dialogue LaTeX ; logique
    de creation de fichier deplacee vers l'utilitaire partage ;
    verification du nouveau parametre avant d'afficher le popup)
  - src/core/control/settings/LatexSettings.h (nouveau champ
    autocompletionEnabled)
  - src/core/control/settings/Settings.cpp (chargement/sauvegarde XML)
  - src/util/include/util/PathUtil.h /
    src/util/PathUtil.cpp (nouvel utilitaire partage
    Util::getOrCreateLatexCompletionFile())
  - ui/latexSettings.glade (nouveau cadre)
  - src/core/gui/dialog/LatexSettingsPanel.h /
    src/core/gui/dialog/LatexSettingsPanel.cpp (case a cocher, bouton)
  - po/xournalpp.pot, po/fr.po, po/de.po (traductions)

NECESSITE : apply_latex_completion_13_6.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

CPP1_OLD0 = """                                 case GDK_KEY_KP_Enter:
                                     self->commitCompletion();
                                     return true;
                                 case GDK_KEY_Escape:
                                     self->hideCompletionPopup();
                                     return true;
                                 default:"""
CPP1_NEW0 = """                                 case GDK_KEY_KP_Enter:
                                     self->commitCompletion();
                                     return true;
                                 // Patch 13.7: F1, not Escape - the LaTeX dialog's Cancel button has
                                 // its own Escape accelerator (bound in intEdTexDialog.glade), which
                                 // operates at the window level and could close the whole dialog
                                 // instead of (or in addition to) just this popup.
                                 case GDK_KEY_F1:
                                     self->hideCompletionPopup();
                                     return true;
                                 default:"""
CPP1_OLD1 = """
void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    Util::ensureFolderExists(Util::getConfigFolder());
    auto completionFile = Util::getConfigFolder() / \"LaTeX_completion.txt\";
    if (!fs::exists(completionFile)) {
        // Patch 13.1.1: create the file, with a short explanatory header, so the user has an actual
        // file to open and edit right away - rather than silently doing nothing until they create it
        // themselves from scratch (with the exact right name, location and format).
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
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // Still couldn't be read (e.g. permissions) - not a hard error, just means no completions are"""
CPP1_NEW1 = """
void IntEdLatexDialog::loadCompletionTerms() {
    this->completionTerms.clear();
    // Patch 13.8: file creation logic moved to Util::getOrCreateLatexCompletionFile(), now shared with
    // LatexSettingsPanel's \"Open dictionary\" button.
    auto completionFile = Util::getOrCreateLatexCompletionFile();
    std::ifstream ifs(completionFile);
    if (!ifs.is_open()) {
        // Still couldn't be read (e.g. permissions) - not a hard error, just means no completions are"""
CPP1_OLD2 = """}

void IntEdLatexDialog::updateCompletionPopup() {
    std::string word = this->getCurrentLatexWord();
    // A backslash plus at least the term's own first two letters, i.e. 3 characters minimum.
    if (word.size() < 3) {"""
CPP1_NEW2 = """}

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
    if (word.size() < 3) {"""
H1_OLD0 = """    bool externalEditorAutoConfirm{false};
    std::string externalEditorCmd{};
    std::string temporaryFileExt{\"tex\"};
};"""
H1_NEW0 = """    bool externalEditorAutoConfirm{false};
    std::string externalEditorCmd{};
    std::string temporaryFileExt{\"tex\"};

    /**
     * Patch 13.8: whether the LaTeX_completion.txt-based autocompletion popup (patch 13.1 onwards) is
     * offered while typing in the internal editor.
     */
    bool autocompletionEnabled{true};
};"""
CPP2_OLD0 = """        this->latexSettings.externalEditorCmd = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.temporaryFileExt\")) == 0) {
        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
CPP2_NEW0 = """        this->latexSettings.externalEditorCmd = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.temporaryFileExt\")) == 0) {
        this->latexSettings.temporaryFileExt = std::string{reinterpret_cast<char*>(value)};
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionEnabled\")) == 0) {
        this->latexSettings.autocompletionEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
CPP2_OLD1 = """    SAVE_BOOL_PROP(latexSettings.externalEditorAutoConfirm);
    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
CPP2_NEW1 = """    SAVE_BOOL_PROP(latexSettings.externalEditorAutoConfirm);
    SAVE_STRING_PROP(latexSettings.externalEditorCmd);
    SAVE_STRING_PROP(latexSettings.temporaryFileExt);
    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
H2_OLD0 = """ */
[[maybe_unused]] [[nodiscard]] fs::path getConfigFolder();
[[maybe_unused]] [[nodiscard]] fs::path getConfigSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getCacheSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getDataSubfolder(const fs::path& subfolder = \"\");
[[maybe_unused]] [[nodiscard]] fs::path getStateSubfolder(const fs::path& subfolder = \"\");"""
H2_NEW0 = """ */
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
CPP3_OLD0 = """    return Util::ensureFolderExists(p);
}

auto Util::getCacheSubfolder(const fs::path& subfolder) -> fs::path {
    auto p = GFilename(g_get_user_cache_dir()).toPath().value_or(fs::path());
    p /= CONFIG_FOLDER_NAME;"""
CPP3_NEW0 = """    return Util::ensureFolderExists(p);
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
                              <object class=\"GtkLabel\" id=\"lbLatexCompletionDescription\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"halign\">start</property>
                                <property name=\"label\" translatable=\"yes\">This file can be edited to add your own terms - the higher up a term appears in the file, the higher its priority during completion.</property>
                                <property name=\"wrap\">True</property>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
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
H3_OLD0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
};"""
H3_NEW0 = """    GtkFileChooser* globalTemplateChooser;
    GtkWidget* sourceViewThemeSelector;
    GtkCheckButton* cbUseSystemFont;
    /// Patch 13.8: \"Enable autocompletion\" checkbox in the new \"Autocompletion\" frame.
    GtkCheckButton* cbLatexAutocompletion;
};"""
CPP4_OLD0 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
CPP4_NEW0 = """        cbAutoDepCheck(GTK_CHECK_BUTTON(builder.get(\"latexSettingsRunCheck\"))),
        // Todo(gtk4): replace this GtkFileChooserButton (by what?)
        globalTemplateChooser(GTK_FILE_CHOOSER(builder.get(\"latexSettingsTemplateFile\"))),
        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
CPP4_OLD1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

#ifdef ENABLE_GTK_SOURCEVIEW
    GtkBox* themeSelectionBox = GTK_BOX(builder.get(\"bxThemeSelectionContainer\"));
    this->sourceViewThemeSelector = gtk_source_style_scheme_chooser_button_new();"""
CPP4_NEW1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
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
CPP4_OLD2 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    this->updateWidgetSensitivity();
}
"""
CPP4_NEW2 = """    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")), settings.externalEditorCmd.c_str());
    gtk_editable_set_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")), settings.temporaryFileExt.c_str());

    // Patch 13.8
    gtk_check_button_set_active(this->cbLatexAutocompletion, settings.autocompletionEnabled);

    this->updateWidgetSensitivity();
}
"""
CPP4_OLD3 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));
}

void LatexSettingsPanel::checkDeps() {"""
CPP4_NEW3 = """            gtk_check_button_get_active(GTK_CHECK_BUTTON(builder.get(\"cbExternalEditorAutoConfirm\")));
    settings.externalEditorCmd = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexExternalEditorCmd\")));
    settings.temporaryFileExt = gtk_editable_get_text(GTK_EDITABLE(builder.get(\"latexTemporaryFileExt\")));

    // Patch 13.8
    settings.autocompletionEnabled = gtk_check_button_get_active(this->cbLatexAutocompletion);
}

void LatexSettingsPanel::checkDeps() {"""
POT_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"\""""
POT_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:544
msgid \"\"
\"This file can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"

#: ../ui/latexSettings.glade:555
msgid \"Enable autocompletion\"
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
FR_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
FR_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Confirmer automatiquement lorsque l'éditeur est fermé\"

#: ../ui/latexSettings.glade:544
msgid \"\"
\"This file can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Ce fichier peut être modifié pour ajouter vos propres termes - plus un \"
\"terme apparaît haut dans le fichier, plus sa priorité est élevée lors de \"
\"la complétion.\"

#: ../ui/latexSettings.glade:555
msgid \"Enable autocompletion\"
msgstr \"Activer le compléteur automatique\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Éditeur externe (expert seulement)\""""
DE_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""
DE_NEW0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"Beim Beenden des Editors automatisch bestätigen\"

#: ../ui/latexSettings.glade:544
msgid \"\"
\"This file can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"
\"Diese Datei kann bearbeitet werden, um eigene Begriffe hinzuzufügen - je \"
\"weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:555
msgid \"Enable autocompletion\"
msgstr \"Autovervollständigung aktivieren\"

#: ../ui/latexSettings.glade:569
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:587
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"

#: ../ui/latexSettings.glade:649
msgid \"External Editor (Expert user only)\"
msgstr \"Externer Editor (nur für Experte)\""""


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
        "h1": Path("src/core/control/settings/LatexSettings.h"),
        "cpp2": Path("src/core/control/settings/Settings.cpp"),
        "h2": Path("src/util/include/util/PathUtil.h"),
        "cpp3": Path("src/util/PathUtil.cpp"),
        "glade": Path("ui/latexSettings.glade"),
        "h3": Path("src/core/gui/dialog/LatexSettingsPanel.h"),
        "cpp4": Path("src/core/gui/dialog/LatexSettingsPanel.cpp"),
        "pot": Path("po/xournalpp.pot"),
        "fr": Path("po/fr.po"),
        "de": Path("po/de.po"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "navigatePlaceholder" not in paths["cpp1"].read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord les patchs 13.1 a 13.6, puis relancez ce script.")
        sys.exit(1)
    if "autocompletionEnabled" in paths["h1"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.8 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["cpp1"], CPP1_OLD0, CPP1_NEW0, "cpp1: zone 1/3")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD1, CPP1_NEW1, "cpp1: zone 2/3")
    ok &= apply_edit(paths["cpp1"], CPP1_OLD2, CPP1_NEW2, "cpp1: zone 3/3")
    ok &= apply_edit(paths["h1"], H1_OLD0, H1_NEW0, "h1: zone 1/1")
    ok &= apply_edit(paths["cpp2"], CPP2_OLD0, CPP2_NEW0, "cpp2: zone 1/2")
    ok &= apply_edit(paths["cpp2"], CPP2_OLD1, CPP2_NEW1, "cpp2: zone 2/2")
    ok &= apply_edit(paths["h2"], H2_OLD0, H2_NEW0, "h2: zone 1/1")
    ok &= apply_edit(paths["cpp3"], CPP3_OLD0, CPP3_NEW0, "cpp3: zone 1/1")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/1")
    ok &= apply_edit(paths["h3"], H3_OLD0, H3_NEW0, "h3: zone 1/1")
    ok &= apply_edit(paths["cpp4"], CPP4_OLD0, CPP4_NEW0, "cpp4: zone 1/4")
    ok &= apply_edit(paths["cpp4"], CPP4_OLD1, CPP4_NEW1, "cpp4: zone 2/4")
    ok &= apply_edit(paths["cpp4"], CPP4_OLD2, CPP4_NEW2, "cpp4: zone 3/4")
    ok &= apply_edit(paths["cpp4"], CPP4_OLD3, CPP4_NEW3, "cpp4: zone 4/4")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/1")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/1")
    ok &= apply_edit(paths["de"], DE_OLD0, DE_NEW0, "de: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
