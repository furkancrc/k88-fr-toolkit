# k88-fr-toolkit

<p align="center">
  <img src="assets/logo.png" width="150" alt="k88-fr-toolkit">
</p>

Reprendre le contrôle du clavier mécanique **AmazonBasics K88-FR** — n'importe
quelle couleur, écrite dans la mémoire du clavier, sans le logiciel d'origine.

Le protocole USB a été retrouvé entièrement par rétro-ingénierie, à partir du
clavier lui-même. Ce dépôt contient l'outil, le protocole documenté, et le
récit de la méthode — y compris les impasses, qui ont pris l'essentiel du
temps.

---

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

**Sauvegarder une couleur dans le clavier.** Elle survit au débranchement et
au redémarrage, sans qu'aucun programme reste actif :

```bash
python -m k88fr.persist "#ff8800"
```

**Changer la couleur sans l'enregistrer** (effet immédiat, perdu au
débranchement) :

```bash
python -m k88fr.led rouge
```

**Interface graphique** :

```bash
python -m k88fr.gui
```

Fermer la fenêtre range l'application dans la **zone de notification**, près
de l'horloge : elle reste accessible sans encombrer la barre des tâches. Un
clic sur l'icône la rouvre ; le menu contextuel permet d'éteindre le clavier
ou de quitter.

Toute couleur est acceptée : `RRGGBB`, `#RRGGBB`, ou un nom (`rouge`, `vert`,
`bleu`, `blanc`, `jaune`, `cyan`, `magenta`, `orange`, `off`).

---

## Le problème de départ

Le K88-FR est livré avec un logiciel Windows propriétaire. Deux versions
traînent dans la nature : celle de 2017, câblée en dur sur le mauvais
identifiant produit (`PID 0x1119` au lieu de `0x1150`), qui ne détecte donc
jamais le clavier ; et celle de 2021, fonctionnelle mais introuvable et non
maintenue. Sans elle, le clavier reste figé sur sa couleur d'usine.

L'objectif : piloter le clavier sans rien devoir à ce logiciel.

---

## La méthode

### 1. Identifier le périphérique

Le clavier s'annonce sous **VID `0x3938`** (Mosart Semiconductor, un fondeur
qui équipe beaucoup de claviers rebadgés) et **PID `0x1150`**. Il expose sept
canaux HID distincts, que Windows présente comme autant de périphériques :

| Canal | usage_page | Rôle |
|---|---|---|
| Col01, Col05 | 0x0001 | clavier standard |
| Col02 | 0x000C | touches multimédia |
| Col03 | 0x0001 | contrôle système |
| Col04 | 0x01FF | vendeur, rôle non identifié |
| **Col06** | **0xFF19** | **canal de configuration** |
| Col07 | 0x0001 | pointeur |

Toute la configuration passe par **Col06**. `k88fr/list_devices.py` les liste.

### 2. Lire le descripteur plutôt que deviner

Plutôt que de fouiller des captures à l'aveugle, on demande au clavier la
liste de ses propres rapports (`k88fr/tools/dump_report_descriptor.py` puis
`parse_hid_descriptor.py`). Le canal Col06 en déclare une vingtaine, dont
`0x14` (19 octets), `0x45` (261 octets), et les gros tampons `0x42`/`0x43`.

C'est plus fiable qu'une capture : le périphérique décrit lui-même ce qu'il
accepte.

### 3. Capturer le trafic USB

Sous Windows, **Wireshark + USBPcap**. Deux pièges qui coûtent une heure :

- USBPcap doit être installé en mode interactif, pour **cocher les
  contrôleurs USB** à instrumenter. Une installation silencieuse ne rattache
  le pilote à rien et aucune interface `USBPcapN` n'apparaît.
- `USBPcapCMD.exe` doit se trouver dans le dossier `extcap` de Wireshark,
  sinon les interfaces USB restent invisibles.

Une fois en place, on capture pendant que le logiciel d'origine applique une
couleur, puis on extrait les charges utiles :

```bash
tshark -r capture.pcapng -Y '_ws.col.info contains "SET_REPORT Request"' \
       -T fields -e usb.data_fragment
```

`k88fr/tools/harvest_captures.py` automatise l'extraction et sort directement
les séquences complètes.

### 4. Le changement de couleur immédiat

Le premier morceau tombe vite. Une écriture du rapport `0x14`, encadrée par
deux rapports de contrôle :

```
Report 9    : 09 21 00…00     ouverture du mode édition
Report 0x14 : 19 octets, couleur RVB aux offsets 6-7-8
Report 9    : 09 22 00…00     fermeture
```

**Sans cet encadrement, rien ne se passe** — et c'est sournois : Windows
retourne un succès, la relecture du rapport renvoie parfois même l'ancienne
valeur. Le firmware ignore silencieusement l'écriture.

Détail qui coûte cher aussi : chaque rapport doit partir sur un **handle HID
neuf**. En réutilisant le même, les écritures échouent avec
`ERROR_GEN_FAILURE`.

Ça donne n'importe quelle couleur… perdue au débranchement.

### 5. La sauvegarde durable

La vraie sauvegarde est un second bloc, distinct :

```
Report 9    : 09 02 00…00     ouverture
Report 0x45 : profil, fragment 1 (en-tête 00 01 12)
Report 0x45 : profil, fragment 2 (en-tête 00 00 01)
Report 9    : 09 07 00…00     fermeture
Report 0x3f : 3 octets — un « checksum »
```

Rejouer une capture à l'octet près fonctionne : la couleur survit au
débranchement. Mais changer les octets RVB et renvoyer le même `0x3f` échoue,
et le clavier repart en vert d'usine.

### 6. La fausse piste (l'essentiel du temps)

Conclusion évidente, et fausse : *il faut calculer ce checksum `0x3f`*.

Un banc d'essai a d'abord été monté pour tester vite. Trois propriétés,
établies expérimentalement, le rendent praticable :

- le profil déposé **survit** à un checksum refusé — on peut donc le déposer
  une fois puis enchaîner des essais légers (2 ms au lieu de renvoyer tout) ;
- une sauvegarde validée **survit aux essais faux qui la suivent** — on peut
  donc tester un lot entier avant de vérifier ;
- la réussite n'est visible qu'au rebranchement, aucun rapport lisible ne
  bouge.

D'où une recherche par dichotomie : un lot de candidats, un débranchement,
16 tours pour isoler une valeur parmi 65536.

Familles éliminées en chemin, chacune par la mesure :

| Famille | Éliminée par |
|---|---|
| CRC et tout schéma à base de XOR | test de linéarité : si la fonction était linéaire, blanc = rouge ⊕ vert ⊕ bleu. Le firmware refuse. Une seule mesure tue toute la famille |
| Sommes d'octets, pondérées ou non | rouge/vert/bleu ont la même somme (452) et des checksums différents |
| Sommes de mots 16 bits | un octet ne peut y contribuer que `0xFF` ou `0xFF00` : les écarts possibles sont figés et ne collent pas |
| Hachage multiplicatif | contradiction de parité : `M·(M−1)` est toujours pair |
| Fletcher, Adler, BSD, SysV | testés sur le message exact |
| Rotation + opération | 25 344 combinaisons, toutes découpes du message |
| Attaque temporelle | vérification à temps constant, aucune fuite |

Puis le verdict : sur un profil magenta bricolé, **les 65536 valeurs** ont été
éliminées. Aucun checksum ne validait ce profil. Le refus venait donc
d'ailleurs.

### 7. Le déblocage

Le clavier possède un **bouton de profil**. Ses cinq profils d'usine sont, par
construction, des profils que le firmware considère comme **valides**. Plutôt
que de deviner ce qu'il attend, autant lire ce qu'il accepte déjà
(`k88fr/tools/dump_profile.py`) :

```
profil 1 (vert fixe)   14 00 00 01 01 03 00 ff 00 00 00 00 01 00 00 00 03 3a 81
profil 2 (balayage)    14 00 00 01 01 03 ff 00 00 03 01 00 01 00 00 00 03 3e 81
                                            ↑ RVB      ↑  ↑              ↑
                                                   mode  param      ce champ bouge
```

Les deux derniers octets, tenus pour constants depuis le début, suivent en
fait la **somme du contenu**. Écart mesuré, identique dans les deux cas :

```
champ = (0x8032 + somme des octets 6 à 20) mod 2^16, en petit-boutiste
```

Vérifié sur cinq échantillons indépendants — les deux profils d'usine et les
captures rouge / vert / bleu. Et `0x8032` est exactement la constante
d'amorçage des routines de checksum du fabricant.

**Le rapport `0x3f` est facultatif.** Il ne participe pas à la validation. En
changeant la couleur sans recalculer ce champ interne, on produisait un profil
incohérent, rejeté quoi qu'il arrive — ce qui faisait porter le soupçon sur le
mauvais coupable pendant des heures.

### 8. Ce qui restait à faire

Reconstruire le champ, et c'est tout :

```python
champ = (0x8032 + sum(rapport[6:21])) & 0xFFFF
rapport[21] = champ & 0xFF
rapport[22] = champ >> 8
```

Validé sur des couleurs jamais capturées — magenta, `#ff8800`, `#00ff80` —
qui survivent toutes au débranchement.

---

## Le protocole en résumé

**Couleur immédiate** (volatile) — rapport `0x14`, 19 octets :

| offset | contenu |
|---|---|
| 0 | identifiant `0x14` |
| 6, 7, 8 | R, G, B |
| 9 | mode d'effet (`0x00` fixe, `0x03` animation) |
| 10 | paramètre de l'effet |
| 17-18 | champ de contrôle interne |

À encadrer par `09 21 …` et `09 22 …`.

**Sauvegarde durable** — rapport `0x45`, 261 octets, envoyé deux fois :

| offset | contenu |
|---|---|
| 0 | identifiant `0x45` |
| 1-3 | en-tête de fragment (`00 01 12` puis `00 00 01`) |
| 10, 11, 12 | R, G, B |
| 13 | mode d'effet |
| 14 | paramètre |
| 21-22 | **champ de contrôle** = `0x8032 + somme(6…20)` |
| 23+ | ignoré (reste de pile du logiciel d'origine) |

À encadrer par `09 02 …` et `09 07 …`.

Détail complet, mesures et impasses : [`docs/protocol.md`](docs/protocol.md).

---

## Structure du dépôt

| Fichier | Rôle |
|---|---|
| [`k88fr/persist.py`](k88fr/persist.py) | sauvegarde durable — `save_color(r, g, b)` |
| [`k88fr/profile.py`](k88fr/profile.py) | construction d'un profil valide, champ de contrôle |
| [`k88fr/led.py`](k88fr/led.py) | couleur immédiate — `K88FR.set_color(r, g, b)` |
| [`k88fr/gui.py`](k88fr/gui.py) | interface graphique |
| [`k88fr/list_devices.py`](k88fr/list_devices.py) | repérer le clavier parmi les périphériques HID |
| [`k88fr/tools/`](k88fr/tools) | outils de rétro-ingénierie (voir ci-dessous) |
| [`docs/protocol.md`](docs/protocol.md) | protocole détaillé et journal de recherche |

Les outils, utiles pour poursuivre l'exploration :

- `dump_report_descriptor.py` + `parse_hid_descriptor.py` — ce que le clavier déclare accepter
- `dump_profile.py` — lire un profil d'usine (le plus rentable de tous)
- `harvest_captures.py` — extraire les séquences d'une capture Wireshark
- `map_checksum_region.py` — délimiter la zone protégée en inversant un bit à la fois
- `crack_checksum.py` — recherche par dichotomie contre le clavier
- `timing_attack.py`, `probe_memory_window.py`, `hunt_device_checksum.py` — pistes explorées

---

## Ce qui reste

Couleur par touche et animations. La structure est comprise et les profils
d'usine montrent le chemin : un octet de mode et un paramètre pilotent les
effets. La méthode qui a marché reste valable — lire un profil d'usine qui
fait déjà ce qu'on veut, plutôt que deviner.

## Licence

MIT
