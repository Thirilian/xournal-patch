#!/usr/bin/env python3
"""
Version 2 (fusionnee) : ajoute un bouton de couleur directement dans la
fenetre d'edition LaTeX (pour changer %%XPP_TEXT_COLOR%% / TOOL_LATEX sans
fermer le dialogue modal, avec recompilation automatique), ET corrige des le
depart le probleme de focus que ce bouton induisait (le focus est desormais
correctement rendu a la zone de texte a l'ouverture).
Remplace apply_color_widget.py + apply_focus_fix.py (ne pas appliquer les
deux anciens scripts en plus de celui-ci).
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    ok = True

    fg = Path("ui/intEdTexDialog.glade")
    ok &= apply_edit(
        fg,
        old='        <child>\n'
            '          <object class="GtkLabel" id="labelTitle">\n'
            '            <property name="name">labelTitle</property>\n'
            '            <property name="visible">True</property>\n'
            '            <property name="can-focus">False</property>\n'
            '            <property name="label" translatable="yes">Enter / edit LaTeX Text</property>\n'
            '            <property name="use-markup">True</property>\n'
            '            <property name="justify">center</property>\n'
            '          </object>\n'
            '          <packing>\n'
            '            <property name="expand">False</property>\n'
            '            <property name="fill">False</property>\n'
            '            <property name="padding">9</property>\n'
            '            <property name="position">0</property>\n'
            '          </packing>\n'
            '        </child>',
        new='        <child>\n'
            '          <object class="GtkBox" id="titleRow">\n'
            '            <property name="visible">True</property>\n'
            '            <property name="can-focus">False</property>\n'
            '            <property name="orientation">horizontal</property>\n'
            '            <property name="spacing">4</property>\n'
            '            <child>\n'
            '              <object class="GtkLabel" id="labelTitle">\n'
            '                <property name="name">labelTitle</property>\n'
            '                <property name="visible">True</property>\n'
            '                <property name="can-focus">False</property>\n'
            '                <property name="label" translatable="yes">Enter / edit LaTeX Text</property>\n'
            '                <property name="use-markup">True</property>\n'
            '                <property name="justify">center</property>\n'
            '                <property name="hexpand">True</property>\n'
            '              </object>\n'
            '              <packing>\n'
            '                <property name="expand">True</property>\n'
            '                <property name="fill">True</property>\n'
            '                <property name="position">0</property>\n'
            '              </packing>\n'
            '            </child>\n'
            '            <child>\n'
            '              <object class="GtkColorButton" id="btColor">\n'
            '                <property name="visible">True</property>\n'
            '                <property name="can-focus">True</property>\n'
            '                <property name="receives-default">True</property>\n'
            '                <property name="use-alpha">False</property>\n'
            '                <property name="tooltip-text" translatable="yes">Formula color</property>\n'
            '              </object>\n'
            '              <packing>\n'
            '                <property name="expand">False</property>\n'
            '                <property name="fill">False</property>\n'
            '                <property name="position">1</property>\n'
            '              </packing>\n'
            '            </child>\n'
            '          </object>\n'
            '          <packing>\n'
            '            <property name="expand">False</property>\n'
            '            <property name="fill">False</property>\n'
            '            <property name="padding">9</property>\n'
            '            <property name="position">0</property>\n'
            '          </packing>\n'
            '        </child>',
        label="intEdTexDialog.glade: ajout du GtkColorButton",
    )

    fc = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    ok &= apply_edit(
        fc,
        old='#include "control/LatexController.h"\n'
            '#include "control/settings/LatexSettings.h"  // for LatexSettings\n'
            '#include "gui/Builder.h"\n'
            '#include "model/Font.h"        // for XojFont\n'
            '#include "util/StringUtils.h"  // for replace_pair, StringUtils\n'
            '#include "util/raii/CStringWrapper.h"',
        new='#include "control/Control.h"\n'
            '#include "control/LatexController.h"\n'
            '#include "control/Tool.h"\n'
            '#include "control/ToolHandler.h"\n'
            '#include "control/settings/LatexSettings.h"  // for LatexSettings\n'
            '#include "gui/Builder.h"\n'
            '#include "model/Font.h"        // for XojFont\n'
            '#include "util/Color.h"        // for rgb_to_GdkRGBA, GdkRGBA_to_argb\n'
            '#include "util/StringUtils.h"  // for replace_pair, StringUtils\n'
            '#include "util/raii/CStringWrapper.h"',
        label="IntEdLatexDialog.cpp: includes",
    )

    ok &= apply_edit(
        fc,
        old='    populateStandardWidgetsFromBuilder(builder);\n\n',
        new='    populateStandardWidgetsFromBuilder(builder);\n\n'
            '    /*\n'
            '     * Color button: lets the user change the formula\'s color without leaving/closing this dialog\n'
            '     * (the dialog is modal, so the main window\'s toolbar color picker is otherwise unreachable).\n'
            '     * Changing it updates the TOOL_LATEX tool color (the same one read at compile time) and\n'
            '     * triggers a recompile so the preview reflects the new color immediately.\n'
            '     */\n'
            '    GtkColorButton* colorButton = GTK_COLOR_BUTTON(builder.get("btColor"));\n'
            '    Control* ctrlPtr = texCtrl->control;\n'
            '    GdkRGBA initialColor = Util::rgb_to_GdkRGBA(ctrlPtr->getToolHandler()->getTool(TOOL_LATEX).getColor());\n'
            '    gtk_color_chooser_set_rgba(GTK_COLOR_CHOOSER(colorButton), &initialColor);\n'
            '    g_signal_connect(colorButton, "color-set", G_CALLBACK(+[](GtkColorButton* btn, gpointer d) {\n'
            '                         auto texCtrl = static_cast<LatexController*>(d);\n'
            '                         GdkRGBA newColor;\n'
            '                         gtk_color_chooser_get_rgba(GTK_COLOR_CHOOSER(btn), &newColor);\n'
            '                         texCtrl->control->getToolHandler()->getTool(TOOL_LATEX).setColor(\n'
            '                                 Util::GdkRGBA_to_argb(newColor));\n'
            '                         LatexController::handleTexChanged(texCtrl);\n'
            '                     }),\n'
            '                     texCtrl.get());\n\n',
        label="IntEdLatexDialog.cpp: initialisation + signal color-set",
    )

    ok &= apply_edit(
        fc,
        old='    connectStandardSignals();\n\n',
        new='    connectStandardSignals();\n\n'
            '    // Adding a focusable color button (see btColor above) changed GTK\'s default initial-focus\n'
            '    // target: it landed on the button instead of the text editor. Restore focus to the text\n'
            '    // editor once the window is shown.\n'
            '    g_signal_connect(this->getWindow(), "show", G_CALLBACK(+[](GtkWidget*, gpointer d) {\n'
            '                         gtk_widget_grab_focus(GTK_WIDGET(d));\n'
            '                     }),\n'
            '                     this->texBox);\n\n',
        label="IntEdLatexDialog.cpp: correctif de focus",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
