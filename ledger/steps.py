"""The pipeline, in order: command, extra arguments, and what the step does in plain words. Imported by `ledger run`,
DATAHQ and the Airflow DAG; nothing else, so it loads anywhere Python does."""
STEPS = [("ingest", [], "Find the 10-Ks at the SEC and locate the statements"),
         ("extract", ["--run"], "The Reader agent reads each filing and cites every cell"),
         ("extract", ["--load"], "Check every citation against the parsed table"),
         ("reconcile", [], "Clean: one value per year, units and signs, newest filing, compare with SEC data"),
         ("texts", [], "Gather the texts: 10-K MD&A, 8-K earnings releases, investor-page transcripts"),
         ("aispend", ["--run"], "The AI spend reader reads what the MD&A says about AI's part of capex and opex"),
         ("aispend", ["--load"], "Check every quote against the filing; one AI-spend row per company and year"),
         ("notes", ["--run"], "The Notes reader reads segment, property, lease and commitments tables"),
         ("notes", ["--load"], "Check every cited cell; one fact per company, segment or category, and year"),
         ("attribution", ["--run"], "The Attributor reads the industry's money-flow model and the company's data"),
         ("attribution", ["--load"], "Recompute every attributed number from its inputs; one row per company, field and year"),
         ("eval", [], "Score the attribution against the reference set: coverage, agreement, error band"),
         ("rules", [], "Run every check in the rule registry"),
         ("faults", [], "Plant mistakes and confirm the checks catch them"),
         ("evidence", [], "Re-read every cited cell on the rendered 10-K"),
         ("report", [], "Write the review page")]


