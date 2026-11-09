import unittest

from scripts import project_version


class ProjectVersionTest(unittest.TestCase):
    def test_release_metadata_versions_match(self):
        found = project_version.versions()
        self.assertEqual(len(set(found.values())), 1, found)


if __name__ == "__main__":
    unittest.main()
