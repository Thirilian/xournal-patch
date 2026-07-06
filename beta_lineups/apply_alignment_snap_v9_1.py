#!/usr/bin/env python3
"""
Patch 9.1 (correctif general, phase 9) du systeme d'ancrage entre objets.

1) Nouvelle regle "petite marque" : si la dimension globale d'un objet
   (son plus grand cote) est < 15pt (SMALL_MARK_MAX_LENGTH), les DEUX axes
   sont forces a un seul point d'ancrage central, quelle que soit la
   finesse individuelle de chaque axe.
2) Regle separee pour les croix (Ctrl+K) : detection geometrique (5
   points, deux diagonales perpendiculaires de meme longueur se croisant
   au point median) - meme comportement de centre unique force sur les
   deux axes, independamment de la taille.
3) Couleur : le point d'ancrage unique d'un axe simplement fin (ex : la
   hauteur d'un trait horizontal, sans vrai choix bord/centre) devient
   rose au lieu de vert - le vert reste reserve aux vrais centres
   (choix delibere parmi 3 candidats, ou "petite marque"/croix).

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)

Independant des patches 8.X (peut etre applique avec ou sans eux, tant
qu'ils ne touchent pas exactement les memes lignes - non teste avec la
combinaison complete de la phase 8).

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
    if "isCrossShape" in content:
        print("[SKIP] Le patch 9.1 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ 1. Reecriture de buildCandidates() + nouvelles fonctions ============
    ok &= apply_edit(
        cpp,
        old='/**\n'
            ' * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis. If the\n'
            ' * box is "thin" on that axis (size <= THIN_AXIS_THRESHOLD, e.g. the thickness of a horizontal or\n'
            ' * vertical line), only the center candidate is returned: offering top/bottom (or left/right)\n'
            ' * candidates as well would produce two near-identical, confusingly close guide lines for a simple\n'
            ' * straight line. `centerFraction` (0 to 1) chooses where the center candidate sits within the box,\n'
            ' * in *both* branches (e.g. TEXT_Y_CENTER_FRACTION only has any effect because of this).\n'
            ' */\n'
            'static auto buildCandidates(double from, double size, double centerFraction = 0.5) -> std::vector<AlignmentCandidate> {\n'
            '    if (size <= THIN_AXIS_THRESHOLD) {\n'
            '        return {{from + size * centerFraction, true}};\n'
            '    }\n'
            '    return {{from, false}, {from + size * centerFraction, true}, {from + size, false}};\n'
            '}\n',
        new='/**\n'
            ' * Below this length (in document points, measured as the larger of an element\'s own width/height),\n'
            ' * an element is considered a "small mark" for anchor purposes - see buildCandidates()\'s\n'
            ' * `forceCenterOnly` parameter. Distinct from THIN_AXIS_THRESHOLD (which only concerns a single axis\n'
            ' * relative to a long line) - this instead looks at the object as a whole, so a small tick or cross\n'
            ' * mark always gets a single center anchor on *both* axes, regardless of how it happens to be\n'
            ' * proportioned.\n'
            ' */\n'
            'constexpr double SMALL_MARK_MAX_LENGTH = 15.0;\n\n'
            '/// True if an element whose own bounding box is `width` x `height` counts as a "small mark" - see\n'
            '/// SMALL_MARK_MAX_LENGTH.\n'
            'static auto isSmallMark(double width, double height) -> bool { return std::max(width, height) < SMALL_MARK_MAX_LENGTH; }\n\n'
            '/**\n'
            ' * True if `stroke` matches the exact point pattern produced by Control::insertCross() (see\n'
            ' * createFloatingMark()/insertCross() in Control.cpp): exactly 5 points forming two perpendicular\n'
            ' * diagonals of equal arm length, crossing at the middle point of the list. There is no persisted\n'
            ' * "this is a cross" flag in the data model (unlike ArrowKind for arrows), so this is a geometric\n'
            ' * deduction, same spirit as the arrow-shaft detection used elsewhere in this file before ArrowKind\n'
            ' * existed. A false positive would require another stroke to coincidentally match this exact\n'
            ' * geometry, which is vanishingly unlikely for anything not created by insertCross() itself.\n'
            ' */\n'
            'static auto isCrossShape(const Stroke* stroke) -> bool {\n'
            '    if (stroke == nullptr || stroke->getPointCount() != 5) {\n'
            '        return false;\n'
            '    }\n'
            '    const Point* p = stroke->getPoints();\n'
            '    constexpr double EPS = 0.01;\n'
            '    Point mid1((p[0].x + p[1].x) / 2, (p[0].y + p[1].y) / 2);\n'
            '    Point mid2((p[3].x + p[4].x) / 2, (p[3].y + p[4].y) / 2);\n'
            '    if (std::abs(mid1.x - p[2].x) > EPS || std::abs(mid1.y - p[2].y) > EPS) {\n'
            '        return false;\n'
            '    }\n'
            '    if (std::abs(mid2.x - p[2].x) > EPS || std::abs(mid2.y - p[2].y) > EPS) {\n'
            '        return false;\n'
            '    }\n'
            '    double d1x = p[1].x - p[0].x;\n'
            '    double d1y = p[1].y - p[0].y;\n'
            '    double d2x = p[4].x - p[3].x;\n'
            '    double d2y = p[4].y - p[3].y;\n'
            '    if (std::abs(d1x * d2x + d1y * d2y) > EPS) {\n'
            '        return false;  // the two diagonals must be perpendicular\n'
            '    }\n'
            '    double len0 = std::hypot(p[0].x - p[2].x, p[0].y - p[2].y);\n'
            '    double len1 = std::hypot(p[1].x - p[2].x, p[1].y - p[2].y);\n'
            '    double len3 = std::hypot(p[3].x - p[2].x, p[3].y - p[2].y);\n'
            '    double len4 = std::hypot(p[4].x - p[2].x, p[4].y - p[2].y);\n'
            '    double avg = (len0 + len1 + len3 + len4) / 4;\n'
            '    if (avg < EPS) {\n'
            '        return false;\n'
            '    }\n'
            '    for (double l: {len0, len1, len3, len4}) {\n'
            '        if (std::abs(l - avg) > EPS) {\n'
            '            return false;\n'
            '        }\n'
            '    }\n'
            '    return true;\n'
            '}\n\n'
            '/**\n'
            ' * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis.\n'
            ' * `forceCenterOnly` (set by the caller for a "small mark" or a cross - see SMALL_MARK_MAX_LENGTH and\n'
            ' * isCrossShape()) always collapses to the single center candidate, tagged as a genuine center match\n'
            ' * (green). Otherwise, if the box is merely "thin" on this one axis (size <= THIN_AXIS_THRESHOLD,\n'
            ' * e.g. the thickness of an otherwise-long horizontal or vertical line), the single candidate is\n'
            ' * still returned, but tagged as an edge match (pink) instead: there was no real edge-vs-center choice\n'
            ' * on a thin axis, so a guide line running parallel to the line it came from shouldn\'t imply a\n'
            ' * deliberate centering the way a true 3-way choice does. Otherwise, offers the normal 3 candidates.\n'
            ' * `centerFraction` (0 to 1) chooses where the center candidate sits within the box, in every branch\n'
            ' * (e.g. TEXT_Y_CENTER_FRACTION only has any effect because of this).\n'
            ' */\n'
            'static auto buildCandidates(double from, double size, double centerFraction = 0.5, bool forceCenterOnly = false)\n'
            '        -> std::vector<AlignmentCandidate> {\n'
            '    if (forceCenterOnly) {\n'
            '        return {{from + size * centerFraction, true}};\n'
            '    }\n'
            '    if (size <= THIN_AXIS_THRESHOLD) {\n'
            '        return {{from + size * centerFraction, false}};\n'
            '    }\n'
            '    return {{from, false}, {from + size * centerFraction, true}, {from + size, false}};\n'
            '}\n',
        label="EditSelection.cpp: reecriture buildCandidates() + isSmallMark()/isCrossShape()",
    )

    # ============ 2. findAlignmentY self ============
    ok &= apply_edit(
        cpp,
        old='    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);',
        new='    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height, 0.5, isSmallMark(xRight - xLeft, height));',
        label="EditSelection.cpp: findAlignmentY - self",
    )

    # ============ 3. findAlignmentY other (2 occurrences identiques) ============
    text = cpp.read_text(encoding="utf-8")
    old_y_other = 'std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);'
    new_y_other = ('std::vector<AlignmentCandidate> candidatesOther = buildCandidates(\n'
                   '                snapped.y, snapped.height, otherCenterFraction,\n'
                   '                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));')
    n = text.count(old_y_other)
    if n == 2:
        text = text.replace(old_y_other, new_y_other)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: findAlignmentY - other ({n} occurrences)")
    elif text.count(new_y_other) > 0:
        print("[SKIP]  EditSelection.cpp: findAlignmentY - other deja a jour.")
    else:
        print(f"[ECHEC] EditSelection.cpp: findAlignmentY - other - motif trouve {n} fois (attendu 2)")
        ok = False

    # ============ 4. findAlignmentX self ============
    ok &= apply_edit(
        cpp,
        old='    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);',
        new='    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width, 0.5, isSmallMark(width, yBottom - yTop));',
        label="EditSelection.cpp: findAlignmentX - self",
    )

    # ============ 5. findAlignmentX other (2 occurrences identiques) ============
    text = cpp.read_text(encoding="utf-8")
    old_x_other = 'std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);'
    new_x_other = ('std::vector<AlignmentCandidate> candidatesOther = buildCandidates(\n'
                   '                snapped.x, snapped.width, 0.5,\n'
                   '                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));')
    n = text.count(old_x_other)
    if n == 2:
        text = text.replace(old_x_other, new_x_other)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: findAlignmentX - other ({n} occurrences)")
    elif text.count(new_x_other) > 0:
        print("[SKIP]  EditSelection.cpp: findAlignmentX - other deja a jour.")
    else:
        print(f"[ECHEC] EditSelection.cpp: findAlignmentX - other - motif trouve {n} fois (attendu 2)")
        ok = False

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
