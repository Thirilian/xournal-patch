#!/usr/bin/env python3
"""
Patch 11.10.1 : CORRECTIF DE COMPILATION - erreur signalee par
l'utilisateur avec le log de build exact :

  error: 'void Control::setObjectAlignmentSnapping(bool)' is
  protected within this context

CAUSE : Control::setObjectAlignmentSnapping() est deliberement
protected (regroupee avec setRotationSnapping()/setGridSnapping(),
prevue pour n'etre appelee qu'a travers le mecanisme d'action interne
de Control), rendant l'appel direct depuis SettingsDialog::save()
(introduit par le patch 11.10) invalide.

CORRECTIF : plutot que d'elargir cet encapsulement (changer l'acces de
la methode), le meme effet exact est reproduit depuis SettingsDialog
en utilisant uniquement l'API publique de Control : mise a jour du
parametre ET de l'etat coche du menu "Edition" (une GAction, suivie
separement de la valeur du parametre) - les deux memes etapes que
setObjectAlignmentSnapping() effectue elle-meme en interne.

Modifie : src/core/gui/dialog/SettingsDialog.cpp (2 zones : includes +
logique de save())

NECESSITE : apply_alignment_snap_v11_10.py

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

OLD_1 = """#include \"control/AudioController.h\"             // for AudioController
#include \"control/Control.h\"                     // for Control
#include \"control/settings/Settings.h\"           // for Settings, SElement
#include \"control/settings/SettingsEnums.h\"      // for STYLUS_CURSOR_ARROW
#include \"control/tools/StrokeStabilizerEnum.h\"  // for AveragingMethod, Pre...
#include \"gui/CreatePreviewImage.h\"              // for createPreviewImage
"""
NEW_1 = """#include \"control/AudioController.h\"             // for AudioController
#include \"control/Control.h\"                     // for Control
#include \"control/actions/ActionDatabase.h\"      // for ActionDatabase
#include \"control/settings/Settings.h\"           // for Settings, SElement
#include \"control/settings/SettingsEnums.h\"      // for STYLUS_CURSOR_ARROW
#include \"control/tools/StrokeStabilizerEnum.h\"  // for AveragingMethod, Pre...
#include \"enums/Action.enum.h\"                   // for Action::OBJECT_ALIGNMENT_SNAPPING
#include \"gui/CreatePreviewImage.h\"              // for createPreviewImage
"""
OLD_2 = """    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    // Patch 11.10: goes through Control (not settings directly), so the \"Edit\" menu's own checked
    // state (a GAction, tracked separately from the settings value) stays in sync too - matching
    // exactly what toggling the menu item itself does (see
    // ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING>::callback()).
    this->control->setObjectAlignmentSnapping(getCheckbox(\"cbObjectAlignmentSnapping\"));
    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
"""
NEW_2 = """    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    // Patch 11.10: CORRECTIF DE COMPILATION - Control::setObjectAlignmentSnapping() is deliberately
    // protected (grouped with setRotationSnapping()/setGridSnapping(), only meant to be called
    // through Control's own action-callback mechanism). Rather than widening that encapsulation,
    // this replicates its exact effect using only Control's public API: updates the setting AND the
    // \"Edit\" menu's own checked state (a GAction, tracked separately from the settings value) - the
    // same two steps setObjectAlignmentSnapping() itself performs (see
    // ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING>::callback()).
    {
        bool objectAlignmentSnappingEnabled = getCheckbox(\"cbObjectAlignmentSnapping\");
        settings->setSnapToObjects(objectAlignmentSnappingEnabled);
        this->control->getActionDatabase()->setActionState(Action::OBJECT_ALIGNMENT_SNAPPING,
                                                            objectAlignmentSnappingEnabled);
    }
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
    cpp = Path("src/core/gui/dialog/SettingsDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] SettingsDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "cbObjectAlignmentSnapping" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] cbObjectAlignmentSnapping introuvable dans SettingsDialog.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_10.py, puis relancez ce script.")
        sys.exit(1)
    if "Patch 11.10: CORRECTIF" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.10.1 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "SettingsDialog.cpp: includes")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "SettingsDialog.cpp: logique de save()")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
