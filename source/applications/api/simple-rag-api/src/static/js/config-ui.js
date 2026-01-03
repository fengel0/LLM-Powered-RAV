// /static/js/config-ui.js

// Internal state
const configMap = new Map();
const configNameCounts = new Map();

// Expose getters for other modules (optional)
export function getCurrentConfigId() {
  const sel = document.getElementById('configSelect');
  return sel?.value ?? null;
}
export function getCurrentConfig() {
  return configMap.get(getCurrentConfigId()) ?? null;
}

/**
 * Initialize Config + Project UI:
 * - populate config & project dropdowns
 * - wire "Show Config" modal
 * - emit "config-changed" / "project-changed"
 */
export function initConfigUI() {
  // ---------- CONFIGS ----------
  const configSelect = document.getElementById('configSelect');
  if (Array.isArray(window.APP_CONFIGS)) {
    window.APP_CONFIGS.forEach(entry => {
      if (entry && typeof entry === 'object') {
        Object.entries(entry).forEach(([id, cfg]) => {
          configMap.set(id, cfg);
          const nm = (cfg?.name ?? '').trim() || id;
          configNameCounts.set(nm, (configNameCounts.get(nm) || 0) + 1);
        });
      }
    });
  }

  if (configSelect) {
    if (configMap.size === 0) {
      configSelect.innerHTML = `<option value="" disabled selected>No configs</option>`;
    } else {
      const options = Array.from(configMap.entries()).map(([id, cfg]) => {
        const rawName = (cfg?.name ?? '').trim() || id;
        const needsDisamb = (configNameCounts.get(rawName) || 0) > 1;
        const label = needsDisamb ? `${rawName} (${id})` : rawName;
        return `<option value="${id}">${label}</option>`;
      });
      configSelect.innerHTML = options.join('');
    }
  }

  // Emit events on change so the rest of the app can react
  configSelect?.addEventListener('change', () => {
    document.dispatchEvent(new CustomEvent('config-changed', {
      detail: { id: getCurrentConfigId(), config: getCurrentConfig() }
    }));
  });

  // ---------- PROJECTS ----------
  const projectSelect = document.getElementById('projectSelect');
  if (projectSelect && Array.isArray(window.PROJECTS)) {
    const options = window.PROJECTS.map(tuple => {
      const id = Array.isArray(tuple) ? tuple[0] : (tuple?.id ?? '');
      const name = Array.isArray(tuple) ? tuple[1] : (tuple?.name ?? '');
      const label = (name && name.trim().length > 0) ? name : id;
      return `<option value="${id}">${label}</option>`;
    });
    projectSelect.innerHTML = options.join('');
  }

  projectSelect?.addEventListener('change', () => {
    const id = projectSelect.value || null;
    document.dispatchEvent(new CustomEvent('project-changed', { detail: { id } }));
  });

  // ---------- CONFIG MODAL ----------
  const showConfigBtn = document.getElementById('showConfigBtn');
  const configOverlay = document.getElementById('configOverlay');
  const closeConfig = document.getElementById('closeConfig');
  const configContent = document.getElementById('configContent');

  if (showConfigBtn && configOverlay && closeConfig && configContent) {
    showConfigBtn.addEventListener('click', () => {
      const id = getCurrentConfigId();
      const cfg = getCurrentConfig();
      if (!id || !cfg) {
        configContent.textContent = 'No config selected or config not found.';
      } else {
        const payload = { id, name: cfg.name ?? id, ...cfg };
        configContent.textContent = JSON.stringify(payload, null, 2);
      }
      configOverlay.classList.remove('hidden');
      configOverlay.classList.add('flex');
    });

    closeConfig.addEventListener('click', () => {
      configOverlay.classList.add('hidden');
      configOverlay.classList.remove('flex');
    });

    configOverlay.addEventListener('click', (e) => {
      if (e.target === configOverlay) {
        configOverlay.classList.add('hidden');
        configOverlay.classList.remove('flex');
      }
    });
  }
}
