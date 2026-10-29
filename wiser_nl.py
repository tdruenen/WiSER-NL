# =============================================================================
#      _       ___     _____ ______ _____        _   _ _
#     | |     / (_)   / ____|  ____|  __ \      | \ | | |
#     | | /| / / _   | (___ | |__  | |__) | ___ |  \| | |
#     | |/ |/ / | |   \___ \|  __| |  _  / |___|| . ` | |
#    _|__/|__/__|_|_______) | |____| | \ \      | |\  | |__
#   |______________________/|______|_|  \_\     |_| \_|____|
#
# Copyright (c) 2026 Eindhoven University of Technology
#
# Auteur: Thijs van Druenen
# Versie: 1.0
#
# Voor informatie over licentie, aansprakelijkheid, disclaimer en
# gebruiksvoorwaarden wordt verwezen naar:
# LICENSE
# DISCLAIMER.md
# =============================================================================

import subprocess
import sys
import os
import shutil
from datetime import datetime

# ---------------- Settings ---------------- #

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

LOG_FILE = os.path.join(
    TEMP_DIR,
    "run_log.txt"
)

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Main pipeline steps
pipeline_steps = [
    ("Genereren van domeinpunten", "01_generate_points.py"),
    ("Interpoleren van windgegevens", "02_interpolate.py"),
    ("Filteren van richtingsdatasets", "03_filter_wind_directions.py"),
    ("Samenvoegen van richtingsdatasets", "04_combine_wind_directions.py"),
    ("Genereren van windsnelheidsverdelingen", "05_create_distributions.py"),
    ("Uitvoeren van kwaliteitscontrole", "06_check_duplicate_hours.py"),
    ("Berekenen van effectieve ruwheid", "07_calculate_effective_roughness.py"),
    ("Aanmaken van uitvoerarchief", "08_generate_output.py")
]

# Cleanup step
cleanup_script = "09_cleanup.py"

# ---------------- Logging ---------------- #

def write_log(text):

    with open(
        LOG_FILE,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(text + "\n")

print(r'''
=============================================================================
      _       ___     _____ ______ _____        _   _ _
     | |     / (_)   / ____|  ____|  __ \      | \ | | |
     | | /| / / _   | (___ | |__  | |__) | ___ |  \| | |
     | |/ |/ / | |   \___ \|  __| |  _  / |___|| . ` | |
    _|__/|__/__|_|_______) | |____| | \ \      | |\  | |__
   |______________________/|______|_|  \_\     |_| \_|____|

 Copyright (c) 2026 Eindhoven University of Technology

 Auteur: Thijs van Druenen
 Versie: 1.0

 Voor informatie over licentie, aansprakelijkheid, disclaimer en
 gebruiksvoorwaarden wordt verwezen naar:
 LICENSE
 DISCLAIMER.md
=============================================================================
''')

def save_log_on_failure():

    if not os.path.exists(LOG_FILE):
        return

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    dst = os.path.join(
        OUTPUT_DIR,
        f"Foutlog_{timestamp}.txt"
    )

    shutil.copy2(
        LOG_FILE,
        dst
    )

    print(
        f"INFO: Foutlog opgeslagen in: {dst}"
    )

# Initialize log

with open(
    LOG_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write("=== LOGBOEK ===\n")
    f.write(
        f"Start: {datetime.now().astimezone().isoformat()}\n\n"
    )

# ---------------- Runner ---------------- #

def run_script(label, script):

    header = f"\n===== {label} ====="

    print(header)
    write_log(header)

    script_path = os.path.join(SRC_DIR, script)

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        cwd=BASE_DIR
    )

    # Standard output
    if result.stdout:

        print(result.stdout)
        write_log(result.stdout)

    # Standard error
    if result.stderr.strip():

        print(result.stderr)
        write_log(result.stderr)

    # Check return code
    if result.returncode != 0:

        msg = (
            f"\nFOUT: Stap mislukt: "
            f"{label}"
        )

        print(msg)
        write_log(msg)

        save_log_on_failure()

        sys.exit(1)

    msg = (
        f"SUCCES: Voltooid: "
        f"{label}"
    )

    print(msg)
    write_log(msg)

# ---------------- Main ---------------- #

if __name__ == "__main__":

    print(
        "INFO: Starten van volledige verwerkingsketen...\n"
    )

    write_log(
        "Verwerkingsketen gestart"
    )


    # Run main pipeline
    for label, script in pipeline_steps:

        script_path = os.path.join(SRC_DIR, script)

        if not os.path.exists(script_path):

            msg = (
                f"FOUT: Script niet gevonden: "
                f"{script} ({label})"
            )

            print(msg)
            write_log(msg)

            save_log_on_failure()

            sys.exit(1)

        run_script(
            label,
            script
        )

    # Finalize log before ZIP/export

    final_msg = (
        f"\nSUCCES: Verwerkingsketen voltooid op "
        f"{datetime.now().astimezone().isoformat()}"
    )

    print(final_msg)
    write_log(final_msg)

    print(
        "\nINFO: Export voltooid"
    )

    # From this point onwards we do NOT care about logging.
    # The log is already included in the ZIP created by step 08.

    cleanup_path = os.path.join(SRC_DIR, cleanup_script)

    if os.path.exists(cleanup_path):


        print(
            "\nINFO: Starten met opschonen..."
        )

        result = subprocess.run(
            [sys.executable, cleanup_path],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

        if result.returncode != 0:

            print(
                f"WAARSCHUWING: Opschonen mislukt "
                f"(retourcode {result.returncode})"
            )

        else:

            print(
                "SUCCES: Opschonen voltooid"
            )

    else:

        print(
            f"WAARSCHUWING: Opschoonscript niet gevonden: "
            f"{cleanup_script}"
        )

    print(
        "\nGEREED: Alle stappen succesvol voltooid!"
    )
