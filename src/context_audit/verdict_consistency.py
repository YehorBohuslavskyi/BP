"""Deterministic response consistency, not a Solidity vulnerability detector.

Structured claims bind conclusions to supplied source excerpts. Narrow relational
prose checks catch explicit contradictions; individual words such as 'checked'
never decide an outcome. This cannot prove arbitrary natural-language entailment.
"""
import re
from typing import Literal
from pydantic import Field
from context_audit.direct_discovery import StrictModel
from context_audit.direct_preparation import TOKENS

VERSION = 'verdict-consistency-v4'


class EvidenceClaim(StrictModel):
    fragment_id: str
    source_quote: str = Field(min_length=1)
    role: Literal['dangerous_behavior', 'protection', 'uncertainty', 'context']


class VerdictBasis(StrictModel):
    mechanism_status: Literal['supported', 'contradicted', 'unknown']
    core_conditions: Literal['established', 'not_established', 'unknown']
    mitigation_status: Literal['none_identified', 'effective', 'ineffective', 'unknown']
    mechanism: str = Field(min_length=1)
    mitigation_reason: str
    unresolved_conditions: list[str]
    evidence_claims: list[EvidenceClaim]


def normalized(text):
    return ' '.join(text.split()).casefold()


def code_only(text):
    return TOKENS.sub(lambda m: ' ' if m.group().startswith(('/',)) else m.group(), text)


def source_text(text):
    """Ignore code whitespace/comments, preserving Solidity string contents."""
    text=code_only(text)
    pieces=[]; offset=0
    for token in TOKENS.finditer(text):
        pieces.append(re.sub(r'\s+', ' ', text[offset:token.start()]))
        pieces.append(' ' if token.group().startswith(('/',)) else token.group())
        offset=token.end()
    pieces.append(re.sub(r'\s+', ' ', text[offset:]))
    return ''.join(pieces).strip()


def affirmed(pattern, text):
    for match in re.finditer(pattern, text):
        prefix=text[max(0,match.start()-32):match.start()]
        if re.search(r'\b(?:no|not|never|cannot|can not|fails? to)\s+(?:(?:a|an|any|such|actual)\s+)?$',prefix):
            continue
        if re.search(r'\b(?:not|never|no)\s+(?:\w+\s+){0,2}revert',match.group()):
            continue
        return True
    return False


def prose_signals(explanation, flow):
    """Look for assertions and their polarity/relations, not token blacklists.

    Legacy replay can only check explicit language. New live responses additionally
    require a structured basis and source-bound claims. Negated protections and
    guards followed by a supported residual danger are not blanket contradictions.
    """
    text = normalized(explanation)
    path = normalized(' '.join(flow))
    combined = text + ' ' + path
    denial = bool(re.search(
        r'(?:hypothesis|candidate|suspected (?:mechanism|vulnerability|path)|this vulnerability)'
        r'[^.!?]{0,140}\b(?:not supported|unsupported|prevented|unreachable|does not hold|is absent)\b', combined))
    core_unknown = bool(re.search(
        r'\b(?:cannot|can not|unable to)\s+(?:reliably\s+)?(?:confirm|establish|verify|assess)\b|'
        r'\bdoes not\s+(?:establish|demonstrate|show|prove)\b[^.!?]{0,100}'
        r'\b(?:harmful|dangerous|theft|exploit(?:able|ability)?|unauthorized|invariant (?:break|violation))\b|'
        r'\bcan only confirm\b|\b(?:required|core|necessary|reachability|preconditions?|guard effectiveness)\b[^.!?]{0,90}\b(?:unknown|unresolved|missing)\b', combined))
    # A denied risk ('no dangerous path') is not a positive reachable risk.
    # Explicitly attributed hypotheses describe the proposition being tested,
    # not an asserted reachable path. Stop at a contrast or sentence boundary so
    # an affirmative residual danger in the next clause is still checked.
    danger_text = re.sub(
        r'\b(?:the )?(?:hypothesis|candidate|suspected attack)\s+'
        r'(?:alleges|posits|assumes|is that)\b[^.!?;]*?'
        r'(?=[.!?;]|,?\s+but\b|$)', ' ', combined)
    harmful_path = affirmed(
        r'(?<!no )\breachable dangerous path\b|\bunrestricted\b[^.!?]{0,80}\b(?:path|takeover|access)\b|'
        r'\b(?:allows?|enables?|permits?)\b[^.!?]{0,120}\b(?:attacker|unauthorized|reenter|steal|drain|corrupt|bypass)\b', danger_text)
    operation_risk = affirmed(
        r'\b(?:unchecked|ignored|ignores|without checking|without any local checks|not checked|not validated)\b[^.!?]{0,140}', danger_text)
    danger = harmful_path or operation_risk
    # Explicit relational protection statements. 'checked' in isolation is inert.
    protection = affirmed(
        r'\b(?:prevents?|preventing)\b(?!\s+not\b)[^.!?]{0,120}|'
        r'\b(?:is|are)\s+(?:prevented|unreachable)\b|'
        r'\b(?:checked|validated)\b[^.!?]{0,100}\b(?:failure|false)\b[^.!?]{0,60}\breverts?\b|'
        r'\b(?:requires?|checks?)\b[^.!?]{0,90}\b(?:success|authorization)\b[^.!?]{0,100}\breverts?\b|'
        r'\bauthorization\b[^.!?]{0,30}\b(?:is enforced|prevents|blocks)\b', combined)
    uncertain = core_unknown or bool(re.search(r'\b(?:unknown|uncertain|insufficient|missing|not supplied|not provided|cannot be assessed)\b', text))
    established = affirmed(r'\b(?:vulnerability|hypothesis|mechanism|dangerous behavior)\b[^.!?]{0,40}\b(?:is established|is confirmed|is proven|clearly exists)\b',combined)
    return {'denial': denial, 'core_unknown': core_unknown, 'danger': danger,
            'protection': protection, 'uncertain': uncertain, 'established':established, 'harmful_path':harmful_path}


def check(response, sources, *, historical=False):
    """Return only safe rule codes/IDs, never source or model prose in diagnostics."""
    data = response.model_dump() if hasattr(response, 'model_dump') else response
    verdict = data['verdict']
    basis = data.get('verdict_basis')
    rules = []
    signals = prose_signals(data['explanation'], data['execution_flow'])
    if not data['explanation'].strip():
        rules.append('EMPTY_EXPLANATION')
    if data['action'] == 'final' and 'FORMAT EXAMPLE ONLY' in data['explanation']:
        rules.append('FORMAT_EXAMPLE_IS_NOT_AN_ASSESSMENT')
    if data['action'] != 'final':
        if basis is not None:
            rules.append('CONTEXT_REQUEST_HAS_VERDICT_BASIS')
    elif basis is None and not historical:
        rules.append('MISSING_VERDICT_BASIS')
    elif basis is not None:
        b = VerdictBasis.model_validate(basis)
        # Paraphrases are allowed. Substring membership establishes neither
        # semantic support nor contradiction; structured status/claims and
        # explicit relational contradictions remain independently checked.
        if not b.mechanism.strip():
            rules.append('EMPTY_MECHANISM')
        roles = set()
        for claim in b.evidence_claims:
            if claim.fragment_id not in data['evidence_ids'] or claim.fragment_id not in sources:
                rules.append('CLAIM_EVIDENCE_NOT_SUPPLIED_OR_CITED')
                continue
            # Case-sensitive Solidity excerpts, with whitespace normalization only.
            quote = source_text(claim.source_quote)
            code = source_text(sources[claim.fragment_id])
            if not re.search(r'[A-Za-z_][A-Za-z_0-9]*', quote) or quote not in code:
                rules.append('SOURCE_QUOTE_NOT_SUPPORTED')
            else:
                roles.add(claim.role)
        if verdict == 'confirmed':
            if b.mechanism_status != 'supported': rules.append('CONFIRMATION_MECHANISM_NOT_SUPPORTED')
            if b.core_conditions != 'established': rules.append('CONFIRMATION_CORE_CONDITIONS_UNKNOWN')
            if b.mitigation_status in ('effective', 'unknown'): rules.append('CONFIRMATION_MITIGATION_NOT_RESOLVED')
            if b.unresolved_conditions or data['incomplete_evidence']: rules.append('CONFIRMATION_UNRESOLVED_CONDITIONS')
            if 'dangerous_behavior' not in roles: rules.append('NO_DANGEROUS_SOURCE_CLAIM')
            if b.mitigation_status == 'ineffective' and (not b.mitigation_reason.strip() or 'protection' not in roles):
                rules.append('MITIGATION_BYPASS_NOT_GROUNDED')
        elif verdict == 'rejected':
            if b.mechanism_status != 'contradicted': rules.append('REJECTION_MECHANISM_NOT_CONTRADICTED')
            if b.mitigation_status != 'effective' and b.core_conditions != 'not_established':
                rules.append('REJECTION_HAS_NO_PROTECTION_OR_CONTRADICTION')
            if 'protection' not in roles or not b.mitigation_reason.strip():
                rules.append('NO_PROTECTION_SOURCE_CLAIM')
            if 'dangerous_behavior' in roles or b.unresolved_conditions: rules.append('REJECTION_UNRESOLVED_OR_DANGEROUS_CLAIM')
        else:
            if b.mechanism_status != 'unknown': rules.append('ABSTENTION_CLAIMS_ESTABLISHED_MECHANISM')
            if not any(s.strip() for s in [*b.unresolved_conditions, *data['incomplete_evidence']]): rules.append('ABSTENTION_WITHOUT_UNCERTAINTY')
    if data['action'] == 'final':
        if verdict == 'confirmed':
            if signals['denial']: rules.append('EXPLICIT_HYPOTHESIS_DENIAL')
            if signals['core_unknown']: rules.append('EXPLICIT_CORE_UNCERTAINTY')
            if signals['protection'] and not signals['danger']: rules.append('PROTECTION_WITHOUT_RESIDUAL_DANGER')
            if basis is not None and signals['protection'] and signals['danger'] and basis['mitigation_status'] != 'ineffective':
                rules.append('MIXED_RISK_AND_PROTECTION_UNRESOLVED')
            if historical and not signals['danger']: rules.append('NO_EXPLICIT_DANGEROUS_BEHAVIOR')
        elif verdict == 'rejected':
            if signals['danger']: rules.append('REJECTION_DESCRIBES_DANGEROUS_PATH')
            if signals['core_unknown']: rules.append('REJECTION_WITH_CORE_UNCERTAINTY')
        elif (signals['established'] or
              ((signals['harmful_path'] if basis is not None else signals['danger']) and not signals['uncertain']) or
              (basis is not None and any(c['role']=='dangerous_behavior' for c in basis['evidence_claims']))):
            # In a structured abstention, an ignored return is a source fact,
            # not by itself an established harmful path. Unknown mechanism and
            # explicit unresolved evidence remain mandatory above. An affirmative
            # dangerous source claim still contradicts abstention. Legacy prose
            # checks and confirmed/rejected rules retain their original behavior.
            rules.append('ABSTENTION_ASSERTS_DANGEROUS_PATH')
    return {'version': VERSION, 'mode': 'historical_limited' if historical and basis is None else 'structured',
            'passed': not rules, 'failed_rules': sorted(set(rules)),
            'original_model_verdict': verdict, 'evidence_ids': list(data['evidence_ids'])}
