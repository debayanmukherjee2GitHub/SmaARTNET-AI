# SmaARTNET-AI

SmaARTNET-AI is an offline desktop tool for turning local network inventory files into a draft network blueprint. Inventory processing and outputs run on your computer. Local AI suggestions are optional and use Ollama; the app does not send inventory to Azure or another cloud service.

## Run from VS Code

1. Open `C:\Users\debpe\Documents\SmaARTNET-AI` in VS Code with **File → Open Folder**.
2. Open **Terminal → New Terminal**.
3. Run:

   ```powershell
   cd .\smartnet_offline
   python app.py
   ```

   If `python` is not recognized, try `py app.py`. Use Python 3.10 or newer with Tkinter available. No Python packages are required for the basic offline workflow.
4. In the app, choose a `.csv` or `.xlsx` inventory, select an output folder, and click **Generate offline blueprint**.

## Input workbook

For Excel, the app reads worksheets named `Inventory` and `Connections` (case-insensitive). `Inventory` contains device details and names. `Connections` is optional and should include source and target endpoint columns, such as `Source` and `Target`, whose values match device names in `Inventory`. If there is no `Inventory` sheet, the first worksheet is used. CSV files are treated as a single inventory table. Legacy `.xls` files are not supported.

## Generated files

The selected output folder receives a Markdown network report, physical and logical topology diagrams, an optional AI-recommended topology diagram, a configuration planning CSV, and normalized JSON data. The diagrams and connection mapping use explicit inventory data; AI-suggested links are labeled as proposals for review. The configuration guide does not generate vendor commands.

For detailed behavior, workbook fields, and optional local Ollama setup, see [`smartnet_offline/README.md`](smartnet_offline/README.md).
