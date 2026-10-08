import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmark import BenchmarkRunner

runner = BenchmarkRunner()
results = runner.run_retrieval_benchmark()
b_avg = results["baseline"]["macro_averages"]
h_avg = results["hybrid"]["macro_averages"]

print("=== RETRIEVAL BENCHMARK RESULTS ===")
print(f"{'Metric':15s} | {'Baseline':8s} | {'Hybrid':8s} | {'Delta':8s}")
print("-" * 47)
metrics = [
    ("mrr", "MRR"),
    ("ndcg_at_5", "nDCG@5"),
    ("hit_rate_at_1", "Hit@1"),
    ("hit_rate_at_3", "Hit@3"),
    ("hit_rate_at_5", "Hit@5"),
    ("precision_at_1", "Precision@1"),
    ("recall_at_5", "Recall@5"),
]

for key, label in metrics:
    b_val = b_avg[key]
    h_val = h_avg[key]
    delta = h_val - b_val
    print(f"{label:15s} | {b_val:8.4f} | {h_val:8.4f} | {delta:+8.4f}")

print("\n=== CATEGORY BREAKDOWN ===")
for cat, data in results["category_breakdown"].items():
    print(f"  {cat:20s}: Baseline MRR={data['baseline_mrr']:.4f}, Hybrid MRR={data['hybrid_mrr']:.4f}")
