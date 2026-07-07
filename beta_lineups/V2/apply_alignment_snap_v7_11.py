#!/usr/bin/env python3
"""
Patch 7.11 : fusion des patchs v1 a v7.9 ET 9.1 en un seul, applicable
PAR-DESSUS d'autres patchs - modifications CIBLEES par ancres de texte
(pas de reecriture de fichier entier), exactement comme le reste de
cette serie. Remplace le patch 7.10, en y integrant aussi les
changements du patch 9.1 (regles "petite marque" et "croix", couleur
rose pour un axe simplement fin).

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v1.py
    apply_alignment_snap_v2.py
    apply_alignment_snap_v3.py
    apply_alignment_snap_v4.py
    apply_alignment_snap_v5.py
    apply_alignment_snap_v6.py
    apply_alignment_snap_v7.py
    apply_alignment_snap_v7_5.py
    apply_alignment_snap_v7_6.py
    apply_alignment_snap_v7_8.py
    apply_alignment_snap_v7_9.py
    apply_alignment_snap_v9_1.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch).

Fichiers concernes :
  - src/core/control/Control.cpp\n  - src/core/control/Control.h\n  - src/core/control/actions/ActionProperties.h\n  - src/core/control/settings/Settings.cpp\n  - src/core/control/settings/Settings.h\n  - src/core/control/tools/EditSelection.cpp\n  - src/core/control/tools/EditSelection.h\n  - src/core/enums/Action.enum.h\n  - src/core/enums/generated/Action.NameMap.generated.h\n  - src/core/model/Stroke.cpp\n  - ui/mainmenubar.xml\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py (fournit ArrowKind/getArrowKind(), deja
     necessaire par la chaine v1-v7.9 elle-meme a partir de v7_5)

NE PAS appliquer si l'un des patchs v1.py a v7_9.py, v7_10.py, ou 9_1.py
a deja ete applique sur ce depot.

A lancer depuis la racine du depot xournalpp, sur une copie fraiche avec
seulement apply_arrow_resize_fix_v2.py deja applique.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/Control.cpp", [
        ("""    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);
}

auto Control::getTextEditor() -> TextEditor* {
    if (this->win) {
        return this->win->getXournal()->getTextEditor();""", """    this->actionDB->setActionState(Action::GRID_SNAPPING, enable);
}

void Control::setObjectAlignmentSnapping(bool enable) {
    settings->setSnapToObjects(enable);
    this->actionDB->setActionState(Action::OBJECT_ALIGNMENT_SNAPPING, enable);
}

auto Control::getTextEditor() -> TextEditor* {
    if (this->win) {
        return this->win->getXournal()->getTextEditor();"""),
    ]),
    ("src/core/control/Control.h", [
        ("""protected:
    void setRotationSnapping(bool enable);
    void setGridSnapping(bool enable);

    void showFontDialog();
    void showColorChooserDialog();""", """protected:
    void setRotationSnapping(bool enable);
    void setGridSnapping(bool enable);
    void setObjectAlignmentSnapping(bool enable);

    void showFontDialog();
    void showColorChooserDialog();"""),
    ]),
    ("src/core/control/actions/ActionProperties.h", [
        ("""};

template <>
struct ActionProperties<Action::PREFERENCES> {
    using app_namespace = std::true_type;
    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->showSettings(); }""", """};

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
    static void callback(GSimpleAction*, GVariant*, Control* ctrl) { ctrl->showSettings(); }"""),
    ]),
    ("src/core/control/settings/Settings.cpp", [
        ("""    this->snapGrid = true;
    this->snapGridTolerance = 0.50;
    this->snapGridSize = DEFAULT_GRID_SIZE;

    this->strokeRecognizerMinSize = 40;
""", """    this->snapGrid = true;
    this->snapGridTolerance = 0.50;
    this->snapGridSize = DEFAULT_GRID_SIZE;
    this->snapToObjects = true;

    this->strokeRecognizerMinSize = 40;
"""),
        ("""        this->snapRotationTolerance = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGrid\")) == 0) {
        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridSize\")) == 0) {
        this->snapGridSize = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridTolerance\")) == 0) {""", """        this->snapRotationTolerance = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGrid\")) == 0) {
        this->snapGrid = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapToObjects\")) == 0) {
        this->snapToObjects = xmlStrcmp(value, reinterpret_cast<const xmlChar*>(\"true\")) == 0;
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridSize\")) == 0) {
        this->snapGridSize = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);
    } else if (xmlStrcmp(name, reinterpret_cast<const xmlChar*>(\"snapGridTolerance\")) == 0) {"""),
        ("""    SAVE_BOOL_PROP(snapGrid);
    SAVE_DOUBLE_PROP(snapGridTolerance);
    SAVE_DOUBLE_PROP(snapGridSize);

    SAVE_DOUBLE_PROP(strokeRecognizerMinSize);
""", """    SAVE_BOOL_PROP(snapGrid);
    SAVE_DOUBLE_PROP(snapGridTolerance);
    SAVE_DOUBLE_PROP(snapGridSize);
    SAVE_BOOL_PROP(snapToObjects);

    SAVE_DOUBLE_PROP(strokeRecognizerMinSize);
"""),
        ("""    save();
}

void Settings::setSnapGridTolerance(double tolerance) {
    this->snapGridTolerance = tolerance;
    save();""", """    save();
}

auto Settings::isSnapToObjects() const -> bool { return this->snapToObjects; }

void Settings::setSnapToObjects(bool b) {
    if (this->snapToObjects == b) {
        return;
    }

    this->snapToObjects = b;
    save();
}

void Settings::setSnapGridTolerance(double tolerance) {
    this->snapGridTolerance = tolerance;
    save();"""),
    ]),
    ("src/core/control/settings/Settings.h", [
        ("""    double getSnapGridSize() const;
    void setSnapGridSize(double gridSize);

    double getStrokeRecognizerMinSize() const;
    void setStrokeRecognizerMinSize(double value);
""", """    double getSnapGridSize() const;
    void setSnapGridSize(double gridSize);

    bool isSnapToObjects() const;
    void setSnapToObjects(bool b);

    double getStrokeRecognizerMinSize() const;
    void setStrokeRecognizerMinSize(double value);
"""),
        ("""    bool snapGrid{};

    /**
     * Default name if you save a new document
     */
    std::u8string defaultSaveName;  // should be string - don't change to path""", """    bool snapGrid{};

    /**
     * object alignment (\"smart guides\") snapping enabled by default
     */
    bool snapToObjects{};

    /**
     * Default name if you save a new document
     */
    std::u8string defaultSaveName;  // should be string - don't change to path"""),
    ]),
    ("src/core/control/tools/EditSelection.cpp", [
        ("""#include \"model/Document.h\"                        // for Document
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
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector""", """#include \"model/Document.h\"                        // for Document
#include \"model/Element.h\"                         // for Element::Index
#include \"model/ElementInsertionPosition.h\"
#include \"model/Layer.h\"                          // for Layer
#include \"model/LineStyle.h\"                      // for LineStyle
#include \"model/Point.h\"                          // for Point
#include \"model/Stroke.h\"                         // for Stroke
#include \"model/Text.h\"                           // for Text
#include \"model/XojPage.h\"                        // for XojPage
#include \"undo/ArrangeUndoAction.h\"               // for ArrangeUndoAction
#include \"undo/InsertUndoAction.h\"                // for InsertsUndoAction
#include \"undo/UndoRedoHandler.h\"                 // for UndoRedoHandler
#include \"util/Range.h\"                           // for Range
#include \"util/Util.h\"                            // for cairo_set_dash_from_vector"""),
        ("""EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,
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
    const double PADDING = 12.;""", """EditSelection::EditSelection(Control* ctrl, InsertionOrder elts, const PageRef& page, Layer* layer, XojPageView* view,
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
    const double PADDING = 12.;"""),
        ("""
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
""", """
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
"""),
        ("""    this->sourceLayer = layer;

    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    this->mouseDownType = CURSOR_SELECTION_NONE;

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);
    updateMatrix();
    if (wasEdgePanning) {
        this->ensureWithinVisibleArea();""", """    this->sourceLayer = layer;

    this->contents->updateContent(this->getRect(), this->snappedBounds, this->rotation, this->preserveAspectRatio,
                                  layer, page, this->undo, this->mouseDownType);

    this->mouseDownType = CURSOR_SELECTION_NONE;
    this->activeGuidesX.clear();
    this->activeGuidesY.clear();

    const bool wasEdgePanning = this->isEdgePanning();
    this->setEdgePan(false);
    updateMatrix();
    if (wasEdgePanning) {
        this->ensureWithinVisibleArea();"""),
        ("""    // box edges horizontal/vertical
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
            cx += this->snappedBounds.width;""", """    // box edges horizontal/vertical
    cairo_matrix_transform_point(&this->cmatrix, &x, &y);
    this->relMousePosRotX = x / zoom - this->snappedBounds.x;
    this->relMousePosRotY = y / zoom - this->snappedBounds.y;
}

/**
 * Smart alignment guides (sub-patch 1: silent snap, no visual guide line yet).
 *
 * Tolerance in screen pixels (independent of zoom) within which a candidate edge/center of the
 * moving selection's bounding box is considered \"aligned\" with a candidate edge/center of another
 * element on the same layer.
 */
constexpr double ALIGNMENT_SNAP_TOLERANCE_PX = 6.0;

/**
 * Result of a successful alignment match: `offset` is the amount to shift the moving object's
 * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide
 * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the
 * moving object and the matched object, so the drawn guide line visually connects the two.
 * `isCenter` is true if either of the two matched candidates was a center point (rather than an
 * edge); `isBoosted` is true for the special \"small stroke crossing a big perpendicular stroke,
 * center-to-center\" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.
 */
struct AlignmentMatch {
    double offset;
    double coordinate;
    double extentFrom;
    double extentTo;
    bool isCenter;
    bool isBoosted;
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
 */
constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 1.5;

/**
 * The \"small stroke crossing a big perpendicular stroke\" boost only applies if the small stroke's
 * own length (its extent along its own axis, e.g. a vertical tick's height) is at most this many
 * document points - the same unit used for arrow-key nudging.
 */
constexpr double PERPENDICULAR_CROSS_MAX_SELF_LENGTH = 15.0;

/**
 * Fraction (0 to 1, from the top) of a Text element's height used as its horizontal-alignment (Y)
 * anchor, instead of the true geometric center (0.5). Text bounding boxes include descender space
 * below the baseline, which pulls the geometric center lower than where a horizontal alignment
 * \"feels\" visually centered on the text - this constant lets that be tuned independently of
 * everything else. Deliberately left at an easily-noticeable default; tune to taste.
 */
constexpr double TEXT_Y_CENTER_FRACTION = 0.6;

/**
 * Below this length (in document points, measured as the larger of an element's own width/height),
 * an element is considered a \"small mark\" for anchor purposes - see buildCandidates()'s
 * `forceCenterOnly` parameter. Distinct from THIN_AXIS_THRESHOLD (which only concerns a single axis
 * relative to a long line) - this instead looks at the object as a whole, so a small tick or cross
 * mark always gets a single center anchor on *both* axes, regardless of how it happens to be
 * proportioned.
 */
constexpr double SMALL_MARK_MAX_LENGTH = 15.0;

/// True if an element whose own bounding box is `width` x `height` counts as a \"small mark\" - see
/// SMALL_MARK_MAX_LENGTH.
static auto isSmallMark(double width, double height) -> bool { return std::max(width, height) < SMALL_MARK_MAX_LENGTH; }

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
                                             double otherHeight, CrossAxis axis) -> bool {
    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;
    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;
    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;
    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;

    if (axis == CrossAxis::Y) {
        return selfVertical && otherHorizontal && selfHeight < otherWidth &&
               selfHeight <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;
    }
    return selfHorizontal && otherVertical && selfWidth < otherHeight &&
           selfWidth <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;
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
static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height, 0.5, isSmallMark(xRight - xLeft, height));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
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
        bool crossEligible = isSmallCrossingBigPerpendicular(xRight - xLeft, height, shaft.width, shaft.height, CrossAxis::Y) &&
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
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.y, snapped.height, otherCenterFraction,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              std::min(xLeft, snapped.x),
                                              std::max(xRight, snapped.x + snapped.width),
                                              cs.isCenter || co.isCenter,
                                              false};
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
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
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? TEXT_Y_CENTER_FRACTION : 0.5;
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.y, snapped.height, otherCenterFraction,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(xLeft, snapped.x),
                                                     std::max(xRight, snapped.x + snapped.width),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
}

/// Same as findAlignmentY(), but for the horizontal candidates (left / horizontal-center / right).
/// yTop/yBottom are the moving box's vertical extent, used for the crossing/overlap check and the
/// guide line's span. Unlike findAlignmentY(), there is no Text-specific center fraction here.
static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width, 0.5, isSmallMark(width, yBottom - yTop));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR;
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
        bool crossEligible = isSmallCrossingBigPerpendicular(width, yBottom - yTop, shaft.width, shaft.height, CrossAxis::X) &&
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
        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) ||
             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y)) &&
            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.x, snapped.width, 0.5,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                double dist = std::abs(cs.value - co.value);
                if (dist < bestAnyDist) {
                    bestAnyDist = dist;
                    bestAny = AlignmentMatch{co.value - cs.value,
                                              co.value,
                                              std::min(yTop, snapped.y),
                                              std::max(yBottom, snapped.y + snapped.height),
                                              cs.isCenter || co.isCenter,
                                              false};
                }
            }
        }
    }
    if (!bestAny) {
        return std::nullopt;
    }

    // --- second pass: collect every match consistent with the chosen offset ---
    double offset = bestAny->offset;
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
        if ((isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X) ||
             isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::Y)) &&
            rangesOverlap(yTop, yBottom, snapped.y, snapped.y + snapped.height)) {
            continue;
        }
        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.x, snapped.width, 0.5,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        for (auto& cs: candidatesSelf) {
            for (auto& co: candidatesOther) {
                if (std::abs((cs.value + offset) - co.value) < tolerance) {
                    guides.push_back(AlignmentMatch{offset, co.value, std::min(yTop, snapped.y),
                                                     std::max(yBottom, snapped.y + snapped.height),
                                                     cs.isCenter || co.isCenter, false});
                }
            }
        }
    }
    return AlignmentSearchResult{offset, guides};
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

                double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;
                std::vector<const Element*> excluded = this->getElementsView().clone();
                double candidateX = this->snappedBounds.x + dx;
                double candidateY = this->snappedBounds.y + dy;
                double width = this->snappedBounds.width;
                double height = this->snappedBounds.height;

                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,
                                              this->sourceLayer, excluded, visibleRect);
                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              this->sourceLayer, excluded, visibleRect);

                if (matchX) {
                    dx += matchX->offset;
                    objectSnappedX = true;
                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});
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
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted});
                    }
                } else {
                    this->activeGuidesY.clear();
                }
            }
        } else {
            this->activeGuidesX.clear();
            this->activeGuidesY.clear();
        }

        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position
        double cx = this->snappedBounds.x;
        double cy = this->snappedBounds.y;
        if ((this->relMousePosRotX > this->snappedBounds.width / 2) ==
            (this->snappedBounds.width > 0)) {  // closer to the right side
            cx += this->snappedBounds.width;"""),
        ("""        cx /= zoom;
        cy /= zoom;

        // compute position where unsnapped corner would move
        Point p = Point(cx + dx, cy + dy);

        // snap this corner
        p = snappingHandler.snapToGrid(p, alt);

        // move
        if (!this->edgePanInhibitNext) {
            moveSelection(p.x - cx, p.y - cy);
            this->setEdgePan(true);
        } else {""", """        cx /= zoom;
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
        } else {"""),
        ("""        cairo_translate(cr, -rx, -ry);
    }
    this->contents->paint(cr, x, y, this->rotation, this->width, this->height, zoom);

    cairo_set_operator(cr, CAIRO_OPERATOR_OVER);

    GdkRGBA selectionColor = view->getSelectionColor();

    // set the line always the same size on display
    cairo_set_line_width(cr, 1);

    const std::vector<double> dashes = {10.0, 10.0};""", """        cairo_translate(cr, -rx, -ry);
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
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
            } else if (guide.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
            }
            double gx = guide.coordinate * zoom;
            cairo_move_to(cr, gx, guide.from * zoom);
            cairo_line_to(cr, gx, guide.to * zoom);
            cairo_stroke(cr);
        }
        for (auto& guide: this->activeGuidesY) {
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
            } else if (guide.isCenter) {
                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green
            } else {
                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink
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

    const std::vector<double> dashes = {10.0, 10.0};"""),
    ]),
    ("src/core/control/tools/EditSelection.h", [
        ("""
#include <array>
#include <memory>  // for unique_ptr
#include <string>
#include <utility>  // for pair
#include <vector>   // for vector""", """
#include <array>
#include <memory>  // for unique_ptr
#include <optional>
#include <string>
#include <utility>  // for pair
#include <vector>   // for vector"""),
        ("""class DeleteUndoAction;
class LineStyle;
class ObjectInputStream;
class ObjectOutputStream;
class XojFont;
class Document;""", """class DeleteUndoAction;
class LineStyle;
class ObjectInputStream;
class Settings;
class ObjectOutputStream;
class XojFont;
class Document;"""),
        ("""    Layer* sourceLayer{};

    /**
     * The contents of the selection
     */
    std::unique_ptr<EditSelectionContents> contents;""", """    Layer* sourceLayer{};

    /**
     * Used to check whether object-alignment snapping (\"smart guides\") is enabled.
     */
    const Settings* settings{};

    /**
     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or
     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that
     * spans between the moving selection and the element it is aligned with, so the drawn line
     * visually connects the two.
     */
    struct AlignmentGuide {
        double coordinate;
        double from;
        double to;
        bool isCenter;
        bool isBoosted;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a
    /// single line, but can hold several simultaneously when multiple anchor points agree on the
    /// same alignment (e.g. two identically-sized objects whose top, center and bottom all line up
    /// at once) - see findAlignmentX/Y() in EditSelection.cpp.
    std::vector<AlignmentGuide> activeGuidesX;
    /// Horizontal guide lines (constant y), same as activeGuidesX but for the Y axis.
    std::vector<AlignmentGuide> activeGuidesY;

    /**
     * The contents of the selection
     */
    std::unique_ptr<EditSelectionContents> contents;"""),
    ]),
    ("src/core/enums/Action.enum.h", [
        ("""    MOVE_SELECTION_LAYER_DOWN,
    ROTATION_SNAPPING,
    GRID_SNAPPING,
    PREFERENCES,

    // Menu View""", """    MOVE_SELECTION_LAYER_DOWN,
    ROTATION_SNAPPING,
    GRID_SNAPPING,
    OBJECT_ALIGNMENT_SNAPPING,
    PREFERENCES,

    // Menu View"""),
    ]),
    ("src/core/enums/generated/Action.NameMap.generated.h", [
        ("""        \"move-selection-layer-down\",
        \"rotation-snapping\",
        \"grid-snapping\",
        \"preferences\",
        \"paired-pages-mode\",
        \"paired-pages-offset\",""", """        \"move-selection-layer-down\",
        \"rotation-snapping\",
        \"grid-snapping\",
        \"object-alignment-snapping\",
        \"preferences\",
        \"paired-pages-mode\",
        \"paired-pages-offset\","""),
    ]),
    ("src/core/model/Stroke.cpp", [
        ("""
auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }

void Stroke::setArrowKind(ArrowKind kind) { this->arrowKind = kind; }

auto Stroke::getArrowKind() const -> ArrowKind { return this->arrowKind; }
""", """
auto Stroke::getToolType() const -> StrokeTool { return this->toolType; }

void Stroke::setArrowKind(ArrowKind kind) {
    this->arrowKind = kind;
    // setPointVector() may have already cached snappedBounds directly from the full point-list range
    // (see setPointVectorInternal()), before this arrowKind is known - invalidate that cache so the
    // next access recomputes it through calcSize(), which now knows to exclude the arrowhead.
    this->sizeCalculated = false;
}

auto Stroke::getArrowKind() const -> ArrowKind { return this->arrowKind; }
"""),
        ("""    Element::y = minY;
    Element::width = maxX - minX;
    Element::height = maxY - minY;
    Element::snappedBounds = Rectangle<double>(minSnapX, minSnapY, maxSnapX - minSnapX, maxSnapY - minSnapY);
}

auto Stroke::getErasable() const -> ErasableStroke* { return this->erasable; }""", """    Element::y = minY;
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

auto Stroke::getErasable() const -> ErasableStroke* { return this->erasable; }"""),
    ]),
    ("ui/mainmenubar.xml", [
        ("""     <attribute name=\"label\" translatable=\"yes\">Grid Snapping</attribute>
     <attribute name=\"action\">win.grid-snapping</attribute>
    </item>
   </section>
   <section>
    <item>""", """     <attribute name=\"label\" translatable=\"yes\">Grid Snapping</attribute>
     <attribute name=\"action\">win.grid-snapping</attribute>
    </item>
    <item>
     <attribute name=\"label\" translatable=\"yes\">Object Alignment Snapping</attribute>
     <attribute name=\"action\">win.object-alignment-snapping</attribute>
    </item>
   </section>
   <section>
    <item>"""),
    ]),
]


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
    stroke_h = Path("src/core/model/Stroke.h")
    if not stroke_h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "ArrowKind" not in stroke_h.read_text(encoding="utf-8"):
        print("[ECHEC] ArrowKind introuvable dans src/core/model/Stroke.h.")
        print("        Appliquez d'abord apply_arrow_resize_fix_v2.py, puis relancez ce script.")
        sys.exit(1)

    enum_h = Path("src/core/enums/Action.enum.h")
    if enum_h.exists() and "OBJECT_ALIGNMENT_SNAPPING" in enum_h.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 7.11 (ou la chaine qu'il remplace) semble deja applique.")
        sys.exit(0)

    ok = True
    for rel_path, edits in EDITS:
        path = Path(rel_path)
        if not path.exists():
            print(f"[ECHEC] Fichier introuvable : {rel_path}")
            ok = False
            continue
        for i, (old, new) in enumerate(edits, 1):
            label = f"{rel_path} (zone {i}/{len(edits)})"
            ok &= apply_edit(path, old, new, label)

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
