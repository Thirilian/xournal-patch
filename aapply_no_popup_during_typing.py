#!/usr/bin/env python3
"""
Patch 14.1 : les erreurs "genuines" (pas de simples fautes de syntaxe
LaTeX, qui sont deja gerees silencieusement) qui pouvaient survenir
PENDANT la frappe dans le dialogue LaTeX interne n'ouvrent plus de
fenetre popup modale (XojMsgBox::showErrorToUser) - qui volait le
focus et pouvait cacher le dialogue.

Ces trois points affichent desormais leur message directement dans la
zone de statut/sortie DEJA existante du dialogue (texErrorLabel +
zone de texte de sortie de compilation, via
AbstractLatexDialog::setCompilationStatus()) - le meme mecanisme deja
utilise silencieusement pour les erreurs de syntaxe LaTeX normales.
Aucune fenetre separee, aucun vol de focus, le dialogue ne disparait
jamais.

Points corriges (tous dans LatexController.cpp) :
  1. triggerImageUpdate() : echec du lancement meme du sous-processus
     pdflatex.
  2. onPdfRenderComplete() : erreur de communication avec le
     sous-processus non liee a une simple syntaxe LaTeX invalide (ex:
     le bug "Invalid UTF-8" precedemment signale).
  3. loadRendered() : echec du chargement du PDF rendu (deux cas).

Deux popups restent INCHANGEES car hors de ce contexte ("pendant la
frappe") : la verification des dependances a l'OUVERTURE du dialogue
(insertLatex()), et le bouton "Test" des Preferences
(LatexSettingsPanel::checkDeps()).

Modifie : src/core/control/LatexController.cpp (3 zones)

A lancer depuis la racine du depot xournalpp.
"""
import sys
from pathlib import Path

OLD_1 = """    if (auto* err = std::get_if<LatexGenerator::GenError>(&result)) {
        XojMsgBox::showErrorToUser(control->getGtkWindow(), err->message);
    } else if (auto** proc = std::get_if<GSubprocess*>(&result)) {
"""
NEW_1 = """    if (auto* err = std::get_if<LatexGenerator::GenError>(&result)) {
        // Patch 14: shown inline in the dialog's own status/output area, exactly like an invalid-LaTeX
        // error, rather than a separate modal popup - which would steal focus from (and potentially
        // hide) the LaTeX dialog while the user might still be typing.
        this->isValidTex = false;
        this->texProcessOutput = err->message;
        this->updateStatus();
    } else if (auto** proc = std::get_if<GSubprocess*>(&result)) {
"""
OLD_2 = """        } else if (!g_error_matches(err, G_SPAWN_EXIT_ERROR, 1)) {
            // The error was not caused by invalid LaTeX.
            string message =
                    FS(_F(\"Latex generation encountered an error: {1} (exit code: {2})\") % err->message % err->code);
            XojMsgBox::showErrorToUser(self->control->getGtkWindow(), message);
        }
"""
NEW_2 = """        } else if (!g_error_matches(err, G_SPAWN_EXIT_ERROR, 1)) {
            // The error was not caused by invalid LaTeX. Patch 14: shown inline (overwriting whatever
            // was captured from stdout above, if anything, since this message is more relevant) rather
            // than a separate modal popup - see triggerImageUpdate()'s own comment for why.
            self->texProcessOutput =
                    FS(_F(\"Latex generation encountered an error: {1} (exit code: {2})\") % err->message % err->code);
        }
"""
OLD_3 = """    if (err != nullptr) {
        string message = FS(_F(\"Could not load LaTeX PDF file: {1}\") % err->message);
        XojMsgBox::showErrorToUser(control->getGtkWindow(), message);
        g_error_free(err);
        return nullptr;
    } else if (!loaded || !img->getPdf()) {
        XojMsgBox::showErrorToUser(control->getGtkWindow(), FS(_F(\"Could not load LaTeX PDF file\")));
        return nullptr;
    }
"""
NEW_3 = """    if (err != nullptr) {
        // Patch 14: shown inline (and isValidTex is reset to false, since this is a genuine failure
        // discovered only after compilation itself succeeded) rather than a separate modal popup -
        // see triggerImageUpdate()'s own comment for why. The caller (onPdfRenderComplete()) calls
        // updateStatus() shortly after this returns, which will pick up both of these.
        this->isValidTex = false;
        this->texProcessOutput = FS(_F(\"Could not load LaTeX PDF file: {1}\") % err->message);
        g_error_free(err);
        return nullptr;
    } else if (!loaded || !img->getPdf()) {
        this->isValidTex = false;
        this->texProcessOutput = FS(_F(\"Could not load LaTeX PDF file\"));
        return nullptr;
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
    cpp = Path("src/core/control/LatexController.cpp")
    if not cpp.exists():
        print("[ECHEC] LatexController.cpp introuvable. Lancez ce script depuis la racine du depot xournalpp.")
        sys.exit(1)
    if "Patch 14" in cpp.read_text(encoding="utf-8"):
        print("[SKIP] Le patch 14.1 semble deja applique.")
        sys.exit(0)

    ok = True
    ok &= apply_edit(cpp, OLD_1, NEW_1, "LatexController.cpp: point 1 (triggerImageUpdate)")
    ok &= apply_edit(cpp, OLD_2, NEW_2, "LatexController.cpp: point 2 (onPdfRenderComplete)")
    ok &= apply_edit(cpp, OLD_3, NEW_3, "LatexController.cpp: point 3 (loadRendered)")

    print()
    if ok:
        print("Toutes les modifications ont ete appliquees avec succes.")
        sys.exit(0)
    else:
        print("Au moins une modification a echoue. Verifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
