#!/usr/bin/env python3
"""
Patch 10.2 (phase 10) : premiere fonctionnalite reellement cablee de
l'onglet Snapping.

Renomme la case "Nameless" (patch 10.1) en "Equidistant assist", et la
relie a un nouveau reglage Settings::equidistantSnappingEnabled (meme
pattern que Settings::snapToObjects - persistant, getter/setter). Cette
case controle desormais specifiquement le palier equidistant ("equal
spacing", patch 8.1.0) : si decochee, ce palier precis ne se declenche
plus, MEME SI "Object Alignment Snapping" (menu Edit) reste active - les
autres paliers (ordinaire, boosted, page-centre, table-centre, grille
bleue) continuent de fonctionner normalement. C'est un reglage plus fin,
imbrique sous le reglage maitre, pas un remplacement.

Modifie :
  - src/core/control/settings/Settings.h (declaration)
  - src/core/control/settings/Settings.cpp (valeur par defaut, XML
    charge/sauvegarde, implementation)
  - src/core/control/tools/EditSelection.cpp (les deux points d'appel de
    findEquidistantX/Y verifient desormais aussi ce reglage)
  - ui/settings.glade (renommage de la case)
  - src/core/gui/dialog/SettingsDialog.cpp (chargement/sauvegarde de la
    case)

NECESSITE : apply_alignment_snap_v10_1.py + apply_alignment_snap_v8_1_0.py
(pour findEquidistantX/Y)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_H1 = """    bool isSnapToObjects() const;
    void setSnapToObjects(bool b);

"""
NEW_H1 = """    bool isSnapToObjects() const;
    void setSnapToObjects(bool b);

    /// Patch 10.2: gates specifically the equidistant (\"equal spacing\") tier of the object alignment
    /// snapping system (see findEquidistantX/Y() in EditSelection.cpp), independently of the other
    /// tiers (ordinary, boosted, page-center, table-center, blue grid...). Only takes effect while
    /// isSnapToObjects() is also true - this is a finer-grained toggle nested under the master one,
    /// not a replacement for it.
    bool isEquidistantSnappingEnabled() const;
    void setEquidistantSnappingEnabled(bool b);

"""
OLD_H2 = """    /**
     * object alignment (\"smart guides\") snapping enabled by default
     */
    bool snapToObjects{};

    /**
"""
NEW_H2 = """    /**
     * object alignment (\"smart guides\") snapping enabled by default
     */
    bool snapToObjects{};

    /**
     * Patch 10.2: whether the equidistant (\"equal spacing\") tier of the object alignment snapping
     * system is enabled. Nested under snapToObjects - see isEquidistantSnappingEnabled() above.
     */
    bool equidistantSnappingEnabled{};

    /**
"""
OLD_C1 = """    this->snapToObjects = true;
"""
NEW_C1 = """    this->snapToObjects = true;
    this->equidistantSnappingEnabled = true;
"""
OLD_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapToObjects\")) == 0) {
        this->snapToObjects = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
NEW_C2 = """    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapToObjects\")) == 0) {
        this->snapToObjects = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"equidistantSnappingEnabled\")) == 0) {
        this->equidistantSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
"""
OLD_C3 = """    SAVE_BOOL_PROP(snapToObjects);
"""
NEW_C3 = """    SAVE_BOOL_PROP(snapToObjects);
    SAVE_BOOL_PROP(equidistantSnappingEnabled);
"""
OLD_C4 = """void Settings::setSnapToObjects(bool b) {
    if (this->snapToObjects == b) {
        return;
    }

    this->snapToObjects = b;
    save();
}
"""
NEW_C4 = """void Settings::setSnapToObjects(bool b) {
    if (this->snapToObjects == b) {
        return;
    }

    this->snapToObjects = b;
    save();
}

auto Settings::isEquidistantSnappingEnabled() const -> bool { return this->equidistantSnappingEnabled; }

void Settings::setEquidistantSnappingEnabled(bool b) {
    if (this->equidistantSnappingEnabled == b) {
        return;
    }

    this->equidistantSnappingEnabled = b;
    save();
}
"""
OLD_EDIT = """                if (!matchXIsBoosted) {
                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchX || std::abs(equidistantX->offset) < std::abs(matchX->offset)) {
                            matchX = AlignmentSearchResult{equidistantX->offset, {*equidistantX}};
                        }
                    }
                }
                if (!matchYIsBoosted) {
                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchY || std::abs(equidistantY->offset) < std::abs(matchY->offset)) {
                            matchY = AlignmentSearchResult{equidistantY->offset, {*equidistantY}};
                        }
                    }
                }
"""
NEW_EDIT = """                if (!matchXIsBoosted && settings->isEquidistantSnappingEnabled()) {
                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchX || std::abs(equidistantX->offset) < std::abs(matchX->offset)) {
                            matchX = AlignmentSearchResult{equidistantX->offset, {*equidistantX}};
                        }
                    }
                }
                if (!matchYIsBoosted && settings->isEquidistantSnappingEnabled()) {
                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,
                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {
                        if (!matchY || std::abs(equidistantY->offset) < std::abs(matchY->offset)) {
                            matchY = AlignmentSearchResult{equidistantY->offset, {*equidistantY}};
                        }
                    }
                }
"""
OLD_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbNameless\">
                                        <property name=\"label\" translatable=\"yes\">Nameless</property>
                                        <property name=\"name\">cbNameless</property>
"""
NEW_GL = """                                      <object class=\"GtkCheckButton\" id=\"cbEquidistantAssist\">
                                        <property name=\"label\" translatable=\"yes\">Equidistant assist</property>
                                        <property name=\"name\">cbEquidistantAssist</property>
"""
OLD_LOAD = """    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
"""
NEW_LOAD = """    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
"""
OLD_SAVE = """    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
"""
NEW_SAVE = """    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
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

    if "cbNameless" not in glade.read_text(encoding="utf-8") and "cbEquidistantAssist" not in glade.read_text(encoding="utf-8"):
        print("[ECHEC] La case du patch 10.1 (cbNameless) est introuvable dans ui/settings.glade.")
        print("        Appliquez d'abord apply_alignment_snap_v10_1.py, puis relancez ce script.")
        sys.exit(1)
    if "findEquidistantX" not in edit_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] findEquidistantX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_1_0.py, puis relancez ce script.")
        sys.exit(1)
    if "equidistantSnappingEnabled" in settings_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 10.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(settings_h, OLD_H1, NEW_H1, "Settings.h: declaration isEquidistantSnappingEnabled/setEquidistantSnappingEnabled")
    ok &= apply_edit(settings_h, OLD_H2, NEW_H2, "Settings.h: membre equidistantSnappingEnabled")
    ok &= apply_edit(settings_cpp, OLD_C1, NEW_C1, "Settings.cpp: valeur par defaut")
    ok &= apply_edit(settings_cpp, OLD_C2, NEW_C2, "Settings.cpp: chargement XML")
    ok &= apply_edit(settings_cpp, OLD_C3, NEW_C3, "Settings.cpp: sauvegarde XML")
    ok &= apply_edit(settings_cpp, OLD_C4, NEW_C4, "Settings.cpp: implementation getter/setter")
    ok &= apply_edit(edit_cpp, OLD_EDIT, NEW_EDIT, "EditSelection.cpp: le palier equidistant verifie le nouveau reglage")
    ok &= apply_edit(glade, OLD_GL, NEW_GL, "ui/settings.glade: renommage en 'Equidistant assist'")
    ok &= apply_edit(dialog_cpp, OLD_LOAD, NEW_LOAD, "SettingsDialog.cpp: chargement de cbEquidistantAssist")
    ok &= apply_edit(dialog_cpp, OLD_SAVE, NEW_SAVE, "SettingsDialog.cpp: sauvegarde de cbEquidistantAssist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
