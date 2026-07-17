#!/usr/bin/env python3
"""
apply_alignment_snap_v90_5.py : version consolidee, fusionnant
l'integralite du process alignment_snap actuel (v90_4 + 11.8 + 11.9 +
11.10 + 11.10.1 + 11.10.2) en un seul script.

NOTE IMPORTANTE : contrairement a v90_4, cette version 90.5 N'INCLUT
PAS les patchs 11.6 et 11.7 (retires volontairement du process par
l'utilisateur).

Reste DEPENDANT de apply_arrow_resize_fix_v2.py, qui doit toujours
etre applique separement AVANT ce script (non fusionne).

Contenu (dans l'ordre) :
  v90_4    : consolidation majeure - systeme d'accroche magnetique aux
             objets (paliers ordinaire/boste/page-centree/graduation),
             correctifs de motif de tirets, direction des fleches,
             desaccrochage de grille non-equidistante, couleurs de
             guidelines
  11.8     : correctif du snap de spline au clic initial
  11.9     : nouveau cas pour l'alignement jaune (case a 3 bords)
  11.10    : cadre "Anchoring assistance" dans les Preferences +
             correctif "plus petite case" pour table centering assist
             + tolerance "Circle assist" par defaut 15.0 + gating de
             coordinate system/circle/spline assist sur le snapping
             global
  11.10.1  : correctif de compilation (setObjectAlignmentSnapping
             protected)
  11.10.2  : correctif de comportement (les cases a cocher ne doivent
             pas se decocher quand le snapping global est desactive)

Modifie :
  - po/fr.po, po/xournalpp.pot
  - src/core/control/Control.cpp / .h
  - src/core/control/actions/ActionProperties.h
  - src/core/control/settings/Settings.cpp / .h
  - src/core/control/tools/ArrowHandler.cpp
  - src/core/control/tools/BaseShapeHandler.cpp / .h
  - src/core/control/tools/EditSelection.cpp / .h
  - src/core/control/tools/EllipseHandler.cpp
  - src/core/control/tools/RulerHandler.cpp
  - src/core/control/tools/SplineHandler.cpp / .h
  - src/core/enums/Action.enum.h
  - src/core/enums/generated/Action.NameMap.generated.h
  - src/core/gui/dialog/SettingsDialog.cpp / .h
  - src/core/model/Stroke.cpp
  - src/core/view/overlays/ShapeToolView.cpp
  - src/core/view/overlays/SplineToolView.cpp
  - ui/mainmenubar.xml, ui/settings.glade
  - src/core/undo/LineRepositionUndoAction.h / .cpp (nouveaux fichiers)

Independant des series table_writing_assist et completion LaTeX, et
des patchs 14.X / 15.X.

NECESSITE : apply_arrow_resize_fix_v2.py (applique separement,
AVANT ce script).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus) :

  git clone https://github.com/xournalpp/xournalpp.git
  cd xournalpp
  git checkout 209481caee183798fcae151d125c1ea2d0317b3b
  python3 apply_arrow_resize_fix_v2.py
  python3 apply_alignment_snap_v90_5.py

Sur un depot vierge (ou tout du moins sans qu'aucun patch individuel
de cette serie n'ait deja ete applique).
"""
import sys
from pathlib import Path

NEW_FILE_H = """/*
 * Xournal++
 *
 * Undo action for the \"line reposition on release\" feature (see EditSelection.cpp, patch 8.6.4.5):
 * translates a set of elements, each by its own individual delta along a single axis (X or Y),
 * without ever changing their size. Used to move every same-length line crossing a big perpendicular
 * line so that the correct edge (or center) - depending on the current Top/Middle/Below zone - lands
 * exactly on that big line.
 *
 * @author Xournal++ Team
 * https://github.com/xournalpp/xournalpp
 *
 * @license GNU GPLv2 or later
 */

#pragma once

#include <string>   // for string
#include <utility>  // for pair
#include <vector>   // for vector

#include \"model/PageRef.h\"  // for PageRef

#include \"UndoAction.h\"  // for UndoAction

class Control;
class Document;
class Element;

class LineRepositionUndoAction: public UndoAction {
public:
    LineRepositionUndoAction(const PageRef& page, std::vector<std::pair<Element*, double>> elementsWithDelta,
                              bool isXAxis);
    ~LineRepositionUndoAction() override;

public:
    bool undo(Control* control) override;
    bool redo(Control* control) override;
    std::string getText() override;

private:
    void apply(double sign);

private:
    std::vector<std::pair<Element*, double>> elementsWithDelta;
    bool isXAxis;
};
"""
NEW_FILE_CPP = """#include \"LineRepositionUndoAction.h\"

#include <utility>  // for move

#include \"control/Control.h\"
#include \"model/Document.h\"
#include \"model/Element.h\"  // for Element
#include \"model/PageRef.h\"  // for PageRef
#include \"model/XojPage.h\"  // for XojPage
#include \"util/Range.h\"     // for Range
#include \"util/i18n.h\"      // for _

LineRepositionUndoAction::LineRepositionUndoAction(const PageRef& page,
                                                    std::vector<std::pair<Element*, double>> elementsWithDelta,
                                                    bool isXAxis):
        UndoAction(\"LineRepositionUndoAction\"), elementsWithDelta(std::move(elementsWithDelta)), isXAxis(isXAxis) {
    this->page = page;
}

LineRepositionUndoAction::~LineRepositionUndoAction() { this->page = nullptr; }

auto LineRepositionUndoAction::undo(Control* control) -> bool {
    apply(-1.0);
    this->undone = true;
    return true;
}

auto LineRepositionUndoAction::redo(Control* control) -> bool {
    apply(1.0);
    this->undone = false;
    return true;
}

void LineRepositionUndoAction::apply(double sign) {
    if (this->elementsWithDelta.empty()) {
        return;
    }

    Range r(elementsWithDelta.front().first->getX(), elementsWithDelta.front().first->getY());

    for (auto& [element, delta]: this->elementsWithDelta) {
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
        if (isXAxis) {
            element->move(sign * delta, 0);
        } else {
            element->move(0, sign * delta);
        }
        r.addPoint(element->getX(), element->getY());
        r.addPoint(element->getX() + element->getElementWidth(), element->getY() + element->getElementHeight());
    }

    this->page->fireRangeChanged(r);
}

auto LineRepositionUndoAction::getText() -> std::string { return _(\"Reposition aligned line\"); }
"""

FR_OLD0 = """msgid \"Grid Snapping\"
msgstr \"Ancrage à la grille\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"Pages liées\""""
FR_NEW0 = """msgid \"Grid Snapping\"
msgstr \"Ancrage à la grille\"

#: ../ui/mainmenubar.xml:159 ../ui/settings.glade:5766
msgid \"Object Alignment Snapping\"
msgstr \"Alignement des objets par ancrage\"

#: ../ui/settings.glade:5785
msgid \"Anchoring assistance\"
msgstr \"Aide à l'ancrage\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"Pages liées\""""
POT_OLD0 = """msgid \"Grid Snapping\"
msgstr \"\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"\""""
POT_NEW0 = """msgid \"Grid Snapping\"
msgstr \"\"

#: ../ui/mainmenubar.xml:159 ../ui/settings.glade:5766
msgid \"Object Alignment Snapping\"
msgstr \"\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"\""""
POT_OLD1 = """\"you have the shape recognizer turned on while writing.\"
msgstr \"\"

#: ../ui/settings.glade:5296
msgid \"Snapping\"
msgstr \"\"
"""
POT_NEW1 = """\"you have the shape recognizer turned on while writing.\"
msgstr \"\"

#: ../ui/settings.glade:5296 ../ui/settings.glade:6741
msgid \"Snapping\"
msgstr \"\"
"""
POT_OLD2 = """#: ../resources-templates/com.github.xournalpp.xournalpp.xml.in:12
msgid \"Xournal++ page template file\"
msgstr \"\""""
POT_NEW2 = """#: ../resources-templates/com.github.xournalpp.xournalpp.xml.in:12
msgid \"Xournal++ page template file\"
msgstr \"\"

#: ../ui/settings.glade:5766
msgid \"Equidistant assist\"
msgstr \"\"

#: ../ui/settings.glade:5785
msgid \"<i>Snaps a moved object into the same spacing as two other objects that are already evenly spaced apart.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5799
msgid \"Page centering assist\"
msgstr \"\"

#: ../ui/settings.glade:5818
msgid \"<i>Snaps an object to the horizontal center of the page.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5832
msgid \"Coordinate system assist\"
msgstr \"\"

#: ../ui/settings.glade:5851
msgid \"<i>While drawing a straight line or arrow, shows a guide and snaps to match the length of another line it crosses at a right angle.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5865
msgid \"Circle assist\"
msgstr \"\"

#: ../ui/settings.glade:5884
msgid \"<i>While drawing an ellipse, snaps its bounding box to a square, making a perfect circle.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5898
msgid \"Graduation assist\"
msgstr \"\"

#: ../ui/settings.glade:5917
msgid \"<i>Shows evenly spaced tick marks along a line already crossed by several perpendicular lines, and snaps to the nearest one.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5931
msgid \"Graduation orientation\"
msgstr \"\"

#: ../ui/settings.glade:5951
msgid \"<i>Allows switching between top, middle, and below anchoring by dragging the cursor along the line. When disabled, anchoring always uses the middle.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5965
msgid \"Table content centering assist\"
msgstr \"\"

#: ../ui/settings.glade:5984
msgid \"<i>Centers text or an image between two parallel lines of equal length, such as a table column or row.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5998
msgid \"Snapping when drawing a spline\"
msgstr \"\"

#: ../ui/settings.glade:6017
msgid \"<i>While drawing a spline, snaps its moving point to the edges and centers of nearby objects.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5785
msgid \"Anchoring assistance\"
msgstr \"\"

#: ../ui/settings.glade:6035
msgid \"Functionalities\"
msgstr \"\"

#: ../ui/settings.glade:6083
msgid \"Object alignment tolerance\"
msgstr \"\"

#: ../ui/settings.glade:6107 ../ui/settings.glade:6237
#: ../ui/settings.glade:6302 ../ui/settings.glade:6367
msgid \"(default: 6.0)\"
msgstr \"\"

#: ../ui/settings.glade:6126
msgid \"<i>The base tolerance, in screen pixels, within which an object's edges and center are considered aligned with another object's.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6148
msgid \"Text vertical center fraction\"
msgstr \"\"

#: ../ui/settings.glade:6172
msgid \"(default: 0.6)\"
msgstr \"\"

#: ../ui/settings.glade:6191
msgid \"<i>The vertical position (0 = top, 1 = bottom) within a text box used as its center for vertical alignment, since a text box's true geometric center often looks slightly off due to descender space.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6213
msgid \"Line crossing assist tolerance\"
msgstr \"\"

#: ../ui/settings.glade:6256
msgid \"<i>The tolerance, in screen pixels, used by the coordinate system assist (patch 8.4) when snapping a drawn line's length to match another line it crosses at a right angle.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6278
msgid \"Spline tool alignment tolerance\"
msgstr \"\"

#: ../ui/settings.glade:6321
msgid \"<i>The tolerance, in screen pixels, for the spline tool's own alignment snap (patch 8.9) - a separate setting from the general object alignment tolerance above.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6343
msgid \"Circle assist tolerance\"
msgstr \"\"

#: ../ui/settings.glade:6386
msgid \"<i>The tolerance, in screen pixels, within which an ellipse's width and height are considered close enough to snap to a perfect circle (patch 8.5).</i>\"
msgstr \"\"

#: ../ui/settings.glade:6404
msgid \"Normal\"
msgstr \"\"

#: ../ui/settings.glade:6438
msgid \"Perpendicular cross boost factor\"
msgstr \"\"

#: ../ui/settings.glade:6462
msgid \"(default: 4.0)\"
msgstr \"\"

#: ../ui/settings.glade:6481
msgid \"<i>Multiplier applied to the base alignment tolerance for the \\\"boosted\\\" (blue) tier's own matching tolerance and Top/Middle/Below zone radius, when a small line crosses a much bigger perpendicular one.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6503
msgid \"Line end anchor tolerance factor\"
msgstr \"\"

#: ../ui/settings.glade:6527
msgid \"(default: 0.9)\"
msgstr \"\"

#: ../ui/settings.glade:6546
msgid \"<i>Tolerance factor for snapping a small line to one of a big line's own two endpoints - deliberately smaller than the perpendicular cross boost factor, since this is a precise \\\"line up exactly with the end\\\" gesture.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6568
msgid \"Small mark max length\"
msgstr \"\"

#: ../ui/settings.glade:6592
msgid \"(default: 15.0)\"
msgstr \"\"

#: ../ui/settings.glade:6611
msgid \"<i>The maximum bounding-box side length, in document points, below which an object (like a tick or a cross mark) is treated as a \\\"small mark\\\" and forced to a single center-only anchor on both axes. For a plain line specifically, this same value also gates the \\\"boosted\\\" (blue) perpendicular-cross match and, in turn, line-end anchoring - non-line objects (including arrows) always use a fixed 15.0 for this rule instead.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6633
msgid \"Line crossing assist minimum length\"
msgstr \"\"

#: ../ui/settings.glade:6657
msgid \"(default: 50.0)\"
msgstr \"\"

#: ../ui/settings.glade:6676
msgid \"<i>The minimum length, in document points, a drawn line/arrow must already have - and a target line on the layer must have - for the coordinate system assist (patch 8.4) to consider them at all.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6694
msgid \"Advanced\"
msgstr \"\"

#: ../ui/settings.glade:6710
msgid \"Settings\"
msgstr \"\""""
CTRL_CPP_OLD0 = """    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);
}

auto Control::getTextEditor() -> TextEditor* {
    if (this->win) {
        return this->win->getXournal()->getTextEditor();"""
CTRL_CPP_NEW0 = """    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);
}

void Control::setObjectAlignmentSnapping(bool enable) {
    settings->setSnapToObjects(enable);
    this->actionDB->setActionState(Action::OBJECT_ALIGNMENT_SNAPPING, enable);
}

auto Control::getTextEditor() -> TextEditor* {
    if (this->win) {
        return this->win->getXournal()->getTextEditor();"""
CTRL_H_OLD0 = """protected:
    void setRotationSnapping(bool enable);
    void setGridSnapping(bool enable);

    void showFontDialog();
    void showColorChooserDialog();"""
CTRL_H_NEW0 = """protected:
    void setRotationSnapping(bool enable);
    void setGridSnapping(bool enable);
    void setObjectAlignmentSnapping(bool enable);

    void showFontDialog();
    void showColorChooserDialog();"""
ACTPROPS_OLD0 = """};

template <>
struct ActionProperties<Action::PREFERENCES> {
    using app_namespace = std::true_type;
    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->showSettings(); }"""
ACTPROPS_NEW0 = """};

template <>
struct ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING> {
    using state_type = bool;
    static constexpr const char* accelerators[] = {\"<Ctrl>B\", nullptr};
    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapToObjects(); }
    static void callback(GSimpleAction* ga, GVariant* p, Control* ctrl) {
        g_simple_action_set_state(ga, p);
        bool enable = g_variant_get_boolean(p);
        ctrl->setObjectAlignmentSnapping(enable);
    }
};

template <>
struct ActionProperties<Action::PREFERENCES> {
    using app_namespace = std::true_type;
    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->showSettings(); }"""
SETTINGS_CPP_OLD0 = """    this->snapGrid = true;
    this->snapGridTolerance = 0.50;
    this->snapGridSize = DEFAULT_GRID_SIZE;

    this->strokeRecognizerMinSize = 40;
"""
SETTINGS_CPP_NEW0 = """    this->snapGrid = true;
    this->snapGridTolerance = 0.50;
    this->snapGridSize = DEFAULT_GRID_SIZE;
    this->snapToObjects = true;
    this->equidistantSnappingEnabled = true;
    this->pageCenteringSnappingEnabled = true;
    this->coordinateSystemAssistEnabled = true;
    this->circleAssistEnabled = true;
    this->graduationAssistEnabled = true;
    this->graduationOrientationEnabled = true;
    this->tableContentCenteringAssistEnabled = true;
    this->splineSnappingEnabled = true;
    this->alignmentSnapTolerancePx = 6.0;
    this->textYCenterFraction = 0.6;
    this->lineCrossSnapTolerancePx = 6.0;
    this->lineCrossMinLength = 50.0;
    this->splineAlignmentSnapTolerancePx = 6.0;
    this->diagonalSnapTolerancePx = 15.0;
    this->perpendicularCrossBoostFactor = 4.0;
    this->lineEndAnchorToleranceFactor = 0.9;
    this->smallMarkMaxLength = 15.0;

    this->strokeRecognizerMinSize = 40;
"""
SETTINGS_CPP_OLD1 = """        this->snapRotationTolerance = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGrid\")) == 0) {
        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridSize\")) == 0) {
        this->snapGridSize = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridTolerance\")) == 0) {"""
SETTINGS_CPP_NEW1 = """        this->snapRotationTolerance = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGrid\")) == 0) {
        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapToObjects\")) == 0) {
        this->snapToObjects = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"equidistantSnappingEnabled\")) == 0) {
        this->equidistantSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"pageCenteringSnappingEnabled\")) == 0) {
        this->pageCenteringSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"coordinateSystemAssistEnabled\")) == 0) {
        this->coordinateSystemAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"circleAssistEnabled\")) == 0) {
        this->circleAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationAssistEnabled\")) == 0) {
        this->graduationAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"graduationOrientationEnabled\")) == 0) {
        this->graduationOrientationEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"tableContentCenteringAssistEnabled\")) == 0) {
        this->tableContentCenteringAssistEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"splineSnappingEnabled\")) == 0) {
        this->splineSnappingEnabled = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"alignmentSnapTolerancePx\")) == 0) {
        this->alignmentSnapTolerancePx = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"textYCenterFraction\")) == 0) {
        this->textYCenterFraction = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"lineCrossSnapTolerancePx\")) == 0) {
        this->lineCrossSnapTolerancePx = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"lineCrossMinLength\")) == 0) {
        this->lineCrossMinLength = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"splineAlignmentSnapTolerancePx\")) == 0) {
        this->splineAlignmentSnapTolerancePx = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"diagonalSnapTolerancePx\")) == 0) {
        this->diagonalSnapTolerancePx = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"perpendicularCrossBoostFactor\")) == 0) {
        this->perpendicularCrossBoostFactor = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"lineEndAnchorToleranceFactor\")) == 0) {
        this->lineEndAnchorToleranceFactor = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"smallMarkMaxLength\")) == 0) {
        this->smallMarkMaxLength = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridSize\")) == 0) {
        this->snapGridSize = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridTolerance\")) == 0) {"""
SETTINGS_CPP_OLD2 = """    SAVE_BOOL_PROP(snapGrid);
    SAVE_DOUBLE_PROP(snapGridTolerance);
    SAVE_DOUBLE_PROP(snapGridSize);

    SAVE_DOUBLE_PROP(strokeRecognizerMinSize);
"""
SETTINGS_CPP_NEW2 = """    SAVE_BOOL_PROP(snapGrid);
    SAVE_DOUBLE_PROP(snapGridTolerance);
    SAVE_DOUBLE_PROP(snapGridSize);
    SAVE_BOOL_PROP(snapToObjects);
    SAVE_BOOL_PROP(equidistantSnappingEnabled);
    SAVE_BOOL_PROP(pageCenteringSnappingEnabled);
    SAVE_BOOL_PROP(coordinateSystemAssistEnabled);
    SAVE_BOOL_PROP(circleAssistEnabled);
    SAVE_BOOL_PROP(graduationAssistEnabled);
    SAVE_BOOL_PROP(graduationOrientationEnabled);
    SAVE_BOOL_PROP(tableContentCenteringAssistEnabled);
    SAVE_BOOL_PROP(splineSnappingEnabled);
    SAVE_DOUBLE_PROP(alignmentSnapTolerancePx);
    SAVE_DOUBLE_PROP(textYCenterFraction);
    SAVE_DOUBLE_PROP(lineCrossSnapTolerancePx);
    SAVE_DOUBLE_PROP(lineCrossMinLength);
    SAVE_DOUBLE_PROP(splineAlignmentSnapTolerancePx);
    SAVE_DOUBLE_PROP(diagonalSnapTolerancePx);
    SAVE_DOUBLE_PROP(perpendicularCrossBoostFactor);
    SAVE_DOUBLE_PROP(lineEndAnchorToleranceFactor);
    SAVE_DOUBLE_PROP(smallMarkMaxLength);

    SAVE_DOUBLE_PROP(strokeRecognizerMinSize);
"""
SETTINGS_CPP_OLD3 = """    save();
}

void Settings::setSnapGridTolerance(double tolerance) {
    this->snapGridTolerance = tolerance;
    save();"""
SETTINGS_CPP_NEW3 = """    save();
}

auto Settings::isSnapToObjects() const -> bool { return this->snapToObjects; }

void Settings::setSnapToObjects(bool b) {
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

auto Settings::isPageCenteringSnappingEnabled() const -> bool { return this->pageCenteringSnappingEnabled; }

void Settings::setPageCenteringSnappingEnabled(bool b) {
    if (this->pageCenteringSnappingEnabled == b) {
        return;
    }

    this->pageCenteringSnappingEnabled = b;
    save();
}

// Patch 11.10.2: CORRECTIF - reverted back to a plain pass-through of the raw stored value. Gating
// this getter itself on isSnapToObjects() (as patch 11.10 originally did) also affected
// SettingsDialog::load(), which uses this same getter to populate the checkbox's displayed state -
// unchecking it in the UI whenever the master toggle happened to be off, even if the user's own
// stored preference was still checked. The gating now happens at the actual call site instead (see
// BaseShapeHandler::applyLineCrossingSnap()), leaving this getter - and therefore the checkbox's own
// displayed/persisted state - entirely independent of isSnapToObjects().
auto Settings::isCoordinateSystemAssistEnabled() const -> bool { return this->coordinateSystemAssistEnabled; }

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {
        return;
    }

    this->coordinateSystemAssistEnabled = b;
    save();
}

// Patch 11.10.2: see isCoordinateSystemAssistEnabled()'s own comment just above.
auto Settings::isCircleAssistEnabled() const -> bool { return this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
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

auto Settings::isGraduationOrientationEnabled() const -> bool { return this->graduationOrientationEnabled; }

void Settings::setGraduationOrientationEnabled(bool b) {
    if (this->graduationOrientationEnabled == b) {
        return;
    }

    this->graduationOrientationEnabled = b;
    save();
}

auto Settings::isTableContentCenteringAssistEnabled() const -> bool {
    return this->tableContentCenteringAssistEnabled;
}

void Settings::setTableContentCenteringAssistEnabled(bool b) {
    if (this->tableContentCenteringAssistEnabled == b) {
        return;
    }

    this->tableContentCenteringAssistEnabled = b;
    save();
}

// Patch 11.10.2: see isCoordinateSystemAssistEnabled()'s own comment above (near line 1730).
auto Settings::isSplineSnappingEnabled() const -> bool { return this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {
        return;
    }

    this->splineSnappingEnabled = b;
    save();
}

auto Settings::getAlignmentSnapTolerancePx() const -> double { return this->alignmentSnapTolerancePx; }

void Settings::setAlignmentSnapTolerancePx(double d) {
    if (this->alignmentSnapTolerancePx == d) {
        return;
    }

    this->alignmentSnapTolerancePx = d;
    save();
}

auto Settings::getTextYCenterFraction() const -> double { return this->textYCenterFraction; }

void Settings::setTextYCenterFraction(double d) {
    if (this->textYCenterFraction == d) {
        return;
    }

    this->textYCenterFraction = d;
    save();
}

auto Settings::getLineCrossSnapTolerancePx() const -> double { return this->lineCrossSnapTolerancePx; }

void Settings::setLineCrossSnapTolerancePx(double d) {
    if (this->lineCrossSnapTolerancePx == d) {
        return;
    }

    this->lineCrossSnapTolerancePx = d;
    save();
}

auto Settings::getLineCrossMinLength() const -> double { return this->lineCrossMinLength; }

void Settings::setLineCrossMinLength(double d) {
    if (this->lineCrossMinLength == d) {
        return;
    }

    this->lineCrossMinLength = d;
    save();
}

auto Settings::getSplineAlignmentSnapTolerancePx() const -> double { return this->splineAlignmentSnapTolerancePx; }

void Settings::setSplineAlignmentSnapTolerancePx(double d) {
    if (this->splineAlignmentSnapTolerancePx == d) {
        return;
    }

    this->splineAlignmentSnapTolerancePx = d;
    save();
}

auto Settings::getDiagonalSnapTolerancePx() const -> double { return this->diagonalSnapTolerancePx; }

void Settings::setDiagonalSnapTolerancePx(double d) {
    if (this->diagonalSnapTolerancePx == d) {
        return;
    }

    this->diagonalSnapTolerancePx = d;
    save();
}

auto Settings::getPerpendicularCrossBoostFactor() const -> double { return this->perpendicularCrossBoostFactor; }

void Settings::setPerpendicularCrossBoostFactor(double d) {
    if (this->perpendicularCrossBoostFactor == d) {
        return;
    }

    this->perpendicularCrossBoostFactor = d;
    save();
}

auto Settings::getLineEndAnchorToleranceFactor() const -> double { return this->lineEndAnchorToleranceFactor; }

void Settings::setLineEndAnchorToleranceFactor(double d) {
    if (this->lineEndAnchorToleranceFactor == d) {
        return;
    }

    this->lineEndAnchorToleranceFactor = d;
    save();
}

auto Settings::getSmallMarkMaxLength() const -> double { return this->smallMarkMaxLength; }

void Settings::setSmallMarkMaxLength(double d) {
    if (this->smallMarkMaxLength == d) {
        return;
    }

    this->smallMarkMaxLength = d;
    save();
}

void Settings::setSnapGridTolerance(double tolerance) {
    this->snapGridTolerance = tolerance;
    save();"""
SETTINGS_H_OLD0 = """    double getSnapGridSize() const;
    void setSnapGridSize(double gridSize);

    double getStrokeRecognizerMinSize() const;
    void setStrokeRecognizerMinSize(double value);
"""
SETTINGS_H_NEW0 = """    double getSnapGridSize() const;
    void setSnapGridSize(double gridSize);

    bool isSnapToObjects() const;
    void setSnapToObjects(bool b);

    /// Patch 10.2: gates specifically the equidistant (\"equal spacing\") tier of the object alignment
    /// snapping system (see findEquidistantX/Y() in EditSelection.cpp), independently of the other
    /// tiers (ordinary, boosted, page-center, table-center, blue grid...). Only takes effect while
    /// isSnapToObjects() is also true - this is a finer-grained toggle nested under the master one,
    /// not a replacement for it.
    bool isEquidistantSnappingEnabled() const;
    void setEquidistantSnappingEnabled(bool b);

    /// Patch 10.3: gates specifically the page-centering tier of the object alignment snapping
    /// system (see computePageCenterX() in EditSelection.cpp), independently of the other tiers.
    /// Only takes effect while isSnapToObjects() is also true.
    bool isPageCenteringSnappingEnabled() const;
    void setPageCenteringSnappingEnabled(bool b);

    /// Patch 10.4: gates the line-crossing snap assist during shape drawing (see
    /// BaseShapeHandler::applyLineCrossingSnap(), patch 8.4). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

    /// Patch 10.5: gates the \"diagonal snap\" perfect-circle assist during ellipse drawing (see
    /// EllipseHandler::createShape(), patch 8.5). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);

    /// Patch 10.6A: gates the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
    /// behavior (see computeBlueGridX/Y() in EditSelection.cpp, patch 8.6). Does NOT affect the
    /// line-end anchors (patch 8.6.5), which always stay active as long as isSnapToObjects() is true.
    bool isGraduationAssistEnabled() const;
    void setGraduationAssistEnabled(bool b);

    /// Patch 10.6B: gates the ability to switch between Top/Middle/Below modes by dragging the
    /// cursor to a different zone (see the \"fresh line\" zone override in EditSelection.cpp, patch
    /// 8.6.6, and the raw cursor-based zone computation it builds on). If disabled, line anchoring
    /// always uses Middle mode, regardless of cursor position during the drag. Nested under
    /// isGraduationAssistEnabled() in the Preferences UI, but independently gated in code.
    bool isGraduationOrientationEnabled() const;
    void setGraduationOrientationEnabled(bool b);

    /// Patch 10.7: gates the \"table center\" tier (see findTableCenterX/Y() in EditSelection.cpp,
    /// patch 8.7.0) - centering a Text/TexImage/Image between two same-length parallel lines
    /// bounding a table column/row. Nested under snapToObjects.
    bool isTableContentCenteringAssistEnabled() const;
    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);

    /// Patch 10.10.2: the base tolerance (in screen pixels, independent of zoom) for the ordinary
    /// (green/pink) alignment snap tier - see ALIGNMENT_SNAP_TOLERANCE_PX's original role in
    /// EditSelection.cpp. Now user-configurable via Preferences instead of a compile-time constant.
    double getAlignmentSnapTolerancePx() const;
    void setAlignmentSnapTolerancePx(double d);

    /// Patch 10.10.2.2: the vertical fraction, within a Text element's own height, used as its
    /// \"center\" for the ordinary alignment snap tier's Y-axis matching - see TEXT_Y_CENTER_FRACTION's
    /// original role in EditSelection.cpp (findAlignmentY() only; horizontal centering always uses the
    /// true geometric 0.5, unaffected by this). Now user-configurable via Preferences.
    double getTextYCenterFraction() const;
    void setTextYCenterFraction(double d);

    /// Patch 10.10.2.3: tolerance (screen pixels) for the line-crossing snap assist during shape
    /// drawing - see LINE_CROSS_SNAP_TOLERANCE_PX's original role in BaseShapeHandler.cpp (patch 8.4).
    double getLineCrossSnapTolerancePx() const;
    void setLineCrossSnapTolerancePx(double d);

    /// Patch 10.10.4 (\"Advanced\"): minimum length (document points) a drawn line/arrow must already
    /// have, and a target line on the layer must have, for the coordinate system (line-crossing snap)
    /// assist to consider them at all - see LINE_CROSS_MIN_LENGTH's original role in
    /// BaseShapeHandler.cpp (patch 8.4).
    double getLineCrossMinLength() const;
    void setLineCrossMinLength(double d);

    /// Patch 10.10.2.4: tolerance (screen pixels) for the spline tool's ordinary (green/pink)
    /// alignment snap - see SplineHandler.cpp's own ALIGNMENT_SNAP_TOLERANCE_PX (patch 8.9), a
    /// SEPARATE constant from EditSelection.cpp's own getAlignmentSnapTolerancePx() above, despite
    /// sharing the same original name - labelled \"Spline tool alignment tolerance\" in Preferences to
    /// disambiguate.
    double getSplineAlignmentSnapTolerancePx() const;
    void setSplineAlignmentSnapTolerancePx(double d);

    /// Patch 10.10.2.5: tolerance (screen pixels) for the \"diagonal snap\" perfect-circle assist
    /// during ellipse drawing - see DIAGONAL_SNAP_TOLERANCE_PX's original role in EllipseHandler.cpp
    /// (patch 8.5).
    double getDiagonalSnapTolerancePx() const;
    void setDiagonalSnapTolerancePx(double d);

    /// Patch 10.10.2.6 (\"Advanced\"): multiplier applied to the base alignment tolerance for the
    /// \"boosted\" (blue) tier's own tolerance and Top/Middle/Below zone radius - see
    /// PERPENDICULAR_CROSS_BOOST_FACTOR's original role in EditSelection.cpp.
    double getPerpendicularCrossBoostFactor() const;
    void setPerpendicularCrossBoostFactor(double d);

    /// Patch 10.10.2.7 (\"Advanced\"): tolerance factor for snapping a small line to one of the big
    /// line's own two endpoints - see LINE_END_ANCHOR_TOLERANCE_FACTOR's original role in
    /// EditSelection.cpp (patch 8.6.5).
    double getLineEndAnchorToleranceFactor() const;
    void setLineEndAnchorToleranceFactor(double d);

    /// Patch 10.10.2.8 (\"Advanced\"): the maximum bounding-box side length (document points) below
    /// which an element is considered a \"small mark\" and forced to a single center-only ordinary-tier
    /// candidate - see SMALL_MARK_MAX_LENGTH's original role in EditSelection.cpp.
    ///
    /// Patch 10.10.3: also reused, for plain 2-point lines specifically (ArrowKind::NONE - never
    /// arrows), by isSmallCrossingBigPerpendicular() as the maximum length a small line can have to
    /// still qualify for the \"boosted\" (blue) perpendicular-cross match against a much bigger line -
    /// merging what used to be the separate PERPENDICULAR_CROSS_MAX_SELF_LENGTH (patch 10.10.2.9),
    /// since for a line specifically, \"small enough to force a center-only ordinary anchor\" and
    /// \"short enough to be a graduation mark\" were judged to be the same underlying question. For any
    /// non-line element (including arrows), isSmallMark() ignores this setting entirely and always
    /// uses a fixed, non-configurable 15.0 instead - see isSmallMark()'s own comment.
    double getSmallMarkMaxLength() const;
    void setSmallMarkMaxLength(double d);

    double getStrokeRecognizerMinSize() const;
    void setStrokeRecognizerMinSize(double value);
"""
SETTINGS_H_OLD1 = """    bool snapGrid{};

    /**
     * Default name if you save a new document
     */
    std::u8string defaultSaveName;  // should be string - don't change to path"""
SETTINGS_H_NEW1 = """    bool snapGrid{};

    /**
     * object alignment (\"smart guides\") snapping enabled by default
     */
    bool snapToObjects{};

    /**
     * Patch 10.2: whether the equidistant (\"equal spacing\") tier of the object alignment snapping
     * system is enabled. Nested under snapToObjects - see isEquidistantSnappingEnabled() above.
     */
    bool equidistantSnappingEnabled{};

    /**
     * Patch 10.3: whether the page-centering tier of the object alignment snapping system is
     * enabled. Nested under snapToObjects - see isPageCenteringSnappingEnabled() above.
     */
    bool pageCenteringSnappingEnabled{};

    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled, as
     * stored/persisted (and displayed in Preferences). Patch 11.10.2: the isSnapToObjects() gate is
     * applied only at the actual call site (BaseShapeHandler::applyLineCrossingSnap()), never here -
     * this field, and the getter above, always reflect the user's own raw preference untouched.
     */
    bool coordinateSystemAssistEnabled{};

    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled, as stored/persisted (and displayed in Preferences). Patch 11.10.2: the
     * isSnapToObjects() gate is applied only at the actual call site (EllipseHandler::createShape()),
     * never here - this field, and the getter above, always reflect the user's own raw preference
     * untouched.
     */
    bool circleAssistEnabled{};

    /**
     * Patch 10.6A: whether the \"graduation\" (blue grid) tick markers and forced-snap-to-nearest-tick
     * behavior is enabled. Nested under snapToObjects - see isGraduationAssistEnabled() above.
     */
    bool graduationAssistEnabled{};

    /**
     * Patch 10.6B: whether Top/Middle/Below mode switching by cursor drag position is enabled. Nested
     * under graduationAssistEnabled in the UI - see isGraduationOrientationEnabled() above.
     */
    bool graduationOrientationEnabled{};

    /**
     * Patch 10.7: whether the \"table center\" tier is enabled. Nested under snapToObjects - see
     * isTableContentCenteringAssistEnabled() above.
     */
    bool tableContentCenteringAssistEnabled{};

    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled, as
     * stored/persisted (and displayed in Preferences). Patch 11.10.2: the isSnapToObjects() gate is
     * applied only at the actual call site (SplineHandler::onMotionNotifyEvent()), never here - this
     * field, and the getter above, always reflect the user's own raw preference untouched.
     */
    bool splineSnappingEnabled{};

    /**
     * Patch 10.10.2: the base tolerance (screen pixels) for the ordinary alignment snap tier. See
     * getAlignmentSnapTolerancePx() above.
     */
    double alignmentSnapTolerancePx{};

    /**
     * Patch 10.10.2.2: the vertical center fraction used for a Text element's own alignment matching
     * (Y-axis only). See getTextYCenterFraction() above.
     */
    double textYCenterFraction{};

    /**
     * Patch 10.10.2.3: tolerance (screen pixels) for the line-crossing snap assist during shape
     * drawing. See getLineCrossSnapTolerancePx() above.
     */
    double lineCrossSnapTolerancePx{};

    /**
     * Patch 10.10.4: minimum length (document points) for the coordinate system (line-crossing snap)
     * assist to consider a drawn line/arrow or a target line at all. See getLineCrossMinLength()
     * above.
     */
    double lineCrossMinLength{};

    /**
     * Patch 10.10.2.4: tolerance (screen pixels) for the spline tool's ordinary alignment snap. See
     * getSplineAlignmentSnapTolerancePx() above.
     */
    double splineAlignmentSnapTolerancePx{};

    /**
     * Patch 10.10.2.5: tolerance (screen pixels) for the perfect-circle \"diagonal snap\" assist. See
     * getDiagonalSnapTolerancePx() above.
     */
    double diagonalSnapTolerancePx{};

    /**
     * Patch 10.10.2.6: multiplier for the \"boosted\" (blue) tier's tolerance and zone radius. See
     * getPerpendicularCrossBoostFactor() above.
     */
    double perpendicularCrossBoostFactor{};

    /**
     * Patch 10.10.2.7: tolerance factor for snapping a small line to a big line's own endpoints. See
     * getLineEndAnchorToleranceFactor() above.
     */
    double lineEndAnchorToleranceFactor{};

    /**
     * Patch 10.10.2.8: the max bounding-box side length for the \"small mark\" rule. Patch 10.10.3:
     * also reused for line self-length in the boosted tier, merging what used to be
     * perpendicularCrossMaxSelfLength (patch 10.10.2.9) - see getSmallMarkMaxLength() above.
     */
    double smallMarkMaxLength{};

    /**
     * Default name if you save a new document
     */
    std::u8string defaultSaveName;  // should be string - don't change to path"""
ARROW_OLD0 = """auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    const double thickness = control->getToolHandler()->getThickness();
    const ArrowKind kind = this->doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE;
"""
ARROW_NEW0 = """auto ArrowHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point c = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    c = applyLineCrossingSnap(c);
    const double thickness = control->getToolHandler()->getThickness();
    const ArrowKind kind = this->doubleEnded ? ArrowKind::DOUBLE : ArrowKind::SINGLE;
"""
BSH_CPP_OLD0 = """#include \"BaseShapeHandler.h\"

#include <cmath>   // for pow, NAN
#include <memory>  // for make_unique, __share...
"""
BSH_CPP_NEW0 = """#include \"BaseShapeHandler.h\"

#include <algorithm>  // for min, max
#include <cmath>   // for pow, NAN
#include <memory>  // for make_unique, __share...
"""
BSH_CPP_OLD1 = """#include \"view/overlays/ShapeToolView.h\"           // for ShapeToolView


BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):
        InputHandler(control, page),
        flipShift(flipShift),"""
BSH_CPP_NEW1 = """#include \"view/overlays/ShapeToolView.h\"           // for ShapeToolView


/**
 * Below this length (in document points), a segment isn't considered eligible for the \"line
 * crossing\" snap assist - neither the line being drawn nor the line/arrow it might cross.
 *
 * Patch 10.10.4: this used to be a compile-time constant here (LINE_CROSS_MIN_LENGTH = 50.0) - it is
 * now user-configurable via Preferences instead, see Settings::getLineCrossMinLength().
 */

/// How close to perfectly horizontal/vertical (in document points, on the perpendicular coordinate)
/// a segment must be to count as axis-aligned for the \"line crossing\" snap assist.
constexpr double LINE_CROSS_AXIS_TOLERANCE = 3.0;

/// Half the length, in document points, of each 15pt marker drawn by the \"line crossing\" snap assist.
constexpr double LINE_CROSS_MARKER_HALF_SIZE = 7.5;

/// Patch 10.10.2.3: this used to be a compile-time constant here (LINE_CROSS_SNAP_TOLERANCE_PX = 6.0)
/// - it is now user-configurable via Preferences instead, see Settings::getLineCrossSnapTolerancePx().

BaseShapeHandler::BaseShapeHandler(Control* control, const PageRef& page, bool flipShift, bool flipControl):
        InputHandler(control, page),
        flipShift(flipShift),"""
BSH_CPP_OLD2 = """void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {
    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);
    std::swap(shape, this->shape);
    Range repaintRange = rg.unite(lastSnappingRange);
    lastSnappingRange = rg;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""
BSH_CPP_NEW2 = """void BaseShapeHandler::updateShape(bool isAltDown, bool isShiftDown, bool isControlDown) {
    auto [shape, rg] = this->createShape(isAltDown, isShiftDown, isControlDown);
    std::swap(shape, this->shape);
    // The line-crossing snap assist's markers (see applyLineCrossingSnap()) can sit outside the
    // shape's own bounding box - most notably the \"far\" marker, before the line has actually reached
    // it. Without this, the dirty-region tracking below would never invalidate their pixels,
    // leaving stale markers on screen from a previous frame (wrong position, or shown when no
    // longer relevant).
    if (this->lineCrossingGuide) {
        for (const Point& center: {this->lineCrossingGuide->nearCenter, this->lineCrossingGuide->farCenter}) {
            rg.addPoint(center.x - LINE_CROSS_MARKER_HALF_SIZE, center.y - LINE_CROSS_MARKER_HALF_SIZE);
            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);
        }
    }
    if (this->diagonalSnapGuide) {
        // The two green lines run along the square's own edges, already covered by the shape's own
        // bounding box in the vast majority of cases - but unite them in anyway for safety (e.g. an
        // ellipse's Range is computed from its own points, which is a good approximation of the
        // bounding box but not necessarily pixel-exact at the corners).
        rg.addPoint(this->diagonalSnapGuide->corner1.x, this->diagonalSnapGuide->corner1.y);
        rg.addPoint(this->diagonalSnapGuide->corner2.x, this->diagonalSnapGuide->corner2.y);
    }
    Range repaintRange = rg.unite(lastSnappingRange);
    lastSnappingRange = rg;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""
BSH_CPP_OLD3 = """
void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);"""
BSH_CPP_NEW3 = """
void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    this->lineCrossingGuide.reset();
    this->diagonalSnapGuide.reset();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);"""
BSH_CPP_OLD4 = """        return true;
    }
    this->currPoint = newPoint;

    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());
"""
BSH_CPP_NEW4 = """        return true;
    }
    this->currPoint = newPoint;
    this->lastZoom = zoom;

    this->updateShape(pos.isAltDown(), pos.isShiftDown(), pos.isControlDown());
"""
BSH_CPP_OLD5 = """
    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""
BSH_CPP_NEW5 = """
    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());
    this->lineCrossingGuide.reset();
    this->diagonalSnapGuide.reset();

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""
BSH_CPP_OLD6 = """    }
}

auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }

auto BaseShapeHandler::createView(xoj::view::Repaintable* parent) const -> std::unique_ptr<xoj::view::OverlayView> {"""
BSH_CPP_NEW6 = """    }
}

/**
 * If `el` is a Stroke with at least 2 points, returns its two \"shaft\" endpoints: for a plain
 * straight line, its only two points; for an arrow (single or double-ended - see
 * ArrowHandler::createShape()), its first and last point specifically, which are always the true
 * shaft start and tip regardless of however many arrowhead \"wing\" points lie in between. Returns
 * nullopt for anything else (not a Stroke, or fewer than 2 points).
 */
static auto getLineShaftEndpoints(const Element* el) -> std::optional<std::pair<Point, Point>> {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getPointCount() < 2) {
        return std::nullopt;
    }
    const Point* pts = stroke->getPoints();
    return std::make_pair(pts[0], pts[stroke->getPointCount() - 1]);
}

auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than inside the
    // getter itself - see Settings::isCoordinateSystemAssistEnabled()'s own doc comment for why.
    if (control != nullptr && control->getSettings() != nullptr &&
        (!control->getSettings()->isSnapToObjects() ||
         !control->getSettings()->isCoordinateSystemAssistEnabled())) {
        return rawEnd;
    }

    double dx = rawEnd.x - this->startPoint.x;
    double dy = rawEnd.y - this->startPoint.y;
    double lineCrossMinLength = (control != nullptr && control->getSettings() != nullptr)
                                         ? control->getSettings()->getLineCrossMinLength()
                                         : 50.0;  // matches Settings::lineCrossMinLength's own default
    bool drawingVertical = std::abs(dx) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dy) > lineCrossMinLength;
    bool drawingHorizontal = std::abs(dy) <= LINE_CROSS_AXIS_TOLERANCE && std::abs(dx) > lineCrossMinLength;
    if (!drawingVertical && !drawingHorizontal) {
        return rawEnd;
    }

    Layer* layer = this->page->getSelectedLayer();
    if (layer == nullptr) {
        return rawEnd;
    }

    double currentLength = drawingVertical ? std::abs(dy) : std::abs(dx);
    double lineCrossTolerancePx =
            (control != nullptr && control->getSettings() != nullptr)
                    ? control->getSettings()->getLineCrossSnapTolerancePx()
                    : 6.0;  // matches Settings::alignmentSnapTolerancePx's own default, just in case
    double tolerance = lineCrossTolerancePx / this->lastZoom;

    bool found = false;
    double bestTargetLength = 0;
    double bestDistFromCurrent = 0;

    for (auto& elPtr: layer->getElements()) {
        auto shaft = getLineShaftEndpoints(elPtr.get());
        if (!shaft) {
            continue;
        }
        double odx = shaft->second.x - shaft->first.x;
        double ody = shaft->second.y - shaft->first.y;
        double targetLength = std::hypot(odx, ody);
        if (targetLength <= lineCrossMinLength) {
            continue;
        }
        bool targetIsVertical = std::abs(odx) <= LINE_CROSS_AXIS_TOLERANCE;
        bool targetIsHorizontal = std::abs(ody) <= LINE_CROSS_AXIS_TOLERANCE;

        if (drawingVertical) {
            if (!targetIsHorizontal) {
                continue;
            }
            double minX = std::min(shaft->first.x, shaft->second.x);
            double maxX = std::max(shaft->first.x, shaft->second.x);
            if (this->startPoint.x < minX || this->startPoint.x > maxX) {
                continue;
            }
            // The target must actually lie in the direction being drawn (above if drawing upward,
            // below if drawing downward) - otherwise it could never really be \"crossed\" by extending
            // the current line further, no matter how far it goes.
            double targetY = shaft->first.y;  // either endpoint works: nearly equal for a horizontal target
            if ((dy > 0 && targetY < this->startPoint.y) || (dy < 0 && targetY > this->startPoint.y)) {
                continue;
            }
            // The markers only appear once the line being drawn has ALREADY crossed the target's
            // height, not in anticipation of reaching it - i.e. targetY must already lie between the
            // origin and the current (raw, pre-snap) endpoint.
            if (targetY < std::min(this->startPoint.y, rawEnd.y) || targetY > std::max(this->startPoint.y, rawEnd.y)) {
                continue;
            }
        } else {
            if (!targetIsVertical) {
                continue;
            }
            double minY = std::min(shaft->first.y, shaft->second.y);
            double maxY = std::max(shaft->first.y, shaft->second.y);
            if (this->startPoint.y < minY || this->startPoint.y > maxY) {
                continue;
            }
            double targetX = shaft->first.x;
            if ((dx > 0 && targetX < this->startPoint.x) || (dx < 0 && targetX > this->startPoint.x)) {
                continue;
            }
            if (targetX < std::min(this->startPoint.x, rawEnd.x) || targetX > std::max(this->startPoint.x, rawEnd.x)) {
                continue;
            }
        }

        double distFromCurrent = std::abs(currentLength - targetLength);
        if (!found || distFromCurrent < bestDistFromCurrent) {
            found = true;
            bestDistFromCurrent = distFromCurrent;
            bestTargetLength = targetLength;
        }
    }

    if (!found || currentLength > bestTargetLength + tolerance) {
        return rawEnd;
    }

    double sign = drawingVertical ? (dy >= 0 ? 1.0 : -1.0) : (dx >= 0 ? 1.0 : -1.0);
    Point farCenter = drawingVertical ? Point(this->startPoint.x, this->startPoint.y + sign * bestTargetLength)
                                       : Point(this->startPoint.x + sign * bestTargetLength, this->startPoint.y);
    this->lineCrossingGuide = LineCrossingGuide{this->startPoint, farCenter, drawingVertical};

    if (bestDistFromCurrent < tolerance) {
        return drawingVertical ? Point(rawEnd.x, this->startPoint.y + sign * bestTargetLength)
                                : Point(this->startPoint.x + sign * bestTargetLength, rawEnd.y);
    }
    return rawEnd;
}

auto BaseShapeHandler::getShape() const -> const std::vector<Point>& { return this->shape; }

auto BaseShapeHandler::createView(xoj::view::Repaintable* parent) const -> std::unique_ptr<xoj::view::OverlayView> {"""
BSH_H_OLD0 = """#pragma once

#include <memory>  // for shared_ptr
#include <utility>  // for pair
#include <vector>   // for vector
"""
BSH_H_NEW0 = """#pragma once

#include <memory>  // for shared_ptr
#include <optional> // for optional
#include <utility>  // for pair
#include <vector>   // for vector
"""
BSH_H_OLD1 = """    const std::vector<Point>& getShape() const;

    /**
     * @brief Whether this shape tool produces an arrow (and if so, single- or double-ended), so that
     * the finalized Stroke can be tagged accordingly (see Stroke::setArrowKind()). NONE by default;
     * overridden by ArrowHandler.
     */
    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }

private:
    /**
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in"""
BSH_H_NEW1 = """    const std::vector<Point>& getShape() const;

    /**
     * Last zoom level seen in onMotionNotifyEvent(), exposed so views (e.g. ShapeToolView) can draw
     * overlay guides at a constant on-screen thickness, matching EditSelection's alignment guides,
     * regardless of the actual zoom level - see lastZoom's own doc comment below for why it exists.
     */
    double getLastZoom() const { return lastZoom; }

    /**
     * @brief Whether this shape tool produces an arrow (and if so, single- or double-ended), so that
     * the finalized Stroke can be tagged accordingly (see Stroke::setArrowKind()). NONE by default;
     * overridden by ArrowHandler.
     */
    virtual ArrowKind getArrowKind() const { return ArrowKind::NONE; }

    /**
     * Two 15pt markers, drawn perpendicular to the line/arrow currently being drawn, illustrating a
     * matching length found on another line/arrow already on the page - see applyLineCrossingSnap().
     * `nearCenter` sits at the fixed origin point of the line being drawn; `farCenter` sits at the
     * target distance away, in the direction being drawn. `perpendicularIsHorizontal` is true when
     * the line being drawn is vertical (so the markers themselves are drawn as short horizontal
     * segments), false when it is horizontal (markers drawn as short vertical segments).
     */
    struct LineCrossingGuide {
        Point nearCenter;
        Point farCenter;
        bool perpendicularIsHorizontal;
    };
    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }

    /**
     * Two green guide lines shown when a shape's bounding box has been snapped to a square (equal
     * width and height) - see EllipseHandler::createShape(). `corner1` and `corner2` are the two
     * opposite corners of the (now square) bounding box; the two lines are drawn along the edges
     * meeting at `corner2` (the one nearer the cursor), from `corner2` to each adjacent corner.
     */
    struct DiagonalSnapGuide {
        Point corner1;
        Point corner2;
    };
    const std::optional<DiagonalSnapGuide>& getDiagonalSnapGuide() const { return diagonalSnapGuide; }

private:
    /**
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in"""
BSH_H_OLD2 = """     */
    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);

protected:
    std::vector<Point> shape;
"""
BSH_H_NEW2 = """     */
    void modifyModifiersByDrawDir(double width, double height, double zoom, bool changeCursor = true);

    /**
     * If the segment from `this->startPoint` to `rawEnd` is axis-aligned (horizontal or vertical,
     * within a small tolerance) and longer than 50pt, and another sufficiently long, perpendicular
     * line/arrow already on the page crosses its path, updates `lineCrossingGuide` with two 15pt
     * markers illustrating that other line's length, and returns `rawEnd` snapped to match that exact
     * length if it is already close enough (same tolerance as the rest of the alignment-snapping
     * system). Otherwise clears `lineCrossingGuide` and returns `rawEnd` unchanged. Meant to be called
     * by a line-like shape's own createShape() (RulerHandler, ArrowHandler) right after computing its
     * own raw endpoint - not used by shapes like Rectangle or Ellipse. A Stroke with an ArrowKind
     * (single or double) is treated purely by its own shaft (first/last point), ignoring any
     * arrowhead \"wing\" points, on both ends of the comparison - a fresh arrow being drawn, and an
     * existing arrow being crossed.
     */
    Point applyLineCrossingSnap(Point rawEnd);

protected:
    std::vector<Point> shape;
"""
BSH_H_OLD3 = """    Point buttonDownPoint;  // used for tapSelect and filtering - never snapped to grid.
    Point startPoint;       // May be snapped to grid

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};"""
BSH_H_NEW3 = """    Point buttonDownPoint;  // used for tapSelect and filtering - never snapped to grid.
    Point startPoint;       // May be snapped to grid

    /// Last zoom level seen in onMotionNotifyEvent() - createShape() has no zoom parameter of its
    /// own, but applyLineCrossingSnap() needs one to convert its pixel-based tolerance.
    double lastZoom = 1.0;

    std::optional<LineCrossingGuide> lineCrossingGuide;
    std::optional<DiagonalSnapGuide> diagonalSnapGuide;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};"""
ES_CPP_OLD0 = """#include \"gui/XournalppCursor.h\"                   // for XournalppCursor
#include \"model/Document.h\"                        // for Document
#include \"model/Element.h\"                         // for Element::Index
#include \"model/ElementInsertionPosition.h\"
#include \"model/Layer.h\"                          // for Layer
#include \"model/LineStyle.h\"                      // for LineStyle
#include \"model/Point.h\"                          // for Point
#include \"model/XojPage.h\"                        // for XojPage
#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction
#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction
#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler
#include \"util/Range.h\"                           // for Range
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector
#include \"util/glib_casts.h\"                      // for wrap_v
#include \"util/i18n.h\"                            // for _
#include \"util/serializing/ObjectInputStream.h\"   // for ObjectInputStream"""
ES_CPP_NEW0 = """#include \"gui/XournalppCursor.h\"                   // for XournalppCursor
#include \"model/Document.h\"                        // for Document
#include \"model/Element.h\"                         // for Element::Index
#include \"model/ElementInsertionPosition.h\"
#include \"model/Layer.h\"                          // for Layer
#include \"model/LineStyle.h\"                      // for LineStyle
#include \"model/BackgroundConfig.h\"                // for BackgroundConfig
#include \"model/PageType.h\"                        // for PageType, PageTypeFormat
#include \"model/Point.h\"                          // for Point
#include \"model/Stroke.h\"                         // for Stroke
#include \"model/Image.h\"                          // for Image
#include \"model/Text.h\"                           // for Text
#include \"model/TexImage.h\"                       // for TexImage
#include \"model/XojPage.h\"                        // for XojPage
#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction
#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction
#include \"undo/LineRepositionUndoAction.h\"        // for LineRepositionUndoAction
#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler
#include \"util/Range.h\"                           // for Range
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector
#include \"util/glib_casts.h\"                      // for wrap_v
#include \"util/i18n.h\"                            // for _
#include \"util/serializing/ObjectInputStream.h\"   // for ObjectInputStream"""
ES_CPP_OLD1 = """constexpr int DELETE_PADDING = 20;
constexpr int ROTATE_PADDING = 8;

/// Number of times to trigger edge pan timer per second
constexpr unsigned int PAN_TIMER_RATE = 30;

namespace SelectionFactory {
/// @return Bounds and SnappingBounds
static auto computeBoxes(const InsertionOrder& elts) -> std::pair<Range, Range> {
    return std::transform_reduce(
            elts.begin(), elts.end(), std::pair<Range, Range>(),
            [](auto&& p, auto&& q) {"""
ES_CPP_NEW1 = """constexpr int DELETE_PADDING = 20;
constexpr int ROTATE_PADDING = 8;

/// Number of times to trigger edge pan timer per second
constexpr unsigned int PAN_TIMER_RATE = 30;

/**
 * Patch 9.2: tolerance in screen pixels (independent of zoom) used ONLY by the \"second pass\" of
 * findAlignmentX/Y() - see the fuller comment near findAlignmentY() itself. Declared here, near the
 * top of the file, since EditSelection::mouseDown() (defined shortly below) needs it too.
 */
constexpr double ALIGNMENT_GROUP_TOLERANCE_PX = 0.5;

namespace SelectionFactory {
/// @return Bounds and SnappingBounds
static auto computeBoxes(const InsertionOrder& elts) -> std::pair<Range, Range> {
    return std::transform_reduce(
            elts.begin(), elts.end(), std::pair<Range, Range>(),
            [](auto&& p, auto&& q) {"""
ES_CPP_OLD2 = """EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,
                             const Range& bounds, const Range& snappingBounds):
        snappedBounds(snappingBounds),
        btnWidth(getBtnWidth(ctrl)),
        sourcePage(page),
        sourceLayer(layer),
        view(view),
        undo(ctrl->getUndoRedoHandler()),
        snappingHandler(ctrl->getSettings()) {
    snappingHandler.setPageRef(page);
    // make the visible bounding box large enough so that anchors do not collapse even for horizontal/vertical strokes
    const double PADDING = 12.;"""
ES_CPP_NEW2 = """EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,
                             const Range& bounds, const Range& snappingBounds):
        snappedBounds(snappingBounds),
        btnWidth(getBtnWidth(ctrl)),
        sourcePage(page),
        sourceLayer(layer),
        settings(ctrl->getSettings()),
        view(view),
        undo(ctrl->getUndoRedoHandler()),
        snappingHandler(ctrl->getSettings()) {
    snappingHandler.setPageRef(page);
    // make the visible bounding box large enough so that anchors do not collapse even for horizontal/vertical strokes
    const double PADDING = 12.;"""
ES_CPP_OLD3 = """
EditSelection::EditSelection(Control* ctrl, const PageRef& page, Layer* layer, XojPageView* view):
        snappedBounds(Rectangle<double>{}),
        btnWidth(getBtnWidth(ctrl)),
        sourcePage(page),
        sourceLayer(layer),
        view(view),
        undo(ctrl->getUndoRedoHandler()),
        snappingHandler(ctrl->getSettings()) {
    snappingHandler.setPageRef(page);
}
"""
ES_CPP_NEW3 = """
EditSelection::EditSelection(Control* ctrl, const PageRef& page, Layer* layer, XojPageView* view):
        snappedBounds(Rectangle<double>{}),
        btnWidth(getBtnWidth(ctrl)),
        sourcePage(page),
        sourceLayer(layer),
        settings(ctrl->getSettings()),
        view(view),
        undo(ctrl->getUndoRedoHandler()),
        snappingHandler(ctrl->getSettings()) {
    snappingHandler.setPageRef(page);
}
"""
ES_CPP_OLD4 = """}

/**
 * Finish the current movement
 * (should be called in the mouse-button-released event handler)
 */
void EditSelection::mouseUp() {
    if (this->mouseDownType == CURSOR_SELECTION_DELETE) {
        this->view->getXournal()->deleteSelection();
        return;
    }
"""
ES_CPP_NEW4 = """}

/**
 * Finish the current movement
 * (should be called in the mouse-button-released event handler)
 */
// \"Line reposition on release\" (patch 8.6.4.5) - defined later in this file (after its
// dependencies like THIN_AXIS_THRESHOLD/rangesOverlap/BLUE_GRID_LENGTH_EPS), forward-declared here
// so EditSelection::mouseUp() below can call it.
static void applyLineRepositionOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements);

void EditSelection::mouseUp() {
    if (this->mouseDownType == CURSOR_SELECTION_DELETE) {
        this->view->getXournal()->deleteSelection();
        return;
    }
"""
ES_CPP_OLD5 = """    this->sourcePage = page;
    this->sourceLayer = layer;

    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    this->mouseDownType = CURSOR_SELECTION_NONE;

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);
    updateMatrix();
    if (wasEdgePanning) {
        this->ensureWithinVisibleArea();
    }
}

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is not modified"""
ES_CPP_NEW5 = """    this->sourcePage = page;
    this->sourceLayer = layer;

    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    // \"Line reposition on release\" (patch 8.6.4.5) - only for an actual move (not a resize/rotate),
    // and only if a boosted (blue) match was active when the drag ended; activeBoostedTarget could
    // otherwise be a stale leftover from an earlier move gesture during this same selection.
    if (this->mouseDownType == CURSOR_SELECTION_MOVE && this->activeBoostedTarget != nullptr) {
        applyLineRepositionOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,
                                     this->activeBoostedIsXAxis, this->activeBoostedZone,
                                     this->getElementsView().clone());
    }

    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();
    this->activeBlueGridMarkers.clear();
    this->activeBoostedTarget = nullptr;

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);
    updateMatrix();
    if (wasEdgePanning) {
        this->ensureWithinVisibleArea();
    }
}

// \"Starting zone\" detection (patch 8.6.4.6) - defined later in this file (after its dependencies
// like THIN_AXIS_THRESHOLD/rangesOverlap and findAlignmentX/Y themselves), forward-declared here so
// EditSelection::mouseDown() below can call it.
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText,
                                bool& outWasBoosted);

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;

    // coordinates relative to top left corner of snapped bounds in coordinate system which is not modified"""
ES_CPP_OLD6 = """
    // coordinates relative to top left corner of snapped bounds in coordinate system which is rotated to make bounding
    // box edges horizontal/vertical
    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;
}

void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {
    double zoom = this->view->getXournal()->getZoom();

    if (this->mouseDownType == CURSOR_SELECTION_MOVE) {
        // compute translation (without snapping)
        double dx = mouseX / zoom - this->snappedBounds.x - this->relMousePosX;
        double dy = mouseY / zoom - this->snappedBounds.y - this->relMousePosY;

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position
        double cx = this->snappedBounds.x;
        double cy = this->snappedBounds.y;
        if ((this->relMousePosRotX > this->snappedBounds.width / 2) ==
            (this->snappedBounds.width > 0)) {  // closer to the right side
            cx += this->snappedBounds.width;"""
ES_CPP_NEW6 = """
    // coordinates relative to top left corner of snapped bounds in coordinate system which is rotated to make bounding
    // box edges horizontal/vertical
    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;

    // \"Blue grid\" starting zone (patch 8.6.4.6): capture, once at the start of this drag, which zone
    // self was already in (Middle if not boosted at all) - see computeStartingZone(). Used later in
    // mouseMove()/paint() to shift the whole grid preview by the right amount as the zone changes.
    this->startingBoostedZone = 0;
    this->startingWasBoosted = false;
    {
        std::vector<const Element*> excludedForStart = this->getElementsView().clone();
        xoj::util::Rectangle<double>* visibleRectPtrForStart = this->view->getXournal()->getVisibleRect(this->view);
        if (visibleRectPtrForStart != nullptr) {
            xoj::util::Rectangle<double> visibleRectForStart = *visibleRectPtrForStart;
            delete visibleRectPtrForStart;
            // Patch 10.10.2: uses the same settings-backed tolerance as the rest of the alignment
            // system, so this \"starting zone\" computation always stays in sync with it.
            double toleranceForStart = settings->getAlignmentSnapTolerancePx() / zoom;
            double groupToleranceForStart =
                    toleranceForStart * (ALIGNMENT_GROUP_TOLERANCE_PX / settings->getAlignmentSnapTolerancePx());
            // Patch 10.10.3: true only if self is a single plain 2-point line (never an arrow) - see
            // the identical check in mouseMove() below for the full rationale.
            bool selfIsLineForStart = false;
            {
                auto selfElementsForLineCheck = this->getElementsView();
                if (selfElementsForLineCheck.size() == 1) {
                    if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForLineCheck.begin())) {
                        selfIsLineForStart =
                                selfStroke->getArrowKind() == ArrowKind::NONE && selfStroke->getPointCount() == 2;
                    }
                }
            }
            // Patch 11.6: true only if self is a single Text element whose content has no line break
            // - see the identical check in mouseMove() below for the full rationale.
            bool selfIsSingleLineTextForStart = false;
            {
                auto selfElementsForTextCheck = this->getElementsView();
                if (selfElementsForTextCheck.size() == 1) {
                    if (const auto* selfText = dynamic_cast<const Text*>(*selfElementsForTextCheck.begin())) {
                        selfIsSingleLineTextForStart = selfText->getText().find('\\n') == std::string::npos;
                    }
                }
            }
            this->startingBoostedZone =
                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,
                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,
                                         visibleRectForStart, toleranceForStart, groupToleranceForStart,
                                         settings->getTextYCenterFraction(),
                                         settings->getPerpendicularCrossBoostFactor(),
                                         settings->getSmallMarkMaxLength(), selfIsLineForStart,
                                         selfIsSingleLineTextForStart, this->startingWasBoosted);
        }
    }
}

/**
 * Smart alignment guides (sub-patch 1: silent snap, no visual guide line yet).
 *
 * Tolerance in screen pixels (independent of zoom) within which a candidate edge/center of the
 * moving selection's bounding box is considered \"aligned\" with a candidate edge/center of another
 * element on the same layer.
 *
 * Patch 10.10.2: this used to be a compile-time constant here (ALIGNMENT_SNAP_TOLERANCE_PX = 6.0) -
 * it is now user-configurable via Preferences instead, see Settings::getAlignmentSnapTolerancePx().
 */

/**
 * Patch 9.2: tolerance in screen pixels (independent of zoom) used ONLY by the \"second pass\" of
 * findAlignmentX/Y() - the pass that, once the winning offset from the first pass is known, looks
 * for every OTHER element whose own candidate also lands within tolerance of that final position, so
 * their guides can all be shown together (revealing a whole group of coinciding anchors, not just
 * the one that won the first pass). Deliberately much stricter than the base alignment tolerance
 * (Settings::getAlignmentSnapTolerancePx(), which governs the first pass, i.e. whether the snap
 * triggers at all): two elements whose anchors merely happen to be a few pixels apart should not
 * both draw a guide and give the false impression that they are aligned with each other. Declared
 * near the top of the file (see ALIGNMENT_GROUP_TOLERANCE_PX above) since EditSelection::mouseDown()
 * needs it too, and that method is defined before this point in the file.
 */

/**
 * Result of a successful alignment match: `offset` is the amount to shift the moving object's
 * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide
 * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the
 * moving object and the matched object, so the drawn guide line visually connects the two.
 * `isCenter` is true if either of the two matched candidates was a center point (rather than an
 * edge); `isBoosted` is true for the special \"small stroke crossing a big perpendicular stroke,
 * center-to-center\" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.
 * `equidistantGaps`/`equidistantPlacement` are only set for an equidistant (\"equal spacing\") match
 * (see findEquidistantX/Y()): each pair in `equidistantGaps` is a (from, to) span, in primary-axis
 * document coordinates, of one gap in the chain to be drawn as a double-headed arrow; all of them
 * are drawn at the same `equidistantPlacement` coordinate on the perpendicular axis. Empty/0 (their
 * default) for every other kind of match, which just draws the plain coordinate/extentFrom/extentTo
 * line instead - see paint().
 */
struct AlignmentMatch {
    double offset;
    double coordinate;
    double extentFrom;
    double extentTo;
    bool isCenter;
    bool isBoosted;
    /// For the \"table center\" feature (see findTableCenterX/Y()): true when a Text/TexImage/Image is
    /// centered between two same-length parallel lines, drawn in yellow with top priority on its axis.
    bool isTableCenter = false;
    /// For a boosted (blue) match only: the \"big line\" element that was matched, needed by the
    /// \"blue grid\" feature (see computeBlueGrid()) to search for other small crossing lines on it.
    const Element* boostedTarget = nullptr;
    bool selfIsCenter = false;
    bool otherIsCenter = false;
    bool selfOnFromSide = true;
    std::vector<std::pair<double, double>> equidistantGaps;
    double equidistantPlacement = 0;
    bool isPageCenter = false;
    bool hasPageMargin = false;
    double pageMarginX = 0;
    /// Patch 11.5: see AlignmentGuide::isBoostedButFree in EditSelection.h for the full explanation -
    /// copied through to it via the AlignmentGuide construction below.
    bool isBoostedButFree = false;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line
/// (AlignmentGuide) consistent with that same offset - there can be more than one when several
/// anchor points happen to agree at once (see findAlignmentX/Y()).
struct AlignmentSearchResult {
    double offset;
    std::vector<AlignmentMatch> guides;
};

/// A single candidate coordinate for alignment, tagged with whether it is a center point.
struct AlignmentCandidate {
    double value;
    bool isCenter;
};

/**
 * Below this size (in document points), a box is considered to have no meaningful \"thickness axis\"
 * of its own (e.g. a horizontal or vertical straight line) - see buildCandidates().
 */
constexpr double THIN_AXIS_THRESHOLD = 3.0;

/**
 * When a small line-like element is moved across a much bigger perpendicular line-like element
 * (e.g. a short axis tick dragged onto a long axis line), a center-to-center match between the two
 * gets an extended tolerance (this factor), takes exclusive priority over any other match on that
 * axis (only the blue guide is shown, even if other alignments would also be in tolerance), and is
 * drawn in a distinct color, since that is a very deliberate, common alignment (e.g. centering a
 * graduation mark on an axis).
 *
 * Patch 10.10.2.6: this used to be a compile-time constant here (PERPENDICULAR_CROSS_BOOST_FACTOR =
 * 4.0) - it is now user-configurable via Preferences instead, see
 * Settings::getPerpendicularCrossBoostFactor(). Only findAlignmentX/Y() use it as a parameter (free
 * functions without direct access to `settings`) - EditSelection::mouseMove() itself calls the
 * getter directly.
 */
/// Tolerance factor for snapping a small line to one of the big line's own two endpoints (patch
/// 8.6.5) - deliberately much smaller than the perpendicular cross boost factor, since this snap is
/// a precise \"line up exactly with the end\" gesture rather than the generous perpendicular-cross
/// boost.
///
/// Patch 10.10.2.7: this used to be a compile-time constant here (LINE_END_ANCHOR_TOLERANCE_FACTOR =
/// 0.9) - it is now user-configurable via Preferences instead, see
/// Settings::getLineEndAnchorToleranceFactor(). Used directly in EditSelection::mouseMove() (a
/// member method with direct access to `settings`), no parameter threading needed.

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's
 * own length (its extent along its own axis, e.g. a vertical tick's height) is at most this many
 * document points - the same unit used for arrow-key nudging.
 *
 * Patch 10.10.2.9: this used to be a compile-time constant here (PERPENDICULAR_CROSS_MAX_SELF_LENGTH
 * = 15.0) - it was briefly user-configurable via its own Preferences entry.
 *
 * Patch 10.10.3: that separate setting was merged into Settings::getSmallMarkMaxLength() instead
 * (passed in here under the still-generic `maxSelfLength` parameter name) - see isSmallMark()'s own
 * comment for the reasoning. Only ever called with this value for a plain line's own length; never
 * for anything else.
 */

/**
 * Fraction (0 to 1, from the top) of a Text element's height used as its horizontal-alignment (Y)
 * anchor, instead of the true geometric center (0.5). Text bounding boxes include descender space
 * below the baseline, which pulls the geometric center lower than where a horizontal alignment
 * \"feels\" visually centered on the text - this constant lets that be tuned independently of
 * everything else. Deliberately left at an easily-noticeable default; tune to taste.
 *
 * Patch 10.10.2.2: this used to be a compile-time constant here (TEXT_Y_CENTER_FRACTION = 0.6) - it
 * is now user-configurable via Preferences instead, see Settings::getTextYCenterFraction(). Only
 * findAlignmentY() uses it (passed in as a parameter, since it's a free function without direct
 * access to `settings`) - findAlignmentX() has no equivalent, horizontal centering always uses the
 * true geometric 0.5.
 */

/**
 * Below this length (in document points, measured as the larger of an element's own width/height),
 * an element is considered a \"small mark\" for anchor purposes - see buildCandidates()'s
 * `forceCenterOnly` parameter. Distinct from THIN_AXIS_THRESHOLD (which only concerns a single axis
 * relative to a long line) - this instead looks at the object as a whole, so a small tick or cross
 * mark always gets a single center anchor on *both* axes, regardless of how it happens to be
 * proportioned.
 *
 * Patch 10.10.2.8: this used to be a compile-time constant here (SMALL_MARK_MAX_LENGTH = 15.0) - it
 * is now user-configurable via Preferences instead, see Settings::getSmallMarkMaxLength(). Passed
 * into isSmallMark() as a parameter, since it is a free function without direct access to `settings`.
 *
 * Patch 10.10.3: for a plain 2-point line (ArrowKind::NONE - never an arrow), this configurable
 * value is ALSO the same one used by isSmallCrossingBigPerpendicular() to gate the \"boosted\" tier -
 * merging what used to be a separate PERPENDICULAR_CROSS_MAX_SELF_LENGTH setting (patch 10.10.2.9),
 * since for a line, \"small enough to force center-only\" and \"short enough to be a graduation mark\"
 * were judged the same question. For anything that is NOT a plain line (any other shape, or an
 * arrow), the user-configurable value is ignored entirely and a fixed, non-configurable 15.0 is used
 * instead - see FIXED_NON_LINE_SMALL_MARK_MAX_LENGTH below.
 */

/// Patch 10.10.3: fixed fallback used by isSmallMark() for anything that is not a plain 2-point line
/// (arrows included) - intentionally NOT user-configurable, since the \"small mark\" question for a
/// non-line shape (a cross, a dot, an arrow...) was judged not worth exposing on its own.
constexpr double FIXED_NON_LINE_SMALL_MARK_MAX_LENGTH = 15.0;

/// True if an element whose own bounding box is `width` x `height` counts as a \"small mark\". `isLine`
/// (true only for a plain 2-point stroke, ArrowKind::NONE) selects whether the user-configurable
/// `smallMarkMaxLength` applies, or the fixed FIXED_NON_LINE_SMALL_MARK_MAX_LENGTH instead - see the
/// comment above.
static auto isSmallMark(double width, double height, bool isLine, double smallMarkMaxLength) -> bool {
    double effectiveMaxLength = isLine ? smallMarkMaxLength : FIXED_NON_LINE_SMALL_MARK_MAX_LENGTH;
    return std::max(width, height) < effectiveMaxLength;
}

/**
 * True if `stroke` matches the exact point pattern produced by Control::insertCross() (see
 * createFloatingMark()/insertCross() in Control.cpp): exactly 5 points forming two perpendicular
 * diagonals of equal arm length, crossing at the middle point of the list. There is no persisted
 * \"this is a cross\" flag in the data model (unlike ArrowKind for arrows), so this is a geometric
 * deduction, same spirit as the arrow-shaft detection used elsewhere in this file before ArrowKind
 * existed. A false positive would require another stroke to coincidentally match this exact
 * geometry, which is vanishingly unlikely for anything not created by insertCross() itself.
 */
static auto isCrossShape(const Stroke* stroke) -> bool {
    if (stroke == nullptr || stroke->getPointCount() != 5) {
        return false;
    }
    const Point* p = stroke->getPoints();
    constexpr double EPS = 0.01;
    Point mid1((p[0].x + p[1].x) / 2, (p[0].y + p[1].y) / 2);
    Point mid2((p[3].x + p[4].x) / 2, (p[3].y + p[4].y) / 2);
    if (std::abs(mid1.x - p[2].x) > EPS || std::abs(mid1.y - p[2].y) > EPS) {
        return false;
    }
    if (std::abs(mid2.x - p[2].x) > EPS || std::abs(mid2.y - p[2].y) > EPS) {
        return false;
    }
    double d1x = p[1].x - p[0].x;
    double d1y = p[1].y - p[0].y;
    double d2x = p[4].x - p[3].x;
    double d2y = p[4].y - p[3].y;
    if (std::abs(d1x * d2x + d1y * d2y) > EPS) {
        return false;  // the two diagonals must be perpendicular
    }
    double len0 = std::hypot(p[0].x - p[2].x, p[0].y - p[2].y);
    double len1 = std::hypot(p[1].x - p[2].x, p[1].y - p[2].y);
    double len3 = std::hypot(p[3].x - p[2].x, p[3].y - p[2].y);
    double len4 = std::hypot(p[4].x - p[2].x, p[4].y - p[2].y);
    double avg = (len0 + len1 + len3 + len4) / 4;
    if (avg < EPS) {
        return false;
    }
    for (double l: {len0, len1, len3, len4}) {
        if (std::abs(l - avg) > EPS) {
            return false;
        }
    }
    return true;
}

/**
 * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis.
 * `forceCenterOnly` (set by the caller for a \"small mark\" or a cross - see SMALL_MARK_MAX_LENGTH and
 * isCrossShape()) always collapses to the single center candidate, tagged as a genuine center match
 * (green). Otherwise, if the box is merely \"thin\" on this one axis (size <= THIN_AXIS_THRESHOLD,
 * e.g. the thickness of an otherwise-long horizontal or vertical line), the single candidate is
 * still returned, but tagged as an edge match (pink) instead: there was no real edge-vs-center choice
 * on a thin axis, so a guide line running parallel to the line it came from shouldn't imply a
 * deliberate centering the way a true 3-way choice does. Otherwise, offers the normal 3 candidates.
 * `centerFraction` (0 to 1) chooses where the center candidate sits within the box, in every branch
 * (e.g. TEXT_Y_CENTER_FRACTION only has any effect because of this).
 */
static auto buildCandidates(double from, double size, double centerFraction = 0.5, bool forceCenterOnly = false)
        -> std::vector<AlignmentCandidate> {
    if (forceCenterOnly) {
        return {{from + size * centerFraction, true}};
    }
    if (size <= THIN_AXIS_THRESHOLD) {
        return {{from + size * centerFraction, false}};
    }
    return {{from, false}, {from + size * centerFraction, true}, {from + size, false}};
}

/// True if the two given [x, x+w] x [y, y+h] boxes intersect at all.
static auto boxesIntersect(double x1, double y1, double w1, double h1, double x2, double y2, double w2, double h2)
        -> bool {
    return x1 <= x2 + w2 && x2 <= x1 + w1 && y1 <= y2 + h2 && y2 <= y1 + h1;
}

/// True if the two given ranges [a1, a2] and [b1, b2] overlap at all.
static auto rangesOverlap(double a1, double a2, double b1, double b2) -> bool { return a1 <= b2 && b1 <= a2; }

/**
 * Which axis a \"perpendicular cross\" check is being performed for - see
 * isSmallCrossingBigPerpendicular(). A vertical self ticked onto a horizontal other only makes
 * sense as a Y-axis match (aligning the tick's own vertical center to the long line's flat
 * position); a horizontal self ticked onto a vertical other only makes sense as an X-axis match.
 * The opposite pairing for a given axis (e.g. a horizontal self matched to a vertical other on the
 * Y axis) would mean \"snap this small stroke to the middle of the big one's own length\" - not a
 * meaningful crossing, and specifically the behavior this axis restriction excludes.
 */
enum class CrossAxis { X, Y };

/**
 * True if `self` (width x height) and `other` (width x height) form a meaningful \"small stroke
 * crossing a big perpendicular stroke\" relationship *for the given axis* (see CrossAxis): one is
 * \"thin\" per THIN_AXIS_THRESHOLD on one axis while the other is thin on the *perpendicular* axis,
 * `self` is shorter, along its own length, than `other` is along its own length, and `self`'s own
 * length is at most PERPENDICULAR_CROSS_MAX_SELF_LENGTH - i.e. a short axis tick being placed onto a
 * long axis line. Only ONE of the two possible orientations is valid per axis (see CrossAxis docs),
 * so a given (self, other) pair can be eligible on at most one axis at a time - never both at once.
 * Does NOT check whether they actually currently overlap in position - see rangesOverlap(), checked
 * separately by the caller, which has the position information.
 */
static auto isSmallCrossingBigPerpendicular(double selfWidth, double selfHeight, double otherWidth,
                                             double otherHeight, CrossAxis axis, double maxSelfLength) -> bool {
    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;
    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;
    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;
    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;

    if (axis == CrossAxis::Y) {
        return selfVertical && otherHorizontal && selfHeight < otherWidth && selfHeight <= maxSelfLength;
    }
    return selfHorizontal && otherVertical && selfWidth < otherHeight && selfWidth <= maxSelfLength;
}

/**
 * Vertical (for a horizontal chain) or horizontal (for a vertical chain) offset, in document
 * points, between the row/column of objects being equally spaced and the double-arrow chain drawn
 * to illustrate it - see findEquidistantX/Y() and paint(). The chain is drawn on the \"outside\" of
 * the objects (below a horizontal row, to the right of a vertical column).
 */
constexpr double EQUIDISTANT_ARROW_MARGIN = 10.0;

/**
 * Equidistant (\"equal spacing\") snapping: if the moving box, placed at x (width wide), would end up
 * adjacent to one of two other elements B and C on `layer`, at exactly the same gap that already
 * separates B and C from each other, returns the match (offset to apply, and a guide spanning from
 * the moving box to the far element). Covers extending an existing rhythm at either end (self-B-C or
 * B-C-self); does not cover inserting self *between* B and C by bisecting their gap. B and C are only
 * considered together if a single horizontal line could pass through the moving box and both of them
 * (their Y-extents, together with [yTop, yBottom], must have a common intersection) - same
 * \"overlap on the perpendicular axis\" rule used elsewhere, not requiring perfect alignment.
 * Always renders pink (this is not an edge/center anchor match, just reused for visual consistency).
 */
static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded,
                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        candidates.push_back(el);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.x + bb.width > cb.x) {
                continue;  // only consider b strictly to the left of c (each pair handled once)
            }
            double gap = cb.x - (bb.x + bb.width);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({yTop, bb.y, cb.y});
            double minEnd = std::min({yBottom, bb.y + bb.height, cb.y + cb.height});
            if (maxStart > minEnd) {
                continue;
            }

            // self extends the row on the left: self, b, c
            double unionFrom = std::min({yTop, bb.y, cb.y});
            double unionTo = std::max({yBottom, bb.y + bb.height, cb.y + cb.height});
            double placement = std::max({yBottom, bb.y + bb.height, cb.y + cb.height}) + EQUIDISTANT_ARROW_MARGIN;
            double targetLeft = bb.x - gap - width;
            double distLeft = std::abs(targetLeft - x);
            if (distLeft < bestDist) {
                bestDist = distLeft;
                best = AlignmentMatch{targetLeft - x, targetLeft, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{targetLeft + width, bb.x}, {bb.x + bb.width, cb.x}};
                best->equidistantPlacement = placement;
            }
            // self extends the row on the right: b, c, self
            double targetRight = cb.x + cb.width + gap;
            double distRight = std::abs(targetRight - x);
            if (distRight < bestDist) {
                bestDist = distRight;
                best = AlignmentMatch{targetRight - x, targetRight, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{bb.x + bb.width, cb.x}, {cb.x + cb.width, targetRight}};
                best->equidistantPlacement = placement;
            }
        }
    }
    return best;
}

/// Same as findEquidistantX(), but along the vertical axis (stacking a row top-to-bottom).
static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded,
                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        candidates.push_back(el);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.y + bb.height > cb.y) {
                continue;
            }
            double gap = cb.y - (bb.y + bb.height);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({xLeft, bb.x, cb.x});
            double minEnd = std::min({xRight, bb.x + bb.width, cb.x + cb.width});
            if (maxStart > minEnd) {
                continue;
            }

            double unionFrom = std::min({xLeft, bb.x, cb.x});
            double unionTo = std::max({xRight, bb.x + bb.width, cb.x + cb.width});
            double placement = std::max({xRight, bb.x + bb.width, cb.x + cb.width}) + EQUIDISTANT_ARROW_MARGIN;
            double targetTop = bb.y - gap - height;
            double distTop = std::abs(targetTop - y);
            if (distTop < bestDist) {
                bestDist = distTop;
                best = AlignmentMatch{targetTop - y, targetTop, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{targetTop + height, bb.y}, {bb.y + bb.height, cb.y}};
                best->equidistantPlacement = placement;
            }
            double targetBottom = cb.y + cb.height + gap;
            double distBottom = std::abs(targetBottom - y);
            if (distBottom < bestDist) {
                bestDist = distBottom;
                best = AlignmentMatch{targetBottom - y, targetBottom, unionFrom, unionTo, false, false};
                best->equidistantGaps = {{bb.y + bb.height, cb.y}, {cb.y + cb.height, targetBottom}};
                best->equidistantPlacement = placement;
            }
        }
    }
    return best;
}

/**
 * Searches for alignment matches of the moving box's y-candidates (see buildCandidates()) against
 * every other element on `layer` (elements in `excluded` are always skipped, i.e. the elements
 * currently being moved; elements whose *visual* bounding box doesn't currently intersect
 * `visibleRect` are ignored, i.e. scrolled out of view).
 *
 * First looks for a \"boosted\" perpendicular-cross center match (see isSmallCrossingBigPerpendicular());
 * if one is found, it is returned alone (a single blue guide), ignoring every
 * other possible match on this axis entirely.
 *
 * Otherwise, finds the single closest ordinary match (center or edge, computed from each element's
 * *snapped* bounds - Element::getSnappedBounds() - rather than its visual bounds, so a selected
 * element's own candidates line up exactly with an identical, unselected element's; a Text element's
 * center candidate uses TEXT_Y_CENTER_FRACTION instead of the true geometric center). Once that
 * match's offset is known, a second pass collects every other match - possibly against different
 * elements too - that the *same* offset would also satisfy, so e.g. two identically-sized objects
 * whose top, center and bottom all align at once are all drawn, not just one of them.
 *
 * xLeft/xRight are the moving box's horizontal extent, used both for the crossing/overlap check and
 * to compute each guide line's span (perpendicular axis).
 */
/**
 * Below this gap (in document points) between the moving object's own extent and the matched
 * element's own extent (on the perpendicular axis), the guide line still spans their full union, as
 * before - the objects are close enough (or overlapping) that trimming wouldn't help. Above it, the
 * line is trimmed to just the empty gap between their two nearest edges, so it no longer runs on top
 * of either object's body (most noticeable when aligning two objects that are long on the
 * perpendicular axis, e.g. two perpendicular lines).
 */
constexpr double GUIDE_TRIM_MIN_GAP = 5.0;

/**
 * Computes the [from, to] span (perpendicular axis) for a guide line connecting an object spanning
 * [selfLo, selfHi] to another spanning [otherLo, otherHi]. If the two don't overlap and the gap
 * between their nearest edges exceeds GUIDE_TRIM_MIN_GAP, the line is trimmed to exactly that gap
 * (the empty space between them). Otherwise (overlapping, or too close to bother trimming), the
 * line spans their full union, as it always did before this trimming was added.
 */
static void computeGuideExtent(double selfLo, double selfHi, double otherLo, double otherHi, double& outFrom,
                                double& outTo) {
    if (selfHi <= otherLo && otherLo - selfHi > GUIDE_TRIM_MIN_GAP) {
        outFrom = selfHi;
        outTo = otherLo;
        return;
    }
    if (otherHi <= selfLo && selfLo - otherHi > GUIDE_TRIM_MIN_GAP) {
        outFrom = otherHi;
        outTo = selfLo;
        return;
    }
    outFrom = std::min(selfLo, otherLo);
    outTo = std::max(selfHi, otherHi);
}

/**
 * Result of computePageCenterX(): `centerX` is the horizontal center to snap to; `marginX`, if set,
 * is the position of the page's own vertical margin line (only for a Lined background), drawn as an
 * extra guide alongside the center line - see paint().
 */
struct PageCenterInfo {
    double centerX;
    std::optional<double> marginX;
};

/**
 * Computes where \"horizontally centered on the page\" means for `page`. For a plain page, this is
 * simply half the page width. For a Lined background (ruled paper with a vertical margin line -
 * see LinedBackgroundView), the margin splits the page into a usable area on one side and a margin
 * strip on the other; centering is done within that usable area instead of the full page width, and
 * the margin's own position is also returned, matching the same \"margin < 0 means the line goes on
 * the right\" convention as LinedBackgroundView itself.
 */
static auto computePageCenterX(const XojPage* page) -> PageCenterInfo {
    double pageWidth = page->getWidth();
    PageType bg = page->getBackgroundType();
    if (bg.format == PageTypeFormat::Lined) {
        BackgroundConfig config(bg.config);
        double margin = 72.0;  // matches LinedBackgroundView's own default
        config.loadValue(background_config_strings::CFG_MARGIN, margin);
        bool marginOnRight = margin < 0;
        if (marginOnRight) {
            margin += pageWidth;
        }
        double centerX = marginOnRight ? margin / 2.0 : (margin + pageWidth) / 2.0;
        return {centerX, margin};
    }
    return {pageWidth / 2.0, std::nullopt};
}

/**
 * Result of computeBlueGridX/Y(): if `forceOffset` is set, the moving object's position along the
 * sliding axis MUST snap to it (there are 2+ equally-spaced same-size crossing lines already on the
 * big line - a real grid). Otherwise (exactly one same-size crossing line found), `forceOffset` is
 * unset and the result is purely indicative: self can keep moving freely along the sliding axis.
 * `markerPositions` are the sliding-axis coordinates of every marker to draw (one short segment each,
 * parallel to self); `perpendicular` is the coordinate shared by all of them (the axis already fixed
 * by the boosted match); `markerHalfLength` is half of self's own length.
 */
struct BlueGridResult {
    std::optional<double> forceOffset;
    std::vector<double> markerPositions;
    double perpendicular;
    double markerHalfLength;
};

/**
 * Below this (document points), two positions are considered \"exactly\" the same length/spacing for
 * the \"blue grid\" feature - a tiny epsilon for floating-point safety, not a real user-facing
 * tolerance (which is deliberately zero for the grid-spacing check, per design).
 */
constexpr double BLUE_GRID_LENGTH_EPS = 0.5;

/**
 * Minimum allowed distance (in document points) between the moving object and the one fixed
 * same-size line found in the \"blue grid\" Case A (see computeBlueGridX/Y()). Trying to bring them
 * closer than this freezes the moving object at exactly this distance (on whichever side it
 * currently approaches from), until the cursor's raw position would put it further than this same
 * distance on the *other* side, at which point it jumps straight to the cursor's actual position and
 * resumes following it normally.
 */
constexpr double BLUE_GRID_MIN_SPACING = 5.0;

/**
 * If `bigLine` (already the target of an active boosted/blue match on the Y axis, i.e. `bigLine` is
 * horizontal and self is a small vertical line/arrow centered on it) has exactly one *other* small
 * vertical line/arrow of the same length as `selfLength` also crossing it, returns markers
 * extending the self-to-that-line spacing beyond self, in the direction away from it, all the way to
 * the end of `bigLine`'s shaft - purely indicative, `forceOffset` unset. If it has two or more such
 * lines, and they are spaced by exact multiples (including 1x) of their smallest mutual gap (strictly,
 * no tolerance), returns markers for the entire grid in both directions across the whole shaft, and
 * forces self to the grid position closest to `selfPos`. Otherwise (2+ found but not a valid regular
 * grid) returns nullopt - no markers, no forced offset. `selfPos` is self's current raw (pre-snap)
 * center position along X.
 */
static auto computeBlueGridX(const Element* bigLine, double selfPos, double selfLength, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<BlueGridResult> {
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double shaftLo = bigShaft.x;
    double shaftHi = bigShaft.x + bigShaft.width;
    double perpendicular = bigShaft.y + bigShaft.height / 2;

    std::vector<double> otherPositions;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (el == bigLine || std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isVerticalLike = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
        if (!isVerticalLike || std::abs(shaft.height - selfLength) > BLUE_GRID_LENGTH_EPS) {
            continue;
        }
        if (!rangesOverlap(shaftLo, shaftHi, shaft.x, shaft.x + shaft.width) ||
            perpendicular < shaft.y || perpendicular > shaft.y + shaft.height) {
            continue;
        }
        otherPositions.push_back(shaft.x + shaft.width / 2);
    }
    if (otherPositions.empty()) {
        return std::nullopt;
    }
    std::sort(otherPositions.begin(), otherPositions.end());

    if (otherPositions.size() == 1) {
        double fixedPos = otherPositions[0];
        double signedD = selfPos - fixedPos;
        double effectivePos = selfPos;
        std::optional<double> forceOffset;
        if (std::abs(signedD) < BLUE_GRID_MIN_SPACING) {
            double clampSign = (signedD >= 0) ? 1.0 : -1.0;
            effectivePos = fixedPos + clampSign * BLUE_GRID_MIN_SPACING;
            forceOffset = effectivePos;
        }
        double d = std::abs(effectivePos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (effectivePos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = effectivePos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{forceOffset, markers, perpendicular, selfLength / 2};
    }

    std::vector<double> gaps;
    for (size_t i = 1; i < otherPositions.size(); ++i) {
        gaps.push_back(otherPositions[i] - otherPositions[i - 1]);
    }
    double minGap = *std::min_element(gaps.begin(), gaps.end());
    if (minGap <= BLUE_GRID_LENGTH_EPS) {
        return std::nullopt;
    }
    for (double g: gaps) {
        double rounded = std::round(g / minGap);
        if (rounded < 1.0 || std::abs(g - rounded * minGap) > BLUE_GRID_LENGTH_EPS) {
            return std::nullopt;
        }
    }

    std::vector<double> markers;
    double p = otherPositions[0];
    while (p - minGap >= shaftLo - BLUE_GRID_LENGTH_EPS) {
        p -= minGap;
    }
    for (; p <= shaftHi + BLUE_GRID_LENGTH_EPS; p += minGap) {
        markers.push_back(p);
    }
    if (markers.empty()) {
        return std::nullopt;
    }
    double closest = markers[0];
    for (double m: markers) {
        if (std::abs(selfPos - m) < std::abs(selfPos - closest)) {
            closest = m;
        }
    }
    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

/// Same as computeBlueGridX(), but for a Y-axis boosted match: `bigLine` is vertical, self is a
/// small horizontal line/arrow, and the grid runs along Y instead of X.
static auto computeBlueGridY(const Element* bigLine, double selfPos, double selfLength, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<BlueGridResult> {
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double shaftLo = bigShaft.y;
    double shaftHi = bigShaft.y + bigShaft.height;
    double perpendicular = bigShaft.x + bigShaft.width / 2;

    std::vector<double> otherPositions;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (el == bigLine || std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isHorizontalLike = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
        if (!isHorizontalLike || std::abs(shaft.width - selfLength) > BLUE_GRID_LENGTH_EPS) {
            continue;
        }
        if (!rangesOverlap(shaftLo, shaftHi, shaft.y, shaft.y + shaft.height) ||
            perpendicular < shaft.x || perpendicular > shaft.x + shaft.width) {
            continue;
        }
        otherPositions.push_back(shaft.y + shaft.height / 2);
    }
    if (otherPositions.empty()) {
        return std::nullopt;
    }
    std::sort(otherPositions.begin(), otherPositions.end());

    if (otherPositions.size() == 1) {
        double fixedPos = otherPositions[0];
        double signedD = selfPos - fixedPos;
        double effectivePos = selfPos;
        std::optional<double> forceOffset;
        if (std::abs(signedD) < BLUE_GRID_MIN_SPACING) {
            double clampSign = (signedD >= 0) ? 1.0 : -1.0;
            effectivePos = fixedPos + clampSign * BLUE_GRID_MIN_SPACING;
            forceOffset = effectivePos;
        }
        double d = std::abs(effectivePos - fixedPos);
        if (d < 1e-6) {
            return std::nullopt;
        }
        double sign = (effectivePos >= fixedPos) ? 1.0 : -1.0;
        std::vector<double> markers;
        for (double p = effectivePos + sign * d; (sign > 0 ? p <= shaftHi : p >= shaftLo); p += sign * d) {
            markers.push_back(p);
        }
        if (markers.empty()) {
            return std::nullopt;
        }
        return BlueGridResult{forceOffset, markers, perpendicular, selfLength / 2};
    }

    std::vector<double> gaps;
    for (size_t i = 1; i < otherPositions.size(); ++i) {
        gaps.push_back(otherPositions[i] - otherPositions[i - 1]);
    }
    double minGap = *std::min_element(gaps.begin(), gaps.end());
    if (minGap <= BLUE_GRID_LENGTH_EPS) {
        return std::nullopt;
    }
    for (double g: gaps) {
        double rounded = std::round(g / minGap);
        if (rounded < 1.0 || std::abs(g - rounded * minGap) > BLUE_GRID_LENGTH_EPS) {
            return std::nullopt;
        }
    }

    std::vector<double> markers;
    double p = otherPositions[0];
    while (p - minGap >= shaftLo - BLUE_GRID_LENGTH_EPS) {
        p -= minGap;
    }
    for (; p <= shaftHi + BLUE_GRID_LENGTH_EPS; p += minGap) {
        markers.push_back(p);
    }
    if (markers.empty()) {
        return std::nullopt;
    }
    double closest = markers[0];
    for (double m: markers) {
        if (std::abs(selfPos - m) < std::abs(selfPos - closest)) {
            closest = m;
        }
    }
    return BlueGridResult{closest, markers, perpendicular, selfLength / 2};
}

/**
 * \"Line reposition on release\" (patch 8.6.4.5): if the moving line was boost-snapped (blue) to
 * `bigLine` when the drag ended, every OTHER plain line of the exact same length crossing `bigLine`
 * the same way (see the eligibility rule below) - the moving line included - is translated (never
 * resized) so that the point matching the current zone lands exactly on `bigLine`: its bottom edge
 * for the \"negative\" zone (e.g. above a horizontal big line), its center for the middle zone, its
 * top edge for the \"positive\" zone (e.g. below it). `isXAxis` says whether the crossing is on the X
 * or Y axis (i.e. whether \"family\" lines are horizontal or vertical). Registers a single
 * LineRepositionUndoAction covering every line actually moved (elements already exactly at their
 * target position are skipped, so releasing without any real zone change is a no-op). Only plain
 * lines (no ArrowKind) ever participate - see patch 8.6.3.2. The currently-selected element(s) are
 * checked separately from `layer->getElements()`, since they are physically removed from the layer
 * for the duration of the selection (see createFromElementOnActiveLayer()) and would otherwise never
 * take part in their own family's transformation.
 */
static void applyLineRepositionOnRelease(Control* control, Layer* layer, const PageRef& page,
                                          const Element* bigLine, bool isXAxis, int zone,
                                          const std::vector<const Element*>& selfElements) {
    if (bigLine == nullptr) {
        return;
    }
    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();
    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);

    // Determine self's own length (the \"same length as the moving line\" filter) from whichever of
    // the selected elements is itself an eligible plain line.
    double selfLength = -1;
    for (const Element* el: selfElements) {
        const auto* stroke = dynamic_cast<const Stroke*>(el);
        if (stroke != nullptr && stroke->getArrowKind() == ArrowKind::NONE && stroke->getPointCount() == 2) {
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            selfLength = isXAxis ? shaft.width : shaft.height;
            break;
        }
    }
    if (selfLength < 0) {
        return;
    }

    auto isEligibleFamilyMember = [&](const Element* el) -> bool {
        if (el == bigLine) {
            return false;
        }
        const auto* stroke = dynamic_cast<const Stroke*>(el);
        if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
            return false;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool matchesOrientation = isXAxis ? (shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD)
                                           : (shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD);
        if (!matchesOrientation) {
            return false;
        }
        double length = isXAxis ? shaft.width : shaft.height;
        if (std::abs(length - selfLength) > BLUE_GRID_LENGTH_EPS) {
            return false;
        }
        if (isXAxis) {
            return rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) &&
                   crossingCoord >= shaft.x && crossingCoord <= shaft.x + shaft.width;
        }
        return rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) &&
               crossingCoord >= shaft.y && crossingCoord <= shaft.y + shaft.height;
    };

    // The currently-selected line is deliberately NOT added to `family` here (patch 8.6.7): it was
    // already dynamically anchored to the correct zone-specific reference point live during the drag
    // (see the \"Dynamic anchor\" code in mouseMove()), and its final position was already committed by
    // updateContent() just before this function runs. Repositioning it again here would move it a
    // second time, off of its already-correct spot. selfElements is still used above purely to learn
    // self's own length.
    std::vector<Element*> family;
    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (isEligibleFamilyMember(el)) {
            family.push_back(el);
        }
    }
    if (family.empty()) {
        return;
    }

    std::vector<std::pair<Element*, double>> elementsWithDelta;
    constexpr double MOVE_EPS = 0.01;  // skip elements already exactly at their target position
    for (Element* el: family) {
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        double refPoint;
        if (zone < 0) {
            refPoint = isXAxis ? (shaft.x + shaft.width) : (shaft.y + shaft.height);  // far edge
        } else if (zone > 0) {
            refPoint = isXAxis ? shaft.x : shaft.y;  // near edge
        } else {
            refPoint = isXAxis ? (shaft.x + shaft.width / 2) : (shaft.y + shaft.height / 2);  // center
        }
        double delta = crossingCoord - refPoint;
        if (std::abs(delta) > MOVE_EPS) {
            elementsWithDelta.emplace_back(el, delta);
        }
    }
    if (elementsWithDelta.empty()) {
        return;
    }

    auto action = std::make_unique<LineRepositionUndoAction>(page, elementsWithDelta, isXAxis);
    action->redo(control);
    control->getUndoRedoHandler()->addUndoAction(std::move(action));
}


/**
 * \"Ordinary anchor point depends on mode\" (patch 8.6.8, point 2): determines which single point
 * should represent a plain small line `el` for the ORDINARY (green/pink) tier's own candidate list,
 * instead of the usual three (near edge, center, far edge). Purely geometric, deduced fresh each
 * time from `el`'s own current shape and any big perpendicular line it happens to cross right now -
 * nothing is stored. Returns -1 if `el`'s far edge (e.g. bottom, for a vertical line) coincides with
 * a crossing big line's center (i.e. el is in \"Top\" mode), +1 if its near edge does (\"Below\" mode),
 * or 0 for every other case (not a plain line, not crossing any big line at all, or crossing one but
 * still centered on it, i.e. \"Middle\") - 0 means \"use the ordinary center\", matching the same value
 * used elsewhere for Middle.
 */
static std::optional<int> detectLineZoneForOrdinaryAnchor(const Element* el, Layer* layer,
                                                            const std::vector<const Element*>& excluded,
                                                            double smallMarkMaxLength) {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
        return std::nullopt;
    }
    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
    // Patch 11.7: this whole \"family\" mechanism (forcing a single, always-pink ordinary-tier
    // candidate for a line that crosses a big perpendicular line) is only appropriate for genuinely
    // SMALL lines (graduation ticks) - the same length bound used to decide boosted-tier eligibility
    // elsewhere (Settings::getSmallMarkMaxLength()). A longer line that happens to geometrically cross
    // some other perpendicular line keeps the normal 3-candidate (near/center/far) ordinary-tier
    // behavior and its usual colors, regardless of any \"family\" it might otherwise appear to belong
    // to - fixes a regression from patch 11.5.3, where any line crossing a big line lost 2 of its 3
    // candidates as soon as a horizontal line was also present on the page, even for lines far too
    // long to be a graduation tick.
    double lineLength = isVertical ? shaft.height : shaft.width;
    if (lineLength >= smallMarkMaxLength) {
        return std::nullopt;
    }
    // Patch 11.5.3: tracks whether `el` was found crossing ANY big line at all (regardless of
    // Top/Below/Middle), so the two different reasons for returning a Middle-equivalent value can be
    // told apart below - genuinely centered on a real big line (0) vs. not crossing any big line at
    // all (nullopt, unchanged from before).
    bool foundCrossingBigLine = false;
    for (auto& bigPtr: layer->getElements()) {
        const Element* big = bigPtr.get();
        if (big == el || std::find(excluded.begin(), excluded.end(), big) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> bigShaft = big->getSnappedBounds();
        if (isVertical) {
            bool bigIsHorizontal = bigShaft.height <= THIN_AXIS_THRESHOLD && bigShaft.width > THIN_AXIS_THRESHOLD;
            if (!bigIsHorizontal ||
                !rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width)) {
                continue;
            }
            foundCrossingBigLine = true;
            double bigCenter = bigShaft.y + bigShaft.height / 2;
            double farEdge = shaft.y + shaft.height;
            double nearEdge = shaft.y;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        } else {
            bool bigIsVertical = bigShaft.width <= THIN_AXIS_THRESHOLD && bigShaft.height > THIN_AXIS_THRESHOLD;
            if (!bigIsVertical ||
                !rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height)) {
                continue;
            }
            foundCrossingBigLine = true;
            double bigCenter = bigShaft.x + bigShaft.width / 2;
            double farEdge = shaft.x + shaft.width;
            double nearEdge = shaft.x;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        }
    }
    return foundCrossingBigLine ? std::optional<int>(0) : std::nullopt;
}

/// Given a plain small line's own zone (see detectLineZoneForOrdinaryAnchor()), builds the single
/// forced ordinary-tier candidate representing it: its far edge for Top (-1), near edge for Below
/// (+1), or its own geometric center for Middle (0) - matching the \"family\" anchor conventions used
/// throughout the rest of this feature (patch 8.6.8). Patch 11.5.3: the Middle candidate is tagged
/// isCenter=false (not true) - a line that belongs to a graduation family should always render its
/// ordinary-tier guide as pink, not green, regardless of which of the three modes it happens to be
/// in right now, since all three represent the same family-anchor concept from the user's point of
/// view.
static auto buildForcedLineCandidate(double from, double size, int zone) -> std::vector<AlignmentCandidate> {
    if (zone < 0) {
        return {{from + size, false}};
    }
    if (zone > 0) {
        return {{from, false}};
    }
    return {{from + size / 2, false}};
}


/**
 * If the moving text box, placed at x (width wide) with Y-extent [yTop, yBottom], has two vertical
 * lines/arrows of the same length on `layer` whose own Y-extent fully contains [yTop, yBottom] (i.e.
 * they bound a table column, extending past the textbox on both ends), returns a match centering the
 * textbox horizontally between them. The guide is drawn in yellow, parallel to the two lines (i.e.
 * vertical), spanning the shared (overlapping) length of the two lines. Only ever called when the
 * moving selection is a single Text, TexImage, or Image.
 */
static auto findTableCenterX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<xoj::util::Rectangle<double>> verticalLines;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isVerticalLine = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
        if (!isVerticalLine) {
            continue;
        }
        if (shaft.y > yTop || shaft.y + shaft.height < yBottom) {
            continue;  // must extend past the textbox on both ends
        }
        verticalLines.push_back(shaft);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;
    double selfCenter = x + width / 2;
    for (size_t i = 0; i < verticalLines.size(); ++i) {
        for (size_t j = 0; j < verticalLines.size(); ++j) {
            if (i == j) {
                continue;
            }
            const auto& left = verticalLines[i];
            const auto& right = verticalLines[j];
            if (!(left.x < right.x)) {
                continue;  // only consider \"left\" strictly left of \"right\" (each pair handled once)
            }
            if (std::abs(left.height - right.height) > tolerance) {
                continue;  // same length, within the usual tolerance
            }
            // Patch 11.10: reject this pair if it isn't the smallest possible cell - i.e. if some
            // other vertical line on the layer lies strictly between them. Without this check, a
            // 2x2 (or larger) block of same-length lines could be mistaken for a single wide \"cell\"
            // spanning multiple real columns, and the resulting guideline could land exactly on top
            // of one of the table's own intermediate lines.
            bool hasLineBetween = false;
            for (size_t k = 0; k < verticalLines.size(); ++k) {
                if (k == i || k == j) {
                    continue;
                }
                if (verticalLines[k].x > left.x && verticalLines[k].x < right.x) {
                    hasLineBetween = true;
                    break;
                }
            }
            if (hasLineBetween) {
                continue;
            }
            double midpoint = (left.x + right.x) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {
                bestDist = dist;
                double spanFrom = std::max(left.y, right.y);
                double spanTo = std::min(left.y + left.height, right.y + right.height);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }

    // Patch 11.9: independently reimplements the \"3-sided cell\" concept from the (separate)
    // table_writing_assist patch series - NOT a code dependency, just the same geometric rule (patch
    // 12.4's rule 5 there): a cell missing exactly one of its 4 sides has that side closed off by the
    // matching endpoint of whichever adjacent perpendicular line was found. Here specifically: the
    // nearest top/bottom horizontals (any lengths) plus exactly one of left/right - the missing one
    // is closed off, giving a well-defined cell center even with only 3 sides drawn. Competes for
    // `best` exactly like the search above (an additional case of the same already-implemented
    // \"table center\" alignment, not a new tier). The guide's own extent, like the search above,
    // always matches the length of whichever single vertical line is actually present (the one
    // parallel to this axis) - never derived from the perpendicular top/bottom lines.
    {
        double selfY = (yTop + yBottom) / 2.0;
        double leftX = -std::numeric_limits<double>::infinity();
        double rightX = std::numeric_limits<double>::infinity();
        double topY = -std::numeric_limits<double>::infinity();
        double bottomY = std::numeric_limits<double>::infinity();
        bool hasLeft = false;
        bool hasRight = false;
        bool hasTop = false;
        bool hasBottom = false;
        xoj::util::Rectangle<double> leftLine;
        xoj::util::Rectangle<double> rightLine;
        xoj::util::Rectangle<double> topLine;
        xoj::util::Rectangle<double> bottomLine;
        for (auto& elPtr: layer->getElements()) {
            const Element* el = elPtr.get();
            if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
            bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
            if (isVertical && shaft.y <= selfY && selfY <= shaft.y + shaft.height) {
                double lineX = shaft.x + shaft.width / 2.0;
                if (lineX <= selfCenter && lineX > leftX) {
                    leftX = lineX;
                    hasLeft = true;
                    leftLine = shaft;
                } else if (lineX > selfCenter && lineX < rightX) {
                    rightX = lineX;
                    hasRight = true;
                    rightLine = shaft;
                }
            } else if (isHorizontal && shaft.x <= selfCenter && selfCenter <= shaft.x + shaft.width) {
                double lineY = shaft.y + shaft.height / 2.0;
                if (lineY <= selfY && lineY > topY) {
                    topY = lineY;
                    hasTop = true;
                    topLine = shaft;
                } else if (lineY > selfY && lineY < bottomY) {
                    bottomY = lineY;
                    hasBottom = true;
                    bottomLine = shaft;
                }
            }
        }
        if (hasTop && hasBottom && (hasLeft != hasRight)) {
            auto rectanglesIntersect = [](const xoj::util::Rectangle<double>& a,
                                           const xoj::util::Rectangle<double>& b) {
                return a.x <= b.x + b.width && a.x + a.width >= b.x && a.y <= b.y + b.height &&
                       a.y + a.height >= b.y;
            };
            bool consistent = (!hasLeft || rectanglesIntersect(topLine, leftLine)) &&
                              (!hasLeft || rectanglesIntersect(bottomLine, leftLine)) &&
                              (!hasRight || rectanglesIntersect(topLine, rightLine)) &&
                              (!hasRight || rectanglesIntersect(bottomLine, rightLine));
            if (consistent) {
                if (!hasRight) {
                    rightX = topLine.x + topLine.width;
                }
                if (!hasLeft) {
                    leftX = topLine.x;
                }
                double midpoint = (leftX + rightX) / 2.0;
                double dist = std::abs(selfCenter - midpoint);
                if (dist < bestDist) {
                    bestDist = dist;
                    const auto& presentLine = hasLeft ? leftLine : rightLine;
                    double spanFrom = presentLine.y;
                    double spanTo = presentLine.y + presentLine.height;
                    best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                    best->isTableCenter = true;
                }
            }
        }
    }

    return best;
}

/// Same as findTableCenterX(), but for two horizontal lines bounding a table row, centering the
/// textbox vertically between them.
static auto findTableCenterY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<xoj::util::Rectangle<double>> horizontalLines;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isHorizontalLine = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
        if (!isHorizontalLine) {
            continue;
        }
        if (shaft.x > xLeft || shaft.x + shaft.width < xRight) {
            continue;
        }
        horizontalLines.push_back(shaft);
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;
    double selfCenter = y + height / 2;
    for (size_t i = 0; i < horizontalLines.size(); ++i) {
        for (size_t j = 0; j < horizontalLines.size(); ++j) {
            if (i == j) {
                continue;
            }
            const auto& top = horizontalLines[i];
            const auto& bottom = horizontalLines[j];
            if (!(top.y < bottom.y)) {
                continue;
            }
            if (std::abs(top.width - bottom.width) > tolerance) {
                continue;
            }
            // Patch 11.10: see findTableCenterX()'s own comment above - mirrored here for the Y axis.
            bool hasLineBetween = false;
            for (size_t k = 0; k < horizontalLines.size(); ++k) {
                if (k == i || k == j) {
                    continue;
                }
                if (horizontalLines[k].y > top.y && horizontalLines[k].y < bottom.y) {
                    hasLineBetween = true;
                    break;
                }
            }
            if (hasLineBetween) {
                continue;
            }
            double midpoint = (top.y + bottom.y) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {
                bestDist = dist;
                double spanFrom = std::max(top.x, bottom.x);
                double spanTo = std::min(top.x + top.width, bottom.x + bottom.width);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }

    // Patch 11.9: see findTableCenterX()'s own comment for the full explanation - mirrored here for
    // the Y axis: nearest left/right verticals (any lengths) plus exactly one of top/bottom, the
    // missing one closed off via the same rule. The guide's own extent always matches the length of
    // whichever single horizontal line is actually present (the one parallel to this axis) - never
    // derived from the perpendicular left/right lines.
    {
        double selfX = (xLeft + xRight) / 2.0;
        double leftX = -std::numeric_limits<double>::infinity();
        double rightX = std::numeric_limits<double>::infinity();
        double topY = -std::numeric_limits<double>::infinity();
        double bottomY = std::numeric_limits<double>::infinity();
        bool hasLeft = false;
        bool hasRight = false;
        bool hasTop = false;
        bool hasBottom = false;
        xoj::util::Rectangle<double> leftLine;
        xoj::util::Rectangle<double> rightLine;
        xoj::util::Rectangle<double> topLine;
        xoj::util::Rectangle<double> bottomLine;
        for (auto& elPtr: layer->getElements()) {
            const Element* el = elPtr.get();
            if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
            bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
            if (isVertical && shaft.y <= selfCenter && selfCenter <= shaft.y + shaft.height) {
                double lineX = shaft.x + shaft.width / 2.0;
                if (lineX <= selfX && lineX > leftX) {
                    leftX = lineX;
                    hasLeft = true;
                    leftLine = shaft;
                } else if (lineX > selfX && lineX < rightX) {
                    rightX = lineX;
                    hasRight = true;
                    rightLine = shaft;
                }
            } else if (isHorizontal && shaft.x <= selfX && selfX <= shaft.x + shaft.width) {
                double lineY = shaft.y + shaft.height / 2.0;
                if (lineY <= selfCenter && lineY > topY) {
                    topY = lineY;
                    hasTop = true;
                    topLine = shaft;
                } else if (lineY > selfCenter && lineY < bottomY) {
                    bottomY = lineY;
                    hasBottom = true;
                    bottomLine = shaft;
                }
            }
        }
        if (hasLeft && hasRight && (hasTop != hasBottom)) {
            auto rectanglesIntersect = [](const xoj::util::Rectangle<double>& a,
                                           const xoj::util::Rectangle<double>& b) {
                return a.x <= b.x + b.width && a.x + a.width >= b.x && a.y <= b.y + b.height &&
                       a.y + a.height >= b.y;
            };
            bool consistent = (!hasTop || rectanglesIntersect(leftLine, topLine)) &&
                              (!hasTop || rectanglesIntersect(rightLine, topLine)) &&
                              (!hasBottom || rectanglesIntersect(leftLine, bottomLine)) &&
                              (!hasBottom || rectanglesIntersect(rightLine, bottomLine));
            if (consistent) {
                if (!hasBottom) {
                    bottomY = leftLine.y + leftLine.height;
                }
                if (!hasTop) {
                    topY = leftLine.y;
                }
                double midpoint = (topY + bottomY) / 2.0;
                double dist = std::abs(selfCenter - midpoint);
                if (dist < bestDist) {
                    bestDist = dist;
                    const auto& presentLine = hasTop ? topLine : bottomLine;
                    double spanFrom = presentLine.x;
                    double spanTo = presentLine.x + presentLine.width;
                    best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                    best->isTableCenter = true;
                }
            }
        }
    }

    return best;
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance,
                            double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                            double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    // Patch 11.6: self's own Y-axis center candidate uses the same Text-aware center fraction as
    // other elements do (see candidatesOther below) - previously hardcoded to 0.5 regardless of
    // whether self happened to be a single-line Text itself, which was an asymmetry bug (a selected
    // single-line textbox's OWN center guideline never honored getTextYCenterFraction(), while it
    // correctly did so when that same textbox was the *other*, non-moving element).
    double selfCenterFraction = selfIsSingleLineText ? textYCenterFraction : 0.5;
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(
            y, height, selfCenterFraction, isSmallMark(xRight - xLeft, height, selfIsLine, smallMarkMaxLength));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * crossBoostFactor;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool crossEligible = isSmallCrossingBigPerpendicular(xRight - xLeft, height, shaft.width, shaft.height, CrossAxis::Y, smallMarkMaxLength) &&
                              rangesOverlap(xLeft, xRight, shaft.x, shaft.x + shaft.width);
        if (!crossEligible) {
            continue;
        }
        double coValue = shaft.y + shaft.height / 2;
        double dist = std::abs((y + height / 2) - coValue);
        if (dist < bestBoostedDist) {
            bestBoostedDist = dist;
            bestBoosted = AlignmentMatch{coValue - (y + height / 2),
                                          coValue,
                                          std::min(xLeft, shaft.x),
                                          std::max(xRight, shaft.x + shaft.width),
                                          true,
                                          true};
            bestBoosted->boostedTarget = el;
        }
    }
    if (bestBoosted) {
        return AlignmentSearchResult{bestBoosted->offset, {*bestBoosted}};
    }

    // --- ordinary tier: single closest match, any kind ---
    std::optional<AlignmentMatch> bestAny;
    double bestAnyDist = tolerance;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        // An element eligible for the boosted (blue) perpendicular-cross relationship with this
        // selection is skipped here entirely: its along-axis center (e.g. a long arrow's own
        // vertical mid-point, on the crossed axis) shouldn't also offer a separate ordinary match.
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        // Patch 11.6: a multi-line Text's own center guideline is always the true geometric
        // center (0.5), never the configurable fraction - that fraction exists specifically to
        // compensate for a SINGLE line of text's visual weight not sitting at its exact geometric
        // middle (ascenders/descenders), which isn't a meaningful concept for a multi-line block.
        const Text* otherText = dynamic_cast<const Text*>(el);
        bool otherIsSingleLineText = otherText != nullptr && otherText->getText().find('\\n') == std::string::npos;
        double otherCenterFraction = otherIsSingleLineText ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded, smallMarkMaxLength); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&
                                otherStrokeForSmallMark->getArrowKind() == ArrowKind::NONE &&
                                otherStrokeForSmallMark->getPointCount() == 2;
            candidatesOther = buildCandidates(
                    snapped.y, snapped.height, otherCenterFraction,
                    isSmallMark(snapped.width, snapped.height, otherIsLine, smallMarkMaxLength) ||
                     isCrossShape(otherStrokeForSmallMark));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              guideFrom,
                                              guideTo,
                                              cs.isCenter || co.isCenter,
                                              false};
                    bestAny->selfIsCenter = cs.isCenter;
                    bestAny->otherIsCenter = co.isCenter;
                    bestAny->selfOnFromSide = xLeft <= snapped.x;
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
    // Patch 9.2/10.10.2: `groupTolerance` is a much stricter tolerance than the first pass'
    // `tolerance` - see ALIGNMENT_GROUP_TOLERANCE_PX's own comment for why. Now received directly as
    // a parameter, computed once by the caller (which has access to `settings`).
    std::vector<AlignmentMatch> guides;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        // Patch 11.6: a multi-line Text's own center guideline is always the true geometric
        // center (0.5), never the configurable fraction - that fraction exists specifically to
        // compensate for a SINGLE line of text's visual weight not sitting at its exact geometric
        // middle (ascenders/descenders), which isn't a meaningful concept for a multi-line block.
        const Text* otherText = dynamic_cast<const Text*>(el);
        bool otherIsSingleLineText = otherText != nullptr && otherText->getText().find('\\n') == std::string::npos;
        double otherCenterFraction = otherIsSingleLineText ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded, smallMarkMaxLength); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&
                                otherStrokeForSmallMark->getArrowKind() == ArrowKind::NONE &&
                                otherStrokeForSmallMark->getPointCount() == 2;
            candidatesOther = buildCandidates(
                    snapped.y, snapped.height, otherCenterFraction,
                    isSmallMark(snapped.width, snapped.height, otherIsLine, smallMarkMaxLength) ||
                     isCrossShape(otherStrokeForSmallMark));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < groupTolerance) {
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);
                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};
                    guide.selfIsCenter = cs.isCenter;
                    guide.otherIsCenter = co.isCenter;
                    guide.selfOnFromSide = xLeft <= snapped.x;
                    guides.push_back(guide);
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
}

/// Same as findAlignmentY(), but for the horizontal candidates (left / horizontal-center / right).
/// yTop/yBottom are the moving box's vertical extent, used for the crossing/overlap check and the
/// guide line's span. Unlike findAlignmentY(), there is no Text-specific center fraction here.
static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance,
                            double groupTolerance, double crossBoostFactor, double smallMarkMaxLength,
                            bool selfIsLine, Layer* layer, const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf =
            buildCandidates(x, width, 0.5, isSmallMark(width, yBottom - yTop, selfIsLine, smallMarkMaxLength));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * crossBoostFactor;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool crossEligible = isSmallCrossingBigPerpendicular(width, yBottom - yTop, shaft.width, shaft.height, CrossAxis::X, smallMarkMaxLength) &&
                              rangesOverlap(yTop, yBottom, shaft.y, shaft.y + shaft.height);
        if (!crossEligible) {
            continue;
        }
        double coValue = shaft.x + shaft.width / 2;
        double dist = std::abs((x + width / 2) - coValue);
        if (dist < bestBoostedDist) {
            bestBoostedDist = dist;
            bestBoosted = AlignmentMatch{coValue - (x + width / 2),
                                          coValue,
                                          std::min(yTop, shaft.y),
                                          std::max(yBottom, shaft.y + shaft.height),
                                          true,
                                          true};
            bestBoosted->boostedTarget = el;
        }
    }
    if (bestBoosted) {
        return AlignmentSearchResult{bestBoosted->offset, {*bestBoosted}};
    }

    // --- ordinary tier: single closest match, any kind ---
    std::optional<AlignmentMatch> bestAny;
    double bestAnyDist = tolerance;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        // An element eligible for the boosted (blue) perpendicular-cross relationship with this
        // selection is skipped here entirely: its along-axis center (e.g. a long arrow's own
        // horizontal mid-point, on the crossed axis) shouldn't also offer a separate ordinary match.
        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded, smallMarkMaxLength); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&
                                otherStrokeForSmallMark->getArrowKind() == ArrowKind::NONE &&
                                otherStrokeForSmallMark->getPointCount() == 2;
            candidatesOther = buildCandidates(
                    snapped.x, snapped.width, 0.5,
                    isSmallMark(snapped.width, snapped.height, otherIsLine, smallMarkMaxLength) ||
                     isCrossShape(otherStrokeForSmallMark));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              guideFrom,
                                              guideTo,
                                              cs.isCenter || co.isCenter,
                                              false};
                    bestAny->selfIsCenter = cs.isCenter;
                    bestAny->otherIsCenter = co.isCenter;
                    bestAny->selfOnFromSide = yTop <= snapped.y;
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
    // Patch 9.2/10.10.2: see the Y-axis findAlignmentY() above for the full explanation.
    std::vector<AlignmentMatch> guides;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
            continue;
        }
        double ew = el->getElementWidth();
        double ex = el->getX();
        double eh = el->getElementHeight();
        double ey = el->getY();
        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded, smallMarkMaxLength); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&
                                otherStrokeForSmallMark->getArrowKind() == ArrowKind::NONE &&
                                otherStrokeForSmallMark->getPointCount() == 2;
            candidatesOther = buildCandidates(
                    snapped.x, snapped.width, 0.5,
                    isSmallMark(snapped.width, snapped.height, otherIsLine, smallMarkMaxLength) ||
                     isCrossShape(otherStrokeForSmallMark));
        }
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < groupTolerance) {
                    double guideFrom;
                    double guideTo;
                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);
                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};
                    guide.selfIsCenter = cs.isCenter;
                    guide.otherIsCenter = co.isCenter;
                    guide.selfOnFromSide = yTop <= snapped.y;
                    guides.push_back(guide);
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
}/**
 * \"Starting zone\" detection (patch 8.6.4.6): mirrors the \"already repositioned\" virtual-center trick
 * used during dragging (see EditSelection::mouseMove()), but applied ONCE, at the very start of a
 * drag (see EditSelection::mouseDown()), to self's own pre-drag geometry [x, y, width, height]. Tries
 * self's true center first (Middle, zone 0), then each of its own edges as a virtual center: if
 * self's own top edge is the one actually touching a big line (i.e. self extends downward from it),
 * that's the \"Below\" zone (+1); if self's own bottom edge is the anchor (self extends upward), that's
 * the \"Top\" zone (-1). Checks both axes (Y first, then X). Returns 0 (Middle) if self isn't currently
 * boosted at all.
 */
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, bool& outWasBoosted) {
    outWasBoosted = false;
    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, groupTolerance, textYCenterFraction,
                                      crossBoostFactor, smallMarkMaxLength, selfIsLine, selfIsSingleLineText, layer,
                                      excluded, visibleRect);
    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, groupTolerance,
                                     textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine, selfIsSingleLineText,
                                     layer, excluded, visibleRect);
    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"
    }
    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, groupTolerance,
                                        textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine,
                                        selfIsSingleLineText, layer, excluded, visibleRect);
    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"
    }

    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, groupTolerance, crossBoostFactor,
                                      smallMarkMaxLength, selfIsLine, layer, excluded, visibleRect);
    if (matchXReal && !matchXReal->guides.empty() && matchXReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchXLeft = findAlignmentX(x - width / 2, width, y, y + height, tolerance, groupTolerance,
                                      crossBoostFactor, smallMarkMaxLength, selfIsLine, layer, excluded,
                                      visibleRect);
    if (matchXLeft && !matchXLeft->guides.empty() && matchXLeft->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;
    }
    auto matchXRight = findAlignmentX(x + width / 2, width, y, y + height, tolerance, groupTolerance,
                                       crossBoostFactor, smallMarkMaxLength, selfIsLine, layer, excluded,
                                       visibleRect);
    if (matchXRight && !matchXRight->guides.empty() && matchXRight->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;
    }
    return 0;
}

void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {
    double zoom = this->view->getXournal()->getZoom();

    if (this->mouseDownType == CURSOR_SELECTION_MOVE) {
        // compute translation (without snapping)
        double dx = mouseX / zoom - this->snappedBounds.x - this->relMousePosX;
        double dy = mouseY / zoom - this->snappedBounds.y - this->relMousePosY;

        // Smart alignment guides: snap the moving selection's bounding box edges/centers to those of
        // other elements on the same layer, if close enough, and remember the match to draw a guide
        // line connecting the two objects (see paint()). Only elements currently visible on screen
        // are considered (an anchor point scrolled out of view would be a confusing match).
        bool objectSnappedX = false;
        bool objectSnappedY = false;
        if (settings != nullptr && settings->isSnapToObjects() && this->sourceLayer != nullptr &&
            this->rotation == 0.0) {
            xoj::util::Rectangle<double>* visibleRectPtr = this->view->getXournal()->getVisibleRect(this->view);
            if (visibleRectPtr != nullptr) {
                xoj::util::Rectangle<double> visibleRect = *visibleRectPtr;
                delete visibleRectPtr;

                double tolerance = settings->getAlignmentSnapTolerancePx() / zoom;
                // Patch 10.10.2: computed once here (mirroring `tolerance` itself) and threaded
                // through to findAlignmentX/Y() as an explicit parameter, since those are free
                // functions without direct access to `settings`.
                double groupTolerance =
                        tolerance * (ALIGNMENT_GROUP_TOLERANCE_PX / settings->getAlignmentSnapTolerancePx());
                std::vector<const Element*> excluded = this->getElementsView().clone();
                double candidateX = this->snappedBounds.x + dx;
                double candidateY = this->snappedBounds.y + dy;
                double width = this->snappedBounds.width;
                double height = this->snappedBounds.height;

                // Patch 10.10.3: true only if self is a single plain 2-point line (ArrowKind::NONE) -
                // computed once, up front, since it's now needed by findAlignmentX/Y() themselves
                // (isSmallMark(), ordinary tier) as well as by the arrow-discard check just below
                // (boosted tier).
                bool selfIsLine = false;
                bool selfIsArrow = false;
                {
                    auto selfElementsForLineCheck = this->getElementsView();
                    if (selfElementsForLineCheck.size() == 1) {
                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForLineCheck.begin())) {
                            selfIsArrow = selfStroke->getArrowKind() != ArrowKind::NONE;
                            selfIsLine = !selfIsArrow && selfStroke->getPointCount() == 2;
                        }
                    }
                }

                // Patch 11.6: true only if self is a single Text element whose content has no line
                // break - see findAlignmentY()'s own comment on selfCenterFraction for why this
                // matters.
                bool selfIsSingleLineText = false;
                {
                    auto selfElementsForTextCheck = this->getElementsView();
                    if (selfElementsForTextCheck.size() == 1) {
                        if (const auto* selfText = dynamic_cast<const Text*>(*selfElementsForTextCheck.begin())) {
                            selfIsSingleLineText = selfText->getText().find('\\n') == std::string::npos;
                        }
                    }
                }

                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,
                                              groupTolerance, settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, this->sourceLayer,
                                              excluded, visibleRect);
                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              groupTolerance, settings->getTextYCenterFraction(),
                                              settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, selfIsSingleLineText,
                                              this->sourceLayer, excluded, visibleRect);

                // An arrow or double arrow, however small, is never eligible to be the \"small\"
                // crossing side of a boosted (blue) match - only plain lines are. If self is an
                // arrow and the search above found one anyway, discard it outright: on that axis,
                // self simply gets no alignment snap at all in that case (not even the ordinary
                // tier), rather than threading an extra flag through findAlignmentX/Y themselves.
                if (selfIsArrow) {
                    if (matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted) {
                        matchX = std::nullopt;
                    }
                    if (matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted) {
                        matchY = std::nullopt;
                    }
                }

                // \"Already halved\" self detection (patch 8.6.4, point 3): if self doesn't already have
                // a boosted match using its own true center, try treating each of its own edges as a
                // \"virtual center\" instead (by searching with a same-size box centered on that edge) -
                // this lets a line that was previously halved by the \"half/double on release\" feature
                // (now anchored at one edge rather than truly centered) still find and reconnect to the
                // big line it was cut from. Whichever of the three (real center, virtual near-edge
                // center, virtual far-edge center) gives the closest boosted match wins; offsets are
                // translated back to the real candidateX/candidateY frame before use. Arrows are
                // excluded here too, matching the \"only plain lines\" scope of the whole feature.
                //
                // selfAnchorY/selfAnchorX track which point should stand in for \"self's position\" when
                // computing the Top/Middle/Below zone further below: self's true center by default, or
                // whichever edge just won a virtual match above (the point actually touching the big
                // line right now).
                double selfAnchorY = candidateY + height / 2;
                double selfAnchorX = candidateX + width / 2;
                {
                    bool selfIsArrowForVirtualCheck = false;
                    auto selfElementsForVirtualCheck = this->getElementsView();
                    if (selfElementsForVirtualCheck.size() == 1) {
                        if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForVirtualCheck.begin())) {
                            selfIsArrowForVirtualCheck = selfStroke->getArrowKind() != ArrowKind::NONE;
                        }
                    }
                    if (!selfIsArrowForVirtualCheck) {
                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                        if (!matchYAlreadyBoosted) {
                            auto matchYVirtualTop = findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,
                                                            tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                            settings->getPerpendicularCrossBoostFactor(),
                                                            settings->getSmallMarkMaxLength(),
                                                            selfIsLine, selfIsSingleLineText,
                                                            this->sourceLayer, excluded, visibleRect);
                            auto matchYVirtualBottom = findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,
                                                               tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                               settings->getPerpendicularCrossBoostFactor(),
                                                               settings->getSmallMarkMaxLength(),
                                                               selfIsLine, selfIsSingleLineText,
                                                               this->sourceLayer, excluded, visibleRect);
                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&
                                                 matchYVirtualTop->guides.front().isBoosted;
                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&
                                                    matchYVirtualBottom->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetY;
                            if (topIsBoosted) {
                                double realOffset = matchYVirtualTop->offset - height / 2;
                                bestRealOffsetY = realOffset;
                                matchY = AlignmentSearchResult{realOffset, matchYVirtualTop->guides};
                                selfAnchorY = candidateY;  // the top edge (raw, pre-snap, like the default case)
                            }
                            if (bottomIsBoosted) {
                                double realOffset = matchYVirtualBottom->offset + height / 2;
                                if (!bestRealOffsetY || std::abs(realOffset) < std::abs(*bestRealOffsetY)) {
                                    matchY = AlignmentSearchResult{realOffset, matchYVirtualBottom->guides};
                                    selfAnchorY = candidateY + height;  // the bottom edge (raw, pre-snap)
                                }
                            }
                        }
                        bool matchXAlreadyBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                        if (!matchXAlreadyBoosted) {
                            auto matchXVirtualLeft = findAlignmentX(candidateX - width / 2, width, candidateY, candidateY + height,
                                                             tolerance, groupTolerance,
                                                             settings->getPerpendicularCrossBoostFactor(),
                                                             settings->getSmallMarkMaxLength(),
                                                             selfIsLine,
                                                             this->sourceLayer, excluded, visibleRect);
                            auto matchXVirtualRight = findAlignmentX(candidateX + width / 2, width, candidateY, candidateY + height,
                                                              tolerance, groupTolerance,
                                                              settings->getPerpendicularCrossBoostFactor(),
                                                              settings->getSmallMarkMaxLength(),
                                                              selfIsLine,
                                                              this->sourceLayer, excluded, visibleRect);
                            bool leftIsBoosted = matchXVirtualLeft && !matchXVirtualLeft->guides.empty() &&
                                                  matchXVirtualLeft->guides.front().isBoosted;
                            bool rightIsBoosted = matchXVirtualRight && !matchXVirtualRight->guides.empty() &&
                                                   matchXVirtualRight->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetX;
                            if (leftIsBoosted) {
                                double realOffset = matchXVirtualLeft->offset - width / 2;
                                bestRealOffsetX = realOffset;
                                matchX = AlignmentSearchResult{realOffset, matchXVirtualLeft->guides};
                                selfAnchorX = candidateX;  // the left edge (raw, pre-snap, like the default case)
                            }
                            if (rightIsBoosted) {
                                double realOffset = matchXVirtualRight->offset + width / 2;
                                if (!bestRealOffsetX || std::abs(realOffset) < std::abs(*bestRealOffsetX)) {
                                    matchX = AlignmentSearchResult{realOffset, matchXVirtualRight->guides};
                                    selfAnchorX = candidateX + width;  // the right edge (raw, pre-snap)
                                }
                            }
                        }
                    }
                }


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.
                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;

                // \"Blue grid\" (see computeBlueGridX/Y()): if one axis is boosted, look on the OTHER
                // (sliding) axis for other same-size small lines/arrows already crossing the same big
                // line. If found, this entirely replaces whatever the ordinary/equidistant search
                // below would otherwise do for that axis - setting matchXIsBoosted/matchYIsBoosted to
                // true here makes the existing equidistant-blending code skip it automatically.
                const Element* xBoostedTarget = matchXIsBoosted ? matchX->guides.front().boostedTarget : nullptr;
                const Element* yBoostedTarget = matchYIsBoosted ? matchY->guides.front().boostedTarget : nullptr;

                // \"Half/double on release\" (see EditSelection::mouseUp(), patch 8.6.4): tracks which
                // third of the boosted snap zone the moving line currently sits in (-1 = the \"negative\"
                // side, e.g. above a horizontal big line; 0 = middle; +1 = the \"positive\" side, e.g.
                // below it), purely for live visual feedback (truncating the blue grid markers below)
                // and for EditSelection::mouseUp() to read once the drag ends.
                this->activeBoostedTarget = nullptr;
                this->activeBoostedIsXAxis = false;
                this->activeBoostedZone = 0;
                // \"Line-end anchors\" (patch 8.6.5): flags/coordinates for the self-shaped blue overlay
                // guide, set below when self snaps to one of the big line's own two endpoints.
                bool endpointGuideActiveX = false;
                double endpointGuideCoordX = 0;
                double endpointGuideFromX = 0;
                double endpointGuideToX = 0;
                bool endpointGuideActiveY = false;
                double endpointGuideCoordY = 0;
                double endpointGuideFromY = 0;
                double endpointGuideToY = 0;
                if (yBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = yBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already
                        // boost-snapped to ANY big line when this drag started (this->startingWasBoosted
                        // == false) may not settle into Top/Below on its own just because the cursor
                        // dragged it into that zone - it must default to Middle, UNLESS other same-size,
                        // same-orientation lines are already established on THIS big line, in which case
                        // it follows their mode instead. A line that WAS already attached somewhere at
                        // mouseDown keeps full free transition between zones, as before.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = height;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == yBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isVerticalShaft =
                                        shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                                if (!isVerticalShaft ||
                                    std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                    shaft.x + shaft.width)) {
                                    continue;
                                }
                                double shaftCenterY = shaft.y + shaft.height / 2;
                                if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                double farEdge = shaft.y + shaft.height;
                                double nearEdge = shaft.y;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle, regardless of where the cursor is or
                        // whether this line was already part of an established family.
                        this->activeBoostedZone = 0;
                    }

                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever
                    // reference point matches the CURRENT zone (bottom edge for -1, center for 0, top
                    // edge for +1), not always its true center - so self visually moves together with
                    // the \"family\" grid preview as the zone changes mid-drag. Guides are left as-is
                    // (still correctly flagged boosted), only the offset is replaced.
                    double refPointY;
                    if (this->activeBoostedZone < 0) {
                        refPointY = candidateY + height;
                    } else if (this->activeBoostedZone > 0) {
                        refPointY = candidateY;
                    } else {
                        refPointY = candidateY + height / 2;
                    }
                    matchY->offset = targetCenter - refPointY;

                    // \"Line-end anchors\" (patch 8.6.5): while this big line has only 1 or 2 small
                    // lines crossing it (self included), its own two endpoints become additional
                    // anchor points for self's OTHER axis (the one along the big line's length) -
                    // letting self snap so it crosses right at one end. Independent of the Y offset
                    // above; only touches matchX.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == yBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isVerticalShaft =
                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                            if (!isVerticalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x,
                                                shaft.x + shaft.width)) {
                                continue;
                            }
                            double shaftCenterY = shaft.y + shaft.height / 2;
                            if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                continue;
                            }
                            existingCount++;
                        }
                        // Endpoint anchoring applies whenever there are at most 2 small lines
                        // (self included) crossing the big line - matching the \"1 or 2 small lines\"
                        // intent of patch 8.6.5 (existingCount counts self too, so this is
                        // existingCount <= 2, not <= 1 as originally miscoded). If \"Graduation
                        // assist\" (patch 10.6A) is disabled, this restriction is lifted entirely:
                        // endpoint anchoring then always applies, regardless of how many lines are
                        // already boosted on the big line, since there is no family/grid concept to
                        // protect from conflicting with in that case.
                        //
                        // Patch 11.3: with 3+ lines AND Graduation assist enabled, the \"Lock X to
                        // start\" branch below only makes sense if those lines actually form a valid,
                        // regular grid (see computeBlueGridX()'s own return value) - if they don't
                        // (e.g. irregularly spaced), there is no family to protect either, so this
                        // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            // Patch 11.5.2: fixed a parameter mix-up from patch 11.3 - self is
                            // vertical here (crossing a horizontal big line), so its relevant length
                            // for family/grid matching is `height`, not `width` (matching the
                            // existing marker-computing call further below, which already used
                            // `height` correctly). The mismatch could make this check see an invalid
                            // grid even when a perfectly valid one (shown via markers) existed,
                            // wrongly triggering patch 11.5's red guide.
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                bestOffset = leftEnd - selfCenterX;
                                found = true;
                            }
                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                bestOffset = rightEnd - selfCenterX;
                                found = true;
                            }
                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            } else if (gridWasInvalid && matchY) {
                                // Patch 11.5: self is free to slide along the big line right now (not
                                // near an endpoint, and the existing family isn't a valid regular grid)
                                // - the crossing guide on the big line (matchY) is still shown, since
                                // self IS still boosted to it, but colored red instead of blue to signal
                                // that Graduation assist can't actually lock it in place here.
                                for (auto& g: matchY->guides) {
                                    g.isBoostedButFree = true;
                                }
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, forming a valid regular grid (see the condition
                            // above), the line-end anchors don't apply - during a Top/Middle/Below
                            // mode transition, self's X position (along the big line's length) should
                            // stay exactly where it was when the drag started, rather than drifting
                            // with the raw mouse X. Only reached when \"Graduation assist\" is enabled
                            // and a valid grid was found - it only makes sense together with the
                            // graduation/family grid preview (patch 10.6A).
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
                    }
                } else if (xBoostedTarget != nullptr) {
                    xoj::util::Rectangle<double> targetShaft = xBoostedTarget->getSnappedBounds();
                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case -
                        // see the Y-branch above for the full explanation.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = width;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == xBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isHorizontalShaft =
                                        shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                                if (!isHorizontalShaft ||
                                    std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                    shaft.y + shaft.height)) {
                                    continue;
                                }
                                double shaftCenterX = shaft.x + shaft.width / 2;
                                if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                double farEdge = shaft.x + shaft.width;
                                double nearEdge = shaft.x;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle.
                        this->activeBoostedZone = 0;
                    }

                    double refPointX;
                    if (this->activeBoostedZone < 0) {
                        refPointX = candidateX + width;
                    } else if (this->activeBoostedZone > 0) {
                        refPointX = candidateX;
                    } else {
                        refPointX = candidateX + width / 2;
                    }
                    matchX->offset = targetCenter - refPointX;

                    // \"Line-end anchors\" (patch 8.6.5), mirrored for the X-boosted case (self
                    // horizontal, big line vertical): its own two endpoints (top/bottom) become
                    // additional anchor points for self's Y position.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == xBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isHorizontalShaft =
                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                            if (!isHorizontalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y,
                                                shaft.y + shaft.height)) {
                                continue;
                            }
                            double shaftCenterX = shaft.x + shaft.width / 2;
                            if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                continue;
                            }
                            existingCount++;
                        }
                        // See the Y-boosted branch above for the full explanation of this condition.
                        // Patch 11.3: see the Y-boosted branch above for the full explanation.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            // Patch 11.5.2: see the Y-boosted branch above for the full explanation -
                            // self is horizontal here, so its relevant length is `width`, not `height`.
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                bestOffset = topEnd - selfCenterY;
                                found = true;
                            }
                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                bestOffset = bottomEnd - selfCenterY;
                                found = true;
                            }
                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            } else if (gridWasInvalid && matchX) {
                                // Patch 11.5: see the Y-boosted branch above for the full explanation.
                                for (auto& g: matchX->guides) {
                                    g.isBoostedButFree = true;
                                }
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only reached when \"Graduation assist\" is enabled and a valid grid was
                            // found (see the condition above).
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
                    }
                }
                this->activeBlueGridMarkers.clear();
                if (matchYIsBoosted && yBoostedTarget != nullptr) {
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
                            if (grid->forceOffset) {
                                matchX = AlignmentSearchResult{*grid->forceOffset - (candidateX + width / 2), {}};
                            }
                            // Patch 11.5: if the grid doesn't force an offset (e.g. only 2 lines so
                            // far - \"indicative only\" markers, per computeBlueGridX()'s own doc
                            // comment), matchX is deliberately left untouched here, rather than being
                            // nulled out - so a genuine ordinary-tier (pink/green) match already found
                            // on self's own axis is not silently discarded just because self happens
                            // to also be boosted on the other axis.
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
                            if (grid->forceOffset) {
                                matchY = AlignmentSearchResult{*grid->forceOffset - (candidateY + height / 2), {}};
                            }
                            // Patch 11.5: see the X-axis case above for the full explanation.
                        }
                    }
                }

                if (!matchXIsBoosted && settings->isEquidistantSnappingEnabled()) {
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

                // Snap to the page's own horizontal center (accounting for a Lined background's
                // margin, if any). Competes with the ordinary X match on closeness, like equidistant
                // snapping does, but never overrides a boosted (blue) match.
                bool matchXIsBoostedForPageCenter = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                if (!matchXIsBoostedForPageCenter && this->sourcePage && settings->isPageCenteringSnappingEnabled()) {
                    PageCenterInfo pageCenter = computePageCenterX(this->sourcePage.get());
                    double pageCenterOffset = pageCenter.centerX - (candidateX + width / 2.0);
                    if (std::abs(pageCenterOffset) < tolerance &&
                        (!matchX || std::abs(pageCenterOffset) < std::abs(matchX->offset))) {
                        AlignmentMatch pageMatch{pageCenterOffset,
                                                  pageCenter.centerX,
                                                  visibleRect.y,
                                                  visibleRect.y + visibleRect.height,
                                                  false,
                                                  false};
                        pageMatch.isPageCenter = true;
                        if (pageCenter.marginX) {
                            pageMatch.hasPageMargin = true;
                            pageMatch.pageMarginX = *pageCenter.marginX;
                        }
                        matchX = AlignmentSearchResult{pageCenterOffset, {pageMatch}};
                    }
                }

                // \"Table center\" (see findTableCenterX/Y()): only relevant when the moving selection is
                // a single Text, TexImage, or Image. Takes strict priority over whatever pink/green
                // match (ordinary tier, equidistant) already exists on its own axis - if found, it
                // fully replaces it, rather than competing on closeness like equidistant does. Never
                // overrides a boosted (blue) match; does not affect the other axis at all.
                auto selfElements = this->getElementsView();
                bool selfIsTableTarget = selfElements.size() == 1 &&
                                          (dynamic_cast<const Text*>(*selfElements.begin()) != nullptr ||
                                           dynamic_cast<const TexImage*>(*selfElements.begin()) != nullptr ||
                                           dynamic_cast<const Image*>(*selfElements.begin()) != nullptr);
                if (selfIsTableTarget && settings->isTableContentCenteringAssistEnabled()) {
                    bool matchXIsBoostedForTable = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;
                    bool matchYIsBoostedForTable = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                    if (!matchXIsBoostedForTable) {
                        if (auto tableX = findTableCenterX(candidateX, width, candidateY, candidateY + height,
                                                            tolerance, this->sourceLayer, excluded)) {
                            matchX = AlignmentSearchResult{tableX->offset, {*tableX}};
                        }
                    }
                    if (!matchYIsBoostedForTable) {
                        if (auto tableY = findTableCenterY(candidateY, height, candidateX, candidateX + width,
                                                            tolerance, this->sourceLayer, excluded)) {
                            matchY = AlignmentSearchResult{tableY->offset, {*tableY}};
                        }
                    }
                }

                if (matchX) {
                    dx += matchX->offset;
                    objectSnappedX = true;
                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX, g.isBoostedButFree});
                    }
                } else {
                    this->activeGuidesX.clear();
                }
                if (matchY) {
                    dy += matchY->offset;
                    objectSnappedY = true;
                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX, g.isBoostedButFree});
                    }
                } else {
                    this->activeGuidesY.clear();
                }

                // \"Line-end anchors\" (patch 8.6.5): push the self-shaped blue overlay guide(s), if
                // any were found above. Uses designated initializers so this compiles regardless of
                // how many extra trailing fields AlignmentGuide has picked up from other patches.
                if (endpointGuideActiveX) {
                    this->activeGuidesX.push_back(AlignmentGuide{.coordinate = endpointGuideCoordX,
                                                                  .from = endpointGuideFromX,
                                                                  .to = endpointGuideToX,
                                                                  .isCenter = false,
                                                                  .isBoosted = true});
                }
                if (endpointGuideActiveY) {
                    this->activeGuidesY.push_back(AlignmentGuide{.coordinate = endpointGuideCoordY,
                                                                  .from = endpointGuideFromY,
                                                                  .to = endpointGuideToY,
                                                                  .isCenter = false,
                                                                  .isBoosted = true});
                }
            }
        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
            this->activeBlueGridMarkers.clear();
            this->activeBoostedTarget = nullptr;
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position
        double cx = this->snappedBounds.x;
        double cy = this->snappedBounds.y;
        if ((this->relMousePosRotX > this->snappedBounds.width / 2) ==
            (this->snappedBounds.width > 0)) {  // closer to the right side
            cx += this->snappedBounds.width;"""
ES_CPP_OLD7 = """        cx /= zoom;
        cy /= zoom;

        // compute position where unsnapped corner would move
        Point p = Point(cx + dx, cy + dy);

        // snap this corner
        p = snappingHandler.snapToGrid(p, alt);

        // move
        if (!this->edgePanInhibitNext) {
            moveSelection(p.x - cx, p.y - cy);
            this->setEdgePan(true);
        } else {"""
ES_CPP_NEW7 = """        cx /= zoom;
        cy /= zoom;

        // compute position where unsnapped corner would move
        Point p = Point(cx + dx, cy + dy);

        // snap this corner to the grid - but not on an axis where an object-alignment guide already
        // snapped it precisely above, or the grid could nudge it slightly off that exact alignment.
        if (objectSnappedX && objectSnappedY) {
            // both axes already precisely aligned to another object; leave p untouched
        } else if (objectSnappedX) {
            p.y = snappingHandler.snapVertically(p.y, alt);
        } else if (objectSnappedY) {
            p.x = snappingHandler.snapHorizontally(p.x, alt);
        } else {
            p = snappingHandler.snapToGrid(p, alt);
        }

        // move
        if (!this->edgePanInhibitNext) {
            moveSelection(p.x - cx, p.y - cy);
            this->setEdgePan(true);
        } else {"""
ES_CPP_OLD8 = """}

/**
 * Paints the selection to cr, with the given zoom factor. The coordinates of cr
 * should be relative to the provided view by getView() (use translateEvent())
 */
void EditSelection::paint(cairo_t* cr, double zoom) {
    double x = this->x;
    double y = this->y;


    if (std::abs(this->rotation) > std::numeric_limits<double>::epsilon()) {"""
ES_CPP_NEW8 = """}

/**
 * Paints the selection to cr, with the given zoom factor. The coordinates of cr
 * should be relative to the provided view by getView() (use translateEvent())
 */
/**
 * Draws a double-headed arrow from (x1, y1) to (x2, y2) (already in screen/pixel coordinates, i.e.
 * pre-multiplied by zoom) on `cr`, using whatever source color/line width is currently set. Used to
 * illustrate an equidistant (\"equal spacing\") match - see findEquidistantX/Y() and paint().
 */
static void drawDoubleArrow(cairo_t* cr, double x1, double y1, double x2, double y2) {
    constexpr double ARROW_HEAD_LENGTH_PX = 7.0;
    constexpr double ARROW_HEAD_ANGLE = M_PI / 7.0;  // ~25 degrees between each wing and the shaft

    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x2, y2);
    cairo_stroke(cr);

    double angle = std::atan2(y2 - y1, x2 - x1);

    // Head at (x1, y1), wings pointing back along the shaft (towards (x2, y2)'s opposite direction).
    double back1 = angle + M_PI;
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 - ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x1, y1);
    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 + ARROW_HEAD_ANGLE),
                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 + ARROW_HEAD_ANGLE));

    // Head at (x2, y2), wings pointing back along the shaft towards (x1, y1).
    double back2 = angle;
    cairo_move_to(cr, x2, y2);
    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 - ARROW_HEAD_ANGLE),
                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 - ARROW_HEAD_ANGLE));
    cairo_move_to(cr, x2, y2);
    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 + ARROW_HEAD_ANGLE),
                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 + ARROW_HEAD_ANGLE));
    cairo_stroke(cr);
}

void EditSelection::paint(cairo_t* cr, double zoom) {
    double x = this->x;
    double y = this->y;


    if (std::abs(this->rotation) > std::numeric_limits<double>::epsilon()) {"""
ES_CPP_OLD9 = """        cairo_translate(cr, -rx, -ry);
    }
    this->contents->paint(cr, x, y, this->rotation, this->width, this->height, zoom);

    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);

    GdkRGBA selectionColor = view->getSelectionColor();

    // set the line always the same size on display
    cairo_set_line_width(cr, 1);

    const std::vector<double> dashes = {10.0, 10.0};"""
ES_CPP_NEW9 = """        cairo_translate(cr, -rx, -ry);
    }
    this->contents->paint(cr, x, y, this->rotation, this->width, this->height, zoom);

    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);

    // Smart alignment guides: a bounded line connecting the moving selection to whichever element(s)
    // it is currently aligned with. Pink for an edge alignment, green if either matched anchor was a
    // center point, blue for the special \"small stroke crossing a big perpendicular stroke\" case.
    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {
        cairo_save(cr);
        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);

        for (auto& guide: this->activeGuidesX) {
            double gx = guide.coordinate * zoom;
            if (guide.isBoosted) {
                if (guide.isBoostedButFree) {
                    cairo_set_source_rgb(cr, 0.9, 0.1, 0.1);  // red: boosted crossing shown, but
                                                               // Graduation assist can't lock here
                                                               // (patch 11.5, see patch 11.3)
                } else {
                    cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                }
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            } else if (guide.isPageCenter) {
                cairo_set_source_rgb(cr, 0.75, 0.75, 0.75);  // light gray
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
                if (guide.hasPageMargin) {
                    double mx = guide.pageMarginX * zoom;
                    cairo_move_to(cr, mx, guide.from * zoom);
                    cairo_line_to(cr, mx, guide.to * zoom);
                    cairo_stroke(cr);
                }
            } else if (!guide.equidistantGaps.empty()) {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
                double py = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);
                }
            } else {
                double mid = (guide.from + guide.to) / 2 * zoom;
                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;
                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;
                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,
                                     firstHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, mid);
                cairo_stroke(cr);
                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,
                                     secondHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, gx, mid);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            }
        }
        for (auto& guide: this->activeGuidesY) {
            double gy = guide.coordinate * zoom;
            if (guide.isBoosted) {
                if (guide.isBoostedButFree) {
                    cairo_set_source_rgb(cr, 0.9, 0.1, 0.1);  // red: see the activeGuidesX loop above
                } else {
                    cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                }
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);
            } else if (!guide.equidistantGaps.empty()) {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
                double px = guide.equidistantPlacement * zoom;
                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {
                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);
                }
            } else {
                double mid = (guide.from + guide.to) / 2 * zoom;
                bool firstHalfIsCenter = guide.selfOnFromSide ? guide.selfIsCenter : guide.otherIsCenter;
                bool secondHalfIsCenter = guide.selfOnFromSide ? guide.otherIsCenter : guide.selfIsCenter;
                cairo_set_source_rgb(cr, firstHalfIsCenter ? 0.0 : 1.0, firstHalfIsCenter ? 0.8 : 0.0,
                                     firstHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, mid, gy);
                cairo_stroke(cr);
                cairo_set_source_rgb(cr, secondHalfIsCenter ? 0.0 : 1.0, secondHalfIsCenter ? 0.8 : 0.0,
                                     secondHalfIsCenter ? 0.2 : 0.8);
                cairo_move_to(cr, mid, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);
            }
        }
        cairo_restore(cr);
    }

    // \"Blue grid\" markers (see computeBlueGridX/Y() in EditSelection.cpp): short segments, parallel
    // to the moving object's own small line/arrow, at each candidate position along the big line it
    // is boost-snapped to.
    if (!this->activeBlueGridMarkers.empty()) {
        cairo_save(cr);
        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue, matching the boosted tier
        // Shift the whole grid preview along its own axis based on how the CURRENT zone differs from
        // the STARTING zone (the one self was already in when this drag began - see
        // EditSelection::mouseDown()/computeStartingZone()): delta = (current - starting) * halfLength,
        // per line. This matches, for example, Middle -> Top shifting everything by -halfLength (half
        // the line's own length, toward the \"negative\" direction), and Below -> Top by a full length.
        for (auto& marker: this->activeBlueGridMarkers) {
            double shift = (this->activeBoostedZone - this->startingBoostedZone) * marker.halfLength * zoom;
            double mx = marker.x * zoom;
            double my = marker.y * zoom;
            double half = marker.halfLength * zoom;
            if (marker.isVertical) {
                double shiftedY = my + shift;
                cairo_move_to(cr, mx, shiftedY - half);
                cairo_line_to(cr, mx, shiftedY + half);
            } else {
                double shiftedX = mx + shift;
                cairo_move_to(cr, shiftedX - half, my);
                cairo_line_to(cr, shiftedX + half, my);
            }
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }

    // \"Table center\" guides (see findTableCenterX/Y()) always render on top in yellow, regardless of
    // how the main guide loop above colored them (they also satisfy isCenter, so that loop draws them
    // too - this separate pass paints over in yellow, giving them priority on their axis without
    // needing to touch that loop's own, more intricate color-selection logic).
    if (!this->activeGuidesX.empty() || !this->activeGuidesY.empty()) {
        cairo_save(cr);
        cairo_set_line_width(cr, 1.5);
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_set_source_rgb(cr, 0.9, 0.75, 0.0);  // gold/yellow
        for (auto& guide: this->activeGuidesX) {
            if (!guide.isTableCenter) {
                continue;
            }
            double gx = guide.coordinate * zoom;
            cairo_move_to(cr, gx, guide.from * zoom);
            cairo_line_to(cr, gx, guide.to * zoom);
            cairo_stroke(cr);
        }
        for (auto& guide: this->activeGuidesY) {
            if (!guide.isTableCenter) {
                continue;
            }
            double gy = guide.coordinate * zoom;
            cairo_move_to(cr, guide.from * zoom, gy);
            cairo_line_to(cr, guide.to * zoom, gy);
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }

    GdkRGBA selectionColor = view->getSelectionColor();

    // set the line always the same size on display
    cairo_set_line_width(cr, 1);

    const std::vector<double> dashes = {10.0, 10.0};"""
ES_H_OLD0 = """
#include <array>
#include <memory>  // for unique_ptr
#include <string>
#include <utility>  // for pair
#include <vector>   // for vector"""
ES_H_NEW0 = """
#include <array>
#include <memory>  // for unique_ptr
#include <optional>
#include <string>
#include <utility>  // for pair
#include <vector>   // for vector"""
ES_H_OLD1 = """class DeleteUndoAction;
class LineStyle;
class ObjectInputStream;
class ObjectOutputStream;
class XojFont;
class Document;"""
ES_H_NEW1 = """class DeleteUndoAction;
class LineStyle;
class ObjectInputStream;
class Settings;
class ObjectOutputStream;
class XojFont;
class Document;"""
ES_H_OLD2 = """    Layer* sourceLayer{};

    /**
     * The contents of the selection
     */
    std::unique_ptr<EditSelectionContents> contents;"""
ES_H_NEW2 = """    Layer* sourceLayer{};

    /**
     * Used to check whether object-alignment snapping (\"smart guides\") is enabled.
     */
    const Settings* settings{};

    /**
     * A single marker of the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp):
     * a short segment, parallel to the moving selection's own small line/arrow, at one candidate
     * position along the big line it is boost-snapped to. `x`/`y` is the marker's center;
     * `halfLength` is half of the moving object's own length; `isVertical` says whether it should be
     * drawn as a short vertical segment (moving object is vertical) or horizontal (moving object is
     * horizontal).
     */
    struct BlueGridMarker {
        double x;
        double y;
        double halfLength;
        bool isVertical;
    };

    /**
     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line
     * visually connects the two. `equidistantGaps`/`equidistantPlacement`, if non-empty, mean this
     * guide is an equidistant (\"equal spacing\") match instead: each pair is one gap in the chain to
     * draw as a double-headed arrow (in primary-axis coordinates), all at `equidistantPlacement` on
     * the perpendicular axis - see paint().
     */
    struct AlignmentGuide {
        double coordinate;
        double from;
        double to;
        bool isCenter;
        bool isBoosted;
        bool isTableCenter = false;
        bool selfIsCenter = false;
        bool otherIsCenter = false;
        bool selfOnFromSide = true;
        std::vector<std::pair<double, double>> equidistantGaps;
        double equidistantPlacement = 0;
        bool isPageCenter = false;
        bool hasPageMargin = false;
        double pageMarginX = 0;
        /// Patch 11.5: true if this guide indicates a boosted crossing point that Graduation assist
        /// would normally lock onto, but currently can't - because the small lines already on this
        /// big line (3+, self included) don't form a valid, regular grid (see computeBlueGridX/Y() and
        /// patch 11.3) - so self can actually be dragged freely along the big line right now, even
        /// though this guide is shown. Rendered in red instead of the usual blue, to signal this.
        bool isBoostedButFree = false;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a
    /// single line, but can hold several simultaneously when multiple anchor points agree on the
    /// same alignment (e.g. two identically-sized objects whose top, center and bottom all line up
    /// at once) - see findAlignmentX/Y() in EditSelection.cpp.
    std::vector<AlignmentGuide> activeGuidesX;
    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.
    std::vector<AlignmentGuide> activeGuidesY;

    /// Active markers for the \"blue grid\" feature (see computeBlueGridX/Y() in EditSelection.cpp),
    /// set during mouseMove() while dragging, if any.
    std::vector<BlueGridMarker> activeBlueGridMarkers;

    /// The \"big line\" element the moving object is currently boost-snapped to, or nullptr if not
    /// currently boosted - set during mouseMove(), read by mouseUp() for the \"half/double on
    /// release\" feature (see patch 8.6.4) and by paint() to truncate the blue grid markers.
    const Element* activeBoostedTarget = nullptr;
    /// True if activeBoostedTarget's crossing is on the X axis (self horizontal, big line vertical),
    /// false if on Y. Only meaningful when activeBoostedTarget is not nullptr.
    bool activeBoostedIsXAxis = false;
    /// Which third of the boosted snap zone the moving line currently sits in: -1 for the \"negative\"
    /// side (e.g. above a horizontal big line), 0 for the middle third, +1 for the \"positive\" side
    /// (e.g. below it). Only meaningful when activeBoostedTarget is not nullptr.
    int activeBoostedZone = 0;
    /// The zone (see activeBoostedZone) self was already in when the current drag started - computed
    /// once in mouseDown() via computeStartingZone(). Used to shift the whole \"blue grid\" preview by
    /// the right amount as the zone changes mid-drag (patch 8.6.4.6).
    int startingBoostedZone = 0;
    /// True if self was already boost-snapped to SOME big line at the moment this drag started (see
    /// startingBoostedZone/computeStartingZone(), patch 8.6.4.6). When false (self is a \"fresh\" line,
    /// not previously attached anywhere), Top/Below zone transitions are disabled for this drag - see
    /// the \"fresh line\" override in mouseMove() (patch 8.6.6): a fresh line can only settle into
    /// Middle, unless other same-size/orientation lines are already established on the big line it
    /// is approaching, in which case it follows their mode instead.
    bool startingWasBoosted = false;

    /**
     * The contents of the selection
     */
    std::unique_ptr<EditSelectionContents> contents;"""
ELLIPSE_OLD0 = """        width = (this->modControl) ? std::hypot(width, height) :
                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);
        height = std::copysign(width, height);
    }

    double radiusX = 0;"""
ELLIPSE_NEW0 = """        width = (this->modControl) ? std::hypot(width, height) :
                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);
        height = std::copysign(width, height);
    } else {
        // Diagonal snap assist: if width and height are already close, snap them to be exactly
        // equal (a perfect circle's bounding box becomes a square), and show two green guide lines
        // along the edges nearest the cursor. The cursor can keep moving freely along the diagonal
        // while snapped, since both dimensions grow/shrink together; if they drift too far apart
        // again, the snap (and the guide) releases.
        this->diagonalSnapGuide.reset();
        // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than inside
        // Settings::isCircleAssistEnabled() itself - see that getter's own doc comment for why.
        bool circleAssistEnabled = control == nullptr || control->getSettings() == nullptr ||
                                    (control->getSettings()->isSnapToObjects() &&
                                     control->getSettings()->isCircleAssistEnabled());
        double diagonalSnapTolerancePx =
                (control != nullptr && control->getSettings() != nullptr)
                        ? control->getSettings()->getDiagonalSnapTolerancePx()
                        : 6.0;  // matches Settings::diagonalSnapTolerancePx's own default, just in case
        double tolerance = diagonalSnapTolerancePx / this->lastZoom;
        if (circleAssistEnabled && std::abs(std::abs(width) - std::abs(height)) < tolerance) {
            double snappedSize = std::max(std::abs(width), std::abs(height));
            width = std::copysign(snappedSize, width);
            height = std::copysign(snappedSize, height);
            this->diagonalSnapGuide =
                    DiagonalSnapGuide{this->startPoint, Point(this->startPoint.x + width, this->startPoint.y + height)};
        }
    }

    double radiusX = 0;"""
RULER_OLD0 = """auto RulerHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    Range rg(this->startPoint.x, this->startPoint.y);
    rg.addPoint(secondPoint.x, secondPoint.y);
    return {{this->startPoint, secondPoint}, rg};"""
RULER_NEW0 = """auto RulerHandler::createShape(bool isAltDown, bool isShiftDown, bool isControlDown)
        -> std::pair<std::vector<Point>, Range> {
    Point secondPoint = snappingHandler.snap(this->currPoint, this->startPoint, isAltDown);
    secondPoint = applyLineCrossingSnap(secondPoint);
    Range rg(this->startPoint.x, this->startPoint.y);
    rg.addPoint(secondPoint.x, secondPoint.y);
    return {{this->startPoint, secondPoint}, rg};"""
SPLINE_CPP_OLD0 = """
#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
#include \"gui/XournalppCursor.h\"                 // for XournalppCursor
#include \"gui/inputdevices/InputEvents.h\"        // for KeyEvent
#include \"gui/inputdevices/PositionInputData.h\"  // for PositionInputData
#include \"model/Document.h\"                      // for Document
#include \"model/Layer.h\"                         // for Layer
#include \"model/SplineSegment.h\"                 // for SplineSegment
#include \"model/Stroke.h\"                        // for Stroke"""
SPLINE_CPP_NEW0 = """
#include \"control/Control.h\"                       // for Control
#include \"control/layer/LayerController.h\"         // for LayerController
#include \"control/settings/Settings.h\"             // for Settings
#include \"control/tools/InputHandler.h\"            // for InputHandler
#include \"control/tools/SnapToGridInputHandler.h\"  // for SnapToGridInputHan...
#include \"control/zoom/ZoomControl.h\"
#include \"gui/MainWindow.h\"                      // for MainWindow
#include \"gui/XournalView.h\"                     // for XournalView
#include \"gui/XournalppCursor.h\"                 // for XournalppCursor
#include \"gui/inputdevices/InputEvents.h\"        // for KeyEvent
#include \"gui/inputdevices/PositionInputData.h\"  // for PositionInputData
#include \"model/Document.h\"                      // for Document
#include \"model/Element.h\"                       // for Element
#include \"model/Layer.h\"                         // for Layer
#include \"model/SplineSegment.h\"                 // for SplineSegment
#include \"model/Stroke.h\"                        // for Stroke"""
SPLINE_CPP_OLD1 = """#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"view/overlays/SplineToolView.h\"

SplineHandler::SplineHandler(Control* control, const PageRef& page):"""
SPLINE_CPP_NEW1 = """#include \"undo/UndoRedoHandler.h\"                // for UndoRedoHandler
#include \"util/Assert.h\"                         // for xoj_assert
#include \"util/DispatchPool.h\"
#include \"util/Rectangle.h\"                      // for Rectangle
#include \"view/overlays/SplineToolView.h\"

SplineHandler::SplineHandler(Control* control, const PageRef& page):"""
SPLINE_CPP_OLD2 = """}

constexpr double SHIFT_AMOUNT = 1.0;
constexpr double ROTATE_AMOUNT = 5.0;
constexpr double SCALE_AMOUNT = 1.05;
constexpr double MAX_TANGENT_LENGTH = 2000.0;"""
SPLINE_CPP_NEW2 = """}

constexpr double SHIFT_AMOUNT = 1.0;
/// Patch 10.10.2.4: this used to be a compile-time constant here (ALIGNMENT_SNAP_TOLERANCE_PX = 6.0)
/// - it is now user-configurable via Preferences instead, see
/// Settings::getSplineAlignmentSnapTolerancePx() (a separate setting from EditSelection.cpp's own
/// alignment tolerance, despite the original constant sharing the same name).
constexpr double ROTATE_AMOUNT = 5.0;
constexpr double SCALE_AMOUNT = 1.05;
constexpr double MAX_TANGENT_LENGTH = 2000.0;"""
SPLINE_CPP_OLD3 = """    return false;
}

auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;"""
SPLINE_CPP_NEW3 = """    return false;
}

/**
 * \"Ordinary\" (green/pink) alignment guide for the spline's moving point (patch 8.9): finds the
 * closest edge or center, on a single axis, among every element on `layer` that is currently
 * visible, within `tolerance` of `value`. Mirrors the \"ordinary tier\" of EditSelection's own
 * alignment system (see EditSelection.cpp), but simplified for a single point rather than a moving
 * box - only three candidates per element (near edge, center, far edge), no boosted/equidistant/etc.
 * tiers. `getAxisRange` extracts an element's own [from, from+size] range on the axis being matched;
 * `getPerpFrom`/`getPerpTo` extract its range on the OTHER axis. The matched element's own
 * perpendicular range (otherPerpFrom/otherPerpTo) is returned as-is, NOT yet combined with any point
 * - the caller combines it with the FINAL, fully-resolved point once known (patch 8.9.1), since at
 * the time this search runs the other axis may not have been resolved yet.
 */
struct SplinePointAlignmentMatch {
    double offset;
    double coordinate;
    double otherPerpFrom;
    double otherPerpTo;
    bool isCenter;
};

template <typename AxisRangeFn, typename PerpFromFn, typename PerpToFn>
static auto findSplinePointAlignment(double value, double tolerance, Layer* layer,
                                      const xoj::util::Rectangle<double>& visibleRect, AxisRangeFn getAxisRange,
                                      PerpFromFn getPerpFrom, PerpToFn getPerpTo)
        -> std::optional<SplinePointAlignmentMatch> {
    std::optional<SplinePointAlignmentMatch> best;
    double bestDist = tolerance;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        double eh = el->getElementHeight();
        double ey = el->getY();
        double ew = el->getElementWidth();
        double ex = el->getX();
        if (!(ex <= visibleRect.x + visibleRect.width && visibleRect.x <= ex + ew &&
              ey <= visibleRect.y + visibleRect.height && visibleRect.y <= ey + eh)) {
            continue;
        }
        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        auto [from, size] = getAxisRange(snapped);
        double candidates[3] = {from, from + size / 2, from + size};
        bool candidateIsCenter[3] = {false, true, false};
        for (int i = 0; i < 3; ++i) {
            double dist = std::abs(value - candidates[i]);
            if (dist < bestDist) {
                bestDist = dist;
                best = SplinePointAlignmentMatch{candidates[i] - value, candidates[i], getPerpFrom(snapped),
                                                  getPerpTo(snapped), candidateIsCenter[i]};
            }
        }
    }
    return best;
}

static auto findSplinePointAlignmentX(double x, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            x, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.x, r.width}; },
            [](const xoj::util::Rectangle<double>& r) { return r.y; },
            [](const xoj::util::Rectangle<double>& r) { return r.y + r.height; });
}

static auto findSplinePointAlignmentY(double y, double tolerance, Layer* layer,
                                       const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<SplinePointAlignmentMatch> {
    return findSplinePointAlignment(
            y, tolerance, layer, visibleRect,
            [](const xoj::util::Rectangle<double>& r) { return std::pair{r.y, r.height}; },
            [](const xoj::util::Rectangle<double>& r) { return r.x; },
            [](const xoj::util::Rectangle<double>& r) { return r.x + r.width; });
}

/// Bounding Range of a single alignment guide (patch 8.9.1), so its area can be included in the
/// repaint range whenever it appears, moves, or disappears - fixing the same kind of \"ghosting\" bug
/// already fixed for the blue grid markers in patch 8.4.2.
static auto splineGuideRange(const std::optional<SplineAlignmentGuide>& guide, bool isVertical) -> Range {
    if (!guide) {
        return Range();
    }
    if (isVertical) {
        return Range(guide->coordinate, guide->from, guide->coordinate, guide->to);
    }
    return Range(guide->from, guide->coordinate, guide->to, guide->coordinate);
}


auto SplineHandler::onMotionNotifyEvent(const PositionInputData& pos, double zoom) -> bool {
    if (!stroke) {
        return false;"""
SPLINE_CPP_OLD4 = """
    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;"""
SPLINE_CPP_NEW4 = """
    Range rg = this->computeLastSegmentRepaintRange();
    if (this->isButtonPressed) {
        this->activeGuideX.reset();
        this->activeGuideY.reset();
        if (this->inFirstKnotAttractionZone) {
            // The button was pressed within the attraction zone. Wait for unpress to confirm/deny spline finalization
            return true;"""
SPLINE_CPP_OLD5 = """        bool nowInAttractionZone =
                this->buttonDownPoint.lineLengthTo(this->knots.front()) < this->knotsAttractionRadius;
        if (nowInAttractionZone) {
            if (this->inFirstKnotAttractionZone) {
                // No need to update anything while staying in the attraction zone
                return true;
            }
        } else {
            this->currPoint = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());
        }
        this->inFirstKnotAttractionZone = nowInAttractionZone;
    }"""
SPLINE_CPP_NEW5 = """        bool nowInAttractionZone =
                this->buttonDownPoint.lineLengthTo(this->knots.front()) < this->knotsAttractionRadius;
        if (nowInAttractionZone) {
            this->activeGuideX.reset();
            this->activeGuideY.reset();
            if (this->inFirstKnotAttractionZone) {
                // No need to update anything while staying in the attraction zone
                return true;
            }
        } else {
            Point snapped = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());

            // Ordinary (green/pink) alignment for the moving point (patch 8.9, corrected in 8.9.2):
            // on any axis where a match is found, it REPLACES the angle/distance snap computed just
            // above outright - it does not merely compete with it. Never considers the spline's own
            // knots so far, only other elements already on the page.
            //
            // Guides are only finalized (patch 8.9.1) once BOTH axes are resolved, using the FINAL
            // snapped point rather than the raw cursor position, so a guide always connects the other
            // element's anchor to the spline preview's actual anchor point, not to the mouse cursor.
            // The previous frame's guides (if any) are kept aside so their old area, along with the
            // new one, gets included in the repaint range below - fixing the same kind of \"ghosting\"
            // bug already fixed for the blue grid markers in patch 8.4.2.
            std::optional<SplineAlignmentGuide> oldGuideX = this->activeGuideX;
            std::optional<SplineAlignmentGuide> oldGuideY = this->activeGuideY;
            this->activeGuideX.reset();
            this->activeGuideY.reset();

            std::optional<SplinePointAlignmentMatch> matchX;
            std::optional<SplinePointAlignmentMatch> matchY;
            Layer* layer = this->page->getSelectedLayer();
            // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than
            // inside Settings::isSplineSnappingEnabled() itself - see that getter's own doc comment
            // for why.
            if (layer != nullptr && control->getSettings() != nullptr &&
                control->getSettings()->isSnapToObjects() && control->getSettings()->isSplineSnappingEnabled()) {
                xoj::util::Rectangle<double>* visibleRectPtr =
                        this->control->getWindow()->getXournal()->getVisibleRect(this->control->getCurrentPageNo());
                if (visibleRectPtr != nullptr) {
                    xoj::util::Rectangle<double> visibleRect = *visibleRectPtr;
                    delete visibleRectPtr;
                    double tolerance = control->getSettings()->getSplineAlignmentSnapTolerancePx() / zoom;

                    // Ordinary (green/pink) alignment now REPLACES the angle/distance snap on any
                    // axis where a match is found (patch 8.9.2, correcting the original \"closest
                    // wins\" design of patch 8.9) - it no longer competes with it, it simply takes
                    // priority outright.
                    matchX = findSplinePointAlignmentX(this->buttonDownPoint.x, tolerance, layer, visibleRect);
                    matchY = findSplinePointAlignmentY(this->buttonDownPoint.y, tolerance, layer, visibleRect);
                }
            }
            if (matchX) {
                snapped.x = this->buttonDownPoint.x + matchX->offset;
            }
            if (matchY) {
                snapped.y = this->buttonDownPoint.y + matchY->offset;
            }
            // Now that `snapped` is final, build the guides so they connect to it rather than to the
            // raw cursor position.
            if (matchX) {
                this->activeGuideX = SplineAlignmentGuide{matchX->coordinate,
                                                           std::min(matchX->otherPerpFrom, snapped.y),
                                                           std::max(matchX->otherPerpTo, snapped.y),
                                                           matchX->isCenter};
            }
            if (matchY) {
                this->activeGuideY = SplineAlignmentGuide{matchY->coordinate,
                                                           std::min(matchY->otherPerpFrom, snapped.x),
                                                           std::max(matchY->otherPerpTo, snapped.x),
                                                           matchY->isCenter};
            }

            double guidePadding = std::max(1.5 / zoom, this->stroke->getWidth());
            Range guidesRg = splineGuideRange(oldGuideX, true);
            guidesRg = guidesRg.unite(splineGuideRange(oldGuideY, false));
            guidesRg = guidesRg.unite(splineGuideRange(this->activeGuideX, true));
            guidesRg = guidesRg.unite(splineGuideRange(this->activeGuideY, false));
            if (guidesRg.isValid()) {
                guidesRg.addPadding(guidePadding);
                rg = rg.unite(guidesRg);
            }

            this->currPoint = snapped;
        }
        this->inFirstKnotAttractionZone = nowInAttractionZone;
    }"""
SPLINE_CPP_OLD6 = """    } else {
        xoj_assert(!this->knots.empty());
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        this->currPoint = snappingHandler.snap(this->buttonDownPoint, knots.back(), pos.isAltDown());
        double dist = this->buttonDownPoint.lineLengthTo(this->knots.front());
        if (dist < this->knotsAttractionRadius) {  // now the spline is closed and finalized
            this->addKnotWithTangent(this->knots.front(), this->tangents.front());"""
SPLINE_CPP_NEW6 = """    } else {
        xoj_assert(!this->knots.empty());
        this->buttonDownPoint = Point(pos.x / zoom, pos.y / zoom);
        // Patch 11.8: `this->currPoint` is NOT recomputed here anymore - it already holds the correct
        // value set by the preceding onMotionNotifyEvent() call, which (unlike snappingHandler.snap()
        // alone) also accounts for the full ordinary (green/pink) alignment guide matching. Discarding
        // that and recomputing via snappingHandler.snap() here (as before) meant a snapped moving
        // point would visibly jump back to the raw cursor position right as the segment got committed
        // - the click should always commit whatever was actually being previewed, snapped or not.
        double dist = this->buttonDownPoint.lineLengthTo(this->knots.front());
        if (dist < this->knotsAttractionRadius) {  // now the spline is closed and finalized
            this->addKnotWithTangent(this->knots.front(), this->tangents.front());"""
SPLINE_CPP_OLD7 = """    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots, this->tangents, this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone};
}

auto SplineHandler::linearizeSpline(const SplineHandler::Data& data) -> std::vector<Point> {"""
SPLINE_CPP_NEW7 = """    if (this->knots.empty()) {
        return std::nullopt;
    }
    return Data{this->knots,       this->tangents,   this->currPoint, this->knotsAttractionRadius,
                this->inFirstKnotAttractionZone, this->activeGuideX, this->activeGuideY};
}

auto SplineHandler::linearizeSpline(const SplineHandler::Data& data) -> std::vector<Point> {"""
SPLINE_H_OLD0 = """};  // namespace xoj::view

/**
 * @brief Helper structure for communication with the views
 */
struct SplineHandlerData {"""
SPLINE_H_NEW0 = """};  // namespace xoj::view

/**
 * @brief A single alignment guide line for the spline's moving point (patch 8.9): connects `currPoint`
 * to whichever other element's edge or center it is currently aligned with, on one axis.
 */
struct SplineAlignmentGuide {
    double coordinate;
    double from;
    double to;
    bool isCenter;
};

/**
 * @brief Helper structure for communication with the views
 */
struct SplineHandlerData {"""
SPLINE_H_OLD1 = """    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
};

/**"""
SPLINE_H_NEW1 = """    const Point& currPoint;
    double knotsAttractionRadius;
    bool closedSpline;
    const std::optional<SplineAlignmentGuide>& guideX;
    const std::optional<SplineAlignmentGuide>& guideY;
};

/**"""
SPLINE_H_OLD2 = """    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::SplineToolView>> viewPool;

    static constexpr double KNOTS_ATTRACTION_RADIUS_IN_PIXELS = 10.0;  // for circling the spline's knots"""
SPLINE_H_NEW2 = """    bool inFirstKnotAttractionZone = false;
    SnapToGridInputHandler snappingHandler;

    /// Active ordinary (green/pink) alignment guides for currPoint (patch 8.9), if any - competes,
    /// axis by axis, with the angle/distance snap already provided by snappingHandler; whichever is
    /// closer to the raw cursor position wins for that axis.
    std::optional<SplineAlignmentGuide> activeGuideX;
    std::optional<SplineAlignmentGuide> activeGuideY;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::SplineToolView>> viewPool;

    static constexpr double KNOTS_ATTRACTION_RADIUS_IN_PIXELS = 10.0;  // for circling the spline's knots"""
ACTION_ENUM_OLD0 = """    MOVE_SELECTION_LAYER_DOWN,
    ROTATION_SNAPPING,
    GRID_SNAPPING,
    PREFERENCES,

    // Menu View"""
ACTION_ENUM_NEW0 = """    MOVE_SELECTION_LAYER_DOWN,
    ROTATION_SNAPPING,
    GRID_SNAPPING,
    OBJECT_ALIGNMENT_SNAPPING,
    PREFERENCES,

    // Menu View"""
NAMEMAP_OLD0 = """        \"move-selection-layer-down\",
        \"rotation-snapping\",
        \"grid-snapping\",
        \"preferences\",
        \"paired-pages-mode\",
        \"paired-pages-offset\","""
NAMEMAP_NEW0 = """        \"move-selection-layer-down\",
        \"rotation-snapping\",
        \"grid-snapping\",
        \"object-alignment-snapping\",
        \"preferences\",
        \"paired-pages-mode\",
        \"paired-pages-offset\","""
SD_CPP_OLD0 = """
#include \"control/AudioController.h\"             // for AudioController
#include \"control/Control.h\"                     // for Control
#include \"control/settings/Settings.h\"           // for Settings, SElement
#include \"control/settings/SettingsEnums.h\"      // for STYLUS_CURSOR_ARROW
#include \"control/tools/StrokeStabilizerEnum.h\"  // for AveragingMethod, Pre...
#include \"gui/CreatePreviewImage.h\"              // for createPreviewImage
#include \"gui/MainWindow.h\"                      // for MainWindow
#include \"gui/XournalView.h\"                     // for XournalView"""
SD_CPP_NEW0 = """
#include \"control/AudioController.h\"             // for AudioController
#include \"control/Control.h\"                     // for Control
#include \"control/actions/ActionDatabase.h\"      // for ActionDatabase
#include \"control/settings/Settings.h\"           // for Settings, SElement
#include \"control/settings/SettingsEnums.h\"      // for STYLUS_CURSOR_ARROW
#include \"control/tools/StrokeStabilizerEnum.h\"  // for AveragingMethod, Pre...
#include \"enums/Action.enum.h\"                   // for Action::OBJECT_ALIGNMENT_SNAPPING
#include \"gui/CreatePreviewImage.h\"              // for createPreviewImage
#include \"gui/MainWindow.h\"                      // for MainWindow
#include \"gui/XournalView.h\"                     // for XournalView"""
SD_CPP_OLD1 = """            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

    g_signal_connect_swapped(builder.get(\"cbIgnoreFirstStylusEvents\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
                             }),"""
SD_CPP_NEW1 = """            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

    // Patch 11.10: greys out the whole rest of the snapping tab (both remaining top-level frames -
    // GTK propagates \"sensitive\" to all their descendants automatically) whenever the master toggle
    // is unchecked.
    g_signal_connect_swapped(builder.get(\"cbObjectAlignmentSnapping\"), \"toggled\",
                             G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingFunctionalitiesFrame\");
                                 self->enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingSettingsFrame\");
                             }),
                             this);

    g_signal_connect_swapped(builder.get(\"cbGraduationAssist\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
                             }),
                             this);

    g_signal_connect_swapped(builder.get(\"cbIgnoreFirstStylusEvents\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
                             }),"""
SD_CPP_OLD2 = """    return gtk_range_get_value(range);
}

/**
 * Checkbox was toggled, enable / disable it
 */"""
SD_CPP_NEW2 = """    return gtk_range_get_value(range);
}

void SettingsDialog::loadDoubleEntry(const char* name, double value) {
    GtkEntry* entry = GTK_ENTRY(builder.get(name));
    char buf[64];
    snprintf(buf, sizeof(buf), \"%g\", value);
    gtk_entry_set_text(entry, buf);
}

auto SettingsDialog::getDoubleEntry(const char* name) -> std::optional<double> {
    GtkEntry* entry = GTK_ENTRY(builder.get(name));
    const gchar* text = gtk_entry_get_text(entry);
    if (text == nullptr || *text == '\\0') {
        return std::nullopt;
    }
    char* end = nullptr;
    double value = g_ascii_strtod(text, &end);
    if (end == text || *end != '\\0') {
        return std::nullopt;
    }
    return value;
}

/**
 * Checkbox was toggled, enable / disable it
 */"""
SD_CPP_OLD3 = """    loadCheckbox(\"cbShowScrollbarLeft\", settings->isScrollbarOnLeft());
    loadCheckbox(\"cbAutoloadMostRecent\", settings->isAutoloadMostRecent());
    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
    loadCheckbox(\"cbAutosave\", settings->isAutosaveEnabled());
    loadCheckbox(\"cbAddVerticalSpace\", settings->getAddVerticalSpace());
    loadCheckbox(\"cbAddHorizontalSpace\", settings->getAddHorizontalSpace());"""
SD_CPP_NEW3 = """    loadCheckbox(\"cbShowScrollbarLeft\", settings->isScrollbarOnLeft());
    loadCheckbox(\"cbAutoloadMostRecent\", settings->isAutoloadMostRecent());
    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
    // Patch 11.10: master toggle for the whole object alignment snapping system - mirrors the \"Edit\"
    // menu's own \"Object Alignment Snapping\" toggle (same underlying setting).
    loadCheckbox(\"cbObjectAlignmentSnapping\", settings->isSnapToObjects());
    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());
    loadCheckbox(\"cbCircleAssist\", settings->isCircleAssistEnabled());
    loadCheckbox(\"cbGraduationAssist\", settings->isGraduationAssistEnabled());
    loadCheckbox(\"cbGraduationOrientation\", settings->isGraduationOrientationEnabled());
    loadCheckbox(\"cbTableContentCenteringAssist\", settings->isTableContentCenteringAssistEnabled());
    loadCheckbox(\"cbSplineSnapping\", settings->isSplineSnappingEnabled());
    loadDoubleEntry(\"entryAlignmentSnapTolerance\", settings->getAlignmentSnapTolerancePx());
    loadDoubleEntry(\"entryTextYCenterFraction\", settings->getTextYCenterFraction());
    loadDoubleEntry(\"entryLineCrossSnapTolerance\", settings->getLineCrossSnapTolerancePx());
    loadDoubleEntry(\"entryLineCrossMinLength\", settings->getLineCrossMinLength());
    loadDoubleEntry(\"entrySplineAlignmentSnapTolerance\", settings->getSplineAlignmentSnapTolerancePx());
    loadDoubleEntry(\"entryDiagonalSnapTolerance\", settings->getDiagonalSnapTolerancePx());
    loadDoubleEntry(\"entryPerpendicularCrossBoostFactor\", settings->getPerpendicularCrossBoostFactor());
    loadDoubleEntry(\"entryLineEndAnchorToleranceFactor\", settings->getLineEndAnchorToleranceFactor());
    loadDoubleEntry(\"entrySmallMarkMaxLength\", settings->getSmallMarkMaxLength());
    loadCheckbox(\"cbAutosave\", settings->isAutosaveEnabled());
    loadCheckbox(\"cbAddVerticalSpace\", settings->getAddVerticalSpace());
    loadCheckbox(\"cbAddHorizontalSpace\", settings->getAddHorizontalSpace());"""
SD_CPP_OLD4 = """    disableWithCheckbox(\"cbUnlimitedScrolling\", \"cbAddHorizontalSpace\");

    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
    enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
    enableWithEnabledCheckbox(\"cbAddVerticalSpace\", \"spAddVerticalSpaceAbove\");
    enableWithEnabledCheckbox(\"cbAddHorizontalSpace\", \"spAddHorizontalSpaceRight\");"""
SD_CPP_NEW4 = """    disableWithCheckbox(\"cbUnlimitedScrolling\", \"cbAddHorizontalSpace\");

    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
    // Patch 11.10
    enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingFunctionalitiesFrame\");
    enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingSettingsFrame\");
    enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
    enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
    enableWithEnabledCheckbox(\"cbAddVerticalSpace\", \"spAddVerticalSpaceAbove\");
    enableWithEnabledCheckbox(\"cbAddHorizontalSpace\", \"spAddHorizontalSpaceRight\");"""
SD_CPP_OLD5 = """    settings->setScrollbarOnLeft(getCheckbox(\"cbShowScrollbarLeft\"));
    settings->setAutoloadMostRecent(getCheckbox(\"cbAutoloadMostRecent\"));
    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    settings->setAutosaveEnabled(getCheckbox(\"cbAutosave\"));
    settings->setAddVerticalSpace(getCheckbox(\"cbAddVerticalSpace\"));
    settings->setAddHorizontalSpace(getCheckbox(\"cbAddHorizontalSpace\"));"""
SD_CPP_NEW5 = """    settings->setScrollbarOnLeft(getCheckbox(\"cbShowScrollbarLeft\"));
    settings->setAutoloadMostRecent(getCheckbox(\"cbAutoloadMostRecent\"));
    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
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
    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));
    settings->setCircleAssistEnabled(getCheckbox(\"cbCircleAssist\"));
    settings->setGraduationAssistEnabled(getCheckbox(\"cbGraduationAssist\"));
    settings->setGraduationOrientationEnabled(getCheckbox(\"cbGraduationOrientation\"));
    settings->setTableContentCenteringAssistEnabled(getCheckbox(\"cbTableContentCenteringAssist\"));
    settings->setSplineSnappingEnabled(getCheckbox(\"cbSplineSnapping\"));
    if (auto v = getDoubleEntry(\"entryAlignmentSnapTolerance\")) {
        settings->setAlignmentSnapTolerancePx(*v);
    }
    if (auto v = getDoubleEntry(\"entryTextYCenterFraction\")) {
        settings->setTextYCenterFraction(*v);
    }
    if (auto v = getDoubleEntry(\"entryLineCrossSnapTolerance\")) {
        settings->setLineCrossSnapTolerancePx(*v);
    }
    if (auto v = getDoubleEntry(\"entryLineCrossMinLength\")) {
        settings->setLineCrossMinLength(*v);
    }
    if (auto v = getDoubleEntry(\"entrySplineAlignmentSnapTolerance\")) {
        settings->setSplineAlignmentSnapTolerancePx(*v);
    }
    if (auto v = getDoubleEntry(\"entryDiagonalSnapTolerance\")) {
        settings->setDiagonalSnapTolerancePx(*v);
    }
    if (auto v = getDoubleEntry(\"entryPerpendicularCrossBoostFactor\")) {
        settings->setPerpendicularCrossBoostFactor(*v);
    }
    if (auto v = getDoubleEntry(\"entryLineEndAnchorToleranceFactor\")) {
        settings->setLineEndAnchorToleranceFactor(*v);
    }
    if (auto v = getDoubleEntry(\"entrySmallMarkMaxLength\")) {
        settings->setSmallMarkMaxLength(*v);
    }
    settings->setAutosaveEnabled(getCheckbox(\"cbAutosave\"));
    settings->setAddVerticalSpace(getCheckbox(\"cbAddVerticalSpace\"));
    settings->setAddHorizontalSpace(getCheckbox(\"cbAddHorizontalSpace\"));"""
SD_H_OLD0 = """#pragma once

#include <functional>
#include <string>  // for string
#include <vector>  // for vector
"""
SD_H_NEW0 = """#pragma once

#include <functional>
#include <optional>  // for optional
#include <string>  // for string
#include <vector>  // for vector
"""
SD_H_OLD1 = """    void loadSlider(const char* name, double value);
    double getSlider(const char* name);

    void initMouseButtonEvents(GladeSearchpath* gladeSearchPath);

    void showStabilizerAvMethodOptions(StrokeStabilizer::AveragingMethod method);"""
SD_H_NEW1 = """    void loadSlider(const char* name, double value);
    double getSlider(const char* name);

    /// Patch 10.10.2: generic helpers for a plain GtkEntry holding a floating-point value, following
    /// the same pattern as loadSlider()/getSlider() above. getDoubleEntry() returns std::nullopt if
    /// the text isn't a valid number, so the caller can silently keep the previous value on save.
    void loadDoubleEntry(const char* name, double value);
    std::optional<double> getDoubleEntry(const char* name);

    void initMouseButtonEvents(GladeSearchpath* gladeSearchPath);

    void showStabilizerAvMethodOptions(StrokeStabilizer::AveragingMethod method);"""
STROKE_OLD0 = """
auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }

void Stroke::setArrowKind(ArrowKind kind) { this->arrowKind = kind; }

auto Stroke::getArrowKind() const -> ArrowKind { return this->arrowKind; }
"""
STROKE_NEW0 = """
auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }

void Stroke::setArrowKind(ArrowKind kind) {
    this->arrowKind = kind;
    // setPointVector() may have already cached snappedBounds directly from the full point-list range
    // (see setPointVectorInternal()), before this arrowKind is known - invalidate that cache so the
    // next access recomputes it through calcSize(), which now knows to exclude the arrowhead.
    this->sizeCalculated = false;
}

auto Stroke::getArrowKind() const -> ArrowKind { return this->arrowKind; }
"""
STROKE_OLD1 = """    Element::y = minY;
    Element::width = maxX - minX;
    Element::height = maxY - minY;
    Element::snappedBounds = Rectangle<double>(minSnapX, minSnapY, maxSnapX - minSnapX, maxSnapY - minSnapY);
}

auto Stroke::getErasable() const -> ErasableStroke* { return this->erasable; }"""
STROKE_NEW1 = """    Element::y = minY;
    Element::width = maxX - minX;
    Element::height = maxY - minY;

    // The alignment-snapping system treats an arrow exactly like a plain straight line: its snapped
    // bounds are derived only from the true shaft endpoints (the first and last point - see
    // ArrowHandler::createShape(), which always starts with the shaft's start point and ends with its
    // tip, regardless of single/double-ended or how many decorative arrowhead \"wing\" points lie in
    // between), ignoring the wings entirely. The *visual* bounds above are unaffected and still cover
    // the whole arrowhead, e.g. for selection/click-hit-testing.
    if (this->arrowKind != ArrowKind::NONE && this->points.size() >= 2) {
        const Point& shaftStart = this->points.front();
        const Point& shaftEnd = this->points.back();
        double snapMinX = std::min(shaftStart.x, shaftEnd.x);
        double snapMinY = std::min(shaftStart.y, shaftEnd.y);
        double snapMaxX = std::max(shaftStart.x, shaftEnd.x);
        double snapMaxY = std::max(shaftStart.y, shaftEnd.y);
        Element::snappedBounds = Rectangle<double>(snapMinX, snapMinY, snapMaxX - snapMinX, snapMaxY - snapMinY);
    } else {
        Element::snappedBounds = Rectangle<double>(minSnapX, minSnapY, maxSnapX - minSnapX, maxSnapY - minSnapY);
    }
}

auto Stroke::getErasable() const -> ErasableStroke* { return this->erasable; }"""
SHAPEVIEW_OLD0 = """#include <vector>

#include \"control/tools/BaseShapeHandler.h\"
#include \"util/raii/CairoWrappers.h\"
#include \"view/Repaintable.h\"
#include \"view/StrokeViewHelper.h\""""
SHAPEVIEW_NEW0 = """#include <vector>

#include \"control/tools/BaseShapeHandler.h\"
#include \"model/Point.h\"
#include \"util/raii/CairoWrappers.h\"
#include \"view/Repaintable.h\"
#include \"view/StrokeViewHelper.h\""""
SHAPEVIEW_OLD1 = """    StrokeViewHelper::pathToCairo(effCr, pts);

    this->commitDrawing(cr);
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }"""
SHAPEVIEW_NEW1 = """    StrokeViewHelper::pathToCairo(effCr, pts);

    this->commitDrawing(cr);

    // \"Line crossing\" snap assist (see BaseShapeHandler::applyLineCrossingSnap()): two short pink
    // markers, perpendicular to the line/arrow being drawn, illustrating a matching length found on
    // another line/arrow already on the page. Drawn in document-space coordinates, same as `pts`
    // above - no manual zoom scaling needed here.
    if (auto guide = this->toolHandler->getLineCrossingGuide()) {
        constexpr double MARKER_HALF_SIZE = 7.5;  // 15pt marker, centered on the guide point
        cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink, matching the alignment-snapping system
        cairo_set_line_width(cr, 1.0);
        // Patch 11.1: this assist's guide must always be a solid line, regardless of the current
        // tool's own line style (e.g. dashed/dotted) - prepareContext() above applies that style to
        // `cr`, and it would otherwise still be active here since guides are drawn on the same
        // context, after the main shape.
        cairo_set_dash(cr, nullptr, 0, 0);
        for (const Point& center: {guide->nearCenter, guide->farCenter}) {
            if (guide->perpendicularIsHorizontal) {
                cairo_move_to(cr, center.x - MARKER_HALF_SIZE, center.y);
                cairo_line_to(cr, center.x + MARKER_HALF_SIZE, center.y);
            } else {
                cairo_move_to(cr, center.x, center.y - MARKER_HALF_SIZE);
                cairo_line_to(cr, center.x, center.y + MARKER_HALF_SIZE);
            }
            cairo_stroke(cr);
        }
    }

    // Diagonal (equal width/height) snap assist for ellipses (see EllipseHandler::createShape()):
    // two green lines along the two edges of the (now square) bounding box that meet at the corner
    // nearest the cursor.
    if (auto guide = this->toolHandler->getDiagonalSnapGuide()) {
        cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green, matching the alignment-snapping system
        // Drawn in document-space coordinates (like everything else here), so the line width must be
        // divided by zoom to render at a constant 1.5 screen pixels - matching the thickness of
        // EditSelection's own alignment guides, which are drawn in already-zoomed pixel coordinates.
        cairo_set_line_width(cr, 1.5 / this->toolHandler->getLastZoom());
        // Patch 11.1: same reasoning as the line-crossing guide above - always solid, regardless of
        // the current tool's own line style.
        cairo_set_dash(cr, nullptr, 0, 0);
        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);
        cairo_line_to(cr, guide->corner2.x, guide->corner2.y);
        cairo_line_to(cr, guide->corner1.x, guide->corner2.y);
        cairo_stroke(cr);
    }
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }"""
SPLINEVIEW_OLD0 = """    }
    cairo_stroke(cr);

    this->drawSpline(cr, data.value());
}
"""
SPLINEVIEW_NEW0 = """    }
    cairo_stroke(cr);

    // Ordinary (green/pink) alignment guide(s) for the moving point (patch 8.9) - green for a
    // center match, pink for an edge match, matching EditSelection's own color convention.
    if (data->guideX || data->guideY) {
        cairo_save(cr);
        cairo_set_line_width(cr, lineWidth);
        if (data->guideX) {
            const auto& g = *data->guideX;
            if (g.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            cairo_move_to(cr, g.coordinate, g.from);
            cairo_line_to(cr, g.coordinate, g.to);
            cairo_stroke(cr);
        }
        if (data->guideY) {
            const auto& g = *data->guideY;
            if (g.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            cairo_move_to(cr, g.from, g.coordinate);
            cairo_line_to(cr, g.to, g.coordinate);
            cairo_stroke(cr);
        }
        cairo_restore(cr);
    }

    this->drawSpline(cr, data.value());
}
"""
MENUBAR_OLD0 = """     <attribute name=\"label\" translatable=\"yes\">Grid Snapping</attribute>
     <attribute name=\"action\">win.grid-snapping</attribute>
    </item>
   </section>
   <section>
    <item>"""
MENUBAR_NEW0 = """     <attribute name=\"label\" translatable=\"yes\">Grid Snapping</attribute>
     <attribute name=\"action\">win.grid-snapping</attribute>
    </item>
    <item>
     <attribute name=\"label\" translatable=\"yes\">Object Alignment Snapping</attribute>
     <attribute name=\"action\">win.object-alignment-snapping</attribute>
    </item>
   </section>
   <section>
    <item>"""
GLADE_OLD0 = """              <packing>
                <property name=\"position\">7</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"toolsTabBox\">
                <property name=\"name\">defaultTabBox</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"margin-start\">5</property>
                <property name=\"orientation\">vertical</property>"""
GLADE_NEW0 = """              <packing>
                <property name=\"position\">7</property>
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
                              <object class=\"GtkFrame\" id=\"snapingMasterFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingMasterBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbObjectAlignmentSnapping\">
                                        <property name=\"label\" translatable=\"yes\">Object Alignment Snapping</property>
                                        <property name=\"name\">cbObjectAlignmentSnapping</property>
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
                                  <object class=\"GtkLabel\" id=\"snapingMasterLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Anchoring assistance</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
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
                                      <object class=\"GtkCheckButton\" id=\"cbEquidistantAssist\">
                                        <property name=\"label\" translatable=\"yes\">Equidistant assist</property>
                                        <property name=\"name\">cbEquidistantAssist</property>
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
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblEquidistantAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;Snaps a moved object into the same spacing as two other objects that are already evenly spaced apart.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">1</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbPageCenteringAssist\">
                                        <property name=\"label\" translatable=\"yes\">Page centering assist</property>
                                        <property name=\"name\">cbPageCenteringAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">2</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblPageCenteringAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;Snaps an object to the horizontal center of the page.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">3</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbCoordinateSystemAssist\">
                                        <property name=\"label\" translatable=\"yes\">Coordinate system assist</property>
                                        <property name=\"name\">cbCoordinateSystemAssist</property>
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
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblCoordinateSystemAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;While drawing a straight line or arrow, shows a guide and snaps to match the length of another line it crosses at a right angle.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">5</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbCircleAssist\">
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
                                        <property name=\"position\">6</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblCircleAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;While drawing an ellipse, snaps its bounding box to a square, making a perfect circle.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">7</property>
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
                                        <property name=\"position\">8</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblGraduationAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;Shows evenly spaced tick marks along a line already crossed by several perpendicular lines, and snaps to the nearest one.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">9</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbGraduationOrientation\">
                                        <property name=\"label\" translatable=\"yes\">Graduation orientation</property>
                                        <property name=\"name\">cbGraduationOrientation</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">10</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblGraduationOrientationExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">36</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;Allows switching between top, middle, and below anchoring by dragging the cursor along the line. When disabled, anchoring always uses the middle.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">11</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbTableContentCenteringAssist\">
                                        <property name=\"label\" translatable=\"yes\">Table content centering assist</property>
                                        <property name=\"name\">cbTableContentCenteringAssist</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">12</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblTableContentCenteringAssistExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;Centers text or an image between two parallel lines of equal length, such as a table column or row.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">13</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbSplineSnapping\">
                                        <property name=\"label\" translatable=\"yes\">Snapping when drawing a spline</property>
                                        <property name=\"name\">cbSplineSnapping</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">14</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkLabel\" id=\"lblSplineSnappingExplanation\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"margin-start\">24</property>
                                        <property name=\"margin-bottom\">4</property>
                                        <property name=\"label\" translatable=\"yes\">&lt;i&gt;While drawing a spline, snaps its moving point to the edges and centers of nearby objects.&lt;/i&gt;</property>
                                        <property name=\"use-markup\">True</property>
                                        <property name=\"wrap\">True</property>
                                        <property name=\"max-width-chars\">85</property>
                                        <property name=\"xalign\">0</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">15</property>
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
                                <property name=\"position\">1</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingSettingsFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingSettingsBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>
                                    <property name=\"spacing\">10</property>
                                    <child>
                                      <object class=\"GtkFrame\" id=\"snapingNormalFrame\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"label-xalign\">0.0099999997764825821</property>
                                        <child>
                                          <object class=\"GtkBox\" id=\"snapingNormalBox\">
                                            <property name=\"visible\">True</property>
                                            <property name=\"can-focus\">False</property>
                                            <property name=\"margin-start\">12</property>
                                            <property name=\"margin-end\">12</property>
                                            <property name=\"margin-bottom\">8</property>
                                            <property name=\"orientation\">vertical</property>
                                            <property name=\"spacing\">6</property>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowAlignmentSnapTolerance\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblAlignmentSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Object alignment tolerance</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryAlignmentSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblAlignmentSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 6.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">0</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblAlignmentSnapToleranceExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The base tolerance, in screen pixels, within which an object's edges and center are considered aligned with another object's.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">1</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowTextYCenterFraction\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblTextYCenterFraction\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Text vertical center fraction</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryTextYCenterFraction\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblTextYCenterFractionDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 0.6)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">2</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblTextYCenterFractionExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The vertical position (0 = top, 1 = bottom) within a text box used as its center for vertical alignment, since a text box's true geometric center often looks slightly off due to descender space.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">3</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowLineCrossSnapTolerance\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineCrossSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Line crossing assist tolerance</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryLineCrossSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineCrossSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 6.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">4</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblLineCrossSnapToleranceExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The tolerance, in screen pixels, used by the coordinate system assist (patch 8.4) when snapping a drawn line's length to match another line it crosses at a right angle.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">5</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowSplineAlignmentSnapTolerance\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblSplineAlignmentSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Spline tool alignment tolerance</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entrySplineAlignmentSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblSplineAlignmentSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 6.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">6</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblSplineAlignmentSnapToleranceExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The tolerance, in screen pixels, for the spline tool's own alignment snap (patch 8.9) - a separate setting from the general object alignment tolerance above.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">7</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowDiagonalSnapTolerance\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblDiagonalSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Circle assist tolerance</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryDiagonalSnapTolerance\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblDiagonalSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 15.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">8</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblDiagonalSnapToleranceExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The tolerance, in screen pixels, within which an ellipse's width and height are considered close enough to snap to a perfect circle (patch 8.5).&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">9</property>
                                              </packing>
                                            </child>
                                          </object>
                                        </child>
                                        <child type=\"label\">
                                          <object class=\"GtkLabel\" id=\"snapingNormalLabel\">
                                            <property name=\"visible\">True</property>
                                            <property name=\"can-focus\">False</property>
                                            <property name=\"label\" translatable=\"yes\">Normal</property>
                                          </object>
                                        </child>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">0</property>
                                      </packing>
                                    </child>
                                    <child>
                                      <object class=\"GtkFrame\" id=\"snapingAdvancedFrame\">
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">False</property>
                                        <property name=\"label-xalign\">0.0099999997764825821</property>
                                        <child>
                                          <object class=\"GtkBox\" id=\"snapingAdvancedBox\">
                                            <property name=\"visible\">True</property>
                                            <property name=\"can-focus\">False</property>
                                            <property name=\"margin-start\">12</property>
                                            <property name=\"margin-end\">12</property>
                                            <property name=\"margin-bottom\">8</property>
                                            <property name=\"orientation\">vertical</property>
                                            <property name=\"spacing\">6</property>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowPerpendicularCrossBoostFactor\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblPerpendicularCrossBoostFactor\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Perpendicular cross boost factor</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryPerpendicularCrossBoostFactor\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblPerpendicularCrossBoostFactorDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 4.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">0</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblPerpendicularCrossBoostFactorExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;Multiplier applied to the base alignment tolerance for the \"boosted\" (blue) tier's own matching tolerance and Top/Middle/Below zone radius, when a small line crosses a much bigger perpendicular one.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">1</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowLineEndAnchorToleranceFactor\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineEndAnchorToleranceFactor\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Line end anchor tolerance factor</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryLineEndAnchorToleranceFactor\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineEndAnchorToleranceFactorDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 0.9)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">2</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblLineEndAnchorToleranceFactorExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;Tolerance factor for snapping a small line to one of a big line's own two endpoints - deliberately smaller than the perpendicular cross boost factor, since this is a precise \"line up exactly with the end\" gesture.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">3</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowSmallMarkMaxLength\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblSmallMarkMaxLength\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Small mark max length</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entrySmallMarkMaxLength\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblSmallMarkMaxLengthDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 15.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">4</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblSmallMarkMaxLengthExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The maximum bounding-box side length, in document points, below which an object (like a tick or a cross mark) is treated as a \"small mark\" and forced to a single center-only anchor on both axes. For a plain line specifically, this same value also gates the \"boosted\" (blue) perpendicular-cross match and, in turn, line-end anchoring - non-line objects (including arrows) always use a fixed 15.0 for this rule instead.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">5</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkBox\" id=\"rowLineCrossMinLength\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"orientation\">horizontal</property>
                                                <property name=\"spacing\">6</property>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineCrossMinLength\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">Line crossing assist minimum length</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">0</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkEntry\" id=\"entryLineCrossMinLength\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">True</property>
                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblLineCrossMinLengthDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 50.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">6</property>
                                              </packing>
                                            </child>
                                            <child>
                                              <object class=\"GtkLabel\" id=\"lblLineCrossMinLengthExplanation\">
                                                <property name=\"visible\">True</property>
                                                <property name=\"can-focus\">False</property>
                                                <property name=\"label\" translatable=\"yes\">&lt;i&gt;The minimum length, in document points, a drawn line/arrow must already have - and a target line on the layer must have - for the coordinate system assist (patch 8.4) to consider them at all.&lt;/i&gt;</property>
                                                <property name=\"use-markup\">True</property>
                                                <property name=\"wrap\">True</property>
                                                <property name=\"max-width-chars\">85</property>
                                                <property name=\"xalign\">0</property>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">7</property>
                                              </packing>
                                            </child>
                                          </object>
                                        </child>
                                        <child type=\"label\">
                                          <object class=\"GtkLabel\" id=\"snapingAdvancedLabel\">
                                            <property name=\"visible\">True</property>
                                            <property name=\"can-focus\">False</property>
                                            <property name=\"label\" translatable=\"yes\">Advanced</property>
                                          </object>
                                        </child>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">1</property>
                                      </packing>
                                    </child>
                                  </object>
                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingSettingsLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Settings</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">2</property>
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
                <property name=\"name\">defaultTabBox</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"margin-start\">5</property>
                <property name=\"orientation\">vertical</property>"""
GLADE_OLD1 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">8</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"toolsTabLabel\">
                <property name=\"name\">defaultTabLabel</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Tools</property>
              </object>
              <packing>
                <property name=\"position\">8</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"audioRecordingTabBox\">
                <property name=\"name\">audioRecordingTabBox</property>"""
GLADE_NEW1 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">9</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"toolsTabLabel\">
                <property name=\"name\">defaultTabLabel</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Tools</property>
              </object>
              <packing>
                <property name=\"position\">9</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"audioRecordingTabBox\">
                <property name=\"name\">audioRecordingTabBox</property>"""
GLADE_OLD2 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">9</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"audioRecordingTabLabel\">
                <property name=\"name\">audioRecordingTabLabel</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Audio Recording</property>
              </object>
              <packing>
                <property name=\"position\">9</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"latexTabBox\">
                <property name=\"visible\">True</property>"""
GLADE_NEW2 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">10</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"audioRecordingTabLabel\">
                <property name=\"name\">audioRecordingTabLabel</property>
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Audio Recording</property>
              </object>
              <packing>
                <property name=\"position\">10</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"latexTabBox\">
                <property name=\"visible\">True</property>"""
GLADE_OLD3 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">11</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"languageTabLabel\">
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Language</property>
              </object>
              <packing>
                <property name=\"position\">11</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"paletteTabBox\">
                <property name=\"visible\">True</property>"""
GLADE_NEW3 = """                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>
                </child>
              </object>
              <packing>
                <property name=\"position\">12</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"languageTabLabel\">
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Language</property>
              </object>
              <packing>
                <property name=\"position\">12</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
            <child>
              <object class=\"GtkBox\" id=\"paletteTabBox\">
                <property name=\"visible\">True</property>"""
GLADE_OLD4 = """                <property name=\"orientation\">vertical</property>
                <child>
                  <placeholder/>
                </child>
              </object>
              <packing>
                <property name=\"position\">12</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"paletteTabLabel\">
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Palette</property>
              </object>
              <packing>
                <property name=\"position\">12</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name=\"expand\">True</property>"""
GLADE_NEW4 = """                <property name=\"orientation\">vertical</property>
                <child>
                  <placeholder/>
                </child>
              </object>
              <packing>
                <property name=\"position\">13</property>
              </packing>
            </child>
            <child type=\"tab\">
              <object class=\"GtkLabel\" id=\"paletteTabLabel\">
                <property name=\"visible\">True</property>
                <property name=\"can-focus\">False</property>
                <property name=\"label\" translatable=\"yes\">Palette</property>
              </object>
              <packing>
                <property name=\"position\">13</property>
                <property name=\"tab-fill\">False</property>
              </packing>
            </child>
          </object>
          <packing>
            <property name=\"expand\">True</property>"""


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


def create_file(path: Path, content: str, label: str) -> bool:
    if path.exists():
        print(f"[SKIP]  {label}: existe deja.")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    paths = {
        "fr": Path("po/fr.po"),
        "pot": Path("po/xournalpp.pot"),
        "ctrl_cpp": Path("src/core/control/Control.cpp"),
        "ctrl_h": Path("src/core/control/Control.h"),
        "actprops": Path("src/core/control/actions/ActionProperties.h"),
        "settings_cpp": Path("src/core/control/settings/Settings.cpp"),
        "settings_h": Path("src/core/control/settings/Settings.h"),
        "arrow": Path("src/core/control/tools/ArrowHandler.cpp"),
        "bsh_cpp": Path("src/core/control/tools/BaseShapeHandler.cpp"),
        "bsh_h": Path("src/core/control/tools/BaseShapeHandler.h"),
        "es_cpp": Path("src/core/control/tools/EditSelection.cpp"),
        "es_h": Path("src/core/control/tools/EditSelection.h"),
        "ellipse": Path("src/core/control/tools/EllipseHandler.cpp"),
        "ruler": Path("src/core/control/tools/RulerHandler.cpp"),
        "spline_cpp": Path("src/core/control/tools/SplineHandler.cpp"),
        "spline_h": Path("src/core/control/tools/SplineHandler.h"),
        "action_enum": Path("src/core/enums/Action.enum.h"),
        "namemap": Path("src/core/enums/generated/Action.NameMap.generated.h"),
        "sd_cpp": Path("src/core/gui/dialog/SettingsDialog.cpp"),
        "sd_h": Path("src/core/gui/dialog/SettingsDialog.h"),
        "stroke": Path("src/core/model/Stroke.cpp"),
        "shapeview": Path("src/core/view/overlays/ShapeToolView.cpp"),
        "splineview": Path("src/core/view/overlays/SplineToolView.cpp"),
        "menubar": Path("ui/mainmenubar.xml"),
        "glade": Path("ui/settings.glade"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "Patch 11.10.2" in paths["settings_cpp"].read_text(encoding="utf-8"):
        print("[SKIP] Ce patch (apply_alignment_snap_v90_5) semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= create_file(Path("src/core/undo/LineRepositionUndoAction.h"), NEW_FILE_H,
                      "src/core/undo/LineRepositionUndoAction.h: fichier cree")
    ok &= create_file(Path("src/core/undo/LineRepositionUndoAction.cpp"), NEW_FILE_CPP,
                      "src/core/undo/LineRepositionUndoAction.cpp: fichier cree")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/1")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/3")
    ok &= apply_edit(paths["pot"], POT_OLD1, POT_NEW1, "pot: zone 2/3")
    ok &= apply_edit(paths["pot"], POT_OLD2, POT_NEW2, "pot: zone 3/3")
    ok &= apply_edit(paths["ctrl_cpp"], CTRL_CPP_OLD0, CTRL_CPP_NEW0, "ctrl_cpp: zone 1/1")
    ok &= apply_edit(paths["ctrl_h"], CTRL_H_OLD0, CTRL_H_NEW0, "ctrl_h: zone 1/1")
    ok &= apply_edit(paths["actprops"], ACTPROPS_OLD0, ACTPROPS_NEW0, "actprops: zone 1/1")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD0, SETTINGS_CPP_NEW0, "settings_cpp: zone 1/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD1, SETTINGS_CPP_NEW1, "settings_cpp: zone 2/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD2, SETTINGS_CPP_NEW2, "settings_cpp: zone 3/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD3, SETTINGS_CPP_NEW3, "settings_cpp: zone 4/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD0, SETTINGS_H_NEW0, "settings_h: zone 1/2")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD1, SETTINGS_H_NEW1, "settings_h: zone 2/2")
    ok &= apply_edit(paths["arrow"], ARROW_OLD0, ARROW_NEW0, "arrow: zone 1/1")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD0, BSH_CPP_NEW0, "bsh_cpp: zone 1/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD1, BSH_CPP_NEW1, "bsh_cpp: zone 2/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD2, BSH_CPP_NEW2, "bsh_cpp: zone 3/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD3, BSH_CPP_NEW3, "bsh_cpp: zone 4/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD4, BSH_CPP_NEW4, "bsh_cpp: zone 5/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD5, BSH_CPP_NEW5, "bsh_cpp: zone 6/7")
    ok &= apply_edit(paths["bsh_cpp"], BSH_CPP_OLD6, BSH_CPP_NEW6, "bsh_cpp: zone 7/7")
    ok &= apply_edit(paths["bsh_h"], BSH_H_OLD0, BSH_H_NEW0, "bsh_h: zone 1/4")
    ok &= apply_edit(paths["bsh_h"], BSH_H_OLD1, BSH_H_NEW1, "bsh_h: zone 2/4")
    ok &= apply_edit(paths["bsh_h"], BSH_H_OLD2, BSH_H_NEW2, "bsh_h: zone 3/4")
    ok &= apply_edit(paths["bsh_h"], BSH_H_OLD3, BSH_H_NEW3, "bsh_h: zone 4/4")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD0, ES_CPP_NEW0, "es_cpp: zone 1/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD1, ES_CPP_NEW1, "es_cpp: zone 2/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD2, ES_CPP_NEW2, "es_cpp: zone 3/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD3, ES_CPP_NEW3, "es_cpp: zone 4/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD4, ES_CPP_NEW4, "es_cpp: zone 5/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD5, ES_CPP_NEW5, "es_cpp: zone 6/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD6, ES_CPP_NEW6, "es_cpp: zone 7/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD7, ES_CPP_NEW7, "es_cpp: zone 8/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD8, ES_CPP_NEW8, "es_cpp: zone 9/10")
    ok &= apply_edit(paths["es_cpp"], ES_CPP_OLD9, ES_CPP_NEW9, "es_cpp: zone 10/10")
    ok &= apply_edit(paths["es_h"], ES_H_OLD0, ES_H_NEW0, "es_h: zone 1/3")
    ok &= apply_edit(paths["es_h"], ES_H_OLD1, ES_H_NEW1, "es_h: zone 2/3")
    ok &= apply_edit(paths["es_h"], ES_H_OLD2, ES_H_NEW2, "es_h: zone 3/3")
    ok &= apply_edit(paths["ellipse"], ELLIPSE_OLD0, ELLIPSE_NEW0, "ellipse: zone 1/1")
    ok &= apply_edit(paths["ruler"], RULER_OLD0, RULER_NEW0, "ruler: zone 1/1")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD0, SPLINE_CPP_NEW0, "spline_cpp: zone 1/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD1, SPLINE_CPP_NEW1, "spline_cpp: zone 2/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD2, SPLINE_CPP_NEW2, "spline_cpp: zone 3/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD3, SPLINE_CPP_NEW3, "spline_cpp: zone 4/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD4, SPLINE_CPP_NEW4, "spline_cpp: zone 5/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD5, SPLINE_CPP_NEW5, "spline_cpp: zone 6/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD6, SPLINE_CPP_NEW6, "spline_cpp: zone 7/8")
    ok &= apply_edit(paths["spline_cpp"], SPLINE_CPP_OLD7, SPLINE_CPP_NEW7, "spline_cpp: zone 8/8")
    ok &= apply_edit(paths["spline_h"], SPLINE_H_OLD0, SPLINE_H_NEW0, "spline_h: zone 1/3")
    ok &= apply_edit(paths["spline_h"], SPLINE_H_OLD1, SPLINE_H_NEW1, "spline_h: zone 2/3")
    ok &= apply_edit(paths["spline_h"], SPLINE_H_OLD2, SPLINE_H_NEW2, "spline_h: zone 3/3")
    ok &= apply_edit(paths["action_enum"], ACTION_ENUM_OLD0, ACTION_ENUM_NEW0, "action_enum: zone 1/1")
    ok &= apply_edit(paths["namemap"], NAMEMAP_OLD0, NAMEMAP_NEW0, "namemap: zone 1/1")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD0, SD_CPP_NEW0, "sd_cpp: zone 1/6")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD1, SD_CPP_NEW1, "sd_cpp: zone 2/6")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD2, SD_CPP_NEW2, "sd_cpp: zone 3/6")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD3, SD_CPP_NEW3, "sd_cpp: zone 4/6")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD4, SD_CPP_NEW4, "sd_cpp: zone 5/6")
    ok &= apply_edit(paths["sd_cpp"], SD_CPP_OLD5, SD_CPP_NEW5, "sd_cpp: zone 6/6")
    ok &= apply_edit(paths["sd_h"], SD_H_OLD0, SD_H_NEW0, "sd_h: zone 1/2")
    ok &= apply_edit(paths["sd_h"], SD_H_OLD1, SD_H_NEW1, "sd_h: zone 2/2")
    ok &= apply_edit(paths["stroke"], STROKE_OLD0, STROKE_NEW0, "stroke: zone 1/2")
    ok &= apply_edit(paths["stroke"], STROKE_OLD1, STROKE_NEW1, "stroke: zone 2/2")
    ok &= apply_edit(paths["shapeview"], SHAPEVIEW_OLD0, SHAPEVIEW_NEW0, "shapeview: zone 1/2")
    ok &= apply_edit(paths["shapeview"], SHAPEVIEW_OLD1, SHAPEVIEW_NEW1, "shapeview: zone 2/2")
    ok &= apply_edit(paths["splineview"], SPLINEVIEW_OLD0, SPLINEVIEW_NEW0, "splineview: zone 1/1")
    ok &= apply_edit(paths["menubar"], MENUBAR_OLD0, MENUBAR_NEW0, "menubar: zone 1/1")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/5")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/5")
    ok &= apply_edit(paths["glade"], GLADE_OLD2, GLADE_NEW2, "glade: zone 3/5")
    ok &= apply_edit(paths["glade"], GLADE_OLD3, GLADE_NEW3, "glade: zone 4/5")
    ok &= apply_edit(paths["glade"], GLADE_OLD4, GLADE_NEW4, "glade: zone 5/5")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
