# `create-ukb-brain` CLI

## Goal

Provide an npm initializer that creates a new brain project from a template.

Target user experience after package publication:

```bash
npm create ukb-brain@latest my-finance-brain -- --template default --offline
```

This works because npm maps `npm create ukb-brain` to a package named `create-ukb-brain`.

## Current local command

Before publishing to npm:

```bash
node packages/create-ukb-brain/bin/create-ukb-brain.mjs my-finance-brain --offline
```

## What the generator creates

```text
my-finance-brain/
  brain.config.yaml
  README.md
  domains/
    finance/
      metrics/
        metric_template.yaml
  plugins/
    context_source.py
```

## Why this is useful

Users can keep the runtime platform stable while creating many separate brain projects:

```text
finance-brain
ops-brain
sales-brain
legal-brain
project-specific-brain
```

Each brain can have its own templates, plugins, governance rules, and golden questions.

## Future CLI commands

The Python `ukb` CLI should eventually add:

```bash
ukb brain validate ./my-finance-brain
ukb brain load ./my-finance-brain
ukb brain compile ./my-finance-brain
ukb brain publish ./my-finance-brain --target local
ukb plugins list ./my-finance-brain
```

The npm package should focus only on creating project structure. The Python platform CLI should run and validate the brain.
