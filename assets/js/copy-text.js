(function () {
  "use strict";

  // Copy buttons stay hidden until the Clipboard API is available.
  if (!navigator.clipboard || !navigator.clipboard.writeText) return;

  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    var target = document.getElementById(button.getAttribute("data-copy-target"));
    if (!target) return;
    var label = button.textContent;
    var timer = null;
    button.hidden = false;
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(target.textContent.trim()).then(function () {
        button.textContent = button.getAttribute("data-copied-label") || label;
        button.classList.add("is-copied");
        clearTimeout(timer);
        timer = setTimeout(function () {
          button.textContent = label;
          button.classList.remove("is-copied");
        }, 2000);
      });
    });
  });
})();
