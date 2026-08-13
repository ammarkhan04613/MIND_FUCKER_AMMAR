// static/bg.js
// Shared video handling logic:
// - Respects prefers-reduced-motion (hides video and uses poster)
// - Uses Page Visibility API to pause when tab is inactive
// - Safely attempts autoplay and falls back to a full-screen poster when autoplay is blocked
// - Exposes toggleTokenInput() used by the forms in templates

(function () {
  const video = document.getElementById('bg-video');
  const overlay = document.querySelector('.overlay');

  function getPoster() {
    if (!video) return null;
    return video.getAttribute('poster') || null;
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function applyReducedMotionMode() {
    if (reduceMotion.matches) {
      if (video) {
        try { video.pause(); } catch (e) { }
        video.style.display = 'none';
      }
      const poster = getPoster();
      if (poster) {
        if (!document.querySelector('.bg-poster-fallback')) {
          const el = document.createElement('div');
          el.className = 'bg-poster-fallback';
          el.style.backgroundImage = `url('${poster}')`;
          document.body.appendChild(el);
        } else {
          document.querySelector('.bg-poster-fallback').style.backgroundImage = `url('${poster}')`;
        }
      }
    } else {
      const posterEl = document.querySelector('.bg-poster-fallback');
      if (posterEl) posterEl.remove();
      if (video) {
        video.style.display = '';
        safePlayVideo();
      }
    }
  }

  function safePlayVideo() {
    if (!video) return;
    if (document.hidden) return;
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        const poster = getPoster();
        if (poster) {
          if (!document.querySelector('.bg-poster-fallback')) {
            const el = document.createElement('div');
            el.className = 'bg-poster-fallback';
            el.style.backgroundImage = `url('${poster}')`;
            document.body.appendChild(el);
            video.style.display = 'none';
          }
        }
      });
    }
  }

  function handleVisibilityChange() {
    if (!video) return;
    if (document.hidden) {
      try { video.pause(); } catch (e) {}
    } else {
      if (!reduceMotion.matches) safePlayVideo();
    }
  }

  function init() {
    if (video) {
      video.setAttribute('muted', '');
      video.setAttribute('playsinline', '');
      video.setAttribute('preload', 'auto');
      if (document.hidden) {
        try { video.pause(); } catch (e) {}
      } else {
        safePlayVideo();
      }
    }

    applyReducedMotionMode();
    reduceMotion.addEventListener('change', applyReducedMotionMode);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pagehide', () => { if (video) try { video.pause(); } catch (e) {} });
    window.addEventListener('online', () => { if (video && !reduceMotion.matches) safePlayVideo(); });
    window.addEventListener('offline', () => { if (video) try { video.pause(); } catch (e) {} });
  }

  window.toggleTokenInput = function toggleTokenInput() {
    const v = document.getElementById('tokenOption') ? document.getElementById('tokenOption').value : 'single';
    const single = document.getElementById('singleTokenInput');
    const file = document.getElementById('tokenFileInput');
    if (single) single.style.display = v === 'single' ? 'block' : 'none';
    if (file) file.style.display = v === 'multiple' ? 'block' : 'none';
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
