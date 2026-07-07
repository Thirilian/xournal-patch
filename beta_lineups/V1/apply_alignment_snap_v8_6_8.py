#!/usr/bin/env python3
"""
Patch 8.6.8 (depend de 8.6.5, compatible avec 8.6.6/8.6.7) : deux
corrections/ajouts.

1) Lors d'une transition de mode (Top/Middle/Below) alors que 3 lignes ou
   plus sont deja accrochees sur la grande ligne (donc les ancrages
   d'extremite du patch 8.6.5 ne s'appliquent pas), la ligne selectionnee
   reste desormais figee sur sa position de depart (X pour un cas Y-boost,
   Y pour un cas X-boost), au lieu de suivre librement la souris sur cet
   axe.

2) Toute ligne simple (fine, sans fleche) sert desormais de reference
   d'ancrage pour le palier ORDINAIRE (vert/rose) selon son PROPRE mode
   actuel, determine geometriquement (aucune donnee stockee) : si elle
   croise une grande ligne perpendiculaire et que son extremite basse
   coincide avec elle -> mode Top -> seule son extremite basse sert de
   candidat ; extremite haute qui coincide -> mode Below -> seule son
   extremite haute sert de candidat ; sinon (pas de grande ligne croisee,
   ou croisee mais centree dessus) -> mode Middle -> seul son centre sert
   de candidat, comme avant. Remplace donc, pour les lignes simples
   uniquement, les 3 candidats habituels (bord/centre/bord) par un seul.

NECESSITE :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py (+ v7_5/6/8/9.py)
  3) apply_alignment_snap_v8_6.py + v8_6_2.py + v8_6_3.py + v8_6_3_2.py + v8_6_3_3.py
  4) apply_alignment_snap_v8_6_4_5.py + v8_6_4_6.py
  5) apply_alignment_snap_v8_6_5.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_Y_ENDIF = """                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        }
"""
NEW_Y_ENDIF = """                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // "Lock X to start" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, the line-end anchors (above) don't apply - during a
                            // Top/Middle/Below mode transition, self's X position (along the big
                            // line's length) should stay exactly where it was when the drag started,
                            // rather than drifting with the raw mouse X.
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
"""
OLD_X_ENDIF = """                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        }
"""
NEW_X_ENDIF = """                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // "Lock Y to start" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
"""
HELPER_BLOCK = """/**
 * "Ordinary anchor point depends on mode" (patch 8.6.8, point 2): determines which single point
 * should represent a plain small line `el` for the ORDINARY (green/pink) tier's own candidate list,
 * instead of the usual three (near edge, center, far edge). Purely geometric, deduced fresh each
 * time from `el`'s own current shape and any big perpendicular line it happens to cross right now -
 * nothing is stored. Returns -1 if `el`'s far edge (e.g. bottom, for a vertical line) coincides with
 * a crossing big line's center (i.e. el is in "Top" mode), +1 if its near edge does ("Below" mode),
 * or 0 for every other case (not a plain line, not crossing any big line at all, or crossing one but
 * still centered on it, i.e. "Middle") - 0 means "use the ordinary center", matching the same value
 * used elsewhere for Middle.
 */
static std::optional<int> detectLineZoneForOrdinaryAnchor(const Element* el, Layer* layer,
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
/// (+1), or its ordinary center for Middle (0) - matching the "family" anchor conventions used
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
OLD_Y_CAND = """        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.y, snapped.height, otherCenterFraction,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
"""
NEW_Y_CAND = """        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.y, snapped.height, otherCenterFraction,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
"""
OLD_X_CAND = """        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(
                snapped.x, snapped.width, 0.5,
                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
"""
NEW_X_CAND = """        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {
            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);
        } else {
            candidatesOther = buildCandidates(
                    snapped.x, snapped.width, 0.5,
                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));
        }
"""


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    text = cpp.read_text(encoding="utf-8")
    if "endpointGuideActiveX" not in text:
        print("[ECHEC] endpointGuideActiveX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_6_5.py, puis relancez ce script.")
        sys.exit(1)
    if "detectLineZoneForOrdinaryAnchor" in text:
        print("[SKIP] Le patch 8.6.8 semble deja applique.")
        sys.exit(0)

    ok = True

    # ============ Correction 1: verrouillage X/Y (2 blocs, uniques) ============
    n = text.count(OLD_Y_ENDIF)
    if n == 1:
        text = text.replace(OLD_Y_ENDIF, NEW_Y_ENDIF, 1)
        print("[OK]    EditSelection.cpp: verrouillage en X (branche Y)")
    elif text.count(NEW_Y_ENDIF) == 1:
        print("[SKIP]  EditSelection.cpp: verrouillage en X deja present.")
    else:
        print(f"[ECHEC] EditSelection.cpp: bloc Y (verrouillage) trouve {n} fois (attendu 1).")
        ok = False

    n = text.count(OLD_X_ENDIF)
    if n == 1:
        text = text.replace(OLD_X_ENDIF, NEW_X_ENDIF, 1)
        print("[OK]    EditSelection.cpp: verrouillage en Y (branche X)")
    elif text.count(NEW_X_ENDIF) == 1:
        print("[SKIP]  EditSelection.cpp: verrouillage en Y deja present.")
    else:
        print(f"[ECHEC] EditSelection.cpp: bloc X (verrouillage) trouve {n} fois (attendu 1).")
        ok = False

    # ============ Correction 2a: nouvelles fonctions utilitaires ============
    anchor = "static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,"
    if "detectLineZoneForOrdinaryAnchor" in text:
        print("[SKIP]  EditSelection.cpp: fonctions utilitaires deja presentes.")
    elif text.count(anchor) != 1:
        print(f"[ECHEC] EditSelection.cpp: ancre findAlignmentY trouvee {text.count(anchor)} fois (attendu 1).")
        ok = False
    else:
        idx = text.find(anchor)
        text = text[:idx] + HELPER_BLOCK + text[idx:]
        print("[OK]    EditSelection.cpp: ajout de detectLineZoneForOrdinaryAnchor/buildForcedLineCandidate")

    # ============ Correction 2b/c: remplacement des 4 sites candidatesOther ============
    # Le texte exact varie selon que le patch 9.1 (isSmallMark/isCrossShape) est applique ou non -
    # les deux variantes sont gerees ici.
    has_9_1_form = "isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el))" in text

    if has_9_1_form:
        old_y_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(\n"
            "                snapped.y, snapped.height, otherCenterFraction,\n"
            "                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));\n"
        )
        new_y_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther;\n"
            "        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {\n"
            "            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);\n"
            "        } else {\n"
            "            candidatesOther = buildCandidates(\n"
            "                    snapped.y, snapped.height, otherCenterFraction,\n"
            "                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));\n"
            "        }\n"
        )
        old_x_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(\n"
            "                snapped.x, snapped.width, 0.5,\n"
            "                isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));\n"
        )
        new_x_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther;\n"
            "        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {\n"
            "            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);\n"
            "        } else {\n"
            "            candidatesOther = buildCandidates(\n"
            "                    snapped.x, snapped.width, 0.5,\n"
            "                    isSmallMark(snapped.width, snapped.height) || isCrossShape(dynamic_cast<const Stroke*>(el)));\n"
            "        }\n"
        )
    else:
        old_y_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n"
        )
        new_y_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther;\n"
            "        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {\n"
            "            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);\n"
            "        } else {\n"
            "            candidatesOther = buildCandidates(snapped.y, snapped.height, otherCenterFraction);\n"
            "        }\n"
        )
        old_x_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n"
        )
        new_x_cand = (
            "        std::vector<AlignmentCandidate> candidatesOther;\n"
            "        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded)) {\n"
            "            candidatesOther = buildForcedLineCandidate(snapped.x, snapped.width, *lineZone);\n"
            "        } else {\n"
            "            candidatesOther = buildCandidates(snapped.x, snapped.width);\n"
            "        }\n"
        )

    n_y = text.count(old_y_cand)
    if n_y == 2:
        text = text.replace(old_y_cand, new_y_cand)
        print("[OK]    EditSelection.cpp: candidatesOther (axe Y) utilise le mode de la ligne (2 occurrences)")
    elif text.count(new_y_cand) == 2:
        print("[SKIP]  EditSelection.cpp: candidatesOther (axe Y) deja modifie.")
    else:
        print(f"[ECHEC] EditSelection.cpp: candidatesOther (axe Y) trouve {n_y} fois (attendu 2).")
        ok = False

    n_x = text.count(old_x_cand)
    if n_x == 2:
        text = text.replace(old_x_cand, new_x_cand)
        print("[OK]    EditSelection.cpp: candidatesOther (axe X) utilise le mode de la ligne (2 occurrences)")
    elif text.count(new_x_cand) == 2:
        print("[SKIP]  EditSelection.cpp: candidatesOther (axe X) deja modifie.")
    else:
        print(f"[ECHEC] EditSelection.cpp: candidatesOther (axe X) trouve {n_x} fois (attendu 2).")
        ok = False

    cpp.write_text(text, encoding="utf-8")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
