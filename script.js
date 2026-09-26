let isToggled = false;
const initialMsg = "2026-09-26 13:44:23,now is html~";
const toggledMsg = ">>>> hai js";
const initialBtn = "clik me 🐱";
const toggledBtn = "reset me 🔄";

function toggleText() {
  isToggled = !isToggled;
  document.getElementById("msg").textContent = isToggled
    ? toggledMsg
    : initialMsg;
  document.getElementById("btn").textContent = isToggled
    ? toggledBtn
    : initialBtn;
}

window.toggleText = toggleText;
