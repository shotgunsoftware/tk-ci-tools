CI tools tests
==============

These tests are designed to fail. It allows us to make sure that these errors will be properly caught by the build pipeline.

Here are the expected output of commands

Black
-----
```
would reformat tests/test_build.py
All done! 💥 💔 💥
1 file would be reformatted.
```

Flake8
------
```
tests/test_build.py:13:16: E222 multiple spaces after operator
tests/test_build.py:15:5: F841 local variable 'a' is assigned to but never used
tests/test_build.py:15:9: F821 undefined name 'b'
```

> Note: The Flake8 errors will only appear on a pull request build, not on a commit build. This is because during a build we can't do a diff with the destination branch, as there is no notion of where we're merging code.
