import os
import pathlib
from unittest import mock

import pytest

from fromager import overrides


def test_patches_for_source_dir(tmp_path: pathlib.Path):
    patches_dir = tmp_path / "patches"
    patches_dir.mkdir()

    project_patch_dir = patches_dir / "project-1.2.3"
    project_patch_dir.mkdir()

    project_variant_patch_dir = patches_dir / "project-1.2.3-variant"
    project_variant_patch_dir.mkdir()

    # legacy form
    p1 = patches_dir / "project-1.2.3-001.patch"
    np1 = patches_dir / "project-1.2.3.txt"
    p2 = patches_dir / "project-1.2.3-variant-002.patch"

    # new form with project dir
    p3 = project_patch_dir / "003.patch"
    p4 = project_patch_dir / "004.patch"
    np2 = project_patch_dir / "not-a-patch.txt"
    p5 = project_variant_patch_dir / "005.patch"
    np3 = project_variant_patch_dir / "not-a-patch.txt"

    # Create all of the test files
    for p in [p1, p2, p3, p4, p5]:
        p.write_text("this is a patch file")
    for f in [np1, np2, np3]:
        f.write_text("this is not a patch file")

    results = list(overrides.patches_for_source_dir(patches_dir, "project-1.2.3"))
    assert results == [p1, p2, p3, p4]

    results = list(
        overrides.patches_for_source_dir(patches_dir, "project-1.2.3-variant")
    )
    assert results == [p2, p5]


def test_extra_environ_for_pkg(tmp_path: pathlib.Path):
    env_dir = tmp_path / "env"
    env_dir.mkdir()

    variant_dir = env_dir / "variant"
    variant_dir.mkdir()

    project_env = variant_dir / "project.env"
    project_env.write_text("VAR1=VALUE1\nVAR2=VALUE2")

    result = overrides.extra_environ_for_pkg(env_dir, "project", "variant")
    assert result == {"VAR1": "VALUE1", "VAR2": "VALUE2"}

    result = overrides.extra_environ_for_pkg(env_dir, "non_existant_project", "variant")
    assert result == {}


def test_extra_environ_for_pkg_expansion(tmp_path: pathlib.Path):
    variant = "cpu"
    pkg_name = "another-shrubbery"
    env_file = tmp_path / variant / "another_shrubbery.env"
    env_file.parent.mkdir(parents=True)

    # good case
    with env_file.open("w", encoding="utf=8") as f:
        f.write("EGG = Python\n")
        f.write("SPAM=Monty ${EGG}!\n")
        f.write("KNIGHT=$NAME\n")

    with mock.patch.dict(os.environ) as environ:
        environ.clear()
        environ["NAME"] = "Ni"
        extra_environ = overrides.extra_environ_for_pkg(tmp_path, pkg_name, variant)

    assert extra_environ == {"EGG": "Python", "SPAM": "Monty Python!", "KNIGHT": "Ni"}

    # unknown key
    with env_file.open("w", encoding="utf=8") as f:
        f.write("EGG=${UNKNOWN_NAME}\n")

    with mock.patch.dict(os.environ) as environ:
        environ.clear()
        environ["NAME"] = "Ni"
        with pytest.raises(KeyError):
            extra_environ = overrides.extra_environ_for_pkg(tmp_path, pkg_name, variant)

    # unsupported
    with env_file.open("w", encoding="utf=8") as f:
        f.write("SPAM=$(ls)\n")

    with pytest.raises(ValueError):
        extra_environ = overrides.extra_environ_for_pkg(tmp_path, pkg_name, variant)
