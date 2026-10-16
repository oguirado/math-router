import hashlib, json, os, subprocess, unittest
from common import *


class T0(unittest.TestCase):
    def test_sha256sums(self):
        r = subprocess.run(["sha256sum", "-c", "v1_frozen/SHA256SUMS"], cwd=W, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(r.stdout.strip().split("\n")), 5)

    def test_v1_index_rebuild_identical(self):
        p = os.path.join(W, "out", "v1_index")
        if not os.path.isdir(p):
            self.skipTest("v1 index absent")
        r = subprocess.run(["python3", os.path.join(W, "v1_frozen", "build_index.py"), "--root", REPO, "--out", p, "--vocab",
                            os.path.join(W, "v1_frozen", "vocabulary.json"), "--check"], capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "byte-identical"))


if __name__ == "__main__":
    unittest.main()
