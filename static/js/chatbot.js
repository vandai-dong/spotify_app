// Chat widget. Everything from the server (including model text and song titles) is inserted with
// textContent / DOM APIs, never as HTML. The conversation history lives here and is sent with each
// question; the server re-validates it.
(function () {
  const input = document.getElementById("userInput");
  const button = document.getElementById("submit");
  const list = document.querySelector("#chat ul");
  const chat = document.getElementById("chat");
  const csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;
  const history = []; // {role, content}

  function post(url, params) {
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(params),
    });
  }

  function addItem(build) {
    const li = document.createElement("li");
    li.className = "list-group-item";
    build(li);
    list.appendChild(li);
    li.scrollIntoView({ block: "end" });
    return li;
  }

  function addMessage(text, { mine = false, error = false, label = "" } = {}) {
    addItem((li) => {
      if (error) li.classList.add("text-danger");
      if (mine) li.style.textAlign = "right";
      if (label) {
        const b = document.createElement("b");
        b.textContent = label + " ";
        li.appendChild(b);
      }
      li.appendChild(document.createTextNode(text));
    });
  }

  function songChip(song, playlists) {
    const row = document.createElement("div");
    row.className = "d-flex align-items-center gap-2 py-1 song-chip";

    const link = document.createElement("a");
    link.textContent = song.title;
    if (/^\/songs\/\d+$/.test(song.url)) link.href = song.url;
    const artist = document.createElement("span");
    artist.className = "text-secondary small";
    artist.textContent = song.artist;

    const like = document.createElement("button");
    like.type = "button";
    like.className = "icon-button" + (song.liked ? " active" : "");
    like.setAttribute("aria-label", "Like " + song.title);
    const heart = document.createElement("i");
    heart.className = (song.liked ? "fa-solid" : "fa-regular") + " fa-heart";
    like.appendChild(heart);
    like.addEventListener("click", async () => {
      const response = await post("/favorites/toggle/" + song.id, {});
      if (!response.ok) return;
      song.liked = !song.liked;
      like.classList.toggle("active", song.liked);
      heart.className = (song.liked ? "fa-solid" : "fa-regular") + " fa-heart";
    });

    row.append(link, artist, like);

    if (playlists.length) {
      const select = document.createElement("select");
      select.className = "form-select form-select-sm w-auto";
      select.setAttribute("aria-label", "Add " + song.title + " to a playlist");
      const placeholder = new Option("Add to playlist…", "");
      select.add(placeholder);
      playlists.forEach((p) => select.add(new Option(p.name, String(p.id))));
      select.addEventListener("change", async () => {
        if (!select.value) return;
        const response = await post("/playlists/" + select.value + "/add", { song_id: song.id });
        placeholder.textContent = response.ok ? "Added ✓" : "Could not add";
        select.value = "";
      });
      row.appendChild(select);
    }
    return row;
  }

  function addAnswer(data) {
    addItem((li) => {
      const b = document.createElement("b");
      b.textContent = "Answer: ";
      li.appendChild(b);
      li.appendChild(document.createTextNode(data.completion));
      (data.songs || []).forEach((song) => li.appendChild(songChip(song, data.playlists || [])));
    });
  }

  async function submit() {
    const text = input.value.trim();
    if (!text) return;
    addMessage(text, { mine: true });
    input.value = "";
    button.disabled = true;
    try {
      const response = await post(chat.dataset.url, { userInput: text, history: JSON.stringify(history) });
      const data = await response.json();
      if (response.ok) {
        addAnswer(data);
        history.push({ role: "user", content: text }, { role: "assistant", content: data.completion });
      } else {
        addMessage(data.error || "Could not get a response.", { error: true, label: "Error:" });
      }
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
