"""Retain response accounting before strict local parsing; never log raw output."""
from openai.lib._parsing._responses import parse_response, type_to_text_format_param
from context_audit.v2_errors import exception_metadata, safe_id


def response_format(schema):
    """The installed SDK's exact strict JSON schema, also used for token counting."""
    return {'format': type_to_text_format_param(schema)}


def parse_result(response, schema, *, candidate_id=None):
    result = {'assessment': None, 'status': 'malformed_response', 'usage': {}}
    try:
        usage = response.usage.model_dump() if response.usage else {}
        result['usage'] = usage
        result.update(status=response.status, model=response.model, response_id=response.id)
        if response.status == 'completed':
            parsed = parse_response(text_format=schema, input_tools=None, response=response)
            if parsed.output_parsed is None:
                raise ValueError('No structured assessment')
            result['assessment'] = parsed.output_parsed.model_dump()
    except Exception as exc:
        result.update(status='response_parse_failed', diagnostic={**exception_metadata(exc),
            'processing_stage': 'response_parsing', 'candidate_id': safe_id(candidate_id)})
    return result
