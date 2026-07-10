#!/usr/bin/env python3
"""
Patch 11.2.2 (version finale, remplace toute version anterieure du meme
nom) : ajustement visuel de la double fleche du repere equidistant
(patch 8.1.0).

Retire desormais 2.0 px ecran de chaque cote (au lieu de 5.0
initialement), en restant centree sur le meme point median. NOUVEAU :
si l'ecart total entre les objets equidistants est inferieur a 10.0 px
ecran, aucun retrait n'est applique du tout (comportement original,
fleche pleine longueur) - evite que le retrait ne rende la fleche
illisible ou disproportionnee sur de tres petits ecarts.

N'affecte QUE le rendu visuel de cette guideline - les points d'ancrage
et le comportement d'accroche lui-meme ne sont pas touches.

Modifie : src/core/control/tools/EditSelection.cpp (nouvelle fonction +
2 points d'appel, axes X et Y)

NECESSITE : apply_alignment_snap_v90.py + apply_alignment_snap_v11_2.py

A lancer depuis la racine du depot xournalpp (a la place de toute
version precedente de ce meme script - ne pas appliquer les deux).
"""
import sys
from pathlib import Path

OLD_1 = """ */
/**
 * Draws a double-headed arrow from (x1, y1) to (x2, y2) (already in screen/pixel coordinates, i.e.
 * pre-multiplied by zoom) on `cr`, using whatever source color/line width is currently set. Used to
 * illustrate an equidistant (\"equal spacing\") match - see findEquidistantX/Y() and paint().
 */
static void drawDoubleArrow(cairo_t* cr, double x1, double y1, double x2, double y2) {
"""
NEW_1 = """ */
/**
 * Patch 11.2.2: the equidistant guide's double arrow is drawn a little shorter than the full gap it
 * illustrates, symmetrically centered within it, so its two arrowheads sit a bit clear of the objects
 * on either side and remain clearly visible rather than flush against them. Below
 * EQUIDISTANT_ARROW_SHRINK_MIN_GAP_PX, the gap is small enough that shrinking would make the arrow
 * feel cramped or lose the illustration entirely - the original, unshrunk behavior is used instead.
 */
constexpr double EQUIDISTANT_ARROW_SHRINK_PX = 2.0;
constexpr double EQUIDISTANT_ARROW_SHRINK_MIN_GAP_PX = 10.0;

/// Shrinks a [fromPx, toPx] screen-space span by EQUIDISTANT_ARROW_SHRINK_PX on each side, staying
/// centered on the same midpoint - unless the gap is below EQUIDISTANT_ARROW_SHRINK_MIN_GAP_PX, in
/// which case it is returned unchanged (no shrink at all).
static std::pair<double, double> shrinkGapForArrow(double fromPx, double toPx) {
    if (std::abs(toPx - fromPx) < EQUIDISTANT_ARROW_SHRINK_MIN_GAP_PX) {
        return {fromPx, toPx};
    }
    double margin = std::min(EQUIDISTANT_ARROW_SHRINK_PX, std::abs(toPx - fromPx) / 2.0);
    double sign = toPx >= fromPx ? 1.0 : -1.0;
    return {fromPx + sign * margin, toPx - sign * margin};
}

/**
 * Draws a double-headed arrow from (x1, y1) to (x2, y2) (already in screen/pixel coordinates, i.e.
 * pre-multiplied by zoom) on `cr`, using whatever source color/line width is currently set. Used to
 * illustrate an equidistant (\"equal spacing\") match - see findEquidistantX/Y() and paint().
 */
static void drawDoubleArrow(cairo_t* cr, double x1, double y1, double x2, double y2) {
"""
OLD_2 = """                    drawDoubleArrow(cr, gapFrom * zoom, py, gapTo * zoom, py);
"""
NEW_2 = """                    auto [shrunkFrom, shrunkTo] = shrinkGapForArrow(gapFrom * zoom, gapTo * zoom);
                    drawDoubleArrow(cr, shrunkFrom, py, shrunkTo, py);
"""
OLD_3 = """                    drawDoubleArrow(cr, px, gapFrom * zoom, px, gapTo * zoom);
"""
NEW_3 = """                    auto [shrunkFrom, shrunkTo] = shrinkGapForArrow(gapFrom * zoom, gapTo * zoom);
                    drawDoubleArrow(cr, px, shrunkFrom, px, shrunkTo);
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


def main():
    cpp = Path("src/core/control/tools/EditSelection.cpp")
    if not cpp.exists():
        print("[ECHEC] EditSelection.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "drawDoubleArrow" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] drawDoubleArrow introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v90.py (+ v11_2.py), puis relancez ce script.")
        sys.exit(1)
    if "EQUIDISTANT_ARROW_SHRINK_MIN_GAP_PX" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.2.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "EditSelection.cpp: ajout de shrinkGapForArrow() (2px, seuil 10px)")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "EditSelection.cpp: application au repere horizontal (axe X)")
    ok &= apply_edit(cpp, OLD_3, NEW_3, "EditSelection.cpp: application au repere vertical (axe Y)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
