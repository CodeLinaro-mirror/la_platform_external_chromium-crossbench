# Gemini Workspace Configuration

Read "./README.md" for all instructions.
Use `poetry run cb` instead of just running `./cb.py`
Use `poetry run help` to gather all details.
Example config files are in the "config/" folder.

# User Mode
By default you are in user-mode and help crossbench users finding the right benchmark and command line flags to complete their tasks.
You are not allowed to modify existing crossbench python files by default.

Never generate python files, only create hjson configs for stories.
Create config.json files for benchmark, story, probe configurations.

Use `poetry run cb_validate_hjson -- file.hjson` to validate generated or modified json and hjson files before running them with crossbench.
Prefer creating json files instead of hjson files to minimize errors with unbalanced quotes.

Use the `poetry run cb describe` meta command to understand how subcommands, benchmarks and probes are configured.
Use the `--debug` options to get more detailed error message.
Use `--env-validation=warn` to bypass input prompts.

Results are stored in the "results/" folder.
The last run's results are in the "results/latest/last_run" folder.

After running crossbench print the resolve symlink path for the "results/latest/" folder.

# Dev Mode
You are only allowed to modify python files in dev-mode and when explicitly instructed.
You must follow the google style guide for python coding.
You are not allowed to use non-local imports or skip pylint checks.

Always do `poetry run ruff check` after completing a change to validate all results.
Run tests with `poetry run pytest tests/crossbench -x -n 7`
