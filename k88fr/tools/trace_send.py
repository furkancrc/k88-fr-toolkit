"""Debogueur minimal : intercepte l'envoi du rapport 0x3f par le logiciel
officiel et remonte la pile d'appels jusqu'a la fonction qui a calcule le
checksum.

Principe : on se greffe sur le processus, on pose un point d'arret sur l'appel
a DeviceIoControl (et a WriteFile) dans les enveloppes d'E/S reperees par
Ghidra. A chaque passage on regarde le tampon transmis ; quand son premier
octet vaut 0x3f, on a trouve l'envoi du checksum. On releve alors les adresses
de retour presentes sur la pile : elles designent les fonctions appelantes,
donc celle qui vient de produire les deux octets.

A lancer AVANT de cliquer sur APPLIQUER dans le logiciel officiel.
IMPORTANT : doit tourner avec le Python 32 bits (comme le logiciel).
"""

import ctypes
import ctypes.wintypes as w
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Points d'arret : sites d'appel releves dans Ghidra
BREAKPOINTS = {
    0x4DECA2: "DeviceIoControl",
    0x4DED22: "WriteFile",
}

CODE_LO, CODE_HI = 0x401000, 0x6A5000  # plage du code applicatif

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004
CONTEXT_FULL = 0x10007
TRAP_FLAG = 0x100


class EXCEPTION_RECORD(ctypes.Structure):
    pass


EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", w.DWORD),
    ("ExceptionFlags", w.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", w.LPVOID),
    ("NumberParameters", w.DWORD),
    ("ExceptionInformation", w.LPVOID * 15),
]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD), ("dwFirstChance", w.DWORD)]


class DEBUG_EVENT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("Exception", EXCEPTION_DEBUG_INFO), ("pad", ctypes.c_byte * 160)]

    _fields_ = [
        ("dwDebugEventCode", w.DWORD),
        ("dwProcessId", w.DWORD),
        ("dwThreadId", w.DWORD),
        ("u", _U),
    ]


class FLOATING_SAVE_AREA(ctypes.Structure):
    _fields_ = [
        ("ControlWord", w.DWORD), ("StatusWord", w.DWORD), ("TagWord", w.DWORD),
        ("ErrorOffset", w.DWORD), ("ErrorSelector", w.DWORD), ("DataOffset", w.DWORD),
        ("DataSelector", w.DWORD), ("RegisterArea", ctypes.c_byte * 80),
        ("Cr0NpxState", w.DWORD),
    ]


class CONTEXT(ctypes.Structure):
    _fields_ = [
        ("ContextFlags", w.DWORD),
        ("Dr0", w.DWORD), ("Dr1", w.DWORD), ("Dr2", w.DWORD),
        ("Dr3", w.DWORD), ("Dr6", w.DWORD), ("Dr7", w.DWORD),
        ("FloatSave", FLOATING_SAVE_AREA),
        ("SegGs", w.DWORD), ("SegFs", w.DWORD), ("SegEs", w.DWORD), ("SegDs", w.DWORD),
        ("Edi", w.DWORD), ("Esi", w.DWORD), ("Ebx", w.DWORD), ("Edx", w.DWORD),
        ("Ecx", w.DWORD), ("Eax", w.DWORD), ("Ebp", w.DWORD), ("Eip", w.DWORD),
        ("SegCs", w.DWORD), ("EFlags", w.DWORD), ("Esp", w.DWORD), ("SegSs", w.DWORD),
        ("ExtendedRegisters", ctypes.c_byte * 512),
    ]


def read_mem(h, addr, size):
    buf = (ctypes.c_char * size)()
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got)):
        return None
    return buf.raw[: got.value]


def write_mem(h, addr, data):
    old = w.DWORD(0)
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), 0x40, ctypes.byref(old))
    written = ctypes.c_size_t(0)
    ok = k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data), ctypes.byref(written))
    k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old, ctypes.byref(old))
    k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))
    return bool(ok)


def get_context(tid):
    th = k32.OpenThread(0x1F03FF, False, tid)
    ctx = CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    k32.GetThreadContext(th, ctypes.byref(ctx))
    return th, ctx


def set_context(th, ctx):
    k32.SetThreadContext(th, ctypes.byref(ctx))
    k32.CloseHandle(th)


def u32(data, off):
    return int.from_bytes(data[off : off + 4], "little")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m k88fr.tools.trace_send <PID>")
        sys.exit(1)
    pid = int(sys.argv[1])

    if not k32.DebugActiveProcess(pid):
        print(f"Impossible de se greffer sur le PID {pid} (erreur {ctypes.get_last_error()})")
        sys.exit(1)
    k32.DebugSetProcessKillOnExit(False)
    print(f"Greffe sur le PID {pid}. Clique maintenant sur APPLIQUER dans le logiciel.")
    print("(Ctrl+C pour arreter)\n")

    hproc = None
    originals = {}
    pending = {}
    hits = 0

    evt = DEBUG_EVENT()
    while True:
        if not k32.WaitForDebugEvent(ctypes.byref(evt), 1000):
            continue
        code = evt.dwDebugEventCode
        status = DBG_CONTINUE

        if code == 3:  # CREATE_PROCESS
            hproc = k32.OpenProcess(0x1F0FFF, False, pid)
            for addr in BREAKPOINTS:
                orig = read_mem(hproc, addr, 1)
                if orig and write_mem(hproc, addr, b"\xcc"):
                    originals[addr] = orig
            print(f"{len(originals)} point(s) d'arret poses\n")

        elif code == 1:  # EXCEPTION
            rec = evt.u.Exception.ExceptionRecord
            addr = rec.ExceptionAddress or 0

            if rec.ExceptionCode == EXCEPTION_BREAKPOINT and addr in originals:
                th, ctx = get_context(evt.dwThreadId)
                esp = ctx.Esp
                stack = read_mem(hproc, esp, 0x400) or b""

                # arguments deja empiles : [esp]=arg1, [esp+4]=arg2, ...
                name = BREAKPOINTS[addr]
                if name == "DeviceIoControl":
                    ioctl = u32(stack, 4)
                    buf_ptr = u32(stack, 8)
                    buf_len = u32(stack, 12)
                else:  # WriteFile
                    ioctl = 0
                    buf_ptr = u32(stack, 4)
                    buf_len = u32(stack, 8)

                payload = read_mem(hproc, buf_ptr, min(buf_len, 32)) if buf_ptr else None
                if payload:
                    rid = payload[0]
                    if rid in (0x3F, 0x45, 0x14):
                        hits += 1
                        print(f"--- {name} : rapport {rid:#04x}"
                              f"{f' ioctl={ioctl:#x}' if ioctl else ''} "
                              f"len={buf_len} : {payload[:12].hex()} ---")
                        if rid == 0x3F:
                            print("    *** ENVOI DU CHECKSUM ***")
                            print("    adresses de retour sur la pile (code applicatif) :")
                            seen = []
                            for off in range(0, len(stack) - 4, 4):
                                v = u32(stack, off)
                                if CODE_LO <= v < CODE_HI and v not in seen:
                                    seen.append(v)
                                    print(f"      esp+{off:#05x} -> {v:#010x}")
                                if len(seen) >= 14:
                                    break
                            print()

                # remettre l'octet d'origine, reculer EIP, single-step pour re-armer
                write_mem(hproc, addr, originals[addr])
                ctx.Eip = addr
                ctx.EFlags |= TRAP_FLAG
                set_context(th, ctx)
                pending[evt.dwThreadId] = addr

            elif rec.ExceptionCode == EXCEPTION_SINGLE_STEP and evt.dwThreadId in pending:
                bp = pending.pop(evt.dwThreadId)
                write_mem(hproc, bp, b"\xcc")
            else:
                status = DBG_EXCEPTION_NOT_HANDLED

        elif code == 5:  # EXIT_PROCESS
            print("Processus termine.")
            break

        k32.ContinueDebugEvent(evt.dwProcessId, evt.dwThreadId, status)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArret demande.")
