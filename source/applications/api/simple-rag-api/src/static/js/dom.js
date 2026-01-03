// /static/js/dom.js
export const sidebar = document.getElementById("sidebar");
export const menuToggle = document.getElementById("menuToggle");
export const convoListDiv = document.getElementById("convoList");
export const newChatBtn = document.getElementById("newChatBtn");
export const apiUrlSelect = document.getElementById("apiUrlSelect");
export const modelSelect = document.getElementById("modelSelect");
export const fetchModelsBtn = document.getElementById("fetchModels");
export const messagesDiv = document.getElementById("messages");
export const statusDiv = document.getElementById("status");
export const messageInput = document.getElementById("messageInput");
export const sendButton = document.getElementById("sendButton");
export const streamToggle = document.getElementById("streamToggle");
export const conversationTitleInput = document.getElementById("conversationTitle");

export const nodesModal = document.getElementById("nodesModal");
export const nodesList = document.getElementById("nodesList");
export const closeModal = document.getElementById("closeModal");

export function updateStatus(text) {
  statusDiv.textContent = text;
}
