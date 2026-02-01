/**
 * Composant réutilisable : select avec création à la volée (icône +)
 * Usage: InlineCreateSelect.init({ selectId: 'id_department', model: 'department', canAdd: true })
 */
(function () {
  "use strict";

  function getCsrfToken() {
    const name = "csrftoken";
    let value = document.cookie
      .split("; ")
      .find((row) => row.startsWith(name + "="));
    return value ? decodeURIComponent(value.split("=")[1]) : "";
  }

  function showToast(message, type) {
    type = type || "success";
    const root = document.getElementById("toast-root");
    if (!root) return;
    const bg = type === "error" ? "bg-rose-500" : "bg-emerald-500";
    const el = document.createElement("div");
    el.className =
      "w-[320px] max-w-[calc(100vw-2rem)] rounded-2xl border border-slate-200 bg-white p-4 shadow-lg transition-all duration-300";
    el.innerHTML = `
      <div class="flex items-start gap-3">
        <div class="mt-0.5 h-2.5 w-2.5 rounded-full ${bg}"></div>
        <div class="min-w-0">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">${type === "error" ? "Erreur" : "Succès"}</div>
          <div class="mt-1 text-sm text-slate-800">${escapeHtml(message)}</div>
        </div>
      </div>
    `;
    root.appendChild(el);
    setTimeout(() => {
      el.classList.add("opacity-0", "translate-y-2");
      setTimeout(() => el.remove(), 350);
    }, 4500);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function createModal(selectEl, config, onSuccess) {
    const existing = document.getElementById("inline-create-modal");
    if (existing) existing.remove();

    const modal = document.createElement("div");
    modal.id = "inline-create-modal";
    modal.className = "fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm";
    modal.innerHTML = `
      <div class="mx-4 w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
        <h3 class="text-lg font-bold text-slate-900">${escapeHtml(config.modalTitle || "Ajouter une valeur")}</h3>
        <p class="mt-1 text-sm text-slate-600">${escapeHtml(config.modalHint || "Saisissez le nom et validez.")}</p>
        <div class="mt-4">
          <label class="block text-sm font-semibold text-slate-900">${escapeHtml(config.labelField || "Nom")}</label>
          <input type="text" data-inline-create-input
            class="mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
            placeholder="${escapeHtml(config.placeholder || "")}"
            autocomplete="off" />
          <p class="mt-1.5 hidden text-xs text-rose-600" data-inline-create-error></p>
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button type="button" data-inline-create-cancel
            class="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Annuler
          </button>
          <button type="button" data-inline-create-submit
            class="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-500 to-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 hover:from-sky-600 hover:to-sky-700">
            <i data-lucide="plus" class="h-4 w-4"></i>
            Ajouter
          </button>
        </div>
      </div>
    `;

    const input = modal.querySelector("[data-inline-create-input]");
    const errEl = modal.querySelector("[data-inline-create-error]");
    const cancelBtn = modal.querySelector("[data-inline-create-cancel]");
    const submitBtn = modal.querySelector("[data-inline-create-submit]");

    function close() {
      modal.remove();
      document.body.style.overflow = "";
    }

    function setError(msg) {
      errEl.textContent = msg || "";
      errEl.classList.toggle("hidden", !msg);
    }

    cancelBtn.addEventListener("click", close);
    modal.addEventListener("click", (e) => {
      if (e.target === modal) close();
    });

    submitBtn.addEventListener("click", function () {
      const name = (input.value || "").trim();
      setError("");
      if (!name) {
        setError("Le nom est requis.");
        return;
      }

      submitBtn.disabled = true;
      const payload = { model: config.model, name: name };
      if (config.parentSelectId) {
        const parentSelect = document.getElementById(config.parentSelectId);
        const parentVal = parentSelect ? parentSelect.value : "";
        if (parentVal) payload.parent_id = parentVal;
        else if (config.requiresParent) {
          setError(config.parentRequiredMessage || "Veuillez d'abord sélectionner un élément parent.");
          submitBtn.disabled = false;
          return;
        }
      }

      fetch(config.apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload),
      })
        .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
        .then(({ ok, data }) => {
          if (ok && data.success) {
            const opt = document.createElement("option");
            opt.value = data.id;
            opt.textContent = data.label || data.name;
            selectEl.appendChild(opt);
            selectEl.value = data.id;
            if (typeof lucide !== "undefined") lucide.createIcons();
            showToast(config.successMessage || "Valeur ajoutée et sélectionnée.");
            close();
            onSuccess && onSuccess(data);
          } else {
            setError(data.error || "Erreur lors de l'ajout.");
            showToast(data.error || "Erreur", "error");
          }
        })
        .catch((err) => {
          setError("Erreur réseau.");
          showToast("Erreur réseau.", "error");
        })
        .finally(() => {
          submitBtn.disabled = false;
        });
    });

    document.body.style.overflow = "hidden";
    document.body.appendChild(modal);
    input.focus();
    if (typeof lucide !== "undefined") lucide.createIcons();
  }

  window.InlineCreateSelect = {
    init: function (options) {
      const selectId = options.selectId;
      const selectEl = document.getElementById(selectId);
      if (!selectEl || !options.canAdd) return;

      const apiUrl = options.apiUrl || "/api/reference/create/";
      const model = options.model;
      if (!model) return;

      const parentSelectId = options.parentSelectId || null;
      const requiresParent = options.requiresParent || false;

      const wrapper = document.createElement("div");
      wrapper.className = "mt-1.5 flex items-center gap-2";
      selectEl.parentNode.insertBefore(wrapper, selectEl);
      wrapper.appendChild(selectEl);
      selectEl.classList.add("flex-1", "min-w-0");
      selectEl.classList.remove("mt-1.5");

      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("aria-label", "Ajouter une nouvelle valeur");
      btn.className =
        "inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-sky-300 hover:bg-sky-50 hover:text-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500/20";
      btn.innerHTML = '<i data-lucide="plus" class="h-4 w-4"></i>';

      btn.addEventListener("click", function () {
        createModal(selectEl, {
          apiUrl,
          model,
          parentSelectId,
          requiresParent,
          modalTitle: options.modalTitle,
          modalHint: options.modalHint,
          labelField: options.labelField,
          placeholder: options.placeholder,
          successMessage: options.successMessage,
          parentRequiredMessage: options.parentRequiredMessage,
        });
      });

      wrapper.appendChild(btn);
      if (typeof lucide !== "undefined") lucide.createIcons();
    },

    initAll: function () {
      document.querySelectorAll("[data-inline-create]").forEach((el) => {
        const canAdd = el.getAttribute("data-inline-create") === "true" || el.getAttribute("data-inline-create") === "1";
        if (!canAdd) return;
        const selectId = el.getAttribute("data-inline-create-select");
        const model = el.getAttribute("data-inline-create-model");
        if (!selectId || !model) return;
        this.init({
          selectId,
          model,
          canAdd: true,
          parentSelectId: el.getAttribute("data-inline-create-parent") || null,
          requiresParent: el.getAttribute("data-inline-create-requires-parent") === "true",
          modalTitle: el.getAttribute("data-inline-create-title") || null,
          modalHint: el.getAttribute("data-inline-create-hint") || null,
        });
      });
    },
  };
})();
