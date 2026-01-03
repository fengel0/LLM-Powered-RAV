// /static/js/modal.js

// Utility: create modal structure dynamically if missing
function ensureNodesModal() {
  let modal = document.getElementById("nodesModal");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "nodesModal";
  modal.className =
    "hidden fixed inset-0 bg-black bg-opacity-50 items-center justify-center z-50";

  const inner = document.createElement("div");
  inner.className =
    "bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-2xl w-full";
  inner.innerHTML = `
    <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">
      Retrieved Context
    </h2>
    <ul id="nodesList" class="text-gray-800 dark:text-gray-200 space-y-2 max-h-96 overflow-y-auto"></ul>
    <div class="text-right mt-6">
      <button id="closeModal"
              class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        Close
      </button>
    </div>
  `;
  modal.appendChild(inner);
  document.body.appendChild(modal);
  return modal;
}

// Show the modal with a list of nodes
export function showNodesModal(nodes) {
  const modal = ensureNodesModal();
  const nodesList = modal.querySelector("#nodesList");

  nodesList.innerHTML = "";

  nodes.forEach((node) => {
    const content =
      node?.text ?? node?.content ?? node?.document ?? JSON.stringify(node);
    const score =
      typeof node?.score === "number"
        ? node.score
        : typeof node?.similarity === "number"
          ? node.similarity
          : null;

    const li = document.createElement("li");
    li.className =
      "p-2 border rounded bg-gray-100 dark:bg-gray-700 whitespace-pre-wrap";
    li.textContent =
      score != null
        ? `${content} (score: ${Number(score).toFixed(2)})`
        : `${content}`;
    nodesList.appendChild(li);
  });

  modal.classList.remove("hidden");
  modal.classList.add("flex");
}

export function hideNodesModal() {
  const modal = document.getElementById("nodesModal");
  if (!modal) return;
  modal.classList.remove("flex");
  modal.classList.add("hidden");
}

/**
 * Initialize modal click handlers once (safe across reloads)
 */
export function initNodesModal() {
  if (document.__nodesModalInit) return;
  document.__nodesModalInit = true;

  document.addEventListener("click", (e) => {
    const t = e.target;
    if (t.id === "closeModal" || t.id === "nodesModal") {
      hideNodesModal();
    }
  });
}
