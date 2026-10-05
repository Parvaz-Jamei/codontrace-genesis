# Console

Local preview for CodonTrace Genesis. The page that ships in the package is built into `src/codontrace/console/static`. Opening it does not need Node.

```bash
python -m codontrace.console
```

Rebuild the page from this directory when the interface changes:

```bash
npm install
npm run build
```

`npm run dev` serves the page with a host profile for layout work. That process is not the installed command, and it does not run the evolution engine.

The installed command checks the public GitHub release when it starts and every 24 hours. The check does not push. A clean git checkout can fast-forward from the page. A dirty tree and a wheel install are left untouched.
