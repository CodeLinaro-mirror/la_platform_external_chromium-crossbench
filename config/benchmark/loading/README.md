# Configs for the loading benchmark

## Running the benchmark

```
./cb.py loading --page-config config/benchmark/loading/page_config_phone.hjson --probe-config config/benchmark/loading/probe_config.hjson --network-config config/benchmark/loading/network_config.hjson --separate --browser <browser>
```

The browser can be `android:chrome-canary`, `android:chrome-stable` etc. See crossbench docs for the full list of options.

If you see a `Could not find wpr.go binary` error:

* If you have chromium checked out locally: set `CHROMIUM_SRC` environment variable to the path of your chromium/src folder.

* If not: see the next section.

### Running the benchmark without full chromium checkout

Check out the [catapult](https://chromium.googlesource.com/catapult) repository:

```
git clone https://chromium.googlesource.com/catapult
```

Then modify the `wpr_go_bin` attribute in the `config/benchmark/loading/network_config.hjson` to point to the location of the `wpr.go` file. You can find it at `web_page_replay_go/src/wpr.go` inside the catapult repository.

## Other running options

### Run the benchmark on live sites

```
./cb.py loading --page-config config/benchmark/loading/page_config_phone.hjson --probe-config config/benchmark/loading/probe_config.hjson --separate --browser <browser>
```

### Record a new WPR archive

Uncomment the `wpr: {},` line in the probe config and run the benchmark on live sites (see the command above). The archive will be located in `results/latest/archive.wprgo`

### Run the benchmark with full set of experimental metrics

```
./cb.py loading --page-config config/benchmark/loading/page_config_phone.hjson --probe-config config/benchmark/loading/probe_config_experimental.hjson --network-config config/benchmark/loading/network_config.hjson --separate --browser <browser>
```

Note that computing extra metrics takes additional time and the trace size can be quite large as well.
