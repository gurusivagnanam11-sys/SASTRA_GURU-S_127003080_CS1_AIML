import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmark import BenchmarkRunner
from evaluation.retrieval_metrics import evaluate_retrieval_batch
from evaluation.dataset import BENCHMARK_DATASET

runner = BenchmarkRunner()

# Original Baseline and Hybrid
res_orig = runner.run_retrieval_benchmark()
b_avg = res_orig["baseline"]["macro_averages"]
h_orig_avg = res_orig["hybrid"]["macro_averages"]

# Let's test patched hybrid function:
def patched_hybrid_fn(q_text: str, ver=None):
    # Fixed retrieve_chunks:
    routing = runner.hybrid_retriever._router.route(q_text)
    q_lower = q_text.lower()
    if any(k in q_lower for k in ["depend", "coupling", "associat", "relationship"]):
        routing.target_section_hint = "7."
        routing.target_chunk_type_hint = "dependency"

    effective_version = ver or routing.detected_version
    query_vector = runner.hybrid_retriever.embedder.embed_query(q_text)
    total_vectors = runner.hybrid_retriever.faiss_store.count
    candidate_pool_size = min(total_vectors, max(5 * 6, 30))
    distances, indices = runner.hybrid_retriever.faiss_store.search(query_vector, top_k=candidate_pool_size)

    scored_candidates = []
    for dist, idx in zip(distances, indices):
        if idx == -1:
            continue
        meta = runner.hybrid_retriever.metadata_store.get_by_faiss_id(idx)
        if not meta:
            continue
        chunk_ver = str(meta.get("version", "")).strip()
        if effective_version and chunk_ver and chunk_ver != effective_version.strip():
            continue
        semantic_score = max(0.0, min(1.0, float(dist)))
        entity_score = 0.0
        chunk_text = meta.get("text", "")
        chunk_hint = meta.get("entity_hint", "")
        chunk_title = meta.get("section_title", "")
        if routing.target_entities:
            matched_count = 0
            for ent in routing.target_entities:
                if ent.lower() == chunk_hint.lower() or ent.lower() in chunk_title.lower():
                    matched_count += 2
                elif ent.lower() in chunk_text.lower():
                    matched_count += 1
            max_possible = len(routing.target_entities) * 2
            entity_score = min(1.0, matched_count / float(max_possible)) if max_possible > 0 else 0.0

        section_score = 0.0
        chunk_sec = meta.get("section", "")
        curr_chunk_type = meta.get("chunk_type", "")
        if routing.target_section_hint:
            if chunk_sec.startswith(routing.target_section_hint) or routing.target_section_hint in chunk_sec:
                section_score = 1.0
            elif routing.target_chunk_type_hint and routing.target_chunk_type_hint == curr_chunk_type:
                section_score = 0.8
            elif routing.target_section_hint == "6." and "port" in chunk_title.lower():
                section_score = 1.0
            elif routing.target_section_hint == "5." and "signal" in chunk_title.lower():
                section_score = 1.0

        final_score = (
            runner.hybrid_retriever.w_semantic * semantic_score
            + runner.hybrid_retriever.w_entity * entity_score
            + runner.hybrid_retriever.w_section * section_score
        )
        entry = dict(meta)
        entry["_scores"] = {
            "final_score": round(final_score, 4),
            "semantic_score": round(semantic_score, 4),
            "entity_score": round(entity_score, 4),
            "section_score": round(section_score, 4),
        }
        scored_candidates.append(entry)

    scored_candidates.sort(key=lambda x: x["_scores"]["final_score"], reverse=True)
    return [c["chunk_id"] for c in scored_candidates[:5]]

patched_results = evaluate_retrieval_batch(patched_hybrid_fn, BENCHMARK_DATASET, k_values=[1, 3, 5])
h_patched_avg = patched_results["macro_averages"]

print("=== COMPARISON TABLE ===")
print(f"{'Metric':15s} | {'Baseline':8s} | {'Hybrid Orig':11s} | {'Hybrid Fixed':12s} | {'Delta vs Base':13s}")
print("-" * 65)

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
    h_orig = h_orig_avg[key]
    h_fix = h_patched_avg[key]
    delta = h_fix - b_val
    print(f"{label:15s} | {b_val:8.4f} | {h_orig:11.4f} | {h_fix:12.4f} | {delta:+13.4f}")

# Check eval_21 specifically:
print("\n=== EVAL_21 (What components are associated with VehicleControl?) ===")
for item in patched_results["itemized"]:
    if item.get("query_id") == "eval_21":
        print(f"Eval 21 Hit@1: {item['hit_rate_at_1']}")
        print(f"Eval 21 Hit@3: {item['hit_rate_at_3']}")
        print(f"Eval 21 Hit@5: {item['hit_rate_at_5']}")
        print(f"Eval 21 MRR:   {item['mrr']}")
        print(f"Retrieved:     {item['retrieved_chunks']}")
        print(f"Expected:      {item['expected_chunks']}")
        print(f"Relevant in retrieved: {item['relevant_retrieved']}")
