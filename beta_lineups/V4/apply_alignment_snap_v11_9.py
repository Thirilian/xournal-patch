#!/usr/bin/env python3
"""
Patch 11.9 (phase alignment_snap) : nouveau cas pour l'alignement
"jaune" deja existant (findTableCenterX/Y, "table center" - Text/
TexImage/Image centre entre deux lignes paralleles de meme longueur,
priorite absolue sur son axe).

Ajoute un second declencheur, en plus des "deux lignes paralleles de
meme longueur" deja gere : le cas d'une "case a 3 bords" - deux lignes
d'un type (verticales ou horizontales, de longueurs QUELCONQUES cette
fois) plus EXACTEMENT une ligne de l'autre type. Le cote manquant est
ferme par l'extremite propre de la ligne perpendiculaire adjacente
(meme regle - "regle 5" - que celle de la serie table_writing_assist,
mais reimplementee ici de facon totalement independante, sans aucune
dependance de code entre les deux series de patchs), en suivant
fidelement la preference exacte de cette regle (toujours privilegier
le haut, puis le bas / toujours privilegier la gauche, puis la droite).

CORRECTIF (remplace la toute premiere version de ce patch) : la
guideline doit avoir la longueur de la ligne EXISTANTE parallele a
l'axe de snap - exactement comme le cas "deux lignes" deja en place -
et non une etendue derivee des lignes perpendiculaires. L'etendue du
guide (spanFrom/spanTo) correspond desormais toujours a la longueur
propre de l'unique ligne parallele reellement presente.

Utilise exactement le meme mecanisme "isTableCenter" deja en place :
meme guideline jaune, meme priorite absolue (remplace entierement tout
match ordinaire/equidistant sur son axe), aucun changement necessaire
ailleurs dans le fichier.

Modifie : src/core/control/tools/EditSelection.cpp (2 zones :
findTableCenterX et findTableCenterY)

NECESSITE : apply_alignment_snap_v90_4.py (+ 11.6, 11.7 selon votre
process de travail actuel)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD0 = """                double spanTo = std::min(left.y + left.height, right.y + right.height);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }
    return best;
}

/// Same as findTableCenterX(), but for two horizontal lines bounding a table row, centering the
/// textbox vertically between them.
static auto findTableCenterY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"""
NEW0 = """                double spanTo = std::min(left.y + left.height, right.y + right.height);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }

    // Patch 11.9: independently reimplements the \"3-sided cell\" concept from the (separate)
    // table_writing_assist patch series - NOT a code dependency, just the same geometric rule (patch
    // 12.4's rule 5 there): a cell missing exactly one of its 4 sides has that side closed off by the
    // matching endpoint of whichever adjacent perpendicular line was found. Here specifically: the
    // nearest top/bottom horizontals (any lengths) plus exactly one of left/right - the missing one
    // is closed off, giving a well-defined cell center even with only 3 sides drawn. Competes for
    // `best` exactly like the search above (an additional case of the same already-implemented
    // \"table center\" alignment, not a new tier). The guide's own extent, like the search above,
    // always matches the length of whichever single vertical line is actually present (the one
    // parallel to this axis) - never derived from the perpendicular top/bottom lines.
    {
        double selfY = (yTop + yBottom) / 2.0;
        double leftX = -std::numeric_limits<double>::infinity();
        double rightX = std::numeric_limits<double>::infinity();
        double topY = -std::numeric_limits<double>::infinity();
        double bottomY = std::numeric_limits<double>::infinity();
        bool hasLeft = false;
        bool hasRight = false;
        bool hasTop = false;
        bool hasBottom = false;
        xoj::util::Rectangle<double> leftLine;
        xoj::util::Rectangle<double> rightLine;
        xoj::util::Rectangle<double> topLine;
        xoj::util::Rectangle<double> bottomLine;
        for (auto& elPtr: layer->getElements()) {
            const Element* el = elPtr.get();
            if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
            bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
            if (isVertical && shaft.y <= selfY && selfY <= shaft.y + shaft.height) {
                double lineX = shaft.x + shaft.width / 2.0;
                if (lineX <= selfCenter && lineX > leftX) {
                    leftX = lineX;
                    hasLeft = true;
                    leftLine = shaft;
                } else if (lineX > selfCenter && lineX < rightX) {
                    rightX = lineX;
                    hasRight = true;
                    rightLine = shaft;
                }
            } else if (isHorizontal && shaft.x <= selfCenter && selfCenter <= shaft.x + shaft.width) {
                double lineY = shaft.y + shaft.height / 2.0;
                if (lineY <= selfY && lineY > topY) {
                    topY = lineY;
                    hasTop = true;
                    topLine = shaft;
                } else if (lineY > selfY && lineY < bottomY) {
                    bottomY = lineY;
                    hasBottom = true;
                    bottomLine = shaft;
                }
            }
        }
        if (hasTop && hasBottom && (hasLeft != hasRight)) {
            auto rectanglesIntersect = [](const xoj::util::Rectangle<double>& a,
                                           const xoj::util::Rectangle<double>& b) {
                return a.x <= b.x + b.width && a.x + a.width >= b.x && a.y <= b.y + b.height &&
                       a.y + a.height >= b.y;
            };
            bool consistent = (!hasLeft || rectanglesIntersect(topLine, leftLine)) &&
                              (!hasLeft || rectanglesIntersect(bottomLine, leftLine)) &&
                              (!hasRight || rectanglesIntersect(topLine, rightLine)) &&
                              (!hasRight || rectanglesIntersect(bottomLine, rightLine));
            if (consistent) {
                if (!hasRight) {
                    rightX = topLine.x + topLine.width;
                }
                if (!hasLeft) {
                    leftX = topLine.x;
                }
                double midpoint = (leftX + rightX) / 2.0;
                double dist = std::abs(selfCenter - midpoint);
                if (dist < bestDist) {
                    bestDist = dist;
                    const auto& presentLine = hasLeft ? leftLine : rightLine;
                    double spanFrom = presentLine.y;
                    double spanTo = presentLine.y + presentLine.height;
                    best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                    best->isTableCenter = true;
                }
            }
        }
    }

    return best;
}

/// Same as findTableCenterX(), but for two horizontal lines bounding a table row, centering the
/// textbox vertically between them.
static auto findTableCenterY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"""
OLD1 = """                double spanTo = std::min(top.x + top.width, bottom.x + bottom.width);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }
    return best;
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance,
                            double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                            double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, Layer* layer,"""
NEW1 = """                double spanTo = std::min(top.x + top.width, bottom.x + bottom.width);
                best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                best->isTableCenter = true;
            }
        }
    }

    // Patch 11.9: see findTableCenterX()'s own comment for the full explanation - mirrored here for
    // the Y axis: nearest left/right verticals (any lengths) plus exactly one of top/bottom, the
    // missing one closed off via the same rule. The guide's own extent always matches the length of
    // whichever single horizontal line is actually present (the one parallel to this axis) - never
    // derived from the perpendicular left/right lines.
    {
        double selfX = (xLeft + xRight) / 2.0;
        double leftX = -std::numeric_limits<double>::infinity();
        double rightX = std::numeric_limits<double>::infinity();
        double topY = -std::numeric_limits<double>::infinity();
        double bottomY = std::numeric_limits<double>::infinity();
        bool hasLeft = false;
        bool hasRight = false;
        bool hasTop = false;
        bool hasBottom = false;
        xoj::util::Rectangle<double> leftLine;
        xoj::util::Rectangle<double> rightLine;
        xoj::util::Rectangle<double> topLine;
        xoj::util::Rectangle<double> bottomLine;
        for (auto& elPtr: layer->getElements()) {
            const Element* el = elPtr.get();
            if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {
                continue;
            }
            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
            bool isVertical = shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
            bool isHorizontal = shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
            if (isVertical && shaft.y <= selfCenter && selfCenter <= shaft.y + shaft.height) {
                double lineX = shaft.x + shaft.width / 2.0;
                if (lineX <= selfX && lineX > leftX) {
                    leftX = lineX;
                    hasLeft = true;
                    leftLine = shaft;
                } else if (lineX > selfX && lineX < rightX) {
                    rightX = lineX;
                    hasRight = true;
                    rightLine = shaft;
                }
            } else if (isHorizontal && shaft.x <= selfX && selfX <= shaft.x + shaft.width) {
                double lineY = shaft.y + shaft.height / 2.0;
                if (lineY <= selfCenter && lineY > topY) {
                    topY = lineY;
                    hasTop = true;
                    topLine = shaft;
                } else if (lineY > selfCenter && lineY < bottomY) {
                    bottomY = lineY;
                    hasBottom = true;
                    bottomLine = shaft;
                }
            }
        }
        if (hasLeft && hasRight && (hasTop != hasBottom)) {
            auto rectanglesIntersect = [](const xoj::util::Rectangle<double>& a,
                                           const xoj::util::Rectangle<double>& b) {
                return a.x <= b.x + b.width && a.x + a.width >= b.x && a.y <= b.y + b.height &&
                       a.y + a.height >= b.y;
            };
            bool consistent = (!hasTop || rectanglesIntersect(leftLine, topLine)) &&
                              (!hasTop || rectanglesIntersect(rightLine, topLine)) &&
                              (!hasBottom || rectanglesIntersect(leftLine, bottomLine)) &&
                              (!hasBottom || rectanglesIntersect(rightLine, bottomLine));
            if (consistent) {
                if (!hasBottom) {
                    bottomY = leftLine.y + leftLine.height;
                }
                if (!hasTop) {
                    topY = leftLine.y;
                }
                double midpoint = (topY + bottomY) / 2.0;
                double dist = std::abs(selfCenter - midpoint);
                if (dist < bestDist) {
                    bestDist = dist;
                    const auto& presentLine = hasTop ? topLine : bottomLine;
                    double spanFrom = presentLine.x;
                    double spanTo = presentLine.x + presentLine.width;
                    best = AlignmentMatch{midpoint - selfCenter, midpoint, spanFrom, spanTo, true, false};
                    best->isTableCenter = true;
                }
            }
        }
    }

    return best;
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance,
                            double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                            double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, Layer* layer,"""


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
    if "isTableCenter" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] isTableCenter introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py (ou v90_4), puis relancez ce script.")
        sys.exit(1)
    if "presentLine" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.9 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD0, NEW0, "EditSelection.cpp: zone 1/2")
    ok &= apply_edit(cpp, OLD1, NEW1, "EditSelection.cpp: zone 2/2")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
