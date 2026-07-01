#!/usr/bin/env python3
"""
Applique le patch "follow cursor" sur une source Xournal++ locale,
en cherchant le code par son contenu exact plutôt que par numéro de ligne.
A lancer depuis la racine du dépôt xournalpp (là où se trouve le dossier src/).
"""
import sys
from pathlib import Path

def apply_edit(path: Path, old: str, new: str, label: str):
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        print("        -> le fichier a probablement trop divergé pour ce patch automatique.")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    root = Path(".")
    ok = True

    # --- PageView.h ---
    f = root / "src/core/gui/PageView.h"
    ok &= apply_edit(
        f,
        old="    bool onMotionNotifyEvent(const PositionInputData& pos);\n"
            "    void onSequenceCancelEvent(DeviceId id);\n"
            "    void onTapEvent(const PositionInputData& pos);\n",
        new="    bool onMotionNotifyEvent(const PositionInputData& pos);\n"
            "    void onSequenceCancelEvent(DeviceId id);\n"
            "    void onTapEvent(const PositionInputData& pos);\n\n"
            "    /**\n"
            "     * Makes the currently active EditSelection (see XournalView::getSelection()) follow the\n"
            "     * pointer until the next left click. Intended to be called right after inserting a new\n"
            "     * floating element (e.g. a freshly compiled LaTeX formula) so the user can drop it in\n"
            "     * place without an extra click-and-drag step.\n"
            "     */\n"
            "    void beginFloatingPlacement();\n",
        label="PageView.h: déclaration beginFloatingPlacement()",
    )

    ok &= apply_edit(
        f,
        old="    bool inEraser = false;\n"
            "    bool startEditingOnButtonRelease = false;\n"
            "    bool inLatex = false;\n"
            "    bool inLatexDoubleClick = false;\n",
        new="    bool inEraser = false;\n"
            "    bool startEditingOnButtonRelease = false;\n"
            "    bool inLatex = false;\n"
            "    bool inLatexDoubleClick = false;\n\n"
            "    /**\n"
            "     * If true, the current EditSelection (e.g. a just-inserted LaTeX formula) follows the\n"
            "     * pointer on hover, without needing the button held down. The next left click drops it\n"
            "     * in place. Set via beginFloatingPlacement().\n"
            "     */\n"
            "    bool awaitingFloatingPlacement = false;\n",
        label="PageView.h: membre awaitingFloatingPlacement",
    )

    # --- PageView.cpp ---
    f = root / "src/core/gui/PageView.cpp"
    ok &= apply_edit(
        f,
        old="auto XojPageView::onButtonPressEvent(const PositionInputData& pos) -> bool {",
        new="void XojPageView::beginFloatingPlacement() {\n"
            "    this->awaitingFloatingPlacement = xournal->getSelection() != nullptr;\n"
            "}\n\n"
            "auto XojPageView::onButtonPressEvent(const PositionInputData& pos) -> bool {",
        label="PageView.cpp: implémentation beginFloatingPlacement()",
    )

    ok &= apply_edit(
        f,
        old="    XournalppCursor* cursor = xournal->getCursor();\n"
            "    cursor->setMouseDown(true);\n\n"
            "    if (((h->getToolType() == TOOL_PEN || h->getToolType() == TOOL_HIGHLIGHTER) &&",
        new="    XournalppCursor* cursor = xournal->getCursor();\n"
            "    cursor->setMouseDown(true);\n\n"
            "    if (this->awaitingFloatingPlacement) {\n"
            "        // The click drops the floating element (e.g. a just-inserted LaTeX formula) at its\n"
            "        // current position instead of being interpreted by the currently selected tool.\n"
            "        this->awaitingFloatingPlacement = false;\n"
            "        return true;\n"
            "    }\n\n"
            "    if (((h->getToolType() == TOOL_PEN || h->getToolType() == TOOL_HIGHLIGHTER) &&",
        label="PageView.cpp: interception du clic dans onButtonPressEvent",
    )

    ok &= apply_edit(
        f,
        old="    if (this->inputHandler && this->inputHandler->onMotionNotifyEvent(pos, zoom)) {\n"
            "        // input handler used this event\n"
            "    } else if (this->imageSizeSelection) {",
        new="    if (this->inputHandler && this->inputHandler->onMotionNotifyEvent(pos, zoom)) {\n"
            "        // input handler used this event\n"
            "    } else if (this->awaitingFloatingPlacement) {\n"
            "        if (EditSelection* selection = xournal->getSelection()) {\n"
            "            // Center the selection under the pointer.\n"
            "            double dx = x - selection->getWidth() / 2 - selection->getXOnView();\n"
            "            double dy = y - selection->getHeight() / 2 - selection->getYOnView();\n"
            "            selection->moveSelection(dx, dy);\n"
            "        } else {\n"
            "            // The selection was cleared/deleted some other way; stop tracking it.\n"
            "            this->awaitingFloatingPlacement = false;\n"
            "        }\n"
            "    } else if (this->imageSizeSelection) {",
        label="PageView.cpp: suivi du curseur dans onMotionNotifyEvent",
    )

    # --- LatexController.cpp ---
    f = root / "src/core/control/LatexController.cpp"
    ok &= apply_edit(
        f,
        old="    /* Clearing the old image and creating the new one creates two separate undo actions; I don't\n"
            "       know yet how to merge that to one. (That bug was already present before.) */\n\n"
            "    this->control->clearSelectionEndText();\n"
            "    if (this->selectedElem) {",
        new="    /* Clearing the old image and creating the new one creates two separate undo actions; I don't\n"
            "       know yet how to merge that to one. (That bug was already present before.) */\n\n"
            "    const bool isNewFormula = this->selectedElem == nullptr;\n\n"
            "    this->control->clearSelectionEndText();\n"
            "    if (this->selectedElem) {",
        label="LatexController.cpp: capture isNewFormula",
    )

    ok &= apply_edit(
        f,
        old="    auto selection =\n"
            "            SelectionFactory::createFromFloatingElement(control, page, layer, view, std::move(this->temporaryRender));\n"
            "    view->getXournal()->setSelection(selection.release());\n"
            "}",
        new="    auto selection =\n"
            "            SelectionFactory::createFromFloatingElement(control, page, layer, view, std::move(this->temporaryRender));\n"
            "    view->getXournal()->setSelection(selection.release());\n\n"
            "    if (isNewFormula) {\n"
            "        // Only for newly-created formulas (not when re-editing an existing one): let the user\n"
            "        // drop the formula wherever they want with a single click, instead of it spawning at a\n"
            "        // fixed position that then needs a separate click-and-drag to move.\n"
            "        view->beginFloatingPlacement();\n"
            "    }\n"
            "}",
        label="LatexController.cpp: déclenchement du mode placement",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Aucun fichier partiellement modifié n'a été touché")
        print("au-delà des [OK] listés ci-dessus -> vérifiez le [ECHEC] et éditez ce bloc à la main si besoin.")
        sys.exit(1)


if __name__ == "__main__":
    main()
