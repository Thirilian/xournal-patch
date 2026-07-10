# Documentation des patchs de snapping/alignement — Xournal++

> Ce document est compilé à partir des docstrings des scripts `.py` disponibles dans `/mnt/user-data/outputs/`, pas de la mémoire de conversation. Pour chaque patch : le numéro, s'il s'agit d'une **nouvelle fonctionnalité** ou d'un **correctif**, et les comportements côté utilisateur qu'il apporte ou corrige.

---

## Prérequis technique

### `apply_arrow_resize_fix_v2.py`
**Nature : correctif** (non lié au snapping, mais prérequis de presque tous les patchs suivants)
- Corrige la déformation de la tête de flèche lors d'un redimensionnement non uniforme.
- Ajoute une métadonnée persistante `ArrowKind` sur les traits (`Stroke`), utilisée massivement par la suite pour distinguer lignes simples et flèches.

---

## Base du système (v1 à v7.9)

Ces patchs construisent, étape par étape, le système d'ancrage de base entre objets (façon Figma/Canva), avec les paliers vert/rose (ordinaire) et bleu (croisement petit trait / grand trait perpendiculaire).

### `v1` — **Nouvelle fonctionnalité**
- Ajoute un snap **silencieux** (sans repère visuel) : en déplaçant un objet, si un de ses bords/centre tombe à moins de 6px d'un bord/centre d'un autre objet du même calque, la position est ajustée pour s'aligner exactement dessus.
- Limité à un seul objet déplacé, désactivé si la sélection est pivotée.

### `v2` — **Nouvelle fonctionnalité**
- Ajoute la ligne de guidage **rose**, bornée (relie exactement les deux objets, ne traverse pas toute la page), affichée pendant le glissement.
- Ajoute un bouton bascule *"Object Alignment Snapping"* (menu Edit), pour activer/désactiver toute la fonctionnalité. Actif par défaut, réglage persistant.

### `v3` — **Nouvelle fonctionnalité + correctifs**
- Une ligne de guidage ne peut se créer qu'avec un objet actuellement visible à l'écran.
- Pour un trait fin horizontal/vertical, un seul point d'ancrage est proposé (le milieu), au lieu de 3 quasi-identiques.
- Le snap-grille existant ne perturbe plus un axe déjà aligné précisément par le snap d'objet.
- La ligne de guidage devient **verte** quand l'alignement implique un centre (rose pour un bord).

### `v4` — **Nouvelle fonctionnalité + correctif**
- Corrige un léger décalage entre un objet sélectionné et sa copie non sélectionnée (cohérence de `getSnappedBounds()`).
- Ajoute le cas **"petit trait perpendiculaire sur grand trait"** : tolérance ×1.5 et ligne de guidage **bleue** quand un petit trait est déplacé sur un grand trait perpendiculaire, centre à centre.
- Raccourci clavier Ctrl+B pour activer/désactiver la fonctionnalité.
- (Ajustement temporaire de l'ancrage centre des traits horizontaux, annulé au patch 5.)

### `v5` — **Correctifs**
- Annule l'ajustement du patch 4 (retour au centre géométrique exact pour les traits fins horizontaux).
- Nouvelle constante dédiée pour le centre vertical du texte (indépendante du cas "trait fin").
- Établit la priorité en paliers : bleu > vert (centre) > rose (bord).
- Le déclenchement du palier bleu exige un vrai chevauchement de position (pas seulement une taille compatible), plafonné à 15pt.
- Bleu plus vif (electric blue).

### `v6` — **Nouvelle fonctionnalité + correctif**
- Corrige un bug qui empêchait le centre du texte d'avoir le moindre effet (patch 5 inopérant).
- Fusionne les paliers vert et rose en une seule recherche (le plus proche gagne parmi tous les candidats) ; seul le bleu reste exclusif.
- Plusieurs lignes de guidage peuvent désormais s'afficher simultanément si plusieurs points d'ancrage correspondent au même décalage.
- Le palier bleu utilise une boîte "hampe seule" (ignore les pointes de flèche).

### `v7` — **Nouvelle fonctionnalité + correctif**
- Les traits sont désormais TOUJOURS jugés via leur hampe seule, dans les deux paliers (une flèche n'offre plus jamais de point d'ancrage lié à sa pointe).
- Ajustement du centre vertical du texte.
- Évite qu'un match vert/rose redondant apparaisse en plus d'un match bleu sur l'axe croisé.

### `v7.2` — **Nouvelle fonctionnalité** *(remplacé par 7.2.2, ne pas appliquer)*
- Étendait la boîte "hampe seule" au côté de l'objet déplacé lui-même.

### `v7.2.2` — **Correctif** *(remplace 7.2)*
- Corrige un bug de dérive/oscillation du snap introduit par 7.2 : la géométrie de la hampe est désormais capturée une seule fois au clic (`mouseDown()`), pas recalculée à chaque frame.

### `v7b` — **Correctif**
- La flèche déplacée elle-même utilise maintenant aussi ses bornes "hampe seule".
- Corrige une ambiguïté d'axe dans la détection du palier bleu (fonctions dédiées par axe au lieu d'une fonction symétrique).

### `v7.5` — **Correctif (refonte propre)**
- Corrige le problème "côté sélection" à la source, dans `Stroke::calcSize()` : une flèche se comporte désormais exactement comme un trait simple pour le système de snapping, qu'elle soit déplacée ou cible. La fonction `getShaftBounds()` devient inutile et est retirée.

### `v7.6` — **Correctif**
- Corrige un bug de séquencement avec le prérequis flèches : `setArrowKind()` invalide désormais le cache de taille, forçant un recalcul correct pour une flèche fraîchement dessinée.

### `v7.8` — **Correctif**
- Corrige un bug résiduel du palier bleu : une paire (petit trait, grande flèche perpendiculaire) pouvait déclencher le bleu sur les DEUX axes simultanément (un correct, un incorrect). La détection devient consciente de l'axe.

### `v7.9` — **Correctif**
- Corrige un effet de bord du patch 7.8 : l'exclusion du palier ordinaire sur l'axe croisé doit se déclencher dès qu'une éligibilité existe sur N'IMPORTE LEQUEL des deux axes, pas seulement celui en cours d'examen.

---

## Phase 8

### 8.1.x — Accroche équidistante ("equal spacing")

#### `8.1` — **Nouvelle fonctionnalité**
- En déplaçant un objet, si le positionner à côté de l'un de deux autres objets déjà présents reproduirait exactement le même écart qui les sépare déjà entre eux, l'objet s'accroche à cette position (comme les smart guides Figma/Canva).
- Couvre uniquement le cas "prolonger un rythme existant" (pas l'insertion entre deux objets).
- Toujours affiché en rose ; ne prend jamais le pas sur le bleu ; concurrence le palier ordinaire (le plus proche gagne).

#### `8.1.2` — **Nouvelle fonctionnalité (rendu visuel)**
- Ajoute le rendu visuel du snapping équidistant : une chaîne de flèches doubles ("<-->") entre chaque paire consécutive d'objets du groupe, en rose, positionnée en dehors des objets.

#### `8.1.3` — **Correctif**
- Le snapping équidistant ne se déclenche désormais que si les objets de référence sont visibles à l'écran (règle déjà appliquée ailleurs, jusque-là absente ici).

### 8.2.x — Guides bicolores

#### `8.2` — **Nouvelle fonctionnalité**
- Scinde la ligne de guidage en deux moitiés colorées indépendamment (rose ou verte selon le match de chaque côté), sauf pour les cas bleu et équidistant.

#### `8.2.2` — **Correctif**
- Corrige le recouvrement visuel de la ligne de guidage avec le corps des objets : recadrée pour ne couvrir que l'espace vide entre deux objets éloignés (au-delà de 5pt).

### 8.3 — Centrage sur la page

#### `8.3` — **Nouvelle fonctionnalité**
- Ajoute un point d'ancrage pour centrer un objet horizontalement par rapport à la **page** (pas par rapport à d'autres objets). Ligne de guidage **grise**, traversant tout l'écran visible.
- Gère la subtilité des pages "Lined" (règle avec marge verticale) : centrage par rapport à la zone utilisable, avec une deuxième ligne grise à la position de la marge.

### 8.4.x — Assistant de croisement de ligne pendant le tracé

#### `8.4` — **Nouvelle fonctionnalité**
- Pendant le tracé en direct d'une ligne/flèche, si son origine croise une autre ligne perpendiculaire déjà tracée, deux repères roses s'affichent (à l'origine et à la distance exacte de la ligne existante) ; la ligne en cours peut s'accrocher à cette longueur exacte.
- Fonctionne dans les 4 directions, traite flèches simples/doubles comme de simples lignes.
- **Indépendant** du système d'ancrage `EditSelection` (fichiers différents).

#### `8.4.2` — **Correctif**
- Corrige un bug de "fantômes" (repères qui restent affichés après relâchement, mal positionnés, ou dédoublés) : la zone de rafraîchissement ne couvrait pas la position des repères eux-mêmes.

#### `8.4.3` — **Correctif**
- Ajoute une vérification directionnelle manquante : la cible doit réellement se trouver dans la direction du tracé (pas seulement alignée perpendiculairement), corrigeant des marqueurs apparaissant sans intersection réelle.

#### `8.4.4` — **Correctif**
- Les repères ne s'affichent désormais que si la ligne en cours a **déjà** croisé la ligne cible, plutôt que de l'anticiper.

#### `8.4.5` — **Correctif**
- Corrige une régression du patch 8.4.4 qui empêchait quasiment tout déclenchement (seuil trop strict face au mouvement discret de la souris) ; ajoute une marge de tolérance.

### 8.5.x — Cercle parfait pour l'ellipse

#### `8.5` — **Nouvelle fonctionnalité**
- Pendant le tracé d'une ellipse, point d'ancrage pour égaliser largeur et hauteur (cercle parfait), avec deux guidelines vertes le long du carré englobant.

#### `8.5.2` — **Correctif**
- Corrige l'épaisseur des deux guidelines vertes pour qu'elle reste constante à l'écran quel que soit le zoom.

### 8.6.x — La "grille bleue" et son évolution (la chaîne la plus longue)

#### `8.6` — **Nouvelle fonctionnalité**
- Quand un petit trait est déjà accroché (bleu) au centre d'un grand trait perpendiculaire, et que ce grand trait a un AUTRE petit trait de même taille, affiche des repères bleus indicatifs espacés régulièrement.
- Avec deux petits traits déjà régulièrement espacés ou plus : affiche toute la grille et **force** l'accroche du trait sélectionné à la position de grille la plus proche.

#### `8.6.2` — **Correctif**
- Corrige une inversion largeur/hauteur qui empêchait la grille bleue de trouver le moindre trait de même taille (aucun repère ne s'affichait jamais).

#### `8.6.3` — **Correctifs + ajustement**
- Désactive l'équidistant générique dès qu'un axe est boosté, même sans candidat de grille trouvé.
- Augmente la force du palier bleu (facteur ×1.5 → ×2.25).
- Ajoute une distance minimale (5pt) avant "téléportation" du trait suivant le curseur (cas à un seul autre trait).

#### `8.6.3.2` — **Nouvelle restriction**
- Exclut définitivement les flèches (et doubles flèches) du rôle de "petit trait" du palier bleu, quelle que soit leur taille — seules les lignes simples peuvent le déclencher.

#### `8.6.3.3` — **Simplification (remplace le mécanisme de 8.6.3.2)**
- Re-simplifie l'exclusion des flèches : filtre après coup plutôt que paramètre traversant les fonctions de recherche. Résultat côté utilisateur : une flèche n'a aucun snap d'alignement du tout dans ce cas précis (comportement accepté).

#### `8.6.4` — **Nouvelle fonctionnalité** *(mécanisme finalement remplacé par 8.6.4.5, voir plus bas)*
- Augmente encore la force du palier bleu (×2.25 → ×4.0).
- Introduit trois "zones" (négative/milieu/positive) pendant le glissement d'un trait déjà accroché à une grande ligne perpendiculaire.
- Au relâchement, coupe/double réellement en longueur tous les traits de même taille (mécanisme "demi/double").

#### `8.6.4.2` — **Correctif**
- Corrige une erreur de compilation réelle (fonction utilisée avant la définition de ses dépendances).

#### `8.6.4.3` — **Correctifs**
- Corrige l'épaisseur du trait qui variait par erreur avec sa longueur lors de la coupe/doublement.
- Corrige le trait sélectionné qui ne changeait jamais de taille/position (retiré du calque pendant la sélection, non cherché par la fonction de relâchement).

#### `8.6.4.4` — **Correctif + nouvelle fonctionnalité (version complète)**
- Corrige une erreur de compilation de type (`const_cast` ciblé).
- Ajoute la détection "trait déjà réduit" : reprendre un trait déjà en mode Top/Below cherche désormais aussi ses extrémités comme "centre virtuel" pour se rattacher à la grande ligne, pas seulement son centre géométrique vrai.

#### `8.6.4.5` — **Remplacement de mécanisme (nouvelle fonctionnalité)**
- **Remplace entièrement** le mécanisme de coupe/doublement (8.6.4 à 8.6.4.4) par un mécanisme de **translation pure** (aucun changement de taille) : les traits de même taille déjà accrochés se déplacent pour placer leur extrémité basse (mode négatif), centre (milieu), ou extrémité haute (mode positif) sur la grande ligne.
- Les repères de prévisualisation gardent désormais leur taille réelle (plus de troncature).
- Le script retire automatiquement l'ancien mécanisme s'il était déjà appliqué.

#### `8.6.4.6` — **Correctifs**
- Détermine la zone de départ du trait au clic, pour calculer correctement le déplacement des repères lors d'un changement de mode (formule dérivée reproduisant 5 cas de transition donnés).
- Le trait sélectionné s'accroche désormais dynamiquement selon la zone courante (au lieu de toujours son centre), suivant visuellement la grille pendant l'aperçu.

#### `8.6.5` — **Nouvelle fonctionnalité**
- Ajoute deux points d'ancrage aux deux extrémités d'une grande ligne, actifs uniquement si elle n'a que 1 ou 2 petites lignes (trait déplacé inclus) qui la croisent.
- Un repère bleu de la même forme que la petite ligne s'affiche par-dessus elle quand elle s'accroche à une extrémité.

#### `8.6.5.2` — **Correctif**
- Corrige une erreur de compilation réelle (`isEndpoint` non déclaré, ancre de structure fragile dans le script 8.6.5).

#### `8.6.6` — **Correctifs**
- Nouveau facteur dédié (`LINE_END_ANCHOR_TOLERANCE_FACTOR = 0.9`) pour la force de snapping aux extrémités, bien plus faible que le palier bleu classique.
- Le repère affiché sur une petite ligne accrochée à une extrémité ne suit plus la souris ; il reste fixe sur la position déjà accrochée.
- Une ligne qui n'était pas déjà accrochée ne peut plus basculer en mode Top/Below simplement en la faisant glisser dans cette zone — elle reste en mode Middle par défaut, sauf si d'autres lignes de même taille/orientation sont déjà établies (elle adopte alors directement leur mode).

#### `8.6.7` — **Correctif**
- Corrige un déplacement en double du trait sélectionné au relâchement (déjà positionné correctement pendant le glissement, puis redéplacé par erreur) — visible seulement après désélection.

#### `8.6.8` — **Correctif + nouvelle fonctionnalité**
- Lors d'une transition de mode avec 3 lignes ou plus déjà accrochées (ancrages d'extrémité inapplicables), le trait sélectionné reste figé sur sa position de départ sur l'axe perpendiculaire.
- Toute ligne simple sert désormais de référence d'ancrage pour le palier **ordinaire** (vert/rose) selon son propre mode géométriquement déterminé (bord bas pour Top, bord haut pour Below, centre sinon) — remplace les 3 candidats habituels par un seul, pour les lignes simples uniquement.

### 8.7 — Centrage de tableau

#### `8.7` — **Nouvelle fonctionnalité**
- Ajoute un point d'ancrage pour centrer un `Text`, `TexImage` ou `Image` entre deux lignes/flèches parallèles de même longueur délimitant une colonne/rangée de tableau.
- Ligne de guidage **jaune**, priorité absolue sur son axe (remplace vert/rose), sans affecter l'autre axe ; ne prend jamais le pas sur le bleu.

### 8.8 — Snapping au redimensionnement

#### `8.8` — **Nouvelle fonctionnalité**
- Ajoute le snapping du palier ordinaire (vert/rose uniquement) au point mobile (coin ou bord) pendant le redimensionnement d'un objet déjà créé — en concurrence avec le snap de grille existant.

### 8.9.x — Alignement pour l'outil spline

#### `8.9` — **Nouvelle fonctionnalité**
- Ajoute l'accroche d'alignement ordinaire (vert/rose) au point mobile de l'outil spline, en concurrence avec l'accroche angle/distance existante.
- Les points déjà posés de la spline en cours de tracé ne sont pas des points d'ancrage possibles.

#### `8.9.1` — **Correctifs**
- Corrige un bug de "fantôme" (même famille que 8.4.2) : la zone de rafraîchissement ne couvrait pas la zone du repère d'alignement.
- Corrige la référence du repère : il relie désormais le point d'ancrage de l'autre objet au point d'ancrage de l'aperçu de la spline (une fois pleinement résolu), pas à la position brute du curseur.

#### `8.9.2` — **Correctif (changement de conception)**
- L'accroche d'alignement **remplace** désormais entièrement le système d'angle/distance sur un axe donné dès qu'un match est trouvé, au lieu de simplement rivaliser avec lui ("le plus proche gagne").

---

## Phase 9

### 9.1 — Correctifs généraux

#### `9.1` — **Correctifs (règles affinées)**
- Nouvelle règle "petite marque" : un objet dont le plus grand côté est < 15pt force un point d'ancrage central unique sur les deux axes.
- Règle séparée pour les croix (détection géométrique à 5 points) : même comportement de centre unique forcé, indépendamment de la taille.
- Le point d'ancrage unique d'un axe simplement fin (sans vrai choix bord/centre) devient **rose** au lieu de vert — le vert reste réservé aux vrais centres.

---

## Résumé synthétique par grande fonctionnalité

| Fonctionnalité | Patchs |
|---|---|
| Système de base (vert/rose/bleu) | v1 à v7.9 |
| Snap équidistant | 8.1, 8.1.2, 8.1.3 |
| Guides bicolores | 8.2, 8.2.2 |
| Centrage sur la page | 8.3 |
| Croisement de ligne pendant le tracé | 8.4 → 8.4.5 |
| Cercle parfait (ellipse) | 8.5, 8.5.2 |
| Grille bleue + évolution (translation, extrémités, modes) | 8.6 → 8.6.8 |
| Centrage de tableau | 8.7 |
| Snapping au redimensionnement | 8.8 |
| Alignement pour l'outil spline | 8.9, 8.9.1, 8.9.2 |
| Petites marques / croix | 9.1 |
