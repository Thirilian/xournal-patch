#!/usr/bin/env python3
"""
Patch 10.3 (phase 10) : ajoute une case "Page centering assist" sous
"Equidistant assist" dans l'onglet Snapping.

Meme principe que le patch 10.2 : nouveau reglage
Settings::pageCenteringSnappingEnabled (persistant, getter/setter), qui
controle EXCLUSIVEMENT le palier de centrage de page (voir
computePageCenterX() en EditSelection.cpp, patch 8.3.0). Si decochee,
seul ce palier precis ne se declenche plus - les autres (ordinaire,
equidistant, boosted, table-centre, grille bleue) continuent de
fonctionner normalement tant que "Object Alignment Snapping" (menu Edit)
reste actif.

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EditSelection.cpp (le point d'appel de
    computePageCenterX verifie desormais aussi ce reglage)
  - ui/settings.glade (nouvelle case, sous Equidistant assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_2.py + apply_alignment_snap_v8_3_0.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isEquidistantSnappingEnabled() const;
    void setEquidistantSnappingEnabled(bool b);

"""
NEW_H1 = """    bool isEquidistantSnappingEnabled() const;
    void setEquidistantSnappingEnabled(bool b);

    /// Patch 10.3: gates specifically the page-centering tier of the object alignment snapping
    /// system (see computePageCenterX() in EditSelection.cpp), independently of the other tiers.
    /// Only takes effect while isSnapToObjects() is also true.
    bool isPageCenteringSnappingEnabled() const;
    void setPageCenteringSnappingEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.2: whether the equidistant (\"equal spacing\") tier of the object alignment snapping
     * system is enabled. Nested under snapToObjects - see isEquidistantSnappingEnabled() above.
     */
    bool equidistantSnappingEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.2: whether the equidistant (\"equal spacing\") tier of the object alignment snapping
     * system is enabled. Nested under snapToObjects - see isEquidistantSnappingEnabled() above.
     */
    bool equidistantSnappingEnabled{};

    /**
     * Patch 10.3: whether the page-centering tier of the object alignment snapping system is
     * enabled. Nested under snapToObjects - see isPageCenteringSnappingEnabled() above.
     */
    bool pageCenteringSnappingEnabled{};

    /**
"""
OLD_C1 = """    this->equidistantSnappingEnabled = true;
"""
NEW_C1 = """    this->equidistantSnappingEnabled = true;
    this->pageCenteringSnappingEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"equidistantSnappingEnabled\")) == 0) {
        this->equidistantSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"equidistantSnappingEnabled\")) == 0) {
        this->equidistantSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"pageCenteringSnappingEnabled\")) == 0) {
        this->pageCenteringSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(equidistantSnappingEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(equidistantSnappingEnabled);
    SAVE_BOOL_PROP(pageCenteringSnappingEnabled);
"""
OLD_C4 = """void Settings::setEquidistantSnappingEnabled(bool b) {
    if (this->equidistantSnappingEnabled == b) {
        return;
    }

    this->equidistantSnappingEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setEquidistantSnappingEnabled(bool b) {
    if (this->equidistantSnappingEnabled == b) {
        return;
    }

    this->equidistantSnappingEnabled = b;
    save();
}

auto Settings::isPageCenteringSnappingEnabled() const -> bool { return this->pageCenteringSnappingEnabled; }

void Settings::setPageCenteringSnappingEnabled(bool b) {
    if (this->pageCenteringSnappingEnabled == b) {
        return;
    }

    this->pageCenteringSnappingEnabled = b;
    save();
}
"""
OLD_EDIT = """                if (!matchXIsBoostedForPageCenter && this->sourcePage) {
"""
NEW_EDIT = """                if (!matchXIsBoostedForPageCenter && this->sourcePage && settings->isPageCenteringSnappingEnabled()) {
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbEquidistantAssist\">
                                        <property name=\"label\" translatable=\"yes\">Equidistant assist</property>
                                        <property name=\"name\">cbEquidistantAssist</property>
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
                                  </object>
"""
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbEquidistantAssist\">
                                        <property name=\"label\" translatable=\"yes\">Equidistant assist</property>
                                        <property name=\"name\">cbEquidistantAssist</property>
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
                                      <object class=\"GtkCheckButton\" id=\"cbPageCenteringAssist\">
                                        <property name=\"label\" translatable=\"yes\">Page centering assist</property>
                                        <property name=\"name\">cbPageCenteringAssist</property>
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
                                  </object>
"""
OLD_LOAD = """    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
"""
OLD_SAVE = """    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
"""
NEW_SAVE = """    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
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

    if "cbEquidistantAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.2 (cbEquidistantAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_2.py, puis relancez ce script.")
        sys.exit(1)
    if "computePageCenterX" not in edit_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] computePageCenterX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_3_0.py, puis relancez ce script.")
        sys.exit(1)
    if "pageCenteringSnappingEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.3 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isPageCenteringSnappingEnabled/setPageCenteringSnappingEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre pageCenteringSnappingEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(edit_cpp, OLD_EDIT, NEW_EDIT, "EditSelection.cpp: le palier de centrage de page verifie le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Page centering assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbPageCenteringAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbPageCenteringAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
