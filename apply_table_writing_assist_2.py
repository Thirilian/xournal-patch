#!/usr/bin/env python3
"""
Patch 12.2 ("aide a l'ecriture d'un tableau") : retrecissement/
agrandissement automatique de la police d'une textbox en mode "case".

Pendant la frappe, si le texte deborde desormais de la case, la taille
de police est reduite (pas de 0.5pt, recherche lineaire) jusqu'a ce
qu'il rentre, avec un plancher a 6pt. A l'inverse, si la taille actuelle
est inferieure a celle memorisee a la creation
(tableModeOriginalFontSize, patch 12.1), on verifie si elle peut
remonter (par pas de 0.5pt) sans deborder, et on l'augmente autant que
possible jusqu'a cette valeur d'origine.

Le redimensionnement a lieu AVANT le recentrage (patch 12.1) a chaque
frappe, dans TextEditor::repaintEditor().

Modifie :
  - src/core/control/tools/TextEditor.h (nouvelle methode
    adjustTableModeFontSize())
  - src/core/control/tools/TextEditor.cpp (implementation, cablage dans
    repaintEditor())

NECESSITE : apply_patch12_1_table_writing_assist.py

Independant de la serie de patchs alignment_snap.

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H1_OLD = """    void recenterInTableCell();
"""
H1_NEW = """    void recenterInTableCell();

    /// Patch 12.2: shrinks the font (down to a 6pt floor) if the text currently overflows
    /// tableCellBounds, or grows it back towards tableModeOriginalFontSize if there is room to do so
    /// - a no-op if !tableMode. Called from repaintEditor(), before recenterInTableCell().
    void adjustTableModeFontSize();
"""
C1_OLD = """#include <cstring>  // for strcmp, size_t
"""
C1_NEW = """#include <algorithm>  // for max, min
#include <cstring>  // for strcmp, size_t
"""
C2_OLD = """void TextEditor::recenterInTableCell() {
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
"""
C2_NEW = """void TextEditor::recenterInTableCell() {
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
    // towards tableModeOriginalFontSize otherwise, as far as it fits. A linear (not binary) search was
    // chosen deliberately: at typical table font sizes, only a handful of steps are ever needed, so the
    // simplicity is worth more here than the (negligible) performance difference.
    constexpr double FONT_SIZE_STEP = 0.5;
    constexpr double MIN_TABLE_MODE_FONT_SIZE = 6.0;

    auto measure = [this]() -> std::pair<double, double> {
        Range box = this->computeBoundingBox();
        return {box.maxX - box.minX, box.maxY - box.minY};
    };
    auto overflows = [this](double w, double h) {
        return w > this->tableCellBounds.width || h > this->tableCellBounds.height;
    };
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
    } else if (currentSize < this->tableModeOriginalFontSize) {
        while (currentSize < this->tableModeOriginalFontSize) {
            double nextSize = std::min(this->tableModeOriginalFontSize, currentSize + FONT_SIZE_STEP);
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
"""


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
    if "tableMode" not in h_file.read_text(encoding="utf-8"):
        print("[ECHEC] tableMode introuvable dans TextEditor.h.")
        print("        Appliquez d'abord apply_patch12_1_table_writing_assist.py, puis relancez ce script.")
        sys.exit(1)
    if "adjustTableModeFontSize" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 12.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H1_OLD, H1_NEW, "TextEditor.h: declaration de adjustTableModeFontSize")
    ok &= apply_edit(cpp_file, C1_OLD, C1_NEW, "TextEditor.cpp: include <algorithm>")
    ok &= apply_edit(cpp_file, C2_OLD, C2_NEW, "TextEditor.cpp: implementation + cablage dans repaintEditor")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
