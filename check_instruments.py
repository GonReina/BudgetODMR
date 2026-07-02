"""
Connectivity check for the SMCV100B and the Red Pitaya SCPI server.

Run this on the PC BEFORE odmr_smcv100b_pc.py to prove both links work. It opens
a raw SCPI socket to each instrument and asks it to identify itself -- the real
end-to-end test (more than a ping, which only proves the network layer).

    python check_instruments.py
"""

import socket

# Set these to match odmr_smcv100b_pc.py
SMCV_IP, SMCV_PORT = "169.254.2.20", 5025
RP_IP,   RP_PORT   = "192.168.137.150", 5000


def scpi_query(ip, port, cmd, term, timeout=5.0):
    """Open a socket, send one query, return the reply (or raise)."""
    with socket.create_connection((ip, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall(cmd.encode() + term)
        buf = b""
        while not buf.endswith(term):
            chunk = s.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf.decode(errors="replace").strip()


def check(name, ip, port, cmd, term, hint):
    print(f"\n[{name}] {ip}:{port}  -> {cmd!r}")
    try:
        reply = scpi_query(ip, port, cmd, term)
        if reply:
            print(f"  OK: {reply}")
            return True
        print(f"  REPLY EMPTY -- connected but no answer. {hint}")
    except socket.timeout:
        print(f"  TIMEOUT -- port open? wrong port/terminator? {hint}")
    except ConnectionRefusedError:
        print(f"  REFUSED -- nothing listening on that port. {hint}")
    except OSError as e:
        print(f"  NO ROUTE/UNREACHABLE ({e}). Check cabling, IP and subnet. {hint}")
    return False


def main():
    ok_smcv = check(
        "SMCV100B", SMCV_IP, SMCV_PORT, "*IDN?", b"\n",
        hint="Check the IP on the instrument screen (Setup > Network) and that "
             "your PC NIC is on the same subnet.",
    )
    ok_rp = check(
        "Red Pitaya", RP_IP, RP_PORT, "ACQ:DEC?", b"\r\n",
        hint="Start the SCPI server from the Red Pitaya web interface (port 5000).",
    )

    print("\n" + "=" * 40)
    print(f"SMCV100B : {'reachable' if ok_smcv else 'NOT reachable'}")
    print(f"RedPitaya: {'reachable' if ok_rp else 'NOT reachable'}")
    if ok_smcv and ok_rp:
        print("Both good -- you can run odmr_smcv100b_pc.py")


if __name__ == "__main__":
    main()
