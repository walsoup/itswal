const { performance } = require('perf_hooks');

const sections = {
  intro: { classList: { remove: () => {}, add: () => {} } },
  bio: { classList: { remove: () => {}, add: () => {} } },
  cat: { classList: { remove: () => {}, add: () => {} } },
  photos: { classList: { remove: () => {}, add: () => {} } },
};

function hideAllSections_old() {
  Object.values(sections).forEach(s => s.classList.remove('visible'));
}

let activeSection = sections.intro;
function hideAllSections_new() {
  if (activeSection) {
    activeSection.classList.remove('visible');
  }
}

function bench(fn, name) {
  const start = performance.now();
  for (let i = 0; i < 1000000; i++) {
    fn();
  }
  const end = performance.now();
  console.log(`${name}: ${end - start} ms`);
}

bench(hideAllSections_old, 'old');
bench(hideAllSections_new, 'new');
bench(hideAllSections_old, 'old');
bench(hideAllSections_new, 'new');
