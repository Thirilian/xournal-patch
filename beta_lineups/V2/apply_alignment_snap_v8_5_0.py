#!/usr/bin/env python3
"""
Patch 8.5.0 : fusion des patchs 8.5 et 8.5.2 (cercle parfait pour
l'ellipse) en un seul, applicable PAR-DESSUS d'autres patchs -
modifications CIBLEES par ancres de texte (pas de reecriture de fichier
entier), exactement comme le reste de cette serie.

Ce script applique, region par region, les memes modifications que la
sequence :
    apply_alignment_snap_v8_5.py
    apply_alignment_snap_v8_5_2.py
(dans cet ordre), sans jamais reecrire un fichier entier - seules les
zones reellement modifiees par cette chaine sont touchees, avec assez de
contexte autour de chacune pour garantir un ancrage unique (verifie lors
de la creation de ce patch, sur une base v7.10 + 8.1.0 + 8.2.0 + 8.3.0 +
8.4.0).

Fichiers concernes :
  - src/core/control/tools/BaseShapeHandler.cpp\n  - src/core/control/tools/BaseShapeHandler.h\n  - src/core/control/tools/EllipseHandler.cpp\n  - src/core/view/overlays/ShapeToolView.cpp\n
NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py), OU v7_10.py
  3) apply_alignment_snap_v8_4.py a v8_4_4.py (ou le patch fusionne
     v8_4_0.py), pour BaseShapeHandler.h/.cpp

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

# Chaque entree : (chemin, [(ancre, remplacement), ...])
EDITS = [
    ("src/core/control/tools/BaseShapeHandler.cpp", [
        ("""            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);
        }
    }
    Range repaintRange = rg.unite(lastSnappingRange);
    lastSnappingRange = rg;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());""", """            rg.addPoint(center.x + LINE_CROSS_MARKER_HALF_SIZE, center.y + LINE_CROSS_MARKER_HALF_SIZE);
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
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""),
        ("""void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    this->lineCrossingGuide.reset();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);""", """void BaseShapeHandler::cancelStroke() {
    this->shape.clear();
    this->lineCrossingGuide.reset();
    this->diagonalSnapGuide.reset();
    Range repaintRange = this->lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());
    this->viewPool->dispatchAndClear(xoj::view::ShapeToolView::FINALIZATION_REQUEST, repaintRange);"""),
        ("""    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());
    this->lineCrossingGuide.reset();

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());""", """    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());
    this->lineCrossingGuide.reset();
    this->diagonalSnapGuide.reset();

    Range repaintRange = lastSnappingRange;
    repaintRange.addPadding(0.5 * this->stroke->getWidth());"""),
    ]),
    ("src/core/control/tools/BaseShapeHandler.h", [
        ("""    const std::vector<Point>& getShape() const;

    /**
     * @brief Whether this shape tool produces an arrow (and if so, single- or double-ended), so that
     * the finalized Stroke can be tagged accordingly (see Stroke::setArrowKind()). NONE by default;
     * overridden by ArrowHandler.""", """    const std::vector<Point>& getShape() const;

    /**
     * Last zoom level seen in onMotionNotifyEvent(), exposed so views (e.g. ShapeToolView) can draw
     * overlay guides at a constant on-screen thickness, matching EditSelection's alignment guides,
     * regardless of the actual zoom level - see lastZoom's own doc comment below for why it exists.
     */
    double getLastZoom() const { return lastZoom; }

    /**
     * @brief Whether this shape tool produces an arrow (and if so, single- or double-ended), so that
     * the finalized Stroke can be tagged accordingly (see Stroke::setArrowKind()). NONE by default;
     * overridden by ArrowHandler."""),
        ("""    };
    const std::optional<LineCrossingGuide>& getLineCrossingGuide() const { return lineCrossingGuide; }

private:
    /**
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in""", """    };
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
     * @brief Create the shape (to be drawn and added as a stroke), depending on the last event in"""),
        ("""    double lastZoom = 1.0;

    std::optional<LineCrossingGuide> lineCrossingGuide;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};""", """    double lastZoom = 1.0;

    std::optional<LineCrossingGuide> lineCrossingGuide;
    std::optional<DiagonalSnapGuide> diagonalSnapGuide;

    std::shared_ptr<xoj::util::DispatchPool<xoj::view::ShapeToolView>> viewPool;
};"""),
    ]),
    ("src/core/control/tools/EllipseHandler.cpp", [
        ("""        width = (this->modControl) ? std::hypot(width, height) :
                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);
        height = std::copysign(width, height);
    }

    double radiusX = 0;""", """        width = (this->modControl) ? std::hypot(width, height) :
                                     std::copysign(std::max(std::abs(width), std::abs(height)), width);
        height = std::copysign(width, height);
    } else {
        // Diagonal snap assist: if width and height are already close, snap them to be exactly
        // equal (a perfect circle's bounding box becomes a square), and show two green guide lines
        // along the edges nearest the cursor. The cursor can keep moving freely along the diagonal
        // while snapped, since both dimensions grow/shrink together; if they drift too far apart
        // again, the snap (and the guide) releases.
        this->diagonalSnapGuide.reset();
        constexpr double DIAGONAL_SNAP_TOLERANCE_PX = 6.0;
        double tolerance = DIAGONAL_SNAP_TOLERANCE_PX / this->lastZoom;
        if (std::abs(std::abs(width) - std::abs(height)) < tolerance) {
            double snappedSize = std::max(std::abs(width), std::abs(height));
            width = std::copysign(snappedSize, width);
            height = std::copysign(snappedSize, height);
            this->diagonalSnapGuide =
                    DiagonalSnapGuide{this->startPoint, Point(this->startPoint.x + width, this->startPoint.y + height)};
        }
    }

    double radiusX = 0;"""),
    ]),
    ("src/core/view/overlays/ShapeToolView.cpp", [
        ("""            cairo_stroke(cr);
        }
    }
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }""", """            cairo_stroke(cr);
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
        cairo_move_to(cr, guide->corner2.x, guide->corner1.y);
        cairo_line_to(cr, guide->corner2.x, guide->corner2.y);
        cairo_line_to(cr, guide->corner1.x, guide->corner2.y);
        cairo_stroke(cr);
    }
}

bool ShapeToolView::isViewOf(const OverlayBase* overlay) const { return overlay == this->toolHandler; }"""),
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
    base_h = Path("src/core/control/tools/BaseShapeHandler.h")
    if not base_h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "applyLineCrossingSnap" not in base_h.read_text(encoding="utf-8"):
        print("[ECHEC] applyLineCrossingSnap introuvable dans BaseShapeHandler.h.")
        print("        Appliquez d'abord la chaine 8.4 (v8_4.py a v8_4_4.py, ou v8_4_0.py), puis relancez ce script.")
        sys.exit(1)

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
