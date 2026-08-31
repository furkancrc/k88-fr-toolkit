"""Reconstruction du checksum du Report 0x3f par algebre lineaire.

Un CRC est une fonction affine sur GF(2) : CRC(a) ^ CRC(b) ne depend que de
(a ^ b), pas du contenu inconnu du buffer ni de l'init/xorout. On exploite ca
avec les 3 couleurs capturees (rouge / vert / bleu) pour retrouver toute la
fonction sans jamais connaitre la structure exacte ecrite en flash.

Notations : la couleur est stockee comme des octets R,G,B consecutifs (une
fois, ou repetes par touche - le raisonnement est identique). On note
  A = contribution CRC de R=0xFF, B = celle de G=0xFF, C = celle de B=0xFF.
Comme G est un octet apres R (et B un octet apres G) :
  A = x^8 * B    et    B = x^8 * C     (dans GF(2)[x]/P)

Mesures :
  CRC(rouge) ^ CRC(vert) = A ^ B = 0x82d1
  CRC(vert)  ^ CRC(bleu) = B ^ C = 0xf8ed

=> (x^8 ^ 1) * C = 0xf8ed, ce qui determine C, donc B, A, puis la constante Z
(checksum d'une couleur nulle). Chaque bit d'un octet contribue via une
multiplication par x, donc l'octet complet 0xFF correspond a une
multiplication par (1+x+...+x^7) = (x+1)^7, qu'on inverse pour obtenir la
contribution d'un bit isole.
"""

POLY = 0x56EB  # trouve par recherche exhaustive (cf. docs/protocol.md)
P = (1 << 16) | POLY  # x^16 + POLY

CRC_RED = 0xC4F6
CRC_GREEN = 0x4627
CRC_BLUE = 0xBECA


def gf_mul(a: int, b: int) -> int:
    """Multiplication dans GF(2)[x] / P."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & (1 << 16):
            a ^= P
    return result


def gf_pow(a: int, n: int) -> int:
    result = 1
    while n:
        if n & 1:
            result = gf_mul(result, a)
        a = gf_mul(a, a)
        n >>= 1
    return result


def _poly_divmod(a: int, b: int) -> tuple[int, int]:
    """Division euclidienne dans GF(2)[x] (pas de reduction mod P)."""
    if b == 0:
        raise ZeroDivisionError
    q = 0
    db = b.bit_length() - 1
    while a.bit_length() - 1 >= db and a:
        shift = (a.bit_length() - 1) - db
        q ^= 1 << shift
        a ^= b << shift
    return q, a


def _poly_mul(a: int, b: int) -> int:
    """Multiplication dans GF(2)[x] sans reduction."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
    return result


def gf_inv(a: int) -> int:
    """Inverse modulo P via Euclide etendu (P n'est pas irreductible, donc
    l'exponentiation de Fermat ne s'applique pas)."""
    if a == 0:
        raise ZeroDivisionError("element non inversible")
    r0, r1 = P, a
    s0, s1 = 0, 1
    while r1:
        q, r = _poly_divmod(r0, r1)
        r0, r1 = r1, r
        s0, s1 = s1, s0 ^ _poly_mul(q, s1)
    if r0 != 1:
        raise ValueError(f"{a:#06x} n'est pas inversible modulo P (pgcd={r0:#x})")
    return s0 % (1 << 16)


X8 = 1 << 8
X8_PLUS_1 = X8 ^ 1
# (1 + x + ... + x^7) = (x+1)^7
SUM_X0_X7 = 0xFF


def _derive():
    c = gf_mul(gf_inv(X8_PLUS_1), CRC_GREEN ^ CRC_BLUE)  # contribution de B=0xFF
    b = gf_mul(X8, c)  # contribution de G=0xFF
    a = gf_mul(X8, b)  # contribution de R=0xFF

    assert a ^ b == CRC_RED ^ CRC_GREEN, "incoherence: le modele lineaire ne tient pas"

    z = CRC_RED ^ a  # checksum pour la couleur (0, 0, 0)

    inv_sum = gf_inv(SUM_X0_X7)
    bit_r = gf_mul(inv_sum, a)  # contribution du bit 0 de R
    bit_g = gf_mul(inv_sum, b)
    bit_b = gf_mul(inv_sum, c)
    return z, bit_r, bit_g, bit_b


Z, BIT_R, BIT_G, BIT_B = _derive()


def _byte_contribution(value: int, bit0: int) -> int:
    total = 0
    for i in range(8):
        if value & (1 << i):
            total ^= gf_mul(gf_pow(2, i), bit0)
    return total


def checksum(r: int, g: int, b: int) -> int:
    """Checksum 16 bits du Report 0x3f pour la couleur donnee."""
    return (
        Z
        ^ _byte_contribution(r, BIT_R)
        ^ _byte_contribution(g, BIT_G)
        ^ _byte_contribution(b, BIT_B)
    )


def checksum_report(r: int, g: int, b: int) -> bytes:
    value = checksum(r, g, b)
    return bytes([0x3F, (value >> 8) & 0xFF, value & 0xFF])


if __name__ == "__main__":
    print(f"POLY={POLY:#06x}  Z={Z:#06x}")
    for name, rgb, expected in [
        ("rouge", (255, 0, 0), CRC_RED),
        ("vert", (0, 255, 0), CRC_GREEN),
        ("bleu", (0, 0, 255), CRC_BLUE),
    ]:
        got = checksum(*rgb)
        flag = "OK" if got == expected else "ECHEC"
        print(f"  {name:6s} {rgb} -> {got:#06x} (attendu {expected:#06x}) {flag}")
    print("\nPredictions:")
    for name, rgb in [
        ("magenta", (255, 0, 255)),
        ("jaune", (255, 255, 0)),
        ("cyan", (0, 255, 255)),
        ("blanc", (255, 255, 255)),
        ("noir", (0, 0, 0)),
    ]:
        print(f"  {name:8s} {rgb} -> {checksum(*rgb):#06x}")
