#!/usr/bin/env python3
"""
Patch 8.6.4.3 (depend de 8.6.4 + 8.6.4.2) : corrige deux bugs reels.

1) L'epaisseur du trait (line width) etait divisee/multipliee en meme
   temps que sa longueur, car LineHalfDoubleUndoAction passait
   restoreLineWidth=false a Element::scale(). Corrige a true.

2) Le trait selectionne (en cours de glissement) ne changeait jamais de
   taille ni de position lors de la transformation "demi/double au
   relachement" : il est en realite retire du calque des sa selection
   (voir createFromElementOnActiveLayer()/createFromElementsOnActiveLayer(),
   layer->removeElementAt(...)) et n'y revient qu'a la deselection.
   applyLineHalfDoubleOnRelease() ne cherchait donc jamais que dans
   layer->getElements(), qui ne contient jamais le trait actuellement
   selectionne. Corrige en verifiant explicitement aussi les elements de
   la selection courante (via getElementsView()), en plus du calque.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_1.py + v8_1_2.py
  4) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  5) apply_alignment_snap_v8_6_4.py + v8_6_4_2.py

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
    undo_cpp = Path("src/core/undo/LineHalfDoubleUndoAction.cpp")
    if not cpp.exists() or not undo_cpp.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "applyLineHalfDoubleOnRelease" not in content:
        print("[ECHEC] applyLineHalfDoubleOnRelease introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_4.py + v8_6_4_2.py, puis relancez ce script.")
        sys.exit(1)
    if "const std::vector<Element*>& selfElements" in content:
        print("[SKIP] Le patch 8.6.4.3 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. correction de l'epaisseur (restoreLineWidth) ============
    ok &= apply_edit(
        undo_cpp,
        old="        element->scale(origin.x, origin.y, f, f, 0, false);",
        new="        element->scale(origin.x, origin.y, f, f, 0, true);",
        label="LineHalfDoubleUndoAction.cpp: conservation de l'epaisseur du trait",
    )

    # ============ 2a. declaration anticipee: nouvelle signature ============
    ok &= apply_edit(
        cpp,
        old="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
            "                                          const Element* bigLine, bool isXAxis, int zone);",
        new="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
            "                                          const Element* bigLine, bool isXAxis, int zone,\n"
            "                                          const std::vector<Element*>& selfElements);",
        label="EditSelection.cpp: declaration anticipee - nouvelle signature",
    )

    # ============ 2b. definition complete: refactorisation + prise en compte de self ============
    ok &= apply_edit(
        cpp,
        old="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
            "                                          const Element* bigLine, bool isXAxis, int zone) {\n"
            "    if (bigLine == nullptr) {\n"
            "        return;\n"
            "    }\n"
            "    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();\n"
            "    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);\n\n"
            "    std::vector<Element*> family;\n"
            "    for (auto& elPtr: layer->getElements()) {\n"
            "        Element* el = elPtr.get();\n"
            "        if (el == bigLine) {\n"
            "            continue;\n"
            "        }\n"
            "        auto* stroke = dynamic_cast<Stroke*>(el);\n"
            "        if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {\n"
            "            continue;\n"
            "        }\n"
            "        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "        bool matchesOrientation = isXAxis ? (shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD)\n"
            "                                           : (shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD);\n"
            "        if (!matchesOrientation) {\n"
            "            continue;\n"
            "        }\n"
            "        if (isXAxis) {\n"
            "            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) ||\n"
            "                crossingCoord < shaft.x || crossingCoord > shaft.x + shaft.width) {\n"
            "                continue;\n"
            "            }\n"
            "        } else {\n"
            "            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) ||\n"
            "                crossingCoord < shaft.y || crossingCoord > shaft.y + shaft.height) {\n"
            "                continue;\n"
            "            }\n"
            "        }\n"
            "        family.push_back(el);\n"
            "    }\n"
            "    if (family.empty()) {\n"
            "        return;\n"
            "    }\n",
        new="static void applyLineHalfDoubleOnRelease(Control* control, Layer* layer, const PageRef& page,\n"
            "                                          const Element* bigLine, bool isXAxis, int zone,\n"
            "                                          const std::vector<Element*>& selfElements) {\n"
            "    if (bigLine == nullptr) {\n"
            "        return;\n"
            "    }\n"
            "    xoj::util::Rectangle<double> bigShaft = bigLine->getSnappedBounds();\n"
            "    double crossingCoord = isXAxis ? (bigShaft.x + bigShaft.width / 2) : (bigShaft.y + bigShaft.height / 2);\n\n"
            "    auto isEligibleFamilyMember = [&](Element* el) -> bool {\n"
            "        if (el == bigLine) {\n"
            "            return false;\n"
            "        }\n"
            "        auto* stroke = dynamic_cast<Stroke*>(el);\n"
            "        if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {\n"
            "            return false;\n"
            "        }\n"
            "        xoj::util::Rectangle<double> shaft = el->getSnappedBounds();\n"
            "        bool matchesOrientation = isXAxis ? (shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD)\n"
            "                                           : (shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD);\n"
            "        if (!matchesOrientation) {\n"
            "            return false;\n"
            "        }\n"
            "        if (isXAxis) {\n"
            "            return rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height) &&\n"
            "                   crossingCoord >= shaft.x && crossingCoord <= shaft.x + shaft.width;\n"
            "        }\n"
            "        return rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width) &&\n"
            "               crossingCoord >= shaft.y && crossingCoord <= shaft.y + shaft.height;\n"
            "    };\n\n"
            "    std::vector<Element*> family;\n"
            "    // The currently-selected element(s) are NOT in `layer->getElements()` while selected (they are\n"
            "    // physically removed from the layer for the duration of the selection - see\n"
            "    // createFromElementOnActiveLayer()/createFromElementsOnActiveLayer() - and only reinserted once\n"
            "    // deselected), so they must be checked separately here, or the moving line itself would never\n"
            "    // take part in its own family's transformation.\n"
            "    for (Element* el: selfElements) {\n"
            "        if (isEligibleFamilyMember(el)) {\n"
            "            family.push_back(el);\n"
            "        }\n"
            "    }\n"
            "    for (auto& elPtr: layer->getElements()) {\n"
            "        Element* el = elPtr.get();\n"
            "        if (isEligibleFamilyMember(el)) {\n"
            "            family.push_back(el);\n"
            "        }\n"
            "    }\n"
            "    if (family.empty()) {\n"
            "        return;\n"
            "    }\n",
        label="EditSelection.cpp: prise en compte du trait selectionne (hors calque)",
    )

    # ============ 3. mouseUp(): transmission des elements de la selection ============
    ok &= apply_edit(
        cpp,
        old="        applyLineHalfDoubleOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,\n"
            "                                     this->activeBoostedIsXAxis, this->activeBoostedZone);\n",
        new="        applyLineHalfDoubleOnRelease(this->view->getXournal()->getControl(), layer, page, this->activeBoostedTarget,\n"
            "                                     this->activeBoostedIsXAxis, this->activeBoostedZone,\n"
            "                                     this->getElementsView().clone());\n",
        label="EditSelection.cpp: mouseUp() transmet les elements de la selection",
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
