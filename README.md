### tl;dr

This script reads data from the GitHub API, stores the responses locally as JSON with minimal changes, and uses duckdb to extracts insights from the local JSON files.

In this case, we are interested in understanding the contributions to the magic open-source data transformations repo, [spellbook](https://github.com/duneanalytics/spellbook) in terms of PRs/issues created and review work (commits and comments).

### Getting Started

1. Install  [poetry](https://python-poetry.org/docs/) and [duckdb](https://duckdb.org/docs/installation/) if needed

2. Run ```poetry install``` to install dependencies

3. Set two local environment variables in the script `read-write-prs.py`:
- SPELLBOOK_JSON_STATS_LOC > full path to the folder that will be used to store the JSON API responses locally
- MM_GITHUB_API > access token to GitHub API (no extra permissions needed)

4. Run `read-write-prs.py`. Storing all files locally the first time will take some time. If all goes well, the output will be printed in your terminal and a CSV version will be made available in the `output` folder.

:fire:
