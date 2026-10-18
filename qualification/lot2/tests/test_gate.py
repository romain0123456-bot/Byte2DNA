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
            reviews = [dict(self.reviews[0], **{severity: 1}), self.reviews[1]]
            self.assertFalse(self.gate(reviews=reviews)['allowed'])

    def test_draft_or_missing_authorization_and_protections_refuse(self):
        for policy in ({'draft': True}, {'authorized': False}, {'protections': False}):
            self.assertFalse(self.gate(**policy)['allowed'])
