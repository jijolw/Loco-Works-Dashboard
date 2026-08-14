import sys
import os
import json

# Setup sys path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, "services"))

from query_service import QueryEngine

engine = QueryEngine()

print("Testing Corrosion Summary Query:")
res_corr = engine.process_query("Tell me about corrosion completed in July 2026", month="July", year=2026)
print(json.dumps(res_corr, indent=2))

print("\nTesting Coaches At Hand Query:")
res_hand = engine.process_query("How many coaches are at hand or active on floor?", month="July", year=2026)
print(json.dumps(res_hand, indent=2))

print("\nTesting Performance / Monthly Outturn Query:")
res_perf = engine.process_query("What is the monthly performance for July 2026?", month="July", year=2026)
print(json.dumps(res_perf, indent=2))

print("\nTesting Type-Wise Holdings Query:")
res_type = engine.process_query("Give me type wise holdings report", month="July", year=2026)
print(json.dumps(res_type, indent=2))
