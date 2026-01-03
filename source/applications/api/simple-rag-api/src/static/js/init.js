// /static/js/init.js
import { apiUrlSelect } from './dom.js';
import { loadAllData } from './state.js';
import { renderConversationList, renderChatTitle, renderChatMessages } from './render.js';
import { updateStatus } from './dom.js';
import { wireEvents, handleSwitch, handleDelete, handleRename } from './events.js';
import { initNodesModal } from './modal.js';
import { initConfigUI } from './config-ui.js';

window.addEventListener("DOMContentLoaded", () => {
  // Populate API hosts
  console.log(window.API_HOSTS)
  if (Array.isArray(window.API_HOSTS) && window.API_HOSTS.length > 0) {
    window.API_HOSTS.forEach((h) => {
      const opt = document.createElement("option");
      opt.value = h;
      opt.textContent = h;
      apiUrlSelect.appendChild(opt);
    });
    apiUrlSelect.value = window.API_HOSTS[0];
  } else {
    const fallback = "https://api.openai.com/v1";
    const opt = document.createElement("option");
    opt.value = fallback;
    opt.textContent = fallback;
    apiUrlSelect.appendChild(opt);
    apiUrlSelect.value = fallback;
  }

  // Load & initial render
  loadAllData();
  renderConversationList(handleSwitch, handleDelete, handleRename);
  renderChatTitle();
  renderChatMessages(updateStatus);
  initNodesModal();
  initConfigUI();

  // Theme toggle
  const themeToggleBtn = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const themeLabel = document.getElementById("themeLabel");
  const rootHtml = document.documentElement;

  const storedTheme = localStorage.getItem("theme");
  if (storedTheme === "dark") {
    rootHtml.classList.add("dark");
    themeLabel.textContent = "Dark Mode";
  } else {
    rootHtml.classList.remove("dark");
    themeLabel.textContent = "Light Mode";
  }

  function updateIconAndLabel() {
    if (rootHtml.classList.contains("dark")) {
      themeIcon.innerHTML = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 3v1m0 16v1m8.485-12.485l-.707.707M4.222 4.222l-.707.707M21 12h-1M4 12H3m16.485 4.485l-.707-.707M4.222 19.778l-.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z"
        />`;
      themeLabel.textContent = "Dark Mode";
    } else {
      themeIcon.innerHTML = `
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M12 3c.132 0 .263.003.394.008A9.001 9.001 0 1112 21v-2a7 7 0 100-14V3z"
        />`;
      themeLabel.textContent = "Light Mode";
    }
  }

  themeToggleBtn.addEventListener("click", () => {
    rootHtml.classList.toggle("dark");
    localStorage.setItem("theme", rootHtml.classList.contains("dark") ? "dark" : "light");
    updateIconAndLabel();
  });

  updateIconAndLabel();

  // Wire up all listeners last
  wireEvents();
});
