# tk-ci-tools

Tools for Azure Pipelines. These tools allow a Toolkit developer to validate their code using Azure Pipelines, ensuring the code is formatted properly, does not contain ambiguous statements and passes all the tests on every single commit.

# How to use the build system.

Create a file named `azure-pipelines.yml` file at the root of your repo and put the following in it:

```
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
