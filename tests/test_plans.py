import unittest


class ProgramWords(unittest.TestCase):
    def test_a_joint_venture_is_not_guidance(self):
        from ledger.plans import program_words
        self.assertEqual(program_words("a greater than $15 billion joint venture, expected to nearly triple the capital invested once completed"), "joint venture")
        self.assertIsNone(program_words("we expect capital expenditures of $9.5 billion to $10.0 billion in 2025"))
        self.assertEqual(program_words("plans to invest $100 billion through 2029"), "through 2029")


if __name__ == '__main__':
    unittest.main()
