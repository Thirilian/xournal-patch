#!/usr/bin/env python3
"""
Patch 11.4 : modifie la condition de passage entre les modes Top/Middle/
Below pour une petite ligne DEJA accrochee (boostee) au moment du clic
(this->startingWasBoosted == true).

NOUVEAU COMPORTEMENT (uniquement quand la ligne etait deja accrochee au
clic - le cas "ligne fraiche", patch 8.6.6, n'est pas touche) :

  - Les trois zones (Top/Middle/Below) occupent toujours la plage totale
    [-zoneR, +zoneR] (zoneR = tolerance * crossBoostFactor), MAIS ne
    sont plus divisees en tiers egaux (33/33/33) - un partage 60/20/20
    favorise desormais le mode dans lequel la ligne etait DEJA au clic
    (this->startingBoostedZone), rendant les transitions moins nerveuses.

  - Si le curseur sort ENTIEREMENT de la plage [-zoneR, +zoneR] (au-dela
    du haut ou du bas des trois zones reunies), la ligne est
    completement "desnapee" de cette grande ligne pour cet axe : aucun
    accroche du tout (ni bleu, ni vert/rose) tant que le curseur reste
    hors plage - permettant de faire glisser librement une petite ligne
    boostee loin de la grande ligne.

Implementation : le corps entier de chaque branche (Y-boostee et
X-boostee) est desormais enveloppe dans un if(desnap)/else, calcule des
la lecture de signedOffset/zoneR - evitant tout dereferencement de
matchX/matchY nul en aval.

Modifie : src/core/control/tools/EditSelection.cpp (4 zones)

NECESSITE : apply_alignment_snap_v90.py + apply_alignment_snap_v11_3.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD0 = """                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    this->activeBoostedTarget = yBoostedTarget;
                    this->activeBoostedIsXAxis = false;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't already
                        // boost-snapped to ANY big line when this drag started (this->startingWasBoosted
                        // == false) may not settle into Top/Below on its own just because the cursor
                        // dragged it into that zone - it must default to Middle, UNLESS other same-size,
                        // same-orientation lines are already established on THIS big line, in which case
                        // it follows their mode instead. A line that WAS already attached somewhere at
                        // mouseDown keeps full free transition between zones, as before.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = height;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == yBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isVerticalShaft =
                                        shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                                if (!isVerticalShaft ||
                                    std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                    shaft.x + shaft.width)) {
                                    continue;
                                }"""
NEW0 = """                    double targetCenter = targetShaft.y + targetShaft.height / 2;
                    double signedOffset = selfAnchorY - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    // Patch 11.4: once a line is already boosted at the moment the drag starts
                    // (this->startingWasBoosted), leaving the full [-zoneR, +zoneR] range entirely
                    // desnaps it from this big line altogether for as long as the cursor stays out
                    // of range - no boosted match on this axis at all (falls through to whatever
                    // the ordinary/equidistant tiers separately determine, or nothing).
                    bool desnapY = this->startingWasBoosted && settings->isGraduationOrientationEnabled() &&
                                   (signedOffset < -zoneR || signedOffset > zoneR);
                    if (desnapY) {
                        matchY = std::nullopt;
                    } else {
                    this->activeBoostedTarget = yBoostedTarget;
                        this->activeBoostedIsXAxis = false;
                        if (settings->isGraduationOrientationEnabled()) {
                            if (this->startingWasBoosted) {
                                // Patch 11.4: once a line was already boosted when the drag started,
                                // the three Top/Middle/Below zones are no longer split into equal
                                // thirds - instead, a 60/20/20 split favors whichever mode
                                // (this->startingBoostedZone) the line was already in at mouseDown,
                                // making it \"stickier\" and less prone to flipping accidentally.
                                double topFrac;
                                double middleFrac;
                                double belowFrac;
                                if (this->startingBoostedZone < 0) {
                                    topFrac = 0.6;
                                    middleFrac = 0.2;
                                    belowFrac = 0.2;
                                } else if (this->startingBoostedZone > 0) {
                                    topFrac = 0.2;
                                    middleFrac = 0.2;
                                    belowFrac = 0.6;
                                } else {
                                    topFrac = 0.2;
                                    middleFrac = 0.6;
                                    belowFrac = 0.2;
                                }
                                (void)middleFrac;
                                double topMiddleBoundary = -zoneR + 2 * zoneR * topFrac;
                                double middleBelowBoundary = zoneR - 2 * zoneR * belowFrac;
                                this->activeBoostedZone = (signedOffset < topMiddleBoundary)
                                                                   ? -1
                                                                   : (signedOffset > middleBelowBoundary ? 1 : 0);
                            } else {
                                this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                                // \"Fresh line\" zone override (patch 8.6.6): a small line that wasn't
                                // already boost-snapped to ANY big line when this drag started may not
                                // settle into Top/Below on its own just because the cursor dragged it
                                // into that zone - it must default to Middle, UNLESS other same-size,
                                // same-orientation lines are already established on THIS big line, in
                                // which case it follows their mode instead.
                                int familyMode = 0;
                                bool familyFound = false;
                                double selfLengthForFamily = height;
                                for (auto& elPtr: this->sourceLayer->getElements()) {
                                    Element* el = elPtr.get();
                                    if (el == yBoostedTarget) {
                                        continue;
                                    }
                                    auto* otherStroke = dynamic_cast<Stroke*>(el);
                                    if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                        continue;
                                    }
                                    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                    bool isVerticalShaft =
                                            shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                                    if (!isVerticalShaft ||
                                        std::abs(shaft.height - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                        continue;
                                    }
                                    if (!rangesOverlap(targetShaft.x, targetShaft.x + targetShaft.width, shaft.x,
                                                        shaft.x + shaft.width)) {
                                        continue;
                                    }
                                    double shaftCenterY = shaft.y + shaft.height / 2;
                                    if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                        continue;
                                    }
                                    double farEdge = shaft.y + shaft.height;
                                    double nearEdge = shaft.y;
                                    if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                        familyMode = -1;
                                    } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                        familyMode = 1;
                                    } else {
                                        familyMode = 0;
                                    }
                                    familyFound = true;
                                    break;
                                }
                                this->activeBoostedZone = familyFound ? familyMode : 0;
                            }
                        } else {
                            // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                            // cursor position - always Middle, regardless of where the cursor is or
                            // whether this line was already part of an established family.
                            this->activeBoostedZone = 0;
                        }

                        // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever
                        // reference point matches the CURRENT zone (bottom edge for -1, center for 0, top
                        // edge for +1), not always its true center - so self visually moves together with
                        // the \"family\" grid preview as the zone changes mid-drag. Guides are left as-is
                        // (still correctly flagged boosted), only the offset is replaced.
                        double refPointY;
                        if (this->activeBoostedZone < 0) {
                            refPointY = candidateY + height;
                        } else if (this->activeBoostedZone > 0) {
                            refPointY = candidateY;
                        } else {
                            refPointY = candidateY + height / 2;
                        }
                        matchY->offset = targetCenter - refPointY;

                        // \"Line-end anchors\" (patch 8.6.5): while this big line has only 1 or 2 small
                        // lines crossing it (self included), its own two endpoints become additional
                        // anchor points for self's OTHER axis (the one along the big line's length) -
                        // letting self snap so it crosses right at one end. Independent of the Y offset
                        // above; only touches matchX.
                        {
                            xoj::util::Rectangle<double> bigShaft = targetShaft;
                            int existingCount = 0;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == yBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isVerticalShaft =
                                        shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                                if (!isVerticalShaft) {
                                    continue;
                                }
                                if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x,
                                                    shaft.x + shaft.width)) {
                                    continue;
                                }"""
OLD1 = """                                if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                double farEdge = shaft.y + shaft.height;
                                double nearEdge = shaft.y;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle, regardless of where the cursor is or
                        // whether this line was already part of an established family.
                        this->activeBoostedZone = 0;
                    }

                    // Dynamic anchor (patch 8.6.4.6): self's own snapped position tracks whichever
                    // reference point matches the CURRENT zone (bottom edge for -1, center for 0, top
                    // edge for +1), not always its true center - so self visually moves together with
                    // the \"family\" grid preview as the zone changes mid-drag. Guides are left as-is
                    // (still correctly flagged boosted), only the offset is replaced.
                    double refPointY;
                    if (this->activeBoostedZone < 0) {
                        refPointY = candidateY + height;
                    } else if (this->activeBoostedZone > 0) {
                        refPointY = candidateY;
                    } else {
                        refPointY = candidateY + height / 2;
                    }
                    matchY->offset = targetCenter - refPointY;

                    // \"Line-end anchors\" (patch 8.6.5): while this big line has only 1 or 2 small
                    // lines crossing it (self included), its own two endpoints become additional
                    // anchor points for self's OTHER axis (the one along the big line's length) -
                    // letting self snap so it crosses right at one end. Independent of the Y offset
                    // above; only touches matchX.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == yBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isVerticalShaft =
                                    shaft.width <= THIN_AXIS_THRESHOLD && shaft.height > THIN_AXIS_THRESHOLD;
                            if (!isVerticalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.x, bigShaft.x + bigShaft.width, shaft.x,
                                                shaft.x + shaft.width)) {
                                continue;
                            }
                            double shaftCenterY = shaft.y + shaft.height / 2;
                            if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                continue;
                            }
                            existingCount++;
                        }
                        // Endpoint anchoring applies whenever there are at most 2 small lines
                        // (self included) crossing the big line - matching the \"1 or 2 small lines\"
                        // intent of patch 8.6.5 (existingCount counts self too, so this is
                        // existingCount <= 2, not <= 1 as originally miscoded). If \"Graduation
                        // assist\" (patch 10.6A) is disabled, this restriction is lifted entirely:
                        // endpoint anchoring then always applies, regardless of how many lines are
                        // already boosted on the big line, since there is no family/grid concept to
                        // protect from conflicting with in that case.
                        //
                        // Patch 11.3: with 3+ lines AND Graduation assist enabled, the \"Lock X to
                        // start\" branch below only makes sense if those lines actually form a valid,
                        // regular grid (see computeBlueGridX()'s own return value) - if they don't
                        // (e.g. irregularly spaced), there is no family to protect either, so this
                        // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterX = candidateX + width / 2;
                            double leftEnd = bigShaft.x;
                            double rightEnd = bigShaft.x + bigShaft.width;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                bestOffset = leftEnd - selfCenterX;
                                found = true;
                            }
                            if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                bestOffset = rightEnd - selfCenterX;
                                found = true;
                            }
                            if (found) {
                                matchX = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveX = true;
                                endpointGuideCoordX = selfCenterX + bestOffset;
                                endpointGuideFromX = candidateY + matchY->offset;
                                endpointGuideToX = candidateY + height + matchY->offset;
                            }
                        } else {
                            // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                            // on this big line, forming a valid regular grid (see the condition
                            // above), the line-end anchors don't apply - during a Top/Middle/Below
                            // mode transition, self's X position (along the big line's length) should
                            // stay exactly where it was when the drag started, rather than drifting
                            // with the raw mouse X. Only reached when \"Graduation assist\" is enabled
                            // and a valid grid was found - it only makes sense together with the
                            // graduation/family grid preview (patch 10.6A).
                            matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                        }
                    }
                } else if (xBoostedTarget != nullptr) {"""
NEW1 = """                                if (std::abs(shaftCenterY - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                existingCount++;
                            }
                            // Endpoint anchoring applies whenever there are at most 2 small lines
                            // (self included) crossing the big line - matching the \"1 or 2 small lines\"
                            // intent of patch 8.6.5 (existingCount counts self too, so this is
                            // existingCount <= 2, not <= 1 as originally miscoded). If \"Graduation
                            // assist\" (patch 10.6A) is disabled, this restriction is lifted entirely:
                            // endpoint anchoring then always applies, regardless of how many lines are
                            // already boosted on the big line, since there is no family/grid concept to
                            // protect from conflicting with in that case.
                            //
                            // Patch 11.3: with 3+ lines AND Graduation assist enabled, the \"Lock X to
                            // start\" branch below only makes sense if those lines actually form a valid,
                            // regular grid (see computeBlueGridX()'s own return value) - if they don't
                            // (e.g. irregularly spaced), there is no family to protect either, so this
                            // falls back to endpoint anchoring too, exactly as if existingCount <= 2.
                            bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                            if (!tryEndpointAnchor) {
                                auto gridCheck = computeBlueGridX(yBoostedTarget, candidateX + width / 2, width,
                                                                   this->sourceLayer, excluded);
                                tryEndpointAnchor = !gridCheck.has_value();
                            }
                            if (tryEndpointAnchor) {
                                double selfCenterX = candidateX + width / 2;
                                double leftEnd = bigShaft.x;
                                double rightEnd = bigShaft.x + bigShaft.width;
                                double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                                double bestOffset = 0;
                                bool found = false;
                                if (std::abs(selfCenterX - leftEnd) <= endpointTolerance) {
                                    bestOffset = leftEnd - selfCenterX;
                                    found = true;
                                }
                                if (std::abs(selfCenterX - rightEnd) <= endpointTolerance &&
                                    (!found || std::abs(rightEnd - selfCenterX) < std::abs(bestOffset))) {
                                    bestOffset = rightEnd - selfCenterX;
                                    found = true;
                                }
                                if (found) {
                                    matchX = AlignmentSearchResult{bestOffset, {}};
                                    endpointGuideActiveX = true;
                                    endpointGuideCoordX = selfCenterX + bestOffset;
                                    endpointGuideFromX = candidateY + matchY->offset;
                                    endpointGuideToX = candidateY + height + matchY->offset;
                                }
                            } else {
                                // \"Lock X to start\" (patch 8.6.8, point 1): with 3 or more lines already
                                // on this big line, forming a valid regular grid (see the condition
                                // above), the line-end anchors don't apply - during a Top/Middle/Below
                                // mode transition, self's X position (along the big line's length) should
                                // stay exactly where it was when the drag started, rather than drifting
                                // with the raw mouse X. Only reached when \"Graduation assist\" is enabled
                                // and a valid grid was found - it only makes sense together with the
                                // graduation/family grid preview (patch 10.6A).
                                matchX = AlignmentSearchResult{this->snappedBounds.x - candidateX, {}};
                            }
                        }
                    }
                } else if (xBoostedTarget != nullptr) {"""
OLD2 = """                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    this->activeBoostedTarget = xBoostedTarget;
                    this->activeBoostedIsXAxis = true;
                    if (settings->isGraduationOrientationEnabled()) {
                        this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                        // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted case -
                        // see the Y-branch above for the full explanation.
                        if (!this->startingWasBoosted) {
                            int familyMode = 0;
                            bool familyFound = false;
                            double selfLengthForFamily = width;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == xBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isHorizontalShaft =
                                        shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                                if (!isHorizontalShaft ||
                                    std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                    continue;
                                }
                                if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                    shaft.y + shaft.height)) {
                                    continue;
                                }"""
NEW2 = """                    double targetCenter = targetShaft.x + targetShaft.width / 2;
                    double signedOffset = selfAnchorX - targetCenter;
                    double zoneR = tolerance * settings->getPerpendicularCrossBoostFactor();
                    // Patch 11.4: see the Y-boosted branch above for the full explanation.
                    bool desnapX = this->startingWasBoosted && settings->isGraduationOrientationEnabled() &&
                                   (signedOffset < -zoneR || signedOffset > zoneR);
                    if (desnapX) {
                        matchX = std::nullopt;
                    } else {
                    this->activeBoostedTarget = xBoostedTarget;
                        this->activeBoostedIsXAxis = true;
                        if (settings->isGraduationOrientationEnabled()) {
                            if (this->startingWasBoosted) {
                                // Patch 11.4: see the Y-boosted branch above for the full explanation.
                                double topFrac;
                                double middleFrac;
                                double belowFrac;
                                if (this->startingBoostedZone < 0) {
                                    topFrac = 0.6;
                                    middleFrac = 0.2;
                                    belowFrac = 0.2;
                                } else if (this->startingBoostedZone > 0) {
                                    topFrac = 0.2;
                                    middleFrac = 0.2;
                                    belowFrac = 0.6;
                                } else {
                                    topFrac = 0.2;
                                    middleFrac = 0.6;
                                    belowFrac = 0.2;
                                }
                                (void)middleFrac;
                                double topMiddleBoundary = -zoneR + 2 * zoneR * topFrac;
                                double middleBelowBoundary = zoneR - 2 * zoneR * belowFrac;
                                this->activeBoostedZone = (signedOffset < topMiddleBoundary)
                                                                   ? -1
                                                                   : (signedOffset > middleBelowBoundary ? 1 : 0);
                            } else {
                                this->activeBoostedZone = (signedOffset < -zoneR / 3) ? -1 : (signedOffset > zoneR / 3 ? 1 : 0);

                                // \"Fresh line\" zone override (patch 8.6.6), mirrored for the X-boosted
                                // case - see the Y-branch above for the full explanation.
                                int familyMode = 0;
                                bool familyFound = false;
                                double selfLengthForFamily = width;
                                for (auto& elPtr: this->sourceLayer->getElements()) {
                                    Element* el = elPtr.get();
                                    if (el == xBoostedTarget) {
                                        continue;
                                    }
                                    auto* otherStroke = dynamic_cast<Stroke*>(el);
                                    if (otherStroke == nullptr || otherStroke->getArrowKind() != ArrowKind::NONE) {
                                        continue;
                                    }
                                    xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                    bool isHorizontalShaft =
                                            shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                                    if (!isHorizontalShaft ||
                                        std::abs(shaft.width - selfLengthForFamily) > BLUE_GRID_LENGTH_EPS) {
                                        continue;
                                    }
                                    if (!rangesOverlap(targetShaft.y, targetShaft.y + targetShaft.height, shaft.y,
                                                        shaft.y + shaft.height)) {
                                        continue;
                                    }
                                    double shaftCenterX = shaft.x + shaft.width / 2;
                                    if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                        continue;
                                    }
                                    double farEdge = shaft.x + shaft.width;
                                    double nearEdge = shaft.x;
                                    if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                        familyMode = -1;
                                    } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                        familyMode = 1;
                                    } else {
                                        familyMode = 0;
                                    }
                                    familyFound = true;
                                    break;
                                }
                                this->activeBoostedZone = familyFound ? familyMode : 0;
                            }
                        } else {
                            // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                            // cursor position - always Middle.
                            this->activeBoostedZone = 0;
                        }

                        double refPointX;
                        if (this->activeBoostedZone < 0) {
                            refPointX = candidateX + width;
                        } else if (this->activeBoostedZone > 0) {
                            refPointX = candidateX;
                        } else {
                            refPointX = candidateX + width / 2;
                        }
                        matchX->offset = targetCenter - refPointX;

                        // \"Line-end anchors\" (patch 8.6.5), mirrored for the X-boosted case (self
                        // horizontal, big line vertical): its own two endpoints (top/bottom) become
                        // additional anchor points for self's Y position.
                        {
                            xoj::util::Rectangle<double> bigShaft = targetShaft;
                            int existingCount = 0;
                            for (auto& elPtr: this->sourceLayer->getElements()) {
                                Element* el = elPtr.get();
                                if (el == xBoostedTarget) {
                                    continue;
                                }
                                auto* otherStroke = dynamic_cast<Stroke*>(el);
                                if (otherStroke == nullptr) {
                                    continue;
                                }
                                xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                                bool isHorizontalShaft =
                                        shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                                if (!isHorizontalShaft) {
                                    continue;
                                }
                                if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y,
                                                    shaft.y + shaft.height)) {
                                    continue;
                                }"""
OLD3 = """                                if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                double farEdge = shaft.x + shaft.width;
                                double nearEdge = shaft.x;
                                if (std::abs(farEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = -1;
                                } else if (std::abs(nearEdge - targetCenter) < BLUE_GRID_LENGTH_EPS) {
                                    familyMode = 1;
                                } else {
                                    familyMode = 0;
                                }
                                familyFound = true;
                                break;
                            }
                            this->activeBoostedZone = familyFound ? familyMode : 0;
                        }
                    } else {
                        // \"Graduation orientation\" disabled (patch 10.6B): never switch modes by
                        // cursor position - always Middle.
                        this->activeBoostedZone = 0;
                    }

                    double refPointX;
                    if (this->activeBoostedZone < 0) {
                        refPointX = candidateX + width;
                    } else if (this->activeBoostedZone > 0) {
                        refPointX = candidateX;
                    } else {
                        refPointX = candidateX + width / 2;
                    }
                    matchX->offset = targetCenter - refPointX;

                    // \"Line-end anchors\" (patch 8.6.5), mirrored for the X-boosted case (self
                    // horizontal, big line vertical): its own two endpoints (top/bottom) become
                    // additional anchor points for self's Y position.
                    {
                        xoj::util::Rectangle<double> bigShaft = targetShaft;
                        int existingCount = 0;
                        for (auto& elPtr: this->sourceLayer->getElements()) {
                            Element* el = elPtr.get();
                            if (el == xBoostedTarget) {
                                continue;
                            }
                            auto* otherStroke = dynamic_cast<Stroke*>(el);
                            if (otherStroke == nullptr) {
                                continue;
                            }
                            xoj::util::Rectangle<double> shaft = el->getSnappedBounds();
                            bool isHorizontalShaft =
                                    shaft.height <= THIN_AXIS_THRESHOLD && shaft.width > THIN_AXIS_THRESHOLD;
                            if (!isHorizontalShaft) {
                                continue;
                            }
                            if (!rangesOverlap(bigShaft.y, bigShaft.y + bigShaft.height, shaft.y,
                                                shaft.y + shaft.height)) {
                                continue;
                            }
                            double shaftCenterX = shaft.x + shaft.width / 2;
                            if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                continue;
                            }
                            existingCount++;
                        }
                        // See the Y-boosted branch above for the full explanation of this condition.
                        // Patch 11.3: see the Y-boosted branch above for the full explanation.
                        bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                        if (!tryEndpointAnchor) {
                            auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                               this->sourceLayer, excluded);
                            tryEndpointAnchor = !gridCheck.has_value();
                        }
                        if (tryEndpointAnchor) {
                            double selfCenterY = candidateY + height / 2;
                            double topEnd = bigShaft.y;
                            double bottomEnd = bigShaft.y + bigShaft.height;
                            double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                            double bestOffset = 0;
                            bool found = false;
                            if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                bestOffset = topEnd - selfCenterY;
                                found = true;
                            }
                            if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                bestOffset = bottomEnd - selfCenterY;
                                found = true;
                            }
                            if (found) {
                                matchY = AlignmentSearchResult{bestOffset, {}};
                                endpointGuideActiveY = true;
                                endpointGuideCoordY = selfCenterY + bestOffset;
                                endpointGuideFromY = candidateX + matchX->offset;
                                endpointGuideToY = candidateX + width + matchX->offset;
                            }
                        } else {
                            // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                            // case: self's Y position should stay exactly where it was at mouseDown.
                            // Only reached when \"Graduation assist\" is enabled and a valid grid was
                            // found (see the condition above).
                            matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                        }
                    }
                }"""
NEW3 = """                                if (std::abs(shaftCenterX - targetCenter) > tolerance * settings->getPerpendicularCrossBoostFactor()) {
                                    continue;
                                }
                                existingCount++;
                            }
                            // See the Y-boosted branch above for the full explanation of this condition.
                            // Patch 11.3: see the Y-boosted branch above for the full explanation.
                            bool tryEndpointAnchor = !settings->isGraduationAssistEnabled() || existingCount <= 2;
                            if (!tryEndpointAnchor) {
                                auto gridCheck = computeBlueGridY(xBoostedTarget, candidateY + height / 2, height,
                                                                   this->sourceLayer, excluded);
                                tryEndpointAnchor = !gridCheck.has_value();
                            }
                            if (tryEndpointAnchor) {
                                double selfCenterY = candidateY + height / 2;
                                double topEnd = bigShaft.y;
                                double bottomEnd = bigShaft.y + bigShaft.height;
                                double endpointTolerance = tolerance * settings->getLineEndAnchorToleranceFactor();
                                double bestOffset = 0;
                                bool found = false;
                                if (std::abs(selfCenterY - topEnd) <= endpointTolerance) {
                                    bestOffset = topEnd - selfCenterY;
                                    found = true;
                                }
                                if (std::abs(selfCenterY - bottomEnd) <= endpointTolerance &&
                                    (!found || std::abs(bottomEnd - selfCenterY) < std::abs(bestOffset))) {
                                    bestOffset = bottomEnd - selfCenterY;
                                    found = true;
                                }
                                if (found) {
                                    matchY = AlignmentSearchResult{bestOffset, {}};
                                    endpointGuideActiveY = true;
                                    endpointGuideCoordY = selfCenterY + bestOffset;
                                    endpointGuideFromY = candidateX + matchX->offset;
                                    endpointGuideToY = candidateX + width + matchX->offset;
                                }
                            } else {
                                // \"Lock Y to start\" (patch 8.6.8, point 1), mirrored for the X-boosted
                                // case: self's Y position should stay exactly where it was at mouseDown.
                                // Only reached when \"Graduation assist\" is enabled and a valid grid was
                                // found (see the condition above).
                                matchY = AlignmentSearchResult{this->snappedBounds.y - candidateY, {}};
                            }
                        }
                    }
                }"""


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
    if "tryEndpointAnchor" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] tryEndpointAnchor introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_3.py, puis relancez ce script.")
        sys.exit(1)
    if "desnapY" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.4 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD0, NEW0, "EditSelection.cpp: zone 1/4")
    ok &= apply_edit(cpp, OLD1, NEW1, "EditSelection.cpp: zone 2/4")
    ok &= apply_edit(cpp, OLD2, NEW2, "EditSelection.cpp: zone 3/4")
    ok &= apply_edit(cpp, OLD3, NEW3, "EditSelection.cpp: zone 4/4")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
