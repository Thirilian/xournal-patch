#!/usr/bin/env python3
"""
Sous-patch 8.1.2 du systeme d'ancrage entre objets (style Canva/Figma).

Ajoute un rendu visuel pour le snapping equidistant (patch 8.1) : au lieu
d'une simple ligne, trace une chaine de fleches doubles ("<-->") entre
chaque paire consecutive d'objets du groupe equidistant (objet deplace
inclus), en rose. La chaine est positionnee en dehors des objets :
en dessous pour une rangee horizontale, a droite pour une colonne
verticale (marge fixe EQUIDISTANT_ARROW_MARGIN, 10pt par defaut).

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py, v7_6.py, v7_8.py, v7_9.py
  4) apply_alignment_snap_v8_1.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path


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
    h = Path("src/core/control/tools/EditSelection.h")
    if not cpp.exists() or not h.exists():
        print("[ECHEC] Fichiers introuvables. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "findEquidistantX" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] findEquidistantX introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v8_1.py, puis relancez ce script.")
        sys.exit(1)

    ok = True

    # ============ 1. AlignmentMatch struct (EditSelection.cpp) ============
    ok &= apply_edit(
        cpp,
        old='/**\n'
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
            '};\n',
        new='/**\n'
            ' * Result of a successful alignment match: `offset` is the amount to shift the moving object\'s\n'
            ' * coordinate to align exactly; `coordinate` is the aligned value itself (for drawing the guide\n'
            ' * line); `extentFrom`/`extentTo` delimit, on the perpendicular axis, the segment spanning both the\n'
            ' * moving object and the matched object, so the drawn guide line visually connects the two.\n'
            ' * `isCenter` is true if either of the two matched candidates was a center point (rather than an\n'
            ' * edge); `isBoosted` is true for the special "small stroke crossing a big perpendicular stroke,\n'
            ' * center-to-center" case (see isSmallCrossingBigPerpendicular()), drawn in a distinct color.\n'
            ' * `equidistantGaps`/`equidistantPlacement` are only set for an equidistant ("equal spacing") match\n'
            ' * (see findEquidistantX/Y()): each pair in `equidistantGaps` is a (from, to) span, in primary-axis\n'
            ' * document coordinates, of one gap in the chain to be drawn as a double-headed arrow; all of them\n'
            ' * are drawn at the same `equidistantPlacement` coordinate on the perpendicular axis. Empty/0 (their\n'
            ' * default) for every other kind of match, which just draws the plain coordinate/extentFrom/extentTo\n'
            ' * line instead - see paint().\n'
            ' */\n'
            'struct AlignmentMatch {\n'
            '    double offset;\n'
            '    double coordinate;\n'
            '    double extentFrom;\n'
            '    double extentTo;\n'
            '    bool isCenter;\n'
            '    bool isBoosted;\n'
            '    std::vector<std::pair<double, double>> equidistantGaps;\n'
            '    double equidistantPlacement = 0;\n'
            '};\n',
        label="EditSelection.cpp: nouveaux champs sur AlignmentMatch",
    )

    # ============ 2. AlignmentGuide struct (EditSelection.h) ============
    ok &= apply_edit(
        h,
        old='    /**\n'
            '     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or\n'
            '     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that\n'
            '     * spans between the moving selection and the element it is aligned with, so the drawn line\n'
            '     * visually connects the two.\n'
            '     */\n'
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '    };',
        new='    /**\n'
            '     * A single active alignment guide line: `coordinate` is the aligned x (for a vertical guide) or\n'
            '     * y (for a horizontal guide); `from`/`to` delimit the segment (in the perpendicular axis) that\n'
            '     * spans between the moving selection and the element it is aligned with, so the drawn line\n'
            '     * visually connects the two. `equidistantGaps`/`equidistantPlacement`, if non-empty, mean this\n'
            '     * guide is an equidistant ("equal spacing") match instead: each pair is one gap in the chain to\n'
            '     * draw as a double-headed arrow (in primary-axis coordinates), all at `equidistantPlacement` on\n'
            '     * the perpendicular axis - see paint().\n'
            '     */\n'
            '    struct AlignmentGuide {\n'
            '        double coordinate;\n'
            '        double from;\n'
            '        double to;\n'
            '        bool isCenter;\n'
            '        bool isBoosted;\n'
            '        std::vector<std::pair<double, double>> equidistantGaps;\n'
            '        double equidistantPlacement = 0;\n'
            '    };',
        label="EditSelection.h: nouveaux champs sur AlignmentGuide",
    )

    # ============ 3. findEquidistantX/Y : ajout de la constante + remplissage des champs ============
    ok &= apply_edit(
        cpp,
        old='/**\n'
            ' * Equidistant ("equal spacing") snapping: if the moving box, placed at x (width wide), would end up\n'
            ' * adjacent to one of two other elements B and C on `layer`, at exactly the same gap that already\n'
            ' * separates B and C from each other, returns the match (offset to apply, and a guide spanning from\n'
            ' * the moving box to the far element). Covers extending an existing rhythm at either end (self-B-C or\n'
            ' * B-C-self); does not cover inserting self *between* B and C by bisecting their gap. B and C are only\n'
            ' * considered together if a single horizontal line could pass through the moving box and both of them\n'
            ' * (their Y-extents, together with [yTop, yBottom], must have a common intersection) - same\n'
            ' * "overlap on the perpendicular axis" rule used elsewhere, not requiring perfect alignment.\n'
            ' * Always renders pink (this is not an edge/center anchor match, just reused for visual consistency).\n'
            ' */\n'
            'static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }\n\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n\n'
            '    for (const Element* b: candidates) {\n'
            '        for (const Element* c: candidates) {\n'
            '            if (b == c) {\n'
            '                continue;\n'
            '            }\n'
            '            xoj::util::Rectangle<double> bb = b->getSnappedBounds();\n'
            '            xoj::util::Rectangle<double> cb = c->getSnappedBounds();\n'
            '            if (bb.x + bb.width > cb.x) {\n'
            '                continue;  // only consider b strictly to the left of c (each pair handled once)\n'
            '            }\n'
            '            double gap = cb.x - (bb.x + bb.width);\n'
            '            if (gap <= 0) {\n'
            '                continue;\n'
            '            }\n'
            '            double maxStart = std::max({yTop, bb.y, cb.y});\n'
            '            double minEnd = std::min({yBottom, bb.y + bb.height, cb.y + cb.height});\n'
            '            if (maxStart > minEnd) {\n'
            '                continue;\n'
            '            }\n\n'
            '            // self extends the row on the left: self, b, c\n'
            '            double unionFrom = std::min({yTop, bb.y, cb.y});\n'
            '            double unionTo = std::max({yBottom, bb.y + bb.height, cb.y + cb.height});\n'
            '            double targetLeft = bb.x - gap - width;\n'
            '            double distLeft = std::abs(targetLeft - x);\n'
            '            if (distLeft < bestDist) {\n'
            '                bestDist = distLeft;\n'
            '                best = AlignmentMatch{targetLeft - x, targetLeft, unionFrom, unionTo, false, false};\n'
            '            }\n'
            '            // self extends the row on the right: b, c, self\n'
            '            double targetRight = cb.x + cb.width + gap;\n'
            '            double distRight = std::abs(targetRight - x);\n'
            '            if (distRight < bestDist) {\n'
            '                bestDist = distRight;\n'
            '                best = AlignmentMatch{targetRight - x, targetRight, unionFrom, unionTo, false, false};\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            '/// Same as findEquidistantX(), but along the vertical axis (stacking a row top-to-bottom).\n'
            'static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }\n\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n\n'
            '    for (const Element* b: candidates) {\n'
            '        for (const Element* c: candidates) {\n'
            '            if (b == c) {\n'
            '                continue;\n'
            '            }\n'
            '            xoj::util::Rectangle<double> bb = b->getSnappedBounds();\n'
            '            xoj::util::Rectangle<double> cb = c->getSnappedBounds();\n'
            '            if (bb.y + bb.height > cb.y) {\n'
            '                continue;\n'
            '            }\n'
            '            double gap = cb.y - (bb.y + bb.height);\n'
            '            if (gap <= 0) {\n'
            '                continue;\n'
            '            }\n'
            '            double maxStart = std::max({xLeft, bb.x, cb.x});\n'
            '            double minEnd = std::min({xRight, bb.x + bb.width, cb.x + cb.width});\n'
            '            if (maxStart > minEnd) {\n'
            '                continue;\n'
            '            }\n\n'
            '            double unionFrom = std::min({xLeft, bb.x, cb.x});\n'
            '            double unionTo = std::max({xRight, bb.x + bb.width, cb.x + cb.width});\n'
            '            double targetTop = bb.y - gap - height;\n'
            '            double distTop = std::abs(targetTop - y);\n'
            '            if (distTop < bestDist) {\n'
            '                bestDist = distTop;\n'
            '                best = AlignmentMatch{targetTop - y, targetTop, unionFrom, unionTo, false, false};\n'
            '            }\n'
            '            double targetBottom = cb.y + cb.height + gap;\n'
            '            double distBottom = std::abs(targetBottom - y);\n'
            '            if (distBottom < bestDist) {\n'
            '                bestDist = distBottom;\n'
            '                best = AlignmentMatch{targetBottom - y, targetBottom, unionFrom, unionTo, false, false};\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n',
        new='/**\n'
            ' * Vertical (for a horizontal chain) or horizontal (for a vertical chain) offset, in document\n'
            ' * points, between the row/column of objects being equally spaced and the double-arrow chain drawn\n'
            ' * to illustrate it - see findEquidistantX/Y() and paint(). The chain is drawn on the "outside" of\n'
            ' * the objects (below a horizontal row, to the right of a vertical column).\n'
            ' */\n'
            'constexpr double EQUIDISTANT_ARROW_MARGIN = 10.0;\n\n'
            '/**\n'
            ' * Equidistant ("equal spacing") snapping: if the moving box, placed at x (width wide), would end up\n'
            ' * adjacent to one of two other elements B and C on `layer`, at exactly the same gap that already\n'
            ' * separates B and C from each other, returns the match (offset to apply, and a guide spanning from\n'
            ' * the moving box to the far element). Covers extending an existing rhythm at either end (self-B-C or\n'
            ' * B-C-self); does not cover inserting self *between* B and C by bisecting their gap. B and C are only\n'
            ' * considered together if a single horizontal line could pass through the moving box and both of them\n'
            ' * (their Y-extents, together with [yTop, yBottom], must have a common intersection) - same\n'
            ' * "overlap on the perpendicular axis" rule used elsewhere, not requiring perfect alignment.\n'
            ' * Always renders pink (this is not an edge/center anchor match, just reused for visual consistency).\n'
            ' */\n'
            'static auto findEquidistantX(double x, double width, double yTop, double yBottom, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }\n\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n\n'
            '    for (const Element* b: candidates) {\n'
            '        for (const Element* c: candidates) {\n'
            '            if (b == c) {\n'
            '                continue;\n'
            '            }\n'
            '            xoj::util::Rectangle<double> bb = b->getSnappedBounds();\n'
            '            xoj::util::Rectangle<double> cb = c->getSnappedBounds();\n'
            '            if (bb.x + bb.width > cb.x) {\n'
            '                continue;  // only consider b strictly to the left of c (each pair handled once)\n'
            '            }\n'
            '            double gap = cb.x - (bb.x + bb.width);\n'
            '            if (gap <= 0) {\n'
            '                continue;\n'
            '            }\n'
            '            double maxStart = std::max({yTop, bb.y, cb.y});\n'
            '            double minEnd = std::min({yBottom, bb.y + bb.height, cb.y + cb.height});\n'
            '            if (maxStart > minEnd) {\n'
            '                continue;\n'
            '            }\n\n'
            '            // self extends the row on the left: self, b, c\n'
            '            double unionFrom = std::min({yTop, bb.y, cb.y});\n'
            '            double unionTo = std::max({yBottom, bb.y + bb.height, cb.y + cb.height});\n'
            '            double placement = std::max({yBottom, bb.y + bb.height, cb.y + cb.height}) + EQUIDISTANT_ARROW_MARGIN;\n'
            '            double targetLeft = bb.x - gap - width;\n'
            '            double distLeft = std::abs(targetLeft - x);\n'
            '            if (distLeft < bestDist) {\n'
            '                bestDist = distLeft;\n'
            '                best = AlignmentMatch{targetLeft - x, targetLeft, unionFrom, unionTo, false, false};\n'
            '                best->equidistantGaps = {{targetLeft + width, bb.x}, {bb.x + bb.width, cb.x}};\n'
            '                best->equidistantPlacement = placement;\n'
            '            }\n'
            '            // self extends the row on the right: b, c, self\n'
            '            double targetRight = cb.x + cb.width + gap;\n'
            '            double distRight = std::abs(targetRight - x);\n'
            '            if (distRight < bestDist) {\n'
            '                bestDist = distRight;\n'
            '                best = AlignmentMatch{targetRight - x, targetRight, unionFrom, unionTo, false, false};\n'
            '                best->equidistantGaps = {{bb.x + bb.width, cb.x}, {cb.x + cb.width, targetRight}};\n'
            '                best->equidistantPlacement = placement;\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n\n'
            '/// Same as findEquidistantX(), but along the vertical axis (stacking a row top-to-bottom).\n'
            'static auto findEquidistantY(double y, double height, double xLeft, double xRight, double tolerance, Layer* layer,\n'
            '                              const std::vector<const Element*>& excluded) -> std::optional<AlignmentMatch> {\n'
            '    std::vector<const Element*> candidates;\n'
            '    for (auto& elPtr: layer->getElements()) {\n'
            '        const Element* el = elPtr.get();\n'
            '        if (std::find(excluded.begin(), excluded.end(), el) == excluded.end()) {\n'
            '            candidates.push_back(el);\n'
            '        }\n'
            '    }\n\n'
            '    std::optional<AlignmentMatch> best;\n'
            '    double bestDist = tolerance;\n\n'
            '    for (const Element* b: candidates) {\n'
            '        for (const Element* c: candidates) {\n'
            '            if (b == c) {\n'
            '                continue;\n'
            '            }\n'
            '            xoj::util::Rectangle<double> bb = b->getSnappedBounds();\n'
            '            xoj::util::Rectangle<double> cb = c->getSnappedBounds();\n'
            '            if (bb.y + bb.height > cb.y) {\n'
            '                continue;\n'
            '            }\n'
            '            double gap = cb.y - (bb.y + bb.height);\n'
            '            if (gap <= 0) {\n'
            '                continue;\n'
            '            }\n'
            '            double maxStart = std::max({xLeft, bb.x, cb.x});\n'
            '            double minEnd = std::min({xRight, bb.x + bb.width, cb.x + cb.width});\n'
            '            if (maxStart > minEnd) {\n'
            '                continue;\n'
            '            }\n\n'
            '            double unionFrom = std::min({xLeft, bb.x, cb.x});\n'
            '            double unionTo = std::max({xRight, bb.x + bb.width, cb.x + cb.width});\n'
            '            double placement = std::max({xRight, bb.x + bb.width, cb.x + cb.width}) + EQUIDISTANT_ARROW_MARGIN;\n'
            '            double targetTop = bb.y - gap - height;\n'
            '            double distTop = std::abs(targetTop - y);\n'
            '            if (distTop < bestDist) {\n'
            '                bestDist = distTop;\n'
            '                best = AlignmentMatch{targetTop - y, targetTop, unionFrom, unionTo, false, false};\n'
            '                best->equidistantGaps = {{targetTop + height, bb.y}, {bb.y + bb.height, cb.y}};\n'
            '                best->equidistantPlacement = placement;\n'
            '            }\n'
            '            double targetBottom = cb.y + cb.height + gap;\n'
            '            double distBottom = std::abs(targetBottom - y);\n'
            '            if (distBottom < bestDist) {\n'
            '                bestDist = distBottom;\n'
            '                best = AlignmentMatch{targetBottom - y, targetBottom, unionFrom, unionTo, false, false};\n'
            '                best->equidistantGaps = {{bb.y + bb.height, cb.y}, {cb.y + cb.height, targetBottom}};\n'
            '                best->equidistantPlacement = placement;\n'
            '            }\n'
            '        }\n'
            '    }\n'
            '    return best;\n'
            '}\n',
        label="EditSelection.cpp: findEquidistantX/Y remplissent les nouveaux champs",
    )

    # ============ 4. mouseMove(): copie des champs vers AlignmentGuide (2 occurrences) ============
    text = cpp.read_text(encoding="utf-8")
    old4 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted}'
    new4 = 'AlignmentGuide{g.coordinate, g.extentFrom, g.extentTo, g.isCenter, g.isBoosted, g.equidistantGaps, g.equidistantPlacement}'
    n4 = text.count(old4)
    if n4 == 2:
        text = text.replace(old4, new4)
        cpp.write_text(text, encoding="utf-8")
        print(f"[OK]    EditSelection.cpp: mouseMove() copie equidistantGaps/Placement ({n4} occurrences)")
    elif text.count(new4) > 0:
        print("[SKIP]  EditSelection.cpp: mouseMove() deja a jour.")
    else:
        print(f"[ECHEC] EditSelection.cpp: mouseMove() - motif trouve {n4} fois (attendu 2)")
        ok = False

    # ============ 5. drawDoubleArrow() avant paint() ============
    ok &= apply_edit(
        cpp,
        old='void EditSelection::paint(cairo_t* cr, double zoom) {',
        new='/**\n'
            ' * Draws a double-headed arrow from (x1, y1) to (x2, y2) (already in screen/pixel coordinates, i.e.\n'
            ' * pre-multiplied by zoom) on `cr`, using whatever source color/line width is currently set. Used to\n'
            ' * illustrate an equidistant ("equal spacing") match - see findEquidistantX/Y() and paint().\n'
            ' */\n'
            'static void drawDoubleArrow(cairo_t* cr, double x1, double y1, double x2, double y2) {\n'
            '    constexpr double ARROW_HEAD_LENGTH_PX = 7.0;\n'
            '    constexpr double ARROW_HEAD_ANGLE = M_PI / 7.0;  // ~25 degrees between each wing and the shaft\n\n'
            '    cairo_move_to(cr, x1, y1);\n'
            '    cairo_line_to(cr, x2, y2);\n'
            '    cairo_stroke(cr);\n\n'
            '    double angle = std::atan2(y2 - y1, x2 - x1);\n\n'
            '    // Head at (x1, y1), wings pointing back along the shaft (towards (x2, y2)\'s opposite direction).\n'
            '    double back1 = angle + M_PI;\n'
            '    cairo_move_to(cr, x1, y1);\n'
            '    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 - ARROW_HEAD_ANGLE),\n'
            '                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 - ARROW_HEAD_ANGLE));\n'
            '    cairo_move_to(cr, x1, y1);\n'
            '    cairo_line_to(cr, x1 + ARROW_HEAD_LENGTH_PX * std::cos(back1 + ARROW_HEAD_ANGLE),\n'
            '                  y1 + ARROW_HEAD_LENGTH_PX * std::sin(back1 + ARROW_HEAD_ANGLE));\n\n'
            '    // Head at (x2, y2), wings pointing back along the shaft towards (x1, y1).\n'
            '    double back2 = angle;\n'
            '    cairo_move_to(cr, x2, y2);\n'
            '    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 - ARROW_HEAD_ANGLE),\n'
            '                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 - ARROW_HEAD_ANGLE));\n'
            '    cairo_move_to(cr, x2, y2);\n'
            '    cairo_line_to(cr, x2 - ARROW_HEAD_LENGTH_PX * std::cos(back2 + ARROW_HEAD_ANGLE),\n'
            '                  y2 - ARROW_HEAD_LENGTH_PX * std::sin(back2 + ARROW_HEAD_ANGLE));\n'
            '    cairo_stroke(cr);\n'
            '}\n\n'
            'void EditSelection::paint(cairo_t* cr, double zoom) {',
        label="EditSelection.cpp: fonction drawDoubleArrow()",
    )

    # ============ 6. paint(): utilisation des fleches doubles pour les guides equidistants ============
    ok &= apply_edit(
        cpp,
        old='        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, guide.from * zoom, gy);\n'
            '            cairo_line_to(cr, guide.to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n',
        new='        for (auto& guide: this->activeGuidesX) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            if (!guide.equidistantGaps.empty()) {\n'
            '                // Equidistant match: one double-headed arrow per gap in the chain, drawn horizontally\n'
            '                // (this is a horizontal row being equally spaced along X) at a fixed Y offset\n'
            '                // (equidistantPlacement) below the row.\n'
            '                double py = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);\n'
            '                }\n'
            '                continue;\n'
            '            }\n'
            '            double gx = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, gx, guide.from * zoom);\n'
            '            cairo_line_to(cr, gx, guide.to * zoom);\n'
            '            cairo_stroke(cr);\n'
            '        }\n'
            '        for (auto& guide: this->activeGuidesY) {\n'
            '            if (guide.isBoosted) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.55, 1.0);  // vivid electric blue\n'
            '            } else if (guide.isCenter) {\n'
            '                cairo_set_source_rgb(cr, 0.0, 0.8, 0.2);  // green\n'
            '            } else {\n'
            '                cairo_set_source_rgb(cr, 1.0, 0.0, 0.8);  // bright pink\n'
            '            }\n'
            '            if (!guide.equidistantGaps.empty()) {\n'
            '                // Equidistant match: one double-headed arrow per gap in the chain, drawn vertically\n'
            '                // (this is a vertical column being equally spaced along Y) at a fixed X offset\n'
            '                // (equidistantPlacement) to the right of the column.\n'
            '                double px = guide.equidistantPlacement * zoom;\n'
            '                for (auto& [gapFrom, gapTo]: guide.equidistantGaps) {\n'
            '                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);\n'
            '                }\n'
            '                continue;\n'
            '            }\n'
            '            double gy = guide.coordinate * zoom;\n'
            '            cairo_move_to(cr, guide.from * zoom, gy);\n'
            '            cairo_line_to(cr, guide.to * zoom, gy);\n'
            '            cairo_stroke(cr);\n'
            '        }\n',
        label="EditSelection.cpp: paint() dessine les fleches doubles pour l'equidistant",
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
