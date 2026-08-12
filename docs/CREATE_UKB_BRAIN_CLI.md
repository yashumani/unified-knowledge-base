# `create-ukb-brain` CLI

## Goal

Provide an npm initializer that creates a new brain project from a template.

Target user experience after package publication:

```bash
npm create ukb-brain@latest my-support-brain -- --template default --offline
```

This works because npm maps `npm create ukb-brain` to a package named `create-ukb-brain`.

## Current local command

Before publishing to npm:

```bash
node packages/create-ukb-brain/bin/create-ukb-brain.mjs my-support-brain --offline
```

## What the generator creates

```text
my-support-brain/
  brain.config.yaml
  README.md
  domains/
    support/
      metrics/
        metric_template.yaml
  plugins/
    context_source.py
```

## Public example policy

Generated examples must be synthetic and neutral. The default project uses a generic support-operations domain and must not include employer-specific dashboards, telecom workflows, finance-planning workflows, or proprietary metrics.

## Why this is useful

Users can keep the runtime platform stable while creating many separate brain projects:

```text
support-brain
ops-brain
sales-brain
legal-brain
project-specific-brain
```

Each brain can have its own templates, plugins, governance rules, and golden questions.

## Future CLI commands

The Python `ukb` CLI should eventually add:

```bash
ukb brain validate ./my-support-brain
ukb brain load ./my-support-brain
ukb brain compile ./my-support-brain
ukb brain publish ./my-support-brain --target local
ukb plugins list ./my-support-brain
```

The npm package should focus only on creating project structure. The Python platform CLI should run and validate the brain.
