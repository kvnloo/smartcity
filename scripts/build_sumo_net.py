"""Build the 8 km micro-ring SUMO net.

Always writes plain nod/edg/typ/con XML plus a .sumocfg. When Eclipse
SUMO's netconvert is on PATH, compiles `output/sumo/naperville.net.xml`.
Otherwise prints the apt / Docker install path; the TraCI mock still ticks.
"""

from __future__ import annotations

import json
import subprocess

from smartcity.adapters.sumo import install_hint, netconvert_argv, sumo_binaries, write_plain_xml


def main() -> None:
    paths = write_plain_xml()
    bins = sumo_binaries()
    print(json.dumps({"paths": paths, "binaries": bins}, indent=2))
    netconvert = bins.get("netconvert")
    if netconvert:
        subprocess.check_call(netconvert_argv(paths, netconvert))
        print("wrote", paths["net"])
    else:
        print(install_hint())


if __name__ == "__main__":
    main()
