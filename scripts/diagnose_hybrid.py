import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from rag.hybrid_retriever import get_baseline_retriever, get_hybrid_retriever
from rag.query_router import get_query_router

query = "What components are associated with VehicleControl?"
target_chunk_id = "autosar_hld__v2.0_p08_c34"

router = get_query_router()
routing = router.route(query)
print("=== ROUTING DECISION ===")
print("Query:", query)
print("query_type:", routing.query_type)
print("detected_version:", routing.detected_version)
print("target_entities:", routing.target_entities)
print("target_section_hint:", routing.target_section_hint)
print("target_chunk_type_hint:", routing.target_chunk_type_hint)

baseline = get_baseline_retriever()
hybrid = get_hybrid_retriever()

# Candidate pool investigation
query_vector = hybrid.embedder.embed_query(query)
total_vectors = hybrid.faiss_store.count
candidate_pool_size = min(total_vectors, max(5 * 6, 30))
distances, indices = hybrid.faiss_store.search(query_vector, top_k=candidate_pool_size)

print(f"\nTotal vectors in index: {total_vectors}")
print(f"Hybrid candidate pool size: {candidate_pool_size}")

raw_candidates = []
target_in_candidates = False
target_candidate_dense_rank = None

for i, (dist, idx) in enumerate(zip(distances, indices)):
    meta = hybrid.metadata_store.get_by_faiss_id(idx)
    if meta:
        cid = meta.get("chunk_id")
        raw_candidates.append((dist, meta))
        if cid == target_chunk_id:
            target_in_candidates = True
            target_candidate_dense_rank = i + 1

print(f"Target chunk '{target_chunk_id}' in FAISS search candidates: {target_in_candidates}")
if target_in_candidates:
    print(f"Dense rank in candidate pool: {target_candidate_dense_rank}")

b_chunks = baseline.retrieve_chunks(query, top_k=15)
h_chunks = hybrid.retrieve_chunks(query, top_k=15)

print("\n=== BASELINE TOP 10 ===")
baseline_ranks = {}
for rank, (score, meta) in enumerate(b_chunks, 1):
    cid = meta.get("chunk_id")
    baseline_ranks[cid] = rank
    if rank <= 10:
        p_val = meta.get('page') or 0
        s_val = str(meta.get('section') or '')
        print(f"Rank {rank:2d} | {cid} | ver={meta.get('version')} | p={p_val:2d} | sec={s_val:10s} | dense={score:.4f} | hint={meta.get('entity_hint')}")

print("\n=== HYBRID TOP 10 ===")
hybrid_ranks = {}
for rank, (score, meta) in enumerate(h_chunks, 1):
    cid = meta.get("chunk_id")
    hybrid_ranks[cid] = rank
    scores = meta.get("_scores", {})
    if rank <= 10:
        p_val = meta.get('page') or 0
        s_val = str(meta.get('section') or '')
        print(f"Rank {rank:2d} | {cid} | ver={meta.get('version')} | p={p_val:2d} | sec={s_val:10s} | final={score:.4f} | dense={scores.get('semantic_score')} | ent={scores.get('entity_score')} | sec_s={scores.get('section_score')} | hint={meta.get('entity_hint')}")

print("\n=== TARGET CHUNK COMPARISON ===")
print("Target:", target_chunk_id)
print("Baseline Rank:", baseline_ranks.get(target_chunk_id, "Not in top 15"))
print("Hybrid Rank:  ", hybrid_ranks.get(target_chunk_id, "Not in top 15"))

# Let's inspect target chunk metadata
target_meta = None
for entry in hybrid.metadata_store.entries:
    if entry.get("chunk_id") == target_chunk_id:
        target_meta = entry
        break

if target_meta:
    print("\nTarget Chunk Metadata:")
    print("  document_id:", target_meta.get("document_id"))
    print("  version:    ", target_meta.get("version"))
    print("  page:       ", target_meta.get("page"))
    print("  section:    ", target_meta.get("section"))
    print("  section_title:", target_meta.get("section_title"))
    print("  chunk_type: ", target_meta.get("chunk_type"))
    print("  entity_hint:", target_meta.get("entity_hint"))
    print("  text snippet:", repr(target_meta.get("text", "")[:200]))

# --- SIMULATE FIX FOR LOCAL VARIABLE SHADOWING ---
def simulate_fixed_hybrid(query, top_k=15):
    routing = hybrid._router.route(query)
    effective_version = routing.detected_version
    query_vector = hybrid.embedder.embed_query(query)
    total_vectors = hybrid.faiss_store.count
    candidate_pool_size = min(total_vectors, max(top_k * 6, 30))
    distances, indices = hybrid.faiss_store.search(query_vector, top_k=candidate_pool_size)
    scored_candidates = []
    for dist, idx in zip(distances, indices):
        if idx == -1:
            continue
        meta = hybrid.metadata_store.get_by_faiss_id(idx)
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
        curr_chunk_type = meta.get("chunk_type", "")  # Notice curr_chunk_type instead of chunk_type!
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
            hybrid.w_semantic * semantic_score
            + hybrid.w_entity * entity_score
            + hybrid.w_section * section_score
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
    return [(c["_scores"]["final_score"], c) for c in scored_candidates[:top_k]]

fixed_chunks = simulate_fixed_hybrid(query, top_k=15)
print("\n=== FIXED HYBRID TOP 10 ===")
fixed_ranks = {}
for rank, (score, meta) in enumerate(fixed_chunks, 1):
    cid = meta.get("chunk_id")
    fixed_ranks[cid] = rank
    scores = meta.get("_scores", {})
    if rank <= 10:
        p_val = meta.get('page') or 0
        s_val = str(meta.get('section') or '')
        print(f"Rank {rank:2d} | {cid} | ver={meta.get('version')} | p={p_val:2d} | sec={s_val:10s} | final={score:.4f} | dense={scores.get('semantic_score')} | ent={scores.get('entity_score')} | sec_s={scores.get('section_score')} | hint={meta.get('entity_hint')}")

print("\n=== TARGET CHUNK IN FIXED HYBRID ===")
print("Target:", target_chunk_id)
print("Fixed Hybrid Rank:", fixed_ranks.get(target_chunk_id, "Not in top 15"))
