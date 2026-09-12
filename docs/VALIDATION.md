# CV alignment validation — 7 September 2026

- Nine Python integrity/accessibility tests and four JavaScript model tests passed.
- JavaScript syntax checks and `git diff --check` passed.
- Playwright reviewed CV and Portfolio at 1280×900 and 390×844; no horizontal document overflow, blank pages or blocking overlays.
- Visually inspected desktop/mobile screenshots and the rendered final one-page PDF.
- PDF link returns HTTP 200 and a PDF document. Text extraction includes all seven existing employment entries. The HTML experience section matches the pre-alignment snapshot byte for byte.
- Screenshot dialog opens, Escape closes it and keyboard focus returns to its trigger.
- Legacy Work Logs redirects to `portfolio.html#token-activity`.
- Without JavaScript, project navigation works, all six project articles remain readable and the full-size image link points to the source PNG.
- No browser console errors. Chromium reports an existing non-blocking Inter font preload warning.

Browser checks used the available Playwright connector; a separate Browser skill was not available in this session. These checks do not establish compatibility with every browser or assistive technology.

## Data engineering update — 12 September 2026

- Twelve Python tests and four JavaScript tests pass, including HTML-to-PDF
  content extraction and executable source-download verification.
- Both public source ZIPs match their SHA-256 manifests. Executing each extracted
  demo reproduces its publicly displayed JSON result.
- The PDF consistency check verifies one page and matching headline, profile,
  three selected projects, experience, education and skills.
- Visually inspected the updated PDF and desktop CV. Reviewed the new Commerce
  CDC case study on mobile; checked both routes at 1280×900 and 390×844 with no
  horizontal document overflow or missing images.
- The PDF, both ZIP downloads and both demo JSON files return HTTP 200 with the
  expected content types. The Commerce CDC download saves as commerce-cdc.zip.
- The evidence disclosure opens and closes. With JavaScript disabled, all eight
  project articles and download links remain available, and the CV's Commerce
  CDC link reaches the correct project anchor.
- No browser page errors were recorded during the route checks.
- Employment titles and dates are preserved. Alex confirmed the added analyst
  detail: data from Dune was turned into charts using Python.

## Project reliability extension — 12 September 2026

- Commerce CDC: 13 tests pass, including randomized late arrivals, zero derived
  writes on replay, no unrelated row rewrites, independent audit and rollback of
  failed repair. The 2,000-customer / 2,000-order synthetic workload reproduces five
  derived writes for one update and 12,002 for a full rebuild of the same state.
- SignalForge: 17 tests pass, including explicit machine populations, coverage
  boundaries, unavailable/expired explanations, rejected snapshot persistence,
  previous-generation retention, recovery and process restart. CLI failures emit
  JSON and exit 1; the previous release remains available.
- Download verification checks SHA-256 manifests against both archives and the
  browsable source mirrors, executes all 30 tests from extracted archives and
  reproduces demo/workload evidence.
- All 12 CV integrity tests and four JavaScript tests pass. The one-page PDF
  matches the HTML and was rendered and visually inspected after the text update.
- Hosted portfolio build, four server-render tests and ESLint pass.
