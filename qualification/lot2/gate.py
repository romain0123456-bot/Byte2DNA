"""Local decision checks only; this module never calls GitHub or merges."""

def merge_gate(head, reviews, checks, required_checks, authorized=False, draft=True,
               mergeable=False, protections=False):
    """Local decision simulation only. Evidence authenticity remains Orca's responsibility."""
    reasons = []
    if not authorized or draft or not mergeable or not protections:
        reasons.append('repository_or_platform_gate')
    valid = [r for r in reviews if r.get('head') == head and r.get('approved') is True
             and r.get('p0') == 0 and r.get('p1') == 0 and r.get('independent') is True
             and r.get('session') and r.get('role') == 'reviewer']
    if any(r.get('head') == head and (r.get('p0', 1) != 0 or r.get('p1', 1) != 0)
           for r in reviews):
        reasons.append('blocking_findings')
    if len({r['session'] for r in valid}) < 2:
        reasons.append('two_independent_exact_head_reviews_required')
    if not required_checks or any(not any(c.get('name') == name and c.get('head') == head
            and c.get('status') == 'SUCCESS' for c in checks) for name in required_checks):
        reasons.append('required_exact_head_ci_missing')
    if any(c.get('name') in required_checks and c.get('head') == head
           and c.get('status') != 'SUCCESS' for c in checks):
        reasons.append('required_check_not_success')
    return {'allowed': not reasons, 'reasons': reasons, 'github_merge': 'NOT_TESTED'}
