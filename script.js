document.addEventListener('DOMContentLoaded', function() {
  // ===== SECTION MANAGEMENT =====
  // Mapping of section IDs to their HTML elements
  const sections = {
    intro: document.getElementById('intro-section'),
    bio: document.getElementById('bio-section'),
    cat: document.getElementById('cat-section'),
    bear: document.getElementById('bear-section'),
    doggo: document.getElementById('doggo-section'),
  };

  // Mapping of navigation link IDs to their HTML elements
  const navLinks = {
    bio: document.getElementById('bio-nav-link'),
    cat: document.getElementById('cat-nav-link'),
    bear: document.getElementById('bear-nav-link'),
    doggo: document.getElementById('doggo-nav-link'),
  };

  /**
   * Hides all content sections and deactivates all navigation links.
   */
  function hideAllSections() {
    for (const key in sections) {
      sections[key].classList.add('hidden');
    }
    for (const key in navLinks) {
      navLinks[key].classList.remove('active');
    }
  }

  /**
   * Shows a specific content section and activates its corresponding navigation link.
   * @param {string} key - The key corresponding to the section and navigation link to show/activate.
   */
  function showSection(key) {
    hideAllSections();
    sections[key].classList.remove('hidden');
    if (navLinks[key]) {
      navLinks[key].classList.add('active');
    }
  }

  // ===== NAVIGATION EVENT LISTENERS =====
  for (const key in navLinks) {
    navLinks[key].addEventListener('click', function(event) {
      event.preventDefault();
      if (sections[key].classList.contains('hidden')) {
        showSection(key);
      } else {
        showSection('intro');
      }
    });
  }

  // ===== INITIALIZATION =====
  showSection('intro');

  // Initialize the squiggle path animation
  const squigglePath = document.getElementById('squiggle-path');
  if (squigglePath) {
    const length = squigglePath.getTotalLength();
    squigglePath.style.setProperty('--squiggle-length', length);
  }

  // ===== PROFILE PICTURE HANDLING =====
  const profilePic = document.getElementById('profile-pic');
  if (profilePic) {
    profilePic.addEventListener('error', function() {
      // If image fails to load, hide the container
      const container = this.parentElement;
      if (container && container.classList.contains('profile-pic-container')) {
        container.style.display = 'none';
      }
    });
  }
});
