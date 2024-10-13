import json
import sys
import io
import time

def run_tests(solution):
    test_cases = generate_test_cases()
    results = []
    
    for inputs, expected in test_cases:
        try:
            result = solution(*inputs)

            # Cast both result and expected to strings for comparison
            result_str = str(result)
            expected_str = str(expected)

            results.append({
                'inputs': inputs,
                'expected': expected_str,
                'result': result_str,
                'passed': result_str == expected_str
            })
        except Exception as e:
            results.append({
                'inputs': inputs,
                'expected': str(expected),
                'result': str(e),
                'passed': False
            })
    
    return results

def generate_test_cases():
    # Example test cases will be read from the test_cases.json file in this case
    with open("test_cases.json", "r") as f:
        test_cases = json.load(f)
    return test_cases

if __name__ == "__main__":
    import user_code  # Directly import the user's code

    # Capture prints from the user's code
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    # Run the tests
    test_results = run_tests(user_code.solution)

    # Get the captured print output
    print_output = new_stdout.getvalue()

    # Restore stdout
    sys.stdout = old_stdout

    # Split print output into lines and add timestamps
    timestamped_prints = []
    for line in print_output.strip().splitlines():
        current_time = time.strftime("%H:%M:%S", time.localtime())
        timestamped_prints.append((current_time, line))

    # Combine the print output (with timestamps) and test results into a JSON object
    combined_result = {
        'stdout': timestamped_prints,  # List of (timestamp, print) tuples
        'test_cases': test_results
    }

    # Output the combined JSON object
    print(json.dumps(combined_result))
