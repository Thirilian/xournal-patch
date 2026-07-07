#!/usr/bin/env python3
"""
Sous-patch 7.5 du systeme d'ancrage entre objets (style Canva/Figma).

Corrige le probleme "cote selection" signale au patch 7.2 : au lieu de
calculer une boite "hampe seule" seulement pour les objets CIBLES
(getShaftBounds(), patch 6/7), corrige le probleme a la source, dans
Stroke::calcSize() : quand un Stroke a un ArrowKind != NONE (grace au
prealable apply_arrow_resize_fix_v2.py), ses "snapped bounds" sont
calculees a partir du premier et dernier point du trace (la vraie hampe)
au lieu de tous les points. La taille visuelle (x/y/width/height, pour la
selection/l'affichage) n'est pas touchee, seule la version utilisee par le
systeme de snapping change.

Consequence : une fleche se comporte EXACTEMENT comme un trait simple pour
le systeme d'ancrage, qu'elle soit l'objet deplace OU une cible - aucun
changement necessaire dans mouseMove(). La fonction getShaftBounds()
(patch 6/7) devient inutile et est retiree ; ses 6 appels redeviennent de
simples el->getSnappedBounds().

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py (fournit ArrowKind/getArrowKind())
  2) apply_alignment_snap_v1.py a v7.py

A lancer depuis la racine du depot xournalpp.
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
    stroke_cpp = Path("src/core/model/Stroke.cpp")
    editsel_cpp = Path("src/core/control/tools/EditSelection.cpp")

    if not stroke_cpp.exists() or not editsel_cpp.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    if "getArrowKind" not in stroke_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] Stroke::getArrowKind() introuvable.")
        print("        Appliquez d'abord apply_arrow_resize_fix_v2.py, puis relancez ce script.")
        sys.exit(1)
    if "getShaftBounds" not in editsel_cpp.read_text(encoding="utf-8"):
        print("[ECHEC] getShaftBounds introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 à v7.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    # ============ Stroke.cpp : fix a la source ============
    ok &= apply_edit(
        stroke_cpp,
        old='    Element::x = minX;\n'
            '    Element::y = minY;\n'
            '    Element::width = maxX - minX;\n'
            '    Element::height = maxY - minY;\n'
            '    Element::snappedBounds = Rectangle<double>(minSnapX, minSnapY, maxSnapX - minSnapX, maxSnapY - minSnapY);\n'
            '}\n',
        new='    Element::x = minX;\n'
            '    Element::y = minY;\n'
            '    Element::width = maxX - minX;\n'
            '    Element::height = maxY - minY;\n\n'
            '    // The alignment-snapping system treats an arrow exactly like a plain straight line: its snapped\n'
            '    // bounds are derived only from the true shaft endpoints (the first and last point - see\n'
            '    // ArrowHandler::createShape(), which always starts with the shaft\'s start point and ends with its\n'
            '    // tip, regardless of single/double-ended or how many decorative arrowhead "wing" points lie in\n'
            '    // between), ignoring the wings entirely. The *visual* bounds above are unaffected and still cover\n'
            '    // the whole arrowhead, e.g. for selection/click-hit-testing.\n'
            '    if (this->arrowKind != ArrowKind::NONE && this->points.size() >= 2) {\n'
            '        const Point& shaftStart = this->points.front();\n'
            '        const Point& shaftEnd = this->points.back();\n'
            '        double snapMinX = std::min(shaftStart.x, shaftEnd.x);\n'
            '        double snapMinY = std::min(shaftStart.y, shaftEnd.y);\n'
            '        double snapMaxX = std::max(shaftStart.x, shaftEnd.x);\n'
            '        double snapMaxY = std::max(shaftStart.y, shaftEnd.y);\n'
            '        Element::snappedBounds = Rectangle<double>(snapMinX, snapMinY, snapMaxX - snapMinX, snapMaxY - snapMinY);\n'
            '    } else {\n'
            '        Element::snappedBounds = Rectangle<double>(minSnapX, minSnapY, maxSnapX - minSnapX, maxSnapY - minSnapY);\n'
            '    }\n'
            '}\n',
        label="Stroke.cpp: snappedBounds hampe-seule pour les flèches",
    )

    # ============ EditSelection.cpp : retrait de getShaftBounds() ============
    ok &= apply_edit(
        editsel_cpp,
        old='/**\n'
            ' * For the blue "perpendicular cross" tier only: returns a bounding box built from just the first\n'
            ' * and last point of `el` (padded by half its stroke width), instead of its full snapped bounds.\n'
            ' * For a plain 2-point straight line this is identical to the normal bounds. For a shape with extra\n'
            ' * decorative points along the way - most notably an arrow, whose arrowhead "wings" are real points\n'
            ' * in the stroke, flaring out perpendicular to the shaft (see ArrowHandler::createShape()) - this\n'
            ' * instead reflects just the true shaft, so a small stroke crossing an arrow\'s shaft is recognized as\n'
            ' * crossing a thin perpendicular line, exactly like it would for a plain straight line. Elements that\n'
            ' * aren\'t a Stroke, or have fewer than 2 points, fall back to the normal snapped bounds.\n'
            ' */\n'
            'static auto getShaftBounds(const Element* el) -> xoj::util::Rectangle<double> {\n'
            '    if (const auto* stroke = dynamic_cast<const Stroke*>(el)) {\n'
            '        size_t n = stroke->getPointCount();\n'
            '        if (n >= 2) {\n'
            '            const Point* pts = stroke->getPoints();\n'
            '            double halfThick = stroke->getWidth() / 2;\n'
            '            double minX = std::min(pts[0].x, pts[n - 1].x) - halfThick;\n'
            '            double minY = std::min(pts[0].y, pts[n - 1].y) - halfThick;\n'
            '            double maxX = std::max(pts[0].x, pts[n - 1].x) + halfThick;\n'
            '            double maxY = std::max(pts[0].y, pts[n - 1].y) + halfThick;\n'
            '            return xoj::util::Rectangle<double>(minX, minY, maxX - minX, maxY - minY);\n'
            '        }\n'
            '    }\n'
            '    return el->getSnappedBounds();\n'
            '}\n\n',
        new='',
        label="EditSelection.cpp: suppression de getShaftBounds()",
    )

    ok &= apply_edit(
        editsel_cpp,
        old=' * First looks for a "boosted" perpendicular-cross center match (see isSmallCrossingBigPerpendicular()\n'
            ' * and getShaftBounds()); if one is found, it is returned alone (a single blue guide), ignoring every',
        new=' * First looks for a "boosted" perpendicular-cross center match (see isSmallCrossingBigPerpendicular());\n'
            ' * if one is found, it is returned alone (a single blue guide), ignoring every',
        label="EditSelection.cpp: nettoyage du commentaire",
    )

    text = editsel_cpp.read_text(encoding="utf-8")
    n = text.count("getShaftBounds(el)")
    if n > 0:
        text = text.replace("getShaftBounds(el)", "el->getSnappedBounds()")
        editsel_cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: {n} appel(s) getShaftBounds(el) -> el->getSnappedBounds()")
    else:
        print("[SKIP]  EditSelection.cpp: plus aucun appel getShaftBounds(el) à remplacer.")

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
