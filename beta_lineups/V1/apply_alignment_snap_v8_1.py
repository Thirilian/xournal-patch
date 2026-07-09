#!/usr/bin/env python3
"""
Sous-patch 8.1 du systeme d'ancrage entre objets (style Canva/Figma).

Ajoute le snapping equidistant ("equal spacing") : en deplacant un objet,
si le placer adjacent a l'un de deux autres elements deja presents sur la
page reproduirait exactement le meme ecart que celui qui separe deja ces
deux elements entre eux, l'objet s'accroche a cette position - exactement
le comportement des "smart guides" de Figma/Canva.

Portee de cette v1 (limitations volontaires) :
  - Ne couvre que le cas "prolonger un rythme existant" (self se place a
    cote de l'un des deux objets, cote oppose a l'autre). Le cas "inserer
    self ENTRE B et C en repartissant l'ecart en deux parts egales" n'est
    PAS couvert (amelioration future possible).
  - Les deux objets de reference doivent se chevaucher (avec le rectangle
    du curseur mobile) sur l'axe perpendiculaire - meme regle que le reste
    du systeme (rangesOverlap), pas besoin d'alignement parfait.
  - Utilise la meme tolerance que le reste du systeme
    (ALIGNMENT_SNAP_TOLERANCE_PX).
  - Toujours affiche en ROSE (ni centre, ni bord, ni le cas bleu du
    croisement perpendiculaire).
  - Ne prend jamais le pas sur le palier bleu (exclusif) ; sur chaque axe,
    concurrence uniquement le palier ordinaire (offset le plus proche
    gagne).

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

NEW_FUNCTIONS = """/**
 * Equidistant ("equal spacing") snapping: if the moving box, placed at x (width wide), would end up
 * adjacent to one of two other elements B and C on `layer`, at exactly the same gap that already
 * separates B and C from each other, returns the match (offset to apply, and a guide spanning from
 * the moving box to the far element). Covers extending an existing rhythm at either end (self-B-C or
 * B-C-self); does not cover inserting self *between* B and C by bisecting their gap. B and C are only
 * considered together if a single horizontal line could pass through the moving box and both of them
 * (their Y-extents, together with [yTop, yBottom], must have a common intersection) - same
 * "overlap on the perpendicular axis" rule used elsewhere, not requiring perfect alignment.
 * Always renders pink (this is not an edge/center anchor match, just reused for visual consistency).
 */
static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {
            candidates.push_back(el);
        }
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.x + bb.width > cb.x) {
                continue;  // only consider b strictly to the left of c (each pair handled once)
            }
            double gap = cb.x - (bb.x + bb.width);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({yTop, bb.y, cb.y});
            double minEnd = std::min({yBottom, bb.y + bb.height, cb.y + cb.height});
            if (maxStart > minEnd) {
                continue;
            }

            // self extends the row on the left: self, b, c
            double unionFrom = std::min({yTop, bb.y, cb.y});
            double unionTo = std::max({yBottom, bb.y + bb.height, cb.y + cb.height});
            double targetLeft = bb.x - gap - width;
            double distLeft = std::abs(targetLeft - x);
            if (distLeft < bestDist) {
                bestDist = distLeft;
                best = AlignmentMatch{targetLeft - x, targetLeft, unionFrom, unionTo, false, false};
            }
            // self extends the row on the right: b, c, self
            double targetRight = cb.x + cb.width + gap;
            double distRight = std::abs(targetRight - x);
            if (distRight < bestDist) {
                bestDist = distRight;
                best = AlignmentMatch{targetRight - x, targetRight, unionFrom, unionTo, false, false};
            }
        }
    }
    return best;
}

/// Same as findEquidistantX(), but along the vertical axis (stacking a row top-to-bottom).
static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,
                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {
    std::vector<const Element*> candidates;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();
        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {
            candidates.push_back(el);
        }
    }

    std::optional<AlignmentMatch> best;
    double bestDist = tolerance;

    for (const Element* b: candidates) {
        for (const Element* c: candidates) {
            if (b == c) {
                continue;
            }
            xoj::util::Rectangle<double> bb = b->getSnappedBounds();
            xoj::util::Rectangle<double> cb = c->getSnappedBounds();
            if (bb.y + bb.height > cb.y) {
                continue;
            }
            double gap = cb.y - (bb.y + bb.height);
            if (gap <= 0) {
                continue;
            }
            double maxStart = std::max({xLeft, bb.x, cb.x});
            double minEnd = std::min({xRight, bb.x + bb.width, cb.x + cb.width});
            if (maxStart > minEnd) {
                continue;
            }

            double unionFrom = std::min({xLeft, bb.x, cb.x});
            double unionTo = std::max({xRight, bb.x + bb.width, cb.x + cb.width});
            double targetTop = bb.y - gap - height;
            double distTop = std::abs(targetTop - y);
            if (distTop < bestDist) {
                bestDist = distTop;
                best = AlignmentMatch{targetTop - y, targetTop, unionFrom, unionTo, false, false};
            }
            double targetBottom = cb.y + cb.height + gap;
            double distBottom = std::abs(targetBottom - y);
            if (distBottom < bestDist) {
                bestDist = distBottom;
                best = AlignmentMatch{targetBottom - y, targetBottom, unionFrom, unionTo, false, false};
            }
        }
    }
    return best;
}

"""

ANCHOR = """/**
 * Searches for alignment matches of the moving box's y-candidates (see buildCandidates()) against
 * every other element on `layer` (elements in `excluded` are always skipped, i.e. the elements
 * currently being moved; elements whose *visual* bounding box doesn't currently intersect
 * `visibleRect` are ignored, i.e. scrolled out of view).
 *
 * First looks for a "boosted" perpendicular-cross center match (see isSmallCrossingBigPerpendicular());
 * if one is found, it is returned alone (a single blue guide), ignoring every
 * other possible match on this axis entirely.
 *
 * Otherwise, finds the single closest ordinary match (center or edge, computed from each element's
 * *snapped* bounds - Element::getSnappedBounds() - rather than its visual bounds, so a selected
 * element's own candidates line up exactly with an identical, unselected element's; a Text element's
 * center candidate uses TEXT_Y_CENTER_FRACTION instead of the true geometric center). Once that
 * match's offset is known, a second pass collects every other match - possibly against different
 * elements too - that the *same* offset would also satisfy, so e.g. two identically-sized objects
 * whose top, center and bottom all align at once are all drawn, not just one of them.
 *
 * xLeft/xRight are the moving box's horizontal extent, used both for the crossing/overlap check and
 * to compute each guide line's span (perpendicular axis).
 */
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


def insert_before_anchor(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "findEquidistantX" in text:
        print("[SKIP]  EditSelection.cpp: fonctions findEquidistantX/Y deja presentes.")
        return True
    idx = text.find(ANCHOR)
    if idx == -1:
        print("[ECHEC] EditSelection.cpp: ancre du commentaire findAlignmentY introuvable.")
        print("        Assurez-vous d'avoir applique v1 a v7_9 au prealable.")
        return False
    if text.count(ANCHOR) > 1:
        print("[ECHEC] EditSelection.cpp: ancre trouvee plusieurs fois (devrait etre unique).")
        return False
    new_text = text[:idx] + NEW_FUNCTIONS + text[idx:]
    path.write_text(new_text, encoding="utf-8")
    print("[OK]    EditSelection.cpp: ajout de findEquidistantX/Y")
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

    ok = True
    ok &= insert_before_anchor(cpp)

    ok &= apply_edit(
        cpp,
        old="                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n"
            "                                              this->sourceLayer, excluded, visibleRect);\n"
            "                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n"
            "                                              this->sourceLayer, excluded, visibleRect);\n\n",
        new="                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,\n"
            "                                              this->sourceLayer, excluded, visibleRect);\n"
            "                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,\n"
            "                                              this->sourceLayer, excluded, visibleRect);\n\n"
            "                // Equidistant (\"equal spacing\") snapping competes with the ordinary alignment match on\n"
            "                // each axis, whichever is closer wins; it never overrides a boosted (blue) match.\n"
            "                bool matchXIsBoosted = matchX && !matchX->guides.empty() && matchX->guides.front().isBoosted;\n"
            "                bool matchYIsBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;\n\n"
            "                if (!matchXIsBoosted) {\n"
            "                    if (auto equidistantX = findEquidistantX(candidateX, width, candidateY, candidateY + height,\n"
            "                                                              tolerance, this->sourceLayer, excluded)) {\n"
            "                        if (!matchX || std::abs(equidistantX->offset) < std::abs(matchX->offset)) {\n"
            "                            matchX = AlignmentSearchResult{equidistantX->offset, {*equidistantX}};\n"
            "                        }\n"
            "                    }\n"
            "                }\n"
            "                if (!matchYIsBoosted) {\n"
            "                    if (auto equidistantY = findEquidistantY(candidateY, height, candidateX, candidateX + width,\n"
            "                                                              tolerance, this->sourceLayer, excluded)) {\n"
            "                        if (!matchY || std::abs(equidistantY->offset) < std::abs(matchY->offset)) {\n"
            "                            matchY = AlignmentSearchResult{equidistantY->offset, {*equidistantY}};\n"
            "                        }\n"
            "                    }\n"
            "                }\n\n",
        label="EditSelection.cpp: integration equidistant dans mouseMove()",
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
