import unittest
from qualification.lot2.gate import merge_gate


class GateContract(unittest.TestCase):
    def setUp(self):
        self.head = 'candidate-sha'
        self.reviews = [dict(head=self.head, role='reviewer', session=str(i),
            independent=True, approved=True, p0=0, p1=0) for i in range(2)]
        self.checks = [dict(head=self.head, name='lot2-qualification', status='SUCCESS')]

    def gate(self, reviews=None, checks=None, **kwargs):
        policy = dict(authorized=True, draft=False, mergeable=True, protections=True)
        policy.update(kwargs)
        return merge_gate(self.head, self.reviews if reviews is None else reviews,
            self.checks if checks is None else checks, ['lot2-qualification'], **policy)

    def test_complete_metadata_only_allows_local_decision(self):
        result = self.gate()
        self.assertTrue(result['allowed'])
        self.assertEqual(result['github_merge'], 'NOT_TESTED')

    def test_changed_head_invalidates_old_reviews_and_checks(self):
        self.head = 'new-candidate-sha'
        result = self.gate()
        self.assertFalse(result['allowed'])
        self.assertIn('required_exact_head_ci_missing', result['reasons'])
        self.assertIn('two_independent_exact_head_reviews_required', result['reasons'])

    def test_pending_failed_and_cancelled_checks_refuse(self):
        for status in ('PENDING', 'FAILURE', 'CANCELLED'):
            with self.subTest(status=status):
                self.assertFalse(self.gate(checks=[dict(self.checks[0], status=status)])['allowed'])

    def test_same_context_and_non_independent_reviews_refuse(self):
        self.assertFalse(self.gate(reviews=[self.reviews[0]] * 2)['allowed'])
        self.assertFalse(self.gate(reviews=[dict(r, independent=False) for r in self.reviews])['allowed'])

    def test_blocking_findings_refuse(self):
        for severity in ('p0', 'p1'):
            reviews = self.reviews + [dict(self.reviews[0], session='blocking', **{severity: 1})]
            result = self.gate(reviews=reviews)
            self.assertFalse(result['allowed'])
            self.assertIn('blocking_findings', result['reasons'])

    def test_draft_or_missing_authorization_and_protections_refuse(self):
        for policy in ({'draft': True}, {'authorized': False}, {'protections': False}):
            self.assertFalse(self.gate(**policy)['allowed'])

    def test_platform_values_require_exact_booleans(self):
        for policy in ({'draft': None}, {'draft': 0}, {'authorized': 'false'},
                       {'protections': 'false'}, {'mergeable': False}):
            result = self.gate(**policy)
            self.assertFalse(result['allowed'])
            self.assertIn('repository_or_platform_gate', result['reasons'])

    def test_malformed_evidence_refuses_without_exception(self):
        for session in ([], 1, ' 1', '', None):
            result = self.gate(reviews=[dict(self.reviews[0], session=session), self.reviews[1]])
            self.assertFalse(result['allowed'])
            self.assertIn('invalid_evidence', result['reasons'])
        self.assertFalse(self.gate(reviews=[dict(r, p0=False) for r in self.reviews])['allowed'])

    def test_missing_role_session_and_wrong_check_name_refuse(self):
        self.assertFalse(self.gate(reviews=[dict(r, role='developer') for r in self.reviews])['allowed'])
        self.assertFalse(self.gate(reviews=[dict(r, session=None) for r in self.reviews])['allowed'])
        result = self.gate(checks=[dict(self.checks[0], name='other')])
        self.assertFalse(result['allowed'])
        self.assertIn('required_exact_head_ci_missing', result['reasons'])

    def test_required_check_type_and_empty_list_refuse(self):
        for names in ('lot2-qualification', [], ['lot2-qualification'] * 2, [['nested']]):
            result = merge_gate(self.head, self.reviews, self.checks, names,
                authorized=True, draft=False, mergeable=True, protections=True)
            self.assertFalse(result['allowed'])

    def test_old_failure_for_same_head_remains_conservatively_blocking(self):
        checks = self.checks + [dict(self.checks[0], status='FAILURE')]
        result = self.gate(checks=checks)
        self.assertFalse(result['allowed'])
        self.assertIn('required_check_not_success', result['reasons'])
