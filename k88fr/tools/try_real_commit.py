"""Rejoue EXACTEMENT la sequence de commit/sauvegarde capturee pour le rouge
(apply_rouge.pcapng, frames 155-177), sans rien recalculer, pour verifier si
ce mecanisme (Report 0x45 + checksum 0x3f) rend la couleur vraiment persistante."""

import hid

VID = 0x3938
PID = 0x1150
TARGET_USAGE_PAGE = 0xFF19

SEQUENCE = [
    bytes.fromhex("09020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"),  # frame 155: open (0x02)
    bytes.fromhex("45000112000000010103ff000000000001000000033a810000000000008f036c020100000094f01a0028816400e2416a00c4080c000002000000000000003aa104d50fb7044b000000d50fb704e43aa1048f03000094f01a00e75464006c020000d50fb70454515e00e43aa10428f11a00cf4f6400d50fb70428f11a00e43aa1042213a000000000ff406a000001a00100106411c800000000dcef1a00e4ef1a0044806400221301a0d50fb704221301a0feffffff00000000e43aa104e0ef1a00cb55c4774418a1040934c077d50fb70420000000e43aa104200000000000000000f01a0091e75b004418a104152362001d236200200000006418a104bf7c640028f01a00"),  # frame 159: Report 0x45 (chunk 1)
    bytes.fromhex("45000001000000010103ff000000000001000000033a810000000000008f036c020100000094f01a0028816400e2416a00c4080c000002000000000000003aa104d50fb7044b000000d50fb704e43aa1048f03000094f01a00e75464006c020000d50fb70454515e00e43aa10428f11a00cf4f6400d50fb70428f11a00e43aa1042213a000000000ff406a000001a00100106411c800000000dcef1a00e4ef1a0044806400221301a0d50fb704221301a0feffffff00000000e43aa104e0ef1a00cb55c4774418a1040934c077d50fb70420000000e43aa104200000000000000000f01a0091e75b004418a104152362001d236200200000006418a104bf7c640028f01a00"),  # frame 165: Report 0x45 (chunk 2)
    bytes.fromhex("09070000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"),  # frame 169: close (0x07)
    bytes.fromhex("3fc4f6"),  # frame 177: Report 0x3f (checksum captured)
]


def find_target_path() -> bytes:
    for info in hid.enumerate(VID, PID):
        if info["usage_page"] == TARGET_USAGE_PAGE:
            return info["path"]
    raise RuntimeError("Device Col06 introuvable")


def main() -> None:
    path = find_target_path()
    for i, report in enumerate(SEQUENCE, 1):
        dev = hid.device()
        dev.open_path(path)
        n = len(report)
        print(f"[{i}/{len(SEQUENCE)}] {n} octets: {report[:8].hex()}...")
        if report[0] in (0x14, 0x20, 0x3f, 0x45):
            ret = dev.send_feature_report(report)
        else:
            ret = dev.write(report)
        print(f"    -> {ret}  error={dev.error()}")
        dev.close()
        import time
        time.sleep(0.15)
    print("Termine.")


if __name__ == "__main__":
    main()
