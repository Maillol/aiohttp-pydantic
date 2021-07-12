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
    event: ["push", "tag"]
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
          name: "Deploy on Pypi",
          image: "plugins/pypi",
          settings: {
            username: {
              from_secret: 'pypi_username'
            },
            password: {
              from_secret: 'pypi_password'
            }
          },
          distributions: 'bdist_wheel'
        },
      ],
      trigger: {
        event: ["tag"]
      },
      depends_on: ["python-" + std.strReplace(pythonVersion, '.', '-') for pythonVersion in PYTHON_VERSIONS]
    }
]
