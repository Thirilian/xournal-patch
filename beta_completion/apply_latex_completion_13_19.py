#!/usr/bin/env python3
"""
Patch 13.19 ("completion LaTeX") : si la case "Enable autocompletion"
(cadre "Autocompletion" des Preferences) est decochee, tout le reste
du contenu du cadre est desormais grise (insensible) - a l'exception
de la case elle-meme et de son propre libelle, qui restent actifs afin
de pouvoir la recocher.

Widgets concernes : le spinbutton de declenchement (patch 13.17), le
menu deroulant de placeholder final (13.17), la case "Allow cursor
navigation alone to trigger the popup" (13.18), le texte explicatif
sur le dictionnaire, et le bouton "Open dictionary".

Reutilise le mecanisme deja existant (updateWidgetSensitivity(),
signal "toggled" -> meme fonction, deja utilise pour la police
systeme et l'editeur externe).

Modifie : src/core/gui/dialog/LatexSettingsPanel.cpp (2 zones)

NECESSITE : apply_latex_completion.py, puis les patchs 13.12 a 13.18
(deja appliques).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

OLD_1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

    // Patch 13.8: \"Open dictionary\" - opens LaTeX_completion.txt (creating it first if needed) with
"""
NEW_1 = """    g_signal_connect_swapped(builder.get(\"cbUseExternalEditor\"), \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);
    // Patch 13.19
    g_signal_connect_swapped(this->cbLatexAutocompletion, \"toggled\",
                             G_CALLBACK(+[](LatexSettingsPanel* self) { self->updateWidgetSensitivity(); }), this);

    // Patch 13.8: \"Open dictionary\" - opens LaTeX_completion.txt (creating it first if needed) with
"""
OLD_2 = """    gtk_widget_set_sensitive(builder.get(\"cbExternalEditorAutoConfirm\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexExternalEditorCmd\"), useExternalEditor);
    gtk_widget_set_sensitive(builder.get(\"latexTemporaryFileExt\"), useExternalEditor);
}
"""
NEW_2 = """    gtk_widget_set_sensitive(builder.get(\"cbExternalEditorAutoConfirm\"), useExternalEditor);
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
    cpp = Path("src/core/gui/dialog/LatexSettingsPanel.cpp")
    if not cpp.exists():
        print("[ECHEC] LatexSettingsPanel.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "cbLatexAutocompletionOnNavigation" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] cbLatexAutocompletionOnNavigation introuvable dans LatexSettingsPanel.cpp.")
        print("        Appliquez d'abord apply_latex_completion.py et les patchs 13.12 a 13.18.")
        sys.exit(1)
    if "Patch 13.19" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.19 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "LatexSettingsPanel.cpp: connexion du signal toggled")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "LatexSettingsPanel.cpp: logique de sensibilite")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
