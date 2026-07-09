#!/usr/bin/env python3
"""
Patch 10.4 (phase 10) : ajoute une case "Coordinate system assist" sous
"Page centering assist" dans l'onglet Snapping.

Nouveau reglage Settings::coordinateSystemAssistEnabled (persistant,
getter/setter), qui controle EXCLUSIVEMENT l'assistant de croisement de
ligne pendant le trace (voir BaseShapeHandler::applyLineCrossingSnap(),
patch 8.4). Contrairement aux reglages des patchs 10.2/10.3, celui-ci est
INDEPENDANT du systeme d'alignement d'objets (EditSelection.cpp) - il
vit dans un fichier different (BaseShapeHandler.cpp, utilise par
RulerHandler et ArrowHandler) et ne depend pas de isSnapToObjects().

Un seul point de garde (au debut de applyLineCrossingSnap() lui-meme)
suffit a couvrir les deux appelants (RulerHandler::createShape() et
ArrowHandler::createShape()).

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/BaseShapeHandler.cpp (garde au debut de
    applyLineCrossingSnap())
  - ui/settings.glade (nouvelle case, sous Page centering assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_3.py + apply_alignment_snap_v8_4_0.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isPageCenteringSnappingEnabled() const;
    void setPageCenteringSnappingEnabled(bool b);

"""
NEW_H1 = """    bool isPageCenteringSnappingEnabled() const;
    void setPageCenteringSnappingEnabled(bool b);

    /// Patch 10.4: gates the line-crossing snap assist during shape drawing (see
    /// BaseShapeHandler::applyLineCrossingSnap(), patch 8.4) - independent of the object alignment
    /// snapping system entirely (does not depend on isSnapToObjects()).
    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.3: whether the page-centering tier of the object alignment snapping system is
     * enabled. Nested under snapToObjects - see isPageCenteringSnappingEnabled() above.
     */
    bool pageCenteringSnappingEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.3: whether the page-centering tier of the object alignment snapping system is
     * enabled. Nested under snapToObjects - see isPageCenteringSnappingEnabled() above.
     */
    bool pageCenteringSnappingEnabled{};

    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled.
     * Independent of the object alignment snapping system - see
     * isCoordinateSystemAssistEnabled() above.
     */
    bool coordinateSystemAssistEnabled{};

    /**
"""
OLD_C1 = """    this->pageCenteringSnappingEnabled = true;
"""
NEW_C1 = """    this->pageCenteringSnappingEnabled = true;
    this->coordinateSystemAssistEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"pageCenteringSnappingEnabled\")) == 0) {
        this->pageCenteringSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"pageCenteringSnappingEnabled\")) == 0) {
        this->pageCenteringSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"coordinateSystemAssistEnabled\")) == 0) {
        this->coordinateSystemAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(pageCenteringSnappingEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(pageCenteringSnappingEnabled);
    SAVE_BOOL_PROP(coordinateSystemAssistEnabled);
"""
OLD_C4 = """void Settings::setPageCenteringSnappingEnabled(bool b) {
    if (this->pageCenteringSnappingEnabled == b) {
        return;
    }

    this->pageCenteringSnappingEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setPageCenteringSnappingEnabled(bool b) {
    if (this->pageCenteringSnappingEnabled == b) {
        return;
    }

    this->pageCenteringSnappingEnabled = b;
    save();
}

auto Settings::isCoordinateSystemAssistEnabled() const -> bool { return this->coordinateSystemAssistEnabled; }

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {
        return;
    }

    this->coordinateSystemAssistEnabled = b;
    save();
}
"""
OLD_SHAPE = """auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    double dx = rawEnd.x - this->startPoint.x;
"""
NEW_SHAPE = """auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    if (control != nullptr && control->getSettings() != nullptr &&
        !control->getSettings()->isCoordinateSystemAssistEnabled()) {
        return rawEnd;
    }

    double dx = rawEnd.x - this->startPoint.x;
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbPageCenteringAssist\">
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
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbPageCenteringAssist\">
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
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbCoordinateSystemAssist\">
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
OLD_LOAD = """    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());
"""
OLD_SAVE = """    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
"""
NEW_SAVE = """    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));
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
    shape_cpp = Path("src/core/control/tools/BaseShapeHandler.cpp")
    glade = Path("ui/settings.glade")
    dialog_cpp = Path("src/core/gui/dialog/SettingsDialog.cpp")
    for p in (settings_h, settings_cpp, shape_cpp, glade, dialog_cpp):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)

    if "cbPageCenteringAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.3 (cbPageCenteringAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_3.py, puis relancez ce script.")
        sys.exit(1)
    if "applyLineCrossingSnap" not in shape_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] applyLineCrossingSnap introuvable dans BaseShapeHandler.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_4_0.py, puis relancez ce script.")
        sys.exit(1)
    if "coordinateSystemAssistEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.4 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isCoordinateSystemAssistEnabled/setCoordinateSystemAssistEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre coordinateSystemAssistEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(shape_cpp, OLD_SHAPE, NEW_SHAPE, "BaseShapeHandler.cpp: applyLineCrossingSnap() verifie le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Coordinate system assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbCoordinateSystemAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbCoordinateSystemAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
