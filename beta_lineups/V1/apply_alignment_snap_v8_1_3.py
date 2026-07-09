#!/usr/bin/env python3
"""
Patch 8.1.3 (depend de 8.1 + 8.1.2) : le snapping equidistant ne se
declenche desormais que si les objets de reference (B et C, celles deja
placees) sont visibles a l'ecran - meme regle "overlap sur l'axe
perpendiculaire" deja utilisee par findAlignmentX/Y, jusqu'ici absente de
findEquidistantX/Y.

L'objet deplace (self) n'a pas besoin de cette verification puisqu'il est
par definition a l'ecran (c'est la ou se trouve le curseur).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py

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
    if "findEquidistantX" not in content:
        print("[ECHEC] findEquidistantX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_1.py + v8_1_2.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        cpp,
        old='static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }',
        new='static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded,\n'
            '                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        candidates.push_back(el);\n'
            '    }',
        label="EditSelection.cpp: filtre de visibilite sur findEquidistantX",
    )

    ok &= apply_edit(
        cpp,
        old='static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }',
        new='static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded,\n'
            '                              const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        candidates.push_back(el);\n'
            '    }',
        label="EditSelection.cpp: filtre de visibilite sur findEquidistantY",
    )

    ok &= apply_edit(
        cpp,
        old='                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,\n'
            '                                                              tolerance, this->sourceLayer, excluded)) {',
        new='                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,\n'
            '                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {',
        label="EditSelection.cpp: mouseMove() transmet visibleRect a findEquidistantX",
    )

    ok &= apply_edit(
        cpp,
        old='                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,\n'
            '                                                              tolerance, this->sourceLayer, excluded)) {',
        new='                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,\n'
            '                                                              tolerance, this->sourceLayer, excluded, visibleRect)) {',
        label="EditSelection.cpp: mouseMove() transmet visibleRect a findEquidistantY",
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
