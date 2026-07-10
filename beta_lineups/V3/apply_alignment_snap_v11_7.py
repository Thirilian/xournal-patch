#!/usr/bin/env python3
"""
Patch 11.7 : CORRECTIF - regression du patch 11.5.3, signalee par
l'utilisateur avec captures d'ecran ("en horizontal on a 3 guidelines
mais en vertical on en a qu'une").

CAUSE : le patch 11.5.3 forcait desormais TOUTE ligne croisant une
grande ligne perpendiculaire (meme en mode Middle) a n'offrir qu'un
seul candidat ordinaire (au lieu des 3 habituels : near/center/far),
pour garantir une guideline rose. Ce mecanisme n'a de sens que pour de
VRAIES petites graduations - mais s'appliquait aussi a des lignes
BEAUCOUP plus longues des qu'une grande ligne perpendiculaire etait
simplement presente ailleurs sur la page, reduisant a tort leurs
options d'alignement disponibles pour tout autre objet cherchant a
s'aligner dessus. Confirme par l'utilisateur : le bug ne se produit
QUE quand une ligne horizontale est aussi presente sur la page.

CORRECTIF : le mecanisme de forcage ne s'applique plus qu'aux lignes
dont la longueur est strictement inferieure a
Settings::getSmallMarkMaxLength() - les vraies petites graduations.
Une ligne plus longue retombe desormais toujours sur le systeme normal
a 3 candidats, avec ses couleurs habituelles, meme si elle croise
geometriquement une grande ligne perpendiculaire.

Modifie : src/core/control/tools/EditSelection.cpp (5 zones :
detectLineZoneForOrdinaryAnchor + ses 4 points d'appel)

NECESSITE : apply_alignment_snap_v90.py (+ 11.1 a 11.6, selon votre
process de travail actuel)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """static std::optional<int> detectLineZoneForOrdinaryAnchor(const Element* el, Layer* layer,
                                                            const std::vector<const Element*>& excluded) {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
        return std::nullopt;
    }
    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
"""
NEW_1 = """static std::optional<int> detectLineZoneForOrdinaryAnchor(const Element* el, Layer* layer,
                                                            const std::vector<const Element*>& excluded,
                                                            double smallMarkMaxLength) {
    const auto* stroke = dynamic_cast<const Stroke*>(el);
    if (stroke == nullptr || stroke->getArrowKind() != ArrowKind::NONE || stroke->getPointCount() != 2) {
        return std::nullopt;
    }
    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
    bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
    bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
    if (!isVertical && !isHorizontal) {
        return std::nullopt;
    }
    // Patch 11.7: this whole \"family\" mechanism (forcing a single, always-pink ordinary-tier
    // candidate for a line that crosses a big perpendicular line) is only appropriate for genuinely
    // SMALL lines (graduation ticks) - the same length bound used to decide boosted-tier eligibility
    // elsewhere (Settings::getSmallMarkMaxLength()). A longer line that happens to geometrically cross
    // some other perpendicular line keeps the normal 3-candidate (near/center/far) ordinary-tier
    // behavior and its usual colors, regardless of any \"family\" it might otherwise appear to belong
    // to - fixes a regression from patch 11.5.3, where any line crossing a big line lost 2 of its 3
    // candidates as soon as a horizontal line was also present on the page, even for lines far too
    // long to be a graduation tick.
    double lineLength = isVertical ? shaft.height : shaft.width;
    if (lineLength >= smallMarkMaxLength) {
        return std::nullopt;
    }
"""
OLD_2 = """if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {"""
NEW_2 = """if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded, smallMarkMaxLength); lineZone.has_value()) {"""


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
    if "Patch 11.7" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.7 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit_unique(cpp, OLD_1, NEW_1, "EditSelection.cpp: detectLineZoneForOrdinaryAnchor restreinte aux petites lignes")
    ok &= apply_edit_all(cpp, OLD_2, NEW_2, "EditSelection.cpp: 4 points d'appel", 4)

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
