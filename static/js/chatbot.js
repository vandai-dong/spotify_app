// Chat widget: posts to the assistant endpoint. All text is inserted with
// textContent, so neither user input nor model output can inject HTML.
(function () {
  const input = document.getElementById("userInput");
  const button = document.getElementById("submit");
  const list = document.querySelector("#chat ul");
  const url = document.getElementById("chat").dataset.url;
  const csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;

  function addMessage(text, { mine = false, error = false, label = "" } = {}) {
    const li = document.createElement("li");
    li.className = "list-group-item" + (error ? " text-danger" : "");
    if (mine) li.style.textAlign = "right";
    if (label) {
      const b = document.createElement("b");
      b.textContent = label + " ";
      li.appendChild(b);
    }
    li.appendChild(document.createTextNode(text));
    list.appendChild(li);
    li.scrollIntoView({ block: "end" });
  }

  async function submit() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, { mine: true });
    input.value = "";
    button.disabled = true;
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ userInput: text }),
      });
      const data = await response.json();
      if (response.ok) addMessage(data.completion, { label: "Answer:" });
      else addMessage(data.error || "Could not get a response.", { error: true, label: "Error:" });
    } catch (e) {
      addMessage("Could not get a response.", { error: true, label: "Error:" });
    } finally {
      button.disabled = false;
      input.focus();
    }
  }

  button.addEventListener("click", submit);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submit();
    }
  });
})();
