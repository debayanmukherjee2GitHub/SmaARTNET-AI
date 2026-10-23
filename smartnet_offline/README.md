# SmaARTNET-AI offline workspace

This desktop application turns a local network inventory into a draft site blueprint. Inventory parsing, summaries, diagrams, and output files are produced locally. There is no Azure or other cloud integration.

## Run

Install Python 3.10 or newer with Tk support, then run:

```powershell
python app.py
```

Choose a `.csv` or `.xlsx` inventory file to see its row count, column count, blank-cell count, and a preview of up to 100 rows. Only the first worksheet of an `.xlsx` file is read. Legacy `.xls` files are not supported.

Choose an output folder and select **Generate offline blueprint**. The application creates:

- `network_blueprint.md` — site/device summaries, explicit connection mapping, input gaps, and validation notes.
- `physical_topology.svg` and `logical_topology.svg` — diagrams based on supplied site, role, and connection values.
- `recommended_topology.svg` — local-model candidate connections, shown with dashed lines for review.
- `configuration_guide.csv` — export-ready device/platform planning fields from the inventory.
- `blueprint_data.json` — normalized data and generation status.

The analyzer does not invent topology links or move devices between sites. If explicit endpoint columns are absent, it reports that connections were not provided. The configuration guide does not emit vendor commands; those require approved customer standards and platform-specific design rules.

## Optional local AI

Install Ollama and a model on this computer, then use **Find local models** in the application. The local model can suggest device placement, candidate connections, additional device roles, risks, assumptions, and questions. The app connects directly to Ollama's loopback API at `127.0.0.1:11434`; it ignores system proxies and refuses redirects. It does not contact Azure or any other cloud endpoint. If the model is unavailable, the application still creates the deterministic inventory report and records that no AI design was generated.

Candidate model connections and placements are separate from the facts read from the inventory. Treat AI output as a draft and have a network architect validate it before implementation.

The inventory mapper recognizes common header names for device/hostname, site/location, role, vendor, model, platform/OS, management IP, serial number, source/target device, endpoint ports, link type, bandwidth, site requirements, connectivity constraints, business rules, capacity, and resilience. Unrecognized columns remain visible in the app preview but do not affect topology generation.
