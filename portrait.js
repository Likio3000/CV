// A local preview enhancement. Content and image remain complete without it.
const portrait = document.querySelector("[data-portrait]");
const motion = matchMedia(
  "(prefers-reduced-motion: no-preference) and (hover: hover) and (pointer: fine)",
);
if (portrait) {
  let frame = 0;
  let point = null;
  const reset = () => {
    cancelAnimationFrame(frame);
    frame = 0;
    point = null;
    portrait.style.removeProperty("--tilt-x");
    portrait.style.removeProperty("--tilt-y");
  };
  portrait.addEventListener(
    "pointermove",
    (event) => {
      if (!motion.matches || event.pointerType !== "mouse") return;
      const bounds = portrait.getBoundingClientRect();
      point = {
        x: Math.max(
          -1,
          Math.min(1, ((event.clientX - bounds.left) / bounds.width) * 2 - 1),
        ),
        y: Math.max(
          -1,
          Math.min(1, ((event.clientY - bounds.top) / bounds.height) * 2 - 1),
        ),
      };
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        portrait.style.setProperty(
          "--tilt-x",
          `${(-point.y * 3.5).toFixed(2)}deg`,
        );
        portrait.style.setProperty(
          "--tilt-y",
          `${(point.x * 3.5).toFixed(2)}deg`,
        );
      });
    },
    { passive: true },
  );
  portrait.addEventListener("pointerleave", reset);
  portrait.addEventListener("pointercancel", reset);
  motion.addEventListener("change", reset);
  window.addEventListener("blur", reset);
}
