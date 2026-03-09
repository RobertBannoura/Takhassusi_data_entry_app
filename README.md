# Majalaty Simple App v2

Updated based on your UI feedback:
- Arabic fields use RTL styling
- EN/AR fields are paired beside each other
- cutoff design is improved
- regular and parallel admission are grouped in the same cutoff row
- current university stays selected
- repeated major values stay filled for the next entry
- simple duplicate warning, search, recent entries, and exports

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## Data model

### universities
General university information.

### majors
General major information and regular tuition.

### major_cutoffs
Per-stream cutoffs with:
- regular cutoff average
- parallel cutoff average
- parallel credit hour price
