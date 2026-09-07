# Alex Bethune — data & software portfolio

A static professional site with a readable HTML CV, four selected project summaries and a token-activity snapshot. The editorial design uses warm paper, pine-green accents and serif headings.

[Public site](https://likio3000.github.io/CV/) · [Selected projects](https://likio3000.github.io/CV/portfolio.html)

## Run locally

No package installation, build step, API keys or backend are needed. From the repository root:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. The CV and project summaries work without JavaScript. Inter, DM Serif Display and IBM Plex Mono are self-hosted with their OFL licenses and system fallbacks; the site makes no third-party runtime requests.

## Pages and content

- `index.html`: profile, selected work, experience, skills, education and contact links. The experience and education were transcribed from the existing CV image; no additional qualifications or employment outcomes are claimed. The existing PDF download remains available.
- `portfolio.html`: the token-activity screenshot supplied on 7 September 2026, followed by Alpha Evolve, VIC Energy Demand, Typing Quest and Senda. Each summary covers the question, implementation, engineering decisions and evidence. Senda links to its rebuild PR and branch while that version is in review.
- `work-logs.html`: a legacy redirect to the portfolio snapshot. Work Logs is no longer a navigation section. The archived dataset and generator remain available in the repository.
- `public-projects.json`: the explicit selection of repositories eligible for the public archive. The log generator skips repositories outside this list before reading their activity.

The HTML CV has a print stylesheet. Use the browser's Print command for a text-based printout; the downloadable original PDF is kept unchanged.

The light token screenshot is stored unchanged in `assets/token-activity-light-2026-09-07.png`. A CSS-applied SVG filter presents it in the site's paper/green palette without changing the source pixels, labels or cell positions. `snapshot.js` provides the full-size dialog, keyboard dismissal and focus return. Without JavaScript, the image link opens the original PNG.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
node --check work-log.js
node --check snapshot.js
node --test tests/*.test.mjs
```

GitHub Actions runs these checks on pushes and pull requests. Tests cover document landmarks, navigation, local resources and anchors, PDF availability, public project selection, exclusion of unselected projects from log generation, archive filtering and pagination, source dates and safe commit links.

For browser acceptance, check CV and Portfolio at desktop and mobile widths, keyboard navigation and skip links, the PDF download, repository links and the no-JavaScript experience. Also check the legacy Work Logs redirect, screenshot dialog (Escape and focus return), mobile image panning and the original-image link without JavaScript. Automated accessibility scans do not establish compatibility with every assistive technology.

## Maintain and publish

Edit the HTML for profile/project copy. `styles.css` provides shared foundations; `direction.css` and `direction-fonts.css` implement the selected editorial design. Keep claims linked to source or evidence, and update Senda's review status and links after its rebuild is merged. Check public repository visibility before adding an entry to `public-projects.json`.

The existing GitHub Pages configuration serves the root of `main`. Merging changes into that branch publishes the site. Pull requests provide a review step; this branch has no workflow that deploys a preview automatically.

See [the work-log documentation](docs/WORK_LOGS.md) to prepare a new archive export. Review generated data before committing it. Local project paths, work-log configuration and cover letters are excluded from Git.
