(function () {
  "use strict";
  var root = document.querySelector("[data-visa-deadline]"), rule = window.AtlasDaysVisaDeadline;
  if (!root || !rule) return;
  var form = root.querySelector("form"), result = root.querySelector("[data-deadline-result]");
  var error = root.querySelector("[data-deadline-error]"), download = root.querySelector("[data-deadline-download]"), latest = null;
  var names = { official: "Official departure deadline", days: "Number of days", months: "Calendar months", years: "Calendar years" };
  var errors = { arrival: "Enter a valid arrival date.", today: "The current date is unavailable.", deadline: "Enter the departure deadline on your permission or admission record.", amount: "Enter a whole number within the displayed limit.", convention: "Choose how the calendar period ends.", order: "The departure deadline cannot be before arrival.", range: "Choose a period ending on or before 31 December 2100.", departure: "The planned departure must be on or after arrival." };
  var dateFormat = new Intl.DateTimeFormat(document.documentElement.lang || "en", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  function date(iso) { return dateFormat.format(new Date(rule.parse(iso) * 86400000)); }
  function today() { var d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function set(selector, text) { root.querySelector(selector).textContent = text; }
  function update() {
    var mode = form.elements.mode.value, calendar = mode === "months" || mode === "years";
    root.querySelector("[data-official-field]").hidden = mode !== "official";
    root.querySelector("[data-duration-field]").hidden = mode === "official";
    root.querySelector("[data-convention-field]").hidden = !calendar;
    form.elements.amount.max = { days: 3660, months: 120, years: 10 }[mode] || 3660;
    set("[data-duration-label]", { days: "Days allowed", months: "Calendar months allowed", years: "Calendar years allowed" }[mode] || "Length of stay");
    var input = { arrival: form.elements.arrival.value, mode: mode, deadline: form.elements.deadline.value,
      amount: form.elements.amount.value, endConvention: form.elements.endConvention.value, departure: form.elements.departure.value, today: today() };
    latest = rule.calculate(input);
    var incomplete = !input.arrival || (mode === "official" ? !input.deadline : !input.amount);
    error.hidden = !latest.error || incomplete;
    error.textContent = latest.error && !incomplete ? errors[latest.error] : "";
    result.hidden = !!latest.error;download.disabled = !!latest.error;
    root.querySelector("[data-deadline-empty]").hidden = !latest.error;
    if (latest.error) return;
    latest.basis = names[mode] + (mode === "official" ? "" : ": " + input.amount);
    latest.convention = calendar ? (input.endConvention === "same" ? "Anniversary date (clamped to month end)" : "Day before anniversary (clamped to month end)") : "Arrival counts as day 1";
    set("[data-deadline-date]", date(latest.deadline));
    set("[data-deadline-basis]", mode === "official" ? "From the official date you entered" : "Calculated from your chosen duration and convention");
    set("[data-deadline-total]", latest.totalDays + (latest.totalDays === 1 ? " calendar day, including arrival and the final day" : " calendar days, including arrival and the final day"));
    var status = latest.daysUntil < 0 ? "Deadline passed " + (-latest.daysUntil) + " day" + (latest.daysUntil === -1 ? "" : "s") + " ago"
      : latest.daysUntil === 0 ? "Departure deadline is today" : latest.daysUntil + " day" + (latest.daysUntil === 1 ? "" : "s") + " until the deadline";
    set("[data-deadline-status]", status);
    root.querySelector("[data-deadline-status]").className = "cal-pill tone-" + (latest.daysUntil < 0 ? "critical" : latest.daysUntil <= 7 ? "warning" : "normal");
    var meter = root.querySelector("progress");meter.max = latest.totalDays;meter.value = Math.min(latest.daysUsed, latest.totalDays);
    set("[data-deadline-progress]", latest.started ? latest.daysUsed + " calendar days since arrival, including today" : "Your stay has not started yet");
    var plan = root.querySelector("[data-departure-status]");plan.hidden = latest.departure === null;
    if (latest.departure !== null) {
      var margin = latest.departureMargin;
      plan.textContent = margin < 0 ? "Your planned departure is " + (-margin) + " day" + (margin === -1 ? "" : "s") + " after the deadline."
        : margin === 0 ? "Your planned departure is on the deadline." : "Your planned departure is " + margin + " day" + (margin === 1 ? "" : "s") + " before the deadline.";
      plan.classList.toggle("is-over", margin < 0);
    }
  }
  form.addEventListener("input", update);form.addEventListener("change", update);
  form.addEventListener("submit", function (e) { e.preventDefault();update(); });
  form.addEventListener("reset", function () { setTimeout(update, 0); });
  download.addEventListener("click", function () {
    if (!latest || latest.error) return;
    function csv(value) { return '"' + String(value == null ? "" : value).replace(/"/g, '""') + '"'; }
    var rows = [["Arrival date", "Departure deadline", "Planned departure", "Total calendar days", "Basis", "Counting convention"],
      [latest.arrival, latest.deadline, latest.departure || "", latest.totalDays, latest.basis, latest.convention]];
    var url = URL.createObjectURL(new Blob([rows.map(function (r) { return r.map(csv).join(","); }).join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" }));
    var a = document.createElement("a");a.href = url;a.download = "visa-deadline-summary.csv";document.body.appendChild(a);a.click();a.remove();setTimeout(function () { URL.revokeObjectURL(url); },1000);
  });
  update();
})();
