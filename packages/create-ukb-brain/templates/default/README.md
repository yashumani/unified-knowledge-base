# {{BRAIN_NAME}}

This is a generated Unified Knowledge Base brain project.

## Purpose

Use this folder to define your domain-specific AI Brain without forking the core platform.

## Structure

```text
brain.config.yaml       Brain identity, runtime mode, plugin list, governance defaults
domains/                Domain-specific objects and templates
plugins/                Local plugins for connectors, parsers, extractors, validators
evals/                  Golden questions and expected objects
```

## Safety note

Do not add confidential company data, customer data, credentials, or proprietary documents unless this project is inside an approved private environment.

## Recommended workflow

1. Add or edit local YAML/Markdown knowledge.
2. Run validation.
3. Submit context to the review queue.
4. Have a human reviewer approve the candidate object.
5. Publish approved objects to the brain runtime.
