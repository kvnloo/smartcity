"""Build a SUMO plain network from the Naperville metre graph."""

from __future__ import annotations

import json
import subprocess

from smartcity.adapters.sumo import sumo_binaries, write_plain_xml


def main() -> None:
    paths = write_plain_xml()
    bins = sumo_binaries()
    print(json.dumps({"paths": paths, "binaries": bins}, indent=2))
    netconvert = bins.get("netconvert")
    if netconvert:
        cmd = paths["netconvert"].split()
        cmd[0] = netconvert
        subprocess.check_call(cmd)
        print("wrote", paths["net"])
    else:
        print("netconvert not on PATH — nod/edg XML is ready. Install Eclipse SUMO to compile the net.")


if __name__ == "__main__":
    main()
