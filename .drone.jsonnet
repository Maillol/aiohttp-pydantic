/*
Code to generate the .drone.yaml. Use the command:

drone jsonnet --stream --format yaml
*/


local PYTHON_VERSIONS = ["3.8", "3.9"];


local BuildAndTestPipeline(name, image) = {
  kind: "pipeline",
  type: "docker",
  name: name,
  steps: [
    {
      name: "Install package and test",
      image: image,
      commands: [
        "test \"$(md5sum tasks.py)\" = \"18f864b3ac76119938e3317e49b4ffa1  tasks.py\"",
        "pip install -U setuptools wheel pip; pip install invoke",
        "invoke prepare-upload"
      ]
    },
    {
      name: "coverage",
      image: "plugins/codecov",
      settings: {
        token: "9ea10e04-a71a-4eea-9dcc-8eaabe1479e2",
        files: ["coverage.xml"]
      }
    }
  ],
  trigger: {
    event: ["pull_request", "push", "tag"]
  }
};


[
    BuildAndTestPipeline("python-" + std.strReplace(pythonVersion, '.', '-'),
             "python:" + pythonVersion)
    for pythonVersion in PYTHON_VERSIONS
] + [
    {
      kind: "pipeline",
      type: "docker",
      name: "Deploy on Pypi",
      steps: [
        {
          name: "Install twine and deploy",
          image: "python:3.8",
          environment: {
            pypi_username: {
              from_secret: 'pypi_username'
            },
            pypi_password: {
              from_secret: 'pypi_password'
            }
          },
          commands: [
            "test \"$(md5sum tasks.py)\" = \"18f864b3ac76119938e3317e49b4ffa1  tasks.py\"",
            "pip install -U setuptools wheel pip; pip install invoke",
            "invoke upload --pypi-user \"$pypi_username\" --pypi-password \"$pypi_password\""
          ]
        },
      ],
      trigger: {
        event: ["tag"]
      },
      depends_on: ["python-" + std.strReplace(pythonVersion, '.', '-') for pythonVersion in PYTHON_VERSIONS]
    }
]
