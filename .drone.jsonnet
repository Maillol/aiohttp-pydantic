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
        "echo Install package",
        "pip install -U setuptools wheel pip; pip install .",
        "echo Test to import module of package",
        "python -c \"import importlib, setuptools; [print(importlib.import_module(package).__name__, '[OK]') for package in setuptools.find_packages() if package.startswith('aiohttp_pydantic.') or package == 'aiohttp_pydantic']\"",
        "echo Install CI dependencies",
        "pip install -r requirements/ci.txt",
        "echo Launch unittest",
        "pytest --cov-report=xml --cov=aiohttp_pydantic tests/",
        "echo Check the README.rst render",
        "python -m readme_renderer -o /dev/null README.rst"
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
          image: "python3.8",
          environment: {
            pypi_username: {
              from_secret: 'pypi_username'
            },
            pypi_password: {
              from_secret: 'pypi_password'
            }
          },
          commands: [
            "pip install --force-reinstall twine wheel",
            "python setup.py build bdist_wheel",
            "set +x",
            "twine upload --non-interactive -u \"$pypi_username\" -p \"$pypi_password\" dist/*"
          ]
        },
      ],
      trigger: {
        event: ["tag"]
      },
      depends_on: ["python-" + std.strReplace(pythonVersion, '.', '-') for pythonVersion in PYTHON_VERSIONS]
    }
]
