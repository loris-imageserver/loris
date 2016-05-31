class AbstractResolverTest(object):
    def test_is_resolvable(self):
        self.assertTrue(
         self.resolver.is_resolvable(self.identifier)
        )

    def test_is_not_resolvable(self):
        self.assertFalse(
                self.resolver.is_resolvable(self.not_identifier)
        )

    def test_format(self):
        self.assertEqual(
                self.resolver._format_from_ident(self.identifier),
                self.expected_format
        )

    def test_resolve(self):
        expected_resolved = (self.expected_filepath, self.expected_format)
        resolved = self.resolver.resolve(self.identifier)
        self.assertSequenceEqual(resolved, expected_resolved)
