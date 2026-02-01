(() => {
  const root = document.documentElement;

  // Ctrl+K command palette
  function openPalette() {
    const modal = document.getElementById("command-palette");
    if (!modal) return;
    if (typeof modal.showModal === "function") modal.showModal();
    const input = modal.querySelector("input[data-cmd-input]");
    if (input) setTimeout(() => input.focus(), 50);
  }

  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openPalette();
    }
  });

  // Auto-dismiss toasts
  const toastRoot = document.getElementById("toast-root");
  if (toastRoot) {
    toastRoot.querySelectorAll("[data-toast]").forEach((el) => {
      const ms = Number(el.getAttribute("data-toast")) || 4500;
      setTimeout(() => {
        el.classList.add("opacity-0", "translate-y-2");
        setTimeout(() => el.remove(), 350);
      }, ms);
    });
  }

  // Dropzone (optional)
  document.querySelectorAll("[data-dropzone]").forEach((zone) => {
    const input = zone.querySelector("input[type=file]");
    if (!input) return;

    const setActive = (v) => zone.classList.toggle("ring-2", v) || zone.classList.toggle("ring-indigo-500/40", v);
    ["dragenter", "dragover"].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        setActive(true);
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      zone.addEventListener(ev, (e) => {
        e.preventDefault();
        setActive(false);
      })
    );
    zone.addEventListener("drop", (e) => {
      const files = e.dataTransfer?.files;
      if (!files?.length) return;
      input.files = files;
      zone.querySelector("[data-dropzone-label]")?.classList.add("text-primary");
    });
  });
})();

