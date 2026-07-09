#!/usr/bin/env python3
"""
Patch 10.5 (phase 10) : ajoute une case "Circle assist" sous "Coordinate
system assist" dans l'onglet Snapping.

Nouveau reglage Settings::circleAssistEnabled (persistant,
getter/setter), qui controle EXCLUSIVEMENT l'assistant de cercle parfait
("diagonal snap") pendant le trace d'une ellipse (voir
EllipseHandler::createShape(), patch 8.5). Comme le patch 10.4,
independant du systeme d'alignement d'objets (EditSelection.cpp) - ne
depend pas de isSnapToObjects().

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EllipseHandler.cpp (garde sur la condition du
    snap diagonal, dans la branche non-Shift)
  - ui/settings.glade (nouvelle case, sous Coordinate system assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_4.py + apply_alignment_snap_v8_5_0.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

"""
NEW_H1 = """    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

    /// Patch 10.5: gates the \"diagonal snap\" perfect-circle assist during ellipse drawing (see
    /// EllipseHandler::createShape(), patch 8.5) - independent of the object alignment snapping
    /// system entirely (does not depend on isSnapToObjects()).
    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled.
     * Independent of the object alignment snapping system - see
     * isCoordinateSystemAssistEnabled() above.
     */
    bool coordinateSystemAssistEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled.
     * Independent of the object alignment snapping system - see
     * isCoordinateSystemAssistEnabled() above.
     */
    bool coordinateSystemAssistEnabled{};

    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled. Independent of the object alignment snapping system - see isCircleAssistEnabled()
     * above.
     */
    bool circleAssistEnabled{};

    /**
"""
OLD_C1 = """    this->coordinateSystemAssistEnabled = true;
"""
NEW_C1 = """    this->coordinateSystemAssistEnabled = true;
    this->circleAssistEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"coordinateSystemAssistEnabled\")) == 0) {
        this->coordinateSystemAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"coordinateSystemAssistEnabled\")) == 0) {
        this->coordinateSystemAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"circleAssistEnabled\")) == 0) {
        this->circleAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(coordinateSystemAssistEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(coordinateSystemAssistEnabled);
    SAVE_BOOL_PROP(circleAssistEnabled);
"""
OLD_C4 = """void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {
        return;
    }

    this->coordinateSystemAssistEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {
        return;
    }

    this->coordinateSystemAssistEnabled = b;
    save();
}

auto Settings::isCircleAssistEnabled() const -> bool { return this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {
        return;
    }

    this->circleAssistEnabled = b;
    save();
}
"""
OLD_ELLIPSE = """        this->diagonalSnapGuide.reset();
        constexpr double DIAGONAL_SNAP_TOLERANCE_PX = 6.0;
        double tolerance = DIAGONAL_SNAP_TOLERANCE_PX / this->lastZoom;
        if (std::abs(std::abs(width) - std::abs(height)) < tolerance) {
"""
NEW_ELLIPSE = """        this->diagonalSnapGuide.reset();
        bool circleAssistEnabled = control == nullptr || control->getSettings() == nullptr ||
                                    control->getSettings()->isCircleAssistEnabled();
        constexpr double DIAGONAL_SNAP_TOLERANCE_PX = 6.0;
        double tolerance = DIAGONAL_SNAP_TOLERANCE_PX / this->lastZoom;
        if (circleAssistEnabled && std::abs(std::abs(width) - std::abs(height)) < tolerance) {
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbCoordinateSystemAssist\">
                                        <property name=\"label\" translatable=\"yes\">Coordinate system assist</property>
                                        <property name=\"name\">cbCoordinateSystemAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">2</property>
                                      </packing>
                                    </child>
                                  </object>
"""
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbCoordinateSystemAssist\">
                                        <property name=\"label\" translatable=\"yes\">Coordinate system assist</property>
                                        <property name=\"name\">cbCoordinateSystemAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">2</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbCircleAssist\">
                                        <property name=\"label\" translatable=\"yes\">Circle assist</property>
                                        <property name=\"name\">cbCircleAssist</property>
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
                                  </object>
"""
OLD_LOAD = """    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());
    loadCheckbox(\"cbCircleAssist\", settings->isCircleAssistEnabled());
"""
OLD_SAVE = """    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));
"""
NEW_SAVE = """    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));
    settings->setCircleAssistEnabled(getCheckbox(\"cbCircleAssist\"));
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
    ellipse_cpp = Path("src/core/control/tools/EllipseHandler.cpp")
    glade = Path("ui/settings.glade")
    dialog_cpp = Path("src/core/gui/dialog/SettingsDialog.cpp")
    for p in (settings_h, settings_cpp, ellipse_cpp, glade, dialog_cpp):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)

    if "cbCoordinateSystemAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.4 (cbCoordinateSystemAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_4.py, puis relancez ce script.")
        sys.exit(1)
    if "diagonalSnapGuide" not in ellipse_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] diagonalSnapGuide introuvable dans EllipseHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_5_0.py, puis relancez ce script.")
        sys.exit(1)
    if "circleAssistEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.5 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isCircleAssistEnabled/setCircleAssistEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre circleAssistEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(ellipse_cpp, OLD_ELLIPSE, NEW_ELLIPSE, "EllipseHandler.cpp: le snap diagonal verifie le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Circle assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbCircleAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbCircleAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
