#!/usr/bin/env python3
"""
Corrige TOUS les doublons possibles créés par des lancements multiples de
apply_follow_cursor.py, sur les 3 fichiers concernés par le patch "follow cursor".
A lancer depuis la racine du dépôt xournalpp.
"""
import re
from pathlib import Path

BLOCKS = [
    (
        Path("src/core/gui/PageView.h"),
        "    /**\n"
        "     * Makes the currently active EditSelection (see XournalView::getSelection()) follow the\n"
        "     * pointer until the next left click. Intended to be called right after inserting a new\n"
        "     * floating element (e.g. a freshly compiled LaTeX formula) so the user can drop it in\n"
        "     * place without an extra click-and-drag step.\n"
        "     */\n"
        "    void beginFloatingPlacement();",
    ),
    (
        Path("src/core/gui/PageView.h"),
        "    /**\n"
        "     * If true, the current EditSelection (e.g. a just-inserted LaTeX formula) follows the\n"
        "     * pointer on hover, without needing the button held down. The next left click drops it\n"
        "     * in place. Set via beginFloatingPlacement().\n"
        "     */\n"
        "    bool awaitingFloatingPlacement = false;",
    ),
    (
        Path("src/core/gui/PageView.cpp"),
        "void XojPageView::beginFloatingPlacement() {\n"
        "    this->awaitingFloatingPlacement = xournal->getSelection() != nullptr;\n"
        "}",
    ),
    (
        Path("src/core/gui/PageView.cpp"),
        "    if (this->awaitingFloatingPlacement) {\n"
        "        // The click drops the floating element (e.g. a just-inserted LaTeX formula) at its\n"
        "        // current position instead of being interpreted by the currently selected tool.\n"
        "        this->awaitingFloatingPlacement = false;\n"
        "        return true;\n"
        "    }",
    ),
    (
        Path("src/core/gui/PageView.cpp"),
        "    } else if (this->awaitingFloatingPlacement) {\n"
        "        if (EditSelection* selection = xournal->getSelection()) {\n"
        "            // Center the selection under the pointer.\n"
        "            double dx = x - selection->getWidth() / 2 - selection->getXOnView();\n"
        "            double dy = y - selection->getHeight() / 2 - selection->getYOnView();\n"
        "            selection->moveSelection(dx, dy);\n"
        "        } else {\n"
        "            // The selection was cleared/deleted some other way; stop tracking it.\n"
        "            this->awaitingFloatingPlacement = false;\n"
        "        }",
    ),
    (
        Path("src/core/control/LatexController.cpp"),
        "    const bool isNewFormula = this->selectedElem == nullptr;",
    ),
    (
        Path("src/core/control/LatexController.cpp"),
        "    if (isNewFormula) {\n"
        "        // Only for newly-created formulas (not when re-editing an existing one): let the user\n"
        "        // drop the formula wherever they want with a single click, instead of it spawning at a\n"
        "        // fixed position that then needs a separate click-and-drag to move.\n"
        "        view->beginFloatingPlacement();\n"
        "    }",
    ),
]


def dedup_all(path: Path, block: str):
    """Remove consecutive duplicate occurrences of `block` (there could be more than 2)."""
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(block) + r"(?:\s*" + re.escape(block) + r")+")
    new_text, n = pattern.subn(block, text)
    if n == 0:
        return "SKIP"
    path.write_text(new_text, encoding="utf-8")
    return "OK"


def report_count(path: Path, block: str):
    if not path.exists():
        return -1
    text = path.read_text(encoding="utf-8")
    return text.count(block)


def main():
    print("=== Nettoyage des doublons ===")
    for path, block in BLOCKS:
        if not path.exists():
            print(f"[ABSENT] {path} n'existe pas")
            continue
        status = dedup_all(path, block)
        label = block.splitlines()[0].strip()[:60]
        print(f"[{status}]  {path.name}: '{label}...'")

    print("\n=== Vérification finale (chaque bloc doit apparaître 0 ou 1 fois) ===")
    all_good = True
    for path, block in BLOCKS:
        c = report_count(path, block)
        label = block.splitlines()[0].strip()[:60]
        status = "OK" if c <= 1 else "PROBLEME"
        if c > 1:
            all_good = False
        print(f"[{status}] {path.name}: occurrences={c}  '{label}...'")

    print()
    if all_good:
        print("Tout est propre. Vous pouvez relancer la compilation.")
    else:
        print("Certains blocs apparaissent encore plus d'une fois : recontactez pour investiguer.")


if __name__ == "__main__":
    main()
