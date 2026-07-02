#!/usr/bin/env python3
"""
Version 2 : corrige le bug d'epaisseur 0 (repere invisible) quand l'outil actif
n'a pas d'epaisseur definie (selection, texte, formes, main...), et met a jour
les tailles : graduations = longueur totale 6, croix = envergure totale 3.

Remplace apply_floating_marks.py (ne pas appliquer les deux a la suite).

NECESSITE apply_paste_follow_cursor_v2.py deja applique.
A lancer depuis la racine du depot xournalpp, sur une copie non modifiee.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    control_cpp = Path("src/core/control/Control.cpp")
    if not control_cpp.exists():
        print("[ECHEC] src/core/control/Control.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    if "getPageViewAndPosUnderCursor" not in control_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] getPageViewAndPosUnderCursor introuvable dans Control.cpp.")
        print("        Appliquez d'abord apply_paste_follow_cursor_v2.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    # --- Action.enum.h : 3 nouvelles valeurs avant le sentinel ---
    f = Path("src/core/enums/Action.enum.h")
    ok &= apply_edit(
        f,
        old='    // Miscellaneous\n'
            '    POSITION_HIGHLIGHTING,\n\n'
            '    // Keep this last value\n'
            '    ENUMERATOR_COUNT\n'
            '};\n',
        new='    // Miscellaneous\n'
            '    POSITION_HIGHLIGHTING,\n\n'
            '    // Floating marks (cross / tick marks), spawn attached to the cursor until the next left click\n'
            '    INSERT_CROSS,\n'
            '    INSERT_TICK_HORIZONTAL,\n'
            '    INSERT_TICK_VERTICAL,\n\n'
            '    // Keep this last value\n'
            '    ENUMERATOR_COUNT\n'
            '};\n',
        label="Action.enum.h: nouvelles valeurs INSERT_CROSS / INSERT_TICK_*",
    )

    # --- Action.NameMap.generated.h : noms correspondants, meme ordre ---
    f = Path("src/core/enums/generated/Action.NameMap.generated.h")
    ok &= apply_edit(
        f,
        old='        "layer-active",\n'
            '        "position-highlighting"};\n',
        new='        "layer-active",\n'
            '        "position-highlighting",\n'
            '        "insert-cross",\n'
            '        "insert-tick-horizontal",\n'
            '        "insert-tick-vertical"};\n',
        label="Action.NameMap.generated.h: noms insert-cross / insert-tick-*",
    )

    # --- ActionProperties.h : accelerateurs + callbacks ---
    f = Path("src/core/control/actions/ActionProperties.h")
    ok &= apply_edit(
        f,
        old='template <>\n'
            'struct ActionProperties<Action::PASTE> {\n'
            '#ifdef __APPLE__\n'
            '    static constexpr const char* accelerators[] = {"<Meta>V", "Paste", nullptr};\n'
            '#else\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl>V", "Paste", nullptr};\n'
            '#endif\n'
            '    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->paste(); }\n'
            '};\n',
        new='template <>\n'
            'struct ActionProperties<Action::PASTE> {\n'
            '#ifdef __APPLE__\n'
            '    static constexpr const char* accelerators[] = {"<Meta>V", "Paste", nullptr};\n'
            '#else\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl>V", "Paste", nullptr};\n'
            '#endif\n'
            '    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->paste(); }\n'
            '};\n'
            'template <>\n'
            'struct ActionProperties<Action::INSERT_CROSS> {\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl>K", nullptr};\n'
            '    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertCross(); }\n'
            '};\n'
            'template <>\n'
            'struct ActionProperties<Action::INSERT_TICK_HORIZONTAL> {\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl>J", nullptr};\n'
            '    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertTickHorizontal(); }\n'
            '};\n'
            'template <>\n'
            'struct ActionProperties<Action::INSERT_TICK_VERTICAL> {\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl><Shift>J", nullptr};\n'
            '    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertTickVertical(); }\n'
            '};\n',
        label="ActionProperties.h: specialisations INSERT_CROSS / INSERT_TICK_*",
    )

    # --- Control.h : declarations ---
    f = Path("src/core/control/Control.h")
    ok &= apply_edit(
        f,
        old='    bool copy();\n'
            '    bool cut();\n'
            '    bool paste();\n\n'
            '    void help();',
        new='    bool copy();\n'
            '    bool cut();\n'
            '    bool paste();\n\n'
            '    /**\n'
            '     * Insert a small cross mark (same shape/size as GeometryToolController::markOrigin()), attached\n'
            '     * to the mouse pointer until the next left click. Uses the currently selected tool\'s color and\n'
            '     * thickness.\n'
            '     */\n'
            '    void insertCross();\n\n'
            '    /**\n'
            '     * Insert a short horizontal tick mark, attached to the mouse pointer until the next left click.\n'
            '     * Uses the currently selected tool\'s color and thickness.\n'
            '     */\n'
            '    void insertTickHorizontal();\n\n'
            '    /**\n'
            '     * Insert a short vertical tick mark, attached to the mouse pointer until the next left click.\n'
            '     * Uses the currently selected tool\'s color and thickness.\n'
            '     */\n'
            '    void insertTickVertical();\n\n'
            '    void help();',
        label="Control.h: déclarations insertCross / insertTick*",
    )

    # --- Control.cpp : implementation ---
    f = control_cpp
    ok &= apply_edit(
        f,
        old='static void beginFloatingPlacement(EditSelection* selection) {\n'
            '    double zoom = selection->getView()->getXournal()->getZoom();\n'
            '    double grabX = zoom * (selection->getXOnView() + selection->getWidth() / 2);\n'
            '    double grabY = zoom * (selection->getYOnView() + selection->getHeight() / 2);\n'
            '    selection->mouseDown(CURSOR_SELECTION_MOVE, grabX, grabY);\n'
            '}\n\n'
            'void Control::clipboardPaste(ElementPtr e) {',
        new='static void beginFloatingPlacement(EditSelection* selection) {\n'
            '    double zoom = selection->getView()->getXournal()->getZoom();\n'
            '    double grabX = zoom * (selection->getXOnView() + selection->getWidth() / 2);\n'
            '    double grabY = zoom * (selection->getYOnView() + selection->getHeight() / 2);\n'
            '    selection->mouseDown(CURSOR_SELECTION_MOVE, grabX, grabY);\n'
            '}\n\n'
            '/**\n'
            ' * Half-extent (in document points) of the cross mark, i.e. the diagonal reaches this far from the\n'
            ' * center in each direction. Total visual span of the cross is 2 * CROSS_MARK_SIZE.\n'
            ' */\n'
            'constexpr double CROSS_MARK_SIZE = 2.5;\n\n'
            '/**\n'
            ' * Half-length (in document points) of the tick marks. Total length of a tick is 2 * TICK_MARK_SIZE.\n'
            ' */\n'
            'constexpr double TICK_MARK_SIZE = 3.;\n\n'
            '/**\n'
            ' * Creates a small Stroke (a cross or a tick mark, depending on localOffsets) using the currently\n'
            ' * selected tool\'s color and thickness, spawns it under the mouse pointer (or at the center of the\n'
            ' * visible area if the pointer isn\'t over any page), and attaches it to the pointer until the next\n'
            ' * left click - same mechanism as clipboardPaste()/clipboardPasteXournal() above.\n'
            ' * localOffsets are pairs of (dx, dy), in document points, relative to the spawn point.\n'
            ' */\n'
            'static void createFloatingMark(Control* ctrl, XournalView* xournal,\n'
            '                                const std::vector<std::pair<double, double>>& localOffsets) {\n'
            '    double x = 0;\n'
            '    double y = 0;\n'
            '    XojPageView* view = getPageViewAndPosUnderCursor(xournal, x, y);\n'
            '    if (!view) {\n'
            '        auto pageNr = ctrl->getCurrentPageNo();\n'
            '        if (pageNr == npos) {\n'
            '            return;\n'
            '        }\n'
            '        view = xournal->getViewFor(pageNr);\n'
            '        if (!view) {\n'
            '            return;\n'
            '        }\n'
            '        xournal->getPasteTarget(x, y);\n'
            '    }\n\n'
            '    ToolHandler* toolHandler = ctrl->getToolHandler();\n'
            '    auto stroke = std::make_unique<Stroke>();\n'
            '    if (toolHandler->isDrawingTool()) {\n'
            '        stroke->setWidth(toolHandler->getThickness());\n'
            '        stroke->setColor(toolHandler->getColor());\n'
            '    } else {\n'
            '        // The active tool has no thickness of its own (e.g. a selection tool, the hand tool...),\n'
            '        // which would otherwise produce an invisible 0-width stroke. Fall back to the pen\'s\n'
            '        // settings, same as GeometryToolController::markOrigin() does.\n'
            '        stroke->setWidth(toolHandler->getToolThickness(TOOL_PEN)[TOOL_SIZE_FINE]);\n'
            '        stroke->setColor(toolHandler->getTool(TOOL_PEN).getColor());\n'
            '    }\n'
            '    for (auto&& [dx, dy]: localOffsets) {\n'
            '        stroke->addPoint(Point(x + dx, y + dy));\n'
            '    }\n\n'
            '    Document* doc = ctrl->getDocument();\n'
            '    doc->lock_shared();\n'
            '    PageRef page = view->getPage();\n'
            '    Layer* layer = page->getSelectedLayer();\n'
            '    doc->unlock_shared();\n\n'
            '    UndoRedoHandler* undoRedo = ctrl->getUndoRedoHandler();\n'
            '    Stroke* rawStroke = stroke.get();\n'
            '    undoRedo->addUndoAction(std::make_unique<InsertUndoAction>(page, layer, rawStroke));\n'
            '    auto sel = SelectionFactory::createFromFloatingElement(ctrl, page, layer, view, std::move(stroke));\n\n'
            '    EditSelection* selection = sel.release();\n'
            '    xournal->setSelection(selection);\n'
            '    beginFloatingPlacement(selection);\n'
            '}\n\n'
            'void Control::insertCross() {\n'
            '    createFloatingMark(this, win->getXournal(),\n'
            '                        {{CROSS_MARK_SIZE, CROSS_MARK_SIZE},\n'
            '                         {-CROSS_MARK_SIZE, -CROSS_MARK_SIZE},\n'
            '                         {0, 0},\n'
            '                         {CROSS_MARK_SIZE, -CROSS_MARK_SIZE},\n'
            '                         {-CROSS_MARK_SIZE, CROSS_MARK_SIZE}});\n'
            '}\n\n'
            'void Control::insertTickHorizontal() {\n'
            '    createFloatingMark(this, win->getXournal(), {{-TICK_MARK_SIZE, 0}, {TICK_MARK_SIZE, 0}});\n'
            '}\n\n'
            'void Control::insertTickVertical() {\n'
            '    createFloatingMark(this, win->getXournal(), {{0, -TICK_MARK_SIZE}, {0, TICK_MARK_SIZE}});\n'
            '}\n\n'
            'void Control::clipboardPaste(ElementPtr e) {',
        label="Control.cpp: createFloatingMark (avec fallback epaisseur) + insertCross/insertTickHorizontal/insertTickVertical",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
