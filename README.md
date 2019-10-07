# tk-ci-tools

Tools for Azure Pipelines. These tools allow a Toolkit developer to validate their code using Azure Pipelines, ensuring the code is formatted properly, does not contain ambiguous statements and passes all the tests on every single commit.

# How to use these tools

Create a file named  `azure-pipeline.yml` file at the root of your repo and put the following:

```
# Imports the shared Azure CI tools from the master branch of shotgunsoftware/tk-ci-tools
resources:
  repositories:
    - repository: templates
      type: github
      name: shotgunsoftware/tk-ci-tools
      ref: refs/heads/master
      endpoint: shotgunsoftware

# Configures CI to be triggered by changes to any branches and on tag creation.
trigger:
  branches:
    include:
    - '*'
  tags:
    include:
    - v*

# This pulls in a variable group from Azure. Variables can be encrypted or not.
variables:
- group: deploy-secrets

jobs:
- template: build-pipeline.yml@templates
```

Someting
    If you need to use an in-development version of these tools from a branch, you can update the `ref` in `repositories` section to point to a different branch.
