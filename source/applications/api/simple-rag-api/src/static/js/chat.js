// /static/js/chat.js
import { apiUrlSelect, modelSelect, fetchModelsBtn, messagesDiv, messageInput, sendButton, streamToggle } from './dom.js';
import { updateStatus } from './dom.js';
import { getCurrentConversation, saveAllData, allData } from './state.js';
import { appendMessageBubble, updateStreamingBubble, finalizeStreamingBubble } from './render.js';
import { fetchModels, fetchContextById, chatUrl } from './api.js';

export async function onFetchModels() {
  const apiUrl = apiUrlSelect.value.trim();
  if (!apiUrl) {
    updateStatus("Please select API URL and enter API Key");
    return;
  }

  fetchModelsBtn.disabled = true;
  updateStatus("Fetching models...");
  try {
    const data = await fetchModels(apiUrl);
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

export async function sendMessage() {
  await sendMessageStreaming();
}

async function sendMessageStreaming() {
  const text = messageInput.value.trim();
  const apiUrl = apiUrlSelect.value.trim();
  const model = modelSelect.value;
  const configId = configSelect?.value?.trim() || null;
  const projectId = projectSelect?.value?.trim() || null;

  if (!text || !apiUrl || !model) {
    updateStatus("Please fill in all fields");
    return;
  }

  messageInput.value = "";
  sendButton.disabled = true;

  // record user message in state
  const convo = getCurrentConversation();
  if (!convo) return;
  convo.messages.push({ role: "user", content: text, nodes: null });
  saveAllData();

  // add user bubble
  appendMessageBubble("user", text, false);
  updateStatus("Streaming...");

  // assistant streaming bubble
  const streamingHandles = appendMessageBubble("assistant", "", true);
  let streamingBuffer = "";
  let contextId = null;
  let assistantNodes = [];

  try {
    const response = await fetch(chatUrl(apiUrl), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: getCurrentConversation().messages,
        max_tokens: 1000,
        temperature: 0.7,
        stream: true,
        config_id: configId,
        project_id: projectId,
      }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    contextId = response.headers.get("X-Context-Id");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6);
        if (data === "[DONE]") break;

        try {
          const parsed = JSON.parse(data);
          const contentDelta = parsed.choices?.[0]?.delta?.content;
          if (contentDelta) {
            streamingBuffer += contentDelta;
            updateStreamingBubble(streamingHandles.contentDiv, streamingBuffer);
          }
        } catch {
          // ignore malformed line
        }
      }
    }

    if (contextId) {
      try {
        assistantNodes = await fetchContextById(apiUrl, contextId);
        console.log(assistantNodes)
      } catch (e) {
        console.warn("Failed to fetch context:", e);
      }
    }

    finalizeStreamingBubble(streamingHandles, streamingBuffer, assistantNodes);

    // persist assistant message
    const convo2 = getCurrentConversation();
    if (convo2) {
      convo2.messages.push({
        role: "assistant",
        content: streamingBuffer,
        nodes: Array.isArray(assistantNodes) && assistantNodes.length ? assistantNodes : null,
      });
      console.log(convo2)
      saveAllData();
    }

    updateStatus("Ready");
  } catch (error) {
    // remove streaming bubble
    streamingHandles?.wrapper?.remove?.();

    // rollback last user message
    const c = getCurrentConversation();
    if (c) {
      c.messages = c.messages.slice(0, -1);
      saveAllData();
    }

    updateStatus(`Error: ${error.message}`);
  } finally {
    sendButton.disabled = false;
  }
}

async function sendMessageNonStreaming() {
  const text = messageInput.value.trim();
  const apiUrl = apiUrlSelect.value.trim();
  const model = modelSelect.value;

  if (!text || !apiUrl || !model) {
    updateStatus("Please fill in all fields");
    return;
  }

  messageInput.value = "";
  sendButton.disabled = true;

  // record + show user
  const convo = getCurrentConversation();
  if (!convo) return;
  convo.messages.push({ role: "user", content: text, nodes: null });
  saveAllData();
  appendMessageBubble("user", text, false);
  updateStatus("Sending...");

  try {
    const response = await fetch(chatUrl(apiUrl), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: getCurrentConversation().messages,
        max_tokens: 1000,
        temperature: 0.7,
        stream: false,
      }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

    const contextId = response.headers.get("X-Context-Id");
    const data = await response.json();
    const assistantText = data.choices?.[0]?.message?.content ?? "";

    let assistantNodes = [];
    if (contextId) {
      try {
        assistantNodes = await fetchContextById(apiUrl, contextId);
      } catch (e) {
        console.warn("Failed to fetch context:", e);
      }
    }

    // persist + render assistant
    const convo2 = getCurrentConversation();
    if (convo2) {
      convo2.messages.push({
        role: "assistant",
        content: assistantText,
        nodes: assistantNodes?.length ? assistantNodes : null,
      });
      saveAllData();
    }

    appendMessageBubble("assistant", assistantText, false);
    updateStatus("Ready");
  } catch (error) {
    // rollback last user msg
    const c = getCurrentConversation();
    if (c) {
      c.messages = c.messages.slice(0, -1);
      saveAllData();
    }
    updateStatus(`Error: ${error.message}`);
  } finally {
    sendButton.disabled = false;
  }
}
