// ─────────────────────────────────────────────────────────────────────────
// GLOBAL STATE
// ─────────────────────────────────────────────────────────────────────────
let allData = {
  conversations: [], // Array of { id, title, messages: [ { role, content, nodes? } ] }
  currentId: null    // The 'id' of the currently open conversation
};

// DOM references
const sidebar = document.getElementById("sidebar");
const menuToggle = document.getElementById("menuToggle");
const convoListDiv = document.getElementById("convoList");
const newChatBtn = document.getElementById("newChatBtn");
const apiUrlSelect = document.getElementById("apiUrlSelect");
const modelSelect = document.getElementById("modelSelect");
const fetchModelsBtn = document.getElementById("fetchModels");
const messagesDiv = document.getElementById("messages");
const statusDiv = document.getElementById("status");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const streamToggle = document.getElementById("streamToggle");
const conversationTitleInput = document.getElementById("conversationTitle");
// NEW: Collection select
const collectionSelectAPI = document.getElementById("collectionSelect");

// Modal references
const nodesModal = document.getElementById("nodesModal");
const nodesList = document.getElementById("nodesList");
const closeModal = document.getElementById("closeModal");

let currentStreamingMessageWrapper = null;
let streamingBuffer = "";

// ─────────────────────────────────────────────────────────────────────────
// UTILITY FUNCTIONS FOR LOCAL STORAGE OF EVERY CONVERSATION
// ─────────────────────────────────────────────────────────────────────────
function saveAllData() {
  try {
    localStorage.setItem("chatbot_data", JSON.stringify(allData));
  } catch (e) {
    console.warn("Could not save to localStorage:", e);
  }
}

function loadAllData() {
  const stored = localStorage.getItem("chatbot_data");
  if (!stored) {
    const firstConvo = createConversationObject("New Conversation");
    allData = {
      conversations: [firstConvo],
      currentId: firstConvo.id
    };
    saveAllData();
    return;
  }
  try {
    const parsed = JSON.parse(stored);
    if (
      typeof parsed === "object" &&
      Array.isArray(parsed.conversations) &&
      parsed.conversations.length > 0 &&
      parsed.currentId !== undefined
    ) {
      allData = parsed;
    } else {
      const firstConvo = createConversationObject("New Conversation");
      allData = {
        conversations: [firstConvo],
        currentId: firstConvo.id
      };
      saveAllData();
    }
  } catch (e) {
    console.warn("Failed to parse chatbot_data:", e);
    const firstConvo = createConversationObject("New Conversation");
    allData = {
      conversations: [firstConvo],
      currentId: firstConvo.id
    };
    saveAllData();
  }
}

function createConversationObject(title) {
  return {
    id: Date.now().toString(),
    title: title || "Untitled",
    // Now each message can optionally have a .nodes array
    messages: []
  };
}

function getCurrentConversation() {
  return allData.conversations.find((c) => c.id === allData.currentId);
}

function updateConversationTitle(id, newTitle) {
  const convo = allData.conversations.find((c) => c.id === id);
  if (convo) {
    convo.title = newTitle;
    saveAllData();
    renderConversationList();
    if (allData.currentId === id) {
      renderChatTitle();
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────
// RENDER THE SIDEBAR CONVERSATION LIST
// ─────────────────────────────────────────────────────────────────────────
function renderConversationList() {
  convoListDiv.innerHTML = "";

  allData.conversations.forEach((convo) => {
    const item = document.createElement("div");
    item.classList.add("convo-item");
    if (convo.id === allData.currentId) {
      item.classList.add("active");
    }

    const flexContainer = document.createElement("div");
    flexContainer.style.display = "flex";
    flexContainer.style.alignItems = "center";
    flexContainer.style.justifyContent = "space-between";

    const titleDiv = document.createElement("div");
    titleDiv.classList.add("title");
    titleDiv.textContent = convo.title;
    titleDiv.style.cursor = "pointer";

    titleDiv.addEventListener("click", () => {
      if (convo.id !== allData.currentId) {
        switchConversation(convo.id);
      }
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
          updateConversationTitle(convo.id, newName);
        } else if (e.key === "Escape") {
          renderConversationList();
        }
      });

      input.addEventListener("blur", () => {
        renderConversationList();
      });
    });

    // Delete Button
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
      deleteConversation(convo.id);
    });

    flexContainer.appendChild(titleDiv);
    flexContainer.appendChild(deleteBtn);
    item.appendChild(flexContainer);
    convoListDiv.appendChild(item);
  });
}

// ─────────────────────────────────────────────────────────────────────────
// DELETE A CONVERSATION
// ─────────────────────────────────────────────────────────────────────────
function deleteConversation(id) {
  const toDelete = allData.conversations.find((c) => c.id === id);
  if (!toDelete) return;

  if (!confirm(`Delete “${toDelete.title}”? This cannot be undone.`)) {
    return;
  }

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
  renderConversationList();
  renderChatTitle();
  renderChatMessages();
}

// ─────────────────────────────────────────────────────────────────────────
function switchConversation(newId) {
  allData.currentId = newId;
  saveAllData();
  renderConversationList();
  renderChatTitle();
  renderChatMessages();
}

// ─────────────────────────────────────────────────────────────────────────
function createNewConversation() {
  const newConvo = createConversationObject("New Conversation");
  allData.conversations.unshift(newConvo);
  allData.currentId = newConvo.id;
  saveAllData();
  renderConversationList();
  renderChatTitle();
  renderChatMessages();
}

// ─────────────────────────────────────────────────────────────────────────
// RENDER THE CHAT PANEL
// ─────────────────────────────────────────────────────────────────────────
function renderChatMessages() {
  messagesDiv.innerHTML = "";
  const convo = getCurrentConversation();
  if (!convo) return;

  convo.messages.forEach((msg) => {
    const wrapper = document.createElement("div");
    if (msg.role === "user") {
      wrapper.className = "flex justify-end";
    } else {
      wrapper.className = "flex justify-start";
    }

    const bubble = document.createElement("div");
    bubble.className = `
      px-4 py-2 rounded-lg max-w-[70%]
      ${msg.role === "user"
        ? "bg-blue-600 text-white"
        : "bg-gray-300 text-gray-900"}
    `.trim();

    const label = document.createElement("div");
    label.className = `
      text-xs mb-1
      ${msg.role === "user"
        ? "text-gray-200"
        : "text-gray-500"}
    `.trim();
    label.textContent = msg.role.charAt(0).toUpperCase() + msg.role.slice(1);

    const contentDiv = document.createElement("div");
    contentDiv.textContent = msg.content;

    bubble.appendChild(label);
    bubble.appendChild(contentDiv);

    // If this is an assistant message with nodes, insert an ℹ️ icon
    if (msg.role === "assistant" && Array.isArray(msg.nodes) && msg.nodes.length > 0) {
      const infoIcon = document.createElement("span");
      infoIcon.innerHTML = "&#8505;"; // ℹ️
      infoIcon.className = "ml-2 align-text-top text-blue-500 cursor-pointer";
      infoIcon.title = "Show retrieved nodes";
      infoIcon.addEventListener("click", () => {
        showNodesModal(msg.nodes);
      });
      bubble.appendChild(infoIcon);
    }

    wrapper.appendChild(bubble);
    messagesDiv.appendChild(wrapper);
  });

  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  updateStatus("Ready");
}

// ─────────────────────────────────────────────────────────────────────────
function renderChatTitle() {
  const convo = getCurrentConversation();
  if (!convo) return;
  conversationTitleInput.value = convo.title;
}

// ─────────────────────────────────────────────────────────────────────────
function appendMessageToCurrent(role, content, isStreaming = false) {
  const convo = getCurrentConversation();
  if (!convo) return;

  if (!isStreaming) {
    convo.messages.push({ role, content, nodes: null });
    saveAllData();
  }

  const wrapper = document.createElement("div");
  if (role === "user") {
    wrapper.className = "flex justify-end";
  } else {
    wrapper.className = "flex justify-start";
  }

  const bubble = document.createElement("div");
  bubble.className = `
    px-4 py-2 rounded-lg max-w-[70%]
    ${role === "user"
      ? "bg-blue-600 text-white"
      : "bg-gray-300 text-gray-900"}
  `.trim();

  if (isStreaming) {
    bubble.classList.add("streaming");
  }

  const label = document.createElement("div");
  label.className = `
    text-xs mb-1
    ${role === "user"
      ? "text-gray-200"
      : "text-gray-500"}
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

// ─────────────────────────────────────────────────────────────────────────
function updateStreamingBubble(contentDiv, text) {
  contentDiv.textContent = text;
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// ─────────────────────────────────────────────────────────────────────────
function finalizeStreamingBubble(wrapperAndBubble, text, nodes) {
  const { bubble, contentDiv } = wrapperAndBubble;
  bubble.classList.remove("streaming");
  contentDiv.textContent = text;

  const convo = getCurrentConversation();
  if (!convo) return;
  const msgObj = {
    role: "assistant",
    content: text,
    nodes: Array.isArray(nodes) ? nodes : null
  };
  convo.messages.push(msgObj);
  saveAllData();

  if (Array.isArray(nodes) && nodes.length > 0) {
    const infoIcon = document.createElement("span");
    infoIcon.innerHTML = "&#8505;"; // ℹ️
    infoIcon.className = "ml-2 align-text-top text-blue-500 cursor-pointer";
    infoIcon.title = "Show retrieved nodes";
    infoIcon.addEventListener("click", () => {
      showNodesModal(nodes);
    });
    bubble.appendChild(infoIcon);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// SHOW / HIDE NODES MODAL  (robust to different node shapes)
// ─────────────────────────────────────────────────────────────────────────
function showNodesModal(nodes) {
  nodesList.innerHTML = "";

  nodes.forEach((node) => {
    const content =
      node?.text ?? node?.content ?? node?.document ?? JSON.stringify(node);
    const score =
      typeof node?.score === "number"
        ? node.score
        : (typeof node?.similarity === "number" ? node.similarity : null);

    const li = document.createElement("li");
    li.textContent = score != null
      ? `${content} (score: ${Number(score).toFixed(2)})`
      : `${content}`;
    nodesList.appendChild(li);
  });

  nodesModal.classList.remove("hidden");
  nodesModal.classList.add("flex");
}

closeModal.addEventListener("click", () => {
  nodesModal.classList.remove("flex");
  nodesModal.classList.add("hidden");
});

nodesModal.addEventListener("click", (e) => {
  if (e.target === nodesModal) {
    nodesModal.classList.remove("flex");
    nodesModal.classList.add("hidden");
  }
});

// ─────────────────────────────────────────────────────────────────────────
// FETCH AVAILABLE MODELS
// ─────────────────────────────────────────────────────────────────────────
async function fetchModels() {
  const apiUrl = apiUrlSelect.value.trim();

  if (!apiUrl) {
    updateStatus("Please select API URL and enter API Key");
    return;
  }

  fetchModelsBtn.disabled = true;
  updateStatus("Fetching models...");

  try {
    const modelsUrl = apiUrl.endsWith("/v1")
      ? `${apiUrl}/models`
      : `${apiUrl}/v1/models`;
    const response = await fetch(modelsUrl, {
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    modelSelect.innerHTML = "";
    data.data.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.id;
      option.textContent = model.id;
      modelSelect.appendChild(option);
    });

    updateStatus(`Loaded ${data.data.length} models`);
  } catch (error) {
    updateStatus(`Error fetching models: ${error.message}`);
  }

  fetchModelsBtn.disabled = false;
}

// ─────────────────────────────────────────────────────────────────────────
// NEW: Fetch projected nodes via context endpoint
// ─────────────────────────────────────────────────────────────────────────
async function fetchContextById(apiUrl, contextId) {
  if (!contextId) return [];
  const base = apiUrl.endsWith("/v1") ? apiUrl : `${apiUrl}/v1`;
  const url = `${base}/contexts/${encodeURIComponent(contextId)}`;

  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Context fetch failed (${res.status}): ${res.statusText}`);
  }
  const json = await res.json();
  return Array.isArray(json.data) ? json.data : [];
}

// ─────────────────────────────────────────────────────────────────────────
// SEND MESSAGE (STREAM) — reads X-Context-Id header and fetches context
// ─────────────────────────────────────────────────────────────────────────
async function sendMessageStreaming() {
  const text = messageInput.value.trim();
  const apiUrl = apiUrlSelect.value.trim();
  const model = modelSelect.value;
  // NEW: resolve selected collection id
  const selectedCollection =
    (collectionSelectAPI && collectionSelectAPI.value) ||
    window.SELECTED_COLLECTION_ID ||
    "";


  console.log(selectedCollection)
  console.log(collectionSelectAPI)
  console.log(collectionSelectAPI.value)
  if (!text || !apiUrl || !model || !selectedCollection) {
    updateStatus("Please fill in all fields (API URL, Model, Collection, Message).");
    return;
  }

  messageInput.value = "";
  sendButton.disabled = true;

  // User message
  appendMessageToCurrent("user", text);
  updateStatus("Streaming...");

  // Assistant streaming bubble
  const streamingHandles = appendMessageToCurrent("assistant", "", true);
  currentStreamingMessageWrapper = streamingHandles;
  streamingBuffer = "";

  let contextId = null;
  let assistantNodes = [];

  try {
    const chatUrl = apiUrl.endsWith("/v1")
      ? `${apiUrl}/chat/completions`
      : `${apiUrl}/v1/chat/completions`;

    const response = await fetch(chatUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: model,
        messages: getCurrentConversation().messages,
        max_tokens: 1000,
        temperature: 0.7,
        stream: true,
        // NEW: include collection in request
        collection: selectedCollection,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Read the context id from the response header (server also exposes it)
    contextId = response.headers.get("X-Context-Id");

    // Stream tokens
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let doneReading = false;
    while (!doneReading) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]") {
          doneReading = true;
          break;
        }

        let parsed;
        try {
          parsed = JSON.parse(data);
        } catch {
          continue;
        }

        const contentDelta = parsed.choices?.[0]?.delta?.content;
        if (contentDelta) {
          streamingBuffer += contentDelta;
          updateStreamingBubble(streamingHandles.contentDiv, streamingBuffer);
        }
      }
    }

    // Fetch nodes using the context id AFTER the stream finishes
    if (contextId) {
      try {
        assistantNodes = await fetchContextById(apiUrl, contextId);
      } catch (e) {
        console.warn("Failed to fetch context:", e);
      }
    }

    finalizeStreamingBubble(currentStreamingMessageWrapper, streamingBuffer, assistantNodes);
    updateStatus("Ready");
  } catch (error) {
    if (currentStreamingMessageWrapper) {
      const { bubble } = currentStreamingMessageWrapper;
      bubble.parentElement.remove();
    }
    updateStatus(`Error: ${error.message}`);

    const convo = getCurrentConversation();
    if (convo) {
      convo.messages.pop();
      saveAllData();
    }
  }

  sendButton.disabled = false;
}

// ─────────────────────────────────────────────────────────────────────────
// SEND MESSAGE (NON-STREAM) — reads X-Context-Id header and fetches context
// ─────────────────────────────────────────────────────────────────────────
async function sendMessageNonStreaming() {
  const text = messageInput.value.trim();
  const apiUrl = apiUrlSelect.value.trim();
  const model = modelSelect.value;
  // NEW: resolve selected collection id
  const selectedCollection =
    (collectionSelectAPI && collectionSelectAPI.value) ||
    window.SELECTED_COLLECTION_ID ||
    "";

  if (!text || !apiUrl || !model || !selectedCollection) {
    updateStatus("Please fill in all fields (API URL, Model, Collection, Message).");
    return;
  }

  messageInput.value = "";
  sendButton.disabled = true;

  appendMessageToCurrent("user", text);
  updateStatus("Sending...");

  try {
    const chatUrl = apiUrl.endsWith("/v1")
      ? `${apiUrl}/chat/completions`
      : `${apiUrl}/v1/chat/completions`;

    const response = await fetch(chatUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: model,
        messages: getCurrentConversation().messages,
        max_tokens: 1000,
        temperature: 0.7,
        stream: false,
        // NEW: include collection in request
        collection: selectedCollection,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    // Read context id from header
    const contextId = response.headers.get("X-Context-Id");

    const data = await response.json();
    const assistantText = data.choices?.[0]?.message?.content ?? "";

    // Try to fetch nodes with context id
    let assistantNodes = [];
    if (contextId) {
      try {
        assistantNodes = await fetchContextById(apiUrl, contextId);
      } catch (e) {
        console.warn("Failed to fetch context:", e);
      }
    }

    const convo = getCurrentConversation();
    if (convo) {
      convo.messages.push({
        role: "assistant",
        content: assistantText,
        nodes: assistantNodes?.length ? assistantNodes : null,
      });
      saveAllData();
      renderChatMessages();
    }

    updateStatus("Ready");
  } catch (error) {
    updateStatus(`Error: ${error.message}`);
    const convo = getCurrentConversation();
    if (convo) {
      convo.messages.pop(); // remove the user msg we just added
      saveAllData();
      renderChatMessages();
    }
  }

  sendButton.disabled = false;
}

async function sendMessage() {
  if (streamToggle.checked) {
    await sendMessageStreaming();
  } else {
    await sendMessageNonStreaming();
  }
}

// ─────────────────────────────────────────────────────────────────────────
// HANDLE EDITING THE CONVERSATION TITLE
// ─────────────────────────────────────────────────────────────────────────
conversationTitleInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    conversationTitleInput.blur();
  }
});

conversationTitleInput.addEventListener("blur", () => {
  const newName = conversationTitleInput.value.trim() || "Untitled";
  updateConversationTitle(allData.currentId, newName);
});

// ─────────────────────────────────────────────────────────────────────────
function updateStatus(text) {
  statusDiv.textContent = text;
}

// ─────────────────────────────────────────────────────────────────────────
menuToggle.addEventListener("click", () => {
  sidebar.classList.toggle("-translate-x-full");
});

// ─────────────────────────────────────────────────────────────────────────
newChatBtn.addEventListener("click", createNewConversation);
fetchModelsBtn.addEventListener("click", fetchModels);
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !sendButton.disabled) {
    sendMessage();
  }
});

// ─────────────────────────────────────────────────────────────────────────
// INITIALIZATION ON PAGE LOAD
// ─────────────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  // Populate API hosts
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

  // OPTIONAL: ensure we have a selected collection id if the template script didn't set it
  if (!window.SELECTED_COLLECTION_ID && window.PROJECTS && window.PROJECTS.length > 0) {
    // PROJECTS is [[id, name], ...]
    window.SELECTED_COLLECTION_ID = window.PROJECTS[0][0];
    if (collectionSelectAPI) collectionSelectAPI.value = window.SELECTED_COLLECTION_ID;
  }

  // Load & render existing conversations
  loadAllData();
  renderConversationList();
  renderChatTitle();
  renderChatMessages();

  // THEME TOGGLE LOGIC
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
    if (rootHtml.classList.contains("dark")) {
      localStorage.setItem("theme", "dark");
    } else {
      localStorage.setItem("theme", "light");
    }
    updateIconAndLabel();
  });

  updateIconAndLabel();
});
