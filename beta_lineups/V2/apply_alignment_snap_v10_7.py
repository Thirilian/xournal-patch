#!/usr/bin/env python3
"""
Patch 10.7 (phase 10) : ajoute une case "Table content centering
assist" sous "Graduation orientation" dans l'onglet Snapping.

Nouveau reglage Settings::tableContentCenteringAssistEnabled
(persistant, getter/setter), qui controle EXCLUSIVEMENT le palier
"centre de tableau" (voir findTableCenterX/Y() en EditSelection.cpp,
patch 8.7.0) - le centrage d'un Text/TexImage/Image entre deux lignes
paralleles de meme longueur delimitant une colonne/rangee de tableau.

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EditSelection.cpp (le point d'appel unique de
    findTableCenterX/Y verifie desormais ce reglage)
  - ui/settings.glade (nouvelle case, sous Graduation orientation)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_6B_2.py + apply_alignment_snap_v8_7_0.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isGraduationOrientationEnabled() const;
    void setGraduationOrientationEnabled(bool b);

"""
NEW_H1 = """    bool isGraduationOrientationEnabled() const;
    void setGraduationOrientationEnabled(bool b);

    /// Patch 10.7: gates the \"table center\" tier (see findTableCenterX/Y() in EditSelection.cpp,
    /// patch 8.7.0) - centering a Text/TexImage/Image between two same-length parallel lines
    /// bounding a table column/row. Nested under snapToObjects.
    bool isTableContentCenteringAssistEnabled() const;
    void setTableContentCenteringAssistEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.6B: whether Top/Middle/Below mode switching by cursor drag position is enabled. Nested
     * under graduationAssistEnabled in the UI - see isGraduationOrientationEnabled() above.
     */
    bool graduationOrientationEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.6B: whether Top/Middle/Below mode switching by cursor drag position is enabled. Nested
     * under graduationAssistEnabled in the UI - see isGraduationOrientationEnabled() above.
     */
    bool graduationOrientationEnabled{};

    /**
     * Patch 10.7: whether the \"table center\" tier is enabled. Nested under snapToObjects - see
     * isTableContentCenteringAssistEnabled() above.
     */
    bool tableContentCenteringAssistEnabled{};

    /**
"""
OLD_C1 = """    this->graduationOrientationEnabled = true;
"""
NEW_C1 = """    this->graduationOrientationEnabled = true;
    this->tableContentCenteringAssistEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationOrientationEnabled\")) == 0) {
        this->graduationOrientationEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationOrientationEnabled\")) == 0) {
        this->graduationOrientationEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"tableContentCenteringAssistEnabled\")) == 0) {
        this->tableContentCenteringAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(graduationOrientationEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(graduationOrientationEnabled);
    SAVE_BOOL_PROP(tableContentCenteringAssistEnabled);
"""
OLD_C4 = """void Settings::setGraduationOrientationEnabled(bool b) {
    if (this->graduationOrientationEnabled == b) {
        return;
    }

    this->graduationOrientationEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setGraduationOrientationEnabled(bool b) {
    if (this->graduationOrientationEnabled == b) {
        return;
    }

    this->graduationOrientationEnabled = b;
    save();
}

auto Settings::isTableContentCenteringAssistEnabled() const -> bool {
    return this->tableContentCenteringAssistEnabled;
}

void Settings::setTableContentCenteringAssistEnabled(bool b) {
    if (this->tableContentCenteringAssistEnabled == b) {
        return;
    }

    this->tableContentCenteringAssistEnabled = b;
    save();
}
"""
OLD_EDIT = """                if (selfIsTableTarget) {
"""
NEW_EDIT = """                if (selfIsTableTarget && settings->isTableContentCenteringAssistEnabled()) {
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbGraduationOrientation\">
                                        <property name=\"label\" translatable=\"yes\">Graduation orientation</property>
                                        <property name=\"name\">cbGraduationOrientation</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">5</property>
                                      </packing>
                                    </child>
                                  </object>
                                </child>
"""
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbGraduationOrientation\">
                                        <property name=\"label\" translatable=\"yes\">Graduation orientation</property>
                                        <property name=\"name\">cbGraduationOrientation</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">5</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbTableContentCenteringAssist\">
                                        <property name=\"label\" translatable=\"yes\">Table content centering assist</property>
                                        <property name=\"name\">cbTableContentCenteringAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">6</property>
                                      </packing>
                                    </child>
                                  </object>
                                </child>
"""
OLD_LOAD = """    loadCheckbox(\"cbGraduationOrientation\", settings->isGraduationOrientationEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbGraduationOrientation\", settings->isGraduationOrientationEnabled());
    loadCheckbox(\"cbTableContentCenteringAssist\", settings->isTableContentCenteringAssistEnabled());
"""
OLD_SAVE = """    settings->setGraduationOrientationEnabled(getCheckbox(\"cbGraduationOrientation\"));
"""
NEW_SAVE = """    settings->setGraduationOrientationEnabled(getCheckbox(\"cbGraduationOrientation\"));
    settings->setTableContentCenteringAssistEnabled(getCheckbox(\"cbTableContentCenteringAssist\"));
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
    settings_h = Path("src/core/control/settings/Settings.h")
    settings_cpp = Path("src/core/control/settings/Settings.cpp")
    edit_cpp = Path("src/core/control/tools/EditSelection.cpp")
    glade = Path("ui/settings.glade")
    dialog_cpp = Path("src/core/gui/dialog/SettingsDialog.cpp")
    for p in (settings_h, settings_cpp, edit_cpp, glade, dialog_cpp):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)

    if "cbGraduationOrientation" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.6B (cbGraduationOrientation) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_6B.py (+ v10_6B_2.py), puis relancez ce script.")
        sys.exit(1)
    if "findTableCenterX" not in edit_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] findTableCenterX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_7_0.py, puis relancez ce script.")
        sys.exit(1)
    if "tableContentCenteringAssistEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.7 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isTableContentCenteringAssistEnabled/setTableContentCenteringAssistEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre tableContentCenteringAssistEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(edit_cpp, OLD_EDIT, NEW_EDIT, "EditSelection.cpp: findTableCenterX/Y verifient le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Table content centering assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbTableContentCenteringAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbTableContentCenteringAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
