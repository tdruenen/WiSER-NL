# WiSER-NL

**WiSER-NL** (Wind Statistics and Effective Roughness for the Netherlands) is an open-source software tool for the determination of:

- wind statistics;
- effective aerodynamic roughness lengths;
- supporting boundary conditions for Computational Fluid Dynamics (CFD) simulations;
- supporting boundary conditions for wind tunnel studies.

WiSER-NL was developed at Eindhoven University of Technology (TU/e) as part of the NEN 8100 revision working group. The tool supports the determination of wind statistics and effective roughness lengths for wind climate assessments in accordance with NEN 8100:2027.

---

# Features

WiSER-NL automatically:

- extracts meteorological statistics from the Dutch Offshore Wind Atlas (DOWA);
- determines representative directional wind statistics;
- determines effective roughness lengths based on upstream land use;
- supports circular and rectangular domains;
- supports between 2 and 360 wind direction sectors;
- generates graphical and tabular output;
- provides traceable and reproducible results through automatic storage of inputs and outputs.

---

# Reference Version

This repository contains the source code of WiSER-NL.

The reference version associated with the NPR is:

**WiSER-NL v1.0**

For reproducible calculations, always use:

- the corresponding software release;
- the corresponding source dataset release.

---

# Software Download

The reference implementation associated with NPR 6097:2027 is:

**WiSER-NL v1.0**

**Software DOI**

https://doi.org/10.xxxx/zenodo.xxxxx

This archived release should be used for reproducible calculations performed in accordance with NPR 6097:2027.

The source code, issue tracker, and development history are available through the GitHub repository:

https://github.com/tdruenen/WiSER-NL

---

# Source Data Download

The source data required by WiSER-NL are **not distributed with the software** and must be downloaded separately.

The official source dataset is published through Zenodo.

**Dataset DOI**

https://doi.org/10.5281/zenodo.23742938

The dataset contains:

- DOWA-based hourly wind speed and wind direction time series at 60 m above ground level;
- metadata for all DOWA locations used by WiSER-NL;
- the Landelijk Grondgebruiksbestand Nederland 2023 (LGN2023);
- the national roughness-length map of the Netherlands derived from LGN2023.

After downloading, extract the dataset archive into the WiSER-NL installation directory. 

For detailed information on the dataset contents, file structure, variables, units, and data production methods, refer to the dataset documentation included in the Zenodo archive.

# Installation

## Requirements

WiSER-NL requires:

- Python 3.11 or newer (recommended);
- required Python packages listed in `requirements.txt`.

Install all dependencies using:

```bash
pip install -r requirements.txt
```

---

# Quick Start

# Running WiSER-NL

Run WiSER-NL using:

```bash
python wiser_nl.py
```

After successful execution, WiSER-NL creates a ZIP archive containing the generated results.


---

# Input File

WiSER-NL uses a single JSON input file:

```text
invoer_parameters.json
```

The input file must be located in the root directory of the WiSER-NL installation, alongside `wiser_nl.py`.

It contains:

- project information;
- coordinate system definition;
- project location;
- domain geometry;
- wind direction sector settings;
- output settings.

A complete description of all input parameters is provided in:

```text
Beschrijving_invoerparameters.txt
```

located in the root directory of this repository.

---

# Methodology

WiSER-NL combines:

## Wind Statistics

Wind statistics are derived from:

**Dutch Offshore Wind Atlas (DOWA)**

The software determines directional points on the domain boundary and derives directional wind statistics from DOWA data.

## Effective Roughness Length

Effective roughness lengths are determined from:

- the Dutch national roughness map;
- upstream land-use conditions;
- distance-weighted roughness analysis.

The implemented methodology follows the procedures described in NPR 6097:2027, which accompanies NEN 8100:2027.

---

# Repository Structure

```text
WiSER-NL/
│
├── CITATION.cff 
├── DISCLAIMER.md 
├── LICENSE  
├── README.md 
├── wiser_nl.py     
├── Beschrijving_invoerparameters.txt
├── invoer_parameters.json
├── requirements.txt
│
├── data/
│   ├── NC/         # DOWA time series
│   ├── NC_Meta/    # DOWA metadata
│   └── LGN/        # Land-use and roughness data
│
├── src/
```

---

# Documentation

Additional documentation is provided in:

- `Beschrijving_invoerparameters.txt`
- NPR 6097:2027

---

# Citation

If WiSER-NL is used in a report, scientific publication, thesis, consultancy study, CFD study, or wind tunnel study, please cite both the software and the source dataset.

## Software

```text
Van Druenen, T. (2026).
WiSER-NL (Version 1.0) [Computer software].
Zenodo.
```

## Dataset

```text
Van Druenen, T. (2026).
WiSER-NL Source Dataset (Version 1.0) [Dataset].
Zenodo.
https://doi.org/10.5281/zenodo.23742938
```

---

# Disclaimer

WiSER-NL is provided for scientific, engineering, and research purposes.

Users remain responsible for verifying:

- model assumptions;
- selected input parameters;
- applicability of the generated results;
- compliance with applicable standards and regulations.

For additional information regarding limitations, warranties, liability, and intended use, see:

```text
DISCLAIMER.md
```

# License

See the `LICENSE` file for licensing information.

---

# Contact

**Eindhoven University of Technology (TU/e)**

**Author:**  
Dr.ir. Thijs van Druenen

GitHub Repository:

https://github.com/tdruenen/WiSER-NL