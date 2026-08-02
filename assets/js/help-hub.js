(function () {
  "use strict";

  var topics = Array.prototype.slice.call(document.querySelectorAll(".help-topic"));
  if (!topics.length) return;
  var desktop = window.matchMedia("(min-width: 761px)");

  function sync() {
    topics.forEach(function (topic) {
      topic.open = desktop.matches || topic.hasAttribute("data-default-open");
    });
  }

  if (desktop.addEventListener) desktop.addEventListener("change", sync);
  else desktop.addListener(sync);
  sync();
})();
