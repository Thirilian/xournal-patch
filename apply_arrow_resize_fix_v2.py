#!/usr/bin/env python3
"""
Corrige la deformation de la tete de fleche lors d'un redimensionnement non
uniforme. Ajoute une metadonnee persistante ArrowKind sur Stroke, extrait le
calcul de la geometrie de la tete dans une fonction reutilisable
(Stroke::computeArrowShape), et regenere la tete a chaque redo/undo d'un
ScaleUndoAction (donc dans la MEME action d'annulation que le redimensionnement).

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
    ok = True

    # ============================================================
    # 1. model/Stroke.h
    # ============================================================
    f = Path("src/core/model/Stroke.h")

    ok &= apply_edit(
        f,
        old='class StrokeCapStyle {\n'
            'public:\n'
            '    enum Value {\n'
            '        ROUND = 0,\n'
            '        BUTT = 1,\n'
            '        SQUARE = 2\n'
            '    };  // Must match the indices in StrokeView::CAIRO_LINE_CAP\n'
            '        // and in EraserHandler::PADDING_COEFFICIENT_CAP\n'
            '    static constexpr std::array<const char8_t*, 3> NAMES = {u8"round", u8"butt", u8"square"};\n'
            '    StrokeCapStyle(Value v): value(v) {}\n\n'
            '    // Implicit conversion to underlying enum type\n'
            '    operator const Value&() const { return value; }\n'
            '    operator Value&() { return value; }\n\n'
            'private:\n'
            '    Value value;\n'
            '};\n',
        new='class StrokeCapStyle {\n'
            'public:\n'
            '    enum Value {\n'
            '        ROUND = 0,\n'
            '        BUTT = 1,\n'
            '        SQUARE = 2\n'
            '    };  // Must match the indices in StrokeView::CAIRO_LINE_CAP\n'
            '        // and in EraserHandler::PADDING_COEFFICIENT_CAP\n'
            '    static constexpr std::array<const char8_t*, 3> NAMES = {u8"round", u8"butt", u8"square"};\n'
            '    StrokeCapStyle(Value v): value(v) {}\n\n'
            '    // Implicit conversion to underlying enum type\n'
            '    operator const Value&() const { return value; }\n'
            '    operator Value&() { return value; }\n\n'
            'private:\n'
            '    Value value;\n'
            '};\n\n'
            '/**\n'
            ' * Marks a Stroke as having been drawn with the arrow tool (single or double-ended), so that its\n'
            ' * arrowhead(s) can be regenerated (e.g. after a resize) instead of being naively affine-transformed,\n'
            ' * which would otherwise distort them under non-uniform scaling. NONE for any regular stroke.\n'
            ' */\n'
            'class ArrowKind {\n'
            'public:\n'
            '    enum Value { NONE, SINGLE, DOUBLE };\n'
            '    static constexpr std::array<const char8_t*, 3> NAMES = {u8"none", u8"single", u8"double"};\n'
            '    ArrowKind(Value v): value(v) {}\n\n'
            '    operator const Value&() const { return value; }\n'
            '    operator Value&() { return value; }\n\n'
            'private:\n'
            '    Value value = NONE;\n'
            '};\n',
        label="Stroke.h: classe ArrowKind",
    )

    ok &= apply_edit(
        f,
        old='    void setToolType(StrokeTool type);\n'
            '    StrokeTool getToolType() const;\n\n',
        new='    void setToolType(StrokeTool type);\n'
            '    StrokeTool getToolType() const;\n\n'
            '    void setArrowKind(ArrowKind kind);\n'
            '    ArrowKind getArrowKind() const;\n\n'
            '    /**\n'
            '     * @brief Computes the point sequence for a straight line from `start` to `end`, with an arrowhead\n'
            '     * at `end` (kind == SINGLE) or at both ends (kind == DOUBLE), sized according to `thickness`.\n'
            '     * This is the single source of truth for arrowhead geometry, used both when initially drawing an\n'
            '     * arrow (see ArrowHandler) and when regenerating the head(s) of an existing arrow Stroke after a\n'
            '     * resize (see ScaleUndoAction).\n'
            '     */\n'
            '    static std::vector<Point> computeArrowShape(Point start, Point end, double thickness, ArrowKind kind);\n\n'
            '    /**\n'
            '     * @brief If this Stroke is an arrow (getArrowKind() != ArrowKind::NONE), replaces its points with\n'
            '     * a freshly computed arrow shape between its current shaft endpoints, using its current width.\n'
            '     * No-op for a stroke that isn\'t an arrow, or that doesn\'t have the expected point layout (e.g. was\n'
            '     * heavily hand-edited since being drawn).\n'
            '     */\n'
            '    void regenerateArrowHeadIfApplicable();\n\n',
        label="Stroke.h: déclarations setArrowKind/getArrowKind/computeArrowShape/regenerateArrowHeadIfApplicable",
    )

    ok &= apply_edit(
        f,
        old='    StrokeTool toolType = StrokeTool::PEN;',
        new='    StrokeTool toolType = StrokeTool::PEN;\n    ArrowKind arrowKind = ArrowKind::NONE;',
        label="Stroke.h: membre arrowKind",
    )

    # ============================================================
    # 2. model/Stroke.cpp
    # ============================================================
    f = Path("src/core/model/Stroke.cpp")

    ok &= apply_edit(
        f,
        old='void Stroke::setToolType(StrokeTool type) { this->toolType = type; }\n\n'
            'auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }\n\n',
        new='void Stroke::setToolType(StrokeTool type) { this->toolType = type; }\n\n'
            'auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }\n\n'
            'void Stroke::setArrowKind(ArrowKind kind) { this->arrowKind = kind; }\n\n'
            'auto Stroke::getArrowKind() const -> ArrowKind { return this->arrowKind; }\n\n'
            'auto Stroke::computeArrowShape(Point start, Point end, double thickness, ArrowKind kind) -> std::vector<Point> {\n'
            '    const double lineLength = std::hypot(end.x - start.x, end.y - start.y);\n'
            '    const double slimness = lineLength / thickness;\n\n'
            '    // We\'ve now computed the line points for the arrow\n'
            '    // so we just have to build the head:\n'
            '    // arrowDist is the distance between the line\'s and the arrow\'s tips\n'
            '    // delta is the angle between each arrow leg and the line\n\n'
            '    // an appropriate opening angle 2*delta is Pi/3 radians for an arrow shape\n'
            '    double delta = M_PI / 6.0;\n'
            '    // We use different slimness regimes for proper sizing:\n'
            '    const double THICK1 = 7, THICK3 = 1.6;\n'
            '    const double LENGTH2 = 0.4, LENGTH4 = (kind == ArrowKind::DOUBLE ? 0.5 : 0.8);\n'
            '    // set up the size of the arrow head to be THICK1 x the thickness of the line\n'
            '    double arrowDist = thickness * THICK1;\n'
            '    // but not too large compared to the line length\n'
            '    if (slimness >= THICK1 / LENGTH2) {\n'
            '        // arrow head is not too long compared to the line length (regime 1)\n'
            '    } else if (slimness >= THICK3 / LENGTH2) {\n'
            '        // arrow head is not too short compared to the thickness (regime 2)\n'
            '        arrowDist = lineLength * LENGTH2;\n'
            '    } else if (slimness >= THICK3 / LENGTH4) {\n'
            '        // arrow head is not too thick compared to the line length (regime 3)\n'
            '        arrowDist = thickness * THICK3;\n'
            '        // help visibility by widening the angle\n'
            '        delta = (1 + (slimness - THICK3 / LENGTH2) / (THICK3 / LENGTH4 - THICK3 / LENGTH2)) * M_PI / 6.0;\n'
            '        // which allows to shorten the tips and keep the horizonzal distance\n'
            '        arrowDist *= sin(M_PI / 6.0) / sin(delta);\n'
            '    } else {\n'
            '        // shrinking down gracefully (regime 4)\n'
            '        arrowDist = lineLength * LENGTH4;\n'
            '        delta = M_PI / 3.0;\n'
            '        arrowDist *= sin(M_PI / 6.0) / sin(M_PI / 3.0);\n'
            '    }\n\n'
            '    const double angle = atan2(end.y - start.y, end.x - start.x);\n\n'
            '    std::vector<Point> shape;\n'
            '    shape.reserve(kind == ArrowKind::DOUBLE ? 10 : 6);\n\n'
            '    shape.emplace_back(start);\n\n'
            '    if (kind == ArrowKind::DOUBLE) {\n'
            '        shape.emplace_back(start.x + arrowDist * cos(angle + delta), start.y + arrowDist * sin(angle + delta));\n'
            '        shape.emplace_back(start);\n'
            '        shape.emplace_back(start.x + arrowDist * cos(angle - delta), start.y + arrowDist * sin(angle - delta));\n'
            '        shape.emplace_back(start);\n'
            '    }\n\n'
            '    shape.emplace_back(end);\n'
            '    shape.emplace_back(end.x - arrowDist * cos(angle + delta), end.y - arrowDist * sin(angle + delta));\n'
            '    shape.emplace_back(end);\n'
            '    shape.emplace_back(end.x - arrowDist * cos(angle - delta), end.y - arrowDist * sin(angle - delta));\n'
            '    shape.emplace_back(end);\n\n'
            '    return shape;\n'
            '}\n\n'
            'void Stroke::regenerateArrowHeadIfApplicable() {\n'
            '    if (this->arrowKind == ArrowKind::NONE) {\n'
            '        return;\n'
            '    }\n'
            '    const size_t expectedCount = (this->arrowKind == ArrowKind::DOUBLE) ? 10 : 6;\n'
            '    if (this->points.size() != expectedCount) {\n'
            '        // The point layout doesn\'t match what computeArrowShape() produces (e.g. the stroke was\n'
            '        // hand-edited since being drawn, or points were erased) - leave it alone rather than guess.\n'
            '        return;\n'
            '    }\n'
            '    const Point start = this->points.front();\n'
            '    const Point end = this->points[this->arrowKind == ArrowKind::DOUBLE ? 5 : 1];\n'
            '    this->setPointVector(computeArrowShape(start, end, this->width, this->arrowKind));\n'
            '}\n\n',
        label="Stroke.cpp: implémentations ArrowKind/computeArrowShape/regenerateArrowHeadIfApplicable",
    )

    # ============================================================
    # 3. control/tools/ArrowHandler.cpp (rewrite: use the shared function)
    # ============================================================
    f = Path("src/core/control/tools/ArrowHandler.cpp")

    ok &= apply_edit(
        f,
        old='#include "ArrowHandler.h"\n\n'
            '#include <algorithm>  // for minmax_element\n'
            '#include <cmath>      // for cos, sin, atan2, M_PI\n\n'
            '#include "control/Control.h"                       // for Control\n'
            '#include "control/ToolHandler.h"                   // for ToolHandler\n'
            '#include "control/tools/BaseShapeHandler.h"        // for BaseShapeHandler\n'
            '#include "control/tools/SnapToGridInputHandler.h"  // for SnapToGridInputHan...\n'
            '#include "gui/inputdevices/PositionInputData.h"    // for PositionInputData\n'
            '#include "model/Point.h"                           // for Point\n'
            '#include "util/Range.h"                            // for Range\n\n'
            'ArrowHandler::ArrowHandler(Control* control, const PageRef& page, bool doubleEnded):\n'
            '        BaseShapeHandler(control, page), doubleEnded(doubleEnded) {}\n\n'
            'ArrowHandler::~ArrowHandler() = default;\n\n'
            'auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)\n'
            '        -> std::pair<std::vector<Point>, Range> {\n'
            '    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    const double lineLength = std::hypot(c.x - this->startPoint.x, c.y - this->startPoint.y);\n'
            '    const double thickness = control->getToolHandler()->getThickness();\n'
            '    const double slimness = lineLength / thickness;\n\n'
            '    // We\'ve now computed the line points for the arrow\n'
            '    // so we just have to build the head:\n'
            '    // arrowDist is the distance between the line\'s and the arrow\'s tips\n'
            '    // delta is the angle between each arrow leg and the line\n\n'
            '    // an appropriate opening angle 2*delta is Pi/3 radians for an arrow shape\n'
            '    double delta = M_PI / 6.0;\n'
            '    // We use different slimness regimes for proper sizing:\n'
            '    const double THICK1 = 7, THICK3 = 1.6;\n'
            '    const double LENGTH2 = 0.4, LENGTH4 = (doubleEnded ? 0.5 : 0.8);\n'
            '    // set up the size of the arrow head to be THICK1 x the thickness of the line\n'
            '    double arrowDist = thickness * THICK1;\n'
            '    // but not too large compared to the line length\n'
            '    if (slimness >= THICK1 / LENGTH2) {\n'
            '        // arrow head is not too long compared to the line length (regime 1)\n'
            '    } else if (slimness >= THICK3 / LENGTH2) {\n'
            '        // arrow head is not too short compared to the thickness (regime 2)\n'
            '        arrowDist = lineLength * LENGTH2;\n'
            '    } else if (slimness >= THICK3 / LENGTH4) {\n'
            '        // arrow head is not too thick compared to the line length (regime 3)\n'
            '        arrowDist = thickness * THICK3;\n'
            '        // help visibility by widening the angle\n'
            '        delta = (1 + (slimness - THICK3 / LENGTH2) / (THICK3 / LENGTH4 - THICK3 / LENGTH2)) *  M_PI / 6.0;\n'
            '        // which allows to shorten the tips and keep the horizonzal distance\n'
            '        arrowDist *= sin(M_PI / 6.0) / sin(delta);\n'
            '    } else {\n'
            '        // shrinking down gracefully (regime 4)\n'
            '        arrowDist = lineLength * LENGTH4;\n'
            '        delta = M_PI / 3.0;\n'
            '        arrowDist *= sin(M_PI / 6.0) / sin(M_PI / 3.0);\n'
            '    }\n\n'
            '    const double angle = atan2(c.y - this->startPoint.y, c.x - this->startPoint.x);\n\n'
            '    std::pair<std::vector<Point>, Range> res; // members initialised below\n'
            '    std::vector<Point>& shape = res.first;\n\n'
            '    shape.reserve(doubleEnded ? 10 : 6);\n\n'
            '    shape.emplace_back(this->startPoint);\n\n'
            '    if (doubleEnded) {\n'
            '        shape.emplace_back(startPoint.x + arrowDist * cos(angle + delta),\n'
            '                           startPoint.y + arrowDist * sin(angle + delta));\n'
            '        shape.emplace_back(startPoint);\n'
            '        shape.emplace_back(startPoint.x + arrowDist * cos(angle - delta),\n'
            '                           startPoint.y + arrowDist * sin(angle - delta));\n'
            '        shape.emplace_back(startPoint);\n'
            '    }\n\n'
            '    shape.emplace_back(c);\n'
            '    shape.emplace_back(c.x - arrowDist * cos(angle + delta), c.y - arrowDist * sin(angle + delta));\n'
            '    shape.emplace_back(c);\n'
            '    shape.emplace_back(c.x - arrowDist * cos(angle - delta), c.y - arrowDist * sin(angle - delta));\n'
            '    shape.emplace_back(c);\n\n'
            '    auto [minX, maxX] = std::minmax_element(shape.begin(), shape.end(), [](auto& p, auto& q) { return p.x < q.x; });\n'
            '    auto [minY, maxY] = std::minmax_element(shape.begin(), shape.end(), [](auto& p, auto& q) { return p.y < q.y; });\n'
            '    res.second = Range(minX->x, minY->y, maxX->x, maxY->y);\n\n'
            '    return res;\n'
            '}\n',
        new='#include "ArrowHandler.h"\n\n'
            '#include <algorithm>  // for minmax_element\n\n'
            '#include "control/Control.h"                       // for Control\n'
            '#include "control/ToolHandler.h"                   // for ToolHandler\n'
            '#include "control/tools/BaseShapeHandler.h"        // for BaseShapeHandler\n'
            '#include "control/tools/SnapToGridInputHandler.h"  // for SnapToGridInputHan...\n'
            '#include "gui/inputdevices/PositionInputData.h"    // for PositionInputData\n'
            '#include "model/Point.h"                           // for Point\n'
            '#include "model/Stroke.h"                          // for Stroke, ArrowKind\n'
            '#include "util/Range.h"                            // for Range\n\n'
            'ArrowHandler::ArrowHandler(Control* control, const PageRef& page, bool doubleEnded):\n'
            '        BaseShapeHandler(control, page), doubleEnded(doubleEnded) {}\n\n'
            'ArrowHandler::~ArrowHandler() = default;\n\n'
            'auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)\n'
            '        -> std::pair<std::vector<Point>, Range> {\n'
            '    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);\n'
            '    const double thickness = control->getToolHandler()->getThickness();\n'
            '    const ArrowKind kind = this->doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE;\n\n'
            '    std::pair<std::vector<Point>, Range> res;  // members initialised below\n'
            '    std::vector<Point>& shape = res.first;\n'
            '    shape = Stroke::computeArrowShape(this->startPoint, c, thickness, kind);\n\n'
            '    auto [minX, maxX] = std::minmax_element(shape.begin(), shape.end(), [](auto& p, auto& q) { return p.x < q.x; });\n'
            '    auto [minY, maxY] = std::minmax_element(shape.begin(), shape.end(), [](auto& p, auto& q) { return p.y < q.y; });\n'
            '    res.second = Range(minX->x, minY->y, maxX->x, maxY->y);\n\n'
            '    return res;\n'
            '}\n',
        label="ArrowHandler.cpp: réutilise Stroke::computeArrowShape",
    )

    # ============================================================
    # 4. control/tools/BaseShapeHandler.h
    # ============================================================
    f = Path("src/core/control/tools/BaseShapeHandler.h")

    ok &= apply_edit(
        f,
        old='#include "model/PageRef.h"  // for PageRef\n'
            '#include "model/Point.h"    // for Point\n'
            '#include "util/Range.h"     // for Range',
        new='#include "model/PageRef.h"  // for PageRef\n'
            '#include "model/Point.h"    // for Point\n'
            '#include "model/Stroke.h"   // for ArrowKind\n'
            '#include "util/Range.h"     // for Range',
        label="BaseShapeHandler.h: include Stroke.h",
    )

    ok &= apply_edit(
        f,
        old='    /**\n'
            '     * @brief Get the shape\'s points.\n'
            '     */\n'
            '    const std::vector<Point>& getShape() const;\n\n'
            'private:',
        new='    /**\n'
            '     * @brief Get the shape\'s points.\n'
            '     */\n'
            '    const std::vector<Point>& getShape() const;\n\n'
            '    /**\n'
            '     * @brief Whether this shape tool produces an arrow (and if so, single- or double-ended), so that\n'
            '     * the finalized Stroke can be tagged accordingly (see Stroke::setArrowKind()). NONE by default;\n'
            '     * overridden by ArrowHandler.\n'
            '     */\n'
            '    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }\n\n'
            'private:',
        label="BaseShapeHandler.h: virtual getArrowKind()",
    )

    # ============================================================
    # 5. control/tools/ArrowHandler.h
    # ============================================================
    f = Path("src/core/control/tools/ArrowHandler.h")

    ok &= apply_edit(
        f,
        old='class ArrowHandler: public BaseShapeHandler {\n'
            'public:\n'
            '    ArrowHandler(Control* control, const PageRef& page, bool doubleEnded);\n'
            '    ~ArrowHandler() override;\n\n'
            'private:',
        new='class ArrowHandler: public BaseShapeHandler {\n'
            'public:\n'
            '    ArrowHandler(Control* control, const PageRef& page, bool doubleEnded);\n'
            '    ~ArrowHandler() override;\n\n'
            '    ArrowKind getArrowKind() const override { return doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE; }\n\n'
            'private:',
        label="ArrowHandler.h: override getArrowKind()",
    )

    # ============================================================
    # 6. control/tools/BaseShapeHandler.cpp
    # ============================================================
    f = Path("src/core/control/tools/BaseShapeHandler.cpp")

    ok &= apply_edit(
        f,
        old='    stroke->setPointVector(this->shape, &lastSnappingRange);',
        new='    stroke->setPointVector(this->shape, &lastSnappingRange);\n'
            '    stroke->setArrowKind(this->getArrowKind());',
        label="BaseShapeHandler.cpp: pose le flag sur le Stroke final",
    )

    # ============================================================
    # 7. undo/ScaleUndoAction.cpp
    # ============================================================
    f = Path("src/core/undo/ScaleUndoAction.cpp")

    ok &= apply_edit(
        f,
        old='#include "control/Control.h"\n'
            '#include "model/Document.h"\n'
            '#include "model/Element.h"    // for Element\n'
            '#include "model/PageRef.h"    // for PageRef\n'
            '#include "model/XojPage.h"    // for XojPage\n'
            '#include "undo/UndoAction.h"  // for UndoAction\n'
            '#include "util/Range.h"       // for Range\n'
            '#include "util/i18n.h"        // for _',
        new='#include "control/Control.h"\n'
            '#include "model/Document.h"\n'
            '#include "model/Element.h"    // for Element\n'
            '#include "model/PageRef.h"    // for PageRef\n'
            '#include "model/Stroke.h"     // for Stroke, ArrowKind\n'
            '#include "model/XojPage.h"    // for XojPage\n'
            '#include "undo/UndoAction.h"  // for UndoAction\n'
            '#include "util/Range.h"       // for Range\n'
            '#include "util/i18n.h"        // for _',
        label="ScaleUndoAction.cpp: include Stroke.h",
    )

    ok &= apply_edit(
        f,
        old='    for (Element* e: this->elements) {\n'
            '        r.addPoint(e->getX(), e->getY());\n'
            '        r.addPoint(e->getX() + e->getElementWidth(), e->getY() + e->getElementHeight());\n'
            '        e->scale(this->x0, this->y0, fx, fy, this->rotation, restoreLineWidth);\n'
            '        r.addPoint(e->getX(), e->getY());\n'
            '        r.addPoint(e->getX() + e->getElementWidth(), e->getY() + e->getElementHeight());\n'
            '    }',
        new='    for (Element* e: this->elements) {\n'
            '        r.addPoint(e->getX(), e->getY());\n'
            '        r.addPoint(e->getX() + e->getElementWidth(), e->getY() + e->getElementHeight());\n'
            '        e->scale(this->x0, this->y0, fx, fy, this->rotation, restoreLineWidth);\n'
            '        if (auto* stroke = dynamic_cast<Stroke*>(e)) {\n'
            '            // A naive affine transform of an arrow\'s points distorts its head under non-uniform\n'
            '            // scaling (the stroke width only scales by the geometric mean of fx/fy, see\n'
            '            // Stroke::scale()). Regenerate the head geometry from scratch instead, using the\n'
            '            // now-scaled shaft endpoints and width. Runs on both redo and undo, so the head always\n'
            '            // matches the current size - no separate undo step needed.\n'
            '            stroke->regenerateArrowHeadIfApplicable();\n'
            '        }\n'
            '        r.addPoint(e->getX(), e->getY());\n'
            '        r.addPoint(e->getX() + e->getElementWidth(), e->getY() + e->getElementHeight());\n'
            '    }',
        label="ScaleUndoAction.cpp: régénération de la tête après scale()",
    )

    # ============================================================
    # 8. control/xojfile/XmlAttrs.h
    # ============================================================
    f = Path("src/core/control/xojfile/XmlAttrs.h")

    ok &= apply_edit(
        f,
        old='// stroke\n'
            'constexpr auto TOOL_STR = u8"tool";\n'
            'constexpr auto PRESSURES_STR = u8"pressures";\n'
            'constexpr auto FILL_STR = u8"fill";\n'
            'constexpr auto CAPSTYLE_STR = u8"capStyle";',
        new='// stroke\n'
            'constexpr auto TOOL_STR = u8"tool";\n'
            'constexpr auto PRESSURES_STR = u8"pressures";\n'
            'constexpr auto FILL_STR = u8"fill";\n'
            'constexpr auto CAPSTYLE_STR = u8"capStyle";\n'
            'constexpr auto ARROW_STR = u8"arrow";  // absent = not an arrow; see ArrowKind::NAMES for the other values',
        label="XmlAttrs.h: constante ARROW_STR",
    )

    # ============================================================
    # 9. control/xojfile/SaveHandler.cpp
    # ============================================================
    f = Path("src/core/control/xojfile/SaveHandler.cpp")

    ok &= apply_edit(
        f,
        old='    stroke->setAttrib(xoj::xml_attrs::TOOL_STR, StrokeTool::NAMES[t]);\n',
        new='    stroke->setAttrib(xoj::xml_attrs::TOOL_STR, StrokeTool::NAMES[t]);\n\n'
            '    if (ArrowKind k = s->getArrowKind(); k != ArrowKind::NONE) {\n'
            '        stroke->setAttrib(xoj::xml_attrs::ARROW_STR, ArrowKind::NAMES[k]);\n'
            '    }\n',
        label="SaveHandler.cpp: écrit l'attribut arrow",
    )

    # ============================================================
    # 10. control/xojfile/DocumentBuilderInterface.h
    # ============================================================
    f = Path("src/core/control/xojfile/DocumentBuilderInterface.h")

    ok &= apply_edit(
        f,
        old='class LineStyle;\n'
            'class PageType;\n'
            'class Point;\n'
            'class StrokeCapStyle;\n'
            'class StrokeTool;\n'
            'class LinkAlignment;',
        new='class LineStyle;\n'
            'class PageType;\n'
            'class Point;\n'
            'class ArrowKind;\n'
            'class StrokeCapStyle;\n'
            'class StrokeTool;\n'
            'class LinkAlignment;',
        label="DocumentBuilderInterface.h: forward-declare ArrowKind",
    )

    ok &= apply_edit(
        f,
        old='    virtual void addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                           const LineStyle& lineStyle, fs::path filename, size_t timestamp) = 0;',
        new='    virtual void addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                           ArrowKind arrowKind, const LineStyle& lineStyle, fs::path filename, size_t timestamp) = 0;',
        label="DocumentBuilderInterface.h: signature addStroke",
    )

    # ============================================================
    # 11. control/xojfile/LoadHandler.h
    # ============================================================
    f = Path("src/core/control/xojfile/LoadHandler.h")

    ok &= apply_edit(
        f,
        old='    void addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                   const LineStyle& lineStyle, fs::path filename, size_t timestamp) override;',
        new='    void addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                   ArrowKind arrowKind, const LineStyle& lineStyle, fs::path filename, size_t timestamp) override;',
        label="LoadHandler.h: signature addStroke",
    )

    # ============================================================
    # 12. control/xojfile/LoadHandler.cpp
    # ============================================================
    f = Path("src/core/control/xojfile/LoadHandler.cpp")

    ok &= apply_edit(
        f,
        old='void LoadHandler::addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                            const LineStyle& lineStyle, fs::path filename, size_t timestamp) {\n'
            '    xoj_assert(!this->stroke);\n'
            '    this->stroke = std::make_unique<Stroke>();\n\n'
            '    this->stroke->setToolType(tool);\n'
            '    this->stroke->setColor(color);\n'
            '    this->stroke->setWidth(width);\n'
            '    this->stroke->setFill(fill);\n'
            '    this->stroke->setStrokeCapStyle(capStyle);\n'
            '    this->stroke->setLineStyle(lineStyle);\n\n'
            '    setAudioAttributes(*this->stroke, std::move(filename), timestamp);\n'
            '}',
        new='void LoadHandler::addStroke(StrokeTool tool, Color color, double width, int fill, StrokeCapStyle capStyle,\n'
            '                            ArrowKind arrowKind, const LineStyle& lineStyle, fs::path filename, size_t timestamp) {\n'
            '    xoj_assert(!this->stroke);\n'
            '    this->stroke = std::make_unique<Stroke>();\n\n'
            '    this->stroke->setToolType(tool);\n'
            '    this->stroke->setColor(color);\n'
            '    this->stroke->setWidth(width);\n'
            '    this->stroke->setFill(fill);\n'
            '    this->stroke->setStrokeCapStyle(capStyle);\n'
            '    this->stroke->setArrowKind(arrowKind);\n'
            '    this->stroke->setLineStyle(lineStyle);\n\n'
            '    setAudioAttributes(*this->stroke, std::move(filename), timestamp);\n'
            '}',
        label="LoadHandler.cpp: implémentation addStroke avec arrowKind",
    )

    # ============================================================
    # 13. control/xojfile/XmlParser.cpp
    # ============================================================
    f = Path("src/core/control/xojfile/XmlParser.cpp")

    ok &= apply_edit(
        f,
        old='    // cap style\n'
            '    const auto capStyle = XmlParserHelper::getAttribMandatory<StrokeCapStyle>(\n'
            '            xoj::xml_attrs::CAPSTYLE_STR, attributeMap, StrokeCapStyle::ROUND, false);\n\n'
            '    // line style\n'
            '    const auto lineStyle =\n'
            '            XmlParserHelper::getAttribMandatory<LineStyle>(xoj::xml_attrs::STYLE_STR, attributeMap, {}, false);',
        new='    // cap style\n'
            '    const auto capStyle = XmlParserHelper::getAttribMandatory<StrokeCapStyle>(\n'
            '            xoj::xml_attrs::CAPSTYLE_STR, attributeMap, StrokeCapStyle::ROUND, false);\n\n'
            '    // arrow (absent = not an arrow)\n'
            '    const auto arrowKind =\n'
            '            XmlParserHelper::getAttribMandatory<ArrowKind>(xoj::xml_attrs::ARROW_STR, attributeMap, ArrowKind::NONE, false);\n\n'
            '    // line style\n'
            '    const auto lineStyle =\n'
            '            XmlParserHelper::getAttribMandatory<LineStyle>(xoj::xml_attrs::STYLE_STR, attributeMap, {}, false);',
        label="XmlParser.cpp: parse l'attribut arrow",
    )

    ok &= apply_edit(
        f,
        old='    // forward data to builder\n'
            '    this->builder.addStroke(tool, color, width, fill, capStyle, lineStyle, std::move(this->tempFilename),\n'
            '                            this->tempTimestamp);',
        new='    // forward data to builder\n'
            '    this->builder.addStroke(tool, color, width, fill, capStyle, arrowKind, lineStyle, std::move(this->tempFilename),\n'
            '                            this->tempTimestamp);',
        label="XmlParser.cpp: passe arrowKind à addStroke",
    )

    # ============================================================
    # 14. control/tools/EditSelectionContents.cpp
    #     C'est ICI que le scale est reellement applique lors d'un redimensionnement
    #     interactif normal (ScaleUndoAction ne sert qu'aux Ctrl+Z/Ctrl+Y ulterieurs -
    #     son constructeur/addUndoAction() n'applique rien lui-meme).
    # ============================================================
    f = Path("src/core/control/tools/EditSelectionContents.cpp")

    ok &= apply_edit(
        f,
        old='    for (auto&& [e, _]: this->insertionOrder) {\n'
            '        if (move) {\n'
            '            e->move(mx, my);\n'
            '        }\n'
            '        if (scale) {\n'
            '            e->scale(bounds.x, bounds.y, fx, fy, 0, this->restoreLineWidth);\n'
            '        }\n'
            '        if (rotate) {\n'
            '            e->rotate(snappedBounds.x + this->lastSnappedBounds.width / 2,\n'
            '                      snappedBounds.y + this->lastSnappedBounds.height / 2, this->rotation);\n'
            '        }\n'
            '    }',
        new='    for (auto&& [e, _]: this->insertionOrder) {\n'
            '        if (move) {\n'
            '            e->move(mx, my);\n'
            '        }\n'
            '        if (scale) {\n'
            '            e->scale(bounds.x, bounds.y, fx, fy, 0, this->restoreLineWidth);\n'
            '            if (auto* stroke = dynamic_cast<Stroke*>(e.get())) {\n'
            '                stroke->regenerateArrowHeadIfApplicable();\n'
            '            }\n'
            '        }\n'
            '        if (rotate) {\n'
            '            e->rotate(snappedBounds.x + this->lastSnappedBounds.width / 2,\n'
            '                      snappedBounds.y + this->lastSnappedBounds.height / 2, this->rotation);\n'
            '        }\n'
            '    }',
        label="EditSelectionContents.cpp: régénère la tête au vrai point d'application du scale",
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
