#!/usr/bin/env python3
"""
apply_table_writing_assist.py : version consolidee, fusionnant les
patchs 12.1 a 12.6 (patch 12.7 EXCLU) en un seul script.

Implemente "l'aide a l'ecriture d'un tableau" : quand une textbox est
creee ou reouverte a l'interieur d'une case detectee (un rectangle
borde sur au moins 3 de ses 4 cotes par des traits fins et droits),
elle est centree en X et Y, avec adaptation dynamique de la taille de
police (retrecissement si debordement, jusqu'a 6pt minimum ; ragrandi-
ssement vers la taille explicitement choisie par l'utilisateur des que
la place le permet a nouveau) et recentrage dynamique pendant la
frappe. Les fleches directionnelles en bout de texte permettent de
naviguer vers une case adjacente (entrant dans une textbox existante
ou en creant une nouvelle, centree).

Contenu (patchs fusionnes, dans l'ordre) :
  12.1 : detection de case, centrage a la creation, recentrage
         dynamique pendant la frappe
  12.2 : retrecissement/agrandissement automatique de la police
  12.3 : navigation clavier entre cases (fleches directionnelles)
  12.3.2 : correctif de compilation (declaration anticipee manquante)
  12.4 : cote manquant base sur l'extremite de la ligne adjacente
         (au lieu du reflet depuis le point de clic) + marge de 1
         unite pour la verification de debordement
  12.5 : une textbox existante parfaitement centree retrouve le mode
         table a sa reouverture
  12.6 : la cible du rescale a la hausse est la taille explicitement
         choisie par l'utilisateur (Settings::getFont()), pas la
         taille figee a l'ouverture de la session d'edition

Le patch 12.7 (correctif du bug de fusion fantome entre deux tableaux
+ subdivision en emplacements ouverts) N'EST PAS inclus ici, a la
demande explicite de l'utilisateur.

Modifie :
  - src/core/control/tools/TextEditor.h
  - src/core/control/tools/TextEditor.cpp
  - src/core/gui/PageView.h (startText() rendue publique)

Independant de la serie de patchs alignment_snap.

A lancer depuis la racine du depot xournalpp, sur un depot vierge (ou
tout du moins sans qu'aucun des patchs individuels 12.1 a 12.6 n'ait
deja ete applique).
"""
import sys
from pathlib import Path

H_OLD0 = """#include \"model/PageRef.h\"  // for PageRef
#include \"util/Color.h\"     // for Color
#include \"util/Range.h\"
#include \"util/raii/CStringWrapper.h\"
#include \"util/raii/GObjectSPtr.h\"
#include \"util/raii/GSourceURef.h\""""
H_NEW0 = """#include \"model/PageRef.h\"  // for PageRef
#include \"util/Color.h\"     // for Color
#include \"util/Range.h\"
#include \"util/Rectangle.h\"
#include \"util/raii/CStringWrapper.h\"
#include \"util/raii/GObjectSPtr.h\"
#include \"util/raii/GSourceURef.h\""""
H_OLD1 = """    Range computeBoundingBox() const;
    void repaintEditor(bool sizeChanged = true);

    /**
     * @brief Compute the cursor's location
     * @return The bounding box of the cursor, in TextBox coordinates (i.e relative to the text box upper left corner)"""
H_NEW1 = """    Range computeBoundingBox() const;
    void repaintEditor(bool sizeChanged = true);

    /// Patch 12.1: repositions textElement so its (freshly measured) bounding box is centered within
    /// tableCellBounds - a no-op if !tableMode. Called from repaintEditor() whenever the content's
    /// size may have changed.
    void recenterInTableCell();

    /// Patch 12.2: shrinks the font (down to a 6pt floor) if the text currently overflows
    /// tableCellBounds, or grows it back towards tableModeOriginalFontSize if there is room to do so
    /// - a no-op if !tableMode. Called from repaintEditor(), before recenterInTableCell().
    void adjustTableModeFontSize();

    /// Patch 12.3: see the .cpp file for the full explanation - returns true if the current text was
    /// deselected and editing switched to an adjacent table cell (in which case `this` must not be
    /// touched again by the caller).
    bool tryNavigateToAdjacentCell(int dx, int dy);

    /**
     * @brief Compute the cursor's location
     * @return The bounding box of the cursor, in TextBox coordinates (i.e relative to the text box upper left corner)"""
H_OLD2 = """    bool cursorOverwrite = false;
    bool cursorVisible = false;

    // In a blinking period, how much time is the cursor visible vs not visible
    static constexpr unsigned int CURSOR_ON_MULTIPLIER = 2;
    static constexpr unsigned int CURSOR_OFF_MULTIPLIER = 1;"""
H_NEW2 = """    bool cursorOverwrite = false;
    bool cursorVisible = false;

    /**
     * @brief Patch 12.1 (\"table writing assist\"): true if this text was created inside a detected
     * table cell (at least 3 of its 4 sides bounded by thin, straight strokes) - see
     * detectTableCell() in TextEditor.cpp. When true, the text is kept horizontally and vertically
     * centered within tableCellBounds as its content changes (see repaintEditor()).
     */
    bool tableMode = false;
    /// The detected cell's bounding rectangle (document coordinates) - only meaningful if tableMode.
    xoj::util::Rectangle<double> tableCellBounds;
    /// The font size textElement had right when tableMode was determined (i.e. before any automatic
    /// shrinking) - used by the (future) dynamic shrink/grow-back logic, patch 12.2.
    double tableModeOriginalFontSize = 0;

    // In a blinking period, how much time is the cursor visible vs not visible
    static constexpr unsigned int CURSOR_ON_MULTIPLIER = 2;
    static constexpr unsigned int CURSOR_OFF_MULTIPLIER = 1;"""
CPP_OLD0 = """#include \"TextEditor.h\"

#include <cstring>  // for strcmp, size_t
#include <memory>   // for allocator, make_unique, __shared_p...
#include <string>   // for std::string()
#include <utility>  // for move
"""
CPP_NEW0 = """#include \"TextEditor.h\"

#include <algorithm>  // for max, min
#include <cmath>      // for abs
#include <cstring>  // for strcmp, size_t
#include <limits>   // for numeric_limits
#include <memory>   // for allocator, make_unique, __shared_p...
#include <optional> // for optional
#include <string>   // for std::string()
#include <utility>  // for move
"""
CPP_OLD1 = """#include \"control/AudioController.h\"
#include \"control/Control.h\"  // for Control
#include \"control/settings/Settings.h\"
#include \"gui/XournalppCursor.h\"  // for XournalppCursor
#include \"model/Document.h\"       // for Document
#include \"model/Font.h\"           // for XojFont
#include \"model/Text.h\"           // for Text
#include \"model/XojPage.h\"        // for XojPage
#include \"undo/DeleteUndoAction.h\""""
CPP_NEW1 = """#include \"control/AudioController.h\"
#include \"control/Control.h\"  // for Control
#include \"control/settings/Settings.h\"
#include \"gui/MainWindow.h\"       // for MainWindow
#include \"gui/PageView.h\"         // for XojPageView
#include \"gui/XournalView.h\"      // for XournalView
#include \"gui/XournalppCursor.h\"  // for XournalppCursor
#include \"model/Document.h\"       // for Document
#include \"model/Element.h\"        // for Element
#include \"model/Font.h\"           // for XojFont
#include \"model/Layer.h\"          // for Layer
#include \"model/Stroke.h\"         // for Stroke, ArrowKind
#include \"model/Text.h\"           // for Text
#include \"model/XojPage.h\"        // for XojPage
#include \"undo/DeleteUndoAction.h\""""
CPP_OLD2 = """    this->repaintEditor(false);
}

void TextEditor::moveCursor(GtkMovementStep step, int count, bool extendSelection) {
    resetImContext();
"""
CPP_NEW2 = """    this->repaintEditor(false);
}

// Patch 12.3.2: forward declaration - detectTableCell() itself is defined much further down in this
// file (right before initializeEditionAt(), patch 12.1), but tryNavigateToAdjacentCell() (patch 12.3)
// needs to call it well before that point.
static auto detectTableCell(double x, double y, Layer* layer) -> std::optional<xoj::util::Rectangle<double>>;

/**
 * Patch 12.3 (\"table writing assist\"): called only when a tableMode text's cursor just failed to
 * move any further in direction (dx, dy) (dx/dy each in {-1, 0, 1}, exactly one of them non-zero) -
 * i.e. one of the four boundary conditions described by the feature request. Looks for a table cell
 * adjacent to the current one in that direction; if found, either enters the Text element already
 * there (cursor moved to the end of its text) or creates a new, empty, centered Text in it if it's
 * empty - deselecting the current text either way. Returns true if a switch happened, in which case
 * the caller MUST return immediately afterwards without touching `this` again: `this` (along with
 * everything it owns) has very likely just been destroyed, since XojPageView::startText() below ends
 * the current text editing internally before starting the new one, which resets the very unique_ptr
 * that owns it.
 */
bool TextEditor::tryNavigateToAdjacentCell(int dx, int dy) {
    if (!this->tableMode) {
        return false;
    }
    constexpr double SEARCH_EPS = 1.0;  // small nudge past the current cell's edge, into the neighbor
    double searchX = this->tableCellBounds.x + this->tableCellBounds.width / 2.0;
    double searchY = this->tableCellBounds.y + this->tableCellBounds.height / 2.0;
    if (dx < 0) {
        searchX = this->tableCellBounds.x - SEARCH_EPS;
    } else if (dx > 0) {
        searchX = this->tableCellBounds.x + this->tableCellBounds.width + SEARCH_EPS;
    }
    if (dy < 0) {
        searchY = this->tableCellBounds.y - SEARCH_EPS;
    } else if (dy > 0) {
        searchY = this->tableCellBounds.y + this->tableCellBounds.height + SEARCH_EPS;
    }

    Layer* layer = this->page->getSelectedLayer();
    auto cell = detectTableCell(searchX, searchY, layer);
    if (!cell) {
        return false;
    }

    double cellCenterX = cell->x + cell->width / 2.0;
    double cellCenterY = cell->y + cell->height / 2.0;

    // Is there already a Text element inside this neighboring cell?
    bool enteringExisting = false;
    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (el->getType() != ELEMENT_TEXT) {
            continue;
        }
        GdkRectangle matchRect = {gint(cellCenterX), gint(cellCenterY), 1, 1};
        if (el->intersectsArea(&matchRect)) {
            enteringExisting = true;
            break;
        }
    }

    // TextEditor doesn't manage its own lifetime - the owning XojPageView does. Find it via the
    // document's page index (this->page is a PageRef, not the index itself).
    size_t pageIndex = this->control->getDocument()->indexOf(this->page);
    XojPageView* pageView = this->control->getWindow()->getXournal()->getViewFor(pageIndex);
    if (pageView == nullptr) {
        return false;
    }

    // From this point on, `this` must NEVER be touched again: XojPageView::startText() below ends
    // the current text editing internally (since the target cell's center cannot intersect the
    // current text's own bounds) before starting the new one - which destroys the very TextEditor
    // that is executing this method.
    pageView->startText(cellCenterX, cellCenterY);
    if (enteringExisting) {
        if (TextEditor* newEditor = pageView->getTextEditor()) {
            newEditor->moveCursor(GTK_MOVEMENT_BUFFER_ENDS, 1, false);
        }
    }
    return true;
}

void TextEditor::moveCursor(GtkMovementStep step, int count, bool extendSelection) {
    resetImContext();
"""
CPP_OLD3 = """    }

    if (gtk_text_iter_equal(&insert, &newplace)) {
        gtk_widget_error_bell(this->xournalWidget);
    }
}"""
CPP_NEW3 = """    }

    if (gtk_text_iter_equal(&insert, &newplace)) {
        // Patch 12.3 (\"table writing assist\"): the cursor failed to move any further - exactly the
        // \"no more room\" condition the feature is about. Only plain arrow-key movements (a single
        // character left/right, or one display line up/down) count - not e.g. Ctrl+Arrow (word
        // movement) or Home/End, which use different `step` values and so never reach here.
        if (this->tableMode) {
            int dx = 0;
            int dy = 0;
            if (step == GTK_MOVEMENT_VISUAL_POSITIONS) {
                dx = (count < 0) ? -1 : 1;
            } else if (step == GTK_MOVEMENT_DISPLAY_LINES) {
                dy = (count < 0) ? -1 : 1;
            }
            if ((dx != 0 || dy != 0) && this->tryNavigateToAdjacentCell(dx, dy)) {
                // `this` may have just been destroyed (see tryNavigateToAdjacentCell's own comment) -
                // return immediately, without touching any member or calling anything else below.
                return;
            }
        }
        gtk_widget_error_bell(this->xournalWidget);
    }
}"""
CPP_OLD4 = """    return res;
}

void TextEditor::repaintEditor(bool sizeChanged) {
    Range dirtyRange(this->previousBoundingBox);
    if (sizeChanged) {
        this->previousBoundingBox = this->computeBoundingBox();
        dirtyRange = dirtyRange.unite(this->previousBoundingBox);
    }
    this->updateCursorBox();
    this->viewPool->dispatch(xoj::view::TextEditionView::FLAG_DIRTY_REGION, dirtyRange);"""
CPP_NEW4 = """    return res;
}

void TextEditor::recenterInTableCell() {
    if (!this->tableMode) {
        return;
    }
    Range box = this->computeBoundingBox();
    double width = box.maxX - box.minX;
    double height = box.maxY - box.minY;
    this->textElement->setX(this->tableCellBounds.x + (this->tableCellBounds.width - width) / 2.0);
    this->textElement->setY(this->tableCellBounds.y + (this->tableCellBounds.height - height) / 2.0);
}

void TextEditor::adjustTableModeFontSize() {
    if (!this->tableMode) {
        return;
    }
    // Patch 12.2: linear search, in small steps, for the font size that best fits the cell right now
    // - shrinking if the text currently overflows (down to MIN_TABLE_MODE_FONT_SIZE), or growing back
    // towards the target size otherwise (patch 12.6 - see below for what that target is), as far as
    // it fits. A linear (not binary) search was chosen deliberately: at typical table font sizes,
    // only a handful of steps are ever needed, so the simplicity is worth more here than the
    // (negligible) performance difference.
    constexpr double FONT_SIZE_STEP = 0.5;
    constexpr double MIN_TABLE_MODE_FONT_SIZE = 6.0;

    auto measure = [this]() -> std::pair<double, double> {
        Range box = this->computeBoundingBox();
        return {box.maxX - box.minX, box.maxY - box.minY};
    };
    auto overflows = [this](double w, double h) {
        // Patch 12.4: text must never touch the cell's own border lines - kept at least MARGIN away
        // from each of them. Centering (recenterInTableCell()) is unaffected and still uses the full
        // cell.
        constexpr double MARGIN = 1.0;
        return w > this->tableCellBounds.width - 2 * MARGIN || h > this->tableCellBounds.height - 2 * MARGIN;
    };
    // Patch 12.6: the grow-back target is the font size as explicitly chosen by the user
    // (Settings::getFont()), queried live - NOT tableModeOriginalFontSize (the size this text
    // happened to have when this editing session started). Settings::getFont() is only ever updated
    // by Control::fontChanged(), which fires exclusively on a genuine user interaction with the font
    // picker - unlike Control::setFontSelected(), which merely updates the picker's displayed value
    // (e.g. every time a text is opened for editing) without touching Settings at all. Using the
    // picker's raw displayed value here would have been circular, since opening this very table-mode
    // text is itself one of the things that overwrites what the picker displays.
    double targetSize = this->control->getSettings()->getFont().getSize();

    auto setSize = [this](double size) {
        this->textElement->getFont().setSize(size);
        this->textElement->updatePangoFont(this->layout.get());
    };

    double currentSize = this->textElement->getFontSize();
    auto [w, h] = measure();

    if (overflows(w, h)) {
        while (currentSize > MIN_TABLE_MODE_FONT_SIZE && overflows(w, h)) {
            currentSize = std::max(MIN_TABLE_MODE_FONT_SIZE, currentSize - FONT_SIZE_STEP);
            setSize(currentSize);
            std::tie(w, h) = measure();
        }
    } else if (currentSize < targetSize) {
        while (currentSize < targetSize) {
            double nextSize = std::min(targetSize, currentSize + FONT_SIZE_STEP);
            setSize(nextSize);
            auto [nw, nh] = measure();
            if (overflows(nw, nh)) {
                setSize(currentSize);  // revert - nextSize doesn't fit
                break;
            }
            currentSize = nextSize;
            w = nw;
            h = nh;
        }
    }
}

void TextEditor::repaintEditor(bool sizeChanged) {
    Range dirtyRange(this->previousBoundingBox);
    if (sizeChanged) {
        this->previousBoundingBox = this->computeBoundingBox();
        dirtyRange = dirtyRange.unite(this->previousBoundingBox);

        // Patch 12.1 (\"table writing assist\"): keep the text centered within its detected table cell
        // as its content (and therefore its size) changes. Patch 12.2: before recentering, first
        // shrink the font if the text now overflows the cell (down to a 6pt floor), or grow it back
        // towards its original size if there is now room to do so. Repositioning/resizing changes the
        // bounding box again, so it must be recomputed once more for the dirty-region tracking to stay
        // correct.
        if (this->tableMode) {
            this->adjustTableModeFontSize();
            this->recenterInTableCell();
            this->previousBoundingBox = this->computeBoundingBox();
            dirtyRange = dirtyRange.unite(this->previousBoundingBox);
        }
    }
    this->updateCursorBox();
    this->viewPool->dispatch(xoj::view::TextEditionView::FLAG_DIRTY_REGION, dirtyRange);"""
CPP_OLD5 = """    }
}

void TextEditor::initializeEditionAt(double x, double y) {
    // Is there already a textfield?
    Text* text = nullptr;"""
CPP_NEW5 = """    }
}

/**
 * Patch 12.1 (\"table writing assist\") - geometric threshold below which a stroke's bounding box side
 * counts as \"thin\" (i.e. it's effectively a straight line, not a genuine 2D shape). Independently
 * reimplemented here from scratch for this feature - deliberately NOT shared with or dependent on the
 * (separate) alignment_snap patch series, which has its own equivalent, user-configurable constant.
 */
constexpr double TABLE_THIN_AXIS_THRESHOLD = 3.0;

/**
 * Looks for a \"table cell\" containing the point (x, y): a rectangle bounded, on at least 3 of its 4
 * sides (left/right/top/bottom), by the nearest thin, straight strokes whose own extent actually
 * spans across the point on the perpendicular axis (so a line elsewhere on the page, not really
 * forming a wall at this position, is not mistaken for one). If exactly one side has no such
 * bounding stroke (e.g. the open bottom of the last row of a table), that side is mirrored from its
 * opposite side, so the returned cell is always a well-defined rectangle centered on (x, y) along
 * that axis. Returns std::nullopt if fewer than 3 sides are found.
 */
static auto detectTableCell(double x, double y, Layer* layer) -> std::optional<xoj::util::Rectangle<double>> {
    double leftX = -std::numeric_limits<double>::infinity();
    double rightX = std::numeric_limits<double>::infinity();
    double topY = -std::numeric_limits<double>::infinity();
    double bottomY = std::numeric_limits<double>::infinity();
    bool hasLeft = false;
    bool hasRight = false;
    bool hasTop = false;
    bool hasBottom = false;
    // Patch 12.4: the full shaft of each found boundary line is kept around (not just its centerline
    // coordinate), so that if a 4th side is missing, its own endpoint can be used to close off the
    // cell - see below.
    xoj::util::Rectangle<double> leftLine;
    xoj::util::Rectangle<double> rightLine;
    xoj::util::Rectangle<double> topLine;
    xoj::util::Rectangle<double> bottomLine;

    for (auto& elPtr: layer->getElements()) {
        Element* el = elPtr.get();
        if (dynamic_cast<const Stroke*>(el) == nullptr) {
            continue;
        }
        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
        bool isVertical = shaft.width <= TABLE_THIN_AXIS_THRESHOLD && shaft.height > TABLE_THIN_AXIS_THRESHOLD;
        bool isHorizontal = shaft.height <= TABLE_THIN_AXIS_THRESHOLD && shaft.width > TABLE_THIN_AXIS_THRESHOLD;
        if (isVertical && shaft.y <= y && y <= shaft.y + shaft.height) {
            double lineX = shaft.x + shaft.width / 2.0;
            if (lineX <= x && lineX > leftX) {
                leftX = lineX;
                hasLeft = true;
                leftLine = shaft;
            } else if (lineX > x && lineX < rightX) {
                rightX = lineX;
                hasRight = true;
                rightLine = shaft;
            }
        } else if (isHorizontal && shaft.x <= x && x <= shaft.x + shaft.width) {
            double lineY = shaft.y + shaft.height / 2.0;
            if (lineY <= y && lineY > topY) {
                topY = lineY;
                hasTop = true;
                topLine = shaft;
            } else if (lineY > y && lineY < bottomY) {
                bottomY = lineY;
                hasBottom = true;
                bottomLine = shaft;
            }
        }
    }

    int foundCount = (hasLeft ? 1 : 0) + (hasRight ? 1 : 0) + (hasTop ? 1 : 0) + (hasBottom ? 1 : 0);
    if (foundCount < 3) {
        return std::nullopt;
    }

    // Patch 12.4: a missing side is no longer mirrored from the click point - it is instead closed
    // off by the matching endpoint of whichever adjacent perpendicular line was found (top preferred,
    // then bottom, for a missing left/right side; left preferred, then right, for a missing top/
    // bottom side) - i.e. the actual extremity of that line's own shaft, not a point derived from
    // (x, y).
    if (!hasLeft) {
        leftX = hasTop ? topLine.x : bottomLine.x;
    }
    if (!hasRight) {
        rightX = hasTop ? (topLine.x + topLine.width) : (bottomLine.x + bottomLine.width);
    }
    if (!hasTop) {
        topY = hasLeft ? leftLine.y : rightLine.y;
    }
    if (!hasBottom) {
        bottomY = hasLeft ? (leftLine.y + leftLine.height) : (rightLine.y + rightLine.height);
    }

    return xoj::util::Rectangle<double>(leftX, topY, rightX - leftX, bottomY - topY);
}

void TextEditor::initializeEditionAt(double x, double y) {
    // Is there already a textfield?
    Text* text = nullptr;"""
CPP_OLD6 = """        this->textElement = std::make_unique<Text>();
        this->textElement->setColor(h->getColor());
        this->textElement->setFont(control->getSettings()->getFont());
        this->textElement->setX(x);
        this->textElement->setY(y - this->textElement->getElementHeight() / 2);

#ifdef ENABLE_AUDIO
        if (auto audioController = control->getAudioController(); audioController && audioController->isRecording()) {"""
CPP_NEW6 = """        this->textElement = std::make_unique<Text>();
        this->textElement->setColor(h->getColor());
        this->textElement->setFont(control->getSettings()->getFont());

        // Patch 12.1 (\"table writing assist\"): if (x, y) falls inside a detected table cell, center
        // the new (still empty) text within it instead of the usual \"top-left at the click point\"
        // placement, and remember the cell + the font size at creation time for later (patch 12.1's
        // own dynamic recentering in repaintEditor(), and the future dynamic shrink/grow-back of
        // patch 12.2).
        if (auto cell = detectTableCell(x, y, this->page->getSelectedLayer())) {
            this->tableMode = true;
            this->tableCellBounds = *cell;
            this->tableModeOriginalFontSize = this->textElement->getFontSize();
            double width = this->textElement->getElementWidth();
            double height = this->textElement->getElementHeight();
            this->textElement->setX(this->tableCellBounds.x + (this->tableCellBounds.width - width) / 2.0);
            this->textElement->setY(this->tableCellBounds.y + (this->tableCellBounds.height - height) / 2.0);
        } else {
            this->tableMode = false;
            this->textElement->setX(x);
            this->textElement->setY(y - this->textElement->getElementHeight() / 2);
        }

#ifdef ENABLE_AUDIO
        if (auto audioController = control->getAudioController(); audioController && audioController->isRecording()) {"""
CPP_OLD7 = """
        text->setInEditing(true);
        this->page->fireElementChanged(text);
    }
    this->layout = this->textElement->createPangoLayout();
    this->previousBoundingBox = Range(this->textElement->boundingRect());"""
CPP_NEW7 = """
        text->setInEditing(true);
        this->page->fireElementChanged(text);

        // Patch 12.5 (\"table writing assist\"): if this existing text happens to already be PERFECTLY
        // centered within a detected table cell, re-enter \"table mode\" for it too, restoring the
        // dynamic font-size adaptation and centering (patches 12.1/12.2) as if it had just been
        // created there - rather than only ever granting these behaviors to brand new texts.
        double textCenterX = this->textElement->getX() + this->textElement->getElementWidth() / 2.0;
        double textCenterY = this->textElement->getY() + this->textElement->getElementHeight() / 2.0;
        if (auto cell = detectTableCell(textCenterX, textCenterY, this->page->getSelectedLayer())) {
            constexpr double CENTER_EPS = 0.5;
            double expectedX = cell->x + (cell->width - this->textElement->getElementWidth()) / 2.0;
            double expectedY = cell->y + (cell->height - this->textElement->getElementHeight()) / 2.0;
            if (std::abs(this->textElement->getX() - expectedX) < CENTER_EPS &&
                std::abs(this->textElement->getY() - expectedY) < CENTER_EPS) {
                this->tableMode = true;
                this->tableCellBounds = *cell;
                this->tableModeOriginalFontSize = this->textElement->getFontSize();
            }
        }
    }
    this->layout = this->textElement->createPangoLayout();
    this->previousBoundingBox = Range(this->textElement->boundingRect());"""
PV_OLD0 = """
    void endText();

    void endLink();

    void endSpline();"""
PV_NEW0 = """
    void endText();

    /// Patch 12.3 (\"table writing assist\"): made public (was private, alongside startLink() and
    /// drawLoadingPage() further down) so TextEditor::tryNavigateToAdjacentCell() can start editing a
    /// new position directly, without needing XojPageView to be a friend or exposing anything else
    /// from that private section.
    void startText(double x, double y);

    void endLink();

    void endSpline();"""
PV_OLD1 = """    void elementsChanged(const std::vector<const Element*>& elements, const Range& range) override;

private:
    void startText(double x, double y);

    void startLink();

    void drawLoadingPage(cairo_t* cr);"""
PV_NEW1 = """    void elementsChanged(const std::vector<const Element*>& elements, const Range& range) override;

private:
    void startLink();

    void drawLoadingPage(cairo_t* cr);"""


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
    h_file = Path("src/core/control/tools/TextEditor.h")
    cpp_file = Path("src/core/control/tools/TextEditor.cpp")
    pv_file = Path("src/core/gui/PageView.h")
    for p in (h_file, cpp_file, pv_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "tableMode" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Ce patch (apply_table_writing_assist) semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H_OLD0, H_NEW0, "h: zone 1/3")
    ok &= apply_edit(h_file, H_OLD1, H_NEW1, "h: zone 2/3")
    ok &= apply_edit(h_file, H_OLD2, H_NEW2, "h: zone 3/3")
    ok &= apply_edit(cpp_file, CPP_OLD0, CPP_NEW0, "cpp: zone 1/8")
    ok &= apply_edit(cpp_file, CPP_OLD1, CPP_NEW1, "cpp: zone 2/8")
    ok &= apply_edit(cpp_file, CPP_OLD2, CPP_NEW2, "cpp: zone 3/8")
    ok &= apply_edit(cpp_file, CPP_OLD3, CPP_NEW3, "cpp: zone 4/8")
    ok &= apply_edit(cpp_file, CPP_OLD4, CPP_NEW4, "cpp: zone 5/8")
    ok &= apply_edit(cpp_file, CPP_OLD5, CPP_NEW5, "cpp: zone 6/8")
    ok &= apply_edit(cpp_file, CPP_OLD6, CPP_NEW6, "cpp: zone 7/8")
    ok &= apply_edit(cpp_file, CPP_OLD7, CPP_NEW7, "cpp: zone 8/8")
    ok &= apply_edit(pv_file, PV_OLD0, PV_NEW0, "pv: zone 1/2")
    ok &= apply_edit(pv_file, PV_OLD1, PV_NEW1, "pv: zone 2/2")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
