const dialog = document.querySelector("#snapshot-dialog");
const opener = document.querySelector("[data-view-image]");

if (dialog && opener && typeof dialog.showModal === "function") {
  opener.addEventListener("click", (event) => {
    event.preventDefault();
    dialog.showModal();
    dialog.querySelector(".image-scroll").scrollLeft = 0;
  });
  dialog.querySelector("[data-close-image]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
  dialog.addEventListener("close", () => opener.focus());
}
