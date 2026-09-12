# Alex Bethune — data & software portfolio

A static professional site with a readable HTML CV, eight selected project summaries and a token-activity snapshot. The editorial design uses warm paper, pine-green accents and serif headings.

[Public site](https://likio3000.github.io/CV/) · [Selected projects](https://likio3000.github.io/CV/portfolio.html)

## Run locally

No package installation, build step, API keys or backend are needed. From the repository root:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. The CV and project summaries work without JavaScript. Inter, DM Serif Display and IBM Plex Mono are self-hosted with their OFL licenses and system fallbacks; the site makes no third-party runtime requests.

## Pages and content

- `index.html`: profile, selected work, experience, skills, education and contact links. The experience and education were transcribed from the existing CV image; no additional qualifications or employment outcomes are claimed. The download links to the text-based, one-page `Alex-Bethune-CV.pdf`.
- `portfolio.html`: DevPulse, Commerce CDC and NYC Taxi lead the data engineering selection, followed by SignalForge, VIC Energy Forecasting, Alpha Evolve, Typing Quest and Senda. Commerce CDC and SignalForge include public runnable source downloads and recorded demo output from synthetic fixtures. DevPulse and NYC Taxi are labelled as local projects with unreleased code; only the initial VIC study has a public repository. Senda links to its rebuild PR and branch while that version is in review. The token-activity screenshot supplied on 7 September 2026 appears after the project evidence as supplementary context.
- `work-logs.html`: a legacy redirect to the portfolio snapshot. Work Logs is no longer a navigation section. The archived dataset and generator remain available in the repository.
- `public-projects.json`: the explicit selection of repositories eligible for the public archive. The log generator skips repositories outside this list before reading their activity.

The HTML CV has a print stylesheet. The downloadable `Alex-Bethune-CV.pdf` prioritizes data projects and copies the existing employment and education entries without adding responsibilities or outcomes. The original `English CV-2.pdf` is preserved as an archive.

To regenerate the PDF after editing CV content, run `python3 -m pip install -r requirements-cv.txt`, then `python3 scripts/build_cv_pdf.py` and `python3 scripts/check_cv_pdf.py`. The generator reads the visible headline, profile summary, selected project cards, experience, education and skills from `index.html`. There is no separate project list or headline in the PDF builder. Render and inspect the generated PDF before publishing it.

The light token screenshot is stored unchanged in `assets/token-activity-light-2026-09-07.png`. A CSS-applied SVG filter presents it in the site's paper/green palette without changing the source pixels, labels or cell positions. `snapshot.js` provides the full-size dialog, keyboard dismissal and focus return. Without JavaScript, the image link opens the original PNG.

## Checks

```sh
python3 -B -m unittest discover -s tests -v
node --check work-log.js
node --check snapshot.js
node --test tests/*.test.mjs
```

GitHub Actions runs these checks on pushes and pull requests. Tests also execute both downloaded demos, verify source hashes against their manifests, and check HTML/PDF consistency. Tests cover document landmarks, navigation, local resources and anchors, PDF availability, public project selection, exclusion of unselected projects from log generation, archive filtering and pagination, source dates and safe commit links.

For browser acceptance, check CV and Portfolio at desktop and mobile widths, keyboard navigation and skip links, the PDF download, repository links and the no-JavaScript experience. Also check the legacy Work Logs redirect, screenshot dialog (Escape and focus return), mobile image panning and the original-image link without JavaScript. Automated accessibility scans do not establish compatibility with every assistive technology.

## Maintain and publish

Edit the HTML for profile/project copy. The three `.cv-project` cards on `index.html` supply the PDF selection in the same order; retain their visible `h3`, `.work-stack` and `.work-summary` fields. The Junior Data Analyst detail was confirmed by Alex: Dune data was brought into Python to create charts. `styles.css` provides shared foundations; `direction.css` and `direction-fonts.css` implement the selected editorial design. Keep claims linked to source or evidence, and update Senda's review status and links after its rebuild is merged. Check public repository visibility before adding an entry to `public-projects.json`.

The existing GitHub Pages configuration serves the root of `main`. Merging changes into that branch publishes the site. Pull requests provide a review step; this branch has no workflow that deploys a preview automatically.

See [the work-log documentation](docs/WORK_LOGS.md) to prepare a new archive export. Review generated data before committing it. Local project paths, work-log configuration and cover letters are excluded from Git.

The proposed GitHub bio, website and pins are recorded in [the profile plan](docs/GITHUB_PROFILE_PLAN.md). [The checkout note](docs/LOCAL_CHECKOUT.md) records the canonical local copy and recovery branch.


## Public project downloads

`downloads/` contains the source ZIPs, recorded demo JSON and SHA-256 manifests
for Commerce CDC and SignalForge. Each bundle includes its MIT license, README,
synthetic input, Python/SQL implementation, tests and recorded output. A reviewer
can run it with Python 3.12+ without authentication, cloud accounts or packages.
The private Sites portfolio is not used as a public evidence link. DevPulse and
NYC Taxi source remain unreleased; only the two explicitly selected demo bundles
were added to this public repository.

To update a bundle, regenerate it in the Data Engineering Portfolio project with
`make portfolio-assets`, then replace the matching ZIP, demo JSON and manifest
together. The download test checks that archive contents match their hashes and
that running the downloaded program reproduces the displayed output.
