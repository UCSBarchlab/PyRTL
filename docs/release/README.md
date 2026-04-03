# PyRTL release process documentation

See [Packaging Python
Projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
for an overview of Python packaging. PyRTL's `pyproject.toml` configuration is
based on this tutorial.

See [Publishing package distribution releases using GitHub
Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
for an overview of distributing Python packages with GitHub Actions. PyRTL's
`python-release.yml` configuration is based on this tutorial.

## PyRTL versioning

PyRTL uses [semantic versioning](https://semver.org/). All version numbers are
of the form `MAJOR.MINOR.PATCH`, with an optional `rcN` suffix for release
candidates, starting from `rc0`. Valid examples include `0.11.1` and
`0.11.0rc0`. Never reuse a version number.

Releases with a `rc` suffix are Release Candidates. Use release candidates for
pre-releases, and to test the release process. `pip` will not install release
candidates by default. Use:
```shell
$ pip install --pre pyrtl
```
to install the latest release candidate.

The rest of this document assumes that the new PyRTL version number is
`$NEW_VERSION`.

See [PEP 440](https://peps.python.org/pep-0440/) for more details on version
numbers.

## Building a new release

1. Clone the PyRTL repository:
   ```shell
   $ git clone git@github.com:UCSBarchlab/PyRTL.git pyrtl
   $ cd pyrtl
   ```
2. Tag the new version:
   ```shell
   $ git tag $NEW_VERSION
   ```
3. Push this change to GitHub. Tags are not pushed by default, so use:
   ```shell
   $ git push origin $NEW_VERSION
   ```

The `python-release.yml` GitHub workflow should detect the new tag, build a new
release, and upload the new release to TestPyPI. Check workflow status at
https://github.com/UCSBarchlab/PyRTL/actions

### Testing a new TestPyPI release

Check the [TestPyPI release
history](https://test.pypi.org/project/pyrtl/#history). You should see your
`$NEW_VERSION` at the top of the page.

Test this TestPyPI release by creating a new Python virtual environment
(`venv`):
```shell
$ python3 -m venv pyrtl-release-test
$ . pyrtl-release-test/bin/activate
```

Then install and test the new release from TestPyPI:
```shell
$ pip install --index-url https://test.pypi.org/simple/ --no-deps pyrtl
```
If you created a `rc` release candidate, don't forget to add the `--pre` flag:
```shell
$ pip install --index-url https://test.pypi.org/simple/ --no-deps --pre pyrtl
```

### Deploying a new PyPI release

If the new release looks good, approve the 'Publish distribution archives on
PyPI' workflow on GitHub to deploy the new release to PyPI.

### Testing a new PyPI release

Check the [PyPI release history](https://pypi.org/project/pyrtl/#history). You
should see your `$NEW_VERSION` at the top of the page.

Test this PyPI release by installing and testing the new release from PyPI:
```shell
$ pip install pyrtl
```
If you created a `rc` release candidate, don't forget to add the `--pre` flag:
```shell
$ pip install --pre pyrtl
```

## Read the Docs Versioning

Read the Docs builds documentation for each PyRTL release. Available versions
can be seen on [PyRTL's
dashboard](https://readthedocs.org/projects/pyrtl/versions/), or in the bottom
right [flyout
menu](https://docs.readthedocs.io/en/stable/glossary.html#term-flyout-menu) on
each documentation page.

After building a new release, check the new release's documentation on [PyRTL's
Read the Docs dashboard](https://readthedocs.org/projects/pyrtl/versions/).

Versioned documentation builds are triggered by the creation of git tags, and
versions for new releases are automatically activated by the Read the Docs
"Activate new version" [automation
rule](https://docs.readthedocs.io/en/stable/automation-rules.html). The "Hide
release candidates" automation rule hides release candidates from the bottom
right flyout menu.

After a full release (not a release candidate), deactivate the documentation
for any corresponding release candidates on the dashboard.

## Manually building and publishing a new release

The following manual steps should be automated by
`.github/workflows/python-release.yml`. Manual release instructions are
provided below in case a release needs to be built without GitHub workflow
automation. If the automation is working, you shouldn't need to run these
commands.

### Manual build

Build distribution archive:

```shell
$ uv build
```

This produces two files in `dist/`: a `.whl` file and a `.tar.gz` file.

### Manual publish on TestPyPI

1. If necessary, create a TestPyPI API token, by going to
   https://test.pypi.org/manage/account/ and clicking 'Add API token'.
2. Upload distribution archive to TestPyPI:
   ```shell
   $ uv run --with twine twine upload --repository testpypi dist/*
   ```
3. Enter your API token when prompted.
4. Check the new release's status at https://test.pypi.org/project/pyrtl/#history
5. Install and test the new release from TestPyPI by following the [Testing a
   new TestPyPI release](#testing-a-new-testpypi-release) instructions above.

### Manual publish on PyPI

> :warning: The next steps update the official PyRTL release on PyPI, which
> affects anyone running `pip install pyrtl`. Proceed with caution!

1. If necessary, create a PyPI API token, by going to
   https://pypi.org/manage/account/ and clicking 'Add API token'.
2. Upload distribution archive to PyPI:
   ```shell
   $ uv run --with twine twine upload dist/*
   ```
3. Enter your API token when prompted.
4. Check the new release's status at https://pypi.org/project/pyrtl/#history
5. Install and test the new release from PyPI by following the [Testing a new
   PyPI release](#testing-a-new-pypi-release) instructions above.

## Fixing Mistakes

First assess the magnitude of the problem. If the new release is unusable or is
unsafe to use, yank the bad release, then publish a fixed release. If the new
release has a smaller problem, and is mostly usable, just publish a fixed
release.

### Yanking A Bad Release

If the new release is unusable, [yank the
release](https://pypi.org/help/#yanked). This can be done by a project owner on
PyPI, by clicking 'Manage project' then 'Options', then Yank'. When a release
is yanked, it remains available to anyone requesting exactly the yanked
version, so a project with a pinned requirement on PyRTL won't break. A yanked
version will not be installed in any other case, so a user running `pip install
pyrtl` will never receive a yanked version.

### Publishing A Fixed Release

Fix the problem in the code, then publish a new release with a new version
number by following the instructions above. Do not attempt to reuse an existing
version number.
