// /static/js/events.js
import {
  sidebar, menuToggle, newChatBtn, fetchModelsBtn, sendButton,
  messageInput, conversationTitleInput, apiUrlSelect
} from './dom.js';

import { updateStatus } from './dom.js';
import { allData, createConversationObject, saveAllData, getCurrentConversation, updateConversationTitle } from './state.js';
import { renderConversationList, renderChatTitle, renderChatMessages } from './render.js';
import { onFetchModels, sendMessage } from './chat.js';

export function wireEvents() {
  menuToggle.addEventListener("click", () => {
    sidebar.classList.toggle("-translate-x-full");
  });

  newChatBtn.addEventListener("click", () => {
    const newConvo = createConversationObject("New Conversation");
    allData.conversations.unshift(newConvo);
    allData.currentId = newConvo.id;
    saveAllData();
    renderConversationList(handleSwitch, handleDelete, handleRename);
    renderChatTitle();
    renderChatMessages(updateStatus);
  });

  fetchModelsBtn.addEventListener("click", onFetchModels);

  sendButton.addEventListener("click", sendMessage);
  messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !sendButton.disabled) sendMessage();
  });

  conversationTitleInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      conversationTitleInput.blur();
    }
  });

  conversationTitleInput.addEventListener("blur", () => {
    const newName = conversationTitleInput.value.trim() || "Untitled";
    updateConversationTitle(allData.currentId, newName);
    renderConversationList(handleSwitch, handleDelete, handleRename);
    renderChatTitle();
  });
}

// Sidebar callbacks
export function handleSwitch(newId) {
  allData.currentId = newId;
  saveAllData();
  renderConversationList(handleSwitch, handleDelete, handleRename);
  renderChatTitle();
  renderChatMessages(updateStatus);
}

export function handleDelete(id) {
  const toDelete = allData.conversations.find((c) => c.id === id);
  if (!toDelete) return;

  if (!confirm(`Delete “${toDelete.title}”? This cannot be undone.`)) return;

  allData.conversations = allData.conversations.filter((c) => c.id !== id);

  if (allData.currentId === id) {
    if (allData.conversations.length > 0) {
      allData.currentId = allData.conversations[0].id;
    } else {
      const fresh = createConversationObject("New Conversation");
      allData.conversations = [fresh];
      allData.currentId = fresh.id;
    }
  }

  saveAllData();
  renderConversationList(handleSwitch, handleDelete, handleRename);
  renderChatTitle();
  renderChatMessages(updateStatus);
}

export function handleRename(id, newTitle) {
  updateConversationTitle(id, newTitle);
  renderConversationList(handleSwitch, handleDelete, handleRename);
  renderChatTitle();
}
