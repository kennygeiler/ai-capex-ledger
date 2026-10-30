import unittest


class PurchaseCommitmentConcepts(unittest.TestCase):
    def test_the_grand_total_is_not_a_purchase_commitment(self):
        from ledger.reference.dimensions import CONCEPTS
        self.assertNotIn("ContractualObligation", CONCEPTS["purchase_commitments"])  # type 71
        self.assertIn("UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount", CONCEPTS["purchase_commitments"])


if __name__ == '__main__':
    unittest.main()
