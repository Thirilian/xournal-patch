#!/usr/bin/env python3
"""
Patch 13.3 ("completion LaTeX") : navigation Tab/Maj+Tab entre les
placeholders ("•") d'une formule.

Des qu'au moins un placeholder existe n'importe ou dans le buffer, le
comportement normal de Tab et Maj+Tab est entierement bloque :
  - Tab : selectionne le prochain placeholder trouve en cherchant vers
    la DROITE de la position du curseur (ou de la fin de la selection
    actuelle).
  - Maj+Tab : meme comportement, en cherchant vers la GAUCHE (du debut
    de la selection actuelle).
Si aucun placeholder n'est trouve dans la direction cherchee (mais
qu'il en existe ailleurs dans le buffer), la touche reste bloquee sans
rien deplacer (pas de retour au debut/fin - comportement volontairement
simple pour cette premiere version).

Shift+Tab est parfois delivre par GTK comme GDK_KEY_ISO_Left_Tab (sans
le modificateur Shift explicite) plutot que GDK_KEY_Tab + Shift - les
deux formes sont gerees.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.h
  - src/core/gui/dialog/IntEdLatexDialog.cpp

NECESSITE : apply_latex_completion_13_2.py

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """    void hideCompletionPopup();
    void commitCompletion();
    void moveCompletionSelection(int delta);
};"""
H_NEW0 = """    void hideCompletionPopup();
    void commitCompletion();
    void moveCompletionSelection(int delta);
    /// Patch 13.3: on Tab (forward=true) or Shift+Tab (forward=false), selects the next/previous \"•\"
    /// placeholder found looking right/left from the cursor (or current selection). Returns true if
    /// Tab/Shift+Tab's normal action should be blocked (i.e. at least one placeholder exists anywhere
    /// in the buffer), regardless of whether one was actually found in the searched direction.
    bool navigatePlaceholder(bool forward);
};"""
CPP_OLD0 = """    g_signal_connect(this->texBox, \"key-press-event\",
                     G_CALLBACK(+[](GtkWidget*, GdkEventKey* event, gpointer d) -> gboolean {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         if (self->currentMatches.empty()) {
                             return false;
                         }
                         switch (event->keyval) {
                             case GDK_KEY_Up:
                                 self->moveCompletionSelection(-1);
                                 return true;
                             case GDK_KEY_Down:
                                 self->moveCompletionSelection(1);
                                 return true;
                             case GDK_KEY_Return:
                             case GDK_KEY_KP_Enter:
                                 self->commitCompletion();
                                 return true;
                             case GDK_KEY_Escape:
                                 self->hideCompletionPopup();
                                 return true;
                             default:
                                 return false;
                         }
                     }),
                     this);
"""
CPP_NEW0 = """    g_signal_connect(this->texBox, \"key-press-event\",
                     G_CALLBACK(+[](GtkWidget*, GdkEventKey* event, gpointer d) -> gboolean {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         if (!self->currentMatches.empty()) {
                             switch (event->keyval) {
                                 case GDK_KEY_Up:
                                     self->moveCompletionSelection(-1);
                                     return true;
                                 case GDK_KEY_Down:
                                     self->moveCompletionSelection(1);
                                     return true;
                                 case GDK_KEY_Return:
                                 case GDK_KEY_KP_Enter:
                                     self->commitCompletion();
                                     return true;
                                 case GDK_KEY_Escape:
                                     self->hideCompletionPopup();
                                     return true;
                                 default:
                                     break;
                             }
                         }
                         // Patch 13.3: Tab/Shift+Tab placeholder navigation - independent of whether
                         // the completion popup is currently shown, since placeholders from a
                         // previously-committed completion may still be present in the buffer. Shift
                         // is conventionally delivered as GDK_KEY_ISO_Left_Tab on its own (not
                         // GDK_KEY_Tab plus a modifier), so both spellings of \"Tab\" are checked here.
                         if (event->keyval == GDK_KEY_Tab || event->keyval == GDK_KEY_KP_Tab ||
                             event->keyval == GDK_KEY_ISO_Left_Tab) {
                             bool shiftHeld = (event->state & GDK_SHIFT_MASK) != 0 ||
                                              event->keyval == GDK_KEY_ISO_Left_Tab;
                             return self->navigatePlaceholder(!shiftHeld);
                         }
                         return false;
                     }),
                     this);
"""
CPP_OLD1 = """    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}"""
CPP_NEW1 = """    }
    gtk_text_buffer_delete_mark(this->textBuffer, insertStartMark);
}

auto IntEdLatexDialog::navigatePlaceholder(bool forward) -> bool {
    // Patch 13.3: Tab/Shift+Tab's normal action is blocked outright as soon as at least one \"•\"
    // placeholder exists ANYWHERE in the buffer - regardless of whether one is actually found in the
    // specific direction being searched.
    GtkTextIter bufStart;
    GtkTextIter bufEnd;
    gtk_text_buffer_get_bounds(this->textBuffer, &bufStart, &bufEnd);
    GtkTextIter searchLimitStart = bufStart;
    if (!gtk_text_iter_forward_search(&searchLimitStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, nullptr, nullptr,
                                       &bufEnd)) {
        return false;  // no placeholders left at all - let Tab/Shift+Tab behave normally
    }

    GtkTextIter selStart;
    GtkTextIter selEnd;
    // Always fills selStart/selEnd, even without a selection (both are then set to the cursor).
    gtk_text_buffer_get_selection_bounds(this->textBuffer, &selStart, &selEnd);

    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    bool found;
    if (forward) {
        GtkTextIter searchFrom = selEnd;
        found = gtk_text_iter_forward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                              &placeholderStart, &placeholderEnd, &bufEnd);
    } else {
        GtkTextIter searchFrom = selStart;
        found = gtk_text_iter_backward_search(&searchFrom, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY,
                                               &placeholderStart, &placeholderEnd, &bufStart);
    }
    if (found) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    }
    // Tab/Shift+Tab is blocked either way, since at least one placeholder exists somewhere.
    return true;
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
    h_file = Path("src/core/gui/dialog/IntEdLatexDialog.h")
    cpp_file = Path("src/core/gui/dialog/IntEdLatexDialog.cpp")
    for p in (h_file, cpp_file):
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "completionTerms" not in h_file.read_text(encoding="utf-8"):
        print("[ECHEC] completionTerms introuvable dans IntEdLatexDialog.h.")
        print("        Appliquez d'abord les patchs 13.1 a 13.2, puis relancez ce script.")
        sys.exit(1)
    if "navigatePlaceholder" in h_file.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.3 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(h_file, H_OLD0, H_NEW0, "h: zone 1/1")
    ok &= apply_edit(cpp_file, CPP_OLD0, CPP_NEW0, "cpp: zone 1/2")
    ok &= apply_edit(cpp_file, CPP_OLD1, CPP_NEW1, "cpp: zone 2/2")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
