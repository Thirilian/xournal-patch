#!/usr/bin/env python3
"""
Patch 13.5 : CORRECTIF DE CRASH - plantage confirme par l'utilisateur
(stacktrace fournie, signal 11 - segfault) au clic sur "OK" dans le
dialogue LaTeX, des que le popover de completion s'est affiche au
moins une fois pendant la saisie.

CAUSE : le membre completionPopover (un GObjectSPtr) faisait un simple
g_object_unref() du popover lors de la destruction de IntEdLatexDialog.
Mais GTK maintient en interne une association entre le popover et
texBox (via relative_to), qui n'etait jamais rompue explicitement.
Quand la fenetre du dialogue est ensuite detruite
(AbstractLatexDialog::~AbstractLatexDialog(), appelee juste apres que
les membres d'IntEdLatexDialog aient deja ete detruits), GTK tente de
nettoyer cette association - sur une memoire deja liberee : un
use-after-free classique, correspondant exactement a la stacktrace
fournie (crash au fond d'une cascade de destruction de widgets GTK).

CORRECTIF : le destructeur detruit desormais explicitement le popover
via gtk_widget_destroy() - qui rompt proprement toutes les
associations internes GTK (dont relative_to) - avant que le
g_object_unref() automatique de completionPopover ne s'execute.

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_4.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """IntEdLatexDialog::~IntEdLatexDialog() = default;
"""
NEW_1 = """IntEdLatexDialog::~IntEdLatexDialog() {
    // Patch 13.5: CRASH FIX - gtk_widget_destroy() properly severs every internal GTK bookkeeping
    // link the popover has (in particular its \"relative_to\" association with texBox), which a plain
    // g_object_unref() (as completionPopover's own destructor would otherwise be the only thing to
    // do, right after this destructor's body finishes) does not. Without this, texBox/the window
    // being destroyed afterwards (in AbstractLatexDialog::~AbstractLatexDialog(), called right after
    // this destructor returns) could still reach for the popover through that stale association,
    // after our own reference to it has already been dropped and the object freed - a use-after-free
    // crash deep inside GTK's widget teardown cascade.
    if (this->completionPopover) {
        gtk_widget_destroy(this->completionPopover.get());
    }
}
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "navigatePlaceholder" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] navigatePlaceholder introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord les patchs 13.1 a 13.4, puis relancez ce script.")
        sys.exit(1)
    if "Patch 13.5" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.5 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: popover detruit explicitement avant la destruction du dialogue")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
