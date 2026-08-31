# k88-fr-toolkit

Outil open source (Python) pour reprogrammer le clavier mécanique **Amazon Basics K88-FR**
(RGB), sans dépendre du logiciel officiel cassé/non maintenu.

## Pourquoi ce projet

Le clavier AmazonBasics K88-FR est piloté par un logiciel Windows propriétaire
de 2017 (`AmazonBasics gaming software`), qui est câblé en dur sur le mauvais
PID (`0x1119` au lieu de `0x1150`) et ne détecte donc jamais le clavier
correctement. Une fois ce PID corrigé, les macros et réglages fonctionnent,
mais l'onglet RGB reste inerte (bouton non fonctionnel, aucune commande
valide envoyée).

Ce dépôt documente le vrai protocole USB/HID du clavier (par rétro-ingénierie)
et fournit un client Python (`hidapi`) qui pilote la couleur RGB directement,
sans dépendre du logiciel officiel.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

**Sauvegarder une couleur dans le clavier** (survit au débranchement, aucun
logiciel n'a besoin de tourner ensuite) :

```bash
python -m k88fr.persist "#ff8800"
```

**Changer la couleur sans la sauvegarder** (effet immédiat, perdu au
débranchement) :

```bash
python -m k88fr.led rouge
```

**Interface graphique** :

```bash
python -m k88fr.gui
```

N'importe quelle couleur fonctionne : hex `RRGGBB` ou `#RRGGBB`, ou un nom
connu (`rouge`/`red`, `vert`/`green`, `bleu`/`blue`, `blanc`/`white`,
`jaune`/`yellow`, `cyan`, `magenta`, `orange`, `off`/`eteint`).

## Identifier le clavier

```bash
python -m k88fr.list_devices
```

Affiche tous les périphériques HID connectés (VID/PID/canal) pour repérer
celui du K88-FR (VID `0x3938`, PID `0x1150`).

## Statut

✅ **N'importe quelle couleur, sauvegardée dans le clavier.** Le profil écrit
survit au débranchement et au redémarrage, sans qu'aucun programme reste actif.

Le clavier vérifie que le profil qu'on lui dépose est cohérent avec lui-même :
le rapport `0x45` porte à ses offsets 21-22 un champ de contrôle valant
`0x8032 + somme des octets 6 à 20`. C'était le seul verrou — le rapport `0x3f`
qu'envoie le logiciel d'origine est facultatif. Détail complet dans
[`docs/protocol.md`](docs/protocol.md).

🚧 **Pas encore fait** : couleur par touche et animations prédéfinies. La
structure du profil est maintenant comprise, donc ces modes sont accessibles :
les profils d'usine du clavier montrent qu'un octet de mode et un paramètre
pilotent les animations.

## Structure du repo

- [`k88fr/led.py`](k88fr/led.py) — API stable : `K88FR.set_color(r, g, b)` +
  CLI (`python -m k88fr.led <couleur>`)
- [`k88fr/list_devices.py`](k88fr/list_devices.py) — liste les périphériques
  HID pour identifier le clavier
- [`k88fr/tools/`](k88fr/tools) — scripts de rétro-ingénierie utilisés pour
  découvrir le protocole (dump du descripteur HID, lecture brute des Report
  Feature, rejeu de captures Wireshark...). Pas une API stable, mais utiles
  pour continuer l'exploration (touche par touche, animations).
- [`docs/protocol.md`](docs/protocol.md) — documentation détaillée du
  protocole découvert, et pistes non résolues

## Méthode utilisée pour la rétro-ingénierie

1. Capture Wireshark + USBPcap du trafic USB pendant l'usage du logiciel
   officiel (partiellement concluant : l'onglet RGB officiel n'envoie rien
   d'exploitable).
2. Extraction du vrai HID Report Descriptor directement depuis le clavier
   (`k88fr/tools/dump_report_descriptor.py` + `parse_hid_descriptor.py`) pour
   lister tous les Report IDs valides.
3. Lecture (`GET_FEATURE`) de chaque Report ID candidat pour repérer des
   motifs connus (ex: la couleur actuellement affichée) dans les données.
4. Modification ciblée d'un seul champ à la fois, en réutilisant l'état lu
   plutôt qu'un buffer construit à la main, pour ne jamais casser un octet
   dont le rôle est encore inconnu.

## Licence

MIT
