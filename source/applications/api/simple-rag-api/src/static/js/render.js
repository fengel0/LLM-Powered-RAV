// /static/js/render.js
import { convoListDiv, messagesDiv, conversationTitleInput } from './dom.js';
import { allData, getCurrentConversation, saveAllData } from './state.js';
import { showNodesModal } from './modal.js';

export function renderConversationList(onSwitch, onDelete, onRename) {
  convoListDiv.innerHTML = "";

  allData.conversations.forEach((convo) => {
    const item = document.createElement("div");
    item.classList.add("convo-item");
    if (convo.id === allData.currentId) item.classList.add("active");

    const flexContainer = document.createElement("div");
    flexContainer.style.display = "flex";
    flexContainer.style.alignItems = "center";
    flexContainer.style.justifyContent = "space-between";

    const titleDiv = document.createElement("div");
    titleDiv.classList.add("title");
    titleDiv.textContent = convo.title;
    titleDiv.style.cursor = "pointer";

    titleDiv.addEventListener("click", () => {
      if (convo.id !== allData.currentId) onSwitch(convo.id);
    });

    titleDiv.addEventListener("dblclick", () => {
      const input = document.createElement("input");
      input.type = "text";
      input.value = convo.title;
      input.classList.add("rename-input");
      flexContainer.replaceChild(input, titleDiv);
      input.focus();

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          const newName = input.value.trim() || "Untitled";
          onRename(convo.id, newName);
        } else if (e.key === "Escape") {
          renderConversationList(onSwitch, onDelete, onRename);
        }
      });

      input.addEventListener("blur", () => {
        renderConversationList(onSwitch, onDelete, onRename);
      });
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.textContent = "🗑";
    deleteBtn.title = "Delete conversation";
    deleteBtn.style.marginLeft = "8px";
    deleteBtn.style.background = "transparent";
    deleteBtn.style.border = "none";
    deleteBtn.style.cursor = "pointer";
    deleteBtn.style.fontSize = "0.9rem";

    deleteBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      onDelete(convo.id);
    });

    flexContainer.appendChild(titleDiv);
    flexContainer.appendChild(deleteBtn);
    item.appendChild(flexContainer);
    convoListDiv.appendChild(item);
  });
}

export function renderChatMessages(updateStatusFn) {
  messagesDiv.innerHTML = "";
  const convo = getCurrentConversation();
  if (!convo) return;

  convo.messages.forEach((msg) => {
    const wrapper = document.createElement("div");
    wrapper.className = msg.role === "user" ? "flex justify-end" : "flex justify-start";

    const bubble = document.createElement("div");
    bubble.className = `
      px-4 py-2 rounded-lg max-w-[70%]
      ${msg.role === "user" ? "bg-blue-600 text-white" : "bg-gray-300 text-gray-900"}
    `.trim();

    const label = document.createElement("div");
    label.className = `
      text-xs mb-1
      ${msg.role === "user" ? "text-gray-200" : "text-gray-500"}
    `.trim();
    label.textContent = msg.role.charAt(0).toUpperCase() + msg.role.slice(1);

    const contentDiv = document.createElement("div");
    contentDiv.textContent = msg.content;

    bubble.appendChild(label);
    bubble.appendChild(contentDiv);

    if (msg.role === "assistant" && Array.isArray(msg.nodes) && msg.nodes.length > 0) {
      const infoIcon = document.createElement("span");
      infoIcon.innerHTML = "&#8505;";
      infoIcon.className = "ml-2 align-text-top text-blue-500 cursor-pointer";
      infoIcon.title = "Show retrieved nodes";
      infoIcon.addEventListener("click", () => showNodesModal(msg.nodes));
      bubble.appendChild(infoIcon);
    }

    wrapper.appendChild(bubble);
    messagesDiv.appendChild(wrapper);
  });

  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  updateStatusFn("Ready");
}

export function renderChatTitle() {
  const convo = getCurrentConversation();
  if (!convo) return;
  conversationTitleInput.value = convo.title;
}

export function appendMessageBubble(role, content, isStreaming) {
  const wrapper = document.createElement("div");
  wrapper.className = role === "user" ? "flex justify-end" : "flex justify-start";

  const bubble = document.createElement("div");
  bubble.className = `
    px-4 py-2 rounded-lg max-w-[70%]
    ${role === "user" ? "bg-blue-600 text-white" : "bg-gray-300 text-gray-900"}
  `.trim();

  if (isStreaming) bubble.classList.add("streaming");

  const label = document.createElement("div");
  label.className = `
    text-xs mb-1
    ${role === "user" ? "text-gray-200" : "text-gray-500"}
  `.trim();
  label.textContent = role.charAt(0).toUpperCase() + role.slice(1);

  const contentDiv = document.createElement("div");
  contentDiv.textContent = isStreaming ? "" : content;

  bubble.appendChild(label);
  bubble.appendChild(contentDiv);
  wrapper.appendChild(bubble);
  messagesDiv.appendChild(wrapper);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;

  return isStreaming ? { wrapper, bubble, contentDiv } : wrapper;
}

export function updateStreamingBubble(contentDiv, text) {
  contentDiv.textContent = text;
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

export function finalizeStreamingBubble(wrapperAndBubble, text, nodes) {
  const { bubble, contentDiv } = wrapperAndBubble;
  bubble.classList.remove("streaming");
  contentDiv.textContent = text;

  if (Array.isArray(nodes) && nodes.length > 0) {
    const infoIcon = document.createElement("span");
    infoIcon.innerHTML = "&#8505;";
    infoIcon.className = "ml-2 align-text-top text-blue-500 cursor-pointer";
    infoIcon.title = "Show retrieved nodes";
    infoIcon.addEventListener("click", () => showNodesModal(nodes));
    bubble.appendChild(infoIcon);
  }
}
