"""Allowlisted diagnostic metadata; never exception messages, bodies or headers."""
import hashlib
import re
from pydantic import ValidationError
from openai import APITimeoutError, APIConnectionError, APIResponseValidationError


# Only application-owned constant messages are translated; arbitrary messages and
# validation input/context are never emitted. Field names are allowlisted too.
PROTOCOL_RULES = {
    'Value error, Duplicate context IDs': 'duplicate_context_ids',
    'Value error, Invalid request_context response': 'invalid_context_request',
    'Value error, Invalid final response': 'invalid_final_response',
    'Value error, A decisive verdict requires supplied source evidence': 'decisive_verdict_without_evidence',
    'Value error, Severity requires confirmation': 'severity_without_confirmation',
    'Value error, Unresolved evidence requires abstention': 'confirmation_with_missing_evidence',
}
VALIDATION_FIELDS = frozenset(('action', 'requested_ids', 'verdict', 'severity', 'explanation',
    'evidence_ids', 'execution_flow', 'incomplete_evidence', 'verdict_basis', 'mechanism_status',
    'core_conditions', 'mitigation_status', 'mechanism', 'mitigation_reason', 'unresolved_conditions',
    'evidence_claims', 'fragment_id', 'source_quote', 'role'))
VALIDATION_TYPES = frozenset(('value_error', 'json_invalid', 'literal_error', 'missing',
    'extra_forbidden', 'list_type', 'string_type', 'string_too_short', 'model_type', 'dict_type'))

# Exact application-owned constants only. A generic ValueError can also be a
# local preflight failure; it is not evidence that a model returned bad output.
# Never copy arbitrary exception messages into diagnostics.
LOCAL_FAILURES = {
    'IMPLEMENTATION_CHANGED': ('configuration_mismatch', 'case_preflight', 'validate_implementation'),
    'MODEL_OR_CREDENTIAL_MISSING': ('configuration_missing_or_mismatch', 'case_preflight', 'validate_model_and_credential'),
    'MODEL_MISMATCH': ('configuration_mismatch', 'case_preflight', 'validate_model'),
    'CREDENTIAL_MISSING': ('authentication_configuration_missing', 'case_preflight', 'validate_credential_presence'),
    'OFFICIAL_ENDPOINT_REQUIRED': ('configuration_mismatch', 'case_preflight', 'validate_endpoint'),
    'SOURCE_COMPILER_CATALOG_MISMATCH': ('provenance_mismatch', 'source_preflight', 'validate_source_identity'),
    'COMPILER_BINARY_CHANGED': ('provenance_mismatch', 'source_preflight', 'validate_compiler_binary'),
    'RECOVERY_HASH_MISMATCH': ('provenance_mismatch', 'source_preflight', 'validate_recovery_hash'),
    'RECOVERY_IMPORT_MISMATCH': ('provenance_mismatch', 'source_preflight', 'validate_recovery_import'),
    'RESUME_MANIFEST_MISMATCH': ('provenance_mismatch', 'resume_preflight', 'validate_run_manifest'),
}


def validation_details(exc):
    errors = exc.errors(include_input=False, include_context=False, include_url=False)
    return [{'type': e['type'] if e['type'] in VALIDATION_TYPES else 'other_validation_error',
             'location': [x if type(x) is int or x in VALIDATION_FIELDS else '<field>' for x in e['loc']],
             'rule': PROTOCOL_RULES.get(e['msg'], 'schema_validation')}
            for e in errors[:20]]


def safe_id(value):
    if value is None:
        return None
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
        return value
    return 'id-sha256-' + hashlib.sha256(str(value).encode()).hexdigest()[:20]


class DiagnosticFailure(RuntimeError):
    def __init__(self, code, diagnostic=None):
        super().__init__(code)
        self.diagnostic = diagnostic


def exception_metadata(exc):
    if isinstance(exc, DiagnosticFailure) and exc.diagnostic is not None:
        return dict(exc.diagnostic)
    details = {'exception_type': type(exc).__name__, 'interrupted': isinstance(exc, KeyboardInterrupt)}
    if type(exc) is ValueError and len(exc.args) == 1 and isinstance(exc.args[0], str) and exc.args[0] in LOCAL_FAILURES:
        category, stage, operation = LOCAL_FAILURES[exc.args[0]]
        return {**details, 'category': category, 'processing_stage': stage,
                'operation': operation, 'error_code': exc.args[0]}
    status = getattr(exc, 'status_code', None)
    if type(status) is int and 100 <= status <= 599:
        details['http_status'] = status
    else:
        status = None
    code = getattr(exc, 'code', None)
    if isinstance(exc, KeyboardInterrupt): category = 'interrupted'
    elif isinstance(exc, APITimeoutError): category = 'timeout'
    elif isinstance(exc, APIConnectionError): category = 'connection_failure'
    elif code in ('unsupported_parameter', 'unsupported_value'): category = 'unsupported_model_parameter'
    elif status == 401: category = 'authentication_failure'
    elif status == 429: category = 'rate_limit'
    elif status is not None and status >= 500: category = 'provider_server_error'
    elif status is not None and 400 <= status < 500: category = 'invalid_request'
    elif isinstance(exc, (ValidationError, APIResponseValidationError)): category = 'response_validation'
    elif isinstance(exc, (ValueError, TypeError, AttributeError, KeyError)): category = 'malformed_response_or_protocol'
    else: category = 'runtime_error'
    details['category'] = category
    if isinstance(exc, ValidationError):
        details['validation_error_count'] = exc.error_count()
        details['validation_errors'] = validation_details(exc)
    return details
