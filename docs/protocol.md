# Protocole HID du K88-FR — notes de rétro-ingénierie

## Identification du périphérique

- **VID** = `0x3938` (Mosart Semiconductor)
- **PID** = `0x1150`
- Chipset partagé avec d'autres claviers rebrandés (AmazonBasics K91, gamme "AYH").
  Le logiciel officiel (2017, `AmazonBasics gaming software.exe`) est câblé en dur
  sur `PID=0x1119` dans `keyboard_config.ini` — il faut le corriger en `0x1150`
  pour que le logiciel détecte le clavier.

Le device expose **7 collections HID** (visibles comme périphériques séparés
sous Windows, `Col01` à `Col07`), toutes sur la même interface USB physique
(l'appareil n'a qu'une seule interface USB, `bNumInterfaces=1`) :

| Collection | usage_page | usage | Rôle |
|---|---|---|---|
| Col01 | 0x0001 | 0x06 | Clavier standard (boot keyboard) |
| Col02 | 0x000C | 0x01 | Consumer Control (touches multimédia) |
| Col03 | 0x0001 | 0x80 | System Control |
| Col04 | 0x01FF | 0x01 | Vendor spécifique (rôle non identifié) |
| Col05 | 0x0001 | 0x06 | Clavier (2e collection, NKRO ?) |
| Col06 | 0xFF19 | 0xFF19 | **Vendor spécifique — canal de configuration** |
| Col07 | 0x0001 | 0x02 | Souris (le clavier a un trackpoint/pavé ?) |

Toute la configuration (macros, LEDs) passe par **Col06**.

## Canal de configuration (Col06)

Ce canal expose un Report Output/Input classique (Report ID 9, 64 octets) et
une vingtaine de Report **Feature** de tailles variées (`GET_FEATURE` /
`SET_FEATURE`, transferts de contrôle EP0). Utiliser
`k88fr/dump_report_descriptor.py` et `k88fr/parse_hid_descriptor.py` pour les
relister depuis un vrai clavier branché.

### Séquence "ouverture / fermeture de mode d'édition" (Report ID 9)

Avant toute écriture d'un Report Feature, il faut encadrer l'écriture par
deux rapports Output Report ID 9 de 64 octets :

- **Ouverture** : `09 21 00 00 ... 00` (64 octets, padding de zéros)
- **Fermeture** : `09 22 00 00 ... 00` (64 octets, padding de zéros)

Sans cette enveloppe, l'écriture d'un Report Feature est acceptée sans erreur
par Windows/USB (`send_feature_report` retourne un code succès) mais **le
firmware l'ignore silencieusement** — aucune erreur ne remonte, la lecture du
report renvoie même parfois l'ancienne valeur.

D'autres variantes de ce même Report ID 9 ont été observées dans le logiciel
officiel : `0x02`/`0x07` (une autre paire ouverture/fermeture, probablement
pour un onglet différent de l'interface), et un sous-message `0x05 ...` dont
le rôle n'est pas encore confirmé (probablement lié aux macros, à creuser).

### Report Feature 0x14 — couleur globale ("contrôle complet")

19 octets (avec Report ID). Layout déduit par comparaison avant/après :

```
offset  0     1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17    18
valeur  0x14  00 00 01 01 03 R  G  B  00 00 00 01 00 00 00 03 <?>   <?>
```

- offset 0 : Report ID (0x14)
- offset 6-8 : composantes **R, G, B** (0-255 chacune) de la couleur unie
- offset 5 : `0x03` par défaut — hypothèse "mode d'effet" **infirmée** :
  changer cette valeur (testé 0-15, cf. `k88fr/tools/try_modes.py`) n'a
  déclenché aucun changement visible. Soit ce n'est pas un sélecteur de
  mode, soit changer un mode nécessite aussi de toucher un autre Report ID
  en parallèle (non identifié).
- offsets 17-18 (`0x3a 0x81` observés) : inchangés lors de nos tests,
  rôle non confirmé (checksum ? marqueur fixe ?) — laissés tels quels
  (on relit le report existant et on ne modifie que R/G/B, jamais ces
  octets, pour rester dans un état valide connu)

**Séquence complète pour changer la couleur globale :**

1. `GET_FEATURE(0x14)` → lire l'état actuel (19 octets)
2. Modifier les octets 6, 7, 8 (R, G, B) dans le buffer lu
3. `Write(Report 9, "09 21 00...00")` — ouverture du mode d'édition
4. `SET_FEATURE(buffer modifié)` — écrit le Report 0x14
5. `Write(Report 9, "09 22 00...00")` — fermeture du mode d'édition

Implémenté dans [`k88fr/led.py`](../k88fr/led.py) (`K88FR.set_color(r, g, b)`).

### Reports encore non identifiés (pistes pour la suite)

- `0x11` (257 octets), `0x12` (133 octets) : contiennent des séquences qui
  ressemblent à des indices/scan-codes de touches (valeurs 0x00-0x95 avec
  motifs répétés) → probablement une table de correspondance touche physique
  ↔ index LED, utile pour le mode "touche par touche".
- `0x13` (400 octets), `0x15` (402 octets), `0x20` (400 octets) : buffers
  binaires composés uniquement de `0x00`/`0xFF` par blocs → probablement des
  masques (quelles touches sont concernées par tel effet/telle couleur),
  pas des couleurs RGB directes.
- `0x42`/`0x43` (2052 octets), `0x44`/`0x45` (260 octets, préfixe identique
  à 0x42/0x43) : contenu qui ressemble à des données binaires opaques
  (haute entropie) — rôle inconnu (table d'animation compilée ? zone
  mémoire flash brute ?).

Prochaine étape suggérée : reproduire la méthode qui a marché pour 0x14 (lire
l'état avant/après une action précise dans l'app officielle, ou par
comparaison de captures Wireshark) sur le mode "touche par touche" pour
identifier comment adresser une LED individuelle.

## Méthode de travail qui a fonctionné

1. `k88fr/list_devices.py` pour repérer VID/PID et les différentes collections.
2. `k88fr/tools/dump_report_descriptor.py` + `k88fr/tools/parse_hid_descriptor.py`
   pour lister tous les Report IDs valides et leur taille — bien plus fiable
   que deviner depuis une capture Wireshark incomplète.
3. `k88fr/tools/read_features.py` pour lire l'état actuel de chaque Report
   Feature et repérer par inspection visuelle des motifs connus (ex:
   `00 ff 00` pour du vert, la couleur affichée au moment du test).
4. `k88fr/tools/analyze_report.py <report_id_hex> <taille>` pour un
   histogramme rapide des valeurs d'un report (distingue un bitmask binaire
   d'une vraie table de données variées).
5. Modifier un seul champ à la fois et comparer avant/après (`k88fr/led.py`
   suit ce principe : on relit toujours l'état existant plutôt que
   d'écrire un buffer construit à la main, pour ne jamais casser les
   octets dont le rôle est encore inconnu).

## Sauvegarde persistante (mémoire flash) — RÉSOLUE

Le logiciel officiel **fonctionnel** se trouvait dans
`C:\Users\furka\Documents\AmazonBasics gaming software\` (version 2021,
`SW 2.0.0.22 / FW 0.08`), contrairement à celui de `Program Files` (2017)
qui ne gère pas le K88. C'est lui qui a permis de capturer la vraie
séquence de sauvegarde.

### Séquence complète d'un « Appliquer »

Deux blocs distincts, à ne pas confondre :

**1. Changement visible (volatile)** — c'est ce que fait `k88fr/led.py` :
```
Report 9  : 09 21 00...00   (ouverture)
Report 0x14 : 19 octets, RGB aux offsets 6,7,8
Report 9  : 09 22 00...00   (fermeture)
```

**2. Sauvegarde en flash (persistante)** :
```
Report 9    : 09 02 00...00        (ouverture)
Report 0x45 : 261 octets, RGB aux offsets 10,11,12   (fragment 1, en-tête 00 01 12)
Report 0x45 : 261 octets, mêmes données              (fragment 2, en-tête 00 00 01)
Report 9    : 09 07 00...00        (fermeture)
Report 0x3f : 3 octets — 0x3f + checksum 16 bits
```

Important : chaque rapport doit être envoyé sur un **handle HID frais**
(ouvrir/fermer le périphérique à chaque fois) avec ~150 ms de pause. En
réutilisant un seul handle, les écritures échouent avec
`ERROR_GEN_FAILURE (0x1F)`.

### L'oracle de validation

Après une écriture flash, le registre `0x14` reflète la couleur du profil
stocké. Si le checksum est correct, il contient la couleur demandée ; s'il
est faux, le firmware invalide le profil et `0x14` repasse au vert d'usine.
**Cela permet de tester une hypothèse sans débrancher le clavier**
(`k88fr/tools/test_checksum_candidates.py`).

### Le checksum du Report 0x3f — non résolu

Valeurs mesurées (version 2021) : rouge `c4f6`, vert `4627`, bleu `beca`.

Zone couverte, déterminée expérimentalement en inversant un bit à chaque
offset (`k88fr/tools/map_checksum_region.py`) : offsets **1, 2 et 6→22** du
Report 0x45, soit 19 octets. Les offsets 3-5 (en-tête de fragment) et toute
la traîne au-delà de 22 sont ignorés — cette traîne est de la mémoire de
pile non initialisée du logiciel, elle diffère d'une capture à l'autre et
n'a aucune importance.

Message effectivement protégé (RGB aux indices 6, 7, 8) :
```
00 01 00 01 01 03 RR GG BB 00 00 00 01 00 00 00 03 3a 81
```

Familles d'algorithmes **écartées expérimentalement** :

- **Tous les CRC (et tout schéma à base de XOR)** : test de linéarité au banc
  d'essai. Si la fonction était linéaire sur GF(2), le blanc vaudrait
  forcément `rouge ⊕ vert ⊕ bleu` = `3c1b`. Le firmware rejette cette
  valeur → la fonction n'est pas linéaire, ce qui élimine toute la famille
  d'un seul test.
- **Recherche exhaustive CRC16** : 65536 polynômes × écart R→G libre
  (1..400), en modes normal/réfléchi et octets inversés → 357 candidats,
  réduits à 16 après contrainte de position, tous rejetés par le matériel.
- **Somme pondérée mod 2¹⁶** : les poids résolus depuis les 3 mesures sont
  incohérents (pas de progression régulière), ce qui exclut Fletcher et
  apparentés.
- **Algorithmes classiques** : Fletcher (mod 255/256), Adler, BSD, SysV,
  sommes de mots (gros/petit-boutiste, complément à un), XOR de mots — sur
  toutes les sous-plages contenant RGB. Aucune correspondance.
- **Famille « rotation + opération »** : rotations 1..15 bits, gauche/droite,
  addition/XOR/soustraction, avant/après l'octet, 7 valeurs d'init, toutes
  sous-plages. Aucune correspondance.

**Conclusion** : fonction propriétaire. Seules les couleurs dont on possède
une capture réelle peuvent être écrites de façon persistante (cf.
`k88fr/presets.py`), tandis que l'aperçu volatile accepte n'importe quelle
couleur.

### Analyse du binaire — état des lieux

`AmazonBasics gaming software.exe` (32 bits, 2018, 4,99 Mo) :

- Construit avec **C++Builder** (décoration de symboles Borland `$qqr`),
  avec les bibliothèques **JCL/JVCL** liées statiquement.
- Fait rare et exploitable : il exporte **14 982 symboles nommés**, ce qui
  donne les noms des fonctions de bibliothèque (mais pas celles du
  développeur, non exportées).
- `Jclmath@Crc16DefaultTable` est présente en `0x708f20` avec
  `Crc16DefaultStart = 0xffff` : c'est un CRC-CCITT standard (polynôme
  `0x1021`). Testé sur le message protégé, il ne correspond pas — cohérent
  avec la non-linéarité mesurée. Cette table est du code de bibliothèque
  non utilisé pour notre checksum.
- Les pointeurs `Hid@HidD_SetFeature` (`0x8861cc`) et consorts sont bien
  résolus dynamiquement en `0x4db7c8`, mais **jamais appelés** : seules des
  écritures (init et nettoyage) référencent ces variables.
- Les vraies E/S passent par `CreateFileA` / `DeviceIoControl` / `WriteFile`,
  dont les enveloppes se situent vers `0x4dd700`–`0x4ded50`. Les appelants
  applicatifs directs sont `0x4353b8`, `0x436018`, `0x436bfc`.
- **Blocage** : la remontée du graphe d'appels s'arrête là, car la
  répartition se fait par appels virtuels C++ (`call dword ptr [edx+0x20]`),
  invisibles pour une indexation des `call rel32`. Le désassemblage linéaire
  de `.text` se désynchronise également (données entrelacées).

**Prochaine étape pour cette voie** : charger le binaire dans Ghidra (analyse
des vtables et décompilation), poser un point d'arrêt sur l'écriture du
rapport `0x3f` et remonter à la routine qui produit les 2 octets. Les
adresses ci-dessus donnent un point de départ direct.

Piste annexe explorée sans succès : les fichiers de profil `config/*.K88`
se terminent par 2 octets variables (`7385`, `c285`, …), mais ils
correspondent au champ interne visible en fin de message (`03 3a 81`), pas
au checksum du rapport `0x3f`.

## Ancienne analyse (avant découverte du logiciel 2021)

Le Report 0x14 (couleur globale) est **purement volatile** : la couleur
revient au vert par défaut au moindre débranchement/rebranchement, sans
même appuyer sur une touche. Pistes testées pour trouver un mécanisme de
sauvegarde persistante :

- Enveloppe `0x02`/`0x07` (au lieu de `0x21`/`0x22`) autour de l'écriture du
  Report 0x14 : aucun effet (même pas de changement temporaire).
- Recherche du motif `00 ff 00` (vert actuel) dans les gros buffers
  `0x42`/`0x43` (2052 octets) : absent.
- Ces buffers `0x42`/`0x43`/`0x44`/`0x45` sont en fait la **même donnée**
  (0x44/0x45 sont un préfixe tronqué de 0x42/0x43) — probablement une
  interface de lecture mémoire brute (firmware/bootloader) à taille de
  fenêtre variable, sans rapport avec les profils LED. Contenu stable
  entre plusieurs lectures (pas aléatoire), mais aucun motif RGB.
- Lecture de `0x20`, `0x30`, `0x3f`, `0x40`, `0x41` (y compris en mode
  édition ouvert via Report 9) : échec systématique avec
  `ERROR_GEN_FAILURE (0x1F)` — vraie erreur matérielle Windows, pas un
  souci de format de notre côté. Le firmware refuse ces accès pour une
  raison non identifiée (report réservé ? nécessite un déverrouillage
  préalable qu'on n'a pas trouvé ?).

**Conclusion** : la sauvegarde persistante native n'a pas été trouvée avec
les moyens à disposition (pas de documentation publique sur ce chipset
Mosart précis, logiciel officiel trop cassé pour servir de référence).
Le produit final utilise donc une **persistance logicielle** (réapplication
automatique de la couleur au démarrage de Windows / rebranchement du
clavier) plutôt qu'une vraie sauvegarde flash. À revisiter si on obtient
un jour un dump de firmware ou une meilleure source sur ce chipset.

## Pistes explorées sans succès (pour ne pas les retester)

- Faire varier l'octet offset 5 du Report 0x14 (hypothèse "mode d'effet") :
  aucun effet visible testé sur les valeurs 0 à 15.
- `k88fr/tools/replay.py` (rejeu de la séquence Report 9 capturée pendant un
  clic sur le bouton couleur du logiciel officiel) : rejeu identique
  byte-à-byte confirmé (comparaison Wireshark), mais aucun effet — le
  logiciel officiel n'envoyait probablement rien d'utile à ce moment-là
  (son onglet LED ne réagit pas non plus visuellement dans l'UI elle-même).
