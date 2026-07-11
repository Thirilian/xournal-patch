#!/usr/bin/env python3
"""
Patch 13.9 ("completion LaTeX") : deux corrections au cadre
"Autocompletion" demandees par l'utilisateur, avec capture d'ecran.

1. Reordonnancement : la case a cocher "Activer le completeur
   automatique" apparait desormais EN PREMIER, suivie du texte
   explicatif, puis du bouton "Ouvrir le dictionnaire" (auparavant :
   texte, case a cocher, bouton).

2. Reformulation du texte explicatif : "Ce fichier peut etre modifie..."
   devient "Le dictionnaire peut etre modifie..." (et l'equivalent
   anglais "This file can be edited..." devient "The dictionary can be
   edited..."), coherent avec le nom du bouton "Ouvrir le dictionnaire".

Traductions francaise et allemande mises a jour en consequence.

Modifie :
  - ui/latexSettings.glade
  - po/xournalpp.pot, po/fr.po, po/de.po

NECESSITE : apply_latex_completion_13_8.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

GLADE_OLD0 = """                            <property name=\"margin-bottom\">8</property>
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
                                <property name=\"expand\">False</property>"""
GLADE_NEW0 = """                            <property name=\"margin-bottom\">8</property>
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
                                <property name=\"expand\">False</property>"""
GLADE_OLD1 = """                              </packing>
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
                                <property name=\"expand\">False</property>"""
GLADE_NEW1 = """                              </packing>
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
                                <property name=\"expand\">False</property>"""
POT_OLD0 = """msgid \"Automatically confirm on editor exit\"
msgstr \"\"

#: ../ui/latexSettings.glade:544
msgid \"\"
\"This file can be edited to add your own terms - the higher up a term \"
\"appears in the file, the higher its priority during completion.\"
msgstr \"\"

#: ../ui/latexSettings.glade:555
msgid \"Enable autocompletion\"
msgstr \"\"

#: ../ui/latexSettings.glade:569"""
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

#: ../ui/latexSettings.glade:569"""
FR_OLD0 = """msgid \"Automatically confirm on editor exit\"
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
msgid \"Open dictionary\""""
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
msgid \"Open dictionary\""""
DE_OLD0 = """msgid \"Automatically confirm on editor exit\"
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
msgstr \"Wörterbuch öffnen\""""
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
msgstr \"Wörterbuch öffnen\""""


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
        "glade": Path("ui/latexSettings.glade"),
        "pot": Path("po/xournalpp.pot"),
        "fr": Path("po/fr.po"),
        "de": Path("po/de.po"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "frameLatexCompletionSettings" not in paths["glade"].read_text(encoding="utf-8"):
        print("[ECHEC] frameLatexCompletionSettings introuvable dans latexSettings.glade.")
        print("        Appliquez d'abord apply_latex_completion_13_8.py, puis relancez ce script.")
        sys.exit(1)
    if "The dictionary can be edited" in paths["glade"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.9 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/2")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/2")
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
