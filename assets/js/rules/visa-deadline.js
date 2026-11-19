/* Date-only planning arithmetic. No visa entitlement is inferred. */
(function (root) {
  "use strict";
  var DAY = 86400000;
  function parse(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || "")) return null;
    var p = iso.split("-").map(Number);
    if (p[0] < 1900 || p[0] > 2100) return null;
    var n = Date.UTC(p[0], p[1] - 1, p[2]) / DAY;
    return format(n) === iso ? n : null;
  }
  function format(n) { return new Date(n * DAY).toISOString().slice(0, 10); }
  function shiftMonths(n, amount) {
    var d = new Date(n * DAY), first = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + amount, 1));
    var last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
    return Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), Math.min(d.getUTCDate(), last)) / DAY;
  }
  function calculate(input) {
    var arrival = parse(input.arrival), deadline, today = parse(input.today), planned = input.departure ? parse(input.departure) : null;
    if (arrival === null) return { error: "arrival" };
    if (today === null) return { error: "today" };
    if (input.mode === "official") {
      deadline = parse(input.deadline);
      if (deadline === null) return { error: "deadline" };
    } else {
      var amount = Number(input.amount), max = { days: 3660, months: 120, years: 10 }[input.mode];
      if (!max || !Number.isInteger(amount) || amount < 1 || amount > max) return { error: "amount" };
      if (input.mode === "days") deadline = arrival + amount - 1;
      else {
        if (input.endConvention !== "same" && input.endConvention !== "before") return { error: "convention" };
        deadline = shiftMonths(arrival, amount * (input.mode === "years" ? 12 : 1)) - (input.endConvention === "before" ? 1 : 0);
      }
    }
    if (deadline < arrival) return { error: "order" };
    if (deadline > parse("2100-12-31")) return { error: "range" };
    if (input.departure && (planned === null || planned < arrival)) return { error: "departure" };
    return { arrival: format(arrival), deadline: format(deadline), totalDays: deadline - arrival + 1,
      daysUntil: deadline - today, daysUsed: Math.max(0, today - arrival + 1), started: today >= arrival,
      departure: planned === null ? null : format(planned), departureMargin: planned === null ? null : deadline - planned };
  }
  root.AtlasDaysVisaDeadline = { parse: parse, format: format, shiftMonths: shiftMonths, calculate: calculate };
})(typeof window === "undefined" ? globalThis : window);
