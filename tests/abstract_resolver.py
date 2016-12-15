from loris import loris_exception


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
                self.resolver.format_from_ident(self.identifier),
                self.expected_format
        )

    def test_resolve(self):
        expected_resolved = (self.expected_filepath, self.expected_format)
        resolved = self.resolver.resolve(self.identifier)
        self.assertEqual(resolved[0], expected_resolved[0])
        self.assertEqual(resolved[1], expected_resolved[1])

    def test_resolve_exception(self):
        self.assertRaises(loris_exception.ResolverException, lambda: self.resolver.resolve(self.not_identifier))
