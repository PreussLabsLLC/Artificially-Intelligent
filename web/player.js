"use strict";

const audio = document.querySelector("#soundtrack");
const stage = document.querySelector("#stage");
const play = document.querySelector("#play");
const restart = document.querySelector("#restart");
const seek = document.querySelector("#seek");
const time = document.querySelector("#time");
const status = document.querySelector("#status");
const caption = document.querySelector("#caption");
const language = document.querySelector("#subtitle-language");

function formatTime(seconds) {
  const whole = Math.floor(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

function changeAt(changes, frame) {
  let low = 0;
  let high = changes.length;
  while (high - low > 1) {
    const mid = Math.floor((low + high) / 2);
    if (changes[mid][0] <= frame) low = mid;
    else high = mid;
  }
  return low;
}

function startPlayer(episode) {
  const {fps, frames, changes, layers, title} = episode;
  const duration = frames / fps;
  let currentChange = -1;
  let request = 0;
  const tracks = episode.subtitles ?? [];

  for (const {code, label} of tracks) language.add(new Option(label, code));
  document.querySelector("#captions").hidden = tracks.length === 0;
  language.addEventListener("change", () => {
    caption.lang = language.value === "es" ? "es-419" : language.value;
    draw();
  });

  function draw() {
    const seconds = Math.min(audio.currentTime, duration);
    const frame = Math.min(frames - 1, Math.floor(seconds * fps));
    const change = changeAt(changes, frame);
    if (change !== currentChange) {
      stage.innerHTML = changes[change][1].map(id => layers[id]).join("");
      currentChange = change;
    }
    const track = tracks.find(track => track.code === language.value);
    const cue = track?.cues.find(([start, end]) => start <= seconds && seconds < end);
    const text = cue?.[2] ?? "";
    if (caption.textContent !== text) caption.textContent = text;
    caption.hidden = !text;
    seek.value = seconds;
    seek.setAttribute("aria-valuetext", formatTime(seconds));
    time.value = `${formatTime(seconds)} / ${formatTime(duration)}`;
  }

  function tick() {
    draw();
    request = audio.paused || audio.ended ? 0 : requestAnimationFrame(tick);
  }

  function updateControls() {
    play.textContent = audio.paused || audio.ended ? "Play" : "Pause";
    cancelAnimationFrame(request);
    tick();
  }

  play.addEventListener("click", async () => {
    if (!audio.paused && !audio.ended) {
      audio.pause();
      return;
    }
    if (audio.ended) audio.currentTime = 0;
    try {
      await audio.play();
      status.textContent = "";
    } catch {
      status.textContent = "The episode audio could not start.";
    }
  });
  restart.addEventListener("click", () => {
    audio.currentTime = 0;
    draw();
  });
  seek.addEventListener("input", () => {
    audio.currentTime = Number(seek.value);
    draw();
  });
  for (const event of ["play", "pause", "ended"]) audio.addEventListener(event, updateControls);
  for (const event of ["seeking", "seeked", "timeupdate"]) audio.addEventListener(event, draw);

  function ready() {
    status.textContent = "";
    play.disabled = restart.disabled = seek.disabled = false;
  }
  seek.max = duration;
  document.querySelector("#episode-title").textContent = title;
  document.title = `${title} · Artificially Intelligent`;
  if (audio.error) status.textContent = "The episode audio could not be loaded.";
  else if (audio.readyState >= HTMLMediaElement.HAVE_METADATA) ready();
  else audio.addEventListener("loadedmetadata", ready, {once: true});
  draw();
}

audio.addEventListener("error", () => {
  play.disabled = restart.disabled = seek.disabled = true;
  status.textContent = "The episode audio could not be loaded.";
});

async function loadPlayer() {
  try {
    const episode = globalThis.episodeData;
    if (!episode) throw new Error("Missing episode data");
    if (episode.version !== 1) throw new Error("Unsupported episode data");
    startPlayer(episode);
  } catch {
    status.textContent = "The episode data could not be loaded.";
    return;
  }

  if (location.protocol === "file:") {
    audio.src = "./episode.m4a";
    return;
  }

  // Load the short soundtrack once so seeking also works on static servers without byte ranges.
  try {
    const response = await fetch("./episode.m4a", {cache: "no-cache"});
    if (!response.ok) throw new Error("Missing episode audio");
    audio.src = URL.createObjectURL(await response.blob());
  } catch {
    status.textContent = "The episode audio could not be loaded.";
  }
}

loadPlayer();
