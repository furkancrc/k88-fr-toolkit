# Protocole HID du K88-FR — notes de rétro-ingénierie

Statut : **vide, à documenter**.

## À remplir au fur et à mesure

- VID / PID du clavier (et de son interface "config" si distincte de l'interface clavier standard) :
- Taille des rapports HID (Input/Output/Feature) :
- Commande "changer une couleur unie" (octets observés) :
- Commande "changer d'effet RGB" :
- Commande "programmer une macro sur une touche" :
- Commande "sauvegarder en mémoire du clavier" (si onboard memory) :

## Comment capturer

1. Installer [Wireshark](https://www.wireshark.org/) + le module USBPcap (proposé à l'installation sous Windows).
2. Lancer Wireshark, choisir l'interface `USBPcapX` correspondant au port où le clavier est branché.
3. Filtrer sur l'adresse du device une fois identifiée (`usb.device_address == N`).
4. Lancer `AmazonBasics gaming software.exe`, faire une action simple (ex: changer la couleur en rouge uni), stopper la capture.
5. Repérer les paquets `URB_INTERRUPT out` ou `URB_CONTROL out` contenant les octets de la commande.
6. Copier les octets ici avec le contexte (quelle action a été faite).
