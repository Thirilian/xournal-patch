#!/usr/bin/env python3
"""
Patch 10.6A (phase 10) : ajoute une case "Graduation assist" sous
"Circle assist" dans l'onglet Snapping.

Nouveau reglage Settings::graduationAssistEnabled (persistant,
getter/setter), qui controle EXCLUSIVEMENT les reperes de graduation
(petites marques bleues) et l'accroche forcee a la graduation la plus
proche (voir computeBlueGridX/Y() en EditSelection.cpp, patch 8.6). Ne
touche PAS l'ancrage aux extremites de la grande ligne (patch 8.6.5),
qui reste toujours actif tant que "Object Alignment Snapping" (menu
Edit) est active - conformement a la demande explicite de l'utilisateur.

Un patch 10.6B suivra, ajoutant une case "Graduation orientation"
indentee sous celle-ci (grisee si "Graduation assist" est desactivee),
controlant separement le changement de mode Top/Middle/Below par
glissement de souris.

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EditSelection.cpp (les deux appels de
    computeBlueGridX/Y verifient desormais ce reglage)
  - ui/settings.glade (nouvelle case, sous Circle assist)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_5.py + apply_alignment_snap_v8_6_A.py
+ apply_alignment_snap_v8_6_B.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);

"""
NEW_H1 = """    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);

    /// Patch 10.6A: gates the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
    /// behavior (see computeBlueGridX/Y() in EditSelection.cpp, patch 8.6). Does NOT affect the
    /// line-end anchors (patch 8.6.5), which always stay active as long as isSnapToObjects() is true.
    bool isGraduationAssistEnabled() const;
    void setGraduationAssistEnabled(bool b);

"""
OLD_H2 = """    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled. Independent of the object alignment snapping system - see isCircleAssistEnabled()
     * above.
     */
    bool circleAssistEnabled{};

    /**
"""
NEW_H2 = """    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled. Independent of the object alignment snapping system - see isCircleAssistEnabled()
     * above.
     */
    bool circleAssistEnabled{};

    /**
     * Patch 10.6A: whether the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
     * behavior is enabled. Nested under snapToObjects - see isGraduationAssistEnabled() above.
     */
    bool graduationAssistEnabled{};

    /**
"""
OLD_C1 = """    this->circleAssistEnabled = true;
"""
NEW_C1 = """    this->circleAssistEnabled = true;
    this->graduationAssistEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"circleAssistEnabled\")) == 0) {
        this->circleAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"circleAssistEnabled\")) == 0) {
        this->circleAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationAssistEnabled\")) == 0) {
        this->graduationAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(circleAssistEnabled);
"""
NEW_C3 = """    SAVE_BOOL_PROP(circleAssistEnabled);
    SAVE_BOOL_PROP(graduationAssistEnabled);
"""
OLD_C4 = """void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {
        return;
    }

    this->circleAssistEnabled = b;
    save();
}
"""
NEW_C4 = """void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {
        return;
    }

    this->circleAssistEnabled = b;
    save();
}

auto Settings::isGraduationAssistEnabled() const -> bool { return this->graduationAssistEnabled; }

void Settings::setGraduationAssistEnabled(bool b) {
    if (this->graduationAssistEnabled == b) {
        return;
    }

    this->graduationAssistEnabled = b;
    save();
}
"""
OLD_EDIT = """                if (matchYIsBoosted && yBoostedTarget != nullptr) {
                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is
                    // boosted, even if no same-size crossing line is found below (e.g. self is the
                    // first small line of its size on this big line) - the blue tier's own semantics
                    // should never be second-guessed by the generic equidistant search.
                    matchXIsBoosted = true;
                    if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,
                                                      this->sourceLayer, excluded)) {
                        for (double pos: grid->markerPositions) {
                            this->activeBlueGridMarkers.push_back(
                                    BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});
                        }
                        matchX = grid->forceOffset
                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                   *grid->forceOffset - (candidateX + width / 2), {}}}
                                         : std::nullopt;
                    }
                }
                if (matchXIsBoosted && xBoostedTarget != nullptr) {
                    matchYIsBoosted = true;
                    if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,
                                                      this->sourceLayer, excluded)) {
                        for (double pos: grid->markerPositions) {
                            this->activeBlueGridMarkers.push_back(
                                    BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});
                        }
                        matchY = grid->forceOffset
                                         ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                   *grid->forceOffset - (candidateY + height / 2), {}}}
                                         : std::nullopt;
                    }
"""
NEW_EDIT = """                if (matchYIsBoosted && yBoostedTarget != nullptr) {
                    // Suppress patch 8.1's equidistant behavior on X unconditionally while Y is
                    // boosted, even if no same-size crossing line is found below (e.g. self is the
                    // first small line of its size on this big line) - the blue tier's own semantics
                    // should never be second-guessed by the generic equidistant search.
                    matchXIsBoosted = true;
                    if (settings->isGraduationAssistEnabled()) {
                        if (auto grid = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,
                                                          this->sourceLayer, excluded)) {
                            for (double pos: grid->markerPositions) {
                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});
                            }
                            matchX = grid->forceOffset
                                             ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                       *grid->forceOffset - (candidateX + width / 2), {}}}
                                             : std::nullopt;
                        }
                    }
                }
                if (matchXIsBoosted && xBoostedTarget != nullptr) {
                    matchYIsBoosted = true;
                    if (settings->isGraduationAssistEnabled()) {
                        if (auto grid = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,
                                                          this->sourceLayer, excluded)) {
                            for (double pos: grid->markerPositions) {
                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});
                            }
                            matchY = grid->forceOffset
                                             ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                       *grid->forceOffset - (candidateY + height / 2), {}}}
                                             : std::nullopt;
                        }
                    }
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbCircleAssist\">
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
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbCircleAssist\">
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
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbGraduationAssist\">
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
OLD_LOAD = """    loadCheckbox(\"cbCircleAssist\", settings->isCircleAssistEnabled());
"""
NEW_LOAD = """    loadCheckbox(\"cbCircleAssist\", settings->isCircleAssistEnabled());
    loadCheckbox(\"cbGraduationAssist\", settings->isGraduationAssistEnabled());
"""
OLD_SAVE = """    settings->setCircleAssistEnabled(getCheckbox(\"cbCircleAssist\"));
"""
NEW_SAVE = """    settings->setCircleAssistEnabled(getCheckbox(\"cbCircleAssist\"));
    settings->setGraduationAssistEnabled(getCheckbox(\"cbGraduationAssist\"));
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

    if "cbCircleAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.5 (cbCircleAssist) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_5.py, puis relancez ce script.")
        sys.exit(1)
    if "computeBlueGridX" not in edit_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] computeBlueGridX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord toute la chaine 8.6 (v8_6_A.py + v8_6_B.py), puis relancez ce script.")
        sys.exit(1)
    if "graduationAssistEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.6A semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isGraduationAssistEnabled/setGraduationAssistEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre graduationAssistEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(edit_cpp, OLD_EDIT, NEW_EDIT, "EditSelection.cpp: computeBlueGridX/Y verifient le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: ajout de la case 'Graduation assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbGraduationAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbGraduationAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
