#!/usr/bin/env python3
"""
Patch 10.1 : consolide et remplace toute la chaine des patchs 10.1.1 a
10.1.5 (creation de l'onglet, correctifs d'ordonnancement, case "Enable
snapping" + "Circle assist" + leur cablage, correctif du menu Edit,
correctif d'acces protected/public) en un seul patch minimal.

Cette version simplifiee n'affiche pour l'instant, dans l'onglet
"Snapping" (entre "Zone de Dessin" et "Outils"), qu'une seule option a
cocher, "Nameless", a l'interieur d'une boite titree "Functionalities" -
non reliee a une variable. Tout le reste (hierarchisation, cablage
Settings/Control, correctifs de synchronisation) a ete retire : ce sera
reintroduit plus tard, une fois les vraies options definies.

Ne touche PAS a Control.h ni a SettingsDialog.cpp (aucun cablage C++
necessaire pour cette version).

Modifie uniquement ui/settings.glade.

Independant de toute la chaine d'alignement/snapping (8.X/9.X) -
applicable directement sur un depot xournalpp vierge.

NE PAS combiner avec les patchs 10.1.1 a 10.1.5 (retires, remplaces par
celui-ci).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

INSERTION_BLOCK = """                <property name=\"position\">7</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"snapingTabBox\">
                <property name=\"name\">snapingTabBox</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"margin-start\">5</property>
                <property name=\"orientation\">vertical</property>
                <child>
                  <object class=\"GtkScrolledWindow\" id=\"snapingScrolledWindow\">
                    <property name=\"visible\">True</property>
                    <property name=\"can-focus\">True</property>
                    <property name=\"min-content-width\">500</property>
                    <property name=\"min-content-height\">450</property>
                    <property name=\"shadow-type\">in</property>
                    <child>
                      <object class=\"GtkViewport\">
                        <property name=\"visible\">True</property>
                        <property name=\"can-focus\">False</property>
                        <child>
                          <object class=\"GtkBox\" id=\"snapingContentBox\">
                            <property name=\"visible\">True</property>
                            <property name=\"can-focus\">False</property>
                            <property name=\"margin-start\">10</property>
                            <property name=\"margin-end\">10</property>
                            <property name=\"margin-top\">10</property>
                            <property name=\"margin-bottom\">10</property>
                            <property name=\"orientation\">vertical</property>
                            <property name=\"spacing\">10</property>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingFunctionalitiesFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingFunctionalitiesBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbNameless\">
                                        <property name=\"label\" translatable=\"yes\">Nameless</property>
                                        <property name=\"name\">cbNameless</property>
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
                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingFunctionalitiesLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Functionalities</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                  <packing>
                    <property name=\"expand\">True</property>
                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">8</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"snapingTabLabel\">
                <property name=\"name\">snapingTabLabel</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Snapping</property>
              </object>
              <packing>
                <property name=\"position\">8</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"toolsTabBox\">
"""


def apply_edit(text, old, new, label):
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: deja applique.")
            return text, True
        print(f"[ECHEC] {label}: motif introuvable.")
        return text, False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouve {count} fois (doit etre unique).")
        return text, False
    text = text.replace(old, new, 1)
    print(f"[OK]    {label}")
    return text, True


def renumber(text, box_id, label_id, old_pos, new_pos):
    ok = True
    box_marker = f'<object class="GtkBox" id="{box_id}">'
    idx = text.find(box_marker)
    if idx == -1:
        print(f"[ECHEC] id introuvable : {box_id}")
        return text, False
    tab_idx = text.find('<child type="tab">', idx)
    segment = text[idx:tab_idx]
    old_str = f'<property name="position">{old_pos}</property>\n              </packing>'
    new_str = f'<property name="position">{new_pos}</property>\n              </packing>'
    if segment.count(old_str) != 1:
        print(f"[ECHEC] {box_id}: ancre de position introuvable ou ambigue.")
        ok = False
    else:
        text = text[:idx] + segment.replace(old_str, new_str, 1) + text[tab_idx:]
        print(f"[OK]    ui/settings.glade: {box_id} position {old_pos} -> {new_pos}")

    label_marker = f'<object class="GtkLabel" id="{label_id}">'
    idx2 = text.find(label_marker)
    if idx2 == -1:
        print(f"[ECHEC] id introuvable : {label_id}")
        return text, False
    end_idx2 = text.find('</packing>', idx2) + len('</packing>')
    segment2 = text[idx2:end_idx2]
    old_str2 = f'<property name="position">{old_pos}</property>\n                <property name="tab-fill">False</property>'
    new_str2 = f'<property name="position">{new_pos}</property>\n                <property name="tab-fill">False</property>'
    if segment2.count(old_str2) != 1:
        print(f"[ECHEC] {label_id}: ancre de position introuvable ou ambigue.")
        ok = False
    else:
        text = text[:idx2] + segment2.replace(old_str2, new_str2, 1) + text[end_idx2:]
        print(f"[OK]    ui/settings.glade: {label_id} position {old_pos} -> {new_pos}")

    return text, ok


def main():
    glade = Path("ui/settings.glade")
    if not glade.exists():
        print("[ECHEC] ui/settings.glade introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)

    text = glade.read_text(encoding="utf-8")
    if "snapingTabBox" in text:
        print("[SKIP] Le patch 10.1 semble deja applique.")
        sys.exit(0)

    ok = True

    text, ok1 = renumber(text, "toolsTabBox", "toolsTabLabel", 8, 9)
    text, ok2 = renumber(text, "audioRecordingTabBox", "audioRecordingTabLabel", 9, 10)
    text, ok3 = renumber(text, "languageTabBox", "languageTabLabel", 11, 12)
    text, ok4 = renumber(text, "paletteTabBox", "paletteTabLabel", 12, 13)
    ok = ok and ok1 and ok2 and ok3 and ok4

    old_anchor = (
        '                <property name="position">7</property>\n'
        '                <property name="tab-fill">False</property>\n'
        '              </packing>\n'
        '            </child>\n'
        '            <child>\n'
        '              <object class="GtkBox" id="toolsTabBox">\n'
    )
    text, ok5 = apply_edit(text, old_anchor, INSERTION_BLOCK, "ui/settings.glade: insertion de l\'onglet Snapping")
    ok = ok and ok5

    glade.write_text(text, encoding="utf-8")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
