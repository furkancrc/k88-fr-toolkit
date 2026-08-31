# k88-fr-toolkit

Outil open source (Python) pour reprogrammer le clavier mécanique **Amazon Basics K88-FR**
(RGB + macros), sans dépendre du logiciel officiel disparu/non maintenu.

## Pourquoi ce projet

Le clavier AmazonBasics K88-FR est piloté par un logiciel Windows propriétaire
(`AmazonBasics gaming software`). Ce logiciel communique avec le clavier via un
canal HID "vendeur" dédié (en plus du HID clavier standard) pour :

- changer les couleurs / effets RGB
- programmer des macros sur les touches

Ce dépôt vise à documenter ce protocole (par rétro-ingénierie) et à fournir un
client Python (`hidapi`) permettant de faire la même chose, en ligne de commande,
multiplateforme.

## Méthode

1. **Capture** — utiliser Wireshark + USBPcap sous Windows pendant que le
   logiciel officiel envoie une commande (couleur, effet, macro), afin
   d'observer les rapports HID de sortie (Output Reports) bruts.
2. **Documentation** — consigner le format des rapports dans
   [`docs/protocol.md`](docs/protocol.md) au fur et à mesure qu'on le comprend.
3. **Implémentation** — reproduire les commandes en Python dans
   [`k88fr/`](k88fr) via la librairie `hidapi`.

## Statut

✅ **Couleur RGB globale fonctionnelle.** Premier morceau du protocole cassé :
on peut changer la couleur unie de l'ensemble du clavier depuis Python.

```bash
python -m k88fr.led 255 0 0   # rouge
python -m k88fr.led 0 0 255   # bleu
```

🚧 Reste à faire : mode "touche par touche" (couleur individuelle) et
animations prédéfinies. Voir [`docs/protocol.md`](docs/protocol.md) pour le
détail du protocole et les pistes en cours.

## Installation (dev)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Identifier le clavier

```bash
python -m k88fr.list_devices
```

Affiche tous les périphériques HID connectés (VID/PID/interface) pour repérer
celui du K88-FR.

## Licence

MIT
