# Android End2End Tests

To support parallel execution in CI, tests are split into dedicated subfolders:

- `loadline/`: Loadline benchmark tests.
- `speedometer/`: Speedometer benchmark tests.
- `others/`: All other tests.

Each folder has a `runner.py` to run its specific tests.
The top-level `runner.py` runs all tests.
