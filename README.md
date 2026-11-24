> Upload the provided rideops_support_tickets.csv on the app home page. The dataset is not included in this repo.

# RideOps Escalation Desk

Escalation Desk helps an L1 agent attach known issues, complete evidence, and send a complete engineering handoff.
The thesis is that backlog grows through inflow and cycle time, while avoidable engineering loops drive much of the cycle time.
The app uses rules and text similarity, not an engineering-outcome probability predictor.
The Scorecard protects reopen and CSAT guardrails while measuring precision and backlog.
September metrics are right-censored and the bundled data must remain private.

Success target: **-15% from process changes in 8 weeks (-30% if repeat contacts also fall)**.

## Exact local run steps

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

Open the local URL printed by Streamlit. On the home page, use the bundled CSV or upload a
compatible RideOps CSV with the data dictionary's columns.

## Fresh-clone commands

```bash
git clone <private-repository-url> rideops-escalation-desk
cd rideops-escalation-desk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

## Deployment

Use a private GitHub repository, grant the reviewer repository access, and deploy `app.py`
through Streamlit Community Cloud. Never make the CSV public. A reviewer can upload the CSV
through the home-page fallback if the bundled data is not included in a private clone.

