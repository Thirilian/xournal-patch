#!/usr/bin/env python3
"""
Sous-patch 1/2 du systeme d'ancrage entre objets (style Canva/Figma).
Ajoute un snap SILENCIEUX (pas encore de ligne de guidage visuelle) : quand on
deplace un objet selectionne, si un de ses bords/centre (haut/milieu/bas,
gauche/milieu/droite) tombe a moins de 6px (independant du zoom) du bord/centre
correspondant d'un autre element du meme calque, la position est ajustee pour
s'aligner exactement dessus.

Limitations volontaires de ce premier sous-patch (prevues pour la suite) :
  - Pas de ligne de guidage visuelle (silencieux pour l'instant).
  - Pas de gestion de l'axe directionnel des lignes/fleches.
  - Desactive si la selection est actuellement pivotee (rotation != 0).
  - Concu pour un seul objet/groupe deplace (pas de cas particulier multi-selection).

Independant des autres patches de cette conversation (fichier different).
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
    f = Path("src/core/control/tools/EditSelection.cpp")
    if not f.exists():
        print(f"[ECHEC] {f} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    ok = True

    # --- helper functions, right before mouseMove() ---
    ok &= apply_edit(
        f,
        old='void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {',
        new='/**\n'
            ' * Smart alignment guides (sub-patch 1: silent snap, no visual guide line yet).\n'
            ' *\n'
            ' * Tolerance in screen pixels (independent of zoom) within which a candidate edge/center of the\n'
            ' * moving selection\'s bounding box is considered "aligned" with a candidate edge/center of another\n'
            ' * element on the same layer.\n'
            ' */\n'
            'constexpr double ALIGNMENT_SNAP_TOLERANCE_PX = 6.0;\n\n'
            '/**\n'
            ' * If any of the moving box\'s 3 horizontal candidates (top / vertical-center / bottom), when placed\n'
            ' * at the given y with the given height, is within `tolerance` (document units) of the corresponding\n'
            ' * candidate of another element on `layer` (elements in `excluded` are skipped - i.e. the elements\n'
            ' * currently being moved), returns the y-offset needed to align them exactly. Returns 0 otherwise.\n'
            ' */\n'
            'static auto findAlignmentOffsetY(double y, double height, double tolerance, Layer* layer,\n'
            '                                  const std::vector<const Element*>& excluded) -> double {\n'
            '    const double candidatesSelf[3] = {y, y + height / 2, y + height};\n'
            '    double bestOffset = 0;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        const double candidatesOther[3] = {ey, ey + eh / 2, ey + eh};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    bestOffset = co - cs;\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return bestOffset;\n'
            '}\n\n'
            '/// Same as findAlignmentOffsetY(), but for the 3 vertical candidates (left / horizontal-center / right).\n'
            'static auto findAlignmentOffsetX(double x, double width, double tolerance, Layer* layer,\n'
            '                                  const std::vector<const Element*>& excluded) -> double {\n'
            '    const double candidatesSelf[3] = {x, x + width / 2, x + width};\n'
            '    double bestOffset = 0;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        const double candidatesOther[3] = {ex, ex + ew / 2, ex + ew};\n'
            '        for (double cs: candidatesSelf) {\n'
            '            for (double co: candidatesOther) {\n'
            '                double dist = std::abs(cs - co);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    bestOffset = co - cs;\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return bestOffset;\n'
            '}\n\n'
            'void EditSelection::mouseMove(double mouseX, double mouseY, bool alt) {',
        label="EditSelection.cpp: findAlignmentOffsetX/Y helpers",
    )

    # --- injection point: right after the raw dx,dy computation ---
    ok &= apply_edit(
        f,
        old='    if (this->mouseDownType == CURSOR_SELECTION_MOVE) {\n'
            '        // compute translation (without snapping)\n'
            '        double dx = mouseX / zoom - this->snappedBounds.x - this->relMousePosX;\n'
            '        double dy = mouseY / zoom - this->snappedBounds.y - this->relMousePosY;\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position\n'
            '        double cx = this->snappedBounds.x;',
        new='    if (this->mouseDownType == CURSOR_SELECTION_MOVE) {\n'
            '        // compute translation (without snapping)\n'
            '        double dx = mouseX / zoom - this->snappedBounds.x - this->relMousePosX;\n'
            '        double dy = mouseY / zoom - this->snappedBounds.y - this->relMousePosY;\n\n'
            '        // Smart alignment guides: snap the moving selection\'s bounding box edges/centers to those of\n'
            '        // other elements on the same layer, if close enough. Silent for now (no guide line drawn yet).\n'
            '        if (this->sourceLayer != nullptr && this->rotation == 0.0) {\n'
            '            double tolerance = ALIGNMENT_SNAP_TOLERANCE_PX / zoom;\n'
            '            std::vector<const Element*> excluded = this->getElementsView().clone();\n'
            '            double candidateX = this->snappedBounds.x + dx;\n'
            '            double candidateY = this->snappedBounds.y + dy;\n'
            '            dx += findAlignmentOffsetX(candidateX, this->snappedBounds.width, tolerance, this->sourceLayer, excluded);\n'
            '            dy += findAlignmentOffsetY(candidateY, this->snappedBounds.height, tolerance, this->sourceLayer, excluded);\n'
            '        }\n\n'
            '        // find corner of reduced bounding box in rotated coordinate system closest to grabbing position\n'
            '        double cx = this->snappedBounds.x;',
        label="EditSelection.cpp: injection du snap dans mouseMove()",
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
