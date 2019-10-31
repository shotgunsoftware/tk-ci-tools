CI tools tests
==============

In order to test the pipeline and make sure it works, you need to make it fail. Here are the things to try.

Fail black
----------
Modify a test so that reformatting needs to be done. You can push such a change by passing in `--no-verify` to git commit to bypass the black pre-commit hook.

Fail flake8
-----------
Trigger a missing variable error, such as adding `a == b` to the test file.

Fail tests
----------
Put an `assert False` in a test.
