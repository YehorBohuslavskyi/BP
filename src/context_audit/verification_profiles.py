"""Explicit fresh-run investigation profiles, separate from frozen API budgets."""
from context_audit.direct_verification import Limits

VERSION = 'investigation-limits-v1'
PROFILES = ('baseline', 'rounds', 'context', 'coverage', 'expanded')


def limits_for(profile):
    if profile not in PROFILES:
        raise ValueError('UNKNOWN_LIMIT_PROFILE')
    values = dict(max_candidates=2, max_rounds=3, max_fragments=8,
                  max_source_tokens=8000, max_input_tokens=12000,
                  max_output_tokens=4000, max_total_tokens=200000)
    if profile in ('rounds', 'expanded'):
        values['max_rounds'] = 5
    if profile in ('context', 'expanded'):
        values['max_fragments'] = 12
    if profile in ('coverage', 'expanded'):
        values['max_candidates'] = 6
    if profile == 'expanded':
        values['max_total_tokens'] = 400000
    return Limits(**values)
