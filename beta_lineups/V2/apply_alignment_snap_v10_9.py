#!/usr/bin/env python3
"""
Patch 10.9 (phase 10 - le 10.8 est saute, correspondant au patch 8.8
lui-meme saute) : ajoute une case "Snapping when drawing a spline" sous
"Table content centering assist" dans l'onglet Snapping.

Nouveau reglage Settings::splineSnappingEnabled (persistant,
getter/setter), qui controle EXCLUSIVEMENT l'accroche d'alignement
ordinaire (vert/rose) pour le point mobile de l'outil spline (voir
SplineHandler::onMotionNotifyEvent(), patch 8.9.0). Comme le patch
8.9.0 lui-meme, ce reglage est INDEPENDANT du systeme d'alignement
d'objets (EditSelection.cpp) - ne depend pas de isSnapToObjects().

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/SplineHandler.cpp (le point d'appel de
    findSplinePointAlignmentX/Y verifie desormais ce reglage)
  - ui/settings.glade (nouvelle case, sous Table content centering
    assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_7.py + apply_alignment_snap_v8_9_0.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isTableContentCenteringAssistEnabled() const;
    void setTableContentCenteringAssistEnabled(bool b);

"""
NEW_H1 = """    bool isTableContentCenteringAssistEnabled() const;
    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0). Independent of the object alignment
    /// snapping system entirely (does not depend on isSnapToObjects()) - matches how patch 8.9.0 was
    /// designed as a standalone feature for a different tool.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.7: whether the \"table center\" tier is enabled. Nested under snapToObjects - see
     * isTableContentCenteringAssistEnabled() above.
     */
    bool tableContentCenteringAssistEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.7: whether the \"table center\" tier is enabled. Nested under snapToObjects - see
     * isTableContentCenteringAssistEnabled() above.
     */
    bool tableContentCenteringAssistEnabled{};

    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled.
     * Independent of the object alignment snapping system - see isSplineSnappingEnabled() above.
     */
    bool splineSnappingEnabled{};

    /**
"""
OLD_C1 = """    this->tableContentCenteringAssistEnabled = true;
"""
NEW_C1 = """    this->tableContentCenteringAssistEnabled = true;
    this->splineSnappingEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"tableContentCenteringAssistEnabled\")) == 0) {
        this->tableContentCenteringAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"tableContentCenteringAssistEnabled\")) == 0) {
        this->tableContentCenteringAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"splineSnappingEnabled\")) == 0) {
        this->splineSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(tableContentCenteringAssistEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(tableContentCenteringAssistEnabled);
    SAVE_BOOL_PROP(splineSnappingEnabled);
"""
OLD_C4 = """void Settings::setTableContentCenteringAssistEnabled(bool b) {
    if (this->tableContentCenteringAssistEnabled == b) {
        return;
    }

    this->tableContentCenteringAssistEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setTableContentCenteringAssistEnabled(bool b) {
    if (this->tableContentCenteringAssistEnabled == b) {
        return;
    }

    this->tableContentCenteringAssistEnabled = b;
    save();
}

auto Settings::isSplineSnappingEnabled() const -> bool { return this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {
        return;
    }

    this->splineSnappingEnabled = b;
    save();
}
"""
OLD_SP = """            if (layer != nullptr) {
"""
NEW_SP = """            if (layer != nullptr && control->getSettings() != nullptr &&
                control->getSettings()->isSplineSnappingEnabled()) {
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbTableContentCenteringAssist\">
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
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbTableContentCenteringAssist\">
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
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbSplineSnapping\">
                                        <property name=\"label\" translatable=\"yes\">Snapping when drawing a spline</property>
                                        <property name=\"name\">cbSplineSnapping</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">7</property>
                                      </packing>
                                    </child>
                                  </object>
                                </child>
"""
OLD_LOAD = """    loadCheckbox(\"cbTableContentCenteringAssist\", settings->isTableContentCenteringAssistEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbTableContentCenteringAssist\", settings->isTableContentCenteringAssistEnabled());
    loadCheckbox(\"cbSplineSnapping\", settings->isSplineSnappingEnabled());
"""
OLD_SAVE = """    settings->setTableContentCenteringAssistEnabled(getCheckbox(\"cbTableContentCenteringAssist\"));
"""
NEW_SAVE = """    settings->setTableContentCenteringAssistEnabled(getCheckbox(\"cbTableContentCenteringAssist\"));
    settings->setSplineSnappingEnabled(getCheckbox(\"cbSplineSnapping\"));
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
    spline_cpp = Path("src/core/control/tools/SplineHandler.cpp")
    glade = Path("ui/settings.glade")
    dialog_cpp = Path("src/core/gui/dialog/SettingsDialog.cpp")
    for p in (settings_h, settings_cpp, spline_cpp, glade, dialog_cpp):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)

    if "cbTableContentCenteringAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.7 (cbTableContentCenteringAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_7.py, puis relancez ce script.")
        sys.exit(1)
    if "findSplinePointAlignmentX" not in spline_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] findSplinePointAlignmentX introuvable dans SplineHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_9_0.py, puis relancez ce script.")
        sys.exit(1)
    if "splineSnappingEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.9 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isSplineSnappingEnabled/setSplineSnappingEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre splineSnappingEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(spline_cpp, OLD_SP, NEW_SP, "SplineHandler.cpp: alignement du point mobile verifie le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Snapping when drawing a spline'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbSplineSnapping")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbSplineSnapping")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
