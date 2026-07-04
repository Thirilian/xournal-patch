#!/usr/bin/env python3
"""
Sous-patch 7.6 du systeme d'ancrage entre objets (style Canva/Figma).

Corrige un bug de sequencement introduit par le patch prealable
apply_arrow_resize_fix_v2.py : dans BaseShapeHandler.cpp, l'ordre des
appels est :
    stroke->setPointVector(this->shape, &lastSnappingRange);
    stroke->setArrowKind(this->getArrowKind());

Or Stroke::setPointVectorInternal() (code d'origine, inchange), quand une
snappingBox valide est fournie ET que le trait n'a pas de pression (cas
normal pour un outil forme), fixe DIRECTEMENT snappedBounds a partir de la
boite englobante complete (ailes de fleche comprises) et marque
sizeCalculated = true - AVANT que setArrowKind() ne soit appele. Le
correctif du patch 7.5 (dans calcSize()) ne se declenche donc jamais pour
une fleche fraichement dessinee, puisque calcSize() n'est appele que si
sizeCalculated est false.

Ce patch corrige Stroke::setArrowKind() pour qu'il invalide ce cache
(sizeCalculated = false), forcant un recalcul via calcSize() au prochain
acces - recalcul qui, cette fois, connait le bon ArrowKind.

NECESSITE, dans cet ordre :
  1) apply_arrow_resize_fix_v2.py
  2) apply_alignment_snap_v1.py a v7.py
  3) apply_alignment_snap_v7_5.py

A lancer depuis la racine du depot xournalpp.
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
    stroke_cpp = Path("src/core/model/Stroke.cpp")
    if not stroke_cpp.exists():
        print("[ECHEC] Stroke.cpp introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)
    content = stroke_cpp.read_text(encoding="utf-8")
    if "arrowKind != ArrowKind::NONE" not in content:
        print("[ECHEC] Le correctif du patch 7.5 est introuvable dans Stroke.cpp.")
        print("        Appliquez d'abord apply_arrow_resize_fix_v2.py, puis v1 à v7.py, puis v7_5.py.")
        sys.exit(1)

    ok = apply_edit(
        stroke_cpp,
        old='void Stroke::setArrowKind(ArrowKind kind) { this->arrowKind = kind; }',
        new='void Stroke::setArrowKind(ArrowKind kind) {\n'
            '    this->arrowKind = kind;\n'
            '    // setPointVector() may have already cached snappedBounds directly from the full point-list range\n'
            '    // (see setPointVectorInternal()), before this arrowKind is known - invalidate that cache so the\n'
            '    // next access recomputes it through calcSize(), which now knows to exclude the arrowhead.\n'
            '    this->sizeCalculated = false;\n'
            '}',
        label="Stroke.cpp: invalidation du cache dans setArrowKind()",
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
