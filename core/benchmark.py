import time


def run_benchmark(config):
    """
    Runs a benchmark test to determine the maximum PID read rate.
    """
    results = []
    conn_config = config.get('network', {}).get('obd_connection', {})
    port = conn_config.get('port')
    fast = conn_config.get('fast', False)

    selected_pids = config['pid_management']['selected_pids']

    if not selected_pids:
        print("No PIDs selected for logging. Please select PIDs in the PID Management menu.")
        return None

    print("\n--- Starting PID Benchmark Test ---")
    print("This will test logging with an increasing number of PIDs.")
    print("Each test runs for 10 seconds. Press Ctrl+C to stop at any time.")
    print("------------------------------------")

    # The preconfigured MCP2515 deployment does not support serial USB/Bluetooth
    # benchmark runs. If the user selected a serial adapter type this will be
    # skipped. Use a development machine with a USB OBD adapter to run benchmarks.
    conn_type = config.get('network', {}).get('obd_connection', {}).get('type')
    if conn_type in (None, 'local_mcp2515', 'wireless_can'):
        print("Benchmarking of USB/serial OBD adapters is disabled in this deployment.")
        return None

    try:
        # Only attempt to import python-obd when the connection type requires it
        conn_type = config.get('network', {}).get('obd_connection', {}).get('type')
        if conn_type in (None, 'local_mcp2515', 'wireless_can'):
            print("Benchmarking of USB/serial OBD adapters is disabled in this deployment.")
            return None

        # Lazy import to avoid importing python-obd on systems that use MCP2515
        import obd
        print(f"Connecting with settings: port='{port or 'auto-scan'}', fast={fast}")
        connection = obd.OBD(port, fast=fast) # port can be None for auto-scan
        if not connection.is_connected():
            print("ERROR: Could not connect to OBD-II adapter.")
            return None

        # Build the list of command objects from the names
        all_commands = {name: getattr(obd.commands, name) for name in selected_pids if hasattr(obd.commands, name)}
        supported_commands = {name: cmd for name, cmd in all_commands.items() if cmd in connection.supported_commands}

        if not supported_commands:
            print("None of the selected PIDs are supported by this vehicle.")
            connection.close()
            return None

        pid_names_to_test = list(supported_commands.keys())

        def chunker(seq, size):
            for pos in range(0, len(seq), size):
                yield seq[pos:pos + size]

        for i in range(1, len(pid_names_to_test) + 1):
            pids_for_this_run = pid_names_to_test[:i]
            commands_for_this_run = [supported_commands[name] for name in pids_for_this_run]

            command_groups = list(chunker(commands_for_this_run, 6))

            print(f"\n[TESTING] {i} PID(s) in {len(command_groups)} group(s): {', '.join(pids_for_this_run)}")

            query_count = 0
            error_count = 0
            start_time = time.time()

            while time.time() - start_time < 10: # Run test for 10 seconds
                for group in command_groups:
                    pids_hex = "".join([cmd.command.decode()[2:] for cmd in group])
                    command_str = f"01{pids_hex}"

                    multi_cmd = obd.OBDCommand(f"BENCHMARK_GROUP_{pids_hex}",
                                               "Benchmark Multi-PID Request",
                                               command_str.encode(),
                                               0, # Bytes, 0 for variable length response
                                               decoder=lambda msgs: msgs) # Don't need a real decoder

                    response = connection.query(multi_cmd, force=True)

                    # A single query here represents a query for all PIDs in the group
                    query_count += len(group)

                    if response.is_null():
                        error_count += len(group)

                # A small sleep to prevent overwhelming the bus, but keep it fast
                time.sleep(0.001)

            end_time = time.time()
            duration = end_time - start_time
            pids_per_second = query_count / duration

            result_entry = {
                "num_pids": i,
                "pids_per_second": round(pids_per_second, 2),
                "total_queries": query_count,
                "errors": error_count,
                "duration_sec": round(duration, 2)
            }
            results.append(result_entry)

            print(f"  [RESULT] Read Rate: {result_entry['pids_per_second']} PID/s, Errors: {result_entry['errors']}")

    except KeyboardInterrupt:
        print("\nBenchmark test stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred during the benchmark: {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

    return results
