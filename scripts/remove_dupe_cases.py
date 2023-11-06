import json
import sys

previous_case_number = None
for line in sys.stdin:
    data = json.loads(line)
    case_number = data['case_number']
    if case_number != previous_case_number:
        print(line)
        previous_case_number = case_number
        
