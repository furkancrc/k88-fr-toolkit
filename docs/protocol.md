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
- offset 5 : `0x03` — probablement le "mode" (0x03 = couleur statique ?
  à vérifier avec les modes animés)
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
2. `k88fr/dump_report_descriptor.py` + `k88fr/parse_hid_descriptor.py` pour
   lister tous les Report IDs valides et leur taille — bien plus fiable que
   deviner depuis une capture Wireshark incomplète.
3. `k88fr/read_features.py` pour lire l'état actuel de chaque Report Feature
   et repérer par inspection visuelle des motifs connus (ex: `00 ff 00` pour
   du vert, la couleur affichée au moment du test).
4. Modifier un seul champ à la fois et comparer avant/après (`k88fr/led.py`
   suit ce principe : on relit toujours l'état existant plutôt que
   d'écrire un buffer construit à la main, pour ne jamais casser les
   octets dont le rôle est encore inconnu).
