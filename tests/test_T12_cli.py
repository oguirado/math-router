import json, os, subprocess, sys, unittest
from common import *

ROUTER = os.path.join(W, "tools", "route_v2.py")
Q = "irrationality of Catalan's constant"


def run(*args, cwd=None):
    return subprocess.run([sys.executable, "-I", ROUTER] + list(args), capture_output=True, text=True, cwd=cwd)


class T12(unittest.TestCase):
    def test_defaults_equal_explicit_mount(self):
        explicit = run("--q", Q, "--index", os.path.join(W, "out", "index"), "--params", os.path.join(W, "out", "params.json"))
        default = run("--q", Q, cwd=os.path.dirname(W))
        self.assertEqual(explicit.returncode, 0)
        self.assertEqual(default.stdout, explicit.stdout)

    def test_paths_resolves_every_row_to_an_existing_file(self):
        r = run("--q", Q, "--k", "3", "--paths")
        self.assertEqual(r.returncode, 0)
        ans = json.loads(r.stdout)
        self.assertEqual(sorted(ans["files"]), sorted(row[0] for row in ans["r"]))
        for row in ans["r"]:
            path, _, anchor = ans["files"][row[0]].partition("#")
            self.assertEqual(anchor, row[1])
            self.assertTrue(os.path.isfile(os.path.join(W, path)))

    def test_paths_off_by_default(self):
        self.assertNotIn("files", json.loads(run("--q", Q).stdout))

    def test_explicit_index_without_params_keeps_builtin_defaults(self):
        d = run("--q", Q, "--index", os.path.join(W, "out", "index"))
        self.assertEqual(d.returncode, 0)
        self.assertEqual(json.loads(d.stdout)["pr"], "0" * 16)


if __name__ == "__main__":
    unittest.main()
