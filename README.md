### Rythulab

RythuLab is a web-based agricultural modeling platform developed to support the creation and customization of crop models. It allows researchers and farmer scientists to design new crop patterns, edit pre-existing crop classification models, and manage structured agricultural data. The platform aims to enhance crop analysis, improve yield prediction, and promote data-driven farming practices through an intuitive digital modeling environment.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch main
bench install-app rythulab
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/rythulab
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
