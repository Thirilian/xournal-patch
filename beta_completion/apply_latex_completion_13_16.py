#!/usr/bin/env python3
"""
Patch 13.16 ("completion LaTeX") : trois correctifs/ameliorations
demandes par l'utilisateur.

1. CORRECTIF (suite au 13.15) : un terme deja complet contenant un
   placeholder etait quand meme propose pendant la navigation, car
   commitCompletion() lui ajoute toujours un placeholder final
   supplementaire - la comparaison "exacte" contre le dictionnaire ne
   pouvait donc jamais reussir pour un tel terme. Desormais, TOUT
   terme contenant un placeholder est exclu des suggestions pendant la
   simple navigation (pas pendant la frappe), via un nouveau parametre
   isNavigation sur updateCompletionPopup().

2. Le caractere ajoute automatiquement apres un terme contenant deja
   un placeholder (patch 13.4) est desormais le grand cercle "◯"
   (U+25EF), et non plus une seconde puce "•". Ce nouveau caractere
   a exactement les memes proprietes de placeholder que "•" - toute
   la logique de recherche/selection/navigation de placeholder (13.2,
   13.3) reconnait desormais les DEUX caracteres de facon totalement
   interchangeable, via deux nouvelles fonctions utilitaires
   partagees. Le rendu PDF (patch 13.11) traite aussi "◯" exactement
   comme "•" (memes raisons : glyphe absent des polices par
   defaut de pdflatex en dehors de \\text{{}}).

3. La selection de texte par cliquer-glisser a la souris n'est plus
   perturbee par le mecanisme de completion : le signal mark-set
   (deja utilise pour detecter la navigation) est desormais ignore des
   qu'une selection non vide existe.

Modifie :
  - src/core/gui/dialog/IntEdLatexDialog.h (nouveau parametre
    isNavigation sur updateCompletionPopup)
  - src/core/gui/dialog/IntEdLatexDialog.cpp (les 3 correctifs)
  - src/core/control/latex/LatexGenerator.cpp (rendu PDF du nouveau
    caractere)

NECESSITE : apply_latex_completion_13_15.py (deja applique).

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

H_OLD0 = """    /// Used specifically to detect an already-complete term while merely navigating through its
    /// middle (getCurrentLatexWord() alone only sees the left-hand portion in that case).
    std::string getFullLatexWordAroundCursor() const;
    void updateCompletionPopup();
    void showOrRefreshCompletionPopup();
    void hideCompletionPopup();
    void commitCompletion();"""
H_NEW0 = """    /// Used specifically to detect an already-complete term while merely navigating through its
    /// middle (getCurrentLatexWord() alone only sees the left-hand portion in that case).
    std::string getFullLatexWordAroundCursor() const;
    /// Patch 13.16: `isNavigation` is true when called from cursor-movement-only triggers (the
    /// \"mark-set\" signal) rather than actual typing (the \"changed\" signal). In that case, any term
    /// containing a placeholder is excluded from the suggestions entirely: such a term can never be
    /// reliably identified as \"already complete\" (commitCompletion() always appends an extra trailing
    /// placeholder to it, so a plain text match against the dictionary's own copy never succeeds),
    /// so it must not be offered while merely navigating through it (see point 1 raised by the user).
    void updateCompletionPopup(bool isNavigation = false);
    void showOrRefreshCompletionPopup();
    void hideCompletionPopup();
    void commitCompletion();"""
CPP_OLD0 = """    //
    // Patch 13.13: skipped entirely while completionSuppressedByF1 is set - navigating around the
    // text must never reopen a popup the user just explicitly dismissed with F1.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         if (mark == gtk_text_buffer_get_insert(buffer) && !self->completionSuppressedByF1) {
                             self->updateCompletionPopup();
                         }
                     }),
                     this);"""
CPP_NEW0 = """    //
    // Patch 13.13: skipped entirely while completionSuppressedByF1 is set - navigating around the
    // text must never reopen a popup the user just explicitly dismissed with F1.
    //
    // Patch 13.16: CORRECTIF - also skipped entirely while a click-and-drag text selection is active
    // (or otherwise exists) - \"mark-set\" fires continuously as the selection grows/shrinks during a
    // drag, and updating the popup on every single one of those movements interfered with the
    // selection process itself. Called with isNavigation=true, since this can only ever be a cursor
    // move without any actual typing - see updateCompletionPopup()'s own doc comment for what that
    // does.
    g_signal_connect(this->getTextBuffer(), \"mark-set\",
                     G_CALLBACK(+[](GtkTextBuffer* buffer, GtkTextIter*, GtkTextMark* mark, gpointer d) {
                         auto* self = static_cast<IntEdLatexDialog*>(d);
                         GtkTextIter selStart;
                         GtkTextIter selEnd;
                         bool hasSelection = gtk_text_buffer_get_selection_bounds(buffer, &selStart, &selEnd);
                         if (mark == gtk_text_buffer_get_insert(buffer) && !self->completionSuppressedByF1 &&
                             !hasSelection) {
                             self->updateCompletionPopup(true);
                         }
                     }),
                     this);"""
CPP_OLD1 = """    return text.get();
}

void IntEdLatexDialog::updateCompletionPopup() {
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer
    // (from an earlier completion, or typed by hand) is unaffected either way."""
CPP_NEW1 = """    return text.get();
}

/**
 * Patch 13.16: two distinct characters now act as placeholders with identical properties - the
 * dictionary's own \"\\u2022\" (U+2022, bullet), and \"\\u25ef\" (U+25EF, large circle), which is what
 * commitCompletion() appends after a term that already contains a \"\\u2022\" of its own (see that
 * function). All placeholder-searching logic below checks for both, always treating them completely
 * interchangeably.
 */
constexpr const char* PLACEHOLDER_BULLET = \"\\xe2\\x80\\xa2\";
constexpr const char* PLACEHOLDER_CIRCLE = \"\\xe2\\x97\\xaf\";

/**
 * Searches forward from `start` (up to `limit`) for the EARLIEST occurrence of either placeholder
 * character. Returns true and fills outStart/outEnd if one was found.
 */
static auto forwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                        GtkTextIter* outEnd) -> bool {
    GtkTextIter bulletSearch = *start;
    GtkTextIter bulletStart;
    GtkTextIter bulletEnd;
    bool foundBullet = gtk_text_iter_forward_search(&bulletSearch, PLACEHOLDER_BULLET, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                     &bulletStart, &bulletEnd, limit);
    GtkTextIter circleSearch = *start;
    GtkTextIter circleStart;
    GtkTextIter circleEnd;
    bool foundCircle = gtk_text_iter_forward_search(&circleSearch, PLACEHOLDER_CIRCLE, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                     &circleStart, &circleEnd, limit);
    if (foundBullet && (!foundCircle || gtk_text_iter_compare(&bulletStart, &circleStart) <= 0)) {
        *outStart = bulletStart;
        *outEnd = bulletEnd;
        return true;
    }
    if (foundCircle) {
        *outStart = circleStart;
        *outEnd = circleEnd;
        return true;
    }
    return false;
}

/**
 * Searches backward from `start` (down to `limit`) for the LATEST (closest to `start`) occurrence of
 * either placeholder character. Returns true and fills outStart/outEnd if one was found.
 */
static auto backwardSearchAnyPlaceholder(const GtkTextIter* start, const GtkTextIter* limit, GtkTextIter* outStart,
                                         GtkTextIter* outEnd) -> bool {
    GtkTextIter bulletSearch = *start;
    GtkTextIter bulletStart;
    GtkTextIter bulletEnd;
    bool foundBullet = gtk_text_iter_backward_search(&bulletSearch, PLACEHOLDER_BULLET, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                      &bulletStart, &bulletEnd, limit);
    GtkTextIter circleSearch = *start;
    GtkTextIter circleStart;
    GtkTextIter circleEnd;
    bool foundCircle = gtk_text_iter_backward_search(&circleSearch, PLACEHOLDER_CIRCLE, GTK_TEXT_SEARCH_TEXT_ONLY,
                                                      &circleStart, &circleEnd, limit);
    if (foundBullet && (!foundCircle || gtk_text_iter_compare(&bulletStart, &circleStart) >= 0)) {
        *outStart = bulletStart;
        *outEnd = bulletEnd;
        return true;
    }
    if (foundCircle) {
        *outStart = circleStart;
        *outEnd = circleEnd;
        return true;
    }
    return false;
}

void IntEdLatexDialog::updateCompletionPopup(bool isNavigation) {
    // Patch 13.8: the whole suggestion mechanism is skipped outright if the user has disabled it in
    // Preferences - Tab/Shift+Tab navigation through any placeholders already present in the buffer
    // (from an earlier completion, or typed by hand) is unaffected either way."""
CPP_OLD2 = """    // itself and get offered again. getFullLatexWordAroundCursor() spans both sides of the cursor to
    // catch this: if it exactly matches some term, there is nothing to complete, full stop - checked
    // before the ordinary prefix-matching loop below, taking priority over it.
    std::string fullWord = this->getFullLatexWordAroundCursor();
    for (const auto& term: this->completionTerms) {
        if (term == fullWord) {"""
CPP_NEW2 = """    // itself and get offered again. getFullLatexWordAroundCursor() spans both sides of the cursor to
    // catch this: if it exactly matches some term, there is nothing to complete, full stop - checked
    // before the ordinary prefix-matching loop below, taking priority over it.
    //
    // Patch 13.16: CORRECTIF - this exact-match check alone never actually fires for a term
    // containing a placeholder, since commitCompletion() always appends an extra trailing one to it
    // (see PLACEHOLDER_CIRCLE above) - the text actually present in the buffer therefore never
    // matches completionTerms' own, unmodified copy of that term. Such terms are instead excluded
    // outright while merely navigating (isNavigation), a few lines below.
    std::string fullWord = this->getFullLatexWordAroundCursor();
    for (const auto& term: this->completionTerms) {
        if (term == fullWord) {"""
CPP_OLD3 = """        // be offered (and the popup must not reopen while merely navigating through it either - see
        // this same check's effect once currentMatches ends up empty below).
        if (term.size() > word.size() && term.compare(0, word.size(), word) == 0) {
            this->currentMatches.push_back(term);
            if (this->currentMatches.size() >= 4) {
                // completionTerms is in file order, so the first 4 matches found are already the"""
CPP_NEW3 = """        // be offered (and the popup must not reopen while merely navigating through it either - see
        // this same check's effect once currentMatches ends up empty below).
        if (term.size() > word.size() && term.compare(0, word.size(), word) == 0) {
            // Patch 13.16: CORRECTIF - while merely navigating (not typing), a term containing a
            // placeholder is never offered - see this function's own doc comment in the header.
            if (isNavigation && term.find(PLACEHOLDER_BULLET) != std::string::npos) {
                continue;
            }
            this->currentMatches.push_back(term);
            if (this->currentMatches.size() >= 4) {
                // completionTerms is in file order, so the first 4 matches found are already the"""
CPP_OLD4 = """    // gives them a natural landing spot to keep typing right after the term, rather than having to
    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
    // untouched.
    if (term.find(\"\\xe2\\x80\\xa2\") != std::string::npos) {
        term += \" \\xe2\\x80\\xa2\";
    }
    std::string word = this->getCurrentLatexWord();
"""
CPP_NEW4 = """    // gives them a natural landing spot to keep typing right after the term, rather than having to
    // move the cursor there manually. Terms with no placeholder at all (e.g. \"\\alpha\") are left
    // untouched.
    //
    // Patch 13.16: the character appended here is now the large circle (PLACEHOLDER_CIRCLE), not
    // another bullet - the detection check above still looks for the dictionary's own bullet
    // character, unaffected. This distinct character lets an auto-appended trailing placeholder be
    // told apart from the term's own placeholder(s) if ever needed later, while every
    // placeholder-searching function below treats both characters with fully identical properties.
    if (term.find(PLACEHOLDER_BULLET) != std::string::npos) {
        term += \" \";
        term += PLACEHOLDER_CIRCLE;
    }
    std::string word = this->getCurrentLatexWord();
"""
CPP_OLD5 = """
    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (gtk_text_iter_forward_search(&insertStart, \"\\xe2\\x80\\xa2\", GTK_TEXT_SEARCH_TEXT_ONLY, &placeholderStart,
                                      &placeholderEnd, &termEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    } else {
        // Patch 13.13: no placeholder in this term - place the cursor at its true end, exactly as if"""
CPP_NEW5 = """
    GtkTextIter placeholderStart;
    GtkTextIter placeholderEnd;
    if (forwardSearchAnyPlaceholder(&insertStart, &termEnd, &placeholderStart, &placeholderEnd)) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);
    } else {
        // Patch 13.13: no placeholder in this term - place the cursor at its true end, exactly as if"""
CPP_OLD6 = """}

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
"""
CPP_NEW6 = """}

auto IntEdLatexDialog::navigatePlaceholder(bool forward) -> bool {
    // Patch 13.3: Tab/Shift+Tab's normal action is blocked outright as soon as at least one
    // placeholder exists ANYWHERE in the buffer - regardless of whether one is actually found in the
    // specific direction being searched. Patch 13.16: checks for either placeholder character.
    GtkTextIter bufStart;
    GtkTextIter bufEnd;
    gtk_text_buffer_get_bounds(this->textBuffer, &bufStart, &bufEnd);
    GtkTextIter anyStart;
    GtkTextIter anyEnd;
    if (!forwardSearchAnyPlaceholder(&bufStart, &bufEnd, &anyStart, &anyEnd)) {
        return false;  // no placeholders left at all - let Tab/Shift+Tab behave normally
    }
"""
CPP_OLD7 = """    GtkTextIter placeholderEnd;
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
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);"""
CPP_NEW7 = """    GtkTextIter placeholderEnd;
    bool found;
    if (forward) {
        found = forwardSearchAnyPlaceholder(&selEnd, &bufEnd, &placeholderStart, &placeholderEnd);
    } else {
        found = backwardSearchAnyPlaceholder(&selStart, &bufStart, &placeholderStart, &placeholderEnd);
    }
    if (found) {
        gtk_text_buffer_select_range(this->textBuffer, &placeholderStart, &placeholderEnd);"""
GEN_OLD0 = """    // plain \"@\" fallback of patch 13.10) rather than triggering a \"Missing character\" warning from
    // pdflatex's default fonts, which don't have a glyph for the raw Unicode bullet character on its
    // own outside of \\text{} (a plain amsmath macro, already available via the default template).
    {
        const std::string bullet = \"\\xe2\\x80\\xa2\";
        const std::string replacement = \"\\\\text{\\xe2\\x80\\xa2}\";
        size_t pos = 0;
        while ((pos = strippedBody.find(bullet, pos)) != std::string::npos) {
            strippedBody.replace(pos, bullet.size(), replacement);
            pos += replacement.size();
        }
    }
"""
GEN_NEW0 = """    // plain \"@\" fallback of patch 13.10) rather than triggering a \"Missing character\" warning from
    // pdflatex's default fonts, which don't have a glyph for the raw Unicode bullet character on its
    // own outside of \\text{} (a plain amsmath macro, already available via the default template).
    //
    // Patch 13.16: the large circle placeholder character (\"◯\", U+25EF - see IntEdLatexDialog.cpp's
    // own comment on it) gets exactly the same treatment, for exactly the same reason - it is just as
    // absent from pdflatex's default fonts outside of \\text{}.
    {
        const std::string bullet = \"\\xe2\\x80\\xa2\";
        const std::string bulletReplacement = \"\\\\text{\\xe2\\x80\\xa2}\";
        size_t pos = 0;
        while ((pos = strippedBody.find(bullet, pos)) != std::string::npos) {
            strippedBody.replace(pos, bullet.size(), bulletReplacement);
            pos += bulletReplacement.size();
        }
        const std::string circle = \"\\xe2\\x97\\xaf\";
        const std::string circleReplacement = \"\\\\text{\\xe2\\x97\\xaf}\";
        pos = 0;
        while ((pos = strippedBody.find(circle, pos)) != std::string::npos) {
            strippedBody.replace(pos, circle.size(), circleReplacement);
            pos += circleReplacement.size();
        }
    }
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
    paths = {
        "h": Path("src/core/gui/dialog/IntEdLatexDialog.h"),
        "cpp": Path("src/core/gui/dialog/IntEdLatexDialog.cpp"),
        "gen": Path("src/core/control/latex/LatexGenerator.cpp"),
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"[ECHEC] Fichier introuvable : {p}. Lancez ce script depuis la racine du depot xournalpp.")
            sys.exit(1)
    if "getFullLatexWordAroundCursor" not in paths["h"].read_text(encoding="utf-8"):
        print("[ECHEC] getFullLatexWordAroundCursor introuvable dans IntEdLatexDialog.h.")
        print("        Appliquez d'abord apply_latex_completion_13_15.py, puis relancez ce script.")
        sys.exit(1)
    if "isNavigation" in paths["h"].read_text(encoding="utf-8"):
        print("[SKIP] Le patch 13.16 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(paths["h"], H_OLD0, H_NEW0, "h: zone 1/1")
    ok &= apply_edit(paths["cpp"], CPP_OLD0, CPP_NEW0, "cpp: zone 1/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD1, CPP_NEW1, "cpp: zone 2/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD2, CPP_NEW2, "cpp: zone 3/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD3, CPP_NEW3, "cpp: zone 4/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD4, CPP_NEW4, "cpp: zone 5/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD5, CPP_NEW5, "cpp: zone 6/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD6, CPP_NEW6, "cpp: zone 7/8")
    ok &= apply_edit(paths["cpp"], CPP_OLD7, CPP_NEW7, "cpp: zone 8/8")
    ok &= apply_edit(paths["gen"], GEN_OLD0, GEN_NEW0, "gen: zone 1/1")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
