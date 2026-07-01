#!/usr/bin/env python3
"""
Version corrigee (order-independent vis-a-vis de apply_txt_prefill.py) :
1) Preserve le ratio de redimensionnement manuel d'une formule lors de sa modification.
2) Pour le cas Text : utilise la taille de police comme reference de scale au lieu de
   la hauteur de la boite. kReferenceFontSize (12pt par defaut) = ratio de 1.
A lancer depuis la racine du depot xournalpp, avant ou apres apply_txt_prefill.py.
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
    ok = True

    # --- LatexController.h : nouveau membre ---
    fh = Path("src/core/control/LatexController.h")
    ok &= apply_edit(
        fh,
        old="    /**\n"
            "     * Image height\n"
            "     */\n"
            "    double imgheight = 0;\n",
        new="    /**\n"
            "     * Image height\n"
            "     */\n"
            "    double imgheight = 0;\n\n"
            "    /**\n"
            "     * Natural (unscaled) height corresponding to a scale of 1 for the element being replaced,\n"
            "     * in points. For a TexImage this is the PDF's intrinsic page height; for a Text this is\n"
            "     * kReferenceFontSize. 0 if creating a brand-new formula.\n"
            "     */\n"
            "    double prevNaturalHeight = 0;\n",
        label="LatexController.h: membre prevNaturalHeight",
    )

    fc = Path("src/core/control/LatexController.cpp")

    # --- includes ---
    ok &= apply_edit(
        fc,
        old='#include <glib.h>  // for g_error_free, g_error_ma...\n\n'
            '#include "control/Tool.h"                    // for Tool',
        new='#include <glib.h>  // for g_error_free, g_error_ma...\n\n'
            '#include <poppler-page.h>  // for poppler_page_get_size\n\n'
            '#include "util/raii/GObjectSPtr.h"  // for GObjectSPtr\n\n'
            '#include "control/Tool.h"                    // for Tool',
        label="LatexController.cpp: includes poppler-page.h / GObjectSPtr.h",
    )

    # --- mise a l'echelle proportionnelle dans loadRendered() ---
    ok &= apply_edit(
        fc,
        old='    img->setX(posx);\n'
            '    img->setY(posy);\n'
            '    img->setText(std::move(renderedTex));\n'
            '    if (std::abs(imgheight) > 1024 * std::numeric_limits<double>::epsilon()) {\n'
            '        double ratio = img->getElementWidth() / img->getElementHeight();\n'
            '        if (ratio == 0) {\n'
            '            img->setWidth(imgwidth == 0 ? 10 : imgwidth);\n'
            '        } else {\n'
            '            img->setWidth(imgheight * ratio);\n'
            '        }\n'
            '        img->setHeight(imgheight);',
        new='    img->setX(posx);\n'
            '    img->setY(posy);\n'
            '    img->setText(std::move(renderedTex));\n'
            '    if (std::abs(imgheight) > 1024 * std::numeric_limits<double>::epsilon()) {\n'
            '        // img currently holds the *natural* size of the freshly rendered formula (set by\n'
            '        // loadData()). Rather than forcing the old box\'s absolute height onto it (which shrinks\n'
            '        // or stretches the new content to fit, e.g. a formula growing from one line to two), we\n'
            '        // scale the natural size by how much the user had previously resized the box relative to\n'
            '        // its own natural size. This preserves a manual resize (if any) while letting the box\n'
            '        // grow/shrink to fit content that naturally became taller or shorter.\n'
            '        double naturalWidth = img->getElementWidth();\n'
            '        double naturalHeight = img->getElementHeight();\n'
            '        if (naturalWidth <= 0 || naturalHeight <= 0) {\n'
            '            img->setWidth(imgwidth == 0 ? 10 : imgwidth);\n'
            '            img->setHeight(imgheight);\n'
            '        } else {\n'
            '            double scale = (prevNaturalHeight > 1024 * std::numeric_limits<double>::epsilon())\n'
            '                                    ? imgheight / prevNaturalHeight\n'
            '                                    : imgheight / naturalHeight;\n'
            '            img->setWidth(naturalWidth * scale);\n'
            '            img->setHeight(naturalHeight * scale);\n'
            '        }',
        label="LatexController.cpp: mise a l'echelle proportionnelle",
    )

    # --- branche TexImage : imgheight + prevNaturalHeight (independant du texte de initialTex) ---
    ok &= apply_edit(
        fc,
        old='        if (auto* img = dynamic_cast<const TexImage*>(self->selectedElem)) {\n'
            '            self->initialTex = img->getText();\n'
            '            self->temporaryRender = img->cloneTexImage();\n'
            '            self->isValidTex = true;\n'
            '        } else if',
        new='        if (auto* img = dynamic_cast<const TexImage*>(self->selectedElem)) {\n'
            '            self->initialTex = img->getText();\n'
            '            self->temporaryRender = img->cloneTexImage();\n'
            '            self->isValidTex = true;\n'
            '            self->imgheight = self->selectedElem->getElementHeight();\n\n'
            '            // Natural size of the PDF page, independent of any manual resize the user may have\n'
            '            // applied to the on-page box (getElementWidth/Height reflect the *displayed* size).\n'
            '            if (PopplerDocument* pdf = img->getPdf()) {\n'
            '                xoj::util::GObjectSPtr<PopplerPage> pdfPage(poppler_document_get_page(pdf, 0), xoj::util::adopt);\n'
            '                if (pdfPage) {\n'
            '                    double naturalWidth = 0;\n'
            '                    double naturalHeight = 0;\n'
            '                    poppler_page_get_size(pdfPage.get(), &naturalWidth, &naturalHeight);\n'
            '                    self->prevNaturalHeight = naturalHeight;\n'
            '                }\n'
            '            }\n'
            '        } else if',
        label="LatexController.cpp: branche TexImage (imgheight/prevNaturalHeight)",
    )

    # --- branche Text : imgheight + prevNaturalHeight base sur la taille de police ---
    # Ancre uniquement sur l'ouverture de la branche, insensible au contenu de initialTex
    # (peu importe que apply_txt_prefill.py ait deja tourne ou non).
    ok &= apply_edit(
        fc,
        old='        } else if (auto* txt = dynamic_cast<const Text*>(self->selectedElem)) {\n',
        new='        } else if (auto* txt = dynamic_cast<const Text*>(self->selectedElem)) {\n'
            '            // Unlike a TexImage, a Text element has no natural-vs-displayed size distinction:\n'
            '            // resizing it changes the font size directly (see Text::scale()), and width/height\n'
            '            // are always recomputed from that font size - there is no separate "natural" render\n'
            '            // to compare against. We approximate an equivalent scale from the font size instead:\n'
            '            // kReferenceFontSize is assumed to correspond to a natural (scale=1) equation render\n'
            '            // at this template\'s base font size. Tune this constant if the resulting equation\n'
            '            // size feels consistently too big or too small.\n'
            '            static constexpr double kReferenceFontSize = 12.0;\n'
            '            self->imgheight = txt->getFontSize();\n'
            '            self->prevNaturalHeight = kReferenceFontSize;\n',
        label="LatexController.cpp: branche Text (imgheight/prevNaturalHeight)",
    )

    # --- suppression de l'ancienne ligne partagee self->imgheight = ...->getElementHeight(); ---
    ok &= apply_edit(
        fc,
        old='        self->imgwidth = self->selectedElem->getElementWidth();\n'
            '        self->imgheight = self->selectedElem->getElementHeight();\n',
        new='        self->imgwidth = self->selectedElem->getElementWidth();\n',
        label="LatexController.cpp: suppression de l'ancienne ligne imgheight partagée",
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
