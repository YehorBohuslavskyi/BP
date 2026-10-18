"""Prepare every reviewed CGT context and estimate costs WITHOUT API calls."""
import argparse
import json
import os
import re
from pathlib import Path

from check_cgt import write_csv, write_json
from context_audit.cgt_dataset import load_cgt
from context_audit.cgt_findings import load_reviewed_findings, sha256
from context_audit.cgt_inference import BlindAnalyzer, estimated_tokens, strip_comments
from context_audit.cgt_sample import choose_sample
from context_audit.indexer import find_function
from context_audit.llm import SYSTEM_PROMPT, AuditResponse
from context_audit.verifier import prepare_finding
from slither.slither import Slither

ROOT = Path(__file__).resolve().parent


def normalized_source(source: str) -> tuple[str, ...]:
    # Preserve spaces inside string literals: only tokenize whitespace outside
    # literals so differently worded messages cannot be declared identical.
    text = strip_comments(source)
    return tuple(re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|\w+|[^\s]', text))


def estimate_cohort(rows: list[dict]) -> dict:
    return {"findings": len(rows), "positive": sum(r['label'] for r in rows),
            "negative": sum(not r['label'] for r in rows),
            "api_calls_min": len(rows), "api_calls_max": 4 * len(rows),
            "first_round_input_tokens_estimate": sum(r['initial_request_estimate'] for r in rows),
            "four_round_input_tokens_estimate_upper": sum(4*r['all_context_request_estimate'] for r in rows),
            "output_tokens_configured_cap": 16000 * len(rows)}


def run(root: Path, manifest: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    candidates, errors = load_reviewed_findings(load_cgt(root), manifest)
    if errors:
        raise ValueError(f'Review manifest validation failed: {errors}')
    reviews = {r['review_id']:r for r in json.loads(manifest.read_text())}
    records = []
    compiler_before = os.environ.get('SOLC_VERSION')
    overhead = SYSTEM_PROMPT + json.dumps(AuditResponse.model_json_schema())
    try:
        for candidate in candidates:
            os.environ['SOLC_VERSION'] = candidate.compiler_version
            row = {"review_id": candidate.review_id, "label": candidate.label, "status": "error"}
            try:
                source = candidate.assessment.source_path
                payload, catalog = prepare_finding(source, source.parent, candidate.finding)
                # Verify the source's actual function body against the original
                # dataset, since archived byte offsets refer to reordered files.
                review = reviews[candidate.review_id]
                stem = re.search(r'-(test\d+)-', candidate.review_id).group(1)
                original = root/'construction/originalSets/Doublade/source_code'/f'{stem}.sol'
                original_slither = Slither(str(original))
                function = find_function(original_slither, candidate.finding.contract,
                                         candidate.finding.function_signature)
                if function is None or normalized_source(function.source_mapping.content) != normalized_source(payload['target']['source']):
                    raise ValueError('Original versus consolidated function differs; review required')
                # This adapter is used only for transformation. No analyze_fn is callable.
                adapter = BlindAnalyzer(payload, None)
                initial, _ = adapter.payload(payload, [])
                full, fragments = adapter.payload(payload, [catalog.get(x['id']) for x in payload['available_context']])
                body = json.dumps({**initial,'provided_context':[]},ensure_ascii=False)
                complete = json.dumps({**full,'provided_context':fragments},ensure_ascii=False)
                row.update(status='ready', original_function_equivalent=True,
                           original_source_sha256=sha256(original), source_sha256=sha256(source),
                           initial_request_estimate=estimated_tokens(overhead+body),
                           all_context_request_estimate=estimated_tokens(overhead+complete),
                           initial_payload_estimate=estimated_tokens(body),
                           full_source_estimate=estimated_tokens(strip_comments(source.read_text())),
                           available_fragments=len(fragments), source_bytes=source.stat().st_size,
                           source_LOC=len(source.read_text().splitlines()))
                write_json(out/(candidate.review_id+'.payload.json'),initial)
            except Exception as error:
                row['error'] = str(error)
            records.append(row)
            print(candidate.review_id,row['status'],flush=True)
    finally:
        if compiler_before is None:
            os.environ.pop('SOLC_VERSION',None)
        else:
            os.environ['SOLC_VERSION']=compiler_before
    ready = [r for r in records if r['status']=='ready']
    # Freeze pilot before any inference: deterministic balanced 5+5 if available.
    pilot_ids = [c.review_id for c in choose_sample([c for c in candidates if c.review_id in {r['review_id'] for r in ready}],10)]
    pilot = [r for r in ready if r['review_id'] in pilot_ids]
    summary = {"api_calls_made":0,"actual_api_usage":None,"reviewed_candidates":len(candidates),
               "ready":len(ready),"preflight_failures":len(records)-len(ready),
               "estimation_method":"ceil(characters/4), includes prompt and schema; not model tokenizer or billed usage",
               "model":None,"pricing_estimate":None,
               "pilot_ids":pilot_ids,"pilot":estimate_cohort(pilot),"full_cohort":estimate_cohort(ready),
               "sample_policy":"alternate labels, round-robin detector families, sorted review IDs",
               "sample_selector_sha256":sha256(ROOT/"src/context_audit/cgt_sample.py"),
               "manifest_sha256":sha256(manifest),"preflight_sha256":sha256(Path(__file__)),
               "approval_required":"User explicitly requested a checkpoint before ANY paid LLM run"}
    write_json(out/'summary.json',summary)
    write_json(out/'findings.json',records)
    write_json(out/'errors.json',[r for r in records if r['status']!='ready'])
    write_csv(out/'findings.csv',records,['review_id','label','status','initial_request_estimate',
                                       'all_context_request_estimate','full_source_estimate','available_fragments',
                                       'original_function_equivalent','error'])
    print(json.dumps(summary,indent=2))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset-root',type=Path,default=ROOT/'datasets/cgt')
    p.add_argument('--review-manifest',type=Path,default=ROOT/'results/cgt_reviewed_baseline/reviews.json')
    p.add_argument('--output-dir',type=Path,default=ROOT/'results/cgt_preflight')
    args=p.parse_args()
    result=run(args.dataset_root.resolve(),args.review_manifest.resolve(),args.output_dir.resolve())
    raise SystemExit(bool(result['preflight_failures']))
