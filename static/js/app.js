document.addEventListener("DOMContentLoaded", () => {
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  [...tooltipTriggerList].map((el) => new bootstrap.Tooltip(el));

  document.querySelectorAll(".compare-block").forEach((block) => {
    const summary = block.querySelector(".compare-summary");
    const update = () => {
      const preferred = block.querySelector("input[name$='_preferred']:checked");
      const intensity = block.querySelector("input[name$='_intensity']:checked");
      if (!preferred || !summary) return;
      const left = block.dataset.left;
      const right = block.dataset.right;
      if (preferred.value === "EQUAL" || (intensity && intensity.value === "1")) {
        summary.textContent = `${left} e ${right} têm importância igual.`;
        return;
      }
      const value = intensity ? intensity.value : "3";
      if (preferred.value === "LEFT") {
        summary.textContent = `${left} é ${value} vezes mais importante que ${right}.`;
      } else {
        summary.textContent = `${right} é ${value} vezes mais importante que ${left}.`;
      }
    };
    block.addEventListener("change", update);
    update();
  });
});
