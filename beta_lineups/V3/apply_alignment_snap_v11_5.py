#!/usr/bin/env python3
"""
Patch 11.5 (phase 11) : couleurs des guidelines - trois changements.

1. Le gris du palier de centrage de page (guide.isPageCenter) est
   eclairci : (0.5, 0.5, 0.5) -> (0.75, 0.75, 0.75).

2. CORRECTIF : une petite ligne boostee (bleu) sur un axe perdait son
   accroche ordinaire (rose/vert) sur l'AUTRE axe (perpendiculaire, le
   long de sa propre longueur) des que computeBlueGridX/Y trouvait une
   famille valide MAIS SANS forcer de decalage precis (cas "2 lignes
   seulement" - marqueurs indicatifs uniquement, par le propre
   commentaire de computeBlueGridX/Y). Le code ecrasait matchX/matchY a
   nullopt dans ce cas, alors qu'il aurait du le laisser intact.
   Desormais, matchX/matchY n'est reassigne QUE si le grid force
   reellement un decalage - sinon, l'accroche ordinaire deja trouvee sur
   cet axe est preservee et continue de s'afficher normalement.

3. NOUVEAU : quand Graduation assist est active mais que la famille de
   petites lignes deja accrochees a la grande ligne (3+, self incluse)
   n'est PAS une grille reguliere valide (voir patch 11.3), et que le
   curseur n'est pas pres d'une extremite non plus (glissement libre),
   le repere bleu de croisement qui s'affichait quand meme sur la
   grande ligne (matchY/matchX conserve son guide d'origine) passe
   desormais en ROUGE - pour signaler que ce repere est purement
   indicatif et que Graduation assist ne peut pas reellement verrouiller
   la position ici. Nouveau champ AlignmentGuide::isBoostedButFree
   (et son pendant AlignmentMatch::isBoostedButFree, copie a travers).

Modifie :
  - src/core/control/tools/EditSelection.h (nouveau champ
    AlignmentGuide::isBoostedButFree)
  - src/core/control/tools/EditSelection.cpp (11 zones)

NECESSITE : apply_alignment_snap_v90.py + apply_alignment_snap_v11_3.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """        bool isPageCenter = false;
        bool hasPageMargin = false;
        double pageMarginX = 0;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a"""
H_NEW0 = """        bool isPageCenter = false;
        bool hasPageMargin = false;
        double pageMarginX = 0;
        /// Patch 11.5: true if this guide indicates a boosted crossing point that Graduation assist
        /// would normally lock onto, but currently can't - because the small lines already on this
        /// big line (3+, self included) don't form a valid, regular grid (see computeBlueGridX/Y() and
        /// patch 11.3) - so self can actually be dragged freely along the big line right now, even
        /// though this guide is shown. Rendered in red instead of the usual blue, to signal this.
        bool isBoostedButFree = false;
    };

    /// Vertical guide lines (constant x), set during mouseMove() while dragging, if any. Usually a"""
CPP_OLD0 = """    bool isPageCenter = false;
    bool hasPageMargin = false;
    double pageMarginX = 0;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line"""
CPP_NEW0 = """    bool isPageCenter = false;
    bool hasPageMargin = false;
    double pageMarginX = 0;
    /// Patch 11.5: see AlignmentGuide::isBoostedButFree in EditSelection.h for the full explanation -
    /// copied through to it via the AlignmentGuide construction below.
    bool isBoostedButFree = false;
};

/// Result of a full search on one axis: the offset that was chosen, plus every guide line"""
CPP_OLD1 = """                        // (e.g. irregularly spaced), there is no family to protect either, so this
                        // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterX = candidateX + width / 2;"""
CPP_NEW1 = """                        // (e.g. irregularly spaced), there is no family to protect either, so this
                        // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterX = candidateX + width / 2;"""
CPP_OLD2 = """                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already"""
CPP_NEW2 = """                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            } else if (gridWasInvalid && matchY) {
                                // Patch 11.5: self is free to slide along the big line right now (not
                                // near an endpoint, and the existing family isn't a valid regular grid)
                                // - the crossing guide on the big line (matchY) is still shown, since
                                // self IS still boosted to it, but colored red instead of blue to signal
                                // that Graduation assist can't actually lock it in place here.
                                for (auto& g: matchY->guides) {
                                    g.isBoostedButFree = true;
                                }
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already"""
CPP_OLD3 = """                        // See the Y-boosted branch above for the full explanation of this condition.
                        // Patch 11.3: see the Y-boosted branch above for the full explanation.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterY = candidateY + height / 2;"""
CPP_NEW3 = """                        // See the Y-boosted branch above for the full explanation of this condition.
                        // Patch 11.3: see the Y-boosted branch above for the full explanation.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        bool gridWasInvalid = false;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                            gridWasInvalid = tryEndpointAnchor;
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterY = candidateY + height / 2;"""
CPP_OLD4 = """                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted"""
CPP_NEW4 = """                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            } else if (gridWasInvalid && matchX) {
                                // Patch 11.5: see the Y-boosted branch above for the full explanation.
                                for (auto& g: matchX->guides) {
                                    g.isBoostedButFree = true;
                                }
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted"""
CPP_OLD5 = """                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});
                            }
                            matchX = grid->forceOffset
                                             ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                       *grid->forceOffset - (candidateX + width / 2), {}}}
                                             : std::nullopt;
                        }
                    }
                }"""
CPP_NEW5 = """                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{pos, grid->perpendicular, grid->markerHalfLength, true});
                            }
                            if (grid->forceOffset) {
                                matchX = AlignmentSearchResult{*grid->forceOffset - (candidateX + width / 2), {}};
                            }
                            // Patch 11.5: if the grid doesn't force an offset (e.g. only 2 lines so
                            // far - \"indicative only\" markers, per computeBlueGridX()'s own doc
                            // comment), matchX is deliberately left untouched here, rather than being
                            // nulled out - so a genuine ordinary-tier (pink/green) match already found
                            // on self's own axis is not silently discarded just because self happens
                            // to also be boosted on the other axis.
                        }
                    }
                }"""
CPP_OLD6 = """                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});
                            }
                            matchY = grid->forceOffset
                                             ? std::optional<AlignmentSearchResult>{AlignmentSearchResult{
                                                       *grid->forceOffset - (candidateY + height / 2), {}}}
                                             : std::nullopt;
                        }
                    }
                }"""
CPP_NEW6 = """                                this->activeBlueGridMarkers.push_back(
                                        BlueGridMarker{grid->perpendicular, pos, grid->markerHalfLength, false});
                            }
                            if (grid->forceOffset) {
                                matchY = AlignmentSearchResult{*grid->forceOffset - (candidateY + height / 2), {}};
                            }
                            // Patch 11.5: see the X-axis case above for the full explanation.
                        }
                    }
                }"""
CPP_OLD7 = """                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX});
                    }
                } else {
                    this->activeGuidesX.clear();"""
CPP_NEW7 = """                    this->activeGuidesX.clear();
                    for (auto& g: matchX->guides) {
                        this->activeGuidesX.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX, g.isBoostedButFree});
                    }
                } else {
                    this->activeGuidesX.clear();"""
CPP_OLD8 = """                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX});
                    }
                } else {
                    this->activeGuidesY.clear();"""
CPP_NEW8 = """                    this->activeGuidesY.clear();
                    for (auto& g: matchY->guides) {
                        this->activeGuidesY.push_back(
                                AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.isTableCenter, g.selfIsCenter, g.otherIsCenter, g.selfOnFromSide, g.equidistantGaps, g.equidistantPlacement, g.isPageCenter, g.hasPageMargin, g.pageMarginX, g.isBoostedButFree});
                    }
                } else {
                    this->activeGuidesY.clear();"""
CPP_OLD9 = """        for (auto& guide: this->activeGuidesX) {
            double gx = guide.coordinate * zoom;
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            } else if (guide.isPageCenter) {
                cairo_set_source_rgb(cr, 0.5, 0.5, 0.5);  // gray
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);"""
CPP_NEW9 = """        for (auto& guide: this->activeGuidesX) {
            double gx = guide.coordinate * zoom;
            if (guide.isBoosted) {
                if (guide.isBoostedButFree) {
                    cairo_set_source_rgb(cr, 0.9, 0.1, 0.1);  // red: boosted crossing shown, but
                                                               // Graduation assist can't lock here
                                                               // (patch 11.5, see patch 11.3)
                } else {
                    cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                }
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);
            } else if (guide.isPageCenter) {
                cairo_set_source_rgb(cr, 0.75, 0.75, 0.75);  // light gray
                cairo_move_to(cr, gx, guide.from * zoom);
                cairo_line_to(cr, gx, guide.to * zoom);
                cairo_stroke(cr);"""
CPP_OLD10 = """        for (auto& guide: this->activeGuidesY) {
            double gy = guide.coordinate * zoom;
            if (guide.isBoosted) {
                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);"""
CPP_NEW10 = """        for (auto& guide: this->activeGuidesY) {
            double gy = guide.coordinate * zoom;
            if (guide.isBoosted) {
                if (guide.isBoostedButFree) {
                    cairo_set_source_rgb(cr, 0.9, 0.1, 0.1);  // red: see the activeGuidesX loop above
                } else {
                    cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue
                }
                cairo_move_to(cr, guide.from * zoom, gy);
                cairo_line_to(cr, guide.to * zoom, gy);
                cairo_stroke(cr);"""


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
    h_file = Path("src/core/control/tools/EditSelection.h")
    cpp_file = Path("src/core/control/tools/EditSelection.cpp")
    for p in (h_file, cpp_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "tryEndpointAnchor" not in cpp_file.read_text(encoding="utf-8"):
        print("[ECHEC] tryEndpointAnchor introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_3.py, puis relancez ce script.")
        sys.exit(1)
    if "isBoostedButFree" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.5 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H_OLD0, H_NEW0, "h: zone 1/1")
    ok &= apply_edit(cpp_file, CPP_OLD0, CPP_NEW0, "cpp: zone 1/11")
    ok &= apply_edit(cpp_file, CPP_OLD1, CPP_NEW1, "cpp: zone 2/11")
    ok &= apply_edit(cpp_file, CPP_OLD2, CPP_NEW2, "cpp: zone 3/11")
    ok &= apply_edit(cpp_file, CPP_OLD3, CPP_NEW3, "cpp: zone 4/11")
    ok &= apply_edit(cpp_file, CPP_OLD4, CPP_NEW4, "cpp: zone 5/11")
    ok &= apply_edit(cpp_file, CPP_OLD5, CPP_NEW5, "cpp: zone 6/11")
    ok &= apply_edit(cpp_file, CPP_OLD6, CPP_NEW6, "cpp: zone 7/11")
    ok &= apply_edit(cpp_file, CPP_OLD7, CPP_NEW7, "cpp: zone 8/11")
    ok &= apply_edit(cpp_file, CPP_OLD8, CPP_NEW8, "cpp: zone 9/11")
    ok &= apply_edit(cpp_file, CPP_OLD9, CPP_NEW9, "cpp: zone 10/11")
    ok &= apply_edit(cpp_file, CPP_OLD10, CPP_NEW10, "cpp: zone 11/11")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
