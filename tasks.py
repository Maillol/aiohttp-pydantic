"""
To use this module, install invoke and type invoke -l
"""

from functools import partial
import os
from pathlib import Path
import setuptools.config
from invoke import task, Exit, Task as Task_, call


def read_configuration(conf_file) -> dict:
    try:  # Setuptools >= 61
        return setuptools.config.setupcfg.read_configuration(conf_file)
    except Exception:
        return setuptools.config.read_configuration(conf_file)


def activate_venv(c, venv: str):
    """
    Activate a virtualenv
    """
    virtual_env = Path().absolute() / venv
    if original_path := os.environ.get("PATH"):
        path = f'{virtual_env / "bin"}:{original_path}'
    else:
        path = str(virtual_env / "bin")
    c.config.run.env["PATH"] = path
    c.config.run.env["VIRTUAL_ENV"] = str(virtual_env)
    os.environ.pop("PYTHONHOME", "")


def title(text, underline_char="#"):
    """
    Display text as a title.
    """
    template = f"{{:{underline_char}^80}}"
    text = template.format(f" {text.strip()} ")
    print(f"\033[1m{text}\033[0m")


class Task(Task_):
    """
    This task add 'skip_if_recent' feature.

    >>> @task(skip_if_recent=['./target', './dependency'])
    >>> def my_tash(c):
    >>>    ...

    target is file created by the task
    dependency is file used by the task

    The task is ran only if the dependency is more recent than the target file.
    The target or the dependency can be a tuple of files.
    """

    def __init__(self, *args, **kwargs):
        self.skip_if_recent = kwargs.pop("skip_if_recent", None)
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        title(self.__doc__ or self.name)

        if self.skip_if_recent:
            targets, dependencies = self.skip_if_recent
            if isinstance(targets, str):
                targets = (targets,)
            if isinstance(dependencies, str):
                dependencies = (dependencies,)

            target_mtime = min(
                ((Path(file).exists() and Path(file).lstat().st_mtime) or 0)
                for file in targets
            )
            dependency_mtime = max(Path(file).lstat().st_mtime for file in dependencies)

            if dependency_mtime < target_mtime:
                print(f"{self.name}, nothing to do")
                return None

        return super().__call__(*args, **kwargs)


task = partial(task, klass=Task)


@task()
def venv(c):
    """
    Create a virtual environment for dev
    """
    c.run("python -m venv --clear venv")
    c.run("venv/bin/pip install -U setuptools wheel pip")
    c.run("venv/bin/pip install -e .")
    c.run("venv/bin/pip install -r requirements/test.txt")


@task()
def check_readme(c):
    """
    Check the README.rst render
    """
    c.run("python -m readme_renderer -o /dev/null README.rst")


@task()
def test(c, isolate=False):
    """
    Launch tests
    """
    opt = "I" if isolate else ""
    c.run(f"python -{opt}m pytest --cov-report=xml --cov=aiohttp_pydantic tests/")


@task()
def tag_eq_version(c):
    """
    Ensure that the last git tag matches the package version
    """
    git_tag = c.run("git describe --tags HEAD", hide=True).stdout.strip()
    package_version = read_configuration("./setup.cfg")["metadata"]["version"]
    if git_tag != f"v{package_version}":
        raise Exit(
            f"ERROR: The git tag {git_tag!r} does not matches"
            f" the package version {package_version!r}"
        )


@task()
def prepare_ci_env(c):
    """
    Prepare CI environment
    """
    title("Creating virtual env", "=")
    c.run("python -m venv --clear dist_venv")
    activate_venv(c, "dist_venv")

    c.run("dist_venv/bin/python -m pip install -U setuptools wheel pip build")

    title("Building wheel", "=")
    c.run("dist_venv/bin/python -m build --wheel")

    title("Installing wheel", "=")
    package_version = read_configuration("./setup.cfg")["metadata"]["version"]
    dist = next(Path("dist").glob(f"aiohttp_pydantic-{package_version}-*.whl"))
    c.run(f"dist_venv/bin/python -m pip install {dist}")

    # We verify that aiohttp-pydantic module is importable before installing CI tools.
    package_names = read_configuration("./setup.cfg")["options"]["packages"]
    for package_name in package_names:
        c.run(f"dist_venv/bin/python -I -c 'import {package_name}'")

    title("Installing CI tools", "=")
    c.run("dist_venv/bin/python -m pip install .[ci]")


@task(prepare_ci_env, check_readme, call(test, isolate=True), klass=Task_)
def prepare_upload(c):
    """
    Launch all tests and verifications
    """


@task(tag_eq_version, prepare_upload)
def upload(c, pypi_user=None, pypi_password=None):
    """
    Upload on pypi
    """
    package_version = read_configuration("./setup.cfg")["metadata"]["version"]
    dist = next(Path("dist").glob(f"aiohttp_pydantic-{package_version}-*.whl"))
    if pypi_user is not None and pypi_password is not None:
        c.run(
            f"dist_venv/bin/twine upload --non-interactive"
            f" -u {pypi_user} -p {pypi_password} {dist}",
            hide=True,
        )
    else:
        c.run(f"dist_venv/bin/twine upload --repository aiohttp-pydantic {dist}")
