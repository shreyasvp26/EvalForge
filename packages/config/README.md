# @agent-eval/config

Shared **tooling** configuration for the EvalForge TypeScript workspace.

This package exists so lint, format, TypeScript, and test settings are defined once and inherited everywhere. Runtime application configuration lives in `@agent-eval/env`, not here.

## Exports

| Path                        | Purpose                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| `./typescript/base.json`    | Strict compiler defaults (zero `any`, exact optionals, NodeNext) |
| `./typescript/library.json` | Composite library builds with `dist/` output                     |
| `./typescript/nextjs.json`  | Next.js app baseline (Presentation plane)                        |
| `./eslint/base.js`          | Strict typed ESLint + import ordering                            |
| `./prettier`                | Formatting defaults                                              |
| `./vitest/node.js`          | Shared Vitest + coverage defaults                                |

## Why

Duplicated tsconfig/eslint snippets drift. Drift becomes "works on my machine" and inconsistent CI. Every package should extend these files rather than copying options.
