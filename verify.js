const fs = require('fs');
const path = require('path');
const vm = require('vm');

// 1. Path to index.html
const indexPath = path.join(__dirname, 'index.html');
const indexContent = fs.readFileSync(indexPath, 'utf8');

console.log('--- Verifying HTML Structure ---');
// HTML Validator function
function validateHTML(html) {
  const voidElements = new Set([
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr', '!doctype'
  ]);
  
  const stack = [];
  let i = 0;
  const len = html.length;
  
  while (i < len) {
    if (html.startsWith('<!--', i)) {
      const end = html.indexOf('-->', i + 4);
      if (end === -1) {
        throw new Error('Unterminated comment starting at index ' + i);
      }
      i = end + 3;
    } else if (html.startsWith('<script', i)) {
      const tagEnd = html.indexOf('>', i);
      if (tagEnd === -1) throw new Error('Unterminated script tag at index ' + i);
      const end = html.toLowerCase().indexOf('</script>', tagEnd + 1);
      if (end === -1) throw new Error('Unterminated script content starting at index ' + i);
      i = end + 9;
    } else if (html.startsWith('<style', i)) {
      const tagEnd = html.indexOf('>', i);
      if (tagEnd === -1) throw new Error('Unterminated style tag at index ' + i);
      const end = html.toLowerCase().indexOf('</style>', tagEnd + 1);
      if (end === -1) throw new Error('Unterminated style content starting at index ' + i);
      i = end + 8;
    } else if (html[i] === '<') {
      const end = html.indexOf('>', i);
      if (end === -1) throw new Error('Unterminated tag starting at index ' + i);
      
      const tagContent = html.substring(i + 1, end).trim();
      i = end + 1;
      
      if (tagContent.startsWith('/')) {
        const tagName = tagContent.substring(1).trim().split(/\s+/)[0].toLowerCase();
        if (stack.length === 0) {
          throw new Error(`Unexpected closing tag </${tagName}> at index ${i}`);
        }
        const lastOpened = stack.pop();
        if (lastOpened.name !== tagName) {
          throw new Error(`Tag mismatch: </${tagName}> closed but expected </${lastOpened.name}> (opened at index ${lastOpened.index})`);
        }
      } else {
        const isSelfClosing = tagContent.endsWith('/');
        const cleanContent = isSelfClosing ? tagContent.slice(0, -1).trim() : tagContent;
        const tagName = cleanContent.split(/\s+/)[0].toLowerCase();
        
        if (tagName.startsWith('!') && !tagName.startsWith('!doctype')) {
          continue;
        }
        
        if (!voidElements.has(tagName) && !isSelfClosing) {
          stack.push({ name: tagName, index: i - tagContent.length - 2 });
        }
      }
    } else {
      i++;
    }
  }
  
  if (stack.length > 0) {
    const unclosed = stack.map(t => `<${t.name}> opened at index ${t.index}`).join(', ');
    throw new Error('Unclosed tags remain: ' + unclosed);
  }
  
  return true;
}

try {
  validateHTML(indexContent);
  console.log('HTML Structure Verification: PASS (No unclosed tags or malformed structures)');
} catch (e) {
  console.error('HTML Structure Verification: FAIL');
  console.error(e.message);
  process.exit(1);
}

console.log('\n--- Verifying JavaScript Syntax ---');
// Extract Javascript from index.html
const rawJsBlocks = [];
const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let match;
while ((match = scriptRegex.exec(indexContent)) !== null) {
  const code = match[1].trim();
  // Only check script blocks that have actual inline javascript (skip external ones)
  if (code && !match[0].includes('src=')) {
    rawJsBlocks.push(code);
  }
}

if (rawJsBlocks.length === 0) {
  console.log('No inline JavaScript blocks found to verify.');
} else {
  rawJsBlocks.forEach((code, index) => {
    try {
      new vm.Script(code);
      console.log(`JS Block ${index + 1} Syntax Check: PASS`);
    } catch (e) {
      console.error(`JS Block ${index + 1} Syntax Check: FAIL`);
      console.error(e.stack);
      process.exit(1);
    }
  });
}

const jsBlocks = rawJsBlocks.map(code => {
  return code
    .replace(/(?<!let\s+)tick\s*=\s*false;/g, 'console.log("[TICK] Setting tick to false"); tick = false;')
    .replace(/(?<!let\s+)tick\s*=\s*true;/g, 'console.log("[TICK] Setting tick to true"); tick = true;')
    .replace(/if\s*\(\s*!tick\s*\)/g, 'console.log("[TICK] Checking !tick. Current tick:", tick); if (!tick)');
});

console.log('\n--- Verifying Jukebox Track Assets ---');
const expectedTracks = [
  'audio/tracks/itswal_expressive_bio.mp3',
  'audio/tracks/itswal_expressive_cats.mp3',
  'audio/tracks/itswal_expressive_home.mp3',
  'audio/tracks/itswal_expressive_photos.mp3',
  'audio/tracks/itswal_pink_bio.mp3',
  'audio/tracks/itswal_pink_cats.mp3',
  'audio/tracks/itswal_pink_home.mp3',
  'audio/tracks/itswal_pink_photos.mp3',
  'audio/tracks/itswal_space_bio.mp3',
  'audio/tracks/itswal_space_cats.mp3',
  'audio/tracks/itswal_space_home.mp3',
  'audio/tracks/itswal_space_photos.mp3',
];

let tracksAllExist = true;
expectedTracks.forEach(trackPath => {
  const fullPath = path.join(__dirname, trackPath);
  if (fs.existsSync(fullPath)) {
    console.log(`Track Exist Check: ${trackPath} -> PRESENT`);
  } else {
    console.error(`Track Exist Check: ${trackPath} -> MISSING`);
    tracksAllExist = false;
  }
});

if (!tracksAllExist) {
  console.error('Jukebox Track Assets Check: FAIL');
  process.exit(1);
} else {
  console.log('Jukebox Track Assets Check: PASS');
}

console.log('\n--- Running Throttled Event Listeners Simulation Tests ---');

// Mock Sandbox Environment
class MockElement {
  constructor(id = '', className = '') {
    this.id = id;
    this.className = className;
    this.classList = {
      classes: new Set(className ? className.split(' ') : []),
      add: (c) => this.classList.classes.add(c),
      remove: (c) => this.classList.classes.delete(c),
      contains: (c) => this.classList.classes.has(c),
    };
    this.style = {
      properties: {},
      setProperty: (k, v) => { this.style.properties[k] = v; },
      removeProperty: (k) => { delete this.style.properties[k]; },
      display: '',
      cursor: '',
    };
    this.listeners = {};
    this.textContent = '';
    this.innerHTML = '';
    this.attributes = {};
  }
  addEventListener(event, callback, options) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  }
  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }
  setAttribute(k, v) {
    this.attributes[k] = v;
  }
  getAttribute(k) {
    return this.attributes[k] || null;
  }
  appendChild(child) {
    return child;
  }
  getTotalLength() {
    return 100;
  }
  getContext(type) {
    return {
      fillStyle: '',
      fillRect: () => {},
      fillText: () => {},
      font: '',
    };
  }
  click() {
    if (this.listeners['click']) {
      this.listeners['click'].forEach(cb => cb({ preventDefault: () => {} }));
    }
  }
}

const mockIds = [
  'wal-toggle', 'wal-text', 'wal-cursor', 'animation-indicator', 'squiggle-svg',
  'theme-hint', 'audio-toggle-btn', 'lightbox', 'lightbox-img', 'squiggle-path',
  'matrix-canvas', 'cat-fact', 'cat-fact-refresh', 'intro', 'bio', 'cat', 'photos',
  'cat-album', 'photos-album', 'cat-album-status', 'photos-album-status'
];

const mockElements = {};
mockIds.forEach(id => {
  mockElements[id] = new MockElement(id);
});

const mockNavLinks = [
  new MockElement('', 'nav-link'),
  new MockElement('', 'nav-link'),
  new MockElement('', 'nav-link'),
  new MockElement('', 'nav-link'),
];
mockNavLinks[0].setAttribute('href', '#intro');
mockNavLinks[1].setAttribute('href', '#bio');
mockNavLinks[2].setAttribute('href', '#cat');
mockNavLinks[3].setAttribute('href', '#photos');

const mockDocument = {
  body: new MockElement('body'),
  listeners: {},
  addEventListener(event, callback, options) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  },
  removeEventListener(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  },
  getElementById(id) {
    return mockElements[id] || null;
  },
  querySelector(selector) {
    if (selector === '.lightbox-close') {
      return new MockElement('', 'lightbox-close');
    }
    return null;
  },
  querySelectorAll(selector) {
    if (selector === '.nav-link') {
      return mockNavLinks;
    }
    return [];
  },
  createElement(tag) {
    return new MockElement();
  }
};

class MockAudio {
  constructor() {
    this.src = '';
    this.preload = '';
    this.crossOrigin = '';
    this.loop = false;
    this.currentTime = 0;
    this.duration = 100;
    this.readyState = 4;
  }
  load() {}
  play() { return Promise.resolve(); }
  pause() {}
  getAttribute(name) { return this[name] || ''; }
}

class MockAudioContext {
  constructor() {
    this.state = 'running';
    this.destination = {};
  }
  createMediaElementSource() {
    return { connect: () => {} };
  }
  createGain() {
    return {
      gain: {
        value: 1,
        cancelScheduledValues: () => {},
        setValueAtTime: () => {},
        linearRampToValueAtTime: () => {},
      },
      connect: () => {},
    };
  }
  resume() { return Promise.resolve(); }
}

let mockRafs = [];
const mockRequestAnimationFrame = (cb) => {
  console.log('mockRequestAnimationFrame called! Current mockRafs length:', mockRafs.length);
  mockRafs.push(cb);
  return mockRafs.length - 1;
};
const mockCancelAnimationFrame = (id) => {
  mockRafs[id] = null;
};
const runRafs = () => {
  const current = mockRafs;
  mockRafs = [];
  current.forEach(cb => {
    if (cb) cb(Date.now());
  });
};

let mockTimeouts = [];
const mockSetTimeout = (cb, delay) => {
  mockTimeouts.push({ cb, delay });
  return mockTimeouts.length - 1;
};
const mockClearTimeout = (id) => {
  if (mockTimeouts[id]) mockTimeouts[id].cb = null;
};
const runTimeouts = () => {
  const current = mockTimeouts;
  mockTimeouts = [];
  current.forEach(t => {
    if (t.cb) t.cb();
  });
};

const sandbox = {
  document: mockDocument,
  window: {
    AudioContext: MockAudioContext,
    webkitAudioContext: MockAudioContext,
    location: { hash: '' },
    listeners: {},
    addEventListener(event, cb) {
      if (!this.listeners[event]) this.listeners[event] = [];
      this.listeners[event].push(cb);
    },
    dispatchEvent(event) {
      const type = event.type || event;
      if (this.listeners[type]) {
        this.listeners[type].forEach(cb => cb(event));
      }
    }
  },
  CustomEvent: class {
    constructor(type, options) {
      this.type = type;
      this.detail = options ? options.detail : null;
    }
  },
  Audio: MockAudio,
  BroadcastChannel: class {
    constructor() {}
    addEventListener() {}
    postMessage() {}
  },
  localStorage: {
    getItem: () => null,
    setItem: () => {},
  },
  sessionStorage: {
    getItem: () => null,
    setItem: () => {},
  },
  setInterval: () => {},
  setTimeout: mockSetTimeout,
  clearTimeout: mockClearTimeout,
  requestAnimationFrame: mockRequestAnimationFrame,
  cancelAnimationFrame: mockCancelAnimationFrame,
  performance: {
    now: () => Date.now(),
  },
  console: console,
};

// Run the script blocks inside the sandbox
vm.createContext(sandbox);

jsBlocks.forEach(code => {
  vm.runInContext(code, sandbox);
});

// Trigger DOMContentLoaded
const domContentLoadedCallbacks = mockDocument.listeners['DOMContentLoaded'] || [];
if (domContentLoadedCallbacks.length === 0) {
  throw new Error('No DOMContentLoaded listener registered!');
}
domContentLoadedCallbacks.forEach(cb => cb());

// Clear initial requestAnimationFrame scheduled by showSection
runRafs();

// Now retrieve mousemove and touchmove listeners from mockDocument
const mousemoveListeners = mockDocument.listeners['mousemove'] || [];
const touchmoveListeners = mockDocument.listeners['touchmove'] || [];
const touchstartListeners = mockDocument.listeners['touchstart'] || [];

if (mousemoveListeners.length === 0 || touchmoveListeners.length === 0 || touchstartListeners.length === 0) {
  throw new Error('Missing mouse/touch event listeners on document!');
}

const handleMouseMove = mousemoveListeners[0];
const handleTouchMove = touchmoveListeners.find(cb => cb === handleMouseMove);
const handleTouchStart = touchstartListeners.find(cb => cb === handleMouseMove);

// Assertions function
function assert(condition, message) {
  if (!condition) {
    console.error(`Assertion failed: ${message}`);
    process.exit(1);
  }
}

// 1. Initial State Check
assert(mockDocument.body.classList.contains('theme-banana'), 'Initial theme should be banana');
assert(mockDocument.body.style.properties['--mouse-x'] === undefined, 'Mouse coordinates should not be set initially');

// 2. Click squiggle to cycle to dark theme (banana -> dark)
const squiggleSvg = mockElements['squiggle-svg'];
squiggleSvg.click();
runTimeouts(); // Trigger nextTheme cycle

assert(mockDocument.body.classList.contains('theme-dark'), 'Theme should now be dark');

// 3. Move mouse when theme is dark
handleMouseMove({ clientX: 100, clientY: 200 });
assert(mockRafs.length === 1, 'One animation frame should be scheduled');
assert(mockDocument.body.style.properties['--mouse-x'] === undefined, 'Style property should not update before requestAnimationFrame runs');

// Run animation frame
runRafs();
assert(mockDocument.body.style.properties['--mouse-x'] === '100px', 'Mouse X coordinate was not updated correctly');
assert(mockDocument.body.style.properties['--mouse-y'] === '200px', 'Mouse Y coordinate was not updated correctly');

// 4. Test throttling: Multiple moves in same frame
handleMouseMove({ clientX: 150, clientY: 250 });
handleMouseMove({ clientX: 200, clientY: 300 });
assert(mockRafs.length === 1, 'Only one animation frame should be scheduled due to throttling');

runRafs();
assert(mockDocument.body.style.properties['--mouse-x'] === '200px', 'Coordinates should update to the last position after animation frame');
assert(mockDocument.body.style.properties['--mouse-y'] === '300px', 'Coordinates should update to the last position after animation frame');

// 5. Test touch events
handleTouchMove({ touches: [{ clientX: 50, clientY: 60 }] });
assert(mockRafs.length === 1, 'Touchmove schedules an animation frame');
runRafs();
assert(mockDocument.body.style.properties['--mouse-x'] === '50px', 'Touch X coordinate should be updated');
assert(mockDocument.body.style.properties['--mouse-y'] === '60px', 'Touch Y coordinate should be updated');

console.log('Calling handleTouchStart. Function is:', handleTouchStart.toString());
handleTouchStart({ touches: [{ clientX: 80, clientY: 90 }] });
console.log('Called handleTouchStart. mockRafs length:', mockRafs.length);
assert(mockRafs.length === 1, 'Touchstart schedules an animation frame');
runRafs();
assert(mockDocument.body.style.properties['--mouse-x'] === '80px', 'Touchstart X coordinate should be updated');
assert(mockDocument.body.style.properties['--mouse-y'] === '90px', 'Touchstart Y coordinate should be updated');

// 6. Test behavior in default theme (non-dark)
// Cycle theme: dark -> default
squiggleSvg.click();
runTimeouts();
assert(!mockDocument.body.classList.contains('theme-dark'), 'Theme should cycle to default (which has no theme-dark class)');

// Move mouse, should not set style properties
handleMouseMove({ clientX: 500, clientY: 600 });
runRafs();
assert(mockDocument.body.style.properties['--mouse-x'] === undefined, 'Mouse coordinates should not be set in default theme');

console.log('All event listener simulation tests: PASS');

// We simulate a document click to unlock the audio context
const unlockCallbacks = mockDocument.listeners['click'] || [];
unlockCallbacks.forEach(cb => cb({ preventDefault: () => {} }));

// We chain microtasks to let the awaits in _crossfade execute and schedule the setTimeout
Promise.resolve()
  .then(() => {}) // 1st microtask
  .then(() => {}) // 2nd microtask
  .then(() => {}) // 3rd microtask
  .then(() => {
    // Now the setTimeout has been scheduled in mockTimeouts. We run it!
    runTimeouts();
    
    // Now we wait for the fadePromise to resolve
    const jukeboxEngine = sandbox.window.__jukebox;
    const fadePromise = jukeboxEngine ? jukeboxEngine._fadePromise : null;
    return fadePromise ? fadePromise : Promise.resolve();
  })
  .then(() => {
    // Test Jukebox secondary fixes (background audio start and cross-tab mute sync UI)
    console.log('\n--- Running Jukebox Secondary Fixes Verification ---');
    const jukeboxEngine = sandbox.window.__jukebox;

    // Verify JukeboxEngine is instantiated and has correct initial properties
    assert(jukeboxEngine !== null, 'JukeboxEngine should be instantiated');

    // Check that slots are initialized and have correct theme/tab after unlock
    assert(jukeboxEngine.slots !== null, 'Slots should be initialized after unlock');
    const activeSlot = jukeboxEngine.slots[jukeboxEngine.activeIdx];
    assert(activeSlot.theme !== null, 'Active slot theme should be initialized after unlock');
    assert(activeSlot.tab !== null, 'Active slot tab should be initialized after unlock');

    // Verify initial button text
    const audioBtn = mockElements['audio-toggle-btn'];
    assert(audioBtn.textContent === '🔊', 'Audio button should initially show sound icon');

    // Simulate mute event dispatch (as if from another tab/sync event)
    jukeboxEngine.setMuted(true);
    assert(jukeboxEngine.isMuted === true, 'JukeboxEngine should be muted');
    assert(audioBtn.textContent === '🔇', 'Audio button UI should update to muted icon on mute sync event');

    // Simulate unmute event dispatch
    jukeboxEngine.setMuted(false);
    assert(jukeboxEngine.isMuted === false, 'JukeboxEngine should be unmuted');
    assert(audioBtn.textContent === '🔊', 'Audio button UI should update to unmuted icon on unmute sync event');

    console.log('Jukebox secondary fixes verification: PASS');
  })
  .catch(err => {
    console.error('Jukebox secondary fixes verification: FAIL');
    console.error(err);
    process.exit(1);
  });
