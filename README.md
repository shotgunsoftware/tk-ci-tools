[![Build Status](https://dev.azure.com/shotgun-ecosystem/Toolkit/_apis/build/status/tk-ci-tools?branchName=master)](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build/latest?definitionId=39&branchName=master)

# tk-ci-tools

Tools for Azure Pipelines. These tools allow a Toolkit developer to validate their code using Azure Pipelines, ensuring the code is formatted properly, does not contain ambiguous statements and passes all the tests.

The pipeline is split into two main sections
- code style validation
- running tests

Code style validation is enforced by running the `pre-commit` hook on all the files in the repository. Tests are run on Windows, macOS and Linux using `pytest` and [`tk-toolchain`](https://github.com/shotgunsoftware/tk-toolchain)

# Learning more about Azure Piplines

If you want to learn more about how Azure Pipelines yml files work, you can visit the following pages:

- [YAML Schema](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema?view=azure-devops&tabs=schema%2Cparameter-schema)
- [YAML Syntax](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/templates?view=azure-devops)
- [Expressions](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/expressions?view=azure-devops) (aka the `{{ }}` syntax)
- [Pre-defined build variables](https://docs.microsoft.com/en-us/azure/devops/pipelines/build/variables?view=azure-devops&tabs=yaml)
- [Library Secrets](https://docs.microsoft.com/en-us/azure/devops/pipelines/process/variables?view=azure-devops&tabs=yaml%2Cbatch)
- [List of available `task`s](https://docs.microsoft.com/en-us/azure/devops/pipelines/tasks/?view=azure-devops)

# Requirements to the build pipeline

## pre-commit hook

Your respository needs to have a pre-commit hook for the code style validation to pass. All Toolkit repositories are expected to have them.

You save the following as a starting point at the root of your respository in a file called `.pre-commit-config.yaml`. The `exclude` setting is a regular expression matching file paths that should not be validated.

```yaml
# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# Styles the code properly
# Exclude the UI files, as they are auto-generated.
exclude: "ui\/.*py$"
# List of super useful formatters.
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v2.4.0
    hooks:
    # Ensures the code is syntaxically correct
    - id: check-ast
      language_version: python3
    # Ensures a file name will resolve on all platform
    - id: check-case-conflict
    # Checks files with the execute bit set have shebangs
    - id: check-executables-have-shebangs
    # Ensure there's no incomplete merges
    - id: check-merge-conflict
    # Adds an empty line if missing at the end of a file.
    - id: end-of-file-fixer
    # Makes sure requirements.txt is properly formatted
    - id: requirements-txt-fixer
    # Removes trailing whitespaces.
    - id: trailing-whitespace
  # Leave black at the bottom so all touchups are done before it is run.
  - repo: https://github.com/ambv/black
    rev: 19.10b0
    hooks:
    - id: black
      language_version: python3

```

## Azure Pipeline configuration

### Invoking the build pipeline from your respository

Create a file named `azure-pipelines.yml` file at the root of your repo and put the following in it:

```yaml
# Imports the shared Azure CI tools from the master branch of shotgunsoftware/tk-ci-tools
resources:
  repositories:
    - repository: templates
      type: github
      name: shotgunsoftware/tk-ci-tools
      ref: refs/heads/master
      endpoint: shotgunsoftware

# We want builds to trigger for 3 reasons:
# - The master branch sees new commits
# - Each PR should get rebuilt when commits are added to it.
# - When we tag something
trigger:
  branches:
    include:
    - master
  tags:
    include:
    - v*
pr:
  branches:
    include:
    - "*"

# This pulls in a variable group from Azure. Variables can be encrypted or not.
variables:
- group: deploy-secrets

# Launch into the build pipeline.
jobs:
- template: build-pipeline.yml@templates
```

If you need to use an in-development version of these tools from a branch, you can update the `ref` in `repositories` section to point to a different branch.

The `build-pipeline.yml` template has a few parameters. You can find out more about them in [build-pipeline.yml](https://github.com/shotgunsoftware/tk-ci-tools/blob/master/build-pipeline.yml).

### Create a build in Azure Pipelines

Once you've added your `azure-pipelines.yml` file to your repository, it's time to add the repository to the Azure Pipelines web service.

1. Go to the [Shotgun Ecosystem Azure Pipelines](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build) page.
2. Click on the `New Pipeline` button at the top right of the page.
3. On the `Connect` page , select `Github`.
4. On the `Select` page, you'll then see a list of repositories you have access to. Scroll all the way to the bottom and select `You may also select a specific connection.`
5. Then click on the `shotgunsoftware` installation token.
6. Find the repository you're trying to add to Azure Pipelines and select it.
7. On the `Configure your pipeline screen`, select `Existing Azure Pipeline YAML file.`
8.  In the pop-up that appeared on the right, select the branch where your pipeline has been setup and the name of the file, usually `azure-pipelines.yml` and click `Continue`.
9.  Click on the `Variables` button at the top right.
10. In the Variables tab, create a new variable name `codecov.token` and make sure `Keep this value secret` is checked. This is important or people outside the organization could push coverage data.
11. The codecov token for your repository can be found at [codecov.io](codecov.io). In this example, we are setting up a pipeline for `tk-multi-launchapp`, so we can find the key at https://codecov.io/gh/shotgunsoftware/tk-multi-launchapp.
12. Click the copy button and paste it in the `Value` box over at Azure Pipelines. If you've done this right, the value should be masked in the edit box.
13. Hit `Ok`, then `Save` at the bottom right of the variable creation page.
14. You're now back to the pipeline edit page. Select the branch you've pushed your azure-pipelines.yml file to kick-off the first build. You can now click `Run` at the top right if you want to save and launch the pipeline on that branch or simply click on the arrow next to `Run` and pick `Save`.
15. Go back to the pipeline [list](https://dev.azure.com/shotgun-ecosystem/Toolkit/_build) page. You should see your new pipeline at the top named `shotgunsoftware.<repo-name>`. We'll need to rename it to just the repository name (this will help our release scripts.). We'll also want to move it to one of the appropriate folder in the `All` tab (nudged between `Recent` and `Runs`). To do this, click on the pipeline. Once you're on the page of the pipeline, click on the `...` button and select `Rename/Move`. Remove the organization name, select the right folder and hit `Save`.
15. You're done! You can now push to Github and your changes will be picked up by the build pipeline according to the rules defined in `azure-pipelines.yml`. As mentionned above, Azure Pipelines will launch a build for any commits done to master, any commits pushed to a pull request and when a tag is created.
