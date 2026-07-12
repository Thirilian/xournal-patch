#!/usr/bin/env python3
"""
Patch 13.18 ("completion LaTeX") : nouvelle case a cocher "Allow
cursor navigation alone to trigger the popup" dans le cadre
"Compleeur automatique" des Preferences, entre le menu deroulant
"Trailing placeholder after completion:" et le texte explicatif sur
le dictionnaire.

Si desactivee : la navigation seule au curseur (fleches, clic - voir
le gestionnaire du signal "mark-set" et le parametre isNavigation de
updateCompletionPopup() dans IntEdLatexDialog.cpp) ne peut plus JAMAIS
faire passer le popup de "ferme" a "ouvert". La frappe elle-meme reste
totalement inchangee dans tous les cas et continue de declencher le
popup normalement.

POINT IMPORTANT : le gate ne bloque QUE la transition "ferme -> ouvert"
(verifie via currentMatches.empty()) - un popup DEJA ouvert (ex: juste
apres une frappe) continue de se mettre a jour/se fermer normalement
au fil des mouvements de curseur suivants, exactement comme avant.
Sans cette nuance, naviguer hors d'un mot pendant qu'un popup est
deja affiche laisserait ce dernier ouvert a tort.

Modifie :
  - src/core/control/settings/LatexSettings.h / Settings.cpp (nouveau
    parametre autocompletionOnNavigation, actif par defaut)
  - src/core/gui/dialog/LatexSettingsPanel.h / .cpp (case a cocher)
  - src/core/gui/dialog/IntEdLatexDialog.cpp (gate dans
    updateCompletionPopup())
  - ui/latexSettings.glade (nouvelle ligne dans le cadre - la case a
    cocher et le decalage de position du label voisin sont fusionnes
    en un seul bloc de remplacement pour eviter toute ambiguite de
    motif une fois la case inseree)
  - po/xournalpp.pot, po/fr.po, po/de.po (traductions)

NECESSITE : apply_latex_completion.py, puis les patchs 13.12 a 13.17
(deja appliques).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

LS_H_OLD0 = """     * Preferences.
     */
    int autocompletionTrailingPlaceholder{2};
};"""
LS_H_NEW0 = """     * Preferences.
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
SETTINGS_OLD0 = """                                       \"latexSettings.autocompletionTrailingPlaceholder\")) == 0) {
        this->latexSettings.autocompletionTrailingPlaceholder =
                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_NEW0 = """                                       \"latexSettings.autocompletionTrailingPlaceholder\")) == 0) {
        this->latexSettings.autocompletionTrailingPlaceholder =
                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"latexSettings.autocompletionOnNavigation\")) ==
               0) {
        this->latexSettings.autocompletionOnNavigation =
                xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapRecognizedShapesEnabled\")) == 0) {
        this->snapRecognizedShapesEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"restoreLineWidthEnabled\")) == 0) {"""
SETTINGS_OLD1 = """    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);
    SAVE_INT_PROP(latexSettings.autocompletionTriggerLength);
    SAVE_INT_PROP(latexSettings.autocompletionTrailingPlaceholder);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
SETTINGS_NEW1 = """    SAVE_BOOL_PROP(latexSettings.autocompletionEnabled);
    SAVE_INT_PROP(latexSettings.autocompletionTriggerLength);
    SAVE_INT_PROP(latexSettings.autocompletionTrailingPlaceholder);
    SAVE_BOOL_PROP(latexSettings.autocompletionOnNavigation);

    xmlNodePtr xmlFont = nullptr;
    xmlFont = xmlNewChild(root, nullptr, reinterpret_cast<const xmlChar*>(\"property\"), nullptr);"""
LSP_H_OLD0 = """    GtkSpinButton* spLatexTriggerLength;
    /// Patch 13.17: which character (if any) is appended after a term with a placeholder of its own.
    GtkComboBoxText* cbxLatexTrailingPlaceholder;
};"""
LSP_H_NEW0 = """    GtkSpinButton* spLatexTriggerLength;
    /// Patch 13.17: which character (if any) is appended after a term with a placeholder of its own.
    GtkComboBoxText* cbxLatexTrailingPlaceholder;
    /// Patch 13.18: \"Allow cursor navigation alone to trigger the popup\" checkbox.
    GtkCheckButton* cbLatexAutocompletionOnNavigation;
};"""
LSP_CPP_OLD0 = """        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))),
        spLatexTriggerLength(GTK_SPIN_BUTTON(builder.get(\"spLatexTriggerLength\"))),
        cbxLatexTrailingPlaceholder(GTK_COMBO_BOX_TEXT(builder.get(\"cbxLatexTrailingPlaceholder\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_NEW0 = """        cbUseSystemFont(GTK_CHECK_BUTTON(builder.get(\"cbUseSystemFont\"))),
        cbLatexAutocompletion(GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletion\"))),
        spLatexTriggerLength(GTK_SPIN_BUTTON(builder.get(\"spLatexTriggerLength\"))),
        cbxLatexTrailingPlaceholder(GTK_COMBO_BOX_TEXT(builder.get(\"cbxLatexTrailingPlaceholder\"))),
        cbLatexAutocompletionOnNavigation(
                GTK_CHECK_BUTTON(builder.get(\"cbLatexAutocompletionOnNavigation\"))) {

    g_signal_connect_swapped(builder.get(\"latexSettingsTestBtn\"), \"clicked\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->checkDeps(); }), this);"""
LSP_CPP_OLD1 = """    gtk_combo_box_set_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder),
                             settings.autocompletionTrailingPlaceholder);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_NEW1 = """    gtk_combo_box_set_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder),
                             settings.autocompletionTrailingPlaceholder);

    // Patch 13.18
    gtk_check_button_set_active(this->cbLatexAutocompletionOnNavigation, settings.autocompletionOnNavigation);

    this->updateWidgetSensitivity();
}
"""
LSP_CPP_OLD2 = """            std::max(1, static_cast<int>(gtk_spin_button_get_value_as_int(this->spLatexTriggerLength)));
    settings.autocompletionTrailingPlaceholder =
            gtk_combo_box_get_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder));
}

void LatexSettingsPanel::checkDeps() {"""
LSP_CPP_NEW2 = """            std::max(1, static_cast<int>(gtk_spin_button_get_value_as_int(this->spLatexTriggerLength)));
    settings.autocompletionTrailingPlaceholder =
            gtk_combo_box_get_active(GTK_COMBO_BOX(this->cbxLatexTrailingPlaceholder));

    // Patch 13.18
    settings.autocompletionOnNavigation = gtk_check_button_get_active(this->cbLatexAutocompletionOnNavigation);
}

void LatexSettingsPanel::checkDeps() {"""
IED_OLD0 = """        this->hideCompletionPopup();
        return;
    }
    std::string word = this->getCurrentLatexWord();
    // Patch 13.17: a backslash plus at least autocompletionTriggerLength letters (2 by default,
    // matching the original hardcoded threshold this replaces)."""
IED_NEW0 = """        this->hideCompletionPopup();
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
    // matching the original hardcoded threshold this replaces)."""
GLADE_OLD0 = """                              <packing>
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
"""
GLADE_NEW0 = """                              <packing>
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
"""
GLADE_OLD1 = """                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">4</property>
                              </packing>
                            </child>
                          </object>"""
GLADE_NEW1 = """                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">5</property>
                              </packing>
                            </child>
                          </object>"""
POT_OLD0 = """msgid \"Trailing placeholder after completion:\"
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
POT_NEW0 = """msgid \"Trailing placeholder after completion:\"
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
"""
FR_OLD0 = """msgid \"Trailing placeholder after completion:\"
msgstr \"Repère ajouté en fin de complétion :\"

#: ../ui/latexSettings.glade:661
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
FR_NEW0 = """msgid \"Trailing placeholder after completion:\"
msgstr \"Repère ajouté en fin de complétion :\"

#: ../ui/latexSettings.glade:658
msgid \"Allow cursor navigation alone to trigger the popup\"
msgstr \"Autoriser la simple navigation au curseur à déclencher le popup\"

#: ../ui/latexSettings.glade:675
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
FR_OLD1 = """\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:672
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:690
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"
"""
FR_NEW1 = """\"un terme apparaît haut dans le fichier, plus sa priorité est élevée lors \"
\"de la complétion.\"

#: ../ui/latexSettings.glade:686
msgid \"Open dictionary\"
msgstr \"Ouvrir le dictionnaire\"

#: ../ui/latexSettings.glade:704
msgid \"Autocompletion\"
msgstr \"Compléteur automatique\"
"""
DE_OLD0 = """msgid \"Trailing placeholder after completion:\"
msgstr \"Nachgestellter Platzhalter nach Vervollständigung:\"

#: ../ui/latexSettings.glade:661
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
DE_NEW0 = """msgid \"Trailing placeholder after completion:\"
msgstr \"Nachgestellter Platzhalter nach Vervollständigung:\"

#: ../ui/latexSettings.glade:658
msgid \"Allow cursor navigation alone to trigger the popup\"
msgstr \"Reine Cursor-Navigation kann das Popup auslösen\"

#: ../ui/latexSettings.glade:675
msgid \"\"
\"The dictionary can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\""""
DE_OLD1 = """\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:672
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:690
msgid \"Autocompletion\"
msgstr \"Autovervollständigung\"
"""
DE_NEW1 = """\"je weiter oben ein Begriff in der Datei steht, desto höher ist seine \"
\"Priorität bei der Vervollständigung.\"

#: ../ui/latexSettings.glade:686
msgid \"Open dictionary\"
msgstr \"Wörterbuch öffnen\"

#: ../ui/latexSettings.glade:704
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
    if "autocompletionTrailingPlaceholder" not in paths["ls_h"].read_text(encoding="utf-8"):
        print("[ECHEC] autocompletionTrailingPlaceholder introuvable dans LatexSettings.h.")
        print("        Appliquez d'abord apply_latex_completion.py et les patchs 13.12 a 13.17.")
        sys.exit(1)
    if "autocompletionOnNavigation" in paths["ls_h"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.18 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["ls_h"], LS_H_OLD0, LS_H_NEW0, "ls_h: zone 1/1")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD0, SETTINGS_NEW0, "settings: zone 1/2")
    ok &= apply_edit(paths["settings"], SETTINGS_OLD1, SETTINGS_NEW1, "settings: zone 2/2")
    ok &= apply_edit(paths["lsp_h"], LSP_H_OLD0, LSP_H_NEW0, "lsp_h: zone 1/1")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD0, LSP_CPP_NEW0, "lsp_cpp: zone 1/3")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD1, LSP_CPP_NEW1, "lsp_cpp: zone 2/3")
    ok &= apply_edit(paths["lsp_cpp"], LSP_CPP_OLD2, LSP_CPP_NEW2, "lsp_cpp: zone 3/3")
    ok &= apply_edit(paths["ied"], IED_OLD0, IED_NEW0, "ied: zone 1/1")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/2")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/2")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/1")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/2")
    ok &= apply_edit(paths["fr"], FR_OLD1, FR_NEW1, "fr: zone 2/2")
    ok &= apply_edit(paths["de"], DE_OLD0, DE_NEW0, "de: zone 1/2")
    ok &= apply_edit(paths["de"], DE_OLD1, DE_NEW1, "de: zone 2/2")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
