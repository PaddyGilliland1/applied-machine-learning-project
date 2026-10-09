# applied-machine-learning

## Project description

[TO WRITE: two to four sentences in your own words: what you built and the dataset you used.]

## Dataset

- Name: Spend over £25,000 in the Department for Transport and its arms-length bodies
- Publisher: Department for Transport
- Source: the data.gov.uk listing,
  <https://www.data.gov.uk/dataset/804be0c6-ae01-4899-bbb9-2317dff1a4f9/financial-transactions-data-dft>,
  which links one CSV file per month
- Licence: UK Open Government Licence (OGL), as stated on the listing,
  <https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>
- File: `dft_spend_over_25k_2022-04_to_2026-03.csv`, beside the notebook

The 48 monthly files from April 2022 to March 2026 are in `dft_originals/`, unchanged from the
publisher. `dft_originals/MANIFEST.csv` gives each file's month, download URL, encoding, SHA-256,
size in bytes and number of rows. For six months, September 2024 to February 2025, the listing
links a GOV.UK publication page instead of a file, so the URL given is the file on that page. I
checked every file against a fresh download from its URL on 9 October 2026.

`build_dataset.py` builds the combined file from them, using only the Python standard library:

```bash
python build_dataset.py
```

It first checks every original against its SHA-256 in the manifest, and stops without writing
anything if a file is missing, extra or changed. It reads each file with the encoding in the
manifest: UTF-8 for January and February 2025, which start with a byte-order mark, cp850 for
April, July and August 2023, and cp1252 for the other 43 months. The three cp850 files store the
pound sign as a byte that cp1252 would read as œ. Most files put spaces around some column names,
and five months name some columns differently, so it maps every header to one set of names. It
adds a `source_file` column naming the original file of each row. It does not clean, filter or
reorder anything. The combined file holds all 126,346 rows of the originals, including 657 blank
rows in May 2022, and the script writes the same bytes on every run.

Contains public sector information licensed under the Open Government Licence v3.0.

## Report

The report is one PDF saved under two names, `module_summary.pdf` and
`Machine_Learning_Analysis_Report.pdf`, and the two files are identical. The brief uses both
names: its overview and rubric call the report `module_summary.pdf`, while its list of what to
submit and Task 7 call it `Machine_Learning_Analysis_Report.pdf`. So I ship the same report under
both.

## How to run

These steps assume Python 3 and Git are installed.

1. Clone this repository and move into its folder.
2. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   On Windows, activate it with `.venv\Scripts\activate` instead.

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Open the notebook, then restart the kernel and run all cells:

   ```bash
   jupyter notebook modeling.ipynb
   ```

A full run takes about seven minutes on a CPU. It writes its five figures, the metrics table,
the table of merged labels and a short model card to `outputs/`, beside the notebook.

## How requirements.txt was created

The notebook was run top to bottom in a fresh virtual environment, and the file was then written
from that environment with:

```bash
pip freeze > requirements.txt
```

## Reflections

[TO WRITE: one ### heading per reflection question in the brief, each answered in your own words.]
