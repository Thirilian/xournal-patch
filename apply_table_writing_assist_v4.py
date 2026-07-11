#!/usr/bin/env python3
"""
table_writing_assist_v4.py : version consolidee, fusionnant
table_writing_assist_v3.py (patchs 12.1 a 12.11) avec le correctif
12.12 en un seul script.

Implemente "l'aide a l'ecriture d'un tableau" : quand une textbox est
creee ou reouverte a l'interieur d'une case detectee, elle est
centree en X et Y, avec adaptation dynamique de la taille de police
et recentrage dynamique pendant la frappe. Les fleches directionnelles
en bout de texte permettent de naviguer vers une case adjacente.

Nouveau dans cette version (patch 12.12, par rapport a v3) :
CORRECTIF - la reconnaissance de "tableau vertical" (colonnes
multiples avec une seule ligne d'en-tete horizontale pres du haut,
patch 12.11) prenait a tort le pas sur la reconnaissance de tableau
classique des que la premiere rangee d'un tableau normal se trouvait
pres du haut des verticales. Un tableau vertical n'a, par definition,
qu'UNE SEULE ligne horizontale qui traverse ses lignes verticales - une
verification supplementaire s'assure desormais qu'aucune autre ligne
horizontale ne traverse les memes verticales avant d'appliquer cette
regle speciale, sinon la detection classique prend le relais.

Modifie :
  - src/core/control/tools/TextEditor.h
  - src/core/control/tools/TextEditor.cpp
  - src/core/gui/PageView.h (startText() rendue publique)

Independant des series alignment_snap et completion LaTeX.

A lancer depuis la racine du depot xournalpp, sur un depot vierge (ou
tout du moins sans qu'aucun patch individuel de cette serie n'ait deja
ete applique).
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

#include <gdk/gdkkeysyms.h>  // for GDK_KEY_B, GDK_KEY_ISO_Enter, GDK_...
#include <glib-object.h>     // for g_object_get, g_object_unref, G_CA..."""
CPP_NEW0 = """#include \"TextEditor.h\"

#include <algorithm>  // for max, min
#include <cmath>      // for abs
#include <cstring>  // for strcmp, size_t
#include <limits>   // for numeric_limits
#include <memory>   // for allocator, make_unique, __shared_p...
#include <optional> // for optional
#include <string>   // for std::string()
#include <utility>  // for move
#include <vector>   // for vector

#include <gdk/gdkkeysyms.h>  // for GDK_KEY_B, GDK_KEY_ISO_Enter, GDK_...
#include <glib-object.h>     // for g_object_get, g_object_unref, G_CA..."""
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
static auto detectTableCell(double x, double y, Layer* layer, double fontSize,
                             const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<xoj::util::Rectangle<double>>;

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
    size_t pageIndex = this->control->getDocument()->indexOf(this->page);
    xoj::util::Rectangle<double>* visibleRectPtr =
            this->control->getWindow()->getXournal()->getVisibleRect(pageIndex);
    if (visibleRectPtr == nullptr) {
        return false;
    }
    xoj::util::Rectangle<double> visibleRect = *visibleRectPtr;
    delete visibleRectPtr;
    auto cell = detectTableCell(searchX, searchY, layer, this->control->getSettings()->getFont().getSize(),
                                 visibleRect);
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
    // document's page index (this->page is a PageRef, not the index itself) - already computed above.
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
static auto detectTableCell(double x, double y, Layer* layer, double fontSize,
                             const xoj::util::Rectangle<double>& visibleRect)
        -> std::optional<xoj::util::Rectangle<double>> {
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
        // Patch 12.8: only consider strokes currently visible to the user, not every stroke on the
        // whole page - both for performance on large pages, and because a stroke scrolled far off
        // screen shouldn't silently participate in a cell the user can't even see.
        if (!el->intersectsArea(visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
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

    // Patch 12.11: special case - 3+ vertical lines all crossed by ONE shared horizontal line
    // positioned close to their own top extremity (within 25% of the verticals' own length) - see the
    // feature request's screenshots. Rather than treating this as an ordinary 3/4-sided cell, or
    // falling back to the font-size-based slot subdivision (patch 12.7/12.10), the header horizontal
    // line's own distance from the verticals' own top defines a repeating \"row height\" that tiles
    // seamlessly downward (no gap, unlike patch 12.7's font-based slots) as far as the verticals' own
    // extent allows. This is NOT a general, reversible rule - it only ever applies to this exact
    // configuration (multiple verticals, one crossing horizontal near their top), never to a
    // rotated/mirrored equivalent (multiple horizontals, one crossing vertical near an edge).
    //
    // Patch 12.12: CORRECTIF - a \"vertical table\" is, by definition, crossed by EXACTLY ONE
    // horizontal line - never more. The rule below used to trigger as soon as topLine alone crossed
    // 3+ verticals near their top, with no check for any OTHER horizontal line crossing those same
    // verticals elsewhere - meaning a genuine classic multi-row table (patch 12.4/12.9/12.10) whose
    // top row simply happened to sit close to the verticals' own top was wrongly hijacked by this
    // special case. A second pass now looks for any other horizontal line crossing any of the same
    // verticals; if one is found, this whole special case is skipped, falling through to the classic
    // detection below instead.
    if (hasLeft && hasRight && hasTop) {
        std::vector<xoj::util::Rectangle<double>> crossedVerticals;
        for (auto& elPtr: layer->getElements()) {
            Element* el = elPtr.get();
            if (dynamic_cast<const Stroke*>(el) == nullptr) {
                continue;
            }
            if (!el->intersectsArea(visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isVertical = shaft.width <= TABLE_THIN_AXIS_THRESHOLD && shaft.height > TABLE_THIN_AXIS_THRESHOLD;
            double lineX = shaft.x + shaft.width / 2.0;
            if (isVertical && shaft.y <= topY && topY <= shaft.y + shaft.height && lineX >= topLine.x &&
                lineX <= topLine.x + topLine.width) {
                crossedVerticals.push_back(shaft);
            }
        }

        bool hasOtherHorizontalCrossing = false;
        for (auto& elPtr: layer->getElements()) {
            Element* el = elPtr.get();
            if (dynamic_cast<const Stroke*>(el) == nullptr) {
                continue;
            }
            if (!el->intersectsArea(visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isHorizontal = shaft.height <= TABLE_THIN_AXIS_THRESHOLD && shaft.width > TABLE_THIN_AXIS_THRESHOLD;
            if (!isHorizontal) {
                continue;
            }
            if (shaft.x == topLine.x && shaft.y == topLine.y && shaft.width == topLine.width &&
                shaft.height == topLine.height) {
                continue;  // this IS topLine itself, encountered again while scanning the layer
            }
            double lineY = shaft.y + shaft.height / 2.0;
            for (const auto& v: crossedVerticals) {
                double vX = v.x + v.width / 2.0;
                if (v.y <= lineY && lineY <= v.y + v.height && vX >= shaft.x && vX <= shaft.x + shaft.width) {
                    hasOtherHorizontalCrossing = true;
                    break;
                }
            }
            if (hasOtherHorizontalCrossing) {
                break;
            }
        }

        double verticalTop = std::min(leftLine.y, rightLine.y);
        double verticalBottom = std::min(leftLine.y + leftLine.height, rightLine.y + rightLine.height);
        double verticalsLength = std::min(leftLine.height, rightLine.height);
        double rowHeight = topY - verticalTop;
        if (!hasOtherHorizontalCrossing && crossedVerticals.size() >= 3 && rowHeight > 0 &&
            rowHeight <= 0.25 * verticalsLength) {
            double rowTop;
            double rowBottom;
            if (y < topY) {
                // Clicked within the header row itself, above the horizontal line.
                rowTop = verticalTop;
                rowBottom = topY;
            } else {
                int rowIndex = static_cast<int>(std::floor((y - topY) / rowHeight));
                rowIndex = std::max(0, rowIndex);
                rowTop = topY + rowIndex * rowHeight;
                rowBottom = rowTop + rowHeight;
            }
            if (rowBottom <= verticalBottom) {
                return xoj::util::Rectangle<double>(leftX, rowTop, rightX - leftX, rowBottom - rowTop);
            }
            // else: no room for a row here - fall through to the classic detection below.
        }
    }

    int foundCount = (hasLeft ? 1 : 0) + (hasRight ? 1 : 0) + (hasTop ? 1 : 0) + (hasBottom ? 1 : 0);
    if (foundCount < 3) {
        return std::nullopt;
    }

    // Patch 12.9: a found boundary that doesn't genuinely connect to ANY of its adjacent found
    // perpendicular boundaries (left-top, left-bottom, right-top, right-bottom - never left-right or
    // top-bottom, which are parallel) is no longer treated as rejecting the whole cell outright
    // (patch 12.8's stricter-but-too-blunt behavior). Instead, that ONE offending boundary alone is
    // dropped (as if it had never been found) - a genuinely 3-sided cell whose open side happens to
    // coincidentally line up with some distant, unrelated stroke elsewhere on the page (or just
    // visible on screen) would otherwise have been rejected entirely, when it should simply fall
    // through to the missing-side handling right below, exactly as if that distant stroke didn't
    // exist at all.
    auto rectanglesIntersect = [](const xoj::util::Rectangle<double>& a, const xoj::util::Rectangle<double>& b) {
        return a.x <= b.x + b.width && a.x + a.width >= b.x && a.y <= b.y + b.height && a.y + a.height >= b.y;
    };
    bool leftConnects = !hasLeft || (hasTop && rectanglesIntersect(leftLine, topLine)) ||
                        (hasBottom && rectanglesIntersect(leftLine, bottomLine)) || (!hasTop && !hasBottom);
    bool rightConnects = !hasRight || (hasTop && rectanglesIntersect(rightLine, topLine)) ||
                         (hasBottom && rectanglesIntersect(rightLine, bottomLine)) || (!hasTop && !hasBottom);
    bool topConnects = !hasTop || (hasLeft && rectanglesIntersect(topLine, leftLine)) ||
                       (hasRight && rectanglesIntersect(topLine, rightLine)) || (!hasLeft && !hasRight);
    bool bottomConnects = !hasBottom || (hasLeft && rectanglesIntersect(bottomLine, leftLine)) ||
                          (hasRight && rectanglesIntersect(bottomLine, rightLine)) || (!hasLeft && !hasRight);
    if (!leftConnects) {
        hasLeft = false;
    }
    if (!rightConnects) {
        hasRight = false;
    }
    if (!topConnects) {
        hasTop = false;
    }
    if (!bottomConnects) {
        hasBottom = false;
    }

    foundCount = (hasLeft ? 1 : 0) + (hasRight ? 1 : 0) + (hasTop ? 1 : 0) + (hasBottom ? 1 : 0);
    if (foundCount < 3) {
        return std::nullopt;
    }

    // Patch 12.7: a column bounded on the left, right and top, but left entirely open at the bottom
    // (no row structure at all below the header line - see the feature request's second example) is
    // subdivided into repeated vertical \"slots\" instead of forming one giant cell spanning the whole
    // column: each slot is fontSize tall, with a SLOT_GAP gap before the next one starts, both
    // measured from just below the top line - and (x, y) determines which slot is being targeted.
    // Slots stop being offered once they would extend past the bounding verticals' own bottom
    // extremity.
    //
    // Patch 12.10: subdivision only kicks in if there is room for AT LEAST TWO slots (i.e. a single
    // slot plus one full gap plus a second slot) - a single slot's worth of height (or less) doesn't
    // meaningfully subdivide anything, so it falls through to the classic 3-sided rule below (patch
    // 12.4 / rule 5) instead, treating the whole open column as one ordinary cell closed off by the
    // bounding verticals' own bottom extremity.
    if (hasLeft && hasRight && hasTop && !hasBottom) {
        constexpr double SLOT_GAP = 10.0;
        double columnBottomLimit = std::min(leftLine.y + leftLine.height, rightLine.y + rightLine.height);
        double availableHeight = columnBottomLimit - topY;
        double minHeightForTwoSlots = 2 * fontSize + SLOT_GAP;
        if (availableHeight >= minHeightForTwoSlots) {
            double slotPeriod = fontSize + SLOT_GAP;
            int slotIndex = static_cast<int>(std::floor((y - topY) / slotPeriod));
            slotIndex = std::max(0, slotIndex);
            double slotTop = topY + slotIndex * slotPeriod;
            double slotBottom = slotTop + fontSize;
            if (slotBottom > columnBottomLimit) {
                return std::nullopt;
            }
            return xoj::util::Rectangle<double>(leftX, slotTop, rightX - leftX, slotBottom - slotTop);
        }
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
        std::optional<xoj::util::Rectangle<double>> cell;
        {
            size_t pageIndexForCell = this->control->getDocument()->indexOf(this->page);
            xoj::util::Rectangle<double>* visibleRectPtr =
                    this->control->getWindow()->getXournal()->getVisibleRect(pageIndexForCell);
            if (visibleRectPtr != nullptr) {
                cell = detectTableCell(x, y, this->page->getSelectedLayer(),
                                        this->control->getSettings()->getFont().getSize(), *visibleRectPtr);
                delete visibleRectPtr;
            }
        }
        if (cell) {
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
        std::optional<xoj::util::Rectangle<double>> cell;
        {
            size_t pageIndexForCell = this->control->getDocument()->indexOf(this->page);
            xoj::util::Rectangle<double>* visibleRectPtr =
                    this->control->getWindow()->getXournal()->getVisibleRect(pageIndexForCell);
            if (visibleRectPtr != nullptr) {
                cell = detectTableCell(textCenterX, textCenterY, this->page->getSelectedLayer(),
                                        this->control->getSettings()->getFont().getSize(), *visibleRectPtr);
                delete visibleRectPtr;
            }
        }
        if (cell) {
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
        print("[SKIP] Ce patch (table_writing_assist_v4) semble deja applique.")
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
