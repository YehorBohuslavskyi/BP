"""Isolated verification worker; model and compiler configuration belong to this process."""
import json
import os
from pathlib import Path
import sys

from openai import OpenAIError

from context_audit.cgt_inference import estimated_tokens
from context_audit.classification_metrics import context_efficiency
from context_audit.findings import Finding
from context_audit.verifier import prepare_finding, summarize_verification, verify_prepared_finding


def verify_request(request: dict) -> dict:
    """Resolve one target, run the core verifier, and expose evidence and efficiency."""
    source = Path(request['source'])
    finding = Finding(**request['finding'])
    payload, catalog = prepare_finding(source, source.parent, finding)
    result = verify_prepared_finding(finding, payload, catalog, request['max_rounds'])
    summary = summarize_verification(result)
    efficiency = context_efficiency(
        estimated_tokens(source.read_text()), estimated_tokens(payload['target']['source']),
        estimated_tokens(json.dumps(payload)), summary['input_tokens'],
    )
    return {'result': result, 'summary': summary, 'initial_payload': payload,
            'model': os.environ.get('OPENAI_MODEL'), 'compiler': os.environ.get('SOLC_VERSION'),
            'context_efficiency': efficiency,
            'source_bytes': source.stat().st_size,
            'estimate_method': 'ceil(characters / 4); source sizes are estimates, API usage is reported by the provider'}


def main() -> int:
    """Read one JSON job from stdin and return a safe JSON result on stdout."""
    try:
        result = verify_request(json.load(sys.stdin))
    except OpenAIError as error:
        # Raw provider exceptions can contain request data; do not expose them.
        result = {'error': f'OpenAI request failed ({type(error).__name__}). Check network access, credentials, and model availability. No automatic retry was made.'}
    except Exception as error:
        result = {'error': f'Verification failed ({type(error).__name__}) during source resolution or response/context validation.'}
    print(json.dumps(result))
    return int('error' in result)


if __name__ == '__main__':
    raise SystemExit(main())
