#!/usr/bin/env python3
"""
Fait suivre le curseur a un objet colle (Ctrl+V), interne ou externe, jusqu'au
prochain clic gauche, et remplace le placement au centre de l'ecran par un
placement sous le curseur quand c'est possible.

Contrairement aux versions precedentes de cette fonctionnalite, ce patch est
autonome : il reutilise le mecanisme de glisser-depose deja present dans
EditSelection (mouseDown/mouseMove, deja actif sur simple mouvement de souris
des que isMoving() est vrai, sans besoin que le bouton soit maintenu) plutot
que d'ajouter un nouveau flag par page. Aucune dependance sur un patch
precedent.

A lancer depuis la racine du depot xournalpp, sur une copie non modifiee.
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
    f = Path("src/core/control/Control.cpp")
    if not f.exists():
        print(f"[ECHEC] {f} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    ok = True

    # --- includes ---
    ok &= apply_edit(
        f,
        old='#include "gui/FloatingToolbox.h"                                 // for Floa...\n'
            '#include "gui/MainWindow.h"                                      // for Main...\n'
            '#include "gui/PageView.h"                                        // for XojP...\n'
            '#include "gui/PdfFloatingToolbox.h"                              // for PdfF...\n'
            '#include "gui/SearchBar.h"                                       // for Sear...\n'
            '#include "gui/XournalView.h"                                     // for Xour...\n'
            '#include "gui/XournalppCursor.h"                                 // for Xour...\n',
        new='#include "gui/FloatingToolbox.h"                                 // for Floa...\n'
            '#include "gui/Layout.h"                                          // for Layout\n'
            '#include "gui/MainWindow.h"                                      // for Main...\n'
            '#include "gui/PageView.h"                                        // for XojP...\n'
            '#include "gui/PdfFloatingToolbox.h"                              // for PdfF...\n'
            '#include "gui/SearchBar.h"                                       // for Sear...\n'
            '#include "gui/XournalView.h"                                     // for Xour...\n'
            '#include "gui/XournalppCursor.h"                                 // for Xour...\n'
            '#include "gui/widgets/XournalWidget.h"                           // for GTK_XOURNAL\n',
        label="Control.cpp: includes Layout.h / XournalWidget.h",
    )

    # --- clipboardPaste(): helper functions + cursor-based spawn + follow ---
    ok &= apply_edit(
        f,
        old='    clipboardPaste(std::move(image));\n'
            '}\n\n'
            'void Control::clipboardPaste(ElementPtr e) {\n'
            '    double x = 0;\n'
            '    double y = 0;\n'
            '    auto pageNr = getCurrentPageNo();\n'
            '    if (pageNr == npos) {\n'
            '        return;\n'
            '    }\n\n'
            '    XojPageView* view = win->getXournal()->getViewFor(pageNr);\n'
            '    if (view == nullptr) {\n'
            '        return;\n'
            '    }\n\n'
            '    this->doc->lock_shared();\n'
            '    PageRef page = this->doc->getPage(pageNr);\n'
            '    Layer* layer = page->getSelectedLayer();\n'
            '    this->doc->unlock_shared();\n\n'
            '    win->getXournal()->getPasteTarget(x, y);\n\n'
            '    double width = e->getElementWidth();\n'
            '    double height = e->getElementHeight();\n\n'
            '    x = std::max(0.0, x - width / 2);\n'
            '    y = std::max(0.0, y - height / 2);\n\n'
            '    e->setX(x);\n'
            '    e->setY(y);\n\n'
            '    undoRedo->addUndoAction(std::make_unique<InsertUndoAction>(page, layer, e.get()));\n'
            '    auto sel = SelectionFactory::createFromFloatingElement(this, page, layer, view, std::move(e));\n\n'
            '    win->getXournal()->setSelection(sel.release());\n'
            '}\n',
        new='    clipboardPaste(std::move(image));\n'
            '}\n\n'
            '/**\n'
            ' * If the mouse pointer is currently over a page, returns that page\'s XojPageView along with the\n'
            ' * pointer\'s position on that page, in document units (matching Element::setX/setY\'s convention).\n'
            ' * Returns nullptr if the pointer isn\'t over the canvas or isn\'t over any page (e.g. paste\n'
            ' * triggered via a keyboard shortcut while the mouse happens to be elsewhere on screen).\n'
            ' */\n'
            'static XojPageView* getPageViewAndPosUnderCursor(XournalView* xournal, double& outX, double& outY) {\n'
            '    GtkWidget* widget = xournal->getWidget();\n'
            '    GdkWindow* window = gtk_widget_get_window(widget);\n'
            '    if (!window) {\n'
            '        return nullptr;\n'
            '    }\n\n'
            '    GdkDisplay* display = gdk_display_get_default();\n'
            '    GdkSeat* seat = display ? gdk_display_get_default_seat(display) : nullptr;\n'
            '    GdkDevice* pointer = seat ? gdk_seat_get_pointer(seat) : nullptr;\n'
            '    if (!pointer) {\n'
            '        return nullptr;\n'
            '    }\n\n'
            '    gint widgetX = 0;\n'
            '    gint widgetY = 0;\n'
            '    GdkModifierType mask;\n'
            '    gdk_window_get_device_position(window, pointer, &widgetX, &widgetY, &mask);\n\n'
            '    // Convert from viewport-relative to layout-absolute pixel coordinates (same convention as\n'
            '    // InputEvent::relative, see AbstractInputHandler::getPageAtCurrentPosition()).\n'
            '    GtkXournal* gtkXournal = GTK_XOURNAL(widget);\n'
            '    double layoutX = widgetX + (gtkXournal->hadjustment ? gtk_adjustment_get_value(gtkXournal->hadjustment) : 0.0);\n'
            '    double layoutY = widgetY + (gtkXournal->vadjustment ? gtk_adjustment_get_value(gtkXournal->vadjustment) : 0.0);\n\n'
            '    XojPageView* pageView = xournal->getLayout()->getPageViewAt(static_cast<int>(layoutX), static_cast<int>(layoutY));\n'
            '    if (!pageView) {\n'
            '        return nullptr;\n'
            '    }\n\n'
            '    auto pagePos = pageView->getPixelPosition();\n'
            '    double zoom = xournal->getZoom();\n'
            '    outX = (layoutX - pagePos.x) / zoom;\n'
            '    outY = (layoutY - pagePos.y) / zoom;\n'
            '    return pageView;\n'
            '}\n\n'
            '/**\n'
            ' * Grabs the given (just-created) selection at its own center and puts it into "moving" state, so\n'
            ' * that it follows the mouse pointer on every subsequent motion event (see the handleSelectionMove\n'
            ' * branch in PenInputHandler::actionMotion(), which moves any selection whose isMoving() is true,\n'
            ' * regardless of whether a mouse button is actually held down). The very next click on the canvas\n'
            ' * then finalizes its position and page, exactly like ending a normal click-and-drag - no further\n'
            ' * code is needed for that part, it is already handled by the existing selection-click logic in\n'
            ' * PenInputHandler::actionStart()/actionEnd().\n'
            ' */\n'
            'static void beginFloatingPlacement(EditSelection* selection) {\n'
            '    double zoom = selection->getView()->getXournal()->getZoom();\n'
            '    double grabX = zoom * (selection->getXOnView() + selection->getWidth() / 2);\n'
            '    double grabY = zoom * (selection->getYOnView() + selection->getHeight() / 2);\n'
            '    selection->mouseDown(CURSOR_SELECTION_MOVE, grabX, grabY);\n'
            '}\n\n'
            'void Control::clipboardPaste(ElementPtr e) {\n'
            '    double x = 0;\n'
            '    double y = 0;\n'
            '    auto pageNr = getCurrentPageNo();\n'
            '    if (pageNr == npos) {\n'
            '        return;\n'
            '    }\n\n'
            '    XojPageView* view = win->getXournal()->getViewFor(pageNr);\n'
            '    if (view == nullptr) {\n'
            '        return;\n'
            '    }\n\n'
            '    double width = e->getElementWidth();\n'
            '    double height = e->getElementHeight();\n\n'
            '    // Prefer spawning the element under the mouse pointer; fall back to the center of the\n'
            '    // visible area if the pointer isn\'t over any page (e.g. paste triggered from a menu with the\n'
            '    // mouse elsewhere on screen).\n'
            '    if (XojPageView* cursorView = getPageViewAndPosUnderCursor(win->getXournal(), x, y)) {\n'
            '        view = cursorView;\n'
            '        x = std::max(0.0, x - width / 2);\n'
            '        y = std::max(0.0, y - height / 2);\n'
            '    } else {\n'
            '        win->getXournal()->getPasteTarget(x, y);\n'
            '        x = std::max(0.0, x - width / 2);\n'
            '        y = std::max(0.0, y - height / 2);\n'
            '    }\n\n'
            '    this->doc->lock_shared();\n'
            '    PageRef page = view->getPage();\n'
            '    Layer* layer = page->getSelectedLayer();\n'
            '    this->doc->unlock_shared();\n\n'
            '    e->setX(x);\n'
            '    e->setY(y);\n\n'
            '    undoRedo->addUndoAction(std::make_unique<InsertUndoAction>(page, layer, e.get()));\n'
            '    auto sel = SelectionFactory::createFromFloatingElement(this, page, layer, view, std::move(e));\n\n'
            '    EditSelection* selection = sel.release();\n'
            '    win->getXournal()->setSelection(selection);\n'
            '    beginFloatingPlacement(selection);\n'
            '}\n',
        label="Control.cpp: clipboardPaste (helpers + spawn sous curseur + suivi)",
    )

    # --- clipboardPasteXournal(): cursor-based spawn + follow instead of immediate mouseUp() ---
    ok &= apply_edit(
        f,
        old='        double x = 0;\n'
            '        double y = 0;\n'
            '        // calculate x/y of paste target, see clipboardPaste(Element* e)\n'
            '        win->getXournal()->getPasteTarget(x, y);\n\n'
            '        x = std::max(0.0, x - selection->getWidth() / 2);\n'
            '        y = std::max(0.0, y - selection->getHeight() / 2);\n\n'
            '        // calculate difference between current selection position and destination\n'
            '        auto dx = x - selection->getXOnView();\n'
            '        auto dy = y - selection->getYOnView();\n\n'
            '        selection->moveSelection(dx, dy);\n'
            '        // update all Elements (same procedure as moving a element selection by hand and releasing the mouse button)\n'
            '        selection->mouseUp();\n\n'
            '        win->getXournal()->setSelection(selection.release());\n'
            '    } catch (const std::exception& e) {',
        new='        double x = 0;\n'
            '        double y = 0;\n'
            '        // Prefer the current mouse position if it happens to be over the same page this selection\n'
            '        // is tied to; otherwise fall back to the center of the visible area (e.g. paste triggered\n'
            '        // from a menu with the mouse elsewhere on screen, or hovering a different page - the user\n'
            '        // can still drag the floating selection onto another page afterwards).\n'
            '        double cursorX = 0;\n'
            '        double cursorY = 0;\n'
            '        if (getPageViewAndPosUnderCursor(win->getXournal(), cursorX, cursorY) == view) {\n'
            '            x = cursorX;\n'
            '            y = cursorY;\n'
            '        } else {\n'
            '            win->getXournal()->getPasteTarget(x, y);\n'
            '        }\n\n'
            '        x = std::max(0.0, x - selection->getWidth() / 2);\n'
            '        y = std::max(0.0, y - selection->getHeight() / 2);\n\n'
            '        // calculate difference between current selection position and destination\n'
            '        auto dx = x - selection->getXOnView();\n'
            '        auto dy = y - selection->getYOnView();\n\n'
            '        selection->moveSelection(dx, dy);\n\n'
            '        EditSelection* rawSelection = selection.release();\n'
            '        win->getXournal()->setSelection(rawSelection);\n'
            '        beginFloatingPlacement(rawSelection);\n'
            '    } catch (const std::exception& e) {',
        label="Control.cpp: clipboardPasteXournal (spawn sous curseur + suivi)",
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
