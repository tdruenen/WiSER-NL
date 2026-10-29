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

import os
import shutil
import logging

# ---------------- Logging ---------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger(__name__)
# ---------------- Settings ---------------- #
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

TEMP_DIR = os.path.join(
    BASE_DIR,
    "temp"
)

# ---------------- Check folder ---------------- #
if not os.path.exists(TEMP_DIR):
    raise FileNotFoundError(
        f"Map niet gevonden: {TEMP_DIR}"
    )

logger.info(f"Map wordt opgeschoond: {TEMP_DIR}")

# ---------------- Remove contents ---------------- #
for item in os.listdir(TEMP_DIR):
    path = os.path.join(TEMP_DIR, item)

    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)  # delete file
            logger.info(f"Bestand verwijderd: {path}")

        elif os.path.isdir(path):
            shutil.rmtree(path)  # delete directory
            logger.info(f"Map verwijderd: {path}")

    except Exception as e:
        logger.warning(
            f"Verwijderen mislukt voor {path}: {e}"
        )

logger.info("\nBestanden succesvol opgeschoond.")