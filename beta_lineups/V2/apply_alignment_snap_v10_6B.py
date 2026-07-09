#!/usr/bin/env python3
"""
Patch 10.6B (phase 10) : ajoute une case "Graduation orientation",
indentee sous "Graduation assist" dans l'onglet Snapping, grisee si
celle-ci est desactivee (meme pattern generique enableWithCheckbox() que
"cbAutosave"/"boxAutosave").

Nouveau reglage Settings::graduationOrientationEnabled (persistant,
getter/setter), qui controle EXCLUSIVEMENT la possibilite de changer de
mode Top/Middle/Below en glissant la souris (voir le calcul de zone base
sur le curseur + la "fresh line zone override" du patch 8.6.6, dans
EditSelection.cpp). Si desactivee, l'ancrage des petites lignes reste
TOUJOURS en mode Middle, quelle que soit la position du curseur pendant
le glissement - independamment de toute famille deja etablie.

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EditSelection.cpp (le calcul de zone par
    curseur, dans les deux branches Y-boosted et X-boosted, est
    desormais conditionne a ce reglage)
  - ui/settings.glade (nouvelle case indentee, sous Graduation assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case, plus la connexion du signal et l'appel d'initialisation pour
    la hierarchisation dynamique)

NECESSITE : apply_alignment_snap_v10_6A.py + apply_alignment_snap_v10_6A_2.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isGraduationAssistEnabled() const;
    void setGraduationAssistEnabled(bool b);

"""
NEW_H1 = """    bool isGraduationAssistEnabled() const;
    void setGraduationAssistEnabled(bool b);

    /// Patch 10.6B: gates the ability to switch between Top/Middle/Below modes by dragging the
    /// cursor to a different zone (see the \"fresh line\" zone override in EditSelection.cpp, patch
    /// 8.6.6, and the raw cursor-based zone computation it builds on). If disabled, line anchoring
    /// always uses Middle mode, regardless of cursor position during the drag. Nested under
    /// isGraduationAssistEnabled() in the Preferences UI, but independently gated in code.
    bool isGraduationOrientationEnabled() const;
    void setGraduationOrientationEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.6A: whether the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
     * behavior is enabled. Nested under snapToObjects - see isGraduationAssistEnabled() above.
     */
    bool graduationAssistEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.6A: whether the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
     * behavior is enabled. Nested under snapToObjects - see isGraduationAssistEnabled() above.
     */
    bool graduationAssistEnabled{};

    /**
     * Patch 10.6B: whether Top/Middle/Below mode switching by cursor drag position is enabled. Nested
     * under graduationAssistEnabled in the UI - see isGraduationOrientationEnabled() above.
     */
    bool graduationOrientationEnabled{};

    /**
"""
OLD_C1 = """    this->graduationAssistEnabled = true;
"""
NEW_C1 = """    this->graduationAssistEnabled = true;
    this->graduationOrientationEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationAssistEnabled\")) == 0) {
        this->graduationAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationAssistEnabled\")) == 0) {
        this->graduationAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationOrientationEnabled\")) == 0) {
        this->graduationOrientationEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(graduationAssistEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(graduationAssistEnabled);
    SAVE_BOOL_PROP(graduationOrientationEnabled);
"""
OLD_C4 = """void Settings::setGraduationAssistEnabled(bool b) {
    if (this->graduationAssistEnabled == b) {
        return;
    }

    this->graduationAssistEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setGraduationAssistEnabled(bool b) {
    if (this->graduationAssistEnabled == b) {
        return;
    }

    this->graduationAssistEnabled = b;
    save();
}

auto Settings::isGraduationOrientationEnabled() const -> bool { return this->graduationOrientationEnabled; }

void Settings::setGraduationOrientationEnabled(bool b) {
    if (this->graduationOrientationEnabled == b) {
        return;
    }

    this->graduationOrientationEnabled = b;
    save();
}
"""
OLD_YB = """                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already
                    // boost-snapped to ANY big line when this drag started (this->startingWasBoosted
                    // == false) may not settle into Top/Below on its own just because the cursor
                    // dragged it into that zone - it must default to Middle, UNLESS other same-size,
                    // same-orientation lines are already established on THIS big line, in which case
                    // it follows their mode instead. A line that WAS already attached somewhere at
                    // mouseDown keeps full free transition between zones, as before.
                    if (!this->startingWasBoosted) {
                        int familyMode = 0;
                        bool familyFound = false;
                        double selfLengthForFamily = height;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == yBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isVerticalShaft =
                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                            if (!isVerticalShaft || std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                continue;
                            }
                            if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                shaft.x + shaft.width)) {
                                continue;
                            }
                            double shaftCenterY = shaft.y + shaft.height / 2;
                            if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            double farEdge = shaft.y + shaft.height;
                            double nearEdge = shaft.y;
                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = -1;
                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = 1;
                            } else {
                                familyMode = 0;
                            }
                            familyFound = true;
                            break;
                        }
                        this->activeBoostedZone = familyFound ? familyMode : 0;
                    }

"""
NEW_YB = """                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already
                        // boost-snapped to ANY big line when this drag started (this->startingWasBoosted
                        // == false) may not settle into Top/Below on its own just because the cursor
                        // dragged it into that zone - it must default to Middle, UNLESS other same-size,
                        // same-orientation lines are already established on THIS big line, in which case
                        // it follows their mode instead. A line that WAS already attached somewhere at
                        // mouseDown keeps full free transition between zones, as before.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = height;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == yBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isVerticalShaft =
                                        shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                                if (!isVerticalShaft ||
                                    std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                    shaft.x + shaft.width)) {
                                    continue;
                                }
                                double shaftCenterY = shaft.y + shaft.height / 2;
                                if (std::abs(shaftCenterY - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                    continue;
                                }
                                double farEdge = shaft.y + shaft.height;
                                double nearEdge = shaft.y;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle, regardless of where the cursor is or
                        // whether this line was already part of an established family.
                        this->activeBoostedZone = 0;
                    }

"""
OLD_XB = """                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                    // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case - see
                    // the Y-branch above for the full explanation.
                    if (!this->startingWasBoosted) {
                        int familyMode = 0;
                        bool familyFound = false;
                        double selfLengthForFamily = width;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == xBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isHorizontalShaft =
                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                            if (!isHorizontalShaft || std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                continue;
                            }
                            if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                shaft.y + shaft.height)) {
                                continue;
                            }
                            double shaftCenterX = shaft.x + shaft.width / 2;
                            if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                continue;
                            }
                            double farEdge = shaft.x + shaft.width;
                            double nearEdge = shaft.x;
                            if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = -1;
                            } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                familyMode = 1;
                            } else {
                                familyMode = 0;
                            }
                            familyFound = true;
                            break;
                        }
                        this->activeBoostedZone = familyFound ? familyMode : 0;
                    }

"""
NEW_XB = """                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case -
                        // see the Y-branch above for the full explanation.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = width;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == xBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isHorizontalShaft =
                                        shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                                if (!isHorizontalShaft ||
                                    std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                    shaft.y + shaft.height)) {
                                    continue;
                                }
                                double shaftCenterX = shaft.x + shaft.width / 2;
                                if (std::abs(shaftCenterX - targetCenter) > tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR) {
                                    continue;
                                }
                                double farEdge = shaft.x + shaft.width;
                                double nearEdge = shaft.x;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle.
                        this->activeBoostedZone = 0;
                    }

"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbGraduationAssist\">
                                        <property name=\"label\" translatable=\"yes\">Graduation assist</property>
                                        <property name=\"name\">cbGraduationAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">4</property>
                                      </packing>
                                    </child>
                                  </object>
"""
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbGraduationAssist\">
                                        <property name=\"label\" translatable=\"yes\">Graduation assist</property>
                                        <property name=\"name\">cbGraduationAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">4</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbGraduationOrientation\">
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
"""
OLD_LOAD = """    loadCheckbox(\"cbGraduationAssist\", settings->isGraduationAssistEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbGraduationAssist\", settings->isGraduationAssistEnabled());
    loadCheckbox(\"cbGraduationOrientation\", settings->isGraduationOrientationEnabled());
"""
OLD_SAVE = """    settings->setGraduationAssistEnabled(getCheckbox(\"cbGraduationAssist\"));
"""
NEW_SAVE = """    settings->setGraduationAssistEnabled(getCheckbox(\"cbGraduationAssist\"));
    settings->setGraduationOrientationEnabled(getCheckbox(\"cbGraduationOrientation\"));
"""
OLD_SIGNAL = """    g_signal_connect_swapped(
            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

"""
NEW_SIGNAL = """    g_signal_connect_swapped(
            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

    g_signal_connect_swapped(builder.get(\"cbGraduationAssist\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
                             }),
                             this);

"""
OLD_INIT = """    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
"""
NEW_INIT = """    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
    enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
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

    if "cbGraduationAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.6A (cbGraduationAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_6A.py (+ v10_6A_2.py), puis relancez ce script.")
        sys.exit(1)
    if "graduationOrientationEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.6B semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isGraduationOrientationEnabled/setGraduationOrientationEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre graduationOrientationEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(edit_cpp, OLD_YB, NEW_YB, "EditSelection.cpp: calcul de zone par curseur (branche Y-boosted)")
    ok &= apply_edit(edit_cpp, OLD_XB, NEW_XB, "EditSelection.cpp: calcul de zone par curseur (branche X-boosted)")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Graduation orientation' (indentee)")
    ok &= apply_edit(dialog_cpp, OLD_SIGNAL, NEW_SIGNAL, "SettingsDialog.cpp: connexion du signal toggled")
    ok &= apply_edit(dialog_cpp, OLD_INIT, NEW_INIT, "SettingsDialog.cpp: appel d'initialisation de la sensibilite")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbGraduationOrientation")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbGraduationOrientation")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
