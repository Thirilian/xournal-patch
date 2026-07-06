#!/usr/bin/env python3
"""
Patch 8.8 (nouvelle fonctionnalite, phase 8) du systeme d'ancrage entre
objets. Ajoute le snapping du palier ordinaire (vert/rose UNIQUEMENT -
jamais bleu, jamais equidistant, jamais centre-de-page, jamais grille
bleue, jamais centre-de-table) au point mobile (coin ou bord) pendant le
redimensionnement d'un objet deja cree.

Concretement : le point qui bouge pendant le redimensionnement (coin pour
une poignee d'angle, bord entier pour une poignee de cote) est desormais
compare aux bords/centres des AUTRES objets via findAlignmentX/Y(), en
concurrence avec le snap de grille deja existant (snappingHandler) -
que celui qui tire le moins loin du point brut l'emporte. Tout resultat
boost (bleu) est explicitement ignore. Les guides verts/roses
correspondants s'affichent normalement pendant le redimensionnement.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)

Independant des autres patches 8.X (ne touche aucune structure partagee,
seulement le bloc de redimensionnement, distinct du bloc de deplacement
modifie par les autres patches).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "CrossAxis" not in content:
        print("[ECHEC] CrossAxis introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 a v7_9.py, puis relancez ce script.")
        sys.exit(1)
    if "rawCornerX" in content:
        print("[SKIP] Le patch 8.8 semble deja applique.")
        sys.exit(0)

    ok = apply_edit(
        cpp,
        old='                scaleShift(xSide ? f : 1, ySide ? f : 1, xSide == -1, ySide == -1);\n\n'
            '                // in each case first scale without snapping consideration then snap\n'
            '                // take care that wSnap and hSnap are not too small\n'
            '                double snappedX =\n'
            '                        snappingHandler.snapHorizontally(this->snappedBounds.x + this->snappedBounds.width * xMul, alt);\n'
            '                double snappedY =\n'
            '                        snappingHandler.snapVertically(this->snappedBounds.y + this->snappedBounds.height * yMul, alt);\n',
        new='                scaleShift(xSide ? f : 1, ySide ? f : 1, xSide == -1, ySide == -1);\n\n'
            '                // in each case first scale without snapping consideration then snap\n'
            '                // take care that wSnap and hSnap are not too small\n\n'
            '                // Alignment-based snap (ordinary tier only - green/pink; never blue/equidistant/table\n'
            '                // center/page center) for the moving corner/edge point during a resize - see\n'
            '                // findAlignmentX/Y(). Competes with the existing grid-based snap below\n'
            '                // (snappingHandler): whichever pulls less far from the raw (post-scale, pre-snap)\n'
            '                // position wins. The "self" box passed to findAlignmentX/Y is a single point on the\n'
            '                // axis being dragged (zero width/height), spanning the object\'s own current extent on\n'
            '                // the other axis, so it can match against other elements\' edges/centers just like a\n'
            '                // real object would.\n'
            '                double rawCornerX = this->snappedBounds.x + this->snappedBounds.width * xMul;\n'
            '                double rawCornerY = this->snappedBounds.y + this->snappedBounds.height * yMul;\n'
            '                std::optional<double> alignedCornerX;\n'
            '                std::optional<double> alignedCornerY;\n'
            '                this->activeGuidesX.clear();\n'
            '                this->activeGuidesY.clear();\n'
            '                {\n'
            '                    std::vector<const Element*> excludedForResize = this->getElementsView().clone();\n'
            '                    xoj::util::Rectangle<double>* visibleRectPtrForResize =\n'
            '                            this->view->getXournal()->getVisibleRect(this->view);\n'
            '                    if (visibleRectPtrForResize != nullptr) {\n'
            '                        xoj::util::Rectangle<double> visibleRectForResize = *visibleRectPtrForResize;\n'
            '                        delete visibleRectPtrForResize;\n'
            '                        double resizeTolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;\n'
            '                        if (xSide != 0) {\n'
            '                            if (auto matchX = findAlignmentX(rawCornerX, 0, this->snappedBounds.y,\n'
            '                                                              this->snappedBounds.y + this->snappedBounds.height,\n'
            '                                                              resizeTolerance, this->sourceLayer, excludedForResize,\n'
            '                                                              visibleRectForResize)) {\n'
            '                                if (!matchX->guides.empty() && !matchX->guides.front().isBoosted) {\n'
            '                                    alignedCornerX = rawCornerX + matchX->offset;\n'
            '                                    for (auto& g: matchX->guides) {\n'
            '                                        this->activeGuidesX.push_back(AlignmentGuide{g.coordinate, g.extentFrom,\n'
            '                                                                                      g.extentTo, g.isCenter,\n'
            '                                                                                      g.isBoosted});\n'
            '                                    }\n'
            '                                }\n'
            '                            }\n'
            '                        }\n'
            '                        if (ySide != 0) {\n'
            '                            if (auto matchY = findAlignmentY(rawCornerY, 0, this->snappedBounds.x,\n'
            '                                                              this->snappedBounds.x + this->snappedBounds.width,\n'
            '                                                              resizeTolerance, this->sourceLayer, excludedForResize,\n'
            '                                                              visibleRectForResize)) {\n'
            '                                if (!matchY->guides.empty() && !matchY->guides.front().isBoosted) {\n'
            '                                    alignedCornerY = rawCornerY + matchY->offset;\n'
            '                                    for (auto& g: matchY->guides) {\n'
            '                                        this->activeGuidesY.push_back(AlignmentGuide{g.coordinate, g.extentFrom,\n'
            '                                                                                      g.extentTo, g.isCenter,\n'
            '                                                                                      g.isBoosted});\n'
            '                                    }\n'
            '                                }\n'
            '                            }\n'
            '                        }\n'
            '                    }\n'
            '                }\n\n'
            '                double snappedX = snappingHandler.snapHorizontally(rawCornerX, alt);\n'
            '                if (alignedCornerX && std::abs(*alignedCornerX - rawCornerX) < std::abs(snappedX - rawCornerX)) {\n'
            '                    snappedX = *alignedCornerX;\n'
            '                }\n'
            '                double snappedY = snappingHandler.snapVertically(rawCornerY, alt);\n'
            '                if (alignedCornerY && std::abs(*alignedCornerY - rawCornerY) < std::abs(snappedY - rawCornerY)) {\n'
            '                    snappedY = *alignedCornerY;\n'
            '                }\n',
        label="EditSelection.cpp: snap ordinaire (vert/rose) sur le point mobile du redimensionnement",
    )

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
