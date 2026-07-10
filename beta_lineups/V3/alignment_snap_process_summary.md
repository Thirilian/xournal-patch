# Xournal++ — Résumé du processus alignment_snap (v90 à 11.7)

Ce document résume l'effet de chaque patch du processus actuel de travail sur `alignment_snap`, dans l'ordre d'application.

Séquence de référence complète :

```
python3 apply_arrow_resize_fix_v2.py     # prérequis, hors alignment_snap

python3 apply_alignment_snap_v90.py
python3 apply_alignment_snap_v11_1.py
python3 apply_alignment_snap_v11_2.py
python3 apply_alignment_snap_v11_2_2.py
python3 apply_alignment_snap_v11_3.py
python3 apply_alignment_snap_v11_4.py
python3 apply_alignment_snap_v11_4_2.py
python3 apply_alignment_snap_v11_5.py
python3 apply_alignment_snap_v11_5_2.py
python3 apply_alignment_snap_v11_5_3.py
python3 apply_alignment_snap_v11_6.py
python3 apply_alignment_snap_v11_7.py
```

---

## `apply_alignment_snap_v90.py` — le socle consolidé

Ce script unique regroupe l'intégralité des patchs 7.11 à 10.10.5.1 (37 scripts fusionnés en un seul, testé identique byte pour byte à leur application séquentielle). Il construit le système complet d'accroche/alignement intelligent d'objets :

- **Paliers de base** : ordinaire (vert = centre, rose = bord), boosté/graduation (bleu), équidistant (double flèche), centre de tableau.
- **Assistants dédiés** : croisement de ligne (8.4), cercle parfait (8.5), accroche pour l'outil spline (8.9).
- **Onglet "Snapping" complet** dans les Préférences : 9 fonctionnalités activables individuellement, 10 variables numériques configurables (tolérances, facteurs, seuils de longueur), réparties en cadres "Normal" et "Advanced".
- **Template de traduction** (`po/xournalpp.pot`) mis à jour avec les 48 chaînes de l'onglet.

*(Le détail patch par patch de ce socle est disponible dans le document `xournalpp_patch_process_summary.md` généré précédemment.)*

---

## Phase 11 — retours d'usage et corrections

### `apply_alignment_snap_v11_1.py`
**Correctif** : les guidelines des assistants "coordinate system" (8.4) et "circle assist" (8.5) héritaient à tort du style de trait (pointillé/points) de l'outil courant au lieu d'être toujours en trait plein. `prepareContext()` appliquait le style de l'outil sur le contexte cairo, et rien ne le réinitialisait avant le tracé des guides, puisqu'ils partagent le même contexte que la forme principale. Ajout d'un `cairo_set_dash(cr, nullptr, 0, 0)` avant chaque tracé — les épaisseurs de trait restent inchangées.

### `apply_alignment_snap_v11_2.py`
**Correctif** : dans `drawDoubleArrow()` (repère équidistant, 8.1.0), la première tête de flèche pointait dans le mauvais sens (mais avec la bonne origine). Une variable `back1 = angle + PI` faisait que les ailes de cette tête étaient calculées avec le signe opposé à ce qu'il fallait — vérifié algébriquement (`cos(θ+π) = -cos(θ)`) et confirmé numériquement. Corrigé pour utiliser directement `angle` (comme la seconde tête), avec un signe `+`.

### `apply_alignment_snap_v11_2_2.py`
**Ajustement visuel** (remplace une version antérieure du même nom) : la double flèche du repère équidistant est désormais dessinée 2px plus courte de chaque côté (au lieu de 5px initialement), centrée sur le même point médian — sauf si l'écart total entre les objets est inférieur à 10px, auquel cas aucun retrait n'est appliqué (comportement original, pleine longueur).

### `apply_alignment_snap_v11_3.py`
**Correctif** : la règle "si 3+ lignes sont accrochées à une grande ligne mais ne sont pas équidistantes, le verrouillage cesse et les lignes glissent librement (sauf aux extrémités)" était cassée depuis son introduction. Le mécanisme de verrouillage "Lock to start" (8.6.8) se déclenchait uniquement sur le nombre de lignes, sans jamais vérifier si elles formaient réellement une grille valide (`computeBlueGridX`/`Y`). Corrigé : le verrouillage ne se déclenche désormais que si une grille valide est effectivement trouvée ; sinon, retombe sur l'ancrage aux extrémités.

### `apply_alignment_snap_v11_4.py`
**Nouvelle fonctionnalité** (retirée puis réintégrée au processus) : modifie la condition de passage entre les modes Top/Middle/Below pour une ligne déjà accrochée au clic. Un partage asymétrique 60/20/20 (au lieu de 33/33/33) favorise le mode de départ, et un désnappage complet se déclenche si le curseur sort entièrement de la plage `[-zoneR, +zoneR]`.

### `apply_alignment_snap_v11_4_2.py`
**Correctif** du patch 11.4 : le partage 60/20/20 provoquait une oscillation Top→Middle→Top→désnappage en glissant progressivement dans une seule direction. Cause : `signedOffset` utilisait `selfAnchorY`/`X`, un point pouvant sauter discontinuement entre le centre, le bord haut ou le bord bas de la ligne selon le mécanisme d'ancrage virtuel préexistant (8.6.4.6). Corrigé pour utiliser le centre géométrique stable de la ligne, uniquement pour les décisions de zone/désnappage (le décalage d'accroche final reste inchangé).

### `apply_alignment_snap_v11_5.py`
**Trois corrections de couleurs de guidelines** :
1. Le gris du palier de centrage de page est éclairci (`0.5,0.5,0.5` → `0.75,0.75,0.75`).
2. **Correctif** : une petite ligne boostée sur un axe perdait son accroche ordinaire (rose/vert) sur l'axe perpendiculaire dès qu'une famille de 2 lignes (sans décalage forcé) était détectée sur l'autre axe — corrigé pour ne plus écraser l'accroche existante dans ce cas.
3. **Nouveau** : quand Graduation assist est actif mais que la famille n'est pas une grille valide (11.3) et que le curseur est en glissement libre, le repère bleu de croisement passe en rouge — signalant que le verrouillage n'est plus actif ici.

### `apply_alignment_snap_v11_5_2.py`
**Correctif** du patch 11.3/11.5 : le patch 11.3 avait introduit une inversion largeur/hauteur — la vérification de validité de grille utilisait le mauvais paramètre de longueur (largeur au lieu de hauteur pour une ligne verticale, et inversement), pouvant faire échouer à tort la détection de grille valide et déclencher le repère rouge du 11.5 même quand la grille était parfaitement valide. Corrigé pour utiliser le même paramètre que le calcul des marqueurs affichés.

### `apply_alignment_snap_v11_5_3.py`
**Correction demandée** : une ligne appartenant à une famille de graduation génère désormais une guideline rose de son côté même en mode Middle (auparavant, seul Top/Below donnait rose ; Middle donnait vert). Nécessite de distinguer, dans `detectLineZoneForOrdinaryAnchor()`, "aucune grande ligne croisée du tout" (nullopt) de "croise une grande ligne mais centrée" (0) — ces deux cas étaient auparavant indiscernables.

### `apply_alignment_snap_v11_6.py`
**Correctif de deux bugs** liés au point d'ancrage vertical des textboxes :
1. Une textbox sélectionnée (self) utilisait toujours un centre à 50% codé en dur sur l'axe Y, au lieu de la fraction configurable `getTextYCenterFraction()` — alors que cette même variable était déjà correctement utilisée quand la textbox était l'objet "autre" (non déplacé). Asymétrie corrigée.
2. Une textbox à **plusieurs lignes** de texte doit toujours utiliser le vrai centre géométrique (0.5), jamais la fraction configurable — celle-ci n'a de sens que pour une seule ligne (ascendantes/descendantes). Corrigé pour self et pour les autres éléments.

### `apply_alignment_snap_v11_7.py`
**Correctif d'une régression** du patch 11.5.3, signalée par l'utilisateur ("en horizontal 3 guidelines, en vertical qu'une seule"). Le patch 11.5.3 forçait toute ligne croisant une grande ligne perpendiculaire (même en mode Middle) à n'offrir qu'un seul candidat d'alignement — pertinent pour de vraies petites graduations, mais s'appliquait aussi à des lignes bien plus longues dès qu'une grande ligne perpendiculaire était simplement présente ailleurs sur la page, réduisant à tort leurs options d'alignement. Restreint désormais le mécanisme aux lignes dont la longueur est strictement inférieure à `Settings::getSmallMarkMaxLength()`.

---

## État final

À l'issue de cette séquence, le système d'alignement dispose de tous les paliers et assistants du socle v90, avec :
- Des guidelines toujours en trait plein, quel que soit le style de l'outil courant.
- Un repère équidistant aux flèches correctement orientées et visuellement affinées.
- Un verrouillage de graduation qui respecte réellement la validité de la grille, avec un indicateur visuel rouge dédié.
- Des couleurs de guidelines cohérentes pour les familles de graduation, quel que soit leur mode (Top/Middle/Below).
- Un point d'ancrage vertical des textboxes qui respecte fidèlement le réglage utilisateur, avec un traitement distinct et cohérent pour le texte multi-lignes.
- Un mécanisme de "famille" de lignes restreint aux véritables petites graduations, sans effet de bord sur les lignes plus longues.
