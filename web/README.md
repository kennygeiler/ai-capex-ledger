# Capex Ledger explorer (web)

React + [shadcn/ui](https://github.com/shadcn-ui/ui) front end for `data/clean/viz.json`. See the repo README for the full picture.

```bash
pnpm install
pnpm dev     # http://localhost:3601, fetches ../data/clean/viz.json
pnpm build   # type-check, then writes ../explorer/standalone.html (one file, data inlined)
```

Add shadcn components with `pnpm dlx shadcn@latest add <name>` (config in `components.json`, style radix-nova).
