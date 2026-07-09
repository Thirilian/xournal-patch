#!/usr/bin/env python3
"""
force_line_style_updatev2.py : version consolidee, fusionnant les
patchs #11 et #11.1 en un seul script.

Force la mise a jour du style de trait de l'objet SELECTIONNE quand
l'utilisateur clique, dans le menu deroulant de l'outil stylo, sur le
style DEJA actif (ce qui, sans ce patch, ne declenche rien du tout -
GTK n'emet jamais le signal "change-state" quand la valeur cible est
deja l'etat courant de l'action).

Point important : ne touche JAMAIS le style de trait propre a l'outil
stylo lui-meme (celui utilise pour un futur nouveau trace) - seul
l'objet selectionne est affecte, via une nouvelle methode dediee
Control::forceLineStyleOnSelection(), separee de la Control::setLineStyle()
existante (qui, elle, met toujours aussi a jour l'etat de l'outil).

Modifie :
  - src/core/gui/toolbarMenubar/StylePopoverFactory.h (nouveau membre
    onForceClick)
  - src/core/gui/toolbarMenubar/StylePopoverFactory.cpp (invocation du
    callback a chaque clic)
  - src/core/gui/toolbarMenubar/ToolMenuHandler.cpp (cablage pour le
    style de trait uniquement, appelle forceLineStyleOnSelection)
  - src/core/control/Control.h (nouvelle declaration)
  - src/core/control/Control.cpp (nouvelle implementation, n'affecte
    jamais l'outil, seulement la selection)

Independant de la serie de patchs alignment_snap - peut etre applique
avant, apres, ou entre deux patchs de cette serie sans dependance.

A lancer depuis la racine du depot xournalpp (sur un depot vierge, ou
tout du moins sans qu'aucune version anterieure de ce patch - #11 ou
#11.1 - n'ait deja ete appliquee).
"""
import sys
from pathlib import Path

OLD_H1 = """#include <string>  // for string, allocator
#include <vector>
"""
NEW_H1 = """#include <functional>  // for function
#include <string>      // for string, allocator
#include <vector>
"""
OLD_H2 = """    GtkWidget* createPopover() const override;

private:
"""
NEW_H2 = """    GtkWidget* createPopover() const override;

    /// Patch #11: called on every click on an entry, in addition to the normal action/change-state
    /// mechanism - even when the clicked entry is already the active one (in which case GTK's own
    /// change-state signal never fires at all, so nothing else would otherwise happen). Left empty
    /// (the default) for popovers that don't need this - see ToolMenuHandler.cpp for the line style
    /// popover, the only current user.
    std::function<void(GVariant*)> onForceClick;

private:
"""
OLD_C1 = """    GtkWidget* box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_popover_set_child(GTK_POPOVER(popover), box);

#if GTK_MAJOR_VERSION == 3
"""
NEW_C1 = """    GtkWidget* box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
    gtk_popover_set_child(GTK_POPOVER(popover), box);

    // Patch #11: stash `this` on the popover itself, so the \"clicked\" handler below (a plain function
    // pointer, no captures) can reach onForceClick without needing its own heap-allocated context.
    g_object_set_data(G_OBJECT(popover), \"xoj-style-popover-factory\", const_cast<StylePopoverFactory*>(this));

#if GTK_MAJOR_VERSION == 3
"""
OLD_C2 = """        g_signal_connect_object(btn, \"clicked\", G_CALLBACK(+[](GtkButton*, gpointer popover) {
                                    gtk_popover_popdown(GTK_POPOVER(popover));
                                }),
                                popover, GConnectFlags(0));
"""
NEW_C2 = """        g_signal_connect_object(btn, \"clicked\", G_CALLBACK(+[](GtkButton* btn, gpointer popover) {
                                    gtk_popover_popdown(GTK_POPOVER(popover));
                                    // Patch #11: GTK's own change-state signal (which normally drives
                                    // the action's callback, see ActionDatabase.cpp) never fires when
                                    // the clicked entry is already the active one - nothing else would
                                    // otherwise happen in that case. onForceClick, if set, makes sure
                                    // the underlying state gets applied regardless.
                                    auto* factory = static_cast<const StylePopoverFactory*>(g_object_get_data(
                                            G_OBJECT(popover), \"xoj-style-popover-factory\"));
                                    if (factory != nullptr && factory->onForceClick) {
                                        factory->onForceClick(
                                                gtk_actionable_get_action_target_value(GTK_ACTIONABLE(btn)));
                                    }
                                }),
                                popover, GConnectFlags(0));
"""
OLD_T1 = """                                                    {_(\"dotted\"), iconName(\"line-style-dot\"), \"dot\"}});
    emplaceCustomItemWithTargetAndMenu(\"PEN\", Cat::TOOLS, Action::SELECT_TOOL, TOOL_PEN, \"tool-pencil\", _(\"Pen\"),
"""
NEW_T1 = """                                                    {_(\"dotted\"), iconName(\"line-style-dot\"), \"dot\"}});
    // Patch #11: clicking a line style entry that is already the selected object's current style
    // doesn't otherwise do anything - see StylePopoverFactory::onForceClick's own comment for why.
    this->penLineStylePopover->onForceClick = [ctrl = this->control](GVariant* target) {
        if (target == nullptr) {
            return;
        }
        auto action = ctrl->getActionDatabase()->getAction(Action::TOOL_PEN_LINE_STYLE);
        if (!action) {
            return;
        }
        xoj::util::GVariantSPtr currentState(g_action_get_state(G_ACTION(action.get())), xoj::util::adopt);
        if (currentState && g_variant_equal(currentState.get(), target)) {
            // Patch #11: forceLineStyleOnSelection(), not setLineStyle() - re-clicking an already
            // active style must only ever affect the selected object, never the pen tool's own style
            // for future new strokes.
            ctrl->forceLineStyleOnSelection(g_variant_get_string(target, nullptr));
        }
    };
    emplaceCustomItemWithTargetAndMenu(\"PEN\", Cat::TOOLS, Action::SELECT_TOOL, TOOL_PEN, \"tool-pencil\", _(\"Pen\"),
"""
OLD_CH1 = """    void setLineStyle(const std::string& style);
"""
NEW_CH1 = """    void setLineStyle(const std::string& style);

    /// Patch #11: see the .cpp file for the full explanation - unlike setLineStyle() above, never
    /// touches the pen tool's own line style, only the currently selected object (if any).
    void forceLineStyleOnSelection(const std::string& style);
"""
OLD_CC1 = """    this->toolHandler->setLineStyle(stl);
}

void Control::setEraserType(EraserType type) {
"""
NEW_CC1 = """    this->toolHandler->setLineStyle(stl);
}

// Patch #11: unlike setLineStyle() above, this NEVER touches the pen tool's own line style (i.e.
// what a brand new stroke would use going forward) - it only forces the currently selected object's
// style, and does nothing at all if nothing is selected. Used when the user re-clicks a line style
// that is already the active one in the menu (see ToolMenuHandler.cpp), where only the selected
// object - never the tool itself - should be affected.
void Control::forceLineStyleOnSelection(const string& style) {
    if (this->win == nullptr) {
        return;
    }
    EditSelection* selection = this->win->getXournal()->getSelection();
    if (selection == nullptr) {
        return;
    }
    LineStyle stl = StrokeStyle::parseStyle(style);
    undoRedo->addUndoAction(selection->setLineStyle(stl));
}

void Control::setEraserType(EraserType type) {
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
    h_file = Path("src/core/gui/toolbarMenubar/StylePopoverFactory.h")
    cpp_file = Path("src/core/gui/toolbarMenubar/StylePopoverFactory.cpp")
    tmh_file = Path("src/core/gui/toolbarMenubar/ToolMenuHandler.cpp")
    ch_file = Path("src/core/control/Control.h")
    ccpp_file = Path("src/core/control/Control.cpp")
    for p in (h_file, cpp_file, tmh_file, ch_file, ccpp_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "onForceClick" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Ce patch (force_line_style_updatev2) semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, OLD_H1, NEW_H1, "StylePopoverFactory.h: include <functional>")
    ok &= apply_edit(h_file, OLD_H2, NEW_H2, "StylePopoverFactory.h: membre onForceClick")
    ok &= apply_edit(cpp_file, OLD_C1, NEW_C1, "StylePopoverFactory.cpp: stockage de this sur le popover")
    ok &= apply_edit(cpp_file, OLD_C2, NEW_C2, "StylePopoverFactory.cpp: invocation d'onForceClick au clic")
    ok &= apply_edit(tmh_file, OLD_T1, NEW_T1, "ToolMenuHandler.cpp: cablage pour le style de trait")
    ok &= apply_edit(ch_file, OLD_CH1, NEW_CH1, "Control.h: declaration de forceLineStyleOnSelection")
    ok &= apply_edit(ccpp_file, OLD_CC1, NEW_CC1, "Control.cpp: implementation de forceLineStyleOnSelection")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
