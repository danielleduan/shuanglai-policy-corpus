# Repository guidance

- Treat government pages and attachments as primary evidence; never invent endpoints or metadata.
- Keep discovery broad and classification explainable. Missing “一体化” is not an exclusion reason.
- Do not commit bulk raw downloads. Commit only code, configuration, documentation, and small reviewed samples.
- Preserve source URLs, timestamps, hashes, parsing status, and exclusion reasons.
- Run `python3 -m unittest discover -s tests -v` and `python3 -m compileall -q src scripts tests` before committing.
