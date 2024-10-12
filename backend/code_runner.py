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
            results.append({
                'inputs': inputs,
                'expected': expected,
                'result': result,
                'passed': result == expected
            })
        except Exception as e:
            results.append({
                'inputs': inputs,
                'expected': expected,
                'result': str(e),
                'passed': False
            })
    
    return results

def generate_test_cases():
    return [
        ((1,), "1"),
        ((3,), "Fizz"),
        ((5,), "Buzz"),
        ((15,), "FizzBuzz"),
        ((4,), "4")
    ]

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
