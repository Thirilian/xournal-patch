# Xournal++ — Résumé du processus "alignment_snap" (version 4)

Ce document résume l'effet de chaque patch du processus `alignment_snap` actuel (version 4), dans l'ordre d'application.

**Commit verrouillé pour ce processus** : `209481caee183798fcae151d125c1ea2d0317b3b`

Séquence de référence complète (telle qu'utilisée) :

```
python3 apply_arrow_resize_fix_v2.py
python3 xournal-patch/beta_lineups/V4/apply_alignment_snap_v90_4.py
python3 xournal-patch/beta_lineups/V4/apply_alignment_snap_v11_8.py
python3 xournal-patch/beta_lineups/V4/apply_alignment_snap_v11_9.py
python3 ~/Téléchargements/apply_alignment_snap_v11_10.py
python3 ~/Téléchargements/apply_alignment_snap_v11_10_1.py
python3 ~/Téléchargements/apply_alignment_snap_v11_10_2.py
```

Indépendant des séries `table_writing_assist`, complétion LaTeX, et des patchs 14.X / 15.X.

---

## `apply_arrow_resize_fix_v2.py`

**Prérequis technique.** Corrige le redimensionnement des flèches, nécessaire au bon fonctionnement du reste de la série.

## `apply_alignment_snap_v90_4.py`

**Consolidation majeure.** Fusionne v90 + 11.1 + 11.3 + 11.5 + 11.5.2 + 11.5.3 + **11.6** + **11.7** (11.6 et 11.7 sont donc déjà inclus ici — pas besoin de les appliquer séparément). Met en place l'ensemble du système d'accroche magnétique aux objets ("smart guides") : paliers ordinaire (rose/vert), bosté (bleu), page-centrée, grille bleue de graduation, etc. Inclut les correctifs de motif de tirets, direction des flèches, désaccrochage de grille non-équidistante, couleurs de guidelines, asymétrie du centrage Y du texte, et restriction de famille de lignes.

## `apply_alignment_snap_v11_8.py`

**Correctif du snap de spline.** Le clic initial lors du dessin d'une spline écrasait le snap complet déjà calculé par un simple snap de grille — corrigé en supprimant cette écrasement redondant dans `onButtonPressEvent()`.

## `apply_alignment_snap_v11_9.py`

**Nouveau cas pour l'alignement "jaune"** (`findTableCenterX/Y`, déjà existant — centre un Texte/TexImage/Image entre deux lignes parallèles de même longueur, priorité absolue sur son axe). Ajoute un second déclencheur : le cas d'une "case à 3 bords" (deux lignes d'un type, longueurs quelconques, plus exactement une ligne de l'autre type) — le côté manquant fermé par l'extrémité propre de la ligne perpendiculaire adjacente. La guideline reprend la longueur de la ligne existante parallèle à l'axe de snap, exactement comme le cas à 2 lignes.

## `apply_alignment_snap_v11_10.py`

**Quatre changements distincts** :
1. Nouveau cadre "Anchoring assistance" ("Aide à l'ancrage") dans l'onglet Snapping des Préférences, avec une case "Object Alignment Snapping" ("Alignement des objets par ancrage") reliée à la même variable que la case du menu Édition (libellé désormais traduit en français, partagé entre les deux). Le reste de l'onglet est grisé si cette case est décochée.
2. Correctif "table centering assist" : la recherche par paire de lignes ne considère plus une case formée de 4 cases réelles comme une case unique (filtre "plus petite case possible").
3. Valeur par défaut de "Circle assist tolerance" : 6.0 → 15.0 pixels.
4. "Coordinate system assist", "Circle assist" et "Spline snapping" désactivés si le snapping global est désactivé.

## `apply_alignment_snap_v11_10_1.py`

**Correctif de compilation.** `Control::setObjectAlignmentSnapping()` est délibérément `protected` — l'appel direct depuis `SettingsDialog::save()` ne compilait pas. Corrigé en reproduisant son effet exact via l'API publique de `Control` (met à jour le paramètre et l'état coché du menu Édition séparément).

## `apply_alignment_snap_v11_10_2.py`

**Correctif de comportement.** Le patch 11.10 (point 4) gatait `isSnapToObjects()` directement dans les getters `isCoordinateSystemAssistEnabled()`/`isCircleAssistEnabled()`/`isSplineSnappingEnabled()` — ce qui décochait à tort leurs cases dans les Préférences dès que le snapping global était désactivé. Corrigé : les getters redeviennent de simples lectures de la valeur stockée (la case reste cochée), et le contrôle `isSnapToObjects()` est déplacé au point d'appel fonctionnel réel de chacune des 3 fonctionnalités.

---

## État final

Le système d'alignement magnétique offre :
- Tous les paliers de snap (ordinaire, bosté, page-centrée, graduation, table-centrée classique et "3 bords").
- Un commutateur maître dans les Préférences, synchronisé avec le menu Édition, qui grise visuellement tout l'onglet sans jamais altérer les préférences individuelles de l'utilisateur.
- Une tolérance "Circle assist" par défaut plus généreuse (15px).
- Un comportement cohérent : le snapping global désactivé arrête bien toutes les fonctionnalités dépendantes, sans jamais décocher leurs cases respectives dans l'interface.
