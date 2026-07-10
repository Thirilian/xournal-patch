# Xournal++ — Résumé du processus de patchs (alignement/accroche)

Ce document résume l'effet de chaque patch appliqué dans l'ordre du processus actuel. Les patchs construisent progressivement un système complet d'accroche/alignement d'objets ("smart alignment guides"), puis l'exposent entièrement dans l'onglet **Snapping** des Préférences.

Séquence de référence complète :

```
python3 apply_arrow_resize_fix_v2.py

python3 apply_alignment_snap_v7_11.py
python3 apply_alignment_snap_v8_1_0.py
python3 apply_alignment_snap_v8_2_0.py
python3 apply_alignment_snap_v8_3_0.py
python3 apply_alignment_snap_v8_4_0.py
python3 apply_alignment_snap_v8_5_0.py
python3 apply_alignment_snap_v8_6_A.py
python3 apply_alignment_snap_v8_6_B.py
python3 apply_alignment_snap_v8_6_B_2.py
python3 apply_alignment_snap_v8_7_0.py
python3 apply_alignment_snap_v8_9_0.py
python3 apply_alignment_snap_v9_2.py

python3 apply_alignment_snap_v10_1.py
python3 apply_alignment_snap_v10_2.py
python3 apply_alignment_snap_v10_3.py
python3 apply_alignment_snap_v10_4.py
python3 apply_alignment_snap_v10_5.py
python3 apply_alignment_snap_v10_6A.py
python3 apply_alignment_snap_v10_6A_2.py
python3 apply_alignment_snap_v10_6B.py
python3 apply_alignment_snap_v10_6B_2.py
python3 apply_alignment_snap_v10_7.py
python3 apply_alignment_snap_v10_9.py
python3 apply_alignment_snap_v10_9_2.py
python3 apply_alignment_snap_v10_10_1.py

python3 apply_alignment_snap_v10_10_2_1.py
python3 apply_alignment_snap_v10_10_2_2.py
python3 apply_alignment_snap_v10_10_2_3.py
python3 apply_alignment_snap_v10_10_2_4.py
python3 apply_alignment_snap_v10_10_2_5.py
python3 apply_alignment_snap_v10_10_2_6.py
python3 apply_alignment_snap_v10_10_2_7.py
python3 apply_alignment_snap_v10_10_2_8.py
python3 apply_alignment_snap_v10_10_2_9.py
python3 apply_alignment_snap_v10_10_3.py
python3 apply_alignment_snap_v10_10_3_2.py
python3 apply_alignment_snap_v10_10_4.py
python3 apply_alignment_snap_v10_10_5_1.py
```

---

## Prérequis

### `apply_arrow_resize_fix_v2.py`
Correctif indépendant, prérequis technique du reste de la chaîne (comportement de redimensionnement des flèches). Ne fait pas partie du système d'alignement lui-même.

---

## Phase fondation (v1 à v9.2) — le moteur d'alignement

Ces patchs construisent le cœur du système, dans `EditSelection.cpp`, `BaseShapeHandler.cpp`, `EllipseHandler.cpp` et `SplineHandler.cpp`. À ce stade, aucun réglage n'est encore exposé dans les Préférences — tout est câblé en dur.

### `apply_alignment_snap_v7_11.py`
Fusionne l'intégralité des patchs v1 à v7.9 (le tout premier système d'alignement silencieux, puis avec guides visuels) ainsi que le patch 9.1 (réécriture de `candidatesOther`). Met en place :
- Le **palier ordinaire** (vert = centre, rose = bord) : recherche du meilleur alignement entre le contour de l'objet déplacé et les autres objets du calque, sur les axes X et Y.
- La **seconde passe multi-guides** : une fois le meilleur alignement trouvé, révèle tous les autres objets dont un point d'ancrage tombe dans la même tolérance, pour afficher plusieurs guides simultanément (façon Figma).
- L'infrastructure de guides visuels (lignes pointillées affichées pendant le déplacement).

### `apply_alignment_snap_v8_1_0.py`
Ajoute le **palier équidistant** : reproduit un espacement égal lorsque l'objet déplacé passe entre deux autres objets déjà espacés régulièrement.

### `apply_alignment_snap_v8_2_0.py`
Améliorations et corrections du palier équidistant (ajustements de tolérance et de détection).

### `apply_alignment_snap_v8_3_0.py`
Ajustements supplémentaires du système d'alignement (consolidation de comportements du palier ordinaire/équidistant).

### `apply_alignment_snap_v8_4_0.py`
Ajoute l'**assistant de croisement de ligne** ("coordinate system assist") dans `BaseShapeHandler.cpp` : pendant le tracé d'une ligne ou d'une flèche, si elle croise perpendiculairement une autre ligne/flèche déjà présente, affiche un repère et accroche sa longueur pour qu'elle corresponde exactement.

### `apply_alignment_snap_v8_5_0.py`
Ajoute l'**assistant de cercle parfait** ("diagonal snap") dans `EllipseHandler.cpp` : pendant le tracé d'une ellipse, si largeur et hauteur sont déjà proches, les force à être strictement égales (cercle parfait), avec guide visuel.

### `apply_alignment_snap_v8_6_A.py`
Introduit le **palier boosté (bleu)** : quand une petite ligne (ex: graduation d'axe) croise perpendiculairement une grande ligne, un accroche centre-à-centre prioritaire est proposé, avec tolérance étendue et couleur distincte.

### `apply_alignment_snap_v8_6_B.py`
Étend le palier boosté : ancrage aux **extrémités** de la grande ligne (patch 8.6.5), repères de **graduation** le long de la grande ligne quand plusieurs petites lignes y sont déjà accrochées (patch 8.6), changement de mode **Top/Middle/Below** par position du curseur (8.6.6), verrouillage de position lors des transitions de mode avec 3+ lignes (8.6.8).

### `apply_alignment_snap_v8_6_B_2.py`
**Correctif** : `detectLineZoneForOrdinaryAnchor()` forçait un candidat centre unique pour *toute* ligne simple (y compris celles sans famille Top/Below établie), faisant disparaître leurs extrémités (palier rose) du palier ordinaire. Corrigé pour ne s'appliquer qu'aux lignes ayant une vraie orientation Top/Below établie.

### `apply_alignment_snap_v8_7_0.py`
Ajoute le palier **centre de tableau** : centre un texte ou une image entre deux lignes parallèles de même longueur (colonne/rangée de tableau).

### `apply_alignment_snap_v8_9_0.py`
Ajoute l'accroche d'alignement (palier ordinaire) pour l'outil **spline**, indépendante du système `EditSelection`.

### `apply_alignment_snap_v9_2.py`
**Correctif** : différencie la tolérance de la première passe (6px, décide si le snap se déclenche) de celle de la seconde passe multi-guides (désormais 0.5px, décide qui d'autre rejoint le groupe). Corrige un bug où deux objets simplement proches (sans être réellement alignés) affichaient tous deux leur guideline.

---

## Phase 10.1 – 10.9 — cases à cocher individuelles

Ces patchs créent l'onglet **Snapping** des Préférences et y ajoutent, un par un, une case à cocher pour chaque fonctionnalité construite ci-dessus.

### `apply_alignment_snap_v10_1.py`
Crée l'onglet "Snapping" dans les Préférences (structure minimale : cadre "Functionalities" vide, insertion dans le notebook avec renumérotation correcte des onglets).

### `apply_alignment_snap_v10_2.py`
Case **"Equidistant assist"** — active/désactive le palier équidistant (8.1).

### `apply_alignment_snap_v10_3.py`
Case **"Page centering assist"** — active/désactive l'accroche au centre horizontal de la page.

### `apply_alignment_snap_v10_4.py`
Case **"Coordinate system assist"** — active/désactive l'assistant de croisement de ligne (8.4). Garde posée directement dans `applyLineCrossingSnap()`, un seul point couvrant les deux appelants (RulerHandler, ArrowHandler).

### `apply_alignment_snap_v10_5.py`
Case **"Circle assist"** — active/désactive l'assistant de cercle parfait (8.5).

### `apply_alignment_snap_v10_6A.py`
Case **"Graduation assist"** — active/désactive les repères de graduation et l'accroche forcée à la graduation la plus proche (8.6). Ne touche pas l'ancrage aux extrémités, qui reste indépendant.

### `apply_alignment_snap_v10_6A_2.py`
**Correctif** : avec "Graduation assist" désactivée et 3+ lignes déjà présentes, le mécanisme de verrouillage de position (8.6.8) restait actif sans condition, empêchant la ligne sélectionnée de glisser librement. Corrigé pour ne s'appliquer que si "Graduation assist" est active.

### `apply_alignment_snap_v10_6B.py`
Case **"Graduation orientation"**, indentée sous "Graduation assist" et grisée si celle-ci est désactivée — active/désactive le changement de mode Top/Middle/Below par glissement du curseur (8.6.6). Désactivée, l'ancrage reste toujours en mode Middle.

### `apply_alignment_snap_v10_6B_2.py`
**Correctif double** (suite à des tests approfondis) : (1) `existingCount <= 1` corrigé en `existingCount <= 2` pour aligner le code sur l'intention documentée de l'ancrage aux extrémités ("1 ou 2 lignes, self inclus") — bug préexistant depuis 8.6.5 lui-même. (2) Si "Graduation assist" est désactivée, l'ancrage aux extrémités s'applique désormais **sans limite** de nombre de lignes déjà présentes.

### `apply_alignment_snap_v10_7.py`
Case **"Table content centering assist"** — active/désactive le palier centre de tableau (8.7).

### `apply_alignment_snap_v10_9.py`
Case **"Snapping when drawing a spline"** — active/désactive l'accroche d'alignement de l'outil spline (8.9).

### `apply_alignment_snap_v10_9_2.py`
**Correctif de compilation** : `SplineHandler.cpp` appelait `control->getSettings()` sans inclure `Settings.h` (seulement `Control.h`, qui n'en fournit qu'une déclaration anticipée) — erreur de type incomplet. Ajout de l'include manquant.

### `apply_alignment_snap_v10_10_1.py`
Ajoute un texte explicatif en italique sous chacune des 8 cases de l'onglet Snapping, décrivant ce qu'apporte chaque fonctionnalité.

---

## Phase 10.10.2 — variables numériques "Normal"

Convertit 5 constantes de compilation en réglages modifiables via une nouvelle zone de texte, dans un cadre **"Settings" > "Normal"**. Chaque patch retire la constante `constexpr`, la remplace par un accesseur `Settings::getXxx()`, et l'enfile (paramètre supplémentaire) à travers les fonctions libres qui en ont besoin (`findAlignmentX`/`Y`, `computeStartingZone`) quand elles n'ont pas d'accès direct à `settings`.

### `apply_alignment_snap_v10_10_2_1.py`
**"Object alignment tolerance"** (défaut 6.0px) — tolérance de base du palier ordinaire. Premier patch de la série ; établit le cadre "Settings" et le modèle de ligne (étiquette + zone de texte + valeur par défaut + description).

### `apply_alignment_snap_v10_10_2_2.py`
**"Text vertical center fraction"** (défaut 0.6) — le fameux 0.6 contrôlant le centre vertical des textboxes pour le palier ordinaire (axe Y uniquement).

### `apply_alignment_snap_v10_10_2_3.py`
**"Line crossing assist tolerance"** (défaut 6.0px) — tolérance de l'assistant de croisement de ligne (8.4). Plus simple : une méthode membre unique déjà pourvue d'accès à `settings`.

### `apply_alignment_snap_v10_10_2_4.py`
**"Spline tool alignment tolerance"** (défaut 6.0px) — tolérance de l'outil spline (8.9), variable strictement séparée de celle d'`EditSelection.cpp` malgré le nom de constante identique à l'origine.

### `apply_alignment_snap_v10_10_2_5.py`
**"Circle assist tolerance"** (défaut 6.0px) — tolérance du cercle parfait (8.5). Complète le cadre "Normal" (5/5).

---

## Phase 10.10.2 (suite) — variables numériques "Advanced"

Même principe, cadre **"Advanced"**, pour 5 variables plus techniques et transversales.

### `apply_alignment_snap_v10_10_2_6.py`
**"Perpendicular cross boost factor"** (défaut 4.0) — multiplicateur de tolérance du palier boosté (bleu) et rayon de la zone Top/Middle/Below. 7 usages, dont 2 dans des fonctions libres (enfilage de paramètre) et 5 directement dans `mouseMove()`.

### `apply_alignment_snap_v10_10_2_7.py`
**"Line end anchor tolerance factor"** (défaut 0.9) — multiplicateur de tolérance de l'ancrage aux extrémités de la grande ligne (8.6.5).

### `apply_alignment_snap_v10_10_2_8.py`
**"Small mark max length"** (défaut 15.0) — seuil de taille en dessous duquel un objet est une "petite marque" forcée à un centre unique, pour le palier ordinaire.

### `apply_alignment_snap_v10_10_2_9.py`
**"Perpendicular cross max self length"** (défaut 15.0) — longueur maximale d'une petite ligne pour rester éligible au palier boosté. Variable découverte suite à un rapport de bug utilisateur ("au-delà de 25, l'ancrage aux extrémités ne marche plus"), absente du tableau original. *(Ce réglage sera fusionné dans le patch 10.10.3 ci-dessous — conservé dans la séquence d'application pour la cohérence historique, mais son réglage dédié disparaît ensuite de l'interface.)*

### `apply_alignment_snap_v10_10_3.py`
**Fusion architecturale** : `SMALL_MARK_MAX_LENGTH` et `PERPENDICULAR_CROSS_MAX_SELF_LENGTH` deviennent un seul réglage. Pour une **ligne pure** (Stroke à 2 points, jamais une flèche), cette valeur gouverne à la fois le palier ordinaire et le palier boosté. Pour tout **objet non-ligne** (flèches incluses), une valeur fixe non configurable de 15.0 s'applique à la place. La 4ᵉ ligne "Advanced" (Perpendicular cross max self length) disparaît de l'interface ; sa case est retirée.

### `apply_alignment_snap_v10_10_3_2.py`
**Correctif de compilation** (erreur de link) : lors de la fusion ci-dessus, un renommage textuel global de variable dans la définition de `computeStartingZone()` a changé le nom du paramètre (`maxSelfLength` → `selfIsLine`) sans changer son type (resté `double` au lieu de `bool`), créant une divergence avec la déclaration anticipée. Type corrigé.

### `apply_alignment_snap_v10_10_4.py`
**"Line crossing assist minimum length"** (défaut 50.0) — longueur minimale pour que l'assistant de croisement de ligne (8.4) considère une ligne. Dernière variable du tableau "Advanced" (5/5) — les deux cadres "Normal" et "Advanced" sont désormais intégralement configurables.

---

## Phase 10.10.5 — internationalisation

### `apply_alignment_snap_v10_10_5_1.py`
Met à jour le template de traduction `po/xournalpp.pot` avec les 48 chaînes traduisibles introduites dans l'onglet Snapping (cases, étiquettes, valeurs par défaut, descriptions, cadres, nom de l'onglet). Fusionne proprement les doublons (référence "Snapping" préexistante, 4 occurrences de "(default: 6.0)"). Ne modifie aucun fichier `.po` de langue individuelle — les traductions se font via Crowdin, la plateforme de traduction collaborative du projet.

---

## État final

À l'issue de cette séquence complète :
- **9 fonctionnalités** optionnelles sont individuellement activables/désactivables depuis l'onglet Snapping, chacune avec un texte explicatif.
- **10 variables numériques** (tolérances, facteurs, seuils de longueur) sont modifiables directement depuis les Préférences, réparties en cadres "Normal" (5) et "Advanced" (5).
- Le tout est prêt à être traduit dans n'importe quelle langue via le processus standard du projet.
