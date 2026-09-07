# Alex Bethune — data & software portfolio

A static professional site with a readable HTML CV, four selected project summaries and an archived development log.

[Public site](https://likio3000.github.io/CV/) · [Selected projects](https://likio3000.github.io/CV/portfolio.html)

## Run locally

No package installation, build step, API keys or backend are needed. From the repository root:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. The CV and project summaries work without JavaScript. The development history uses the committed `work-log-data.js` snapshot. Fonts are requested from Google Fonts, with system fallbacks when offline.

## Pages and content

- `index.html`: profile, selected work, experience, skills, education and contact links. The experience and education were transcribed from the existing CV image; no additional qualifications or employment outcomes are claimed. The existing PDF download remains available.
- `portfolio.html`: Alpha Evolve, VIC Energy Demand, Typing Quest and Senda. Each summary covers the question, implementation, engineering decisions and evidence. Senda links to its rebuild PR and branch while that version is in review.
- `work-logs.html`: selected historical development entries. The export date is visible; this is an archive, not a live contribution monitor or measure of productivity.
- `public-projects.json`: the explicit selection of repositories eligible for the public archive. The log generator skips repositories outside this list before reading their activity.

The HTML CV has a print stylesheet. Use the browser's Print command for a text-based printout; the downloadable original PDF is kept unchanged.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
node --check work-log.js
```

GitHub Actions runs these checks on pushes and pull requests. Tests cover document landmarks, navigation, local resources and anchors, PDF availability, the public project selection and exclusion of unselected projects from log generation.

For browser acceptance, check all three pages at desktop and mobile widths, keyboard navigation and skip links, the PDF download, repository links and the no-JavaScript CV/portfolio. The archive additionally needs a rendering check with its committed dataset. Automated accessibility scans do not establish compatibility with every assistive technology.

## Maintain and publish

Edit the HTML for profile/project copy and `styles.css` for the shared visual system. Keep claims linked to source or evidence, and update Senda's review status and links after its rebuild is merged. Check public repository visibility before adding an entry to `public-projects.json`.

The existing GitHub Pages configuration serves the root of `main`. Merging changes into that branch publishes the site. Pull requests provide a review step; this branch has no workflow that deploys a preview automatically.

See [the work-log documentation](docs/WORK_LOGS.md) to prepare a new archive export. Review generated data before committing it. Local project paths, work-log configuration and cover letters are excluded from Git.
