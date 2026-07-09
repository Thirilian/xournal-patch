#!/usr/bin/env python3
"""
Patch 10.6A.2 : CORRECTIF d'un bug du patch 10.6A signale par
l'utilisateur.

BUG : quand "Graduation assist" est desactivee ET qu'il y a 3 lignes ou
plus deja accrochees a la meme grande ligne, le mecanisme de
"verrouillage" du patch 8.6.8 (qui fige la position de la ligne
selectionnee le long de la grande ligne, pour eviter qu'elle ne derive
visuellement pendant un changement de mode Top/Middle/Below) restait
actif SANS CONDITION - il ne verifiait pas le nouveau reglage. Resultat :
avec "Graduation assist" desactivee et 3+ lignes, les reperes de
graduation disparaissaient bien (correct), mais la ligne selectionnee ne
pouvait plus du tout glisser le long de la grande ligne (bloquee).

CORRECTIF : ce verrouillage ne s'applique desormais que si
"Graduation assist" est active - il n'a de sens qu'en complement de
l'apercu de la famille de graduation (patch 10.6A), qu'il accompagnait a
l'origine. Si desactivee, la ligne selectionnee est laissee libre de
glisser normalement le long de la grande ligne, meme avec 3+ lignes deja
presentes.

Modifie : src/core/control/tools/EditSelection.cpp (2 occurrences,
verrouillage X et Y)

NECESSITE : apply_alignment_snap_v10_6A.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_X = """                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X.
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
"""
NEW_X = """                        } else if (settings->isGraduationAssistEnabled()) {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X. Only makes sense together with
                            // the graduation/family grid preview (patch 10.6A) - if that's disabled,
                            // self is left free to slide along the big line instead of being locked.
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
"""
OLD_Y = """                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
"""
NEW_Y = """                        } else if (settings->isGraduationAssistEnabled()) {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only makes sense together with the graduation/family grid preview (patch
                            // 10.6A) - if that's disabled, self is left free to slide along the big
                            // line instead of being locked.
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
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
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "isGraduationAssistEnabled" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] isGraduationAssistEnabled introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v10_6A.py, puis relancez ce script.")
        sys.exit(1)

    ok = True
    ok &= apply_edit(cpp, OLD_X, NEW_X, "EditSelection.cpp: verrouillage X conditionne a Graduation assist")
    ok &= apply_edit(cpp, OLD_Y, NEW_Y, "EditSelection.cpp: verrouillage Y conditionne a Graduation assist")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
