#!/usr/bin/env python3
"""
Sous-patch 7.8 du systeme d'ancrage entre objets (style Canva/Figma).

Corrige un bug residuel du palier bleu : isSmallCrossingBigPerpendicular()
testait les deux orientations possibles (self vertical/other horizontal OU
self horizontal/other vertical) sans savoir sur quel axe la recherche a
lieu. Consequence : pour une paire (petit trait, grande fleche
perpendiculaire), les DEUX paliers bleus (X et Y) pouvaient se declencher
simultanement - un correct ("centrer un petit trait sur une grande ligne"),
l'autre incorrect ("le petit trait snap a la moitie du grand trait", deja
signale et cense etre exclu).

La fonction devient consciente de l'axe (CrossAxis::X ou CrossAxis::Y) :
seule UNE orientation est valide par axe, garantissant qu'une paire donnee
ne peut jamais declencher le bleu sur les deux axes a la fois.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py
  4) apply_alignment_snap_v7_6.py

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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    content = cpp.read_text(encoding="utf-8")
    if "isSmallCrossingBigPerpendicular" not in content:
        print("[ECHEC] isSmallCrossingBigPerpendicular introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1 à v7.py (+ v7_5, v7_6), puis relancez ce script.")
        sys.exit(1)
    if "CrossAxis" in content:
        print("[SKIP] Le patch 7.8 semble déjà appliqué (CrossAxis présent).")
        sys.exit(0)

    ok = True

    # ============ redéfinition de la fonction avec conscience de l'axe ============
    ok &= apply_edit(
        cpp,
        old='/**\n'
            ' * True if `self` (width x height) and `other` (width x height) are two line-like boxes (one is\n'
            ' * "thin", per THIN_AXIS_THRESHOLD, on one axis while the other is thin on the *perpendicular* axis -\n'
            ' * i.e. one roughly horizontal, one roughly vertical), `self` is shorter, along its own length, than\n'
            ' * `other` is along its own length, AND `self`\'s own length is at most PERPENDICULAR_CROSS_MAX_SELF_LENGTH\n'
            ' * - i.e. a small stroke crossing a much bigger perpendicular one, such as a short axis tick being\n'
            ' * placed onto a long axis line. Does NOT check whether they actually currently overlap in position -\n'
            ' * see rangesOverlap(), checked separately by the caller, which has the position information.\n'
            ' */\n'
            'static auto isSmallCrossingBigPerpendicular(double selfWidth, double selfHeight, double otherWidth,\n'
            '                                             double otherHeight) -> bool {\n'
            '    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;\n'
            '    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;\n\n'
            '    if (selfVertical && otherHorizontal) {\n'
            '        return selfHeight < otherWidth && selfHeight <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;\n'
            '    }\n'
            '    if (selfHorizontal && otherVertical) {\n'
            '        return selfWidth < otherHeight && selfWidth <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;\n'
            '    }\n'
            '    return false;\n'
            '}\n',
        new='/**\n'
            ' * Which axis a "perpendicular cross" check is being performed for - see\n'
            ' * isSmallCrossingBigPerpendicular(). A vertical self ticked onto a horizontal other only makes\n'
            ' * sense as a Y-axis match (aligning the tick\'s own vertical center to the long line\'s flat\n'
            ' * position); a horizontal self ticked onto a vertical other only makes sense as an X-axis match.\n'
            ' * The opposite pairing for a given axis (e.g. a horizontal self matched to a vertical other on the\n'
            ' * Y axis) would mean "snap this small stroke to the middle of the big one\'s own length" - not a\n'
            ' * meaningful crossing, and specifically the behavior this axis restriction excludes.\n'
            ' */\n'
            'enum class CrossAxis { X, Y };\n\n'
            '/**\n'
            ' * True if `self` (width x height) and `other` (width x height) form a meaningful "small stroke\n'
            ' * crossing a big perpendicular stroke" relationship *for the given axis* (see CrossAxis): one is\n'
            ' * "thin" per THIN_AXIS_THRESHOLD on one axis while the other is thin on the *perpendicular* axis,\n'
            ' * `self` is shorter, along its own length, than `other` is along its own length, and `self`\'s own\n'
            ' * length is at most PERPENDICULAR_CROSS_MAX_SELF_LENGTH - i.e. a short axis tick being placed onto a\n'
            ' * long axis line. Only ONE of the two possible orientations is valid per axis (see CrossAxis docs),\n'
            ' * so a given (self, other) pair can be eligible on at most one axis at a time - never both at once.\n'
            ' * Does NOT check whether they actually currently overlap in position - see rangesOverlap(), checked\n'
            ' * separately by the caller, which has the position information.\n'
            ' */\n'
            'static auto isSmallCrossingBigPerpendicular(double selfWidth, double selfHeight, double otherWidth,\n'
            '                                             double otherHeight, CrossAxis axis) -> bool {\n'
            '    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;\n'
            '    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;\n\n'
            '    if (axis == CrossAxis::Y) {\n'
            '        return selfVertical && otherHorizontal && selfHeight < otherWidth &&\n'
            '               selfHeight <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;\n'
            '    }\n'
            '    return selfHorizontal && otherVertical && selfWidth < otherHeight &&\n'
            '           selfWidth <= PERPENDICULAR_CROSS_MAX_SELF_LENGTH;\n'
            '}\n',
        label="EditSelection.cpp: isSmallCrossingBigPerpendicular devient consciente de l'axe",
    )

    # ============ mise à jour des 6 appels ============
    replacements = [
        ('isSmallCrossingBigPerpendicular(xRight - xLeft, height, shaft.width, shaft.height)',
         'isSmallCrossingBigPerpendicular(xRight - xLeft, height, shaft.width, shaft.height, CrossAxis::Y)',
         "findAlignmentY palier bleu"),
        ('isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height)',
         'isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y)',
         "findAlignmentY palier ordinaire (2 occurrences)"),
        ('isSmallCrossingBigPerpendicular(width, yBottom - yTop, shaft.width, shaft.height)',
         'isSmallCrossingBigPerpendicular(width, yBottom - yTop, shaft.width, shaft.height, CrossAxis::X)',
         "findAlignmentX palier bleu"),
        ('isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height)',
         'isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height, CrossAxis::X)',
         "findAlignmentX palier ordinaire (2 occurrences)"),
    ]

    text = cpp.read_text(encoding="utf-8")
    for old, new, label in replacements:
        n = text.count(old)
        if n == 0:
            if text.count(new) > 0:
                print(f"[SKIP]  {label}: déjà appliqué.")
                continue
            print(f"[ECHEC] {label}: motif introuvable")
            ok = False
            continue
        text = text.replace(old, new)
        print(f"[OK]    {label}: {n} occurrence(s) mise(s) à jour")
    cpp.write_text(text, encoding="utf-8")

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
