#!/usr/bin/env python3
"""
Patch 11.10 (phase alignment_snap) : quatre changements distincts.

1. Nouveau cadre "Anchoring assistance" ("Aide a l'ancrage") avant le
   cadre "Functionalities" dans l'onglet Snapping des Preferences,
   contenant une seule case "Object Alignment Snapping" ("Alignement
   des objets par ancrage" en francais), reliee a la meme variable
   (isSnapToObjects()/setSnapToObjects()) que la case du meme nom deja
   presente dans le menu Edition (dont le libelle est desormais
   traduit en francais, partageant la meme traduction gettext que la
   nouvelle case pour rester automatiquement synchronise). Le reste du
   contenu de l'onglet (les deux autres cadres de la page) est grise
   des que cette case est decochee, via le mecanisme deja existant
   enableWithCheckbox() (qui propage via GTK a tous les descendants).

2. Correctif "table centering assist" (findTableCenterX/Y dans
   EditSelection.cpp) : la recherche par paire de lignes paralleles de
   meme longueur pouvait a tort considerer une case formee de 4 cases
   reelles (en sautant une ligne intermediaire) comme une case unique,
   pouvant alors faire tomber la guideline jaune calculee exactement
   sur une des lignes du tableau. Un nouveau filtre rejette desormais
   toute paire pour laquelle une autre ligne se trouve strictement
   entre les deux, ne retenant que la plus petite case possible.

3. La valeur par defaut de "Circle assist tolerance" passe de 6.0 a
   15.0 pixels (constante C++ ET texte affiche dans les Preferences).

4. "Coordinate system assist", "Circle assist" et "Snapping when
   drawing a spline" sont desormais desactives des que la
   fonctionnalite de snapping (isSnapToObjects()) elle-meme est
   desactivee - ils etaient auparavant totalement independants de ce
   commutateur maitre.

Modifie :
  - src/core/control/settings/Settings.h (commentaires mis a jour)
  - src/core/control/settings/Settings.cpp (3 accesseurs regates,
    valeur par defaut 15.0)
  - src/core/gui/dialog/SettingsDialog.cpp (case a cocher, chargement/
    sauvegarde, grisage)
  - src/core/control/tools/EditSelection.cpp (filtre "plus petite
    case")
  - ui/settings.glade (nouveau cadre, renumerotation des positions,
    texte par defaut 15.0)
  - po/xournalpp.pot, po/fr.po (traductions)

NECESSITE : apply_arrow_resize_fix_v2.py, apply_alignment_snap_v90_4.py,
apply_alignment_snap_v11_6.py, apply_alignment_snap_v11_7.py,
apply_alignment_snap_v11_9.py (deja appliques).

A lancer depuis la racine du depot xournalpp, sur le commit
209481caee183798fcae151d125c1ea2d0317b3b (verrouille pour ce
processus).
"""
import sys
from pathlib import Path

SETTINGS_H_OLD0 = """    void setPageCenteringSnappingEnabled(bool b);

    /// Patch 10.4: gates the line-crossing snap assist during shape drawing (see
    /// BaseShapeHandler::applyLineCrossingSnap(), patch 8.4) - independent of the object alignment
    /// snapping system entirely (does not depend on isSnapToObjects()).
    bool isCoordinateSystemAssistEnabled() const;
    void setCoordinateSystemAssistEnabled(bool b);

    /// Patch 10.5: gates the \"diagonal snap\" perfect-circle assist during ellipse drawing (see
    /// EllipseHandler::createShape(), patch 8.5) - independent of the object alignment snapping
    /// system entirely (does not depend on isSnapToObjects()).
    bool isCircleAssistEnabled() const;
    void setCircleAssistEnabled(bool b);
"""
SETTINGS_H_NEW0 = """    void setPageCenteringSnappingEnabled(bool b);

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
SETTINGS_H_OLD1 = """    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0). Independent of the object alignment
    /// snapping system entirely (does not depend on isSnapToObjects()) - matches how patch 8.9.0 was
    /// designed as a standalone feature for a different tool.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);
"""
SETTINGS_H_NEW1 = """    void setTableContentCenteringAssistEnabled(bool b);

    /// Patch 10.9: gates the ordinary (green/pink) alignment snap for the spline tool's moving point
    /// (see SplineHandler::onMotionNotifyEvent(), patch 8.9.0).
    /// Patch 11.10: now also gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
    /// independent of it.
    bool isSplineSnappingEnabled() const;
    void setSplineSnappingEnabled(bool b);
"""
SETTINGS_H_OLD2 = """    bool pageCenteringSnappingEnabled{};

    /**
     * Patch 10.4: whether the line-crossing snap assist during shape drawing is enabled.
     * Independent of the object alignment snapping system - see
     * isCoordinateSystemAssistEnabled() above.
     */
    bool coordinateSystemAssistEnabled{};

    /**
     * Patch 10.5: whether the perfect-circle \"diagonal snap\" assist during ellipse drawing is
     * enabled. Independent of the object alignment snapping system - see isCircleAssistEnabled()
     * above.
     */
    bool circleAssistEnabled{};
"""
SETTINGS_H_NEW2 = """    bool pageCenteringSnappingEnabled{};

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
SETTINGS_H_OLD3 = """    bool tableContentCenteringAssistEnabled{};

    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled.
     * Independent of the object alignment snapping system - see isSplineSnappingEnabled() above.
     */
    bool splineSnappingEnabled{};
"""
SETTINGS_H_NEW3 = """    bool tableContentCenteringAssistEnabled{};

    /**
     * Patch 10.9: whether the spline tool's ordinary (green/pink) alignment snap is enabled, as
     * stored/persisted. Patch 11.10: the getter isSplineSnappingEnabled() above additionally requires
     * isSnapToObjects() to also be true - this raw field alone does not reflect that.
     */
    bool splineSnappingEnabled{};
"""
SETTINGS_CPP_OLD0 = """    this->lineCrossSnapTolerancePx = 6.0;
    this->lineCrossMinLength = 50.0;
    this->splineAlignmentSnapTolerancePx = 6.0;
    this->diagonalSnapTolerancePx = 6.0;
    this->perpendicularCrossBoostFactor = 4.0;
    this->lineEndAnchorToleranceFactor = 0.9;
    this->smallMarkMaxLength = 15.0;"""
SETTINGS_CPP_NEW0 = """    this->lineCrossSnapTolerancePx = 6.0;
    this->lineCrossMinLength = 50.0;
    this->splineAlignmentSnapTolerancePx = 6.0;
    this->diagonalSnapTolerancePx = 15.0;
    this->perpendicularCrossBoostFactor = 4.0;
    this->lineEndAnchorToleranceFactor = 0.9;
    this->smallMarkMaxLength = 15.0;"""
SETTINGS_CPP_OLD1 = """    save();
}

auto Settings::isCoordinateSystemAssistEnabled() const -> bool { return this->coordinateSystemAssistEnabled; }

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {"""
SETTINGS_CPP_NEW1 = """    save();
}

// Patch 11.10: now gated on isSnapToObjects() (the master \"snapping\" toggle) - previously
// independent of it (see the (now outdated) doc comment on the header declaration).
auto Settings::isCoordinateSystemAssistEnabled() const -> bool {
    return this->snapToObjects && this->coordinateSystemAssistEnabled;
}

void Settings::setCoordinateSystemAssistEnabled(bool b) {
    if (this->coordinateSystemAssistEnabled == b) {"""
SETTINGS_CPP_OLD2 = """    save();
}

auto Settings::isCircleAssistEnabled() const -> bool { return this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {"""
SETTINGS_CPP_NEW2 = """    save();
}

// Patch 11.10: see isCoordinateSystemAssistEnabled()'s own comment just above.
auto Settings::isCircleAssistEnabled() const -> bool { return this->snapToObjects && this->circleAssistEnabled; }

void Settings::setCircleAssistEnabled(bool b) {
    if (this->circleAssistEnabled == b) {"""
SETTINGS_CPP_OLD3 = """    save();
}

auto Settings::isSplineSnappingEnabled() const -> bool { return this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {"""
SETTINGS_CPP_NEW3 = """    save();
}

// Patch 11.10: see isCoordinateSystemAssistEnabled()'s own comment above (near line 1730).
auto Settings::isSplineSnappingEnabled() const -> bool { return this->snapToObjects && this->splineSnappingEnabled; }

void Settings::setSplineSnappingEnabled(bool b) {
    if (this->splineSnappingEnabled == b) {"""
DIALOG_OLD0 = """            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

    g_signal_connect_swapped(builder.get(\"cbGraduationAssist\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
                             }),"""
DIALOG_NEW0 = """            builder.get(\"cbAutosave\"), \"toggled\",
            G_CALLBACK(+[](SettingsDialog* self) { self->enableWithCheckbox(\"cbAutosave\", \"boxAutosave\"); }), this);

    // Patch 11.10: greys out the whole rest of the snapping tab (both remaining top-level frames -
    // GTK propagates \"sensitive\" to all their descendants automatically) whenever the master toggle
    // is unchecked.
    g_signal_connect_swapped(builder.get(\"cbObjectAlignmentSnapping\"), \"toggled\",
                             G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingFunctionalitiesFrame\");
                                 self->enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingSettingsFrame\");
                             }),
                             this);

    g_signal_connect_swapped(builder.get(\"cbGraduationAssist\"), \"toggled\", G_CALLBACK(+[](SettingsDialog* self) {
                                 self->enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
                             }),"""
DIALOG_OLD1 = """    loadCheckbox(\"cbShowScrollbarLeft\", settings->isScrollbarOnLeft());
    loadCheckbox(\"cbAutoloadMostRecent\", settings->isAutoloadMostRecent());
    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());"""
DIALOG_NEW1 = """    loadCheckbox(\"cbShowScrollbarLeft\", settings->isScrollbarOnLeft());
    loadCheckbox(\"cbAutoloadMostRecent\", settings->isAutoloadMostRecent());
    loadCheckbox(\"cbAutoloadXoj\", settings->isAutoloadPdfXoj());
    // Patch 11.10: master toggle for the whole object alignment snapping system - mirrors the \"Edit\"
    // menu's own \"Object Alignment Snapping\" toggle (same underlying setting).
    loadCheckbox(\"cbObjectAlignmentSnapping\", settings->isSnapToObjects());
    loadCheckbox(\"cbEquidistantAssist\", settings->isEquidistantSnappingEnabled());
    loadCheckbox(\"cbPageCenteringAssist\", settings->isPageCenteringSnappingEnabled());
    loadCheckbox(\"cbCoordinateSystemAssist\", settings->isCoordinateSystemAssistEnabled());"""
DIALOG_OLD2 = """    disableWithCheckbox(\"cbUnlimitedScrolling\", \"cbAddHorizontalSpace\");

    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
    enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
    enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
    enableWithEnabledCheckbox(\"cbAddVerticalSpace\", \"spAddVerticalSpaceAbove\");"""
DIALOG_NEW2 = """    disableWithCheckbox(\"cbUnlimitedScrolling\", \"cbAddHorizontalSpace\");

    enableWithCheckbox(\"cbAutosave\", \"boxAutosave\");
    // Patch 11.10
    enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingFunctionalitiesFrame\");
    enableWithCheckbox(\"cbObjectAlignmentSnapping\", \"snapingSettingsFrame\");
    enableWithCheckbox(\"cbGraduationAssist\", \"cbGraduationOrientation\");
    enableWithCheckbox(\"cbIgnoreFirstStylusEvents\", \"spNumIgnoredStylusEvents\");
    enableWithEnabledCheckbox(\"cbAddVerticalSpace\", \"spAddVerticalSpaceAbove\");"""
DIALOG_OLD3 = """    settings->setScrollbarOnLeft(getCheckbox(\"cbShowScrollbarLeft\"));
    settings->setAutoloadMostRecent(getCheckbox(\"cbAutoloadMostRecent\"));
    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));"""
DIALOG_NEW3 = """    settings->setScrollbarOnLeft(getCheckbox(\"cbShowScrollbarLeft\"));
    settings->setAutoloadMostRecent(getCheckbox(\"cbAutoloadMostRecent\"));
    settings->setAutoloadPdfXoj(getCheckbox(\"cbAutoloadXoj\"));
    // Patch 11.10: goes through Control (not settings directly), so the \"Edit\" menu's own checked
    // state (a GAction, tracked separately from the settings value) stays in sync too - matching
    // exactly what toggling the menu item itself does (see
    // ActionProperties<Action::OBJECT_ALIGNMENT_SNAPPING>::callback()).
    this->control->setObjectAlignmentSnapping(getCheckbox(\"cbObjectAlignmentSnapping\"));
    settings->setEquidistantSnappingEnabled(getCheckbox(\"cbEquidistantAssist\"));
    settings->setPageCenteringSnappingEnabled(getCheckbox(\"cbPageCenteringAssist\"));
    settings->setCoordinateSystemAssistEnabled(getCheckbox(\"cbCoordinateSystemAssist\"));"""
ES_OLD0 = """            if (std::abs(left.height - right.height) > tolerance) {
                continue;  // same length, within the usual tolerance
            }
            double midpoint = (left.x + right.x) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {"""
ES_NEW0 = """            if (std::abs(left.height - right.height) > tolerance) {
                continue;  // same length, within the usual tolerance
            }
            // Patch 11.10: reject this pair if it isn't the smallest possible cell - i.e. if some
            // other vertical line on the layer lies strictly between them. Without this check, a
            // 2x2 (or larger) block of same-length lines could be mistaken for a single wide \"cell\"
            // spanning multiple real columns, and the resulting guideline could land exactly on top
            // of one of the table's own intermediate lines.
            bool hasLineBetween = false;
            for (size_t k = 0; k < verticalLines.size(); ++k) {
                if (k == i || k == j) {
                    continue;
                }
                if (verticalLines[k].x > left.x && verticalLines[k].x < right.x) {
                    hasLineBetween = true;
                    break;
                }
            }
            if (hasLineBetween) {
                continue;
            }
            double midpoint = (left.x + right.x) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {"""
ES_OLD1 = """            if (std::abs(top.width - bottom.width) > tolerance) {
                continue;
            }
            double midpoint = (top.y + bottom.y) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {"""
ES_NEW1 = """            if (std::abs(top.width - bottom.width) > tolerance) {
                continue;
            }
            // Patch 11.10: see findTableCenterX()'s own comment above - mirrored here for the Y axis.
            bool hasLineBetween = false;
            for (size_t k = 0; k < horizontalLines.size(); ++k) {
                if (k == i || k == j) {
                    continue;
                }
                if (horizontalLines[k].y > top.y && horizontalLines[k].y < bottom.y) {
                    hasLineBetween = true;
                    break;
                }
            }
            if (hasLineBetween) {
                continue;
            }
            double midpoint = (top.y + bottom.y) / 2;
            double dist = std::abs(selfCenter - midpoint);
            if (dist < bestDist) {"""
GLADE_OLD0 = """                        <property name=\"can-focus\">False</property>
                        <child>
                          <object class=\"GtkBox\" id=\"snapingContentBox\">
                            <property name=\"visible\">True</property>
                            <property name=\"can-focus\">False</property>
                            <property name=\"margin-start\">10</property>
                            <property name=\"margin-end\">10</property>
                            <property name=\"margin-top\">10</property>
                            <property name=\"margin-bottom\">10</property>
                            <property name=\"orientation\">vertical</property>
                            <property name=\"spacing\">10</property>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingFunctionalitiesFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingFunctionalitiesBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>"""
GLADE_NEW0 = """                        <property name=\"can-focus\">False</property>
                        <child>
                          <object class=\"GtkBox\" id=\"snapingContentBox\">
                            <property name=\"visible\">True</property>
                            <property name=\"can-focus\">False</property>
                            <property name=\"margin-start\">10</property>
                            <property name=\"margin-end\">10</property>
                            <property name=\"margin-top\">10</property>
                            <property name=\"margin-bottom\">10</property>
                            <property name=\"orientation\">vertical</property>
                            <property name=\"spacing\">10</property>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingMasterFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingMasterBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>
                                    <child>
                                      <object class=\"GtkCheckButton\" id=\"cbObjectAlignmentSnapping\">
                                        <property name=\"label\" translatable=\"yes\">Object Alignment Snapping</property>
                                        <property name=\"name\">cbObjectAlignmentSnapping</property>
                                        <property name=\"visible\">True</property>
                                        <property name=\"can-focus\">True</property>
                                        <property name=\"receives-default\">False</property>
                                        <property name=\"draw-indicator\">True</property>
                                      </object>
                                      <packing>
                                        <property name=\"expand\">False</property>
                                        <property name=\"fill\">True</property>
                                        <property name=\"position\">0</property>
                                      </packing>
                                    </child>
                                  </object>
                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingMasterLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Anchoring assistance</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingFunctionalitiesFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingFunctionalitiesBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>
                                    <property name=\"margin-end\">12</property>
                                    <property name=\"margin-bottom\">8</property>
                                    <property name=\"orientation\">vertical</property>"""
GLADE_OLD1 = """                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingFunctionalitiesLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Functionalities</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">0</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingSettingsFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingSettingsBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>"""
GLADE_NEW1 = """                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingFunctionalitiesLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Functionalities</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">1</property>
                              </packing>
                            </child>
                            <child>
                              <object class=\"GtkFrame\" id=\"snapingSettingsFrame\">
                                <property name=\"visible\">True</property>
                                <property name=\"can-focus\">False</property>
                                <property name=\"label-xalign\">0.0099999997764825821</property>
                                <child>
                                  <object class=\"GtkBox\" id=\"snapingSettingsBox\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"margin-start\">12</property>"""
GLADE_OLD2 = """                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblDiagonalSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 6.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">8</property>"""
GLADE_NEW2 = """                                                    <property name=\"width-chars\">8</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">1</property>
                                                  </packing>
                                                </child>
                                                <child>
                                                  <object class=\"GtkLabel\" id=\"lblDiagonalSnapToleranceDefault\">
                                                    <property name=\"visible\">True</property>
                                                    <property name=\"can-focus\">False</property>
                                                    <property name=\"label\" translatable=\"yes\">(default: 15.0)</property>
                                                  </object>
                                                  <packing>
                                                    <property name=\"expand\">False</property>
                                                    <property name=\"fill\">True</property>
                                                    <property name=\"position\">2</property>
                                                  </packing>
                                                </child>
                                              </object>
                                              <packing>
                                                <property name=\"expand\">False</property>
                                                <property name=\"fill\">True</property>
                                                <property name=\"position\">8</property>"""
GLADE_OLD3 = """                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingSettingsLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Settings</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">1</property>
                              </packing>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                  <packing>
                    <property name=\"expand\">True</property>
                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>"""
GLADE_NEW3 = """                                </child>
                                <child type=\"label\">
                                  <object class=\"GtkLabel\" id=\"snapingSettingsLabel\">
                                    <property name=\"visible\">True</property>
                                    <property name=\"can-focus\">False</property>
                                    <property name=\"label\" translatable=\"yes\">Settings</property>
                                  </object>
                                </child>
                              </object>
                              <packing>
                                <property name=\"expand\">False</property>
                                <property name=\"fill\">True</property>
                                <property name=\"position\">2</property>
                              </packing>
                            </child>
                          </object>
                        </child>
                      </object>
                    </child>
                  </object>
                  <packing>
                    <property name=\"expand\">True</property>
                    <property name=\"fill\">True</property>
                    <property name=\"position\">0</property>
                  </packing>"""
POT_OLD0 = """msgid \"Grid Snapping\"
msgstr \"\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"\""""
POT_NEW0 = """msgid \"Grid Snapping\"
msgstr \"\"

#: ../ui/mainmenubar.xml:159 ../ui/settings.glade:5766
msgid \"Object Alignment Snapping\"
msgstr \"\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"\""""
POT_OLD1 = """msgid \"<i>While drawing a spline, snaps its moving point to the edges and centers of nearby objects.</i>\"
msgstr \"\"

#: ../ui/settings.glade:6035
msgid \"Functionalities\"
msgstr \"\""""
POT_NEW1 = """msgid \"<i>While drawing a spline, snaps its moving point to the edges and centers of nearby objects.</i>\"
msgstr \"\"

#: ../ui/settings.glade:5785
msgid \"Anchoring assistance\"
msgstr \"\"

#: ../ui/settings.glade:6035
msgid \"Functionalities\"
msgstr \"\""""
FR_OLD0 = """msgid \"Grid Snapping\"
msgstr \"Ancrage à la grille\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"Pages liées\""""
FR_NEW0 = """msgid \"Grid Snapping\"
msgstr \"Ancrage à la grille\"

#: ../ui/mainmenubar.xml:159 ../ui/settings.glade:5766
msgid \"Object Alignment Snapping\"
msgstr \"Alignement des objets par ancrage\"

#: ../ui/settings.glade:5785
msgid \"Anchoring assistance\"
msgstr \"Aide à l'ancrage\"

#: ../src/core/gui/toolbarMenubar/ToolMenuHandler.cpp:326
msgid \"Paired pages\"
msgstr \"Pages liées\""""


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
        "dialog": Path("src/core/gui/dialog/SettingsDialog.cpp"),
        "es": Path("src/core/control/tools/EditSelection.cpp"),
        "glade": Path("ui/settings.glade"),
        "pot": Path("po/xournalpp.pot"),
        "fr": Path("po/fr.po"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "isTableCenter" not in paths["es"].read_text(encoding="utf-8"):
        print("[ECHEC] isTableCenter introuvable dans EditSelection.cpp.")
        print("        Appliquez d'abord les patchs alignment_snap prerequis, puis relancez ce script.")
        sys.exit(1)
    if "cbObjectAlignmentSnapping" in paths["dialog"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 11.10 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD0, SETTINGS_H_NEW0, "settings_h: zone 1/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD1, SETTINGS_H_NEW1, "settings_h: zone 2/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD2, SETTINGS_H_NEW2, "settings_h: zone 3/4")
    ok &= apply_edit(paths["settings_h"], SETTINGS_H_OLD3, SETTINGS_H_NEW3, "settings_h: zone 4/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD0, SETTINGS_CPP_NEW0, "settings_cpp: zone 1/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD1, SETTINGS_CPP_NEW1, "settings_cpp: zone 2/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD2, SETTINGS_CPP_NEW2, "settings_cpp: zone 3/4")
    ok &= apply_edit(paths["settings_cpp"], SETTINGS_CPP_OLD3, SETTINGS_CPP_NEW3, "settings_cpp: zone 4/4")
    ok &= apply_edit(paths["dialog"], DIALOG_OLD0, DIALOG_NEW0, "dialog: zone 1/4")
    ok &= apply_edit(paths["dialog"], DIALOG_OLD1, DIALOG_NEW1, "dialog: zone 2/4")
    ok &= apply_edit(paths["dialog"], DIALOG_OLD2, DIALOG_NEW2, "dialog: zone 3/4")
    ok &= apply_edit(paths["dialog"], DIALOG_OLD3, DIALOG_NEW3, "dialog: zone 4/4")
    ok &= apply_edit(paths["es"], ES_OLD0, ES_NEW0, "es: zone 1/2")
    ok &= apply_edit(paths["es"], ES_OLD1, ES_NEW1, "es: zone 2/2")
    ok &= apply_edit(paths["glade"], GLADE_OLD0, GLADE_NEW0, "glade: zone 1/4")
    ok &= apply_edit(paths["glade"], GLADE_OLD1, GLADE_NEW1, "glade: zone 2/4")
    ok &= apply_edit(paths["glade"], GLADE_OLD2, GLADE_NEW2, "glade: zone 3/4")
    ok &= apply_edit(paths["glade"], GLADE_OLD3, GLADE_NEW3, "glade: zone 4/4")
    ok &= apply_edit(paths["pot"], POT_OLD0, POT_NEW0, "pot: zone 1/2")
    ok &= apply_edit(paths["pot"], POT_OLD1, POT_NEW1, "pot: zone 2/2")
    ok &= apply_edit(paths["fr"], FR_OLD0, FR_NEW0, "fr: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
