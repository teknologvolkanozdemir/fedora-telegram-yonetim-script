import unittest
from bot import build_command


class T(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(build_command("install", "vim git")[0], ["dnf", "install", "-y", "vim", "git"])
        self.assertEqual(build_command("upgrade", "41")[0][-2], "--releasever=41")

    def test_invalid(self):
        self.assertIsNone(build_command("install", "vim; rm -rf /"))
        self.assertIsNone(build_command("install", "--best"))
        self.assertIsNone(build_command("upgrade", "x"))
        self.assertIsNone(build_command("foo"))


if __name__ == "__main__":
    unittest.main()
