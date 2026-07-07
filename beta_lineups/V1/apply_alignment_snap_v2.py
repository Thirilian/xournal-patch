#!/usr/bin/env python3
"""
Sous-patch 2/2 du systeme d'ancrage entre objets (style Canva/Figma).
Ajoute :
  - Une ligne de guidage ROSE, bornee (elle relie exactement les deux objets
    alignes, ne traverse pas toute la page), dessinee pendant le glissement.
  - Un bouton bascule "Object Alignment Snapping" (menu Edit, a cote de
    "Grid Snapping"), qui active/desactive toute la fonctionnalite. Reglage
    persiste, active par defaut.

NECESSITE apply_alignment_snap_v1.py deja applique.
A lancer depuis la racine du depot xournalpp.
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
    editsel_cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not editsel_cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    if "findAlignmentOffsetX" not in editsel_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] findAlignmentOffsetX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    # ============ Settings.h ============
    f = Path("src/core/control/settings/Settings.h")
    ok &= apply_edit(
        f,
        old='    bool isSnapGrid() const;\n'
            '    void setSnapGrid(bool b);\n'
            '    double getSnapGridTolerance() const;\n'
            '    void setSnapGridTolerance(double tolerance);\n'
            '    double getSnapGridSize() const;\n'
            '    void setSnapGridSize(double gridSize);\n\n',
        new='    bool isSnapGrid() const;\n'
            '    void setSnapGrid(bool b);\n'
            '    double getSnapGridTolerance() const;\n'
            '    void setSnapGridTolerance(double tolerance);\n'
            '    double getSnapGridSize() const;\n'
            '    void setSnapGridSize(double gridSize);\n\n'
            '    bool isSnapToObjects() const;\n'
            '    void setSnapToObjects(bool b);\n\n',
        label="Settings.h: déclarations isSnapToObjects/setSnapToObjects",
    )
    ok &= apply_edit(
        f,
        old='    /**\n'
            '     * grid snapping enabled by default\n'
            '     */\n'
            '    bool snapGrid{};',
        new='    /**\n'
            '     * grid snapping enabled by default\n'
            '     */\n'
            '    bool snapGrid{};\n\n'
            '    /**\n'
            '     * object alignment ("smart guides") snapping enabled by default\n'
            '     */\n'
            '    bool snapToObjects{};',
        label="Settings.h: membre snapToObjects",
    )

    # ============ Settings.cpp ============
    f = Path("src/core/control/settings/Settings.cpp")
    ok &= apply_edit(
        f,
        old='    this->snapGrid = true;\n'
            '    this->snapGridTolerance = 0.50;\n'
            '    this->snapGridSize = DEFAULT_GRID_SIZE;\n',
        new='    this->snapGrid = true;\n'
            '    this->snapGridTolerance = 0.50;\n'
            '    this->snapGridSize = DEFAULT_GRID_SIZE;\n'
            '    this->snapToObjects = true;\n',
        label="Settings.cpp: valeur par défaut snapToObjects",
    )
    ok &= apply_edit(
        f,
        old='    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>("snapGrid")) == 0) {\n'
            '        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>("true")) == 0;\n',
        new='    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>("snapGrid")) == 0) {\n'
            '        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>("true")) == 0;\n'
            '    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>("snapToObjects")) == 0) {\n'
            '        this->snapToObjects = xmlStrcmp(value, reinterpret_cast<const xmlChar*>("true")) == 0;\n',
        label="Settings.cpp: chargement XML snapToObjects",
    )
    ok &= apply_edit(
        f,
        old='    SAVE_BOOL_PROP(snapGrid);\n'
            '    SAVE_DOUBLE_PROP(snapGridTolerance);\n'
            '    SAVE_DOUBLE_PROP(snapGridSize);\n',
        new='    SAVE_BOOL_PROP(snapGrid);\n'
            '    SAVE_DOUBLE_PROP(snapGridTolerance);\n'
            '    SAVE_DOUBLE_PROP(snapGridSize);\n'
            '    SAVE_BOOL_PROP(snapToObjects);\n',
        label="Settings.cpp: sauvegarde XML snapToObjects",
    )
    ok &= apply_edit(
        f,
        old='auto Settings::isSnapGrid() const -> bool { return this->snapGrid; }\n\n'
            'void Settings::setSnapGrid(bool b) {\n'
            '    if (this->snapGrid == b) {\n'
            '        return;\n'
            '    }\n\n'
            '    this->snapGrid = b;\n'
            '    save();\n'
            '}\n',
        new='auto Settings::isSnapGrid() const -> bool { return this->snapGrid; }\n\n'
            'void Settings::setSnapGrid(bool b) {\n'
            '    if (this->snapGrid == b) {\n'
            '        return;\n'
            '    }\n\n'
            '    this->snapGrid = b;\n'
            '    save();\n'
            '}\n\n'
            'auto Settings::isSnapToObjects() const -> bool { return this->snapToObjects; }\n\n'
            'void Settings::setSnapToObjects(bool b) {\n'
            '    if (this->snapToObjects == b) {\n'
            '        return;\n'
            '    }\n\n'
            '    this->snapToObjects = b;\n'
            '    save();\n'
            '}\n',
        label="Settings.cpp: getter/setter isSnapToObjects/setSnapToObjects",
    )

    # ============ Action.enum.h ============
    f = Path("src/core/enums/Action.enum.h")
    ok &= apply_edit(
        f,
        old='    ROTATION_SNAPPING,\n'
            '    GRID_SNAPPING,\n',
        new='    ROTATION_SNAPPING,\n'
            '    GRID_SNAPPING,\n'
            '    OBJECT_ALIGNMENT_SNAPPING,\n',
        label="Action.enum.h: OBJECT_ALIGNMENT_SNAPPING",
    )

    # ============ Action.NameMap.generated.h ============
    f = Path("src/core/enums/generated/Action.NameMap.generated.h")
    ok &= apply_edit(
        f,
        old='        "rotation-snapping",\n'
            '        "grid-snapping",\n',
        new='        "rotation-snapping",\n'
            '        "grid-snapping",\n'
            '        "object-alignment-snapping",\n',
        label="Action.NameMap.generated.h: object-alignment-snapping",
    )

    # ============ ActionProperties.h ============
    f = Path("src/core/control/actions/ActionProperties.h")
    ok &= apply_edit(
        f,
        old='template <>\n'
            'struct ActionProperties<Action::GRID_SNAPPING> {\n'
            '    using state_type = bool;\n'
            '    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapGrid(); }\n'
            '    static void callback(GSimpleAction* ga, GVariant* p, Control* ctrl) {\n'
            '        g_simple_action_set_state(ga, p);\n'
            '        bool enable = g_variant_get_boolean(p);\n'
            '        ctrl->setGridSnapping(enable);\n'
            '    }\n'
            '};\n',
        new='template <>\n'
            'struct ActionProperties<Action::GRID_SNAPPING> {\n'
            '    using state_type = bool;\n'
            '    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapGrid(); }\n'
            '    static void callback(GSimpleAction* ga, GVariant* p, Control* ctrl) {\n'
            '        g_simple_action_set_state(ga, p);\n'
            '        bool enable = g_variant_get_boolean(p);\n'
            '        ctrl->setGridSnapping(enable);\n'
            '    }\n'
            '};\n\n'
            'template <>\n'
            'struct ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING> {\n'
            '    using state_type = bool;\n'
            '    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapToObjects(); }\n'
            '    static void callback(GSimpleAction* ga, GVariant* p, Control* ctrl) {\n'
            '        g_simple_action_set_state(ga, p);\n'
            '        bool enable = g_variant_get_boolean(p);\n'
            '        ctrl->setObjectAlignmentSnapping(enable);\n'
            '    }\n'
            '};\n',
        label="ActionProperties.h: spécialisation OBJECT_ALIGNMENT_SNAPPING",
    )

    # ============ Control.h ============
    f = Path("src/core/control/Control.h")
    ok &= apply_edit(
        f,
        old='    void setGridSnapping(bool enable);\n',
        new='    void setGridSnapping(bool enable);\n'
            '    void setObjectAlignmentSnapping(bool enable);\n',
        label="Control.h: déclaration setObjectAlignmentSnapping",
    )

    # ============ Control.cpp ============
    f = Path("src/core/control/Control.cpp")
    ok &= apply_edit(
        f,
        old='void Control::setGridSnapping(bool enable) {\n'
            '    settings->setSnapGrid(enable);\n'
            '    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);\n'
            '}\n',
        new='void Control::setGridSnapping(bool enable) {\n'
            '    settings->setSnapGrid(enable);\n'
            '    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);\n'
            '}\n\n'
            'void Control::setObjectAlignmentSnapping(bool enable) {\n'
            '    settings->setSnapToObjects(enable);\n'
            '    this->actionDB->setActionState(Action::OBJECT_ALIGNMENT_SNAPPING, enable);\n'
            '}\n',
        label="Control.cpp: implémentation setObjectAlignmentSnapping",
    )

    # ============ ui/mainmenubar.xml ============
    f = Path("ui/mainmenubar.xml")
    ok &= apply_edit(
        f,
        old='    <item>\n'
            '     <attribute name="label" translatable="yes">Grid Snapping</attribute>\n'
            '     <attribute name="action">win.grid-snapping</attribute>\n'
            '    </item>\n'
            '   </section>',
        new='    <item>\n'
            '     <attribute name="label" translatable="yes">Grid Snapping</attribute>\n'
            '     <attribute name="action">win.grid-snapping</attribute>\n'
            '    </item>\n'
            '    <item>\n'
            '     <attribute name="label" translatable="yes">Object Alignment Snapping</attribute>\n'
            '     <attribute name="action">win.object-alignment-snapping</attribute>\n'
            '    </item>\n'
            '   </section>',
        label="mainmenubar.xml: entrée de menu Object Alignment Snapping",
    )

    # ============ EditSelection.h ============
    f = Path("src/core/control/tools/EditSelection.h")
    ok &= apply_edit(
        f,
        old='#include <array>\n'
            '#include <memory>  // for unique_ptr\n'
            '#include <string>\n'
            '#include <utility>  // for pair\n'
            '#include <vector>   // for vector',
        new='#include <array>\n'
            '#include <memory>  // for unique_ptr\n'
            '#include <optional>\n'
            '#include <string>\n'
            '#include <utility>  // for pair\n'
            '#include <vector>   // for vector',
        label="EditSelection.h: include <optional>",
    )
    ok &= apply_edit(
        f,
        old='class UndoRedoHandler;\n'
            'class Layer;\n'
            'class XojPageView;\n'
            'class Selection;\n'
            'class EditSelectionContents;\n'
            'class DeleteUndoAction;\n'
            'class LineStyle;\n'
            'class ObjectInputStream;\n',
        new='class UndoRedoHandler;\n'
            'class Layer;\n'
            'class XojPageView;\n'
            'class Selection;\n'
            'class EditSelectionContents;\n'
            'class DeleteUndoAction;\n'
            'class LineStyle;\n'
            'class ObjectInputStream;\n'
            'class Settings;\n',
        label="EditSelection.h: forward declaration Settings",
    )
    ok &= apply_edit(
        f,
        old='    /**\n'
            '     * The source layer (form where the Elements come)\n'
            '     */\n'
            '    Layer* sourceLayer{};\n\n',
        new='    /**\n'
            '     * The source layer (form where the Elements come)\n'
            '     */\n'
            '    Layer* sourceLayer{};\n\n'
            '    /**\n'
            '     * Used to check whether object-alignment snapping ("smart guides") is enabled.\n'
            '     */\n'
            '    const Settings* settings{};\n\n'
            '    /**\n'
            '     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or\n'
            '     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that\n'
            '     * spans between the moving selection and the element it is aligned with, so the drawn line\n'
            '     * visually connects the two.\n'
            '     */\n'
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '    };\n\n'
            '    /// Vertical guide line (constant x), set during mouseMove() while dragging, if any.\n'
            '    std::optional<AlignmentGuide> activeGuideX;\n'
            '    /// Horizontal guide line (constant y), set during mouseMove() while dragging, if any.\n'
            '    std::optional<AlignmentGuide> activeGuideY;\n\n',
        label="EditSelection.h: membres settings/activeGuideX/activeGuideY",
    )

    # ============ EditSelection.cpp ============
    f = editsel_cpp

    ok &= apply_edit(
        f,
        old='EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,\n'
            '                             const Range& bounds, const Range& snappingBounds):\n'
            '        snappedBounds(snappingBounds),\n'
            '        btnWidth(getBtnWidth(ctrl)),\n'
            '        sourcePage(page),\n'
            '        sourceLayer(layer),\n'
            '        view(view),\n'
            '        undo(ctrl->getUndoRedoHandler()),\n'
            '        snappingHandler(ctrl->getSettings()) {',
        new='EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,\n'
            '                             const Range& bounds, const Range& snappingBounds):\n'
            '        snappedBounds(snappingBounds),\n'
            '        btnWidth(getBtnWidth(ctrl)),\n'
            '        sourcePage(page),\n'
            '        sourceLayer(layer),\n'
            '        settings(ctrl->getSettings()),\n'
            '        view(view),\n'
            '        undo(ctrl->getUndoRedoHandler()),\n'
            '        snappingHandler(ctrl->getSettings()) {',
        label="EditSelection.cpp: initialiseur settings (constructeur 1)",
    )

    ok &= apply_edit(
        f,
        old='EditSelection::EditSelection(Control* ctrl, const PageRef& page, Layer* layer, XojPageView* view):\n'
            '        snappedBounds(Rectangle<double>{}),\n'
            '        btnWidth(getBtnWidth(ctrl)),\n'
            '        sourcePage(page),\n'
            '        sourceLayer(layer),\n'
            '        view(view),\n'
            '        undo(ctrl->getUndoRedoHandler()),\n'
            '        snappingHandler(ctrl->getSettings()) {',
        new='EditSelection::EditSelection(Control* ctrl, const PageRef& page, Layer* layer, XojPageView* view):\n'
            '        snappedBounds(Rectangle<double>{}),\n'
            '        btnWidth(getBtnWidth(ctrl)),\n'
            '        sourcePage(page),\n'
            '        sourceLayer(layer),\n'
            '        settings(ctrl->getSettings()),\n'
            '        view(view),\n'
            '        undo(ctrl->getUndoRedoHandler()),\n'
            '        snappingHandler(ctrl->getSettings()) {',
        label="EditSelection.cpp: initialiseur settings (constructeur 2)",
    )

    ok &= apply_edit(
        f,
        old='/**\n'
            ' * If any of the moving box\'s 3 horizontal candidates (top / vertical-center / bottom), when placed\n'
            ' * at the given y with the given height, is within `tolerance` (document units) of the corresponding\n'
            ' * candidate of another element on `layer` (elements in `excluded` are skipped - i.e. the elements\n'
            ' * currently being moved), returns the y-offset needed to align them exactly. Returns 0 otherwise.\n'
            ' */\n'
            'static auto findAlignmentOffsetY(double y, double height, double tolerance, Layer* layer,\n'
            '                                  const std::vector<const Element*>& excluded) -> double {\n'
            '    const double candidatesSelf[3] = {y, y + height / 2, y + height};\n'
            '    double bestOffset = 0;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        const double candidatesOther[3] = {ey, ey + eh / 2, ey + eh};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    bestOffset = co - cs;\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return bestOffset;\n'
            '}\n\n'
            '/// Same as findAlignmentOffsetY(), but for the 3 vertical candidates (left / horizontal-center / right).\n'
            'static auto findAlignmentOffsetX(double x, double width, double tolerance, Layer* layer,\n'
            '                                  const std::vector<const Element*>& excluded) -> double {\n'
            '    const double candidatesSelf[3] = {x, x + width / 2, x + width};\n'
            '    double bestOffset = 0;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        const double candidatesOther[3] = {ex, ex + ew / 2, ex + ew};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    bestOffset = co - cs;\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return bestOffset;\n'
            '}\n\n'
            'void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {\n'
            '    double zoom = this->view->getXournal()->getZoom();',
        new='/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '};\n\n'
            '/**\n'
            ' * If any of the moving box\'s 3 horizontal candidates (top / vertical-center / bottom), when placed\n'
            ' * at the given y with the given height, is within `tolerance` (document units) of the corresponding\n'
            ' * candidate of another element on `layer` (elements in `excluded` are skipped - i.e. the elements\n'
            ' * currently being moved), returns the match. Returns nullopt otherwise.\n'
            ' * xLeft/xRight are the moving box\'s horizontal extent, used together with the matched element\'s own\n'
            ' * extent to compute the guide line\'s span (perpendicular axis).\n'
            ' */\n'
            'static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    const double candidatesSelf[3] = {y, y + height / 2, y + height};\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        const double candidatesOther[3] = {ey, ey + eh / 2, ey + eh};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co - cs, co, std::min(xLeft, ex), std::max(xRight, ex + ew)};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            '/// Same as findAlignmentY(), but for the 3 vertical candidates (left / horizontal-center / right).\n'
            '/// yTop/yBottom are the moving box\'s vertical extent, used for the guide line\'s span.\n'
            'static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    const double candidatesSelf[3] = {x, x + width / 2, x + width};\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        const double candidatesOther[3] = {ex, ex + ew / 2, ex + ew};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co - cs, co, std::min(yTop, ey), std::max(yBottom, ey + eh)};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            'void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {\n'
            '    double zoom = this->view->getXournal()->getZoom();',
        label="EditSelection.cpp: findAlignmentX/Y (avec info de ligne de guidage)",
    )

    ok &= apply_edit(
        f,
        old='        // Smart alignment guides: snap the moving selection\'s bounding box edges/centers to those of\n'
            '        // other elements on the same layer, if close enough. Silent for now (no guide line drawn yet).\n'
            '        if (this->sourceLayer != nullptr && this->rotation == 0.0) {\n'
            '            double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;\n'
            '            std::vector<const Element*> excluded = this->getElementsView().clone();\n'
            '            double candidateX = this->snappedBounds.x + dx;\n'
            '            double candidateY = this->snappedBounds.y + dy;\n'
            '            dx += findAlignmentOffsetX(candidateX, this->snappedBounds.width, tolerance, this->sourceLayer, excluded);\n'
            '            dy += findAlignmentOffsetY(candidateY, this->snappedBounds.height, tolerance, this->sourceLayer, excluded);\n'
            '        }\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position\n'
            '        double cx = this->snappedBounds.x;',
        new='        // Smart alignment guides: snap the moving selection\'s bounding box edges/centers to those of\n'
            '        // other elements on the same layer, if close enough, and remember the match to draw a guide\n'
            '        // line connecting the two objects (see paint()).\n'
            '        if (settings != nullptr && settings->isSnapToObjects() && this->sourceLayer != nullptr &&\n'
            '            this->rotation == 0.0) {\n'
            '            double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;\n'
            '            std::vector<const Element*> excluded = this->getElementsView().clone();\n'
            '            double candidateX = this->snappedBounds.x + dx;\n'
            '            double candidateY = this->snappedBounds.y + dy;\n'
            '            double width = this->snappedBounds.width;\n'
            '            double height = this->snappedBounds.height;\n\n'
            '            auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n'
            '                                          this->sourceLayer, excluded);\n'
            '            auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n'
            '                                          this->sourceLayer, excluded);\n\n'
            '            if (matchX) {\n'
            '                dx += matchX->offset;\n'
            '                this->activeGuideX = AlignmentGuide{matchX->coordinate, matchX->extentFrom, matchX->extentTo};\n'
            '            } else {\n'
            '                this->activeGuideX.reset();\n'
            '            }\n'
            '            if (matchY) {\n'
            '                dy += matchY->offset;\n'
            '                this->activeGuideY = AlignmentGuide{matchY->coordinate, matchY->extentFrom, matchY->extentTo};\n'
            '            } else {\n'
            '                this->activeGuideY.reset();\n'
            '            }\n'
            '        } else {\n'
            '            this->activeGuideX.reset();\n'
            '            this->activeGuideY.reset();\n'
            '        }\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position\n'
            '        double cx = this->snappedBounds.x;',
        label="EditSelection.cpp: injection avec suivi de la ligne de guidage",
    )

    ok &= apply_edit(
        f,
        old='    this->mouseDownType = CURSOR_SELECTION_NONE;\n\n'
            '    const bool wasEdgePanning = this->isEdgePanning();',
        new='    this->mouseDownType = CURSOR_SELECTION_NONE;\n'
            '    this->activeGuideX.reset();\n'
            '    this->activeGuideY.reset();\n\n'
            '    const bool wasEdgePanning = this->isEdgePanning();',
        label="EditSelection.cpp: réinitialisation des guides dans mouseUp()",
    )

    ok &= apply_edit(
        f,
        old='    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);\n\n'
            '    GdkRGBA selectionColor = view->getSelectionColor();',
        new='    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);\n\n'
            '    // Smart alignment guides: a bounded pink line connecting the moving selection to whichever\n'
            '    // element(s) it is currently aligned with.\n'
            '    if (this->activeGuideX || this->activeGuideY) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n'
            '        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n\n'
            '        if (this->activeGuideX) {\n'
            '            double gx = this->activeGuideX->coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, this->activeGuideX->from * zoom);\n'
            '            cairo_line_to(cr, gx, this->activeGuideX->to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        if (this->activeGuideY) {\n'
            '            double gy = this->activeGuideY->coordinate * zoom;\n'
            '            cairo_move_to(cr, this->activeGuideY->from * zoom, gy);\n'
            '            cairo_line_to(cr, this->activeGuideY->to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }\n\n'
            '    GdkRGBA selectionColor = view->getSelectionColor();',
        label="EditSelection.cpp: rendu des lignes de guidage roses dans paint()",
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
