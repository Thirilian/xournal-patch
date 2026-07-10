#!/usr/bin/env python3
"""
Patch 11.4.2 : CORRECTIF - le patch 11.4 (partage 60/20/20 + coupure de
desnappage) provoquait une oscillation Top -> Middle -> Top -> desnap en
glissant progressivement dans une seule direction, au lieu du
comportement fluide et monotone attendu.

CAUSE : `signedOffset` (qui pilote la decision de zone/desnappage)
etait calcule a partir de `selfAnchorY`/`selfAnchorX` - un point qui
n'est PAS stable : c'est un choix discret entre le centre de la ligne,
son bord haut ou son bord bas, qui peut basculer d'une frame a l'autre
des que le "meilleur" point d'ancrage virtuel change (mecanisme
preexistant du patch 8.6.4.6). Ce saut discontinu (jusqu'a la moitie de
la longueur de la ligne) provoquait des retours en arriere non-monotones
dans le calcul de zone - invisible avec l'ancien systeme symetrique
(1/3-1/3-1/3, sans biais ni coupure nette), mais tres visible avec le
nouveau systeme du patch 11.4.

CORRECTIF : `signedOffset` utilise desormais le centre geometrique
STABLE de la ligne (candidateY/X + hauteur/largeur / 2), inchange
d'une frame a l'autre independamment du mecanisme de bascule -
uniquement pour la decision de zone/desnappage. Le decalage d'accroche
final (refPointY/X, matchY/X->offset) n'est PAS touche et continue
d'utiliser le point d'ancrage le plus pertinent comme avant.

Corrige aussi un avertissement de compilation collateral :
selfAnchorY/X deviennent des variables ecrites-mais-jamais-lues suite a
ce changement - marquees explicitement (void) pour eviter l'avertissement,
sans retirer le calcul lui-meme (garde la logique de selection
d'ancrage virtuel intacte pour son autre role, le calcul de matchY/X).

Modifie : src/core/control/tools/EditSelection.cpp (3 zones)

NECESSITE : apply_alignment_snap_v90.py + apply_alignment_snap_v11_4.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """                        }
                    }
                }


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
"""
NEW_1 = """                        }
                    }
                }
                // Patch 11.4.2: selfAnchorY/X are no longer read for the zone/desnap decisions (see
                // above) - still computed for potential future use and to keep the virtual-anchor
                // selection logic self-contained, but explicitly marked unused here to avoid a
                // compiler warning.
                (void)selfAnchorY;
                (void)selfAnchorX;


                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on
"""
OLD_2 = """                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
"""
NEW_2 = """                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    // Patch 11.4.2: uses self's stable geometric center here, NOT selfAnchorY (which
                    // can jump discontinuously between self's center/top-edge/bottom-edge from one
                    // frame to the next, whenever the \"best\" virtual anchor above switches) - zone and
                    // desnap decisions need a smooth, monotonic reference as the cursor moves, whereas
                    // selfAnchorY is only appropriate for the actual snap offset itself (refPointY,
                    // computed separately below, independent of signedOffset).
                    double signedOffset = (candidateY + height / 2) - targetCenter;
"""
OLD_3 = """                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
"""
NEW_3 = """                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    // Patch 11.4.2: see the Y-boosted branch above for the full explanation.
                    double signedOffset = (candidateX + width / 2) - targetCenter;
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
    if "desnapY" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] desnapY introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_4.py, puis relancez ce script.")
        sys.exit(1)
    if "11.4.2" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.4.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "EditSelection.cpp: selfAnchorY/X marquees (void)")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "EditSelection.cpp: signedOffset stable (branche Y-boostee)")
    ok &= apply_edit(cpp, OLD_3, NEW_3, "EditSelection.cpp: signedOffset stable (branche X-boostee)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
