// /static/js/state.js
export let allData = {
  conversations: [], // Array of { id, title, messages: [ { role, content, nodes? } ] }
  currentId: null    // The 'id' of the currently open conversation
};

export function setAllData(next) {
  allData = next;
}

export function createConversationObject(title) {
  return {
    id: Date.now().toString(),
    title: title || "Untitled",
    messages: []
  };
}

export function getCurrentConversation() {
  return allData.conversations.find((c) => c.id === allData.currentId);
}

export function updateConversationTitle(id, newTitle) {
  const convo = allData.conversations.find((c) => c.id === id);
  if (convo) {
    convo.title = newTitle;
    saveAllData();
  }
}

export function saveAllData() {
  try {
    localStorage.setItem("chatbot_data", JSON.stringify(allData));
  } catch (e) {
    console.warn("Could not save to localStorage:", e);
  }
}

export function loadAllData() {
  const stored = localStorage.getItem("chatbot_data");
  if (!stored) {
    const firstConvo = createConversationObject("New Conversation");
    setAllData({
      conversations: [firstConvo],
      currentId: firstConvo.id
    });
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
      setAllData(parsed);
    } else {
      const firstConvo = createConversationObject("New Conversation");
      setAllData({
        conversations: [firstConvo],
        currentId: firstConvo.id
      });
      saveAllData();
    }
  } catch (e) {
    console.warn("Failed to parse chatbot_data:", e);
    const firstConvo = createConversationObject("New Conversation");
    setAllData({
      conversations: [firstConvo],
      currentId: firstConvo.id
    });
    saveAllData();
  }
}
