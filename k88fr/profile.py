"""Construction d'un profil valide pour le K88-FR.

Le rapport 0x45 (sauvegarde flash) porte, a ses offsets 21-22, un champ de
controle interne que le firmware verifie :

    champ = (0x8032 + somme des octets 6 a 20) mod 2^16, en petit-boutiste

La constante 0x8032 est celle utilisee par les routines de checksum du
fabricant. Formule etablie sur cinq echantillons independants : les profils
d'usine 1 et 2 lus dans le clavier, et les captures rouge / vert / bleu.

C'est ce champ qui manquait : en changeant la couleur sans le recalculer, on
produisait un profil invalide, refuse quel que soit le checksum externe.
"""

MAGIC = 0x8032
DATA_RANGE = (6, 21)      # octets couverts par le champ interne, dans le rapport 0x45
INNER_AT = 21             # position du champ interne
RGB_OFFSETS = (10, 11, 12)


def inner_checksum(data: bytes) -> int:
    """Champ de controle interne pour un rapport 0x45 donne."""
    lo, hi = DATA_RANGE
    return (MAGIC + sum(data[lo:hi])) & 0xFFFF


def with_color(report: bytes, rgb: tuple[int, int, int]) -> bytes:
    """Remplace la couleur d'un rapport 0x45 et recalcule le champ interne."""
    out = bytearray(report)
    for offset, value in zip(RGB_OFFSETS, rgb):
        out[offset] = value
    value = inner_checksum(bytes(out))
    out[INNER_AT] = value & 0xFF
    out[INNER_AT + 1] = (value >> 8) & 0xFF
    return bytes(out)


def is_consistent(report: bytes) -> bool:
    """Verifie qu'un rapport porte deja le bon champ interne."""
    stored = report[INNER_AT] | (report[INNER_AT + 1] << 8)
    return stored == inner_checksum(report)
