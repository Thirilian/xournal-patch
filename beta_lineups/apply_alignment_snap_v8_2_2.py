#!/usr/bin/env python3
"""
Patch 8.2.2 (depend de 8.2) du systeme d'ancrage entre objets.

Corrige le recouvrement visuel des lignes de guidage avec le corps des
objets : si l'objet deplace et l'objet cible sont a plus de
GUIDE_TRIM_MIN_GAP (5pt) l'un de l'autre sur l'axe perpendiculaire, la
ligne de guidage est desormais recadree pour ne couvrir QUE l'espace vide
entre leurs deux bords les plus proches, au lieu de l'union complete de
leurs deux etendues (qui recouvrait systematiquement le corps de l'objet
cible quand celui-ci est long sur cet axe, ex: deux lignes perpendiculaires
alignees). En dessous de ce seuil (ou en cas de chevauchement), le
comportement precedent (union complete) est conserve.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py
  4) apply_alignment_snap_v8_2.py

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
    if "selfIsCenter" not in content:
        print("[ECHEC] selfIsCenter introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_2.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    # ============ 1. helper computeGuideExtent, insere via ancre (evite de perdre une ligne) ============
    start_marker = "static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"
    if "computeGuideExtent" in content:
        print("[SKIP]  EditSelection.cpp: computeGuideExtent deja present.")
    else:
        idx = content.find(start_marker)
        if idx == -1:
            print("[ECHEC] EditSelection.cpp: signature de findAlignmentY introuvable.")
            ok = False
        elif content.count(start_marker) > 1:
            print("[ECHEC] EditSelection.cpp: signature de findAlignmentY trouvee plusieurs fois.")
            ok = False
        else:
            helper = (
                "/**\n"
                " * Below this gap (in document points) between the moving object's own extent and the matched\n"
                " * element's own extent (on the perpendicular axis), the guide line still spans their full union, as\n"
                " * before - the objects are close enough (or overlapping) that trimming wouldn't help. Above it, the\n"
                " * line is trimmed to just the empty gap between their two nearest edges, so it no longer runs on top\n"
                " * of either object's body (most noticeable when aligning two objects that are long on the\n"
                " * perpendicular axis, e.g. two perpendicular lines).\n"
                " */\n"
                "constexpr double GUIDE_TRIM_MIN_GAP = 5.0;\n\n"
                "/**\n"
                " * Computes the [from, to] span (perpendicular axis) for a guide line connecting an object spanning\n"
                " * [selfLo, selfHi] to another spanning [otherLo, otherHi]. If the two don't overlap and the gap\n"
                " * between their nearest edges exceeds GUIDE_TRIM_MIN_GAP, the line is trimmed to exactly that gap\n"
                " * (the empty space between them). Otherwise (overlapping, or too close to bother trimming), the\n"
                " * line spans their full union, as it always did before this trimming was added.\n"
                " */\n"
                "static void computeGuideExtent(double selfLo, double selfHi, double otherLo, double otherHi, double& outFrom,\n"
                "                                double& outTo) {\n"
                "    if (selfHi <= otherLo && otherLo - selfHi > GUIDE_TRIM_MIN_GAP) {\n"
                "        outFrom = selfHi;\n"
                "        outTo = otherLo;\n"
                "        return;\n"
                "    }\n"
                "    if (otherHi <= selfLo && selfLo - otherHi > GUIDE_TRIM_MIN_GAP) {\n"
                "        outFrom = otherHi;\n"
                "        outTo = selfLo;\n"
                "        return;\n"
                "    }\n"
                "    outFrom = std::min(selfLo, otherLo);\n"
                "    outTo = std::max(selfHi, otherHi);\n"
                "}\n\n"
            )
            new_content = content[:idx] + helper + content[idx:]
            cpp.write_text(new_content, encoding="utf-8")
            print("[OK]    EditSelection.cpp: ajout de computeGuideExtent()")
            content = new_content

    # ============ 2. findAlignmentY pass 1 (bestAny) ============
    ok &= apply_edit(
        cpp,
        old='                    bestAnyDist = dist;\n'
            '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
            '                                              co.value,\n'
            '                                              std::min(xLeft, snapped.x),\n'
            '                                              std::max(xRight, snapped.x + snapped.width),\n'
            '                                              cs.isCenter || co.isCenter,\n'
            '                                              false};\n'
            '                    bestAny->selfIsCenter = cs.isCenter;\n'
            '                    bestAny->otherIsCenter = co.isCenter;\n'
            '                    bestAny->selfOnFromSide = xLeft <= snapped.x;\n',
        new='                    bestAnyDist = dist;\n'
            '                    double guideFrom;\n'
            '                    double guideTo;\n'
            '                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);\n'
            '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
            '                                              co.value,\n'
            '                                              guideFrom,\n'
            '                                              guideTo,\n'
            '                                              cs.isCenter || co.isCenter,\n'
            '                                              false};\n'
            '                    bestAny->selfIsCenter = cs.isCenter;\n'
            '                    bestAny->otherIsCenter = co.isCenter;\n'
            '                    bestAny->selfOnFromSide = xLeft <= snapped.x;\n',
        label="EditSelection.cpp: findAlignmentY pass 1 utilise computeGuideExtent",
    )

    # ============ 3. findAlignmentY pass 2 (collect guides) ============
    ok &= apply_edit(
        cpp,
        old='                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
            '                    AlignmentMatch guide{offset, co.value, std::min(xLeft, snapped.x),\n'
            '                                         std::max(xRight, snapped.x + snapped.width),\n'
            '                                         cs.isCenter || co.isCenter, false};\n'
            '                    guide.selfIsCenter = cs.isCenter;\n'
            '                    guide.otherIsCenter = co.isCenter;\n'
            '                    guide.selfOnFromSide = xLeft <= snapped.x;\n'
            '                    guides.push_back(guide);\n'
            '                }\n',
        new='                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
            '                    double guideFrom;\n'
            '                    double guideTo;\n'
            '                    computeGuideExtent(xLeft, xRight, snapped.x, snapped.x + snapped.width, guideFrom, guideTo);\n'
            '                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};\n'
            '                    guide.selfIsCenter = cs.isCenter;\n'
            '                    guide.otherIsCenter = co.isCenter;\n'
            '                    guide.selfOnFromSide = xLeft <= snapped.x;\n'
            '                    guides.push_back(guide);\n'
            '                }\n',
        label="EditSelection.cpp: findAlignmentY pass 2 utilise computeGuideExtent",
    )

    # ============ 4. findAlignmentX pass 1 (bestAny) ============
    ok &= apply_edit(
        cpp,
        old='                    bestAnyDist = dist;\n'
            '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
            '                                              co.value,\n'
            '                                              std::min(yTop, snapped.y),\n'
            '                                              std::max(yBottom, snapped.y + snapped.height),\n'
            '                                              cs.isCenter || co.isCenter,\n'
            '                                              false};\n'
            '                    bestAny->selfIsCenter = cs.isCenter;\n'
            '                    bestAny->otherIsCenter = co.isCenter;\n'
            '                    bestAny->selfOnFromSide = yTop <= snapped.y;\n',
        new='                    bestAnyDist = dist;\n'
            '                    double guideFrom;\n'
            '                    double guideTo;\n'
            '                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);\n'
            '                    bestAny = AlignmentMatch{co.value - cs.value,\n'
            '                                              co.value,\n'
            '                                              guideFrom,\n'
            '                                              guideTo,\n'
            '                                              cs.isCenter || co.isCenter,\n'
            '                                              false};\n'
            '                    bestAny->selfIsCenter = cs.isCenter;\n'
            '                    bestAny->otherIsCenter = co.isCenter;\n'
            '                    bestAny->selfOnFromSide = yTop <= snapped.y;\n',
        label="EditSelection.cpp: findAlignmentX pass 1 utilise computeGuideExtent",
    )

    # ============ 5. findAlignmentX pass 2 (collect guides) ============
    ok &= apply_edit(
        cpp,
        old='                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
            '                    AlignmentMatch guide{offset, co.value, std::min(yTop, snapped.y),\n'
            '                                         std::max(yBottom, snapped.y + snapped.height),\n'
            '                                         cs.isCenter || co.isCenter, false};\n'
            '                    guide.selfIsCenter = cs.isCenter;\n'
            '                    guide.otherIsCenter = co.isCenter;\n'
            '                    guide.selfOnFromSide = yTop <= snapped.y;\n'
            '                    guides.push_back(guide);\n'
            '                }\n',
        new='                if (std::abs((cs.value + offset) - co.value) < tolerance) {\n'
            '                    double guideFrom;\n'
            '                    double guideTo;\n'
            '                    computeGuideExtent(yTop, yBottom, snapped.y, snapped.y + snapped.height, guideFrom, guideTo);\n'
            '                    AlignmentMatch guide{offset, co.value, guideFrom, guideTo, cs.isCenter || co.isCenter, false};\n'
            '                    guide.selfIsCenter = cs.isCenter;\n'
            '                    guide.otherIsCenter = co.isCenter;\n'
            '                    guide.selfOnFromSide = yTop <= snapped.y;\n'
            '                    guides.push_back(guide);\n'
            '                }\n',
        label="EditSelection.cpp: findAlignmentX pass 2 utilise computeGuideExtent",
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
