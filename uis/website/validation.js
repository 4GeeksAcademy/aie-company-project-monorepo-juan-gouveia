document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("registration-form");
  if (!form) return;

  const stepPanels = Array.from(document.querySelectorAll("[data-step-panel]"));
  const progressItems = Array.from(document.querySelectorAll("[data-progress-step]"));
  const prevBtn = document.getElementById("prev-step-btn");
  const nextBtn = document.getElementById("next-step-btn");
  const submitBtn = document.getElementById("submit-step-btn");

  const fields = {
    name: form.querySelector('input[name="name"]'),
    email: form.querySelector('input[name="email"]'),
    birthYear: form.querySelector("#birth-year"),
    pais: form.querySelector("#pais"),
    ciudad: form.querySelector("#ciudad"),
    favorita: form.querySelector("#ubicacion-favorita"),
    telefono: form.querySelector("#telefono"),
    como: form.querySelector("#como-nos-conociste"),
    sinRestricciones: form.querySelector("#sin-restricciones"),
    vegano: form.querySelector("#vegano"),
    sinGluten: form.querySelector("#sin-gluten"),
    otros: form.querySelector("#otros"),
    ofertas: form.querySelector("#ofertas-email"),
    terminos: form.querySelector("#acepto-terminos")
  };

  let currentStep = 1;
  const TOTAL_STEPS = 3;

  const citiesByCountry = {
    colombia: [
      { value: "medellin", label: "Medellín" },
      { value: "bogota", label: "Bogotá" },
      { value: "cali", label: "Cali" }
    ],
    "estados-unidos": [
      { value: "miami", label: "Miami" },
      { value: "orlando", label: "Orlando" }
    ]
  };

  const favoritesByCountryCity = {
    "colombia|medellin": [
      { value: "bra-med-01", label: "Brasaland Medellín 01" },
      { value: "bra-med-02", label: "Brasaland Medellín 02" },
      { value: "bra-med-03", label: "Brasaland Medellín 03" },
      { value: "bra-med-04", label: "Brasaland Medellín 04" }
    ],
    "colombia|bogota": [
      { value: "bra-bog-01", label: "Brasaland Bogotá 01" },
      { value: "bra-bog-02", label: "Brasaland Bogotá 02" },
      { value: "bra-bog-03", label: "Brasaland Bogotá 03" },
      { value: "bra-bog-04", label: "Brasaland Bogotá 04" }
    ],
    "colombia|cali": [
      { value: "bra-cal-01", label: "Brasaland Cali 01" },
      { value: "bra-cal-02", label: "Brasaland Cali 02" }
    ],
    "estados-unidos|miami": [
      { value: "bra-mia-01", label: "Brasaland Miami 01" },
      { value: "bra-mia-02", label: "Brasaland Miami 02" }
    ],
    "estados-unidos|orlando": [
      { value: "bra-orl-01", label: "Brasaland Orlando 01" },
      { value: "bra-orl-02", label: "Brasaland Orlando 02" }
    ]
  };

  const phonePrefixByCountry = {
    colombia: "+57",
    "estados-unidos": "+1"
  };

  const stepFieldValidators = {
    1: [validateName, validateEmail, validateBirthDate],
    2: [validateCountry, validateCity, validateFavoriteIfSelected, validatePhone],
    3: [validateHowDidYouKnow, validateDietaryRules, validateTerms]
  };

  const errorElements = new WeakMap();

  function setError(input, message) {
    if (!input) return false;

    input.setCustomValidity(message || "");

    let errorEl = errorElements.get(input);
    const isCheckbox = input.type === "checkbox";
    const host = isCheckbox && input.closest("label") ? input.closest("label") : input;

    if (message && !errorEl) {
      errorEl = document.createElement("p");
      errorEl.className = "mt-1 text-sm text-red-600";
      errorEl.setAttribute("aria-live", "polite");

      const key = input.id || input.name || `field-${Math.random().toString(36).slice(2, 8)}`;
      errorEl.id = `${key}-error`;
      host.insertAdjacentElement("afterend", errorEl);
      errorElements.set(input, errorEl);

      const describedBy = input.getAttribute("aria-describedby");
      if (!describedBy) {
        input.setAttribute("aria-describedby", errorEl.id);
      }
    }

    if (errorEl) {
      if (message) {
        errorEl.textContent = message;
        errorEl.classList.remove("hidden");
        input.setAttribute("aria-invalid", "true");
      } else {
        errorEl.textContent = "";
        errorEl.classList.add("hidden");
        input.removeAttribute("aria-invalid");
      }
    }

    return !message;
  }

  function reportIfNeeded(input, shouldReport) {
    // Sin pop-up nativo; los errores se muestran debajo del campo.
  }

  function renderOptions(select, placeholder, options) {
    select.innerHTML = "";
    const first = document.createElement("option");
    first.value = "";
    first.textContent = placeholder;
    select.appendChild(first);

    options.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.value;
      opt.textContent = item.label;
      select.appendChild(opt);
    });
  }

  function getCitiesForCountry(country) {
    return citiesByCountry[country] || [];
  }

  function getFavoritesFor(country, city) {
    return favoritesByCountryCity[`${country}|${city}`] || [];
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
  }

  function isAdultOver18(value) {
    if (!value) return false;
    const birth = new Date(value);
    if (Number.isNaN(birth.getTime())) return false;
    const today = new Date();
    const threshold = new Date(today.getFullYear() - 18, today.getMonth(), today.getDate());
    return birth < threshold;
  }

  function hasAtLeastTwoWords(text) {
    const words = text.trim().replace(/\s+/g, " ").split(" ").filter(Boolean);
    return words.length >= 2;
  }

  function isValidPhoneIntl(value) {
    return /^\+\d{8,15}$/.test((value || "").trim());
  }

  function validateName(report) {
    const value = fields.name.value.trim();
    if (!value) {
      setError(fields.name, "Ingresa tu nombre completo (nombre y apellido).");
      reportIfNeeded(fields.name, report);
      return false;
    }
    if (!hasAtLeastTwoWords(value)) {
      setError(fields.name, "Ingresa tu nombre completo (nombre y apellido).");
      reportIfNeeded(fields.name, report);
      return false;
    }
    setError(fields.name, "");
    return true;
  }

  function validateEmail(report) {
    const value = fields.email.value.trim();
    if (!value) {
      setError(fields.email, "El correo es obligatorio.");
      reportIfNeeded(fields.email, report);
      return false;
    }
    if (!isValidEmail(value)) {
      setError(fields.email, "Ingresa un email válido (ejemplo: nombre@correo.com).");
      reportIfNeeded(fields.email, report);
      return false;
    }
    setError(fields.email, "");
    return true;
  }

  function validateBirthDate(report) {
    const value = fields.birthYear.value;
    if (!value) {
      setError(fields.birthYear, "La fecha de nacimiento es obligatoria.");
      reportIfNeeded(fields.birthYear, report);
      return false;
    }
    if (!isAdultOver18(value)) {
      setError(fields.birthYear, "Debes ser mayor de 18 años para registrarte en Brasa Points.");
      reportIfNeeded(fields.birthYear, report);
      return false;
    }
    setError(fields.birthYear, "");
    return true;
  }

  function validateCountry(report) {
    if (!fields.pais.value) {
      setError(fields.pais, "Selecciona tu país.");
      reportIfNeeded(fields.pais, report);
      return false;
    }
    setError(fields.pais, "");
    return true;
  }

  function validateCity(report) {
    const country = fields.pais.value;
    const city = fields.ciudad.value;
    const allowed = getCitiesForCountry(country).map((c) => c.value);

    if (!city) {
      setError(fields.ciudad, "Selecciona tu ciudad.");
      reportIfNeeded(fields.ciudad, report);
      return false;
    }
    if (!allowed.includes(city)) {
      setError(fields.ciudad, "La ciudad no corresponde al país seleccionado.");
      reportIfNeeded(fields.ciudad, report);
      return false;
    }
    setError(fields.ciudad, "");
    return true;
  }

  function validateFavoriteIfSelected(report) {
    const country = fields.pais.value;
    const city = fields.ciudad.value;
    const fav = fields.favorita.value;

    if (!fav) {
      setError(fields.favorita, "");
      return true;
    }

    const allowed = getFavoritesFor(country, city).map((f) => f.value);
    if (!allowed.includes(fav)) {
      setError(fields.favorita, "La ubicación favorita no corresponde al país y ciudad seleccionados.");
      reportIfNeeded(fields.favorita, report);
      return false;
    }

    setError(fields.favorita, "");
    return true;
  }

  function validatePhone(report) {
    const value = fields.telefono.value.trim();
    if (!value) {
      setError(fields.telefono, "El teléfono es obligatorio.");
      reportIfNeeded(fields.telefono, report);
      return false;
    }
    if (!isValidPhoneIntl(value)) {
      setError(fields.telefono, "Usa formato internacional: +[código país][10 dígitos].");
      reportIfNeeded(fields.telefono, report);
      return false;
    }
    setError(fields.telefono, "");
    return true;
  }

  function validateHowDidYouKnow(report) {
    if (!fields.como.value) {
      setError(fields.como, "Selecciona una opción.");
      reportIfNeeded(fields.como, report);
      return false;
    }
    setError(fields.como, "");
    return true;
  }

  function validateDietaryRules(report) {
    const isSinRestricciones = fields.sinRestricciones.checked;
    const anyOtherChecked = fields.vegano.checked || fields.sinGluten.checked || fields.otros.checked;

    if (isSinRestricciones && anyOtherChecked) {
      setError(fields.sinRestricciones, "No puedes seleccionar 'Sin restricciones' junto con otra preferencia.");
      reportIfNeeded(fields.sinRestricciones, report);
      return false;
    }

    setError(fields.sinRestricciones, "");
    return true;
  }

  function validateTerms(report) {
    if (!fields.terminos.checked) {
      setError(fields.terminos, "Debes aceptar los términos del programa.");
      reportIfNeeded(fields.terminos, report);
      return false;
    }
    setError(fields.terminos, "");
    return true;
  }

  function validateStep(step, report) {
    const validators = stepFieldValidators[step] || [];
    for (const validator of validators) {
      if (!validator(report)) return false;
    }
    return true;
  }

  function validateAllSteps(report) {
    for (let step = 1; step <= TOTAL_STEPS; step += 1) {
      if (!validateStep(step, report)) return false;
    }
    return true;
  }

  function updateProgress(step) {
    progressItems.forEach((item, idx) => {
      const n = idx + 1;
      const circle = item.querySelector("span:first-child");
      const text = item.querySelector("span:last-child");

      item.removeAttribute("aria-current");

      if (n < step) {
        circle.className = "flex h-8 w-8 items-center justify-center rounded-full bg-red-600 text-sm font-semibold text-white";
        text.className = "text-sm font-medium text-gray-800";
      } else if (n === step) {
        item.setAttribute("aria-current", "step");
        circle.className = "flex h-8 w-8 items-center justify-center rounded-full bg-red-600 text-sm font-semibold text-white";
        text.className = "text-sm font-medium text-gray-800";
      } else {
        circle.className = "flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-sm font-semibold text-gray-700";
        text.className = "text-sm font-medium text-gray-500";
      }
    });
  }

  function renderStep(step) {
    stepPanels.forEach((panel) => {
      const panelStep = Number(panel.getAttribute("data-step-panel"));
      panel.classList.toggle("hidden", panelStep !== step);
    });

    prevBtn.classList.toggle("hidden", step === 1);
    nextBtn.classList.toggle("hidden", step === TOTAL_STEPS);
    submitBtn.classList.toggle("hidden", step !== TOTAL_STEPS);

    updateProgress(step);
  }

  function syncCitiesByCountry() {
    const country = fields.pais.value;
    const cities = getCitiesForCountry(country);

    renderOptions(fields.ciudad, "Selecciona tu ciudad", cities);
    fields.ciudad.disabled = cities.length === 0;

    renderOptions(fields.favorita, "Selecciona tu Brasaland favorito", []);
    fields.favorita.disabled = true;

    setError(fields.ciudad, "");
    setError(fields.favorita, "");
  }

  function syncFavoritesByCountryCity() {
    const country = fields.pais.value;
    const city = fields.ciudad.value;
    const favorites = getFavoritesFor(country, city);

    renderOptions(fields.favorita, "Selecciona tu Brasaland favorito", favorites);
    fields.favorita.disabled = favorites.length === 0;

    setError(fields.favorita, "");
  }

  function syncPhonePrefixByCountry() {
    const prefix = phonePrefixByCountry[fields.pais.value];
    if (!prefix) return;

    const raw = fields.telefono.value.trim();

    if (!raw) {
      fields.telefono.value = prefix;
      return;
    }

    if (/^\+\d{1,4}$/.test(raw)) {
      fields.telefono.value = prefix;
    }
  }

  function enforceDietaryExclusivity(changed) {
    if (changed === fields.sinRestricciones && fields.sinRestricciones.checked) {
      fields.vegano.checked = false;
      fields.sinGluten.checked = false;
      fields.otros.checked = false;
    }

    if (
      (changed === fields.vegano || changed === fields.sinGluten || changed === fields.otros) &&
      (fields.vegano.checked || fields.sinGluten.checked || fields.otros.checked)
    ) {
      fields.sinRestricciones.checked = false;
    }

    validateDietaryRules(false);
  }

  nextBtn.addEventListener("click", () => {
    const ok = validateStep(currentStep, true);
    if (!ok) return;
    currentStep = Math.min(currentStep + 1, TOTAL_STEPS);
    renderStep(currentStep);
  });

  prevBtn.addEventListener("click", () => {
    currentStep = Math.max(currentStep - 1, 1);
    renderStep(currentStep);
  });

  form.addEventListener("submit", (event) => {
    const valid = validateAllSteps(true);
    if (!valid) {
      event.preventDefault();
      for (let step = 1; step <= TOTAL_STEPS; step += 1) {
        if (!validateStep(step, false)) {
          currentStep = step;
          renderStep(currentStep);
          break;
        }
      }
      return;
    }
  });

  fields.name.addEventListener("blur", () => validateName(false));
  fields.email.addEventListener("blur", () => validateEmail(false));
  fields.birthYear.addEventListener("change", () => validateBirthDate(false));
  fields.telefono.addEventListener("blur", () => validatePhone(false));
  fields.como.addEventListener("change", () => validateHowDidYouKnow(false));
  fields.terminos.addEventListener("change", () => validateTerms(false));

  fields.pais.addEventListener("change", () => {
    syncCitiesByCountry();
    syncPhonePrefixByCountry();
    validateCountry(false);
  });

  fields.ciudad.addEventListener("change", () => {
    syncFavoritesByCountryCity();
    validateCity(false);
  });

  fields.favorita.addEventListener("change", () => validateFavoriteIfSelected(false));

  [fields.sinRestricciones, fields.vegano, fields.sinGluten, fields.otros].forEach((cb) => {
    cb.addEventListener("change", (e) => enforceDietaryExclusivity(e.target));
  });

  syncCitiesByCountry();
  fields.ofertas.checked = false;
  renderStep(currentStep);
});