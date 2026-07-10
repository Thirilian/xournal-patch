#!/usr/bin/env python3
"""
Patch 11.5.3 (phase 11) : une petite ligne appartenant a une famille de
graduation genere desormais une guideline rose de son cote, MEME en
mode Middle (auparavant, seuls Top et Below donnaient rose ; Middle
donnait vert).

CAUSE (confirmee par 3 captures d'ecran de l'utilisateur) :
detectLineZoneForOrdinaryAnchor() retournait 0 a la fois pour "aucune
grande ligne croisee du tout" ET pour "croise une grande ligne mais
centree dessus (Middle)" - ces deux cas etaient indiscernables pour
l'appelant. Les 4 points d'appel testaient `lineZone && *lineZone != 0`,
qui exclut explicitement le cas Middle du forcage - laissant alors la
ligne utiliser le systeme normal a 3 candidats (pres/centre/loin), et
un alignement centre-a-centre y ressort donc "vert" (isCenter=true).

CORRECTIF (deux parties) :
1. detectLineZoneForOrdinaryAnchor() distingue desormais les deux cas :
   nullopt si aucune grande ligne croisee, 0 si une grande ligne EST
   croisee mais que la ligne y est centree (Middle).
2. Les 4 points d'appel testent desormais simplement lineZone.has_value()
   - des qu'une famille est detectee, meme en Middle, force le candidat
   unique.
3. buildForcedLineCandidate() : le candidat Middle (zone=0) est
   desormais tague isCenter=false (au lieu de true) - une ligne de
   famille reste rose dans les trois modes, plutot que de changer de
   couleur selon son orientation courante.

Modifie : src/core/control/tools/EditSelection.cpp (5 zones :
detectLineZoneForOrdinaryAnchor + buildForcedLineCandidate fusionnes en
1 bloc, plus 4 points d'appel)

NECESSITE : apply_alignment_snap_v90.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_FUNC = """    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
    for (auto& bigPtr: layer->getElements()) {
        const Element* big = bigPtr.get();
        if (big == el || std::find(excluded.begin(), excluded.end(), big) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> bigShaft = big->getSnappedBounds();
        if (isVertical) {
            bool bigIsHorizontal = bigShaft.height <= THIN_AXIS_THRESHOLD && bigShaft.width > THIN_AXIS_THRESHOLD;
            if (!bigIsHorizontal ||
                !rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width)) {
                continue;
            }
            double bigCenter = bigShaft.y + bigShaft.height / 2;
            double farEdge = shaft.y + shaft.height;
            double nearEdge = shaft.y;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        } else {
            bool bigIsVertical = bigShaft.width <= THIN_AXIS_THRESHOLD && bigShaft.height > THIN_AXIS_THRESHOLD;
            if (!bigIsVertical ||
                !rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height)) {
                continue;
            }
            double bigCenter = bigShaft.x + bigShaft.width / 2;
            double farEdge = shaft.x + shaft.width;
            double nearEdge = shaft.x;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        }
    }
    return 0;
}

/// Given a plain small line's own zone (see detectLineZoneForOrdinaryAnchor()), builds the single
/// forced ordinary-tier candidate representing it: its far edge for Top (-1), near edge for Below
/// (+1), or its ordinary center for Middle (0) - matching the \"family\" anchor conventions used
/// throughout the rest of this feature (patch 8.6.8).
static auto buildForcedLineCandidate(double from, double size, int zone) -> std::vector<AlignmentCandidate> {
    if (zone < 0) {
        return {{from + size, false}};
    }
    if (zone > 0) {
        return {{from, false}};
    }
    return {{from + size / 2, true}};
}
"""
NEW_FUNC = """    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
    // Patch 11.5.3: tracks whether `el` was found crossing ANY big line at all (regardless of
    // Top/Below/Middle), so the two different reasons for returning a Middle-equivalent value can be
    // told apart below - genuinely centered on a real big line (0) vs. not crossing any big line at
    // all (nullopt, unchanged from before).
    bool foundCrossingBigLine = false;
    for (auto& bigPtr: layer->getElements()) {
        const Element* big = bigPtr.get();
        if (big == el || std::find(excluded.begin(), excluded.end(), big) != excluded.end()) {
            continue;
        }
        xoj::util::Rectangle<double> bigShaft = big->getSnappedBounds();
        if (isVertical) {
            bool bigIsHorizontal = bigShaft.height <= THIN_AXIS_THRESHOLD && bigShaft.width > THIN_AXIS_THRESHOLD;
            if (!bigIsHorizontal ||
                !rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x, shaft.x + shaft.width)) {
                continue;
            }
            foundCrossingBigLine = true;
            double bigCenter = bigShaft.y + bigShaft.height / 2;
            double farEdge = shaft.y + shaft.height;
            double nearEdge = shaft.y;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        } else {
            bool bigIsVertical = bigShaft.width <= THIN_AXIS_THRESHOLD && bigShaft.height > THIN_AXIS_THRESHOLD;
            if (!bigIsVertical ||
                !rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y, shaft.y + shaft.height)) {
                continue;
            }
            foundCrossingBigLine = true;
            double bigCenter = bigShaft.x + bigShaft.width / 2;
            double farEdge = shaft.x + shaft.width;
            double nearEdge = shaft.x;
            if (std::abs(farEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return -1;
            }
            if (std::abs(nearEdge - bigCenter) < BLUE_GRID_LENGTH_EPS) {
                return 1;
            }
        }
    }
    return foundCrossingBigLine ? std::optional<int>(0) : std::nullopt;
}

/// Given a plain small line's own zone (see detectLineZoneForOrdinaryAnchor()), builds the single
/// forced ordinary-tier candidate representing it: its far edge for Top (-1), near edge for Below
/// (+1), or its own geometric center for Middle (0) - matching the \"family\" anchor conventions used
/// throughout the rest of this feature (patch 8.6.8). Patch 11.5.3: the Middle candidate is tagged
/// isCenter=false (not true) - a line that belongs to a graduation family should always render its
/// ordinary-tier guide as pink, not green, regardless of which of the three modes it happens to be
/// in right now, since all three represent the same family-anchor concept from the user's point of
/// view.
static auto buildForcedLineCandidate(double from, double size, int zone) -> std::vector<AlignmentCandidate> {
    if (zone < 0) {
        return {{from + size, false}};
    }
    if (zone > 0) {
        return {{from, false}};
    }
    return {{from + size / 2, false}};
}
"""
OLD_CALL = """if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone && *lineZone != 0) {"""
NEW_CALL = """if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {"""


def apply_edit_unique(path: Path, old: str, new: str, label: str) -> bool:
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


def apply_edit_all(path: Path, old: str, new: str, label: str, expected_count: int) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) >= expected_count:
            print(f"[SKIP]  {label}: deja applique.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count != expected_count:
        print(f"[ECHEC] {label}: motif trouve {count} fois dans {path} (attendu {expected_count})")
        return False
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "detectLineZoneForOrdinaryAnchor" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] detectLineZoneForOrdinaryAnchor introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py, puis relancez ce script.")
        sys.exit(1)
    if "foundCrossingBigLine" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.5.3 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit_unique(cpp, OLD_FUNC, NEW_FUNC, "EditSelection.cpp: detectLineZoneForOrdinaryAnchor + buildForcedLineCandidate")
    ok &= apply_edit_all(cpp, OLD_CALL, NEW_CALL, "EditSelection.cpp: 4 points d'appel", 4)

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
