/**
 * terminal-player.js
 *
 * Reads a JSON session file produced by `terminal-capture` and animates
 * it inside a styled <div> — with fully selectable text, a live timer,
 * and playback controls.
 *
 * Usage (inline):
 *   <div id="my-term"></div>
 *   <script src="terminal-player.js"></script>
 *   <script>
 *     TerminalPlayer.create('#my-term', 'session.json');
 *   </script>
 *
 * Usage (embed from Reveal.js slide):
 *   TerminalPlayer.create('#my-term', 'session.json', {
 *     typingSpeed: 40,      // ms per character when typing the command
 *     pauseBeforeType: 800, // ms pause before typing starts
 *     pauseAfterType: 600,  // ms pause after command typed, before output
 *     finalHold: 8000,      // ms to hold on the last frame before looping
 *     loop: true,           // whether to loop the animation
 *     autoplay: true,       // start playing immediately
 *     speedMultiplier: 1.0, // global speed factor (0.5 = half speed, 2 = double)
 *   });
 */

(function (global) {
  'use strict';

  // ── Defaults ────────────────────────────────────────────────────────────────

  const DEFAULTS = {
    typingSpeed: 35,        // ms per character
    pauseBeforeType: 900,   // ms before typing starts
    pauseAfterType: 500,    // ms after command typed, before output streams
    finalHold: 9000,        // ms to hold on final frame before loop
    loop: true,
    autoplay: true,
    speedMultiplier: 1.0,
    theme: {
      bg:         '#12121c',
      headerBg:   '#1c1c2c',
      headerText: '#a0a0c8',
      promptCol:  '#50c878',
      cmdCol:     '#dcdcdc',
      outputCol:  '#b4b4c8',
      timerBg:    '#28280c',
      timerBorder:'#ffdc3c',
      timerText:  '#ffdc3c',
      cursorCol:  '#50c878',
      fontFamily: '"Cascadia Code", "Fira Code", "JetBrains Mono", "Liberation Mono", "DejaVu Sans Mono", monospace',
      fontSize:   '14px',
      lineHeight: '1.5',
    },
  };

  // ── Line model (mirrors Python events_to_lines) ──────────────────────────

  function textToLines(text) {
    const lines = [''];
    let i = 0;
    while (i < text.length) {
      const ch = text[i];
      if (ch === '\r' && text[i + 1] === '\n') {
        lines.push('');
        i += 2;
        continue;
      }
      if (ch === '\n') {
        lines.push('');
      } else if (ch === '\r') {
        lines[lines.length - 1] = '';
      } else if (ch === '\x08') {
        lines[lines.length - 1] = lines[lines.length - 1].slice(0, -1);
      } else if (ch >= ' ' || ch === '\t') {
        lines[lines.length - 1] += ch;
      }
      i++;
    }
    // Strip trailing empty lines
    while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
    return lines;
  }

  // ── DOM helpers ──────────────────────────────────────────────────────────

  function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'style' && typeof v === 'object') {
        Object.assign(e.style, v);
      } else if (k === 'className') {
        e.className = v;
      } else {
        e.setAttribute(k, v);
      }
    });
    children.forEach(c => {
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else e.appendChild(c);
    });
    return e;
  }

  // ── Player class ─────────────────────────────────────────────────────────

  class TerminalPlayerInstance {
    constructor(container, session, opts) {
      this.container = container;
      this.session   = session;
      this.opts      = Object.assign({}, DEFAULTS, opts, {
        theme: Object.assign({}, DEFAULTS.theme, opts && opts.theme),
      });
      this._timers   = [];
      this._playing  = false;
      this._outputLines = [];
      this._build();
      if (this.opts.autoplay) this.play();
    }

    _build() {
      const t = this.opts.theme;
      const wrap = this.container;
      wrap.style.cssText = `
        background: ${t.bg};
        border-radius: 8px;
        overflow: hidden;
        font-family: ${t.fontFamily};
        font-size: ${t.fontSize};
        line-height: ${t.lineHeight};
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        position: relative;
        display: flex;
        flex-direction: column;
      `;

      // Header bar
      this._header = el('div', {
        style: {
          background: t.headerBg,
          color: t.headerText,
          padding: '8px 16px',
          fontSize: '0.9em',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          userSelect: 'none',
          flexShrink: '0',
        },
      });

      // Traffic lights
      const dots = el('div', { style: { display: 'flex', gap: '6px', marginRight: '12px' } });
      ['#ff5f57','#febc2e','#28c840'].forEach(c => {
        dots.appendChild(el('div', { style: {
          width: '12px', height: '12px', borderRadius: '50%', background: c,
        }}));
      });

      this._titleEl = el('span', {}, [this.session.title || this.session.command]);

      // Timer pill
      this._timerEl = el('span', {
        style: {
          background: t.timerBg,
          border: `1px solid ${t.timerBorder}`,
          color: t.timerText,
          padding: '2px 10px',
          borderRadius: '12px',
          fontSize: '0.85em',
          fontFamily: 'inherit',
          minWidth: '70px',
          textAlign: 'right',
          visibility: 'hidden',
        },
      }, ['⏱ 0.0 s']);

      // Controls
      this._playBtn = el('button', {
        style: {
          background: 'transparent',
          border: 'none',
          color: t.headerText,
          cursor: 'pointer',
          fontSize: '1.1em',
          padding: '0 0 0 12px',
          lineHeight: '1',
        },
      }, ['▶']);
      this._playBtn.title = 'Play / Pause';
      this._playBtn.addEventListener('click', () => this._playing ? this.pause() : this.play());

      this._restartBtn = el('button', {
        style: {
          background: 'transparent',
          border: 'none',
          color: t.headerText,
          cursor: 'pointer',
          fontSize: '1.0em',
          padding: '0 0 0 8px',
          lineHeight: '1',
        },
      }, ['↺']);
      this._restartBtn.title = 'Restart';
      this._restartBtn.addEventListener('click', () => this.restart());

      const headerLeft = el('div', { style: { display: 'flex', alignItems: 'center' } });
      headerLeft.appendChild(dots);
      headerLeft.appendChild(this._titleEl);

      const headerRight = el('div', { style: { display: 'flex', alignItems: 'center' } });
      headerRight.appendChild(this._timerEl);
      headerRight.appendChild(this._playBtn);
      headerRight.appendChild(this._restartBtn);

      this._header.appendChild(headerLeft);
      this._header.appendChild(headerRight);

      // Terminal body
      this._body = el('div', {
        style: {
          flex: '1',
          overflow: 'auto',
          padding: '12px 16px',
          boxSizing: 'border-box',
          minHeight: '200px',
        },
      });

      // Pre element for selectable text
      this._pre = el('pre', {
        style: {
          margin: '0',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
          fontFamily: 'inherit',
          fontSize: 'inherit',
          lineHeight: 'inherit',
          color: t.outputCol,
        },
      });
      this._body.appendChild(this._pre);

      wrap.appendChild(this._header);
      wrap.appendChild(this._body);
    }

    // ── Rendering helpers ──────────────────────────────────────────────────

    _renderLines(promptLine, outputLines, cursor = false) {
      const t = this.opts.theme;
      this._pre.innerHTML = '';

      // Prompt line
      if (promptLine !== null) {
        const promptSpan = el('span', { style: { color: t.promptCol } }, ['❯ ']);
        const cmdSpan    = el('span', { style: { color: t.cmdCol } }, [promptLine]);
        this._pre.appendChild(promptSpan);
        this._pre.appendChild(cmdSpan);
        if (cursor) {
          const cur = el('span', {
            className: 'tplayer-cursor',
            style: {
              display: 'inline-block',
              width: '0.6em',
              height: '1.1em',
              background: t.cursorCol,
              verticalAlign: 'text-bottom',
              marginLeft: '1px',
              animation: 'tplayer-blink 1s step-end infinite',
            },
          });
          this._pre.appendChild(cur);
        }
        this._pre.appendChild(document.createTextNode('\n'));
      }

      // Output lines
      outputLines.forEach(line => {
        this._pre.appendChild(document.createTextNode(line + '\n'));
      });

      // Scroll to bottom
      this._body.scrollTop = this._body.scrollHeight;
    }

    _setTimer(visible, label) {
      if (visible) {
        this._timerEl.style.visibility = 'visible';
        this._timerEl.textContent = label || '⏱ 0.0 s';
      } else {
        this._timerEl.style.visibility = 'hidden';
      }
    }

    // ── Scheduling helpers ────────────────────────────────────────────────

    _after(ms, fn) {
      const id = setTimeout(fn, ms / this.opts.speedMultiplier);
      this._timers.push(id);
      return id;
    }

    _clearTimers() {
      this._timers.forEach(clearTimeout);
      this._timers = [];
    }

    // ── Playback ──────────────────────────────────────────────────────────

    play() {
      if (this._playing) return;
      this._playing = true;
      this._playBtn.textContent = '⏸';
      this._run();
    }

    pause() {
      this._playing = false;
      this._playBtn.textContent = '▶';
      this._clearTimers();
    }

    restart() {
      this._clearTimers();
      this._playing = false;
      this._outputLines = [];
      this._pre.innerHTML = '';
      this._setTimer(false, '');
      this._playBtn.textContent = '▶';
      this.play();
    }

    _run() {
      const opts    = this.opts;
      const session = this.session;
      const inputEvent = session.events.find(e => e.type === 'input');
      const command = inputEvent ? inputEvent.text : session.command;
      const outputEvents = session.events.filter(e => e.type === 'output');
      const totalElapsed = session.total_elapsed;

      let delay = opts.pauseBeforeType;

      // 1. Empty terminal
      this._renderLines(null, [], false);

      // 2. Type the command character by character
      let typed = '';
      for (let i = 0; i < command.length; i++) {
        const ch = command[i];
        const d  = delay + i * opts.typingSpeed;
        this._after(d, () => {
          typed += ch;
          this._renderLines(typed, [], true);
        });
      }
      delay += command.length * opts.typingSpeed + opts.pauseAfterType;

      // 3. Show timer, stream output events at their real relative timestamps
      this._after(delay, () => {
        this._setTimer(true, '⏱ 0.0 s');
        this._renderLines(command, [], false);
      });

      // Timer ticks — one tick every ~0.5s of real elapsed time
      const tickInterval = Math.max(totalElapsed / 12, 0.3);
      for (let t = 0; t <= totalElapsed + tickInterval; t += tickInterval) {
        const d = delay + t * 1000;
        const label = `⏱ ${Math.min(t, totalElapsed).toFixed(1)} s`;
        this._after(d, () => {
          this._setTimer(true, label);
        });
      }

      // Output events — replay at their real timestamps relative to execution start
      outputEvents.forEach(ev => {
        const evDelay = delay + ev.t * 1000;
        this._after(evDelay, () => {
          const newLines = textToLines(ev.text);
          this._outputLines = this._outputLines.concat(newLines);
          this._renderLines(command, this._outputLines, false);
        });
      });

      // 4. Hide timer, final hold, then loop (or stop)
      const endDelay = delay + totalElapsed * 1000 + 200;
      this._after(endDelay, () => {
        this._setTimer(false, '');
        this._renderLines(command, this._outputLines, false);
      });

      if (opts.loop) {
        this._after(endDelay + opts.finalHold, () => {
          this._outputLines = [];
          this._playing = false;
          this.play();
        });
      } else {
        this._after(endDelay + opts.finalHold, () => {
          this._playing = false;
          this._playBtn.textContent = '▶';
        });
      }
    }
  }

  // ── Inject cursor blink keyframe once ─────────────────────────────────────

  function injectStyles() {
    if (document.getElementById('tplayer-styles')) return;
    const style = document.createElement('style');
    style.id = 'tplayer-styles';
    style.textContent = `
      @keyframes tplayer-blink {
        0%, 100% { opacity: 1; }
        50%       { opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  const TerminalPlayer = {
    /**
     * Create a terminal player inside `selector` (CSS selector or DOM element),
     * loading the session from `jsonUrl`.
     *
     * Returns a Promise that resolves to the player instance.
     */
    create(selector, jsonUrl, opts = {}) {
      injectStyles();
      const container = typeof selector === 'string'
        ? document.querySelector(selector)
        : selector;
      if (!container) {
        console.error(`terminal-player: element not found: ${selector}`);
        return Promise.reject(new Error(`Element not found: ${selector}`));
      }

      container._terminalPlayer = true; // guard against double-init before fetch resolves

      return fetch(jsonUrl)
        .then(r => {
          if (!r.ok) throw new Error(`Failed to load session: ${r.status} ${jsonUrl}`);
          return r.json();
        })
        .then(session => {
          const player = new TerminalPlayerInstance(container, session, opts);
          container._terminalPlayer = player;
          return player;
        });
    },

    /**
     * Convenience: embed a player by creating a new <div> inside `parentSelector`
     * and loading the session from `jsonUrl`.
     */
    embed(parentSelector, jsonUrl, opts = {}) {
      injectStyles();
      const parent = typeof parentSelector === 'string'
        ? document.querySelector(parentSelector)
        : parentSelector;
      if (!parent) {
        console.error(`terminal-player: parent not found: ${parentSelector}`);
        return Promise.reject(new Error(`Parent not found: ${parentSelector}`));
      }
      const div = document.createElement('div');
      parent.appendChild(div);
      return TerminalPlayer.create(div, jsonUrl, opts);
    },

    /**
     * Auto-initialise any elements with data-terminal-player="url/to/session.json".
     * Call after DOMContentLoaded.
     */
    autoInit() {
      injectStyles();
      document.querySelectorAll('[data-terminal-player]').forEach(el => {
        const url  = el.getAttribute('data-terminal-player');
        const opts = {};
        if (el.dataset.typingSpeed)      opts.typingSpeed      = +el.dataset.typingSpeed;
        if (el.dataset.pauseBeforeType)  opts.pauseBeforeType  = +el.dataset.pauseBeforeType;
        if (el.dataset.pauseAfterType)   opts.pauseAfterType   = +el.dataset.pauseAfterType;
        if (el.dataset.finalHold)        opts.finalHold        = +el.dataset.finalHold;
        if (el.dataset.loop !== undefined) opts.loop           = el.dataset.loop !== 'false';
        if (el.dataset.autoplay !== undefined) opts.autoplay   = el.dataset.autoplay !== 'false';
        if (el.dataset.speedMultiplier)  opts.speedMultiplier  = +el.dataset.speedMultiplier;
        TerminalPlayer.create(el, url, opts);
      });
    },
  };

  // Expose globally
  global.TerminalPlayer = TerminalPlayer;

  // Auto-init on DOMContentLoaded if any data-terminal-player elements exist
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TerminalPlayer.autoInit());
  } else {
    TerminalPlayer.autoInit();
  }

}(typeof window !== 'undefined' ? window : this));
