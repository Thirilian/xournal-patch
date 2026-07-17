#!/usr/bin/env python3
"""
Patch 11.10.2 : CORRECTIF - bug signale par l'utilisateur : le patch
11.10 decochait a tort les cases "Coordinate system assist", "Circle
assist" et "Snapping when drawing a spline" dans les Preferences des
que "Object Alignment Snapping" etait desactivee - alors que seule
leur FONCTIONNALITE doit s'arreter, leur propre case doit rester
cochee si elle l'etait.

CAUSE : le patch 11.10 gatait isSnapToObjects() DANS le getter
lui-meme (Settings::isCoordinateSystemAssistEnabled() etc.) - or ce
meme getter est aussi utilise par SettingsDialog::load() pour
initialiser l'etat AFFICHE de la case a cocher, qui se retrouvait donc
decochee des que le commutateur maitre etait desactive, meme si la
preference propre de l'utilisateur restait cochee.

CORRECTIF : les 3 getters sont rendus a leur simple lecture directe de
la valeur stockee (comportement d'origine, identique a
isEquidistantSnappingEnabled()/isPageCenteringSnappingEnabled(), qui
n'avaient jamais ce probleme). Le controle isSnapToObjects() est
deplace au niveau des points d'appel FONCTIONNELS reels :
  - BaseShapeHandler::applyLineCrossingSnap() (coordinate system
    assist)
  - EllipseHandler::createShape() (circle assist)
  - SplineHandler::onMotionNotifyEvent() (spline snapping)

Modifie :
  - src/core/control/settings/Settings.h (commentaires corriges)
  - src/core/control/settings/Settings.cpp (3 getters revertis)
  - src/core/control/tools/BaseShapeHandler.cpp,
    EllipseHandler.cpp, SplineHandler.cpp (gate ajoute au point
    d'appel reel)

NECESSITE : apply_alignment_snap_v11_10.py et
apply_alignment_snap_v11_10_1.py (deja appliques).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

SETTINGS_H_OLD0 = """    void setPageCenteringSnappingEnabled(bool b);

    /// Patch 10.4: gates the line-crossing snap assist during shape drawing (see
    /// BaseShapeHandler::applyLineCrossingSnap(), patch 8.4).
    /// Patch 11.10: now also gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
    /// independent of it.
    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

    /// Patch 10.5: gates the \"diagonal snap\" perfect-circle assist during ellipse drawing (see
    /// EllipseHandler::createShape(), patch 8.5).
    /// Patch 11.10: now also gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
    /// independent of it.
    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);
"""
SETTINGS_H_NEW0 = """    void setPageCenteringSnappingEnabled(bool b);

    /// Patch 10.4: gates the line-crossing snap assist during shape drawing (see
    /// BaseShapeHandler::applyLineCrossingSnap(), patch 8.4). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

    /// Patch 10.5: gates the \"diagonal snap\" perfect-circle assist during ellipse drawing (see
    /// EllipseHandler::createShape(), patch 8.5). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);
"""
SETTINGS_H_OLD1 = """    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0).
    /// Patch 11.10: now also gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
    /// independent of it.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);
"""
SETTINGS_H_NEW1 = """    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0). This getter alone is independent of
    /// isSnapToObjects() (patch 11.10.2) - the call site additionally checks that too, so the
    /// feature stops working while the master toggle is off without unchecking (or otherwise
    /// altering) this setting's own stored/displayed value.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);
"""
SETTINGS_H_OLD2 = """
    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled, as
     * stored/persisted. Patch 11.10: the getter isCoordinateSystemAssistEnabled() above additionally
     * requires isSnapToObjects() to also be true - this raw field alone does not reflect that.
     */
    bool coordinateSystemAssistEnabled{};

    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled, as stored/persisted. Patch 11.10: the getter isCircleAssistEnabled() above
     * additionally requires isSnapToObjects() to also be true - this raw field alone does not
     * reflect that.
     */
    bool circleAssistEnabled{};
"""
SETTINGS_H_NEW2 = """
    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled, as
     * stored/persisted (and displayed in Preferences). Patch 11.10.2: the isSnapToObjects() gate is
     * applied only at the actual call site (BaseShapeHandler::applyLineCrossingSnap()), never here -
     * this field, and the getter above, always reflect the user's own raw preference untouched.
     */
    bool coordinateSystemAssistEnabled{};

    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled, as stored/persisted (and displayed in Preferences). Patch 11.10.2: the
     * isSnapToObjects() gate is applied only at the actual call site (EllipseHandler::createShape()),
     * never here - this field, and the getter above, always reflect the user's own raw preference
     * untouched.
     */
    bool circleAssistEnabled{};
"""
SETTINGS_H_OLD3 = """
    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled, as
     * stored/persisted. Patch 11.10: the getter isSplineSnappingEnabled() above additionally requires
     * isSnapToObjects() to also be true - this raw field alone does not reflect that.
     */
    bool splineSnappingEnabled{};
"""
SETTINGS_H_NEW3 = """
    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled, as
     * stored/persisted (and displayed in Preferences). Patch 11.10.2: the isSnapToObjects() gate is
     * applied only at the actual call site (SplineHandler::onMotionNotifyEvent()), never here - this
     * field, and the getter above, always reflect the user's own raw preference untouched.
     */
    bool splineSnappingEnabled{};
"""
SETTINGS_CPP_OLD0 = """    save();
}

// Patch 11.10: now gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
// independent of it (see the (now outdated) doc comment on the header declaration).
auto Settings::isCoordinateSystemAssistEnabled() const -> bool {
    return this->snapToObjects && this->coordinateSystemAssistEnabled;
}

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {"""
SETTINGS_CPP_NEW0 = """    save();
}

// Patch 11.10.2: CORRECTIF - reverted back to a plain pass-through of the raw stored value. Gating
// this getter itself on isSnapToObjects() (as patch 11.10 originally did) also affected
// SettingsDialog::load(), which uses this same getter to populate the checkbox's displayed state -
// unchecking it in the UI whenever the master toggle happened to be off, even if the user's own
// stored preference was still checked. The gating now happens at the actual call site instead (see
// BaseShapeHandler::applyLineCrossingSnap()), leaving this getter - and therefore the checkbox's own
// displayed/persisted state - entirely independent of isSnapToObjects().
auto Settings::isCoordinateSystemAssistEnabled() const -> bool { return this->coordinateSystemAssistEnabled; }

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {"""
SETTINGS_CPP_OLD1 = """    save();
}

// Patch 11.10: see isCoordinateSystemAssistEnabled()'s own comment just above.
auto Settings::isCircleAssistEnabled() const -> bool { return this->snapToObjects && this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {"""
SETTINGS_CPP_NEW1 = """    save();
}

// Patch 11.10.2: see isCoordinateSystemAssistEnabled()'s own comment just above.
auto Settings::isCircleAssistEnabled() const -> bool { return this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {"""
SETTINGS_CPP_OLD2 = """    save();
}

// Patch 11.10: see isCoordinateSystemAssistEnabled()'s own comment above (near line 1730).
auto Settings::isSplineSnappingEnabled() const -> bool { return this->snapToObjects && this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {"""
SETTINGS_CPP_NEW2 = """    save();
}

// Patch 11.10.2: see isCoordinateSystemAssistEnabled()'s own comment above (near line 1730).
auto Settings::isSplineSnappingEnabled() const -> bool { return this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {"""
SHAPE_OLD0 = """auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    if (control != nullptr && control->getSettings() != nullptr &&
        !control->getSettings()->isCoordinateSystemAssistEnabled()) {
        return rawEnd;
    }
"""
SHAPE_NEW0 = """auto BaseShapeHandler::applyLineCrossingSnap(Point rawEnd) -> Point {
    this->lineCrossingGuide.reset();

    // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than inside the
    // getter itself - see Settings::isCoordinateSystemAssistEnabled()'s own doc comment for why.
    if (control != nullptr && control->getSettings() != nullptr &&
        (!control->getSettings()->isSnapToObjects() ||
         !control->getSettings()->isCoordinateSystemAssistEnabled())) {
        return rawEnd;
    }
"""
ELLIPSE_OLD0 = """        // while snapped, since both dimensions grow/shrink together; if they drift too far apart
        // again, the snap (and the guide) releases.
        this->diagonalSnapGuide.reset();
        bool circleAssistEnabled = control == nullptr || control->getSettings() == nullptr ||
                                    control->getSettings()->isCircleAssistEnabled();
        double diagonalSnapTolerancePx =
                (control != nullptr && control->getSettings() != nullptr)
                        ? control->getSettings()->getDiagonalSnapTolerancePx()"""
ELLIPSE_NEW0 = """        // while snapped, since both dimensions grow/shrink together; if they drift too far apart
        // again, the snap (and the guide) releases.
        this->diagonalSnapGuide.reset();
        // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than inside
        // Settings::isCircleAssistEnabled() itself - see that getter's own doc comment for why.
        bool circleAssistEnabled = control == nullptr || control->getSettings() == nullptr ||
                                    (control->getSettings()->isSnapToObjects() &&
                                     control->getSettings()->isCircleAssistEnabled());
        double diagonalSnapTolerancePx =
                (control != nullptr && control->getSettings() != nullptr)
                        ? control->getSettings()->getDiagonalSnapTolerancePx()"""
SPLINE_OLD0 = """            std::optional<SplinePointAlignmentMatch> matchX;
            std::optional<SplinePointAlignmentMatch> matchY;
            Layer* layer = this->page->getSelectedLayer();
            if (layer != nullptr && control->getSettings() != nullptr &&
                control->getSettings()->isSplineSnappingEnabled()) {
                xoj::util::Rectangle<double>* visibleRectPtr =
                        this->control->getWindow()->getXournal()->getVisibleRect(this->control->getCurrentPageNo());
                if (visibleRectPtr != nullptr) {"""
SPLINE_NEW0 = """            std::optional<SplinePointAlignmentMatch> matchX;
            std::optional<SplinePointAlignmentMatch> matchY;
            Layer* layer = this->page->getSelectedLayer();
            // Patch 11.10.2: gated on isSnapToObjects() here (the actual call site) rather than
            // inside Settings::isSplineSnappingEnabled() itself - see that getter's own doc comment
            // for why.
            if (layer != nullptr && control->getSettings() != nullptr &&
                control->getSettings()->isSnapToObjects() && control->getSettings()->isSplineSnappingEnabled()) {
                xoj::util::Rectangle<double>* visibleRectPtr =
                        this->control->getWindow()->getXournal()->getVisibleRect(this->control->getCurrentPageNo());
                if (visibleRectPtr != nullptr) {"""


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
    paths = {
        "settings_h": Path("src/core/control/settings/Settings.h"),
        "settings_cpp": Path("src/core/control/settings/Settings.cpp"),
        "shape": Path("src/core/control/tools/BaseShapeHandler.cpp"),
        "ellipse": Path("src/core/control/tools/EllipseHandler.cpp"),
        "spline": Path("src/core/control/tools/SplineHandler.cpp"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "cbObjectAlignmentSnapping" not in Path("src/core/gui/dialog/SettingsDialog.cpp").read_text(encoding="utf-8"):
        print("[ECHEC] cbObjectAlignmentSnapping introuvable dans SettingsDialog.cpp.")
        print("        Appliquez d'abord apply_alignment_snap_v11_10.py et v11_10_1.py.")
        sys.exit(1)
    if "Patch 11.10.2" in paths["settings_cpp"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.10.2 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD0, SETTINGS_H_NEW0, "settings_h: zone 1/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD1, SETTINGS_H_NEW1, "settings_h: zone 2/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD2, SETTINGS_H_NEW2, "settings_h: zone 3/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD3, SETTINGS_H_NEW3, "settings_h: zone 4/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD0, SETTINGS_CPP_NEW0, "settings_cpp: zone 1/3")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD1, SETTINGS_CPP_NEW1, "settings_cpp: zone 2/3")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD2, SETTINGS_CPP_NEW2, "settings_cpp: zone 3/3")
    ok &= apply_edit(paths["shape"], SHAPE_OLD0, SHAPE_NEW0, "shape: zone 1/1")
    ok &= apply_edit(paths["ellipse"], ELLIPSE_OLD0, ELLIPSE_NEW0, "ellipse: zone 1/1")
    ok &= apply_edit(paths["spline"], SPLINE_OLD0, SPLINE_NEW0, "spline: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
