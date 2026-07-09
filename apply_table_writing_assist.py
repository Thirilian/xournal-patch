#!/usr/bin/env python3
"""
Patch 12.1 ("aide a l'ecriture d'un tableau") : quand une textbox est
creee (double-clic/clic avec l'outil texte) a l'interieur d'une "case"
detectee - un rectangle borde sur au moins 3 de ses 4 cotes
(gauche/droite/haut/bas) par des traits fins et droits dont l'etendue
propre traverse reellement le point de clic sur l'axe perpendiculaire
(le 4e cote, s'il manque, est reflete depuis le cote oppose) - la
textbox est centree en X et en Y par rapport a cette case, et la taille
de police au moment de la creation est memorisee pour un usage futur
(patch 12.2). Pendant la frappe, la textbox est recentree
dynamiquement a chaque changement de contenu.

Detection de case reimplementee independamment ici (pas de dependance
avec la serie de patchs alignment_snap, qui a son propre mecanisme
equivalent et configurable).

Prochaines etapes prevues (patchs separes) :
  - 12.2 : retrecissement/agrandissement automatique de la police selon
    le debordement (minimum 6pt).
  - 12.3 : navigation clavier entre cases.

Modifie :
  - src/core/control/tools/TextEditor.h (nouveaux membres tableMode,
    tableCellBounds, tableModeOriginalFontSize ; nouvelle methode
    recenterInTableCell())
  - src/core/control/tools/TextEditor.cpp (detectTableCell(), cablage
    dans initializeEditionAt() et repaintEditor())

Independant de la serie de patchs alignment_snap.

A lancer depuis la racine du depot xournalpp (sur un depot vierge).
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

#include <cstring>  // for strcmp, size_t
#include <limits>   // for numeric_limits
#include <memory>   // for allocator, make_unique, __shared_p...
#include <optional> // for optional
#include <string>   // for std::string()
#include <utility>  // for move
"""
CPP_OLD1 = """#include \"control/settings/Settings.h\"
#include \"gui/XournalppCursor.h\"  // for XournalppCursor
#include \"model/Document.h\"       // for Document
#include \"model/Font.h\"           // for XojFont
#include \"model/Text.h\"           // for Text
#include \"model/XojPage.h\"        // for XojPage
#include \"undo/DeleteUndoAction.h\""""
CPP_NEW1 = """#include \"control/settings/Settings.h\"
#include \"gui/XournalppCursor.h\"  // for XournalppCursor
#include \"model/Document.h\"       // for Document
#include \"model/Element.h\"        // for Element
#include \"model/Font.h\"           // for XojFont
#include \"model/Layer.h\"          // for Layer
#include \"model/Stroke.h\"         // for Stroke, ArrowKind
#include \"model/Text.h\"           // for Text
#include \"model/XojPage.h\"        // for XojPage
#include \"undo/DeleteUndoAction.h\""""
CPP_OLD2 = """    return res;
}

void TextEditor::repaintEditor(bool sizeChanged) {
    Range dirtyRange(this->previousBoundingBox);
    if (sizeChanged) {
        this->previousBoundingBox = this->computeBoundingBox();
        dirtyRange = dirtyRange.unite(this->previousBoundingBox);
    }
    this->updateCursorBox();
    this->viewPool->dispatch(xoj::view::TextEditionView::FLAG_DIRTY_REGION, dirtyRange);"""
CPP_NEW2 = """    return res;
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

void TextEditor::repaintEditor(bool sizeChanged) {
    Range dirtyRange(this->previousBoundingBox);
    if (sizeChanged) {
        this->previousBoundingBox = this->computeBoundingBox();
        dirtyRange = dirtyRange.unite(this->previousBoundingBox);

        // Patch 12.1 (\"table writing assist\"): keep the text centered within its detected table cell
        // as its content (and therefore its size) changes. Repositioning changes the bounding box
        // again, so it must be recomputed once more for the dirty-region tracking to stay correct.
        if (this->tableMode) {
            this->recenterInTableCell();
            this->previousBoundingBox = this->computeBoundingBox();
            dirtyRange = dirtyRange.unite(this->previousBoundingBox);
        }
    }
    this->updateCursorBox();
    this->viewPool->dispatch(xoj::view::TextEditionView::FLAG_DIRTY_REGION, dirtyRange);"""
CPP_OLD3 = """    }
}

void TextEditor::initializeEditionAt(double x, double y) {
    // Is there already a textfield?
    Text* text = nullptr;"""
CPP_NEW3 = """    }
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
            } else if (lineX > x && lineX < rightX) {
                rightX = lineX;
                hasRight = true;
            }
        } else if (isHorizontal && shaft.x <= x && x <= shaft.x + shaft.width) {
            double lineY = shaft.y + shaft.height / 2.0;
            if (lineY <= y && lineY > topY) {
                topY = lineY;
                hasTop = true;
            } else if (lineY > y && lineY < bottomY) {
                bottomY = lineY;
                hasBottom = true;
            }
        }
    }

    int foundCount = (hasLeft ? 1 : 0) + (hasRight ? 1 : 0) + (hasTop ? 1 : 0) + (hasBottom ? 1 : 0);
    if (foundCount < 3) {
        return std::nullopt;
    }

    if (!hasLeft) {
        leftX = x - (rightX - x);
    }
    if (!hasRight) {
        rightX = x + (x - leftX);
    }
    if (!hasTop) {
        topY = y - (bottomY - y);
    }
    if (!hasBottom) {
        bottomY = y + (y - topY);
    }

    return xoj::util::Rectangle<double>(leftX, topY, rightX - leftX, bottomY - topY);
}

void TextEditor::initializeEditionAt(double x, double y) {
    // Is there already a textfield?
    Text* text = nullptr;"""
CPP_OLD4 = """        this->textElement = std::make_unique<Text>();
        this->textElement->setColor(h->getColor());
        this->textElement->setFont(control->getSettings()->getFont());
        this->textElement->setX(x);
        this->textElement->setY(y - this->textElement->getElementHeight() / 2);

#ifdef ENABLE_AUDIO
        if (auto audioController = control->getAudioController(); audioController && audioController->isRecording()) {"""
CPP_NEW4 = """        this->textElement = std::make_unique<Text>();
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
    for p in (h_file, cpp_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "tableMode" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 12.1 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H_OLD0, H_NEW0, "h: zone 1/3")
    ok &= apply_edit(h_file, H_OLD1, H_NEW1, "h: zone 2/3")
    ok &= apply_edit(h_file, H_OLD2, H_NEW2, "h: zone 3/3")
    ok &= apply_edit(cpp_file, CPP_OLD0, CPP_NEW0, "cpp: zone 1/5")
    ok &= apply_edit(cpp_file, CPP_OLD1, CPP_NEW1, "cpp: zone 2/5")
    ok &= apply_edit(cpp_file, CPP_OLD2, CPP_NEW2, "cpp: zone 3/5")
    ok &= apply_edit(cpp_file, CPP_OLD3, CPP_NEW3, "cpp: zone 4/5")
    ok &= apply_edit(cpp_file, CPP_OLD4, CPP_NEW4, "cpp: zone 5/5")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
