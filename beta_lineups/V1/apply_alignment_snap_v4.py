#!/usr/bin/env python3
"""
Sous-patch 4/4 du systeme d'ancrage entre objets (style Canva/Figma). Ajoute :
  1) Les points d'ancrage utilisent Element::getSnappedBounds() de facon
     coherente pour l'objet deplace ET les objets cibles (au lieu de melanger
     snappedBounds pour soi-meme et la boite visuelle - qui inclut
     l'epaisseur du trait - pour les autres), corrigeant le leger decalage
     entre un objet selectionne et sa copie non selectionnee.
  2) Cas "petit trait perpendiculaire sur grand trait" : tolerance x1.5 et
     ligne de guidage BLEUE quand un petit trait (horizontal ou vertical) est
     deplace sur un grand trait perpendiculaire et que l'alignement se fait
     centre a centre.
  3) Raccourci clavier Ctrl+B pour Object Alignment Snapping.
  4) L'ancrage centre des traits horizontaux (axe Y) est deplace 20% plus bas
     (a 70% de l'epaisseur au lieu de 50%).

NECESSITE apply_alignment_snap_v1.py, v2.py et v3.py deja appliques, dans cet
ordre.
A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    h = Path("src/core/control/tools/EditSelection.h")
    ap = Path("src/core/control/actions/ActionProperties.h")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    if "THIN_AXIS_THRESHOLD" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] THIN_AXIS_THRESHOLD introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v1/v2/v3.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    ok &= apply_edit(
        ap,
        old='struct ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING> {\n'
            '    using state_type = bool;\n'
            '    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapToObjects(); }',
        new='struct ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING> {\n'
            '    using state_type = bool;\n'
            '    static constexpr const char* accelerators[] = {"<Ctrl>B", nullptr};\n'
            '    static state_type initialState(Control* ctrl) { return ctrl->getSettings()->isSnapToObjects(); }',
        label="ActionProperties.h: raccourci Ctrl+B",
    )

    ok &= apply_edit(
        h,
        old='    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '    };',
        new='    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '    };',
        label="EditSelection.h: champ isBoosted dans AlignmentGuide",
    )

    ok &= apply_edit(
        cpp,
        old='/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' * `isCenter` is true if either of the two matched candidates was a center point (rather than an\n'
            ' * edge), used to draw the guide line in a different color.\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '};\n\n'
            '/// A single candidate coordinate for alignment, tagged with whether it is a center point.\n'
            'struct AlignmentCandidate {\n'
            '    double value;\n'
            '    bool isCenter;\n'
            '};\n\n'
            '/**\n'
            ' * Below this size (in document points), a box is considered to have no meaningful "thickness axis"\n'
            ' * of its own (e.g. a horizontal or vertical straight line) - see buildCandidates().\n'
            ' */\n'
            'constexpr double THIN_AXIS_THRESHOLD = 3.0;\n\n'
            '/**\n'
            ' * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis. If the\n'
            ' * box is "thin" on that axis (size <= THIN_AXIS_THRESHOLD, e.g. the thickness of a horizontal or\n'
            ' * vertical line), only the center candidate is returned: offering top/bottom (or left/right)\n'
            ' * candidates as well would produce two near-identical, confusingly close guide lines for a simple\n'
            ' * straight line.\n'
            ' */\n'
            'static auto buildCandidates(double from, double size) -> std::vector<AlignmentCandidate> {\n'
            '    if (size <= THIN_AXIS_THRESHOLD) {\n'
            '        return {{from + size / 2, true}};\n'
            '    }\n'
            '    return {{from, false}, {from + size / 2, true}, {from + size, false}};\n'
            '}\n\n'
            '/// True if the two given [x, x+w] x [y, y+h] boxes intersect at all.\n'
            'static auto boxesIntersect(double x1, double y1, double w1, double h1, double x2, double y2, double w2, double h2)\n'
            '        -> bool {\n'
            '    return x1 <= x2 + w2 && x2 <= x1 + w1 && y1 <= y2 + h2 && y2 <= y1 + h1;\n'
            '}\n\n'
            '/**\n'
            ' * If any of the moving box\'s y-candidates (see buildCandidates()), when placed at the given y with\n'
            ' * the given height, is within `tolerance` (document units) of the corresponding candidate of\n'
            ' * another element on `layer`, returns the match. Candidates are only considered for elements whose\n'
            ' * bounding box currently intersects `visibleRect` (elements scrolled out of view are ignored), and\n'
            ' * elements in `excluded` are always skipped (i.e. the elements currently being moved).\n'
            ' * xLeft/xRight are the moving box\'s horizontal extent, used together with the matched element\'s own\n'
            ' * extent to compute the guide line\'s span (perpendicular axis).\n'
            ' */\n'
            'static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height);\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(ey, eh);\n'
            '        for (auto& cs: candidatesSelf) {\n'
            '            for (auto& co: candidatesOther) {\n'
            '                double dist = std::abs(cs.value - co.value);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co.value - cs.value, co.value, std::min(xLeft, ex), std::max(xRight, ex + ew),\n'
            '                                           cs.isCenter || co.isCenter};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            '/// Same as findAlignmentY(), but for the horizontal candidates (left / horizontal-center / right).\n'
            '/// yTop/yBottom are the moving box\'s vertical extent, used for the guide line\'s span.\n'
            'static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(ex, ew);\n'
            '        for (auto& cs: candidatesSelf) {\n'
            '            for (auto& co: candidatesOther) {\n'
            '                double dist = std::abs(cs.value - co.value);\n'
            '                if (dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co.value - cs.value, co.value, std::min(yTop, ey), std::max(yBottom, ey + eh),\n'
            '                                           cs.isCenter || co.isCenter};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}',
        new='/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' * `isCenter` is true if either of the two matched candidates was a center point (rather than an\n'
            ' * edge); `isBoosted` is true for the special "small stroke crossing a big perpendicular stroke,\n'
            ' * center-to-center" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '};\n\n'
            '/// A single candidate coordinate for alignment, tagged with whether it is a center point.\n'
            'struct AlignmentCandidate {\n'
            '    double value;\n'
            '    bool isCenter;\n'
            '};\n\n'
            '/**\n'
            ' * Below this size (in document points), a box is considered to have no meaningful "thickness axis"\n'
            ' * of its own (e.g. a horizontal or vertical straight line) - see buildCandidates().\n'
            ' */\n'
            'constexpr double THIN_AXIS_THRESHOLD = 3.0;\n\n'
            '/**\n'
            ' * When a small line-like element is moved across a much bigger perpendicular line-like element\n'
            ' * (e.g. a short axis tick dragged onto a long axis line), a center-to-center match between the two\n'
            ' * gets an extended tolerance (this factor) and a distinct guide-line color, since that is a very\n'
            ' * deliberate, common alignment (e.g. centering a graduation mark on an axis).\n'
            ' */\n'
            'constexpr double PERPENDICULAR_CROSS_BOOST_FACTOR = 1.5;\n\n'
            '/**\n'
            ' * Builds the 1 or 3 alignment candidates for a box spanning [from, from + size] on one axis. If the\n'
            ' * box is "thin" on that axis (size <= THIN_AXIS_THRESHOLD, e.g. the thickness of a horizontal or\n'
            ' * vertical line), only the center candidate is returned: offering top/bottom (or left/right)\n'
            ' * candidates as well would produce two near-identical, confusingly close guide lines for a simple\n'
            ' * straight line. `centerFraction` (0 to 1) chooses where that lone candidate sits within the box;\n'
            ' * it is not exactly 0.5 for the horizontal-stroke case (see findAlignmentY()).\n'
            ' */\n'
            'static auto buildCandidates(double from, double size, double centerFraction = 0.5) -> std::vector<AlignmentCandidate> {\n'
            '    if (size <= THIN_AXIS_THRESHOLD) {\n'
            '        return {{from + size * centerFraction, true}};\n'
            '    }\n'
            '    return {{from, false}, {from + size / 2, true}, {from + size, false}};\n'
            '}\n\n'
            '/// True if the two given [x, x+w] x [y, y+h] boxes intersect at all.\n'
            'static auto boxesIntersect(double x1, double y1, double w1, double h1, double x2, double y2, double w2, double h2)\n'
            '        -> bool {\n'
            '    return x1 <= x2 + w2 && x2 <= x1 + w1 && y1 <= y2 + h2 && y2 <= y1 + h1;\n'
            '}\n\n'
            '/**\n'
            ' * True if `self` (width x height) and `other` (width x height) are two line-like boxes (one is\n'
            ' * "thin", per THIN_AXIS_THRESHOLD, on one axis while the other is thin on the *perpendicular* axis -\n'
            ' * i.e. one roughly horizontal, one roughly vertical), AND `self` is shorter, along its own length,\n'
            ' * than `other` is along its own length - i.e. a small stroke crossing a much bigger perpendicular\n'
            ' * one, such as a short axis tick being placed onto a long axis line.\n'
            ' */\n'
            'static auto isSmallCrossingBigPerpendicular(double selfWidth, double selfHeight, double otherWidth,\n'
            '                                             double otherHeight) -> bool {\n'
            '    bool selfVertical = selfWidth <= THIN_AXIS_THRESHOLD && selfHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool selfHorizontal = selfHeight <= THIN_AXIS_THRESHOLD && selfWidth > THIN_AXIS_THRESHOLD;\n'
            '    bool otherVertical = otherWidth <= THIN_AXIS_THRESHOLD && otherHeight > THIN_AXIS_THRESHOLD;\n'
            '    bool otherHorizontal = otherHeight <= THIN_AXIS_THRESHOLD && otherWidth > THIN_AXIS_THRESHOLD;\n\n'
            '    if (selfVertical && otherHorizontal) {\n'
            '        return selfHeight < otherWidth;\n'
            '    }\n'
            '    if (selfHorizontal && otherVertical) {\n'
            '        return selfWidth < otherHeight;\n'
            '    }\n'
            '    return false;\n'
            '}\n\n'
            '/**\n'
            ' * If any of the moving box\'s y-candidates (see buildCandidates()), when placed at the given y with\n'
            ' * the given height, is within `tolerance` (document units) of the corresponding candidate of\n'
            ' * another element on `layer`, returns the match. Candidates are only considered for elements whose\n'
            ' * *visual* bounding box currently intersects `visibleRect` (elements scrolled out of view are\n'
            ' * ignored); the alignment candidates themselves are computed from each element\'s *snapped* bounds\n'
            ' * (Element::getSnappedBounds()) rather than its visual bounds, so that a selected element\'s own\n'
            ' * candidates (computed the same way, from EditSelection::snappedBounds) line up exactly with an\n'
            ' * identical, unselected element\'s - the visual bounds include the stroke\'s rendered thickness,\n'
            ' * which the snapped bounds deliberately exclude.\n'
            ' * elements in `excluded` are always skipped (i.e. the elements currently being moved).\n'
            ' * xLeft/xRight are the moving box\'s horizontal extent, used together with the matched element\'s own\n'
            ' * extent to compute the guide line\'s span (perpendicular axis).\n'
            ' */\n'
            'static auto findAlignmentY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    // The horizontal-stroke center candidate sits 20% lower than the true geometric center (0.5 + 0.2).\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(y, height, 0.7);\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
            '        bool crossBoost = isSmallCrossingBigPerpendicular(xRight - xLeft, height, snapped.width, snapped.height);\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.y, snapped.height, 0.7);\n'
            '        for (auto& cs: candidatesSelf) {\n'
            '            for (auto& co: candidatesOther) {\n'
            '                bool boosted = crossBoost && cs.isCenter && co.isCenter;\n'
            '                double effTolerance = boosted ? tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR : tolerance;\n'
            '                double dist = std::abs(cs.value - co.value);\n'
            '                if (dist < effTolerance && dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co.value - cs.value,\n'
            '                                           co.value,\n'
            '                                           std::min(xLeft, snapped.x),\n'
            '                                           std::max(xRight, snapped.x + snapped.width),\n'
            '                                           cs.isCenter || co.isCenter,\n'
            '                                           boosted};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            '/// Same as findAlignmentY(), but for the horizontal candidates (left / horizontal-center / right).\n'
            '/// yTop/yBottom are the moving box\'s vertical extent, used for the guide line\'s span.\n'
            'static auto findAlignmentX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                            const std::vector<const Element*>& excluded,\n'
            '                            const xoj::util::Rectangle<double>& visibleRect) -> std::optional<AlignmentMatch> {\n'
            '    const std::vector<AlignmentCandidate> candidatesSelf = buildCandidates(x, width);\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) != excluded.end()) {\n'
            '            continue;\n'
            '        }\n'
            '        double ew = el->getElementWidth();\n'
            '        double ex = el->getX();\n'
            '        double eh = el->getElementHeight();\n'
            '        double ey = el->getY();\n'
            '        if (!boxesIntersect(ex, ey, ew, eh, visibleRect.x, visibleRect.y, visibleRect.width, visibleRect.height)) {\n'
            '            continue;\n'
            '        }\n'
            '        xoj::util::Rectangle<double> snapped = el->getSnappedBounds();\n'
            '        bool crossBoost = isSmallCrossingBigPerpendicular(width, yBottom - yTop, snapped.width, snapped.height);\n'
            '        std::vector<AlignmentCandidate> candidatesOther = buildCandidates(snapped.x, snapped.width);\n'
            '        for (auto& cs: candidatesSelf) {\n'
            '            for (auto& co: candidatesOther) {\n'
            '                bool boosted = crossBoost && cs.isCenter && co.isCenter;\n'
            '                double effTolerance = boosted ? tolerance * PERPENDICULAR_CROSS_BOOST_FACTOR : tolerance;\n'
            '                double dist = std::abs(cs.value - co.value);\n'
            '                if (dist < effTolerance && dist < bestDist) {\n'
            '                    bestDist = dist;\n'
            '                    best = AlignmentMatch{co.value - cs.value,\n'
            '                                           co.value,\n'
            '                                           std::min(yTop, snapped.y),\n'
            '                                           std::max(yBottom, snapped.y + snapped.height),\n'
            '                                           cs.isCenter || co.isCenter,\n'
            '                                           boosted};\n'
            '                }\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}',
        label="EditSelection.cpp: findAlignmentX/Y (snappedBounds cohérent + boost croisement + centre décalé)",
    )

    ok &= apply_edit(
        cpp,
        old='                if (matchX) {\n'
            '                    dx += matchX->offset;\n'
            '                    objectSnappedX = true;\n'
            '                    this->activeGuideX =\n'
            '                            AlignmentGuide{matchX->coordinate, matchX->extentFrom, matchX->extentTo, matchX->isCenter};\n'
            '                } else {\n'
            '                    this->activeGuideX.reset();\n'
            '                }\n'
            '                if (matchY) {\n'
            '                    dy += matchY->offset;\n'
            '                    objectSnappedY = true;\n'
            '                    this->activeGuideY =\n'
            '                            AlignmentGuide{matchY->coordinate, matchY->extentFrom, matchY->extentTo, matchY->isCenter};\n'
            '                } else {\n'
            '                    this->activeGuideY.reset();\n'
            '                }',
        new='                if (matchX) {\n'
            '                    dx += matchX->offset;\n'
            '                    objectSnappedX = true;\n'
            '                    this->activeGuideX = AlignmentGuide{matchX->coordinate, matchX->extentFrom, matchX->extentTo,\n'
            '                                                         matchX->isCenter, matchX->isBoosted};\n'
            '                } else {\n'
            '                    this->activeGuideX.reset();\n'
            '                }\n'
            '                if (matchY) {\n'
            '                    dy += matchY->offset;\n'
            '                    objectSnappedY = true;\n'
            '                    this->activeGuideY = AlignmentGuide{matchY->coordinate, matchY->extentFrom, matchY->extentTo,\n'
            '                                                         matchY->isCenter, matchY->isBoosted};\n'
            '                } else {\n'
            '                    this->activeGuideY.reset();\n'
            '                }',
        label="EditSelection.cpp: transmission de isBoosted vers AlignmentGuide",
    )

    ok &= apply_edit(
        cpp,
        old='    // it is currently aligned with. Pink for an edge alignment, green if either matched anchor was a\n'
            '    // center point.\n'
            '    if (this->activeGuideX || this->activeGuideY) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n\n'
            '        if (this->activeGuideX) {\n'
            '            if (this->activeGuideX->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = this->activeGuideX->coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, this->activeGuideX->from * zoom);\n'
            '            cairo_line_to(cr, gx, this->activeGuideX->to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        if (this->activeGuideY) {\n'
            '            if (this->activeGuideY->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gy = this->activeGuideY->coordinate * zoom;\n'
            '            cairo_move_to(cr, this->activeGuideY->from * zoom, gy);\n'
            '            cairo_line_to(cr, this->activeGuideY->to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }',
        new='    // it is currently aligned with. Pink for an edge alignment, green if either matched anchor was a\n'
            '    // center point, blue for the special "small stroke crossing a big perpendicular stroke" case.\n'
            '    if (this->activeGuideX || this->activeGuideY) {\n'
            '        cairo_save(cr);\n'
            '        cairo_set_line_width(cr, 1.5);\n'
            '        cairo_set_dash(cr, nullptr, 0, 0);\n\n'
            '        if (this->activeGuideX) {\n'
            '            if (this->activeGuideX->isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.4, 1.0);  // blue\n'
            '            } else if (this->activeGuideX->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = this->activeGuideX->coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, this->activeGuideX->from * zoom);\n'
            '            cairo_line_to(cr, gx, this->activeGuideX->to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        if (this->activeGuideY) {\n'
            '            if (this->activeGuideY->isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.4, 1.0);  // blue\n'
            '            } else if (this->activeGuideY->isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gy = this->activeGuideY->coordinate * zoom;\n'
            '            cairo_move_to(cr, this->activeGuideY->from * zoom, gy);\n'
            '            cairo_line_to(cr, this->activeGuideY->to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        cairo_restore(cr);\n'
            '    }',
        label="EditSelection.cpp: couleur bleue pour le cas croisement dans paint()",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
