# create-ukb-brain

Create a Unified Knowledge Base brain project from a template.

## Published usage

```bash
npm create ukb-brain@latest my-finance-brain -- --template default --offline
```

## Local development usage

```bash
node packages/create-ukb-brain/bin/create-ukb-brain.mjs my-finance-brain --offline
```

## Output

The generator creates a human-editable brain project:

```text
brain.config.yaml
README.md
domains/
plugins/
```

The generated project is designed to be loaded by the Unified Knowledge Base runtime.
