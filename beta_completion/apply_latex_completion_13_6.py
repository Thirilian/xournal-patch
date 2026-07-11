#!/usr/bin/env python3
"""
Patch 13.6 : CORRECTIF - suite au patch 13.5, l'utilisateur a signale
un nouvel avertissement critique GLib :
  g_object_unref: assertion 'G_IS_OBJECT (object)' failed

CAUSE : gtk_widget_destroy() finalise deja completement le popover ici
(ce n'est pas une simple "deconnexion" - GTK laisse tomber sa propre
reference interne en rompant l'association relative_to, et c'etait la
seule reference en dehors de la notre). Le g_object_unref()
automatique de completionPopover, qui s'execute juste apres la fin de
ce destructeur, operait donc sur un objet deja finalise - exactement
l'avertissement signale.

CORRECTIF : completionPopover.release() abandonne notre propre suivi
du pointeur SANS g_object_unref() correspondant, puisque
gtk_widget_destroy() a deja entierement pris en charge la liberation
de l'objet.

Modifie : src/core/gui/dialog/IntEdLatexDialog.cpp (1 zone)

NECESSITE : apply_latex_completion_13_5.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """IntEdLatexDialog::~IntEdLatexDialog() {
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
NEW_1 = """IntEdLatexDialog::~IntEdLatexDialog() {
    // Patch 13.5: CRASH FIX - gtk_widget_destroy() properly severs every internal GTK bookkeeping
    // link the popover has (in particular its \"relative_to\" association with texBox), which a plain
    // g_object_unref() (as completionPopover's own destructor would otherwise be the only thing to
    // do, right after this destructor's body finishes) does not. Without this, texBox/the window
    // being destroyed afterwards (in AbstractLatexDialog::~AbstractLatexDialog(), called right after
    // this destructor returns) could still reach for the popover through that stale association,
    // after our own reference to it has already been dropped and the object freed - a use-after-free
    // crash deep inside GTK's widget teardown cascade.
    //
    // Patch 13.6: CRASH FIX (continued) - gtk_widget_destroy() itself already fully finalizes the
    // popover here (it isn't merely \"disconnected\" - GTK drops its own internal reference to it as
    // part of severing the \"relative_to\" association, and that was the only reference besides ours).
    // completionPopover.release() drops OUR OWN tracking of the pointer without a matching
    // g_object_unref(), which would otherwise run on that already-finalized object once this
    // destructor returns (member destruction happens right after the destructor body finishes) -
    // this is exactly the \"g_object_unref: assertion 'G_IS_OBJECT (object)' failed\" GLib critical
    // the user reported after patch 13.5 alone.
    if (this->completionPopover) {
        gtk_widget_destroy(this->completionPopover.get());
        this->completionPopover.release();
    }
}
"""


def main():
    cpp = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    if not cpp.exists():
        print("[ECHEC] IntEdLatexDialog.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "Patch 13.5" not in cpp.read_text(encoding="utf-8"):
        print("[ECHEC] Le patch 13.5 introuvable dans IntEdLatexDialog.cpp.")
        print("        Appliquez d'abord apply_latex_completion_13_5.py, puis relancez ce script.")
        sys.exit(1)
    if "Patch 13.6" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.6 semble deja applique.")
        sys.exit(0)

    text = cpp.read_text(encoding="utf-8")
    count = text.count(OLD_1)
    if count != 1:
        print(f"[ECHEC] Motif trouve {count} fois dans IntEdLatexDialog.cpp (doit etre unique).")
        sys.exit(1)

    text = text.replace(OLD_1, NEW_1, 1)
    cpp.write_text(text, encoding="utf-8")
    print("[OK]    IntEdLatexDialog.cpp: release() au lieu d'un second unref sur l'objet deja finalise")

    print()
    print("Toutes les modifications ont ete appliquees avec succes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
