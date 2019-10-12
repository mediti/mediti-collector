#!/usr/bin/env python3
"""Run precommit checks on the repository."""
import argparse
import os
import pathlib
import re
import subprocess
import sys


def main() -> int:
    """Execute the main routine."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--overwrite",
        help="Overwrites the unformatted source files with the "
        "well-formatted code in place. If not set, "
        "an exception is raised if any of the files do not conform "
        "to the style guide.",
        action='store_true')

    args = parser.parse_args()

    overwrite = bool(args.overwrite)

    repo_root = pathlib.Path(__file__).parent

    if overwrite:
        print('Removing trailing whitespace...')
        for pth in (sorted(
            (repo_root / "mediti_collector").glob("**/*.py")) + sorted(
                (repo_root / "tests").glob("**/*.py"))):
            pth.write_text(
                re.sub(r'[ \t]+$', '', pth.read_text(), flags=re.MULTILINE))

    print("YAPF'ing...")
    if overwrite:
        # yapf: disable
        subprocess.check_call([
            "yapf", "--in-place", "--style=style.yapf", "--recursive",
            "tests", "mediti_collector", "setup.py", "precommit.py"],
            cwd=repo_root.as_posix())
        # yapf: enable
    else:
        # yapf: disable
        subprocess.check_call([
            "yapf", "--diff", "--style=style.yapf", "--recursive",
            "tests", "mediti_collector", "setup.py", "precommit.py"],
            cwd=repo_root.as_posix())
        # yapf: enable

    print("Mypy'ing...")
    subprocess.check_call(["mypy", "--strict", "mediti_collector", "tests"],
                          cwd=repo_root.as_posix())

    print("Isort'ing...")
    # yapf: disable
    isort_files = map(
        str,
        sorted((repo_root / "mediti_collector").glob("**/*.py")) +
        sorted((repo_root / "tests").glob("**/*.py")))
    # yapf: enable

    if overwrite:
        # yapf: disable
        cmd = [
            "isort", "--balanced", "--multi-line", "4", "--line-width", "80",
            "--dont-skip", "__init__.py", "--project", "mediti_collector"
        ]
        # yapf: enable
        cmd.extend(isort_files)
        subprocess.check_call(cmd)
    else:
        # yapf: disable
        cmd = [
            "isort",
            "--check-only",
            "--diff",
            "--balanced",
            "--multi-line", "4",
            "--line-width", "80",
            "--dont-skip", "__init__.py",
            "--project", "mediti_collector"
        ]
        # yapf: enable
        cmd.extend(isort_files)
        subprocess.check_call(cmd)

    print("Pydocstyle'ing...")
    subprocess.check_call(["pydocstyle", "mediti_collector"],
                          cwd=repo_root.as_posix())

    print("Pylint'ing...")
    subprocess.check_call(
        ["pylint", "--rcfile=pylint.rc", "tests", "mediti_collector"],
        cwd=repo_root.as_posix())

    print("Testing...")
    env = os.environ.copy()
    env['ICONTRACT_SLOW'] = 'true'

    # yapf: disable
    subprocess.check_call(
        ["coverage", "run",
         "--source", "mediti_collector",
         "-m", "unittest", "discover", "tests"],
        cwd=repo_root.as_posix(),
        env=env)
    # yapf: enable

    subprocess.check_call(["coverage", "report"])

    print("Doctesting...")
    subprocess.check_call(
        ["python3", "-m", "doctest", (repo_root / "README.rst").as_posix()])

    for pth in sorted((repo_root / "mediti_collector").glob("**/*.py")):
        subprocess.check_call(["python3", "-m", "doctest", pth.as_posix()])

    print("Checking with twine ...")
    subprocess.check_call(["python3", "setup.py", "sdist"],
                          cwd=repo_root.as_posix())

    subprocess.check_call(["twine", "check", "dist/*"],
                          cwd=repo_root.as_posix())

    return 0


if __name__ == "__main__":
    sys.exit(main())
