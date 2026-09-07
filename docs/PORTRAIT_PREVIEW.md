# Local portrait preview

This branch adds an artistic treatment of Alex's supplied photograph to the CV header. The image was generated with Image Gen using the original photo as a reference, preserving the back-facing pose, clothing and bridge composition. The WebP asset is 138,410 bytes at 1086 × 1448 pixels; the supplied photograph is not modified.

The image has reserved dimensions and remains visible without JavaScript. The optional pointer tilt is bounded to 3.5 degrees, runs only for a mouse with a fine pointer and is disabled for reduced motion and touch. The portrait is omitted from print output.

This proposal is local pending visual review. The general UI redesign is commit `08669d4` on `likio/cv-portfolio-refresh` and is already in draft PR #1. The portrait changes are on `likio/cv-portrait-preview` and have not been pushed. Publishing them requires approval of the visual proposal.

Validation: checked at 320, 390, 820, 984 and 1440px with no page overflow or WCAG A/AA axe violations; verified bounded pointer motion, reduced-motion reset, touch/no-JavaScript fallback and print omission.
