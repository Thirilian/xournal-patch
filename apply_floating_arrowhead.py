#!/usr/bin/env python3
"""
Patch 15.0v2 : version CONSOLIDEE de toute la serie 15.X (tetes de fleche,
Ctrl+L), regroupant les patchs 15.1 a 15.9 puis 15.11 (15.10 exclu).

DIFFERENCE avec le patch 15.0 (premiere version, desormais obsolete) :
cinq zones ont ete rendues ROBUSTES a une eventuelle application prealable
d'apply_arrow_resize_fix_v2.py (prerequis de la serie alignment_snap), qui
modifie les MEMES fichiers a des points de couture voisins :
  - XmlAttrs.h : ancrage reduit a la seule ligne CAPSTYLE_STR (au lieu du
    bloc CAPSTYLE_STR + ligne vide + commentaire "// text", que
    arrow_resize_fix_v2 scinde en y inserant sa propre constante ARROW_STR).
  - DocumentBuilderInterface.h / LoadHandler.h / LoadHandler.cpp (zone 1) :
    ancrage reduit a la QUEUE de la signature addStroke (a partir de
    "fs::path filename, size_t timestamp"), qui reste identique que
    arrow_resize_fix_v2 ait ou non insere son parametre ArrowKind PLUS TOT
    dans la meme signature (juste avant lineStyle) ; desambiguise de
    addText() (signature voisine similaire) via la ligne suivante,
    propre a addStroke (setStrokePoints / xoj_assert(!this->stroke)).
  - LoadHandler.cpp (zone 2) : ancrage deplace apres setLineStyle() (l'ajout
    arrow_resize_fix_v2 se trouve avant, sur setStrokeCapStyle()).
  - XmlParser.cpp (zone 2, appel a addStroke) : ancrage reduit a la queue de
    l'appel (a partir de "this->tempTimestamp)"), independant de la presence
    du parametre arrowKind insere plus tot dans le meme appel.
Toutes ces zones ont ete testees et verifiees UNIQUES dans les deux etats
(avec et sans apply_arrow_resize_fix_v2.py applique au prealable), et
produisent le meme resultat final que le patch 15.0 original dans le cas
ou apply_arrow_resize_fix_v2.py n'a PAS ete applique (verifie par diff
byte pour byte).

Genere par diff automatise (difflib, groupement de hunks avec verification
d'unicite de chaque motif) entre :
  - etat F : juste apres apply_paste_follow_cursor_v3.py +
    apply_floating_marks_v2.py
  - etat T : F + apply_patch15_1.py .. apply_patch15_9.py +
    apply_patch15_11.py (apply_patch15_10.py explicitement exclu)
puis 5 zones retravaillees manuellement pour la robustesse ci-dessus.

Nouvelle chaine minimale pour la serie 15.X :
  apply_paste_follow_cursor_v3.py
  apply_floating_marks_v2.py
  apply_fix_warnings.py       (optionnel, inchange)
  [apply_arrow_resize_fix_v2.py]  (optionnel, ordre indifferent avec ce script)
  apply_patch15_0v2.py

NECESSITE : apply_paste_follow_cursor_v3.py puis apply_floating_marks_v2.py
(deja appliques). apply_arrow_resize_fix_v2.py peut etre applique avant OU
apres ce script, dans nimporte quel ordre - ou pas du tout.

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

Z1_OLD = '    INSERT_TICK_HORIZONTAL,\n    INSERT_TICK_VERTICAL,\n\n    // Keep this last value\n'
Z1_NEW = '    INSERT_TICK_HORIZONTAL,\n    INSERT_TICK_VERTICAL,\n    INSERT_ARROWHEAD,\n\n    // Keep this last value\n'
Z2_OLD = '        "insert-cross",\n        "insert-tick-horizontal",\n        "insert-tick-vertical"};\n'
Z2_NEW = '        "insert-cross",\n        "insert-tick-horizontal",\n        "insert-tick-vertical",\n        "insert-arrowhead"};\n'
Z3_OLD = '    static constexpr const char* accelerators[] = {"<Ctrl><Shift>J", nullptr};\n    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertTickVertical(); }\n};\ntemplate <>\n'
Z3_NEW = '    static constexpr const char* accelerators[] = {"<Ctrl><Shift>J", nullptr};\n    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertTickVertical(); }\n};\ntemplate <>\nstruct ActionProperties<Action::INSERT_ARROWHEAD> {\n    static constexpr const char* accelerators[] = {"<Ctrl>L", nullptr};\n    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->insertArrowHead(); }\n};\ntemplate <>\n'
Z4_OLD = '    void insertTickVertical();\n\n    void help();\n\n'
Z4_NEW = "    void insertTickVertical();\n\n    /**\n     * Insert a small arrowhead mark (a single upward-pointing chevron at spawn), attached to the mouse\n     * pointer until the next left click. Uses the currently selected tool's color and thickness.\n     */\n    void insertArrowHead();\n\n    void help();\n\n"
Z5_OLD = "\n/**\n * Creates a small Stroke (a cross or a tick mark, depending on localOffsets) using the currently\n * selected tool's color and thickness, spawns it under the mouse pointer (or at the center of the\n"
Z5_NEW = "\n/**\n * Half-extent (in document points) of the arrowhead mark, both horizontally (from the tip to either\n * leg's far end) and vertically (from the tip to the legs' base). Total visual span of the arrowhead\n * is 2 * ARROWHEAD_SIZE wide and ARROWHEAD_SIZE tall.\n */\nconstexpr double ARROWHEAD_SIZE = 3.;\n\n/**\n * Creates a small Stroke (a cross or a tick mark, depending on localOffsets) using the currently\n * selected tool's color and thickness, spawns it under the mouse pointer (or at the center of the\n"
Z6_OLD = ' */\nstatic void createFloatingMark(Control* ctrl, XournalView* xournal,\n                                const std::vector<std::pair<double, double>>& localOffsets) {\n    double x = 0;\n    double y = 0;\n'
Z6_NEW = ' */\nstatic void createFloatingMark(Control* ctrl, XournalView* xournal,\n                                const std::vector<std::pair<double, double>>& localOffsets,\n                                bool snappableTip = false) {\n    double x = 0;\n    double y = 0;\n'
Z7_OLD = '        stroke->setColor(toolHandler->getTool(TOOL_PEN).getColor());\n    }\n    for (auto&& [dx, dy]: localOffsets) {\n        stroke->addPoint(Point(x + dx, y + dy));\n'
Z7_NEW = '        stroke->setColor(toolHandler->getTool(TOOL_PEN).getColor());\n    }\n    stroke->setHasSnappableTip(snappableTip);\n    for (auto&& [dx, dy]: localOffsets) {\n        stroke->addPoint(Point(x + dx, y + dy));\n'
Z8_OLD = 'void Control::insertTickVertical() {\n    createFloatingMark(this, win->getXournal(), {{0, -TICK_MARK_SIZE}, {0, TICK_MARK_SIZE}});\n}\n\n'
Z8_NEW = 'void Control::insertTickVertical() {\n    createFloatingMark(this, win->getXournal(), {{0, -TICK_MARK_SIZE}, {0, TICK_MARK_SIZE}});\n}\n\nvoid Control::insertArrowHead() {\n    // A simple upward-pointing chevron/arrowhead ("^"), drawn as a single continuous 2-segment\n    // stroke: bottom-left leg end -> tip -> bottom-right leg end. Document Y grows downward, so the\n    // tip (pointing up) has the most negative Y offset of the three points. Patch 15.2/15.3: the\n    // object\'s bounding-box center (not the tip) is its single snappable anchor - see EditSelection\'s\n    // own handling of it.\n    createFloatingMark(this, win->getXournal(),\n                        {{-ARROWHEAD_SIZE, ARROWHEAD_SIZE},\n                         {0, -ARROWHEAD_SIZE},\n                         {ARROWHEAD_SIZE, ARROWHEAD_SIZE}},\n                        true);\n}\n\n'
Z9_OLD = '    void setStrokeCapStyle(const StrokeCapStyle capStyle);\n\n    [[maybe_unused]] void debugPrint() const;\n\n'
Z9_NEW = '    void setStrokeCapStyle(const StrokeCapStyle capStyle);\n\n    /**\n     * Patch 15.2: true for a stroke created as an arrowhead mark (Control::insertArrowHead(), Ctrl+L)\n     * - its bounding-box center is treated as a single snappable\n     * anchor point: while this stroke is being moved, that point magnetically snaps to the nearest\n     * point along any other stroke\'s own path (no guideline shown, unlike alignment_snap - see\n     * EditSelection). Persisted to the .xopp file (SaveHandler/XmlParser) so the behavior survives a\n     * save/reload, and copied on clone()/copy-paste, but intentionally NOT copied by\n     * applyStyleFrom() - it identifies this specific stroke, it isn\'t a reusable visual style.\n     */\n    bool hasSnappableTip() const;\n    void setHasSnappableTip(bool value);\n\n    /**\n     * Patch 15.6: whether this arrowhead mark is currently in "inverted" mode, toggled by pressing R\n     * while it is selected (see EditSelection::toggleArrowHeadInvert()). Meaningless unless\n     * hasSnappableTip() is also true. When false ("normal"): an unsnapped arrowhead points up, and a\n     * newly-snapped one is oriented by the shortest counterclockwise rotation from up. When true\n     * ("inverted"): an unsnapped arrowhead points down instead, and a newly-snapped one is oriented by\n     * the shortest CLOCKWISE rotation from down instead - see EditSelection::snapArrowHeadTip().\n     * Persisted to the .xopp file (SaveHandler/XmlParser), and copied on clone()/copy-paste, but\n     * intentionally NOT copied by applyStyleFrom() - same reasoning as hasSnappableTip() above.\n     */\n    bool isArrowHeadInverted() const;\n    void setArrowHeadInverted(bool value);\n\n    [[maybe_unused]] void debugPrint() const;\n\n'
Z10_OLD = '\n    StrokeCapStyle capStyle = StrokeCapStyle::ROUND;\n};\n'
Z10_NEW = "\n    StrokeCapStyle capStyle = StrokeCapStyle::ROUND;\n\n    /// Patch 15.2: see hasSnappableTip()'s own doc comment above.\n    bool snappableTip = false;\n\n    /// Patch 15.6: see isArrowHeadInverted()'s own doc comment above.\n    bool arrowHeadInverted = false;\n};\n"
Z11_OLD = '    s->snappedBounds = this->snappedBounds;\n    s->sizeCalculated = this->sizeCalculated;\n    return s;\n}\n'
Z11_NEW = '    s->snappedBounds = this->snappedBounds;\n    s->sizeCalculated = this->sizeCalculated;\n    s->snappableTip = this->snappableTip;\n    s->arrowHeadInverted = this->arrowHeadInverted;\n    return s;\n}\n'
Z12_OLD = '    out.writeInt(this->capStyle);\n\n    out.writeData(this->points.data(), this->points.size(), sizeof(Point));\n\n'
Z12_NEW = '    out.writeInt(this->capStyle);\n\n    out.writeInt(this->snappableTip ? 1 : 0);\n\n    out.writeInt(this->arrowHeadInverted ? 1 : 0);\n\n    out.writeData(this->points.data(), this->points.size(), sizeof(Point));\n\n'
Z13_OLD = '\n    this->capStyle = static_cast<StrokeCapStyle::Value>(in.readInt());\n\n    in.readData(this->points);\n'
Z13_NEW = '\n    this->capStyle = static_cast<StrokeCapStyle::Value>(in.readInt());\n\n    this->snappableTip = in.readInt() != 0;\n\n    this->arrowHeadInverted = in.readInt() != 0;\n\n    in.readData(this->points);\n'
Z14_OLD = 'void Stroke::setStrokeCapStyle(const StrokeCapStyle capStyle) { this->capStyle = capStyle; }\n\nvoid Stroke::debugPrint() const {\n    g_message("%s", FC(FORMAT_STR("Stroke {1} / hasPressure() = {2}") % (int64_t)this % this->hasPressure()));\n'
Z14_NEW = 'void Stroke::setStrokeCapStyle(const StrokeCapStyle capStyle) { this->capStyle = capStyle; }\n\nauto Stroke::hasSnappableTip() const -> bool { return this->snappableTip; }\n\nvoid Stroke::setHasSnappableTip(bool value) { this->snappableTip = value; }\n\nauto Stroke::isArrowHeadInverted() const -> bool { return this->arrowHeadInverted; }\n\nvoid Stroke::setArrowHeadInverted(bool value) { this->arrowHeadInverted = value; }\n\nvoid Stroke::debugPrint() const {\n    g_message("%s", FC(FORMAT_STR("Stroke {1} / hasPressure() = {2}") % (int64_t)this % this->hasPressure()));\n'
Z15_OLD = '\n    /**\n     * Get the cursor type for the current position (if 0 then the default cursor should be used)\n     */\n'
Z15_NEW = '\n    /**\n     * Patch 15.6: if this selection is a single Stroke with hasSnappableTip() (an arrowhead mark),\n     * toggles its "inverted" mode (Stroke::setArrowHeadInverted()) and immediately rotates it by 180\n     * degrees (this->rotation += pi) to match. Returns true if applied (there was a single arrowhead\n     * selected), false otherwise (nothing to do - the caller can then let the key press fall through\n     * to whatever it would otherwise do). Public: called from XournalView::onKeyPressEvent() on "R".\n     */\n    bool toggleArrowHeadInvert();\n\n    /**\n     * Get the cursor type for the current position (if 0 then the default cursor should be used)\n     */\n'
Z16_OLD = '\n    /**\n     * Gets the PageView under the cursor\n     */\n'
Z16_NEW = '\n    /**\n     * Patch 15.2/15.5: if this selection is a single Stroke with hasSnappableTip() (an arrowhead\n     * mark, see Control::insertArrowHead()), its bounding-box center is a single snappable anchor\n     * point: whenever the selection is moved, that point magnetically snaps to the nearest point\n     * along any other stroke\'s own path on the source layer (found by projecting the tip onto every\n     * line segment of every other stroke, clamped to the segment, and keeping the closest result\n     * overall), within a fixed pixel tolerance - no guideline is drawn for this, unlike\n     * alignment_snap. Given the proposed (dx, dy) translation, adjusts it in place so the tip lands\n     * exactly on the nearest qualifying point, if one is close enough; otherwise leaves it untouched.\n     *\n     * Patch 15.5: also keeps the arrowhead\'s own orientation (this->rotation) in sync with the\n     * tangent direction of whichever segment it is currently snapped to, imagining an invisible\n     * vector from the object\'s center to its own tip:\n     * - Not snapped: orientation resets to "pointing up" (this->rotation = 0, its as-drawn\n     *   orientation).\n     * - Newly snapped (was not snapped on the previous call): of the segment\'s two possible tangent\n     *   directions (180 degrees apart), the one reached by the shortest counterclockwise rotation\n     *   starting from "up" is used.\n     * - Remains snapped (was already snapped on the previous call, whether to the same point or a\n     *   different one reached by continuing to drag along the stroke(s)): of the two tangent\n     *   directions, the one closest to the arrowhead\'s current orientation is used instead, so it\n     *   never suddenly flips 180 degrees while being dragged smoothly along a line.\n     */\n    void snapArrowHeadTip(double& dx, double& dy);\n\n    /**\n     * Gets the PageView under the cursor\n     */\n'
Z17_OLD = '    double y{};\n    double rotation = 0;\n\n    /**\n'
Z17_NEW = "    double y{};\n    double rotation = 0;\n\n    /// Patch 15.5: tracks whether the arrowhead's single anchor point was snapped to another\n    /// stroke on the PREVIOUS call to snapArrowHeadTip() - see that method's own doc comment.\n    bool arrowHeadWasSnapped = false;\n\n    /**\n"
Z18_OLD = '    this->edgePanHandler.cancel();\n    finalizeSelection();\n}\n\n'
Z18_NEW = '    this->edgePanHandler.cancel();\n    finalizeSelection();\n}\n\n/**\n * Patch 15.2: pixel tolerance (in document points, independent of zoom) within which the arrowhead\'s\n * tip snaps to the nearest point on another stroke\'s path. Deliberately a plain, independent\n * constant here - not shared with alignment_snap\'s own tolerance setting (if that separate,\n * independent patch series happens to be applied too), since this is an unrelated snapping\n * mechanism (a single point onto a stroke\'s path, not a bounding box edge/center onto another\'s).\n */\nconstexpr double ARROWHEAD_SNAP_TOLERANCE = 8.0;\n\n/**\n * Returns the closest point to `p` lying on the segment [a, b] (clamped to the segment, not the\n * infinite line through it).\n */\nstatic auto closestPointOnSegment(const Point& p, const Point& a, const Point& b) -> Point {\n    double abx = b.x - a.x;\n    double aby = b.y - a.y;\n    double lengthSq = abx * abx + aby * aby;\n    if (lengthSq < 1e-9) {\n        return a;  // degenerate (zero-length) segment\n    }\n    double t = ((p.x - a.x) * abx + (p.y - a.y) * aby) / lengthSq;\n    t = std::clamp(t, 0.0, 1.0);\n    return Point(a.x + t * abx, a.y + t * aby);\n}\n\n/// Normalizes an angle, in radians, into (-pi, pi].\nstatic auto normalizeAngle(double a) -> double {\n    while (a <= -M_PI) {\n        a += 2 * M_PI;\n    }\n    while (a > M_PI) {\n        a -= 2 * M_PI;\n    }\n    return a;\n}\n\n/**\n * Patch 15.11: true if the given raw direction angle (atan2(dy, dx), this document\'s Y-down space)\n * falls within the "normal" (non-inverted) arrowhead mode\'s allowed half of the compass - visually:\n * from just past "left" (exclusive) through "up" to "right" (inclusive). The complementary half (used\n * when the arrowhead is in "inverted" mode, see Stroke::isArrowHeadInverted()) is everything else:\n * from just past "right" (exclusive) through "down" to "left" (inclusive). The two halves are exact\n * diametric opposites of one another, split along the horizontal ("left"-"right") axis.\n */\nstatic auto isNormalModeAngle(double rawAngle) -> bool {\n    constexpr double UP = -(M_PI / 2);\n    double rel = normalizeAngle(rawAngle - UP);\n    return rel > -(M_PI / 2) && rel <= (M_PI / 2);\n}\n\nvoid EditSelection::snapArrowHeadTip(double& dx, double& dy) {\n    auto elements = this->getElementsView();\n    if (elements.size() != 1) {\n        return;\n    }\n    const auto* stroke = dynamic_cast<const Stroke*>(*elements.begin());\n    if (!stroke || !stroke->hasSnappableTip() || stroke->getPointCount() < 3) {\n        return;\n    }\n\n    // Patch 15.4: CORRECTIF - EditSelection\'s own (x, y, width, height) is a PADDED view of the\n    // element\'s true bounds (see the constructor: a fixed 12-point margin added symmetrically on\n    // every side, "so anchors do not collapse even for horizontal/vertical strokes"). Mixing this\n    // padded x/y with the stroke\'s own unpadded getElementWidth()/Height() (patch 15.3\'s bug) shifted\n    // the computed center away from the true visual center by roughly that padding amount. Since the\n    // padding is symmetric, using this->width/height instead (which carry that exact same padding)\n    // cancels it out correctly: this->x + this->width / 2 always equals the element\'s own true\n    // center, regardless of the padding\'s actual value.\n    Point prospectiveTip{this->x + this->width / 2 + dx, this->y + this->height / 2 + dy};\n\n    Point best = prospectiveTip;\n    Point bestSegA{};\n    Point bestSegB{};\n    double bestDistSq = ARROWHEAD_SNAP_TOLERANCE * ARROWHEAD_SNAP_TOLERANCE;\n    bool found = false;\n    for (auto& elPtr: this->sourceLayer->getElements()) {\n        const Element* other = elPtr.get();\n        if (other == stroke) {\n            continue;\n        }\n        const auto* otherStroke = dynamic_cast<const Stroke*>(other);\n        if (!otherStroke) {\n            continue;\n        }\n        const auto& pts = otherStroke->getPointVector();\n        for (size_t i = 0; i + 1 < pts.size(); ++i) {\n            Point candidate = closestPointOnSegment(prospectiveTip, pts[i], pts[i + 1]);\n            double ddx = candidate.x - prospectiveTip.x;\n            double ddy = candidate.y - prospectiveTip.y;\n            double distSq = ddx * ddx + ddy * ddy;\n            if (distSq < bestDistSq) {\n                bestDistSq = distSq;\n                best = candidate;\n                bestSegA = pts[i];\n                bestSegB = pts[i + 1];\n                found = true;\n            }\n        }\n    }\n\n    if (found) {\n        dx += best.x - prospectiveTip.x;\n        dy += best.y - prospectiveTip.y;\n    }\n\n    // Patch 15.5/15.6: keep the arrowhead\'s own orientation in sync with the tangent of whichever\n    // segment it is (now) snapped to - see this method\'s own doc comment in the header for the full\n    // rule.\n    //\n    // Patch 15.9: CORRECTIF - the invisible vector (center to tip) must always be the reference for\n    // "up"/"down"/direction, which means it must be measured from the stroke\'s OWN CURRENT raw\n    // points, not assumed to always be -pi/2 ("up"). That assumption only holds for a\n    // freshly-spawned arrowhead: once a previous rotate-and-finalize cycle has baked a rotation into\n    // the raw points (from an earlier drag-and-snap, or an earlier "R" press), the raw tip no longer\n    // points up on its own - and this->rotation resets to 0 on every brand-new EditSelection (e.g.\n    // right after a deselect then re-select), so treating it as "relative to a fixed up" produced a\n    // mismatched orientation as soon as the arrowhead was re-selected. rawTipAngle below is\n    // recomputed fresh every time instead, directly from the three points as they currently stand.\n    constexpr double UP_ABS = -(M_PI / 2);\n    constexpr double DOWN_ABS = M_PI / 2;\n    bool inverted = stroke->isArrowHeadInverted();\n    Point rawTip = stroke->getPoint(1);\n    Point rawLegA = stroke->getPoint(0);\n    Point rawLegB = stroke->getPoint(2);\n    Point rawCenter{(rawLegA.x + rawLegB.x) / 2, (rawLegA.y + rawLegB.y) / 2};\n    double rawTipAngle = std::atan2(rawTip.y - rawCenter.y, rawTip.x - rawCenter.x);\n    if (!found) {\n        this->rotation = (inverted ? DOWN_ABS : UP_ABS) - rawTipAngle;\n        this->arrowHeadWasSnapped = false;\n        return;\n    }\n\n    double tangentA = std::atan2(bestSegB.y - bestSegA.y, bestSegB.x - bestSegA.x);\n    double tangentB = normalizeAngle(tangentA + M_PI);\n    double chosen;\n    if (!this->arrowHeadWasSnapped) {\n        // Patch 15.11: pick whichever of the two colinear tangent directions actually points within\n        // the current mode\'s allowed half of the compass (see isNormalModeAngle()\'s own doc comment).\n        // Since that allowed half and its "inverted" complement are two exact diametric halves, and\n        // tangentA/tangentB are themselves always exactly 180 degrees apart, exactly one of the two is\n        // ever compliant with the current mode - the other is always compliant with the opposite mode.\n        // This replaces the previous "shortest rotation from up (normal) / down (inverted)" heuristic\n        // (patch 15.5/15.6), which could pick a direction violating the mode\'s allowed half.\n        bool tangentAOk = inverted ? !isNormalModeAngle(tangentA) : isNormalModeAngle(tangentA);\n        chosen = tangentAOk ? tangentA : tangentB;\n    } else {\n        // Remains snapped: whichever of the two tangent directions is closest to the current\n        // orientation, so it never suddenly flips 180 degrees while being dragged along a line.\n        // Same rule regardless of inverted mode - only the initial choice above differs by mode.\n        double currentOrientation = normalizeAngle(this->rotation + rawTipAngle);\n        double diffA = std::abs(normalizeAngle(tangentA - currentOrientation));\n        double diffB = std::abs(normalizeAngle(tangentB - currentOrientation));\n        chosen = diffA <= diffB ? tangentA : tangentB;\n    }\n    this->rotation = chosen - rawTipAngle;\n    this->arrowHeadWasSnapped = true;\n}\n\n/**\n * Patch 15.6: see this method\'s own doc comment in the header.\n */\nauto EditSelection::toggleArrowHeadInvert() -> bool {\n    auto elements = this->getElementsView();\n    if (elements.size() != 1) {\n        return false;\n    }\n    // Patch 15.7: CORRECTIF - getElementsView()\'s iterator actually yields "const Element*" (despite\n    // the container\'s own template argument saying "Element*" - the const-ness is propagated by the\n    // const-qualified accessor method itself), so a direct dynamic_cast<Stroke*> doesn\'t compile\n    // (casting away constness). The underlying Stroke is genuinely mutable here (this same object is\n    // freely mutated elsewhere, e.g. in finalizeSelection()), so a const_cast on top of a const\n    // dynamic_cast is safe and standard practice for this situation.\n    const auto* constStroke = dynamic_cast<const Stroke*>(*elements.begin());\n    auto* stroke = const_cast<Stroke*>(constStroke);\n    if (!stroke || !stroke->hasSnappableTip()) {\n        return false;\n    }\n    stroke->setArrowHeadInverted(!stroke->isArrowHeadInverted());\n    this->rotation = normalizeAngle(this->rotation + M_PI);\n    this->view->getXournal()->repaintSelection();\n    return true;\n}\n\n'
Z19_OLD = '        // move\n        if (!this->edgePanInhibitNext) {\n            moveSelection(p.x - cx, p.y - cy);\n            this->setEdgePan(true);\n        } else {\n'
Z19_NEW = "        // move\n        if (!this->edgePanInhibitNext) {\n            double moveDx = p.x - cx;\n            double moveDy = p.y - cy;\n            // Patch 15.2: possibly adjusts the move so an arrowhead's tip lands on the nearest point\n            // of another stroke's path - a no-op for any other kind of selection.\n            snapArrowHeadTip(moveDx, moveDy);\n            moveSelection(moveDx, moveDy);\n            this->setEdgePan(true);\n        } else {\n"
Z20_OLD = 'constexpr auto CAPSTYLE_STR = u8"capStyle";\n'
Z20_NEW = 'constexpr auto CAPSTYLE_STR = u8"capStyle";\n/// Patch 15.2: see Stroke::hasSnappableTip()\'s own doc comment.\nconstexpr auto SNAPPABLE_TIP_STR = u8"snappableTip";\n/// Patch 15.6: see Stroke::isArrowHeadInverted()\'s own doc comment.\nconstexpr auto ARROWHEAD_INVERTED_STR = u8"arrowHeadInverted";\n'
Z21_OLD = '    if (s->getLineStyle().hasDashes()) {\n        stroke->setAttrib(xoj::xml_attrs::STYLE_STR, StrokeStyle::formatStyle(s->getLineStyle()));\n    }\n}\n'
Z21_NEW = '    if (s->getLineStyle().hasDashes()) {\n        stroke->setAttrib(xoj::xml_attrs::STYLE_STR, StrokeStyle::formatStyle(s->getLineStyle()));\n    }\n\n    // Patch 15.2: only written for strokes that actually have it, same convention as FILL_STR/STYLE_STR\n    // above, to avoid bloating every stroke\'s XML with an attribute only relevant to arrowhead marks.\n    if (s->hasSnappableTip()) {\n        stroke->setAttrib(xoj::xml_attrs::SNAPPABLE_TIP_STR, "true");\n    }\n\n    // Patch 15.6: same convention - only written when actually inverted.\n    if (s->isArrowHeadInverted()) {\n        stroke->setAttrib(xoj::xml_attrs::ARROWHEAD_INVERTED_STR, "true");\n    }\n}\n'
Z22_OLD = 'fs::path filename, size_t timestamp) = 0;\n    virtual void setStrokePoints(std::vector<Point> pointVector, bool hasPressure) = 0;\n'
Z22_NEW = 'fs::path filename, size_t timestamp,\n                           bool snappableTip = false, bool arrowHeadInverted = false) = 0;\n    virtual void setStrokePoints(std::vector<Point> pointVector, bool hasPressure) = 0;\n'
Z23_OLD = 'fs::path filename, size_t timestamp) override;\n    void setStrokePoints(std::vector<Point> pointVector, bool hasPressure) override;\n'
Z23_NEW = 'fs::path filename, size_t timestamp,\n                   bool snappableTip = false, bool arrowHeadInverted = false) override;\n    void setStrokePoints(std::vector<Point> pointVector, bool hasPressure) override;\n'
Z24_OLD = 'fs::path filename, size_t timestamp) {\n    xoj_assert(!this->stroke);\n'
Z24_NEW = 'fs::path filename, size_t timestamp, bool snappableTip,\n                            bool arrowHeadInverted) {\n    xoj_assert(!this->stroke);\n'
Z25_OLD = 'this->stroke->setLineStyle(lineStyle);\n\n    setAudioAttributes(*this->stroke, std::move(filename), timestamp);\n'
Z25_NEW = 'this->stroke->setLineStyle(lineStyle);\n    this->stroke->setHasSnappableTip(snappableTip);\n    this->stroke->setArrowHeadInverted(arrowHeadInverted);\n\n    setAudioAttributes(*this->stroke, std::move(filename), timestamp);\n'
Z26_OLD = '            XmlParserHelper::getAttribMandatory<LineStyle>(xoj::xml_attrs::STYLE_STR, attributeMap, {}, false);\n\n    // audio filename and timestamp\n    const auto optFilename = XmlParserHelper::getAttrib<fs::path>(xoj::xml_attrs::AUDIO_FILENAME_STR, attributeMap);\n'
Z26_NEW = '            XmlParserHelper::getAttribMandatory<LineStyle>(xoj::xml_attrs::STYLE_STR, attributeMap, {}, false);\n\n    // Patch 15.2: snappable tip marker (arrowhead marks) - optional, absent for every ordinary stroke.\n    const auto snappableTipSV =\n            XmlParserHelper::getAttrib<std::string_view>(xoj::xml_attrs::SNAPPABLE_TIP_STR, attributeMap);\n    const bool snappableTip = snappableTipSV.has_value() && *snappableTipSV == "true";\n\n    // Patch 15.6: "inverted" arrowhead marker - optional, absent unless the user pressed R.\n    const auto arrowHeadInvertedSV =\n            XmlParserHelper::getAttrib<std::string_view>(xoj::xml_attrs::ARROWHEAD_INVERTED_STR, attributeMap);\n    const bool arrowHeadInverted = arrowHeadInvertedSV.has_value() && *arrowHeadInvertedSV == "true";\n\n    // audio filename and timestamp\n    const auto optFilename = XmlParserHelper::getAttrib<fs::path>(xoj::xml_attrs::AUDIO_FILENAME_STR, attributeMap);\n'
Z27_OLD = 'this->tempTimestamp);\n\n    // Reset timestamp, filename was already moved from\n'
Z27_NEW = 'this->tempTimestamp, snappableTip, arrowHeadInverted);\n\n    // Reset timestamp, filename was already moved from\n'
Z28_OLD = '            clearSelection();\n            return true;\n        }\n\n'
Z28_NEW = '            clearSelection();\n            return true;\n        }\n\n        // Patch 15.6: R toggles an arrowhead mark\'s "inverted" mode (see\n        // EditSelection::toggleArrowHeadInvert()\'s own doc comment) - a no-op, falling through to\n        // whatever else "R" might otherwise do, if the selection isn\'t a single arrowhead.\n        if (keyval == GDK_KEY_r || keyval == GDK_KEY_R) {\n            if (selection->toggleArrowHeadInvert()) {\n                return true;\n            }\n        }\n\n'

FILES = [
    ("src/core/enums/Action.enum.h", [
        (Z1_OLD, Z1_NEW, "zone 1/1"),
    ]),
    ("src/core/enums/generated/Action.NameMap.generated.h", [
        (Z2_OLD, Z2_NEW, "zone 1/1"),
    ]),
    ("src/core/control/actions/ActionProperties.h", [
        (Z3_OLD, Z3_NEW, "zone 1/1"),
    ]),
    ("src/core/control/Control.h", [
        (Z4_OLD, Z4_NEW, "zone 1/1"),
    ]),
    ("src/core/control/Control.cpp", [
        (Z5_OLD, Z5_NEW, "zone 1/4"),
        (Z6_OLD, Z6_NEW, "zone 2/4"),
        (Z7_OLD, Z7_NEW, "zone 3/4"),
        (Z8_OLD, Z8_NEW, "zone 4/4"),
    ]),
    ("src/core/model/Stroke.h", [
        (Z9_OLD, Z9_NEW, "zone 1/2"),
        (Z10_OLD, Z10_NEW, "zone 2/2"),
    ]),
    ("src/core/model/Stroke.cpp", [
        (Z11_OLD, Z11_NEW, "zone 1/4"),
        (Z12_OLD, Z12_NEW, "zone 2/4"),
        (Z13_OLD, Z13_NEW, "zone 3/4"),
        (Z14_OLD, Z14_NEW, "zone 4/4"),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        (Z15_OLD, Z15_NEW, "zone 1/3"),
        (Z16_OLD, Z16_NEW, "zone 2/3"),
        (Z17_OLD, Z17_NEW, "zone 3/3"),
    ]),
    ("src/core/control/tools/EditSelection.cpp", [
        (Z18_OLD, Z18_NEW, "zone 1/2"),
        (Z19_OLD, Z19_NEW, "zone 2/2"),
    ]),
    ("src/core/control/xojfile/XmlAttrs.h", [
        (Z20_OLD, Z20_NEW, "zone 1/1"),
    ]),
    ("src/core/control/xojfile/SaveHandler.cpp", [
        (Z21_OLD, Z21_NEW, "zone 1/1"),
    ]),
    ("src/core/control/xojfile/DocumentBuilderInterface.h", [
        (Z22_OLD, Z22_NEW, "zone 1/1"),
    ]),
    ("src/core/control/xojfile/LoadHandler.h", [
        (Z23_OLD, Z23_NEW, "zone 1/1"),
    ]),
    ("src/core/control/xojfile/LoadHandler.cpp", [
        (Z24_OLD, Z24_NEW, "zone 1/2"),
        (Z25_OLD, Z25_NEW, "zone 2/2"),
    ]),
    ("src/core/control/xojfile/XmlParser.cpp", [
        (Z26_OLD, Z26_NEW, "zone 1/2"),
        (Z27_OLD, Z27_NEW, "zone 2/2"),
    ]),
    ("src/core/gui/XournalView.cpp", [
        (Z28_OLD, Z28_NEW, "zone 1/1"),
    ]),
]


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {path}: {label}: deja applique.")
            return True
        print(f"[ECHEC] {path}: {label}: motif introuvable")
        return False
    if count > 1:
        print(f"[ECHEC] {path}: {label}: motif trouve {count} fois (doit etre unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {path}: {label}")
    return True


def main():
    for filename, _ in FILES:
        if not Path(filename).exists():
            print(f"[ECHEC] Fichier introuvable : {filename}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)

    marker_h = Path("src/core/control/tools/EditSelection.h").read_text(encoding="utf-8")
    marker_cpp = Path("src/core/control/tools/EditSelection.cpp").read_text(encoding="utf-8")
    if "toggleArrowHeadInvert" in marker_h and "isNormalModeAngle" in marker_cpp:
        print("[SKIP] Le patch 15.0v2 (ou la serie 15.1-15.11 equivalente) semble deja applique.")
        sys.exit(0)

    ok = True
    for filename, zone_defs in FILES:
        p = Path(filename)
        for old, new, label in zone_defs:
            ok &= apply_edit(p, old, new, label)

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
