#!/usr/bin/env python3
"""
Patch 11.6 (phase alignment_snap) : CORRECTIF - deux bugs lies au point
d'ancrage vertical (Y) des textboxes, signales par l'utilisateur.

1. Quand une textbox (a une seule ligne) etait SELF (l'objet
   deplace), son propre candidat de centre sur l'axe Y utilisait
   toujours un 0.5 code en dur, au lieu de la fraction configurable
   getTextYCenterFraction() - alors que cette meme variable etait deja
   correctement utilisee quand cette textbox etait l'AUTRE element
   (non deplace). Asymetrie corrigee : self utilise desormais la meme
   logique que other.

2. Une textbox a PLUSIEURS lignes de texte doit toujours utiliser le
   vrai centre geometrique (0.5), jamais la fraction configurable -
   celle-ci existe specifiquement pour compenser le fait qu'une SEULE
   ligne de texte n'a pas son poids visuel exactement a son milieu
   geometrique (a cause des ascendantes/descendantes) ; ce raisonnement
   ne s'applique pas a un bloc de texte multi-lignes. S'applique a la
   fois a self et aux autres elements.

Necessite d'enfiler un nouveau parametre booleen `selfIsSingleLineText`
a travers findAlignmentY() et computeStartingZone() (meme methode
d'enfilage que les precedents booleens selfIsLine/selfIsArrow), calcule
une fois par mouseDown()/mouseMove() en verifiant si self est un
element Text unique sans saut de ligne dans son contenu.

Modifie : src/core/control/tools/EditSelection.cpp (8 zones)

NECESSITE : apply_alignment_snap_v90.py (+ 11.1 a 11.5.3, selon votre
process de travail actuel)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD0 = """// like THIN_AXIS_THRESHOLD/rangesOverlap and findAlignmentX/Y themselves), forward-declared here so
// EditSelection::mouseDown() below can call it.
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool& outWasBoosted);

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;
"""
NEW0 = """// like THIN_AXIS_THRESHOLD/rangesOverlap and findAlignmentX/Y themselves), forward-declared here so
// EditSelection::mouseDown() below can call it.
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText,
                                bool& outWasBoosted);

void EditSelection::mouseDown(CursorSelectionType type, double x, double y) {
    double zoom = this->view->getXournal()->getZoom();

    this->mouseDownType = type;
"""
OLD1 = """                    if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForLineCheck.begin())) {
                        selfIsLineForStart =
                                selfStroke->getArrowKind() == ArrowKind::NONE && selfStroke->getPointCount() == 2;
                    }
                }
            }
            this->startingBoostedZone =
                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,
                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,
                                         visibleRectForStart, toleranceForStart, groupToleranceForStart,
                                         settings->getTextYCenterFraction(),
                                         settings->getPerpendicularCrossBoostFactor(),
                                         settings->getSmallMarkMaxLength(), selfIsLineForStart,
                                         this->startingWasBoosted);
        }
    }
}

/**
 * Smart alignment guides (sub-patch 1: silent snap, no visual guide line yet)."""
NEW1 = """                    if (const auto* selfStroke = dynamic_cast<const Stroke*>(*selfElementsForLineCheck.begin())) {
                        selfIsLineForStart =
                                selfStroke->getArrowKind() == ArrowKind::NONE && selfStroke->getPointCount() == 2;
                    }
                }
            }
            // Patch 11.6: true only if self is a single Text element whose content has no line break
            // - see the identical check in mouseMove() below for the full rationale.
            bool selfIsSingleLineTextForStart = false;
            {
                auto selfElementsForTextCheck = this->getElementsView();
                if (selfElementsForTextCheck.size() == 1) {
                    if (const auto* selfText = dynamic_cast<const Text*>(*selfElementsForTextCheck.begin())) {
                        selfIsSingleLineTextForStart = selfText->getText().find('\\n') == std::string::npos;
                    }
                }
            }
            this->startingBoostedZone =
                    computeStartingZone(this->snappedBounds.x, this->snappedBounds.y, this->snappedBounds.width,
                                         this->snappedBounds.height, this->sourceLayer, excludedForStart,
                                         visibleRectForStart, toleranceForStart, groupToleranceForStart,
                                         settings->getTextYCenterFraction(),
                                         settings->getPerpendicularCrossBoostFactor(),
                                         settings->getSmallMarkMaxLength(), selfIsLineForStart,
                                         selfIsSingleLineTextForStart, this->startingWasBoosted);
        }
    }
}

/**
 * Smart alignment guides (sub-patch 1: silent snap, no visual guide line yet)."""
OLD2 = """    }
    return best;
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance,
                            double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                            double smallMarkMaxLength, bool selfIsLine, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    const std::vector<AlignmentCandidate> candidatesSelf =
            buildCandidates(y, height, 0.5, isSmallMark(xRight - xLeft, height, selfIsLine, smallMarkMaxLength));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * crossBoostFactor;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();"""
NEW2 = """    }
    return best;
}

static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance,
                            double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                            double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, Layer* layer,
                            const std::vector<const Element*>& excluded,
                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentSearchResult> {
    // Patch 11.6: self's own Y-axis center candidate uses the same Text-aware center fraction as
    // other elements do (see candidatesOther below) - previously hardcoded to 0.5 regardless of
    // whether self happened to be a single-line Text itself, which was an asymmetry bug (a selected
    // single-line textbox's OWN center guideline never honored getTextYCenterFraction(), while it
    // correctly did so when that same textbox was the *other*, non-moving element).
    double selfCenterFraction = selfIsSingleLineText ? textYCenterFraction : 0.5;
    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(
            y, height, selfCenterFraction, isSmallMark(xRight - xLeft, height, selfIsLine, smallMarkMaxLength));

    // --- boosted (blue) tier: exclusive, uses shaft bounds ---
    std::optional<AlignmentMatch> bestBoosted;
    double bestBoostedDist = tolerance * crossBoostFactor;
    for (auto& elPtr: layer->getElements()) {
        const Element* el = elPtr.get();"""
OLD3 = """        // vertical mid-point, on the crossed axis) shouldn't also offer a separate ordinary match.
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&"""
NEW3 = """        // vertical mid-point, on the crossed axis) shouldn't also offer a separate ordinary match.
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        // Patch 11.6: a multi-line Text's own center guideline is always the true geometric
        // center (0.5), never the configurable fraction - that fraction exists specifically to
        // compensate for a SINGLE line of text's visual weight not sitting at its exact geometric
        // middle (ascenders/descenders), which isn't a meaningful concept for a multi-line block.
        const Text* otherText = dynamic_cast<const Text*>(el);
        bool otherIsSingleLineText = otherText != nullptr && otherText->getText().find('\\n') == std::string::npos;
        double otherCenterFraction = otherIsSingleLineText ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&"""
OLD4 = """        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        double otherCenterFraction = dynamic_cast<const Text*>(el) != nullptr ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&"""
NEW4 = """        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();
        if ((isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::X, smallMarkMaxLength) ||
             isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height, CrossAxis::Y, smallMarkMaxLength)) &&
            rangesOverlap(xLeft, xRight, snapped.x, snapped.x + snapped.width)) {
            continue;
        }
        // Patch 11.6: a multi-line Text's own center guideline is always the true geometric
        // center (0.5), never the configurable fraction - that fraction exists specifically to
        // compensate for a SINGLE line of text's visual weight not sitting at its exact geometric
        // middle (ascenders/descenders), which isn't a meaningful concept for a multi-line block.
        const Text* otherText = dynamic_cast<const Text*>(el);
        bool otherIsSingleLineText = otherText != nullptr && otherText->getText().find('\\n') == std::string::npos;
        double otherCenterFraction = otherIsSingleLineText ? textYCenterFraction : 0.5;
        std::vector<AlignmentCandidate> candidatesOther;
        if (auto lineZone = detectLineZoneForOrdinaryAnchor(el, layer, excluded); lineZone.has_value()) {
            candidatesOther = buildForcedLineCandidate(snapped.y, snapped.height, *lineZone);
        } else {
            const Stroke* otherStrokeForSmallMark = dynamic_cast<const Stroke*>(el);
            bool otherIsLine = otherStrokeForSmallMark != nullptr &&"""
OLD5 = """ * boosted at all.
 */
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool& outWasBoosted) {
    outWasBoosted = false;
    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, groupTolerance, textYCenterFraction,
                                      crossBoostFactor, smallMarkMaxLength, selfIsLine, layer, excluded,
                                      visibleRect);
    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, groupTolerance,
                                     textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine, layer,
                                     excluded, visibleRect);
    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"
    }
    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, groupTolerance,
                                        textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine,
                                        layer, excluded, visibleRect);
    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"
    }

    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, groupTolerance, crossBoostFactor,"""
NEW5 = """ * boosted at all.
 */
static int computeStartingZone(double x, double y, double width, double height, Layer* layer,
                                const std::vector<const Element*>& excluded,
                                const xoj::util::Rectangle<double>& visibleRect, double tolerance,
                                double groupTolerance, double textYCenterFraction, double crossBoostFactor,
                                double smallMarkMaxLength, bool selfIsLine, bool selfIsSingleLineText, bool& outWasBoosted) {
    outWasBoosted = false;
    auto matchYReal = findAlignmentY(y, height, x, x + width, tolerance, groupTolerance, textYCenterFraction,
                                      crossBoostFactor, smallMarkMaxLength, selfIsLine, selfIsSingleLineText, layer,
                                      excluded, visibleRect);
    if (matchYReal && !matchYReal->guides.empty() && matchYReal->guides.front().isBoosted) {
        outWasBoosted = true;
        return 0;
    }
    auto matchYTop = findAlignmentY(y - height / 2, height, x, x + width, tolerance, groupTolerance,
                                     textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine, selfIsSingleLineText,
                                     layer, excluded, visibleRect);
    if (matchYTop && !matchYTop->guides.empty() && matchYTop->guides.front().isBoosted) {
        outWasBoosted = true;
        return 1;  // top edge is the anchor -> self extends downward -> \"Below\"
    }
    auto matchYBottom = findAlignmentY(y + height / 2, height, x, x + width, tolerance, groupTolerance,
                                        textYCenterFraction, crossBoostFactor, smallMarkMaxLength, selfIsLine,
                                        selfIsSingleLineText, layer, excluded, visibleRect);
    if (matchYBottom && !matchYBottom->guides.empty() && matchYBottom->guides.front().isBoosted) {
        outWasBoosted = true;
        return -1;  // bottom edge is the anchor -> self extends upward -> \"Top\"
    }

    auto matchXReal = findAlignmentX(x, width, y, y + height, tolerance, groupTolerance, crossBoostFactor,"""
OLD6 = """                            selfIsArrow = selfStroke->getArrowKind() != ArrowKind::NONE;
                            selfIsLine = !selfIsArrow && selfStroke->getPointCount() == 2;
                        }
                    }
                }

                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,
                                              groupTolerance, settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, this->sourceLayer,
                                              excluded, visibleRect);
                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              groupTolerance, settings->getTextYCenterFraction(),
                                              settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, this->sourceLayer,
                                              excluded, visibleRect);

                // An arrow or double arrow, however small, is never eligible to be the \"small\"
                // crossing side of a boosted (blue) match - only plain lines are. If self is an
                // arrow and the search above found one anyway, discard it outright: on that axis,
                // self simply gets no alignment snap at all in that case (not even the ordinary
                // tier), rather than threading an extra flag through findAlignmentX/Y themselves."""
NEW6 = """                            selfIsArrow = selfStroke->getArrowKind() != ArrowKind::NONE;
                            selfIsLine = !selfIsArrow && selfStroke->getPointCount() == 2;
                        }
                    }
                }

                // Patch 11.6: true only if self is a single Text element whose content has no line
                // break - see findAlignmentY()'s own comment on selfCenterFraction for why this
                // matters.
                bool selfIsSingleLineText = false;
                {
                    auto selfElementsForTextCheck = this->getElementsView();
                    if (selfElementsForTextCheck.size() == 1) {
                        if (const auto* selfText = dynamic_cast<const Text*>(*selfElementsForTextCheck.begin())) {
                            selfIsSingleLineText = selfText->getText().find('\\n') == std::string::npos;
                        }
                    }
                }

                auto matchX = findAlignmentX(candidateX, width, candidateY, candidateY + height, tolerance,
                                              groupTolerance, settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, this->sourceLayer,
                                              excluded, visibleRect);
                auto matchY = findAlignmentY(candidateY, height, candidateX, candidateX + width, tolerance,
                                              groupTolerance, settings->getTextYCenterFraction(),
                                              settings->getPerpendicularCrossBoostFactor(),
                                              settings->getSmallMarkMaxLength(), selfIsLine, selfIsSingleLineText,
                                              this->sourceLayer, excluded, visibleRect);

                // An arrow or double arrow, however small, is never eligible to be the \"small\"
                // crossing side of a boosted (blue) match - only plain lines are. If self is an
                // arrow and the search above found one anyway, discard it outright: on that axis,
                // self simply gets no alignment snap at all in that case (not even the ordinary
                // tier), rather than threading an extra flag through findAlignmentX/Y themselves."""
OLD7 = """                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                        if (!matchYAlreadyBoosted) {
                            auto matchYVirtualTop = findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,
                                                            tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                            settings->getPerpendicularCrossBoostFactor(),
                                                            settings->getSmallMarkMaxLength(),
                                                            selfIsLine,
                                                            this->sourceLayer, excluded, visibleRect);
                            auto matchYVirtualBottom = findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,
                                                               tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                               settings->getPerpendicularCrossBoostFactor(),
                                                               settings->getSmallMarkMaxLength(),
                                                               selfIsLine,
                                                               this->sourceLayer, excluded, visibleRect);
                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&
                                                 matchYVirtualTop->guides.front().isBoosted;
                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&
                                                    matchYVirtualBottom->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetY;"""
NEW7 = """                        bool matchYAlreadyBoosted = matchY && !matchY->guides.empty() && matchY->guides.front().isBoosted;
                        if (!matchYAlreadyBoosted) {
                            auto matchYVirtualTop = findAlignmentY(candidateY - height / 2, height, candidateX, candidateX + width,
                                                            tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                            settings->getPerpendicularCrossBoostFactor(),
                                                            settings->getSmallMarkMaxLength(),
                                                            selfIsLine, selfIsSingleLineText,
                                                            this->sourceLayer, excluded, visibleRect);
                            auto matchYVirtualBottom = findAlignmentY(candidateY + height / 2, height, candidateX, candidateX + width,
                                                               tolerance, groupTolerance, settings->getTextYCenterFraction(),
                                                               settings->getPerpendicularCrossBoostFactor(),
                                                               settings->getSmallMarkMaxLength(),
                                                               selfIsLine, selfIsSingleLineText,
                                                               this->sourceLayer, excluded, visibleRect);
                            bool topIsBoosted = matchYVirtualTop && !matchYVirtualTop->guides.empty() &&
                                                 matchYVirtualTop->guides.front().isBoosted;
                            bool bottomIsBoosted = matchYVirtualBottom && !matchYVirtualBottom->guides.empty() &&
                                                    matchYVirtualBottom->guides.front().isBoosted;
                            std::optional<double> bestRealOffsetY;"""


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
    if "getTextYCenterFraction" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] getTextYCenterFraction introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py, puis relancez ce script.")
        sys.exit(1)
    if "selfIsSingleLineText" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.6 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD0, NEW0, "EditSelection.cpp: zone 1/8")
    ok &= apply_edit(cpp, OLD1, NEW1, "EditSelection.cpp: zone 2/8")
    ok &= apply_edit(cpp, OLD2, NEW2, "EditSelection.cpp: zone 3/8")
    ok &= apply_edit(cpp, OLD3, NEW3, "EditSelection.cpp: zone 4/8")
    ok &= apply_edit(cpp, OLD4, NEW4, "EditSelection.cpp: zone 5/8")
    ok &= apply_edit(cpp, OLD5, NEW5, "EditSelection.cpp: zone 6/8")
    ok &= apply_edit(cpp, OLD6, NEW6, "EditSelection.cpp: zone 7/8")
    ok &= apply_edit(cpp, OLD7, NEW7, "EditSelection.cpp: zone 8/8")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
