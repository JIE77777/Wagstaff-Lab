# -*- coding: utf-8 -*-
from __future__ import annotations

from html import escape

# NOTE:
# - Keep HTML/JS as a normal triple-quoted string.
# - Do NOT use Python f-strings here: the template contains many `{}` (CSS/JS/template literals).

_SHARED_CSS = r"""
@font-face {
  font-family: 'Bricolage Grotesque';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/BricolageGrotesque-normal-400.ttf') format('truetype');
}
@font-face {
  font-family: 'Bricolage Grotesque';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/BricolageGrotesque-normal-600.ttf') format('truetype');
}
@font-face {
  font-family: 'Bricolage Grotesque';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/BricolageGrotesque-normal-700.ttf') format('truetype');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/IBMPlexSans-normal-400.ttf') format('truetype');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/IBMPlexSans-normal-500.ttf') format('truetype');
}
@font-face {
  font-family: 'IBM Plex Sans';
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/IBMPlexSans-normal-600.ttf') format('truetype');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/JetBrainsMono-normal-400.ttf') format('truetype');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url('__WAGSTAFF_APP_ROOT__/static/app/fonts/JetBrainsMono-normal-500.ttf') format('truetype');
}

:root {
  --paper: #f8f2e6;
  --paper-2: #efe4d2;
  --ink: #1b1c1f;
  --muted: #6f6a61;
  --line: rgba(27, 28, 31, 0.16);
  --accent: #0f7b6c;
  --accent-2: #d07b3a;
  --accent-soft: rgba(15, 123, 108, 0.16);
  --panel: rgba(255, 255, 255, 0.86);
  --panel-strong: #ffffff;
  --shadow: 0 24px 56px rgba(22, 23, 24, 0.12);
  --shadow-soft: 0 12px 24px rgba(22, 23, 24, 0.08);
  --radius: 18px;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  min-height: 100vh;
  color: var(--ink);
  font-family: "IBM Plex Sans", "Noto Sans", sans-serif;
  background:
    radial-gradient(900px 560px at 12% -10%, rgba(15, 123, 108, 0.2), transparent 60%),
    radial-gradient(860px 520px at 95% 0%, rgba(208, 123, 58, 0.16), transparent 60%),
    linear-gradient(180deg, var(--paper), var(--paper-2));
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background-image:
    radial-gradient(rgba(27, 28, 31, 0.08) 0.6px, transparent 0.6px),
    repeating-linear-gradient(115deg, rgba(27, 28, 31, 0.04) 0, rgba(27, 28, 31, 0.04) 1px, transparent 1px, transparent 24px);
  background-size: 28px 28px, 220px 220px;
  opacity: 0.45;
}
a { color: var(--accent); text-decoration: none; }
a:hover { color: #0a5d51; }

.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(248, 242, 230, 0.92);
  backdrop-filter: blur(14px);
  border-bottom: 1px solid var(--line);
}
.topbar,
.subbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px 18px;
  padding: 14px 20px;
}
.topbar { justify-content: space-between; }
.subbar {
  border-top: 1px solid rgba(27, 28, 31, 0.08);
  background: rgba(255, 255, 255, 0.4);
  justify-content: space-between;
}
.topbar-left,
.topbar-right,
.subbar-left,
.subbar-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 12px;
}
.topbar-right { margin-left: auto; }
.subbar-right { flex: 1 1 360px; justify-content: flex-end; }
.subbar-left { flex-direction: column; align-items: flex-start; gap: 4px; }
.brand {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: "Bricolage Grotesque", "IBM Plex Sans", sans-serif;
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
}
.brand-sub {
  font-size: 10px;
  letter-spacing: 0.22em;
  color: var(--muted);
  font-weight: 600;
}
.page-title {
  font-family: "Bricolage Grotesque", "IBM Plex Sans", sans-serif;
  font-size: 20px;
  font-weight: 700;
}
.page-sub {
  font-size: 12px;
  color: var(--muted);
}
.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.nav-link {
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--panel);
  transition: transform 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}
.nav-link:hover {
  color: var(--ink);
  border-color: rgba(15, 123, 108, 0.45);
  transform: translateY(-1px);
}
.nav-link.active {
  color: #fff;
  border-color: var(--ink);
  background: var(--ink);
}
.label-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}
.mode-toggle {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.mode-btn {
  font-size: 12px;
  padding: 6px 12px;
}
.mode-btn.active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}

.search {
  flex: 1 1 300px;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 560px;
}
input[type="text"],
textarea {
  width: 100%;
  background: var(--panel-strong);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  outline: none;
  box-shadow: var(--shadow-soft);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
input[type="text"]:focus,
textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
textarea {
  min-height: 84px;
  resize: vertical;
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
}
select {
  background: var(--panel-strong);
  color: var(--ink);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
}
button,
.btn {
  background: var(--panel-strong);
  border: 1px solid var(--line);
  color: var(--ink);
  border-radius: 999px;
  padding: 9px 12px;
  cursor: pointer;
  font-weight: 600;
  box-shadow: var(--shadow-soft);
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}
button:hover,
.btn:hover {
  border-color: rgba(15, 123, 108, 0.45);
  transform: translateY(-1px);
}
button.primary,
.btn.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: none;
}
button.primary:hover,
.btn.primary:hover {
  background: #0a5d51;
}
.btn.ghost {
  background: transparent;
  border-color: transparent;
  box-shadow: none;
  color: var(--muted);
}
.btn.ghost:hover { color: var(--ink); transform: none; }
.btn.active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}
.btn.ghost.active {
  background: var(--ink);
  border-color: var(--ink);
  color: #fff;
}
.btn.back { display: none; }

button:focus-visible,
.nav-link:focus-visible,
input[type="text"]:focus-visible,
textarea:focus-visible,
select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.meta,
#meta {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px dashed var(--line);
  background: rgba(255, 255, 255, 0.6);
  color: var(--muted);
  font-size: 12px;
  max-width: 42vw;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.layout {
  display: grid;
  grid-template-columns: minmax(200px, 250px) minmax(320px, 420px) minmax(420px, 1fr);
  grid-template-areas: "filters recipes detail";
  gap: 20px;
  padding: 20px;
}
.layout > .panel:nth-child(1) { grid-area: filters; }
.layout > .panel:nth-child(2) { grid-area: recipes; }
.layout > .panel:nth-child(3) { grid-area: detail; }

body[data-view="explore"] #filterPanel,
body[data-view="simulate"] #filterPanel {
  display: none;
}
body[data-view="explore"] .layout,
body[data-view="simulate"] .layout {
  grid-template-columns: minmax(320px, 440px) minmax(420px, 1fr);
  grid-template-areas: "recipes detail";
}
body[data-view="explore"] #searchBar,
body[data-view="simulate"] #searchBar {
  display: none;
}

.wrap {
  display: grid;
  grid-template-columns: minmax(360px, 460px) minmax(0, 1fr);
  grid-template-areas: "list detail";
  gap: 20px;
  padding: 20px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: var(--shadow);
  min-height: 0;
  display: flex;
  flex-direction: column;
  animation: panelRise 0.5s ease both;
}
.panel--primary {
  border-color: rgba(15, 123, 108, 0.45);
  box-shadow: 0 30px 60px rgba(20, 30, 30, 0.16);
}
.panel-head,
.phead,
.panel h2 {
  margin: 0;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.panel-title {
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--muted);
  font-weight: 600;
}
.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.panel h2 button {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  box-shadow: none;
}
.panel-body,
.pbody,
.detail-body,
.detail {
  padding: 18px;
}
.panel-body--meta {
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.6);
}
.detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-size: 14px;
  line-height: 1.6;
}

.list {
  max-height: min(60vh, 680px);
  overflow: auto;
}
.list::-webkit-scrollbar { width: 10px; }
.list::-webkit-scrollbar-thumb {
  background: rgba(27, 28, 31, 0.16);
  border-radius: 999px;
}
.list::-webkit-scrollbar-track { background: transparent; }

.item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.list .item,
.li {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(27, 28, 31, 0.08);
  cursor: pointer;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 12px;
  animation: itemIn 0.25s ease;
}
.li { grid-template-columns: auto 1fr; }
.list .item:hover,
.li:hover { background: rgba(15, 123, 108, 0.08); }
.list .item.active,
.li.active {
  background: rgba(15, 123, 108, 0.18);
  box-shadow: inset 3px 0 0 var(--accent);
}
.li > div { display: flex; flex-direction: column; gap: 4px; }
.item .name { font-weight: 600; }
.item .meta { color: var(--muted); font-size: 12px; }

.detail-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
}
.hero-title {
  font-family: "Bricolage Grotesque", "IBM Plex Sans", sans-serif;
  font-size: 20px;
  font-weight: 700;
}
.hero-sub {
  font-size: 12px;
  color: var(--muted);
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.pill,
.chip {
  font-size: 11px;
  padding: 4px 10px;
  border: 1px solid rgba(27, 28, 31, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.6);
}
.chip {
  color: var(--ink);
  background: rgba(15, 123, 108, 0.08);
  border-color: rgba(15, 123, 108, 0.25);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}
.stat-card {
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px 12px;
  box-shadow: var(--shadow-soft);
}
.stat-label {
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}
.stat-value { margin-top: 6px; }
.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.stat-row .mono {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.stat-actions { flex: 0 0 auto; }

.section { border-top: 1px dashed rgba(27, 28, 31, 0.16); padding-top: 12px; }
.section-title {
  font-size: 11px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}
.list-lines { display: flex; flex-direction: column; gap: 6px; }
.line { display: flex; gap: 8px; align-items: baseline; }

.tool-card {
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.result-section {
  padding: 12px 16px;
  border-bottom: 1px dashed rgba(27, 28, 31, 0.12);
}
.result-section:last-child { border-bottom: none; }
.result-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.result-grid {
  display: grid;
  gap: 12px;
}
.result-card {
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
  animation: cardIn 0.4s ease both;
}
.result-card:hover {
  border-color: rgba(15, 123, 108, 0.4);
  transform: translateY(-1px);
}
.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}
.result-score { font-size: 12px; color: var(--muted); }
.result-missing { font-size: 12px; color: #9a3412; }
.result-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(27, 28, 31, 0.08);
  cursor: pointer;
  animation: cardIn 0.35s ease both;
}
.result-row:hover { background: rgba(15, 123, 108, 0.08); }
.formula {
  font-size: 12px;
  color: var(--muted);
}

.kv {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 6px 12px;
  font-size: 13px;
}
.kv .k { color: var(--muted); }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

.err {
  color: #7f1d1d;
  font-size: 12px;
  white-space: pre-wrap;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(185, 28, 28, 0.2);
  background: rgba(254, 242, 242, 0.9);
}
.err:empty { display: none; }
.ok { color: #059669; font-size: 12px; }
.muted { color: var(--muted); }
.small { font-size: 12px; }
.mono { font-family: "JetBrains Mono", "SFMono-Regular", monospace; }
#listCount {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px dashed var(--line);
  color: var(--muted);
}
#stats { color: var(--muted); font-size: 12px; }

.itemRef { display: inline-flex; align-items: center; gap: 8px; }
.itemIcon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid rgba(27, 28, 31, 0.2);
  background: rgba(15, 123, 108, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex: 0 0 auto;
}
.itemIconImg {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
  display: block;
}
.itemIconFallback {
  width: 100%;
  height: 100%;
  display: none;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--muted);
}
.itemLabel { color: var(--ink); }

.icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(27, 28, 31, 0.2);
  background: rgba(15, 123, 108, 0.08);
  object-fit: contain;
}
.icon.placeholder { display: inline-block; }

pre {
  margin: 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.7);
  box-shadow: var(--shadow-soft);
  overflow: auto;
  max-height: 520px;
  font-size: 12px;
  line-height: 1.35;
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
}
details summary { cursor: pointer; color: var(--muted); }
.err.fixed {
  position: fixed;
  bottom: 12px;
  left: 12px;
  right: 12px;
  z-index: 50;
}

/* Cooking page overrides */
body.page--cooking {
  --paper: #f9f1e6;
  --paper-2: #eadfce;
  --ink: #1f1a16;
  --muted: #7a6859;
  --accent: #c3523a;
  --accent-2: #1f7a72;
  --accent-soft: rgba(195, 82, 58, 0.18);
  --panel: rgba(255, 255, 255, 0.92);
  --panel-strong: #ffffff;
  --shadow: 0 28px 60px rgba(31, 26, 22, 0.14);
  --shadow-soft: 0 16px 32px rgba(31, 26, 22, 0.1);
  --radius: 20px;
  background:
    radial-gradient(760px 520px at 10% -20%, rgba(31, 122, 114, 0.2), transparent 60%),
    radial-gradient(820px 520px at 110% 0%, rgba(195, 82, 58, 0.22), transparent 60%),
    linear-gradient(180deg, var(--paper), var(--paper-2));
}
body.page--cooking::before {
  background-image:
    radial-gradient(rgba(31, 26, 22, 0.08) 0.6px, transparent 0.6px),
    repeating-linear-gradient(115deg, rgba(31, 26, 22, 0.05) 0, rgba(31, 26, 22, 0.05) 1px, transparent 1px, transparent 26px);
  background-size: 30px 30px, 240px 240px;
  opacity: 0.5;
}
body.page--cooking .header {
  background: rgba(249, 241, 230, 0.94);
  border-bottom: 1px solid rgba(31, 26, 22, 0.14);
}
body.page--cooking .brand {
  letter-spacing: 0.36em;
}
body.page--cooking .page-title {
  font-size: 22px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}
body.page--cooking .page-sub {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
body.page--cooking .search {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(31, 26, 22, 0.14);
  padding: 6px;
  border-radius: 999px;
  box-shadow: var(--shadow-soft);
}
body.page--cooking input[type="text"] {
  border-radius: 999px;
  box-shadow: none;
}
body.page--cooking .nav-link.active {
  background: var(--accent);
  border-color: var(--accent);
}
body.page--cooking .mode-toggle {
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(31, 26, 22, 0.12);
  box-shadow: var(--shadow-soft);
}
body.page--cooking .mode-btn {
  border: none;
  box-shadow: none;
  padding: 6px 14px;
}
body.page--cooking .mode-btn::before {
  content: attr(data-icon);
  margin-right: 6px;
  font-size: 12px;
}
body.page--cooking .layout {
  gap: 24px;
  padding: 24px;
}
body.page--cooking .list {
  max-height: min(64vh, 720px);
}
body.page--cooking .list .item,
body.page--cooking .result-row {
  border-bottom: 1px dashed rgba(31, 26, 22, 0.12);
}
body.page--cooking .list .item.active {
  background: rgba(195, 82, 58, 0.12);
  box-shadow: inset 3px 0 0 var(--accent);
}
body.page--cooking .result-grid {
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
}
body.page--cooking .panel {
  border: 1px solid rgba(31, 26, 22, 0.14);
  box-shadow: var(--shadow);
}
body.page--cooking .panel-head {
  position: relative;
  background: rgba(255, 255, 255, 0.78);
}
body.page--cooking .panel-head::before {
  content: "";
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 22px;
  border-radius: 999px;
  background: var(--accent-2);
}
body.page--cooking .panel-title {
  padding-left: 10px;
  letter-spacing: 0.28em;
}
body.page--cooking .panel--primary {
  border-color: rgba(31, 122, 114, 0.4);
  box-shadow: 0 32px 70px rgba(31, 122, 114, 0.18);
}
body.page--cooking .result-card {
  border-color: rgba(31, 26, 22, 0.12);
  background: rgba(255, 255, 255, 0.82);
}
body.page--cooking .result-card.is-ok,
body.page--cooking .result-row.is-ok {
  box-shadow: inset 4px 0 0 rgba(31, 122, 114, 0.6);
}
body.page--cooking .result-card.is-miss,
body.page--cooking .result-row.is-miss {
  box-shadow: inset 4px 0 0 rgba(195, 82, 58, 0.6);
}
body.page--cooking .result-card:hover {
  border-color: rgba(195, 82, 58, 0.45);
}
body.page--cooking .result-meta .pill {
  border-color: rgba(195, 82, 58, 0.25);
  background: rgba(195, 82, 58, 0.12);
}
body.page--cooking .result-missing {
  color: #8a3d22;
}
body.page--cooking .tool-card {
  border: 1px dashed rgba(31, 26, 22, 0.16);
  background: rgba(255, 255, 255, 0.7);
}
body.page--cooking .tool-ingredients {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
body.page--cooking .ingredient-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
body.page--cooking .ingredient-search {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
body.page--cooking .ingredient-search input {
  width: 100%;
  border-radius: 12px;
  border: 1px solid rgba(31, 26, 22, 0.16);
  background: rgba(255, 255, 255, 0.85);
  padding: 8px 10px;
  font-size: 12px;
}
body.page--cooking .ingredient-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
body.page--cooking .ingredient-filter {
  border: 1px solid rgba(31, 26, 22, 0.16);
  background: rgba(255, 255, 255, 0.7);
  color: var(--ink);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 11px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}
body.page--cooking .ingredient-filter.active {
  background: var(--accent-soft);
  border-color: rgba(195, 82, 58, 0.4);
}
body.page--cooking .ingredient-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  max-height: 240px;
  overflow: auto;
  padding-right: 4px;
}
body.page--cooking .ingredient-item {
  border: 1px solid rgba(31, 26, 22, 0.12);
  border-radius: 14px;
  padding: 6px 8px;
  background: rgba(255, 255, 255, 0.88);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
body.page--cooking .ingredient-item:hover {
  border-color: rgba(195, 82, 58, 0.45);
  transform: translateY(-1px);
}
body.page--cooking .ingredient-item .itemRef {
  display: flex;
  align-items: center;
  gap: 6px;
}
body.page--cooking .ingredient-meta {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-top: 4px;
  font-size: 10px;
  color: var(--muted);
}
body.page--cooking .formula {
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
  font-size: 11px;
}

#detailPanel,
#listPanel { scroll-margin-top: 150px; }

@keyframes panelRise {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes itemIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@media (max-width: 1280px) {
  .layout {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    grid-template-areas:
      "filters recipes"
      "detail detail";
  }
}
@media (max-width: 980px) {
  .subbar-right {
    width: 100%;
    justify-content: flex-start;
  }
  .search { max-width: none; }
  .meta,
  #meta { max-width: 100%; }
}
@media (max-width: 860px) {
  .header { position: static; }
  .topbar, .subbar { padding: 10px 14px; }
  .brand { font-size: 11px; letter-spacing: 0.28em; }
  .nav-link { padding: 4px 10px; }
  .page-title { font-size: 18px; }
  .page-sub { display: none; }
  .subbar-left { flex-direction: row; align-items: baseline; gap: 8px; }
  #detailPanel,
  #listPanel { scroll-margin-top: 12px; }
  .layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      "filters"
      "recipes"
      "detail";
    padding: 14px;
  }
  .wrap {
    grid-template-columns: 1fr;
    grid-template-areas:
      "list"
      "detail";
    padding: 14px;
  }
  .grid2 { grid-template-columns: 1fr; }
  .kv { grid-template-columns: 1fr; }
  .list { max-height: 42vh; }
  .btn.back { display: inline-flex; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
"""

_INDEX_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff WebCraft</title>
  <style>
__SHARED_CSS__
  </style>
</head>
<body>
  <header class="header">
    <div class="topbar">
      <div class="topbar-left">
        <div class="brand">Wagstaff <span class="brand-sub">Field Manual</span></div>
        <div class="nav-links">
          <a id="navCraft" class="nav-link active" href="#">Craft</a>
          <a id="navCooking" class="nav-link" href="#">Cooking</a>
          <a id="navCatalog" class="nav-link" href="#">Catalog</a>
        </div>
      </div>
      <div class="topbar-right">
        <div class="label-toggle">
          <span class="muted" id="labelModeLabel">Label</span>
          <select id="labelMode">
            <option value="en">EN</option>
            <option value="zh">中文</option>
            <option value="id">ID</option>
          </select>
        </div>
        <div class="meta" id="meta"></div>
      </div>
    </div>
    <div class="subbar">
      <div class="subbar-left">
        <div class="page-title">Craft Atlas</div>
        <div class="page-sub">Recipes and planning tools</div>
      </div>
      <div class="subbar-right">
        <div class="search">
          <input id="q" type="text" placeholder="Search: axe | ing:twigs | tag:bookbuilder | filter:TOOLS | tab:LIGHT" />
          <button id="btnSearch" class="primary">Search</button>
        </div>
      </div>
    </div>
  </header>

  <div class="layout">
    <div class="panel panel--filters">
      <div class="panel-head">
        <div class="panel-title" id="groupTitle">Filters</div>
        <div class="panel-actions">
          <button id="btnToggle" class="btn ghost">Toggle</button>
        </div>
      </div>
      <div class="list" id="groupList"></div>
    </div>

    <div class="panel panel--list" id="listPanel">
      <div class="panel-head">
        <div class="panel-title" id="listTitle">Recipes</div>
        <span class="small muted" id="listCount"></span>
      </div>
      <div class="list" id="recipeList"></div>
    </div>

    <div class="panel panel--primary" id="detailPanel">
      <div class="panel-head">
        <div class="panel-title"><span id="detailTitle">Details</span></div>
        <button class="btn ghost back" id="btnBackList">Back to list</button>
      </div>
      <div class="detail">
        <div id="detail"></div>

        <div class="tool-card">
          <div class="small muted" id="inventoryHelp">Inventory (for missing/planning)</div>
          <textarea id="inv" placeholder="twigs=2, flint=1
rocks=10"></textarea>
          <div class="grid2" style="margin-top:8px;">
            <div>
              <div class="small muted" id="builderTagLabel">builder_tag (optional)</div>
              <input id="builderTag" type="text" placeholder="bookbuilder / handyperson / ..." />
            </div>
            <div style="display:flex; gap:8px; align-items:flex-end;">
              <button id="btnPlan" class="primary" style="flex:1;">Plan</button>
              <button id="btnMissing" style="flex:1;">Missing</button>
            </div>
          </div>
          <div id="planOut" class="small" style="margin-top:8px;"></div>
        </div>

        <div class="err" id="err"></div>
      </div>
    </div>
  </div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const navCraft = document.getElementById('navCraft');
    if (navCraft) navCraft.href = APP_ROOT + '/';

    const navCooking = document.getElementById('navCooking');
    if (navCooking) navCooking.href = APP_ROOT + '/cooking';

    const navCatalog = document.getElementById('navCatalog');
    if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';

    const el = (id) => document.getElementById(id);
    const isNarrow = () => window.matchMedia('(max-width: 860px)').matches;
    const focusPanel = (id) => {
      if (!isNarrow()) return;
      const node = el(id);
      if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const focusDetail = () => focusPanel('detailPanel');
    const focusList = () => focusPanel('listPanel');
    const backBtn = el('btnBackList');
    if (backBtn) backBtn.onclick = () => focusList();
    const state = {
      mode: 'filters', // filters | tabs | tags
      groups: [],
      activeGroup: null,
      recipes: [],
      activeRecipe: null,
      activeRecipeData: null,
      assets: {},
      icon: null, // {mode, static_base, api_base}

      // label mode: en | zh | id (persisted in localStorage)
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    function setError(msg) {
      el('err').textContent = msg || '';
    }

    function parseInventory(text) {
      const out = {};
      const raw = (text || '').trim();
      if (!raw) return out;

      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        const m = p.match(/^([^=\s]+)\s*(?:=|\s)\s*([0-9]+(?:\.[0-9]+)?)$/);
        if (!m) continue;
        const k = m[1].trim();
        const v = parseFloat(m[2]);
        if (!k || !Number.isFinite(v) || v <= 0) continue;
        out[k] = v;
      }
      return out;
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    async function loadAssets() {
      try {
        const res = await fetchJson(api('/api/v1/assets'));
        state.assets = res.assets || {};
        state.icon = res.icon || null;
      } catch (e) {
        state.assets = {};
        state.icon = null;
      }
    }

    function _iconUrls(iid) {
      const cfg = state.icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/data/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'flex';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }

    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnPlan = el('btnPlan');
      if (btnPlan) btnPlan.textContent = t('btn.plan', 'Plan');
      const btnMissing = el('btnMissing');
      if (btnMissing) btnMissing.textContent = t('btn.missing', 'Missing');
      const btnToggle = el('btnToggle');
      if (btnToggle) btnToggle.textContent = t('btn.toggle', 'Toggle');
      const listTitle = el('listTitle');
      if (listTitle) {
        const txt = listTitle.textContent || '';
        if (!txt.includes(':') && !txt.includes('(')) {
          listTitle.textContent = t('craft.list.recipes', txt || 'Recipes');
        }
      }
      const groupTitle = el('groupTitle');
      if (groupTitle) {
        if (state.mode === 'filters') groupTitle.textContent = t('craft.group.filters', 'Filters');
        else if (state.mode === 'tabs') groupTitle.textContent = t('craft.group.tabs', 'Tabs');
        else groupTitle.textContent = t('craft.group.tags', 'Tags');
      }
      const detailTitle = el('detailTitle');
      if (detailTitle) detailTitle.textContent = t('craft.detail.title', 'Details');
      const invHelp = el('inventoryHelp');
      if (invHelp) invHelp.textContent = t('craft.inventory.help', 'Inventory (for missing/planning)');
      const builderLabel = el('builderTagLabel');
      if (builderLabel) builderLabel.textContent = t('craft.builder_tag.label', 'builder_tag (optional)');
      const input = el('q');
      if (input) input.placeholder = t('craft.search.placeholder', input.placeholder || '');
      const inv = el('inv');
      if (inv) inv.placeholder = t('craft.inventory.placeholder', inv.placeholder || '');
      const builderTag = el('builderTag');
      if (builderTag) builderTag.placeholder = t('craft.builder_tag.placeholder', builderTag.placeholder || '');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      setView(state.view);
      renderRecipeList();
      renderRecipeDetail(state.activeRecipeData);
      renderIngredientFilters();
      renderIngredientGrid();
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      if (!iid) return '';
      const m = (state.assets && state.assets[iid]) ? state.assets[iid] : null;
      const enName = (m && m.name) ? m.name : iid;
      const zhName = getI18nName(iid);
      const name = resolveLabel(iid, enName, zhName);

      const tipParts = [`id:${iid}`];
      if (enName && enName !== iid) tipParts.push(`en:${enName}`);
      if (zhName && zhName !== enName && zhName !== iid) tipParts.push(`zh:${zhName}`);
      if (m && m.image) tipParts.push(`img:${m.image}`);
      if (m && m.atlas) tipParts.push(`atlas:${m.atlas}`);
      const tip = escHtml(tipParts.join(' | '));

      const { src, fallback } = _iconUrls(iid);
      const iconChar = (m && (m.image || m.atlas)) ? '🖼️' : '📦';

      if (!src) {
        return `<span class="itemRef" title="${tip}">` +
          `<span class="itemIcon"><span class="itemIconFallback" style="display:flex;">${iconChar}</span></span>` +
          `<span class="itemLabel">${escHtml(name)}</span></span>`;
      }

      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span class="itemRef" title="${tip}">` +
        `<span class="itemIcon">` +
          `<img class="itemIconImg" src="${escHtml(src)}"${fbAttr} onerror="iconError(this)" alt="" />` +
          `<span class="itemIconFallback">${iconChar}</span>` +
        `</span>` +
        `<span class="itemLabel">${escHtml(name)}</span>` +
      `</span>`;
    }


    function renderGroupList() {
      const box = el('groupList');
      box.innerHTML = '';
      for (const g of state.groups) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
        div.innerHTML = `<span class="name">${g.name}</span><span class="meta">${g.count ?? ''}</span>`;
        div.onclick = () => selectGroup(g.name);
        box.appendChild(div);
      }
    }

    function renderRecipeList() {
      if (state.view !== 'encyclopedia') {
        renderResultList();
        return;
      }
      const formulaEl = el('formula');
      if (formulaEl) formulaEl.textContent = '';
      const box = el('recipeList');
      box.innerHTML = '';
      el('listCount').textContent = state.recipes.length ? `${state.recipes.length}` : '';
      for (const nm of state.recipes) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeRecipe === nm ? ' active' : '');
        div.innerHTML = `<span class="name">${renderItem(nm)}</span><span class="meta"></span>`;
        div.onclick = () => selectRecipe(nm);
        box.appendChild(div);
      }
    }

    function renderRecipeDetail(rec) {
      if (!rec) {
        el('detail').innerHTML = `<div class="muted">${escHtml(t('craft.detail.empty', 'Select a recipe.'))}</div>`;
        return;
      }
      const filters = (rec.filters || []).map(x => `<span class="chip">${x}</span>`).join('');
      const tags = (rec.builder_tags || []).map(x => `<span class="chip">${x}</span>`).join('');
      const ings = (rec.ingredients || []).map(i => {
        const item = i.item;
        const amt = i.amount ?? '';
        const num = i.amount_num;
        const extra = (num === null || num === undefined) ? ' <span class="muted">(?)</span>' : '';
        return `<div class="line"><span>•</span><span>${renderItem(item)} <span class="mono">x${escHtml(amt)}</span>${extra}</span></div>`;
      }).join('');
      const tabLabel = String(rec.tab || '').replace('RECIPETABS.','');
      const techLabel = String(rec.tech || '').replace('TECH.','');
      const heroSubParts = [];
      if (tabLabel) heroSubParts.push(`Tab: ${tabLabel}`);
      if (techLabel) heroSubParts.push(`Tech: ${techLabel}`);
      const heroSub = heroSubParts.length ? heroSubParts.join(' | ') : '-';
      const heroMeta = [tabLabel, techLabel].filter(Boolean).map(v => `<span class="pill">${escHtml(v)}</span>`).join('');
      const heroMetaHtml = heroMeta || '<span class="muted">-</span>';
      const statRows = [
        {
          label: t('craft.detail.product', 'Product'),
          value: rec.product ? renderItem(rec.product) : '<span class="muted">-</span>',
        },
        {
          label: t('craft.detail.tech', 'Tech'),
          value: techLabel ? `<span class="mono">${escHtml(techLabel)}</span>` : '<span class="muted">-</span>',
        },
        {
          label: t('craft.detail.station', 'Station'),
          value: rec.station_tag ? `<span class="mono">${escHtml(rec.station_tag)}</span>` : '<span class="muted">-</span>',
        },
        {
          label: t('craft.detail.builder_skill', 'Builder skill'),
          value: rec.builder_skill ? `<span class="mono">${escHtml(rec.builder_skill)}</span>` : '<span class="muted">-</span>',
        },
      ];
      const statCards = statRows.map(row => `
        <div class="stat-card">
          <div class="stat-label">${escHtml(row.label)}</div>
          <div class="stat-value">${row.value}</div>
        </div>
      `).join('');

      el('detail').innerHTML = `
        <div class="detail-hero">
          <div>
            <div class="hero-title">${renderItem(rec.name)}</div>
            <div class="hero-sub">${escHtml(heroSub)}</div>
          </div>
          <div class="hero-meta">${heroMetaHtml}</div>
        </div>
        <div class="stat-grid">
          ${statCards}
        </div>
        <div class="section">
          <div class="section-title">${escHtml(t('craft.detail.filters', 'Filters'))}</div>
          <div class="chips">${filters || '<span class="muted">-</span>'}</div>
        </div>
        <div class="section">
          <div class="section-title">${escHtml(t('craft.detail.builder_tags', 'Builder tags'))}</div>
          <div class="chips">${tags || '<span class="muted">-</span>'}</div>
        </div>
        <div class="section">
          <div class="section-title">${escHtml(t('craft.detail.ingredients', 'Ingredients'))}</div>
          <div class="list-lines">${ings || '<span class="muted">-</span>'}</div>
          ${(rec.ingredients_unresolved && rec.ingredients_unresolved.length)
            ? `<div class="muted small">${escHtml(t('craft.detail.unresolved', 'Unresolved'))}: ${rec.ingredients_unresolved.join(', ')}</div>`
            : ''}
        </div>
      `;
    }

    async function loadMeta() {
      const m = await fetchJson(api('/api/v1/meta'));
      state.i18n = (m && m.i18n) ? m.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(m && m.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = m.scripts_sha256_12 ? `sha:${m.scripts_sha256_12}` : '';
      const ae = m.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = m.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = `${sha} | mode:${m.engine_mode || ''} | files:${m.scripts_file_count || ''} | ${ae} | ${te}`;
    }

    async function loadGroups() {
      setError('');
      if (state.mode === 'filters') {
        el('groupTitle').textContent = t('craft.group.filters', 'Filters');
        const res = await fetchJson(api('/api/v1/craft/filters'));
        const order = res.order || [];
        state.groups = order.map(n => ({ name: n, count: '' }));
      } else if (state.mode === 'tabs') {
        el('groupTitle').textContent = t('craft.group.tabs', 'Tabs');
        const res = await fetchJson(api('/api/v1/craft/tabs'));
        state.groups = (res.tabs || []).map(t => ({ name: t.name, count: t.count }));
      } else {
        el('groupTitle').textContent = t('craft.group.tags', 'Tags');
        const res = await fetchJson(api('/api/v1/craft/tags'));
        state.groups = (res.tags || []).map(t => ({ name: t.name, count: t.count }));
      }

      state.activeGroup = null;
      state.recipes = [];
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectGroup(name) {
      setError('');
      state.activeGroup = name;
      renderGroupList();

      let url = '';
      if (state.mode === 'filters') url = api(`/api/v1/craft/filters/${encodeURIComponent(name)}/recipes`);
      else if (state.mode === 'tabs') url = api(`/api/v1/craft/tabs/${encodeURIComponent(name)}/recipes`);
      else url = api(`/api/v1/craft/tags/${encodeURIComponent(name)}/recipes`);

      const res = await fetchJson(url);
      state.recipes = (res.recipes || []);
      state.activeRecipe = null;
      state.activeRecipeData = null;

      el('listTitle').textContent = t('craft.list.recipes', 'Recipes');
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectRecipe(name) {
      setError('');
      state.activeRecipe = name;
      renderRecipeList();
      const res = await fetchJson(api(`/api/v1/craft/recipes/${encodeURIComponent(name)}`));
      state.activeRecipeData = res.recipe || null;
      renderRecipeDetail(state.activeRecipeData);
      focusDetail();
    }

    async function doSearch() {
      setError('');
      const q = el('q').value.trim();
      if (!q) return;
      const res = await fetchJson(api(`/api/v1/craft/recipes/search?q=${encodeURIComponent(q)}&limit=200`));
      const results = (res.results || []).map(r => r.name).filter(Boolean);
      state.recipes = results;
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = `${t('label.search', 'Search')}: ${q}`;
    }

    async function doPlan() {
      setError('');
      const inv = parseInventory(el('inv').value);
      const builderTag = el('builderTag').value.trim() || null;
      const payload = { inventory: inv, builder_tag: builderTag, strict: false, limit: 200 };
      const res = await fetchJson(api('/api/v1/craft/plan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const craftable = res.craftable || [];
      el('planOut').innerHTML = craftable.length
        ? `<div class="ok">${escHtml(t('craft.plan.craftable', 'Craftable'))} (${craftable.length})</div><div>${craftable.slice(0,120).map(n => renderItem(n)).join(', ')}</div>`
        : `<div class="muted">${escHtml(t('craft.plan.none', 'No craftable recipes with current inventory.'))}</div>`;
    }

    async function doMissing() {
      setError('');
      const nm = state.activeRecipe;
      if (!nm) {
        setError(t('craft.error.select_recipe', 'Select a recipe first.'));
        return;
      }
      const inv = parseInventory(el('inv').value);
      const res = await fetchJson(api('/api/v1/craft/missing'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: nm, inventory: inv }),
      });
      const miss = res.missing || [];
      if (!miss.length) {
        el('planOut').innerHTML = `<div class="ok">${escHtml(t('craft.missing.none', 'No missing materials.'))}</div>`;
        return;
      }
      const needLabel = t('label.need', 'need');
      const haveLabel = t('label.have', 'have');
      const reasonLabel = t('label.reason', 'reason');
      const lines = miss.map(m => `• ${renderItem(m.item)} ${escHtml(needLabel)}:${escHtml(m.need)} ${escHtml(haveLabel)}:${escHtml(m.have)} (${escHtml(reasonLabel)}:${escHtml(m.reason)})`).join('<br/>');
      el('planOut').innerHTML = `<div class="muted">${escHtml(t('craft.missing.title', 'Missing'))} (${miss.length})</div><div class="mono">${lines}</div>`;
    }

    function toggleMode() {
      if (state.mode === 'filters') state.mode = 'tabs';
      else if (state.mode === 'tabs') state.mode = 'tags';
      else state.mode = 'filters';
      loadGroups().catch(e => setError(String(e)));
    }

    // wire
    el('btnToggle').onclick = toggleMode;
    el('btnSearch').onclick = () => doSearch().catch(e => setError(String(e)));
    el('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch().catch(err => setError(String(err))); });
    el('btnPlan').onclick = () => doPlan().catch(e => setError(String(e)));
    el('btnMissing').onclick = () => doMissing().catch(e => setError(String(e)));

    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const recipe = params.get('recipe');
      const q = params.get('q');
      if (recipe) {
        selectRecipe(recipe).catch(e => setError(String(e)));
        return;
      }
      if (q) {
        el('q').value = q;
        doSearch().catch(e => setError(String(e)));
      }
    }

    // init
    (async () => {
      try {
        await loadMeta();
        await ensureI18nNames(state.labelMode);
        await loadAssets();
        await loadGroups();
        initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


_CATALOG_TEMPLATE = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff Catalog</title>
  <style>
__SHARED_CSS__
  </style>
</head>
<body>
  <header class="header">
    <div class="topbar">
      <div class="topbar-left">
        <div class="brand">Wagstaff <span class="brand-sub">Field Manual</span></div>
        <div class="nav-links">
          <a class="nav-link" id="navCraft" href="__WAGSTAFF_APP_ROOT__/">Craft</a>
          <a class="nav-link" id="navCooking" href="__WAGSTAFF_APP_ROOT__/cooking">Cooking</a>
          <a class="nav-link active" id="navCatalog" href="__WAGSTAFF_APP_ROOT__/catalog">Catalog</a>
        </div>
      </div>
      <div class="topbar-right">
        <div class="label-toggle">
          <span class="muted" id="labelModeLabel">Label</span>
          <select id="labelMode">
            <option value="en">EN</option>
            <option value="zh">中文</option>
            <option value="id">ID</option>
          </select>
        </div>
        <div class="meta" id="meta">...</div>
      </div>
    </div>
    <div class="subbar">
      <div class="subbar-left">
        <div class="page-title">Catalog Index</div>
        <div class="page-sub">Items, stats, and prefab links</div>
      </div>
      <div class="subbar-right">
        <div class="search">
          <input id="q" type="text" placeholder="Search item id / name. Examples: beefalo, axe, spear, monstermeat" />
          <button class="btn primary" id="btnSearch">Search</button>
        </div>
        <button class="btn ghost" id="btnAll">All</button>
      </div>
    </div>
  </header>

  <div class="wrap">
    <div class="panel panel--list" id="listPanel">
      <div class="panel-head">
        <div class="panel-title" id="listTitle">Catalog</div>
        <span class="small muted" id="stats"></span>
      </div>
      <div class="panel-body panel-body--meta">
        <div class="small muted" id="searchHelp">Hints: kind:structure cat:weapon src:craft tag:monster comp:equippable slot:head</div>
      </div>
      <div class="list" id="list"></div>
    </div>

    <div class="panel panel--primary" id="detailPanel">
      <div class="panel-head">
        <div class="panel-title" id="detailTitle">Item Detail</div>
        <button class="btn ghost back" id="btnBackList">Back to list</button>
      </div>
      <div class="detail" id="detail">
        <div class="muted" id="detailEmpty">Select an item.</div>
      </div>
    </div>
  </div>

  <div class="err fixed" id="err"></div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const el = (id) => document.getElementById(id);
    const isNarrow = () => window.matchMedia('(max-width: 860px)').matches;
    const focusPanel = (id) => {
      if (!isNarrow()) return;
      const node = el(id);
      if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const focusDetail = () => focusPanel('detailPanel');
    const focusList = () => focusPanel('listPanel');
    const backBtn = el('btnBackList');
    if (backBtn) backBtn.onclick = () => focusList();

    function setError(msg) {
      const box = el('err');
      if (!msg) { box.style.display = 'none'; box.textContent = ''; return; }
      box.style.display = 'block';
      box.textContent = String(msg);
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    function hasCjk(text) {
      return /[\u4e00-\u9fff]/.test(String(text || ''));
    }

    let meta = {};
    let assets = {};
    let icon = null; // {mode, static_base, api_base}
    let activeId = null;

    const state = {
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      tuningTrace: {},    // {trace_key: trace}
      tuningTraceEnabled: false,
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    // list render state (supports full catalog without freezing)
    let allKeys = [];
    let viewKeys = [];
    let renderPos = 0;
    const CHUNK = 240;
    const PAGE_SIZE = 400;
    let catalogTotal = 0;
    let searchTotal = 0;
    let listMode = 'all';
    let loadingPage = false;
    let loadedKeys = new Set();

    function _iconUrls(iid) {
      const cfg = icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/data/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'inline-block';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      if (!enabled) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }
    // ui i18n (catalog)
    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnAll = el('btnAll');
      if (btnAll) btnAll.textContent = t('btn.all', 'All');
      const input = el('q');
      if (input) input.placeholder = t('catalog.search.placeholder', input.placeholder || '');
      const hint = el('searchHelp');
      if (hint) hint.textContent = t('catalog.search.hint', hint.textContent || '');
      const detailEmpty = el('detailEmpty');
      if (detailEmpty) detailEmpty.textContent = t('catalog.detail.empty', 'Select an item.');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const q = el('q').value;
      await runSearch(q);
    }

    function iconHtmlFor(id, sizePx) {
      const iid = String(id || '').trim();
      const sz = Number(sizePx || 28);
      const { src, fallback } = _iconUrls(iid);
      if (!src) {
        return `<span class="icon placeholder" style="width:${sz}px;height:${sz}px;"></span>`;
      }
      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span style="display:inline-flex; align-items:center; justify-content:center;">` +
        `<img class="icon" style="width:${sz}px;height:${sz}px;" src="${escHtml(src)}" loading="lazy" onerror="iconError(this)"${fbAttr} />` +
        `<span class="icon placeholder" style="width:${sz}px;height:${sz}px; display:none;"></span>` +
        `</span>`;
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      const a = assets[iid] || assets[iid.toLowerCase()] || null;
      const zh = getI18nName(iid);
      const label = resolveLabel(iid, a?.name || iid, zh);
      const iconHtml = iconHtmlFor(iid, 30);
      return `<span class="item">${iconHtml}<span>${escHtml(label)}</span></span>`;
    }

    function listKeys() {
      return allKeys;
    }

    async function runSearch(q) {
      const query = String(q || '').trim();
      if (!query) {
        listMode = 'all';
        searchTotal = 0;
        renderList(listKeys());
        return;
      }
      listMode = 'search';
      try {
        const res = await fetchJson(api(`/api/v1/catalog/search?q=${encodeURIComponent(query)}&limit=800`));
        const items = res.items || [];
        searchTotal = Number(res.total || res.count || items.length);
        applyCatalogItems(items, false);
        const keys = [];
        items.forEach((it) => {
          const iid = String(it.id || '').trim();
          if (iid) keys.push(iid);
        });
        renderList(keys);
      } catch (e) {
        setError(String(e));
      }
    }

    function appendListChunk() {
      const box = el('list');
      if (renderPos >= viewKeys.length) return;

      const end = Math.min(renderPos + CHUNK, viewKeys.length);
      const frag = document.createDocumentFragment();

      for (let i = renderPos; i < end; i++) {
        const k = viewKeys[i];
        const a = assets[k] || {};
        const zh = getI18nName(k);
        const label = resolveLabel(k, a.name || k, zh);
        const div = document.createElement('div');
        div.className = 'li' + (k === activeId ? ' active' : '');
        div.dataset.id = k;

        const iconHtml = iconHtmlFor(k, 34);
        const metaBits = [];
        if (a.kind) metaBits.push(a.kind);
        if (a.categories && a.categories.length) metaBits.push(a.categories.slice(0, 2).join(','));
        if (a.sources && a.sources.length) metaBits.push(a.sources.slice(0, 2).join(','));
        const metaLine = metaBits.length ? `<div class="small muted">${escHtml(metaBits.join(' · '))}</div>` : '';
        div.innerHTML = `${iconHtml}<div><div>${escHtml(label)}</div><div class="small mono">${escHtml(k)}</div>${metaLine}</div>`;
        div.onclick = () => openItem(k).catch(e => setError(String(e)));
        frag.appendChild(div);
      }

      box.appendChild(frag);
      renderPos = end;

      // stats line
      const shown = Math.min(renderPos, viewKeys.length);
      const total = (listMode === 'search')
        ? (searchTotal || viewKeys.length)
        : (catalogTotal || allKeys.length);
      el('stats').textContent = `${total} items. Showing ${shown}/${viewKeys.length}.`;
    }

    function renderList(keys) {
      viewKeys = (keys || []).slice();
      renderPos = 0;
      const box = el('list');
      box.innerHTML = '';
      if (!viewKeys.length) {
        box.innerHTML = '<div class="pbody muted">No results.</div>';
        const total = (listMode === 'search')
          ? (searchTotal || 0)
          : (catalogTotal || allKeys.length);
        el('stats').textContent = `${total} items. Showing 0/0.`;
        return;
      }
      appendListChunk();
    }

    async function maybeLoadMore() {
      if (listMode !== 'all') return;
      if (loadingPage) return;
      if (catalogTotal && allKeys.length >= catalogTotal) return;
      const before = allKeys.length;
      await loadCatalogPage(allKeys.length);
      if (allKeys.length > before) {
        viewKeys = listKeys();
      }
    }

    function installInfiniteScroll() {
      const box = el('list');
      box.addEventListener('scroll', () => {
        if (box.scrollTop + box.clientHeight >= box.scrollHeight - 200) {
          appendListChunk();
          maybeLoadMore().then(() => appendListChunk());
        }
      });
    }

    function setActiveInList(id) {
      activeId = String(id || '').trim();
      for (const node of el('list').querySelectorAll('.li')) {
        if (node.dataset.id === activeId) node.classList.add('active');
        else node.classList.remove('active');
      }
    }


    function recipeLinkCraft(name) {

      return `${APP_ROOT}/?recipe=${encodeURIComponent(name)}`;
    }
    function recipeLinkCooking(name) {
      return `${APP_ROOT}/cooking?recipe=${encodeURIComponent(name)}`;
    }

    function renderRecipeList(names, hrefFn) {
      const arr = names || [];
      if (!arr.length) return '<span class="muted">-</span>';
      const lines = arr.slice(0, 80).map(n => `<div class="line"><span>•</span><span><a class="mono" href="${hrefFn(n)}">${escHtml(n)}</a></span></div>`).join('');
      const more = arr.length > 80 ? `<div class="muted">… +${arr.length-80} more</div>` : '';
      return `<div class="list-lines">${lines}${more}</div>`;
    }

    function renderChips(list, extraClass) {
      const arr = (list || []).filter(Boolean);
      if (!arr.length) return '<span class="muted">-</span>';
      const cls = extraClass ? ` ${extraClass}` : '';
      return arr.slice(0, 80).map(v => `<span class="chip${cls}">${escHtml(v)}</span>`).join('');
    }

    function renderMonoLines(list, limit) {
      const arr = (list || []).filter(Boolean);
      if (!arr.length) return '<span class="muted">-</span>';
      const cap = Math.max(1, Number(limit || 8));
      const lines = arr.slice(0, cap).map(v => `<div class="mono">${escHtml(v)}</div>`).join('');
      const more = arr.length > cap ? `<div class="muted small">… +${arr.length - cap} more</div>` : '';
      return `<div class="list-lines">${lines}${more}</div>`;
    }

    function renderAnalysis(rep) {
      if (!rep) return '<span class="muted">-</span>';
      const brain = rep.brain ? `<span class="chip mono">${escHtml(rep.brain)}</span>` : '<span class="muted">-</span>';
      const sg = rep.stategraph ? `<span class="chip mono">${escHtml(rep.stategraph)}</span>` : '<span class="muted">-</span>';
      const tags = (rep.tags || []).slice(0, 60).map(t => `<span class="chip mono">${escHtml(t)}</span>`).join('') || '<span class="muted">-</span>';
      const comps = (rep.components || []).slice(0, 80).map(c => `<span class="chip mono">${escHtml(c)}</span>`).join('') || '<span class="muted">-</span>';
      const evs = (rep.events || []).slice(0, 80).map(e => `<span class="chip mono">${escHtml(e)}</span>`).join('') || '<span class="muted">-</span>';

      return `
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.brain', 'Brain'))}</div>
          <div class="chips">${brain}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.stategraph', 'Stategraph'))}</div>
          <div class="chips">${sg}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.components', 'Components'))}</div>
          <div class="chips">${comps}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.tags', 'Tags'))}</div>
          <div class="chips">${tags}</div>
        </div>
        <div class="section">
          <div class="small muted">${escHtml(t('catalog.analysis.events', 'Events'))}</div>
          <div class="chips">${evs}</div>
        </div>
        <div class="section">
          <details>
            <summary>${escHtml(t('catalog.analysis.raw_report', 'Raw report (JSON)'))}</summary>
            <pre>${escHtml(JSON.stringify(rep, null, 2))}</pre>
          </details>
        </div>
      `;
    }

    async function openItem(id) {
      setError('');
      const q = String(id || '').trim();
      if (!q) return;
      setActiveInList(q);

      const data = await fetchJson(api(`/api/v1/items/${encodeURIComponent(q)}`));
      const item = data.item || {};
      const asset = data.asset || {};
      const craft = data.craft || {};
      const cooking = data.cooking || {};
      const iconHtml = iconHtmlFor(q, 64);

      const zh = getI18nName(q);
      const label = resolveLabel(q, item?.name || asset?.name || q, zh);
      const atlas = asset?.atlas || '';
      const image = asset?.image || '';
      const iconPath = asset?.icon || '';

      const kind = item?.kind || '';
      const categories = item?.categories || [];
      const behaviors = item?.behaviors || [];
      const sources = item?.sources || [];
      const slots = item?.slots || [];
      const components = item?.components || [];
      const tags = item?.tags || [];
      const prefabFiles = item?.prefab_files || [];
      const brains = item?.brains || [];
      const stategraphs = item?.stategraphs || [];
      const helpers = item?.helpers || [];
      const prefabAssets = item?.prefab_assets || [];
      const stats = item?.stats || {};

      const kindRow = [];
      if (kind) kindRow.push(kind);
      (sources || []).forEach((s) => kindRow.push(`src:${s}`));
      (slots || []).forEach((s) => kindRow.push(`slot:${s}`));

      const cookRec = cooking.as_recipe;

      function cookTraceForField(field) {
        if (!cookRec) return null;
        const v = cookRec[field];
        if (v && typeof v === 'object' && (v.trace || v.expr || v.value !== undefined)) return v;
        if (cookRec._tuning && cookRec._tuning[field]) return cookRec._tuning[field];
        const key = `cooking:${cookRec.name || q}:${field}`;
        return state.tuningTrace[key] || null;
      }

      function cookStat(field) {
        if (!cookRec) return '';
        const tr = cookTraceForField(field);
        if (tr && tr.value !== null && tr.value !== undefined) return tr.value;
        const val = cookRec[field];
        if (val && typeof val === 'object') {
          if (val.value !== undefined && val.value !== null) return val.value;
          if (val.expr !== undefined) return val.expr;
        }
        return val ?? '';
      }

      function renderCookStatRow(field) {
        if (!cookRec) return '<span class="muted">-</span>';
        const tr = cookTraceForField(field);
        const val = cookStat(field);
        const expr = tr ? (tr.expr ?? '') : '';
        const showExpr = expr && String(expr) !== String(val);
        const titleAttr = showExpr ? ` title="${escHtml(expr)}"` : '';
        const key = `cooking:${cookRec.name || q}:${field}`;
        const canTrace = Boolean(key);
        const enabled = Boolean(state.tuningTraceEnabled);
        const btn = canTrace
          ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';
        const details = tr
          ? `<details style="margin-top:4px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(tr, null, 2))}</pre></details>`
          : '';
        const main = (val !== null && val !== undefined && val !== '')
          ? `<span class="mono"${titleAttr}>${escHtml(val ?? '')}</span>`
          : `<span class="mono">${escHtml(expr ?? '')}</span>`;
        const actions = btn ? `<span class="stat-actions">${btn}</span>` : '';
        return `<div class="stat-row">${main}${actions}</div>${details}`;
      }

      const STAT_LABELS = {
        weapon_damage: 'Weapon Damage',
        weapon_range: 'Weapon Range',
        weapon_range_min: 'Weapon Range (min)',
        weapon_range_max: 'Weapon Range (max)',
        combat_damage: 'Combat Damage',
        attack_period: 'Attack Period',
        attack_range: 'Attack Range',
        attack_range_max: 'Attack Range (max)',
        area_damage: 'Area Damage',
        uses_max: 'Max Uses',
        uses: 'Uses',
        armor_condition: 'Armor Condition',
        armor_absorption: 'Armor Absorption',
        edible_health: 'Edible Health',
        edible_hunger: 'Edible Hunger',
        edible_sanity: 'Edible Sanity',
        perish_time: 'Perish Time',
        fuel_level: 'Fuel Level',
        fuel_max: 'Max Fuel',
        dapperness: 'Dapperness',
        insulation: 'Insulation',
        insulation_winter: 'Insulation (Winter)',
        insulation_summer: 'Insulation (Summer)',
        waterproof: 'Waterproof',
        light_radius: 'Light Radius',
        light_intensity: 'Light Intensity',
        light_falloff: 'Light Falloff',
        stack_size: 'Stack Size',
        health_max: 'Max Health',
        sanity_max: 'Max Sanity',
        sanity_rate: 'Sanity Rate',
        sanity_aura: 'Sanity Aura',
        hunger_max: 'Max Hunger',
        hunger_rate: 'Hunger Rate',
        walk_speed: 'Walk Speed',
        run_speed: 'Run Speed',
        speed_multiplier: 'Speed Multiplier',
        recharge_time: 'Recharge Time',
        recharge_percent: 'Recharge Percent',
        recharge_charge: 'Recharge Charge',
        equip_slot: 'Equip Slot',
        equip_walk_speed_mult: 'Equip Walk Speed Mult',
        equip_run_speed_mult: 'Equip Run Speed Mult',
        equip_restricted_tag: 'Equip Restricted Tag',
        equip_stack: 'Equip Stack',
        equip_insulated: 'Equip Insulated',
        equip_moisture: 'Equip Moisture',
        equip_moisture_max: 'Equip Moisture Max',
        equip_magic_dapperness: 'Equip Magic Dapperness',
        heat: 'Heat',
        heat_radius: 'Heat Radius',
        heat_radius_cutoff: 'Heat Radius Cutoff',
        heat_falloff: 'Heat Falloff',
        heater_exothermic: 'Heater Exothermic',
        heater_endothermic: 'Heater Endothermic',
        equipped_heat: 'Equipped Heat',
        carried_heat_multiplier: 'Carried Heat Mult',
        heat_rate: 'Heat Rate',
        planar_damage_base: 'Planar Damage (base)',
        planar_damage_bonus: 'Planar Damage (bonus)',
        planar_damage: 'Planar Damage',
        planar_absorption: 'Planar Absorption',
        planar_absorption_base: 'Planar Absorption (base)',
        work_left: 'Work Left',
      };

      function renderStatRow(statKey, entry) {
        const key = String(statKey || '');
        const label = t(`stat.${key}`, STAT_LABELS[key] || key);
        const val = entry?.value ?? entry?.expr ?? '';
        const expr = entry?.expr ?? '';
        const showExpr = expr && String(expr) !== String(val);
        const traceKey = entry?.trace_key || `item:${q}:stat:${key}`;
        const trace = entry?.trace || state.tuningTrace[traceKey];
        const enabled = Boolean(state.tuningTraceEnabled);
        const btn = traceKey
          ? `<button class="btn" data-item-trace="${escHtml(traceKey)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';
        const details = trace
          ? `<details style="margin-top:4px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(trace, null, 2))}</pre></details>`
          : '';
        const value = `<span class="mono">${escHtml(val ?? '')}</span>${showExpr ? ` <span class="small muted mono">${escHtml(expr)}</span>` : ''}${btn}${details}`;
        return `
          <div class="stat-card">
            <div class="stat-label">${escHtml(label)}</div>
            <div class="stat-value">${value}</div>
          </div>
        `;
      }

      function renderStats(statsObj) {
        const entries = Object.entries(statsObj || {});
        if (!entries.length) return '<span class="muted">-</span>';
        return `<div class="stat-grid">${entries.map(([k, v]) => renderStatRow(k, v)).join('')}</div>`;
      }

      const cookBrief = cookRec ? `
        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
          <div class="list-lines">
            <div class="line"><span>•</span><span><a class="mono" href="${recipeLinkCooking(cookRec.name || q)}">${escHtml(cookRec.name || q)}</a></span></div>
          </div>
          <div class="stat-grid" style="margin-top:8px;">
            <div class="stat-card"><div class="stat-label">${escHtml(t('label.hunger', 'Hunger'))}</div><div class="stat-value">${renderCookStatRow('hunger')}</div></div>
            <div class="stat-card"><div class="stat-label">${escHtml(t('label.health', 'Health'))}</div><div class="stat-value">${renderCookStatRow('health')}</div></div>
            <div class="stat-card"><div class="stat-label">${escHtml(t('label.sanity', 'Sanity'))}</div><div class="stat-value">${renderCookStatRow('sanity')}</div></div>
            <div class="stat-card"><div class="stat-label">${escHtml(t('label.perish', 'Perish'))}</div><div class="stat-value">${renderCookStatRow('perishtime')}</div></div>
            <div class="stat-card"><div class="stat-label">${escHtml(t('label.cooktime', 'Cooktime'))}</div><div class="stat-value">${renderCookStatRow('cooktime')}</div></div>
          </div>
        </div>
      ` : `
        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.cooking_recipe', 'Cooking recipe'))}</div>
          <span class="muted">-</span>
        </div>
      `;

      const analyzerEnabled = Boolean(meta.analyzer_enabled);
      const analyzerBox = analyzerEnabled ? `
        <div class="section">
          <div class="row" style="justify-content:space-between;">
            <div class="section-title">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
            <button class="btn" id="btnAnalyze">${escHtml(t('btn.analyze', 'Analyze'))}</button>
          </div>
          <div class="muted small">${escHtml(t('catalog.prefab_analysis_help', 'Uses server-side LuaAnalyzer (prefab parser). Availability depends on how the server was started.'))}</div>
          <div id="analysis"></div>
        </div>
      ` : `
        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.prefab_analysis', 'Prefab analysis'))}</div>
          <div class="muted">${escHtml(t('catalog.prefab_analysis_disabled', 'Analyzer disabled. Start server with enable_analyzer=true and provide scripts_dir / scripts_zip (or dst_root).'))}</div>
        </div>
      `;

      el('detail').innerHTML = `
        <div class="detail-hero">
          <div class="row" style="align-items:center; gap:12px;">
            ${iconHtml}
            <div>
              <div class="hero-title">${escHtml(label)}</div>
              <div class="hero-sub mono">${escHtml(q)}</div>
            </div>
          </div>
          <div class="hero-meta">${renderChips(kindRow, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.stats', 'Stats'))}</div>
          ${renderStats(stats)}
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.categories', 'Categories'))}</div>
          <div class="chips">${renderChips(categories, '')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.behaviors', 'Behaviors'))}</div>
          <div class="chips">${renderChips(behaviors, '')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.components', 'Components'))}</div>
          <div class="chips">${renderChips(components, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.tags', 'Tags'))}</div>
          <div class="chips">${renderChips(tags, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.brains', 'Brains'))}</div>
          <div class="chips">${renderChips(brains, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.stategraphs', 'Stategraphs'))}</div>
          <div class="chips">${renderChips(stategraphs, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.helpers', 'Helpers'))}</div>
          <div class="chips">${renderChips(helpers, 'mono')}</div>
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.prefab_files', 'Prefab files'))}</div>
          ${renderMonoLines(prefabFiles, 6)}
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.assets', 'Assets'))}</div>
          <div class="list-lines">
            <div class="mono">${escHtml(t('label.icon', 'icon'))}: ${escHtml(iconPath || '-')}</div>
            <div class="mono">${escHtml(t('label.atlas', 'atlas'))}: ${escHtml(atlas || '-')}</div>
            <div class="mono">${escHtml(t('label.image', 'image'))}: ${escHtml(image || '-')}</div>
          </div>
        </div>

        ${prefabAssets && prefabAssets.length ? `<div class="section"><details><summary class="section-title">${escHtml(t('catalog.section.prefab_assets', 'Prefab assets (raw)'))}</summary><pre>${escHtml(JSON.stringify(prefabAssets, null, 2))}</pre></details></div>` : ''}

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.craft_produced', 'Craft: produced by'))}</div>
          ${renderRecipeList(craft.produced_by, recipeLinkCraft)}
        </div>

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.craft_used', 'Craft: used as ingredient'))}</div>
          ${renderRecipeList(craft.used_in, recipeLinkCraft)}
        </div>

        ${cookBrief}

        <div class="section">
          <div class="section-title">${escHtml(t('catalog.section.cooking_used', 'Cooking: used as card ingredient'))}</div>
          ${renderRecipeList(cooking.used_in, recipeLinkCooking)}
        </div>

        ${analyzerBox}
      `;

      if (analyzerEnabled) {
        el('btnAnalyze').onclick = async () => {
          try {
            setError('');
            el('analysis').innerHTML = `<div class="muted">${escHtml(t('label.loading', 'Loading...'))}</div>`;
            const res = await fetchJson(api(`/api/v1/analyze/prefab/${encodeURIComponent(q)}`));
            const rep = res.report || {};
            el('analysis').innerHTML = renderAnalysis(rep);
          } catch (e) {
            el('analysis').innerHTML = '';
            setError(String(e));
          }
        };
      }
      if (cookRec) {
        for (const btn of el('detail').querySelectorAll('button[data-cook-trace]')) {
          const field = btn.getAttribute('data-cook-trace');
          if (!field) continue;
          btn.onclick = async () => {
            try {
              setError('');
              await fetchTuningTrace(`cooking:${cookRec.name || q}:${field}`);
              await openItem(q);
            } catch (e) {
              setError(String(e));
            }
          };
        }
      }

      for (const btn of el('detail').querySelectorAll('button[data-item-trace]')) {
        const key = btn.getAttribute('data-item-trace');
        if (!key) continue;
        btn.onclick = async () => {
          try {
            setError('');
            await fetchTuningTrace(key);
            await openItem(q);
          } catch (e) {
            setError(String(e));
          }
        };
      }
      focusDetail();
    }

    async function loadMeta() {
      meta = await fetchJson(api('/api/v1/meta'));
      state.i18n = (meta && meta.i18n) ? meta.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(meta && meta.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = meta.scripts_sha256_12 ? `sha:${meta.scripts_sha256_12}` : '';
      const ver = meta.schema_version ? `v${meta.schema_version}` : '';
      const ae = meta.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = meta.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = [ver, sha, ae, te].filter(Boolean).join(' · ');

      el('navCraft').href = APP_ROOT + '/';
      el('navCooking').href = APP_ROOT + '/cooking';
      el('navCatalog').href = APP_ROOT + '/catalog';
    }

    function applyCatalogItems(items, updateList) {
      const trackList = (updateList !== false);
      (items || []).forEach((it) => {
        const iid = String(it.id || '').trim();
        if (!iid) return;
        if (trackList) {
          if (loadedKeys.has(iid)) return;
          loadedKeys.add(iid);
        }
        assets[iid] = {
          name: it.name || iid,
          image: it.image || null,
          icon: it.icon || it.image || null,
          kind: it.kind || '',
          categories: Array.isArray(it.categories) ? it.categories : [],
          behaviors: Array.isArray(it.behaviors) ? it.behaviors : [],
          sources: Array.isArray(it.sources) ? it.sources : [],
          tags: Array.isArray(it.tags) ? it.tags : [],
          components: Array.isArray(it.components) ? it.components : [],
          slots: Array.isArray(it.slots) ? it.slots : [],
        };
        if (trackList) allKeys.push(iid);
      });
    }

    async function loadCatalogPage(offset) {
      if (loadingPage) return [];
      loadingPage = true;
      try {
        const res = await fetchJson(api(`/api/v1/catalog/index?offset=${offset}&limit=${PAGE_SIZE}`));
        icon = res.icon || icon;
        catalogTotal = Number(res.total || res.count || 0);
        const items = res.items || [];
        applyCatalogItems(items, true);
        return items;
      } finally {
        loadingPage = false;
      }
    }

    async function loadAssets() {
      assets = {};
      allKeys = [];
      loadedKeys = new Set();
      listMode = 'all';
      searchTotal = 0;
      await loadCatalogPage(0);
      const total = catalogTotal || allKeys.length;
      el('stats').textContent = `${total} items. Showing 0/0.`;
    }

    async function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const item = params.get('item');
      const q = params.get('q');
      if (q) {
        el('q').value = q;
        await runSearch(q);
        return;
      }
      if (item) {
        el('q').value = item;
        await runSearch(item);
        openItem(item).catch(e => setError(String(e)));
      }
    }

    el('btnSearch').onclick = () => {
      setError('');
      const q = el('q').value;
      runSearch(q).catch(e => setError(String(e)));
    };

    el('btnAll').onclick = () => {
      try {
        setError('');
        el('q').value = '';
        listMode = 'all';
        searchTotal = 0;
        renderList(listKeys());
      } catch (e) { setError(String(e)); }
    };

    el('q').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') el('btnSearch').click();
    });

    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    (async () => {
      try {
        await loadMeta();
        await loadAssets();
        await ensureI18nNames(state.labelMode);
        installInfiniteScroll();
        renderList(listKeys());
        await initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


def render_catalog_html(app_root: str = "") -> str:
    """Render the Catalog UI page."""
    from html import escape as _esc

    root = str(app_root or "")
    css = _SHARED_CSS.replace("__WAGSTAFF_APP_ROOT__", root)
    return _CATALOG_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", _esc(root)).replace("__SHARED_CSS__", css)



def render_index_html(app_root: str = "") -> str:
    """Render the UI page.

    app_root:
      - ""       normal direct serving
      - "/xxx"   reverse proxy mount path
    """
    root = str(app_root or "")
    css = _SHARED_CSS.replace("__WAGSTAFF_APP_ROOT__", root)
    return _INDEX_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", escape(root)).replace("__SHARED_CSS__", css)


_COOKING_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="app-root" content="__WAGSTAFF_APP_ROOT__" />
  <title>Wagstaff WebCraft - Cooking</title>
  <style>
__SHARED_CSS__
  </style>
</head>
<body class="page--cooking" data-view="encyclopedia">
  <header class="header">
    <div class="topbar">
      <div class="topbar-left">
        <div class="brand">Wagstaff <span class="brand-sub">Field Manual</span></div>
        <div class="nav-links">
          <a id="navCraft" class="nav-link" href="#">Craft</a>
          <a id="navCooking" class="nav-link active" href="#">Cooking</a>
          <a id="navCatalog" class="nav-link" href="#">Catalog</a>
        </div>
      </div>
      <div class="topbar-right">
        <div class="label-toggle">
          <span class="muted" id="labelModeLabel">Label</span>
          <select id="labelMode">
            <option value="en">EN</option>
            <option value="zh">中文</option>
            <option value="id">ID</option>
          </select>
        </div>
        <div class="meta" id="meta"></div>
      </div>
    </div>
    <div class="subbar">
      <div class="subbar-left">
        <div class="page-title" id="pageTitle">Cooking Lab</div>
        <div class="page-sub" id="pageSub">Recipe rules and cookpot tools</div>
        <div class="mode-toggle" id="modeToggle">
          <button class="btn mode-btn active" data-mode="encyclopedia" data-icon="📖" id="modeEncy">Encyclopedia</button>
          <button class="btn mode-btn" data-mode="explore" data-icon="🧭" id="modeExplore">Explore</button>
          <button class="btn mode-btn" data-mode="simulate" data-icon="⚗️" id="modeSim">Simulate</button>
        </div>
      </div>
      <div class="subbar-right">
        <div class="search" id="searchBar">
          <input id="q" type="text" placeholder="Search: meatballs | ing:berries | tag:honeyed | type:FOODTYPE.MEAT" />
          <button id="btnSearch" class="primary">Search</button>
        </div>
      </div>
    </div>
  </header>

  <div class="layout">
    <div class="panel panel--filters" id="filterPanel">
      <div class="panel-head">
        <div class="panel-title" id="groupTitle">FoodTypes</div>
        <div class="panel-actions">
          <button id="btnToggle" class="btn ghost">Toggle</button>
        </div>
      </div>
      <div class="list" id="groupList"></div>
    </div>

    <div class="panel panel--list" id="listPanel">
      <div class="panel-head">
        <div class="panel-title" id="listTitle">Recipes</div>
        <div class="panel-actions">
          <span class="small muted" id="listCount"></span>
          <button id="btnShowAll" class="btn ghost">Show all</button>
          <button id="btnViewCards" class="btn ghost">Cards</button>
          <button id="btnViewDense" class="btn ghost">Dense</button>
        </div>
      </div>
      <div class="list" id="recipeList"></div>
    </div>

    <div class="panel panel--primary" id="detailPanel">
      <div class="panel-head">
        <div class="panel-title"><span id="detailTitle">Details / Tools</span></div>
        <button class="btn ghost back" id="btnBackList">Back to list</button>
      </div>
      <div class="detail">
        <div id="detail"></div>

        <div class="tool-card" id="toolExplore">
          <div class="small muted" id="slotsHelp">Cookpot slots (<=4 for explore, =4 for simulate)</div>
          <textarea id="slots" placeholder="carrot=2\nberries=1\nbutterflywings=1"></textarea>
          <div class="row">
            <button id="btnExplore" class="primary">Explore</button>
            <button id="btnSim" class="btn">Simulate</button>
          </div>
        </div>

        <div class="tool-card tool-ingredients" id="ingredientPicker">
          <div class="ingredient-head">
            <div class="small muted" id="ingredientTitle">Ingredient picker</div>
            <button id="ingredientClear" class="btn ghost">Clear slots</button>
          </div>
          <div class="ingredient-search">
            <input id="ingredientSearch" type="text" placeholder="Filter ingredients..." />
            <div class="small muted" id="ingredientHint">Click to add, Shift/Alt to remove</div>
          </div>
          <div class="ingredient-filters" id="ingredientFilters"></div>
          <div class="ingredient-grid" id="ingredientGrid"></div>
        </div>

        <div class="tool-card">
          <div class="small muted" id="resultTitle">Results</div>
          <div class="small muted" id="formula"></div>
          <div id="out" class="small"></div>
        </div>

        <div class="err" id="err"></div>
      </div>
    </div>
  </div>

  <script>
    const APP_ROOT = (document.querySelector('meta[name="app-root"]')?.content || '').replace(/\/+$/,'');
    const api = (path) => APP_ROOT + path;

    const el = (id) => document.getElementById(id);
    const isNarrow = () => window.matchMedia('(max-width: 860px)').matches;
    const focusPanel = (id) => {
      if (!isNarrow()) return;
      const node = el(id);
      if (node) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const focusDetail = () => focusPanel('detailPanel');
    const focusList = () => focusPanel('listPanel');
    const backBtn = el('btnBackList');
    if (backBtn) backBtn.onclick = () => focusList();

    function setError(msg) {
      el('err').textContent = msg || '';
    }

    function parseInventory(text) {
      const out = {};
      const raw = (text || '').trim();
      if (!raw) return out;

      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        const m = p.match(/^([^=\s]+)\s*(?:=|\s)\s*([0-9]+(?:\.[0-9]+)?)$/);
        if (!m) continue;
        const k = m[1].trim();
        const v = parseFloat(m[2]);
        if (!k || !Number.isFinite(v) || v <= 0) continue;
        out[k] = v;
      }
      return out;
    }

    function parseSlots(text) {
      const raw = (text || '').trim();
      if (!raw) return {};

      // prefer explicit counts
      const asInv = parseInventory(raw);
      if (Object.keys(asInv).length) return asInv;

      // fallback: "a, b, c" means each counts as 1
      const out = {};
      const parts = raw
        .split(/[,\n]/g)
        .map(s => s.trim())
        .filter(Boolean);

      for (const p of parts) {
        out[p] = (out[p] || 0) + 1;
      }
      return out;
    }

    async function fetchJson(url, opts) {
      const r = await fetch(url, opts || {});
      if (!r.ok) {
        const t = await r.text();
        throw new Error(`HTTP ${r.status} ${r.statusText}\n${t}`);
      }
      return await r.json();
    }

    function escHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, (c) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
      }[c]));
    }

    async function loadAssets() {
      try {
        const res = await fetchJson(api('/api/v1/assets'));
        state.assets = res.assets || {};
        state.icon = res.icon || null;
      } catch (e) {
        state.assets = {};
        state.icon = null;
      }
    }

    function _iconUrls(iid) {
      const cfg = state.icon || {};
      const mode = String(cfg.mode || 'off');
      const enc = encodeURIComponent(iid);
      const staticBaseRaw = String(cfg.static_base || '/static/data/icons');
      const staticBase = (APP_ROOT && staticBaseRaw.startsWith('/') && !staticBaseRaw.startsWith(APP_ROOT + '/'))
        ? (APP_ROOT + staticBaseRaw)
        : staticBaseRaw;
      const apiBase = String(cfg.api_base || '/api/v1/icon');
      const staticUrl = api(`${staticBase}/${enc}.png`);
      const apiUrl = api(`${apiBase}/${enc}.png`);

      if (mode === 'dynamic') return { src: apiUrl, fallback: '' };
      if (mode === 'static') return { src: staticUrl, fallback: apiUrl };
      if (mode === 'auto') return { src: staticUrl, fallback: apiUrl };
      return { src: '', fallback: '' };
    }

    function iconError(img) {
      try {
        const fb = img?.dataset?.fallback || '';
        const tried = img?.dataset?.fallbackTried || '';
        if (fb && !tried) {
          img.dataset.fallbackTried = '1';
          img.src = fb;
          return;
        }
        img.style.display = 'none';
        const nxt = img.nextElementSibling;
        if (nxt) nxt.style.display = 'flex';
      } catch (e) {
        // ignore
      }
    }

    function _altId(iid) {
      if (!iid) return '';
      const s = String(iid);
      if (s.includes('_')) return s.replace(/_/g,'');
      return '';
    }

    function getI18nName(iid) {
      const mp = (state.i18nNames && state.i18nNames.zh) ? state.i18nNames.zh : null;
      if (!mp) return '';
      const k = String(iid || '').trim();
      if (!k) return '';
      const lo = k.toLowerCase();
      const a1 = _altId(k);
      const a2 = _altId(lo);
      return mp[k] || mp[lo] || (a1 ? mp[a1] : '') || (a2 ? mp[a2] : '') || '';
    }

    async function ensureI18nNames(mode) {
      if (String(mode || '') !== 'zh') return;
      if (state.i18nLoaded && state.i18nLoaded.zh) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      if (!enabled) return;
      try {
        const res = await fetchJson(api('/api/v1/i18n/names/zh'));
        state.i18nNames.zh = res.names || {};
        state.i18nLoaded.zh = true;
      } catch (e) {
        state.i18nLoaded.zh = false;
      }
    }

    // ui i18n (cooking)
    function uiLang() {
      return (state.labelMode === 'zh') ? 'zh' : 'en';
    }

    async function ensureUiStrings(lang) {
      const l = String(lang || '').trim();
      if (!l) return;
      if (state.uiLoaded && state.uiLoaded[l]) return;
      try {
        const res = await fetchJson(api(`/api/v1/i18n/ui/${encodeURIComponent(l)}`));
        state.uiStrings[l] = res.strings || {};
        state.uiLoaded[l] = true;
      } catch (e) {
        state.uiStrings[l] = {};
        state.uiLoaded[l] = false;
      }
    }

    function t(key, fallback) {
      const l = uiLang();
      const mp = (state.uiStrings && state.uiStrings[l]) ? state.uiStrings[l] : {};
      return (mp && mp[key]) ? mp[key] : (fallback || key || '');
    }

    function applyUiStrings() {
      const navCraft = el('navCraft');
      if (navCraft) navCraft.textContent = t('nav.craft', 'Craft');
      const navCooking = el('navCooking');
      if (navCooking) navCooking.textContent = t('nav.cooking', 'Cooking');
      const navCatalog = el('navCatalog');
      if (navCatalog) navCatalog.textContent = t('nav.catalog', 'Catalog');
      const label = el('labelModeLabel');
      if (label) label.textContent = t('label.mode', 'Label');
      const modeEncy = el('modeEncy');
      if (modeEncy) modeEncy.textContent = t('cooking.mode.encyclopedia', 'Encyclopedia');
      const modeExplore = el('modeExplore');
      if (modeExplore) modeExplore.textContent = t('cooking.mode.explore', 'Explore');
      const modeSim = el('modeSim');
      if (modeSim) modeSim.textContent = t('cooking.mode.simulate', 'Simulate');
      const btnSearch = el('btnSearch');
      if (btnSearch) btnSearch.textContent = t('btn.search', 'Search');
      const btnToggle = el('btnToggle');
      if (btnToggle) btnToggle.textContent = t('btn.toggle', 'Toggle');
      const listTitle = el('listTitle');
      if (listTitle) {
        const txt = listTitle.textContent || '';
        if (!txt.includes(':') && !txt.includes('(')) {
          listTitle.textContent = t('cooking.list.recipes', txt || 'Recipes');
        }
      }
      const groupTitle = el('groupTitle');
      if (groupTitle) {
        if (state.mode === 'foodtypes') groupTitle.textContent = t('cooking.group.foodtypes', 'FoodTypes');
        else if (state.mode === 'tags') groupTitle.textContent = t('cooking.group.tags', 'Tags');
        else groupTitle.textContent = t('cooking.group.all', 'All');
      }
      const detailTitle = el('detailTitle');
      if (detailTitle) detailTitle.textContent = t('cooking.detail.title', 'Details / Tools');
      const slotsHelp = el('slotsHelp');
      if (slotsHelp) slotsHelp.textContent = t('cooking.slots.help', 'Cookpot slots (<=4 for explore, =4 for simulate)');
      const input = el('q');
      if (input) input.placeholder = t('cooking.search.placeholder', input.placeholder || '');
      const slots = el('slots');
      if (slots) slots.placeholder = t('cooking.slots.placeholder', slots.placeholder || '');
      const btnShowAll = el('btnShowAll');
      if (btnShowAll) btnShowAll.textContent = t('btn.show_all', 'Show all');
      const btnExplore = el('btnExplore');
      if (btnExplore) btnExplore.textContent = t('btn.explore', 'Explore');
      const btnSim = el('btnSim');
      if (btnSim) btnSim.textContent = t('btn.simulate', 'Simulate');
      const btnViewCards = el('btnViewCards');
      if (btnViewCards) btnViewCards.textContent = t('btn.view_cards', 'Cards');
      const btnViewDense = el('btnViewDense');
      if (btnViewDense) btnViewDense.textContent = t('btn.view_dense', 'Dense');
      const resultTitle = el('resultTitle');
      if (resultTitle) resultTitle.textContent = t('cooking.results.title', 'Results');
      const ingredientTitle = el('ingredientTitle');
      if (ingredientTitle) ingredientTitle.textContent = t('cooking.ingredients.title', 'Ingredient picker');
      const ingredientHint = el('ingredientHint');
      if (ingredientHint) ingredientHint.textContent = t('cooking.ingredients.hint', 'Click to add, Shift/Alt to remove');
      const ingredientSearch = el('ingredientSearch');
      if (ingredientSearch) ingredientSearch.placeholder = t('cooking.ingredients.search', ingredientSearch.placeholder || 'Filter ingredients...');
      const ingredientClear = el('ingredientClear');
      if (ingredientClear) ingredientClear.textContent = t('cooking.ingredients.clear', 'Clear slots');
    }

    async function fetchTuningTrace(prefix) {
      if (!state.tuningTraceEnabled) return {};
      const pfx = String(prefix || '').trim();
      if (!pfx) return {};
      const res = await fetchJson(api(`/api/v1/tuning/trace?prefix=${encodeURIComponent(pfx)}`));
      const traces = res.traces || {};
      for (const k in traces) {
        if (!Object.prototype.hasOwnProperty.call(traces, k)) continue;
        state.tuningTrace[k] = traces[k];
      }
      return traces;
    }

    function applyLabelModeUI() {
      const sel = el('labelMode');
      if (!sel) return;
      const enabled = Boolean(state.i18n && state.i18n.enabled);
      const optZh = sel.querySelector('option[value="zh"]');
      if (optZh) optZh.disabled = !enabled;
      if (!enabled && state.labelMode === 'zh') {
        state.labelMode = 'en';
        try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      }
      sel.value = state.labelMode || 'en';
    }

    function resolveLabel(iid, enName, zhName) {
      const mode = String(state.labelMode || 'en');
      if (mode === 'id') return iid;
      if (mode === 'zh' && zhName) return zhName;
      return enName || iid;
    }

    async function setLabelMode(mode) {
      state.labelMode = String(mode || 'en');
      try { localStorage.setItem('ws_label_mode', state.labelMode); } catch (e) {}
      applyLabelModeUI();
      await ensureI18nNames(state.labelMode);
      await ensureUiStrings(uiLang());
      applyUiStrings();
      renderRecipeList();
      renderRecipeDetail(state.activeRecipeData);
    }

    function renderItem(id) {
      const iid = String(id || '').trim();
      if (!iid) return '';
      const m = (state.assets && state.assets[iid]) ? state.assets[iid] : null;
      const enName = (m && m.name) ? m.name : iid;
      const zhName = getI18nName(iid);
      const name = resolveLabel(iid, enName, zhName);

      const tipParts = [`id:${iid}`];
      if (enName && enName !== iid) tipParts.push(`en:${enName}`);
      if (zhName && zhName !== enName && zhName !== iid) tipParts.push(`zh:${zhName}`);
      if (m && m.image) tipParts.push(`img:${m.image}`);
      if (m && m.atlas) tipParts.push(`atlas:${m.atlas}`);
      const tip = escHtml(tipParts.join(' | '));

      const { src, fallback } = _iconUrls(iid);
      const iconChar = (m && (m.image || m.atlas)) ? '🖼️' : '📦';

      if (!src) {
        return `<span class="itemRef" title="${tip}">` +
          `<span class="itemIcon"><span class="itemIconFallback" style="display:flex;">${iconChar}</span></span>` +
          `<span class="itemLabel">${escHtml(name)}</span></span>`;
      }

      const fbAttr = fallback ? ` data-fallback="${escHtml(fallback)}"` : '';
      return `<span class="itemRef" title="${tip}">` +
        `<span class="itemIcon">` +
          `<img class="itemIconImg" src="${escHtml(src)}"${fbAttr} onerror="iconError(this)" alt="" />` +
          `<span class="itemIconFallback">${iconChar}</span>` +
        `</span>` +
        `<span class="itemLabel">${escHtml(name)}</span>` +
      `</span>`;
    }


    const state = {
      mode: 'foodtypes', // foodtypes | tags | all
      view: 'encyclopedia', // encyclopedia | explore | simulate
      listView: localStorage.getItem('ws_cooking_list') || 'card',
      results: null,
      groups: [],
      activeGroup: null,
      recipes: [],
      activeRecipe: null,
      activeRecipeData: null,
      assets: {},
      icon: null, // {mode, static_base, api_base}
      ingredients: [],
      ingredientFilter: 'all',
      ingredientQuery: '',
      ingredientSource: '',

      // label mode: en | zh | id (persisted in localStorage)
      labelMode: localStorage.getItem('ws_label_mode') || 'en',
      i18n: null,         // meta from /api/v1/meta (set in loadMeta)
      i18nNames: {},      // {lang: {id: name}}
      i18nLoaded: {},     // {lang: true}
      tuningTrace: {},    // {trace_key: trace}
      tuningTraceEnabled: false,
      uiStrings: {},      // {lang: {key: text}}
      uiLoaded: {},       // {lang: true}
    };

    const ING_CATEGORIES = [
      { key: 'all', label: () => t('cooking.ingredients.all', 'All'), tags: [] },
      { key: 'meat', label: () => t('cooking.ingredients.meat', 'Meat'), tags: ['meat'] },
      { key: 'veggie', label: () => t('cooking.ingredients.veggie', 'Veggie'), tags: ['veggie', 'vegetable'] },
      { key: 'fruit', label: () => t('cooking.ingredients.fruit', 'Fruit'), tags: ['fruit'] },
      { key: 'fish', label: () => t('cooking.ingredients.fish', 'Fish'), tags: ['fish'] },
      { key: 'egg', label: () => t('cooking.ingredients.egg', 'Egg'), tags: ['egg'] },
      { key: 'dairy', label: () => t('cooking.ingredients.dairy', 'Dairy'), tags: ['dairy'] },
      { key: 'sweetener', label: () => t('cooking.ingredients.sweetener', 'Sweetener'), tags: ['sweetener'] },
      { key: 'fungus', label: () => t('cooking.ingredients.fungus', 'Fungus'), tags: ['fungus', 'mushroom'] },
      { key: 'monster', label: () => t('cooking.ingredients.monster', 'Monster'), tags: ['monster'] },
      { key: 'inedible', label: () => t('cooking.ingredients.filler', 'Filler'), tags: ['inedible', 'filler'] },
      { key: 'other', label: () => t('cooking.ingredients.other', 'Other'), tags: [] },
    ];

    const ING_GUESS = {
      meat: ['meat', 'morsel', 'drumstick', 'froglegs', 'batwing', 'smallmeat', 'monstermeat', 'leafymeat'],
      fish: ['fish', 'eel', 'salmon', 'tuna', 'perch', 'trout', 'barnacle'],
      egg: ['egg'],
      dairy: ['milk', 'butter', 'cheese'],
      sweetener: ['honey', 'sugar', 'nectar', 'syrup'],
      fruit: ['berries', 'berry', 'banana', 'pomegranate', 'watermelon', 'dragonfruit', 'durian', 'fig'],
      veggie: ['carrot', 'corn', 'pumpkin', 'eggplant', 'pepper', 'potato', 'tomato', 'onion', 'garlic', 'asparagus', 'cactus', 'kelp'],
      fungus: ['mushroom', 'cap'],
      monster: ['monster', 'durian'],
      inedible: ['twigs', 'ice'],
    };

    function setView(view) {
      state.view = String(view || 'encyclopedia');
      document.body.dataset.view = state.view;

      for (const btn of document.querySelectorAll('.mode-btn')) {
        const v = btn.getAttribute('data-mode');
        btn.classList.toggle('active', v === state.view);
      }

      const btnShowAll = el('btnShowAll');
      if (btnShowAll) btnShowAll.style.display = (state.view === 'encyclopedia') ? '' : 'none';
      const btnViewCards = el('btnViewCards');
      if (btnViewCards) btnViewCards.style.display = (state.view === 'encyclopedia') ? 'none' : '';
      const btnViewDense = el('btnViewDense');
      if (btnViewDense) btnViewDense.style.display = (state.view === 'encyclopedia') ? 'none' : '';
      const picker = el('ingredientPicker');
      if (picker) picker.style.display = (state.view === 'encyclopedia') ? 'none' : '';

      const title = el('pageTitle');
      const sub = el('pageSub');
      if (title) {
        title.textContent = (state.view === 'simulate')
          ? t('cooking.title.simulate', 'Cooking Simulate')
          : (state.view === 'explore' ? t('cooking.title.explore', 'Cooking Explore') : t('cooking.title.encyclopedia', 'Cooking Lab'));
      }
      if (sub) {
        sub.textContent = (state.view === 'simulate')
          ? t('cooking.sub.simulate', 'Simulate results with full slots')
          : (state.view === 'explore' ? t('cooking.sub.explore', 'Explore recipes with partial slots') : t('cooking.sub.encyclopedia', 'Recipe rules and cookpot tools'));
      }

      if (state.view !== 'encyclopedia') {
        const listTitle = el('listTitle');
        if (listTitle) listTitle.textContent = (state.view === 'simulate')
          ? t('cooking.list.simulate', 'Simulate')
          : t('cooking.list.explore', 'Explore');
        const listCount = el('listCount');
        if (listCount) listCount.textContent = '';
      }

      renderRecipeList();
    }

    function setListView(view) {
      state.listView = String(view || 'card');
      try { localStorage.setItem('ws_cooking_list', state.listView); } catch (e) {}
      const btnViewCards = el('btnViewCards');
      if (btnViewCards) btnViewCards.classList.toggle('active', state.listView === 'card');
      const btnViewDense = el('btnViewDense');
      if (btnViewDense) btnViewDense.classList.toggle('active', state.listView === 'dense');
      renderRecipeList();
    }

    function formatMissing(missing) {
      const rows = Array.isArray(missing) ? missing : [];
      if (!rows.length) return '';
      const parts = rows.slice(0, 4).map((m) => {
        const key = String(m.key || '').trim();
        const delta = Number(m.delta || 0);
        const dir = String(m.direction || '');
        const prefix = (m.type === 'name') ? 'name:' : 'tag:';
        if (!key) return '';
        if (dir === 'under') return `${prefix}${key} +${delta.toFixed(1)}`;
        if (dir === 'over') return `${prefix}${key} -${delta.toFixed(1)}`;
        if (dir === 'mismatch') return `${prefix}${key} != ${Number(m.required || 0).toFixed(1)}`;
        return `${prefix}${key}`;
      }).filter(Boolean);
      if (!parts.length) return '';
      const suffix = rows.length > 4 ? ' ...' : '';
      return parts.join(', ') + suffix;
    }

    function renderResultList() {
      const box = el('recipeList');
      box.innerHTML = '';
      const res = state.results;
      const formula = res && res.formula ? String(res.formula) : '';
      const formulaEl = el('formula');
      if (formulaEl) {
        formulaEl.textContent = formula ? `${t('label.formula', 'Formula')}: ${formula}` : '';
      }
      if (!res) {
        box.innerHTML = `<div class="muted">${escHtml(t('cooking.results.empty', 'Run explore or simulate to see results.'))}</div>`;
        el('listCount').textContent = '';
        return;
      }

      const cookable = Array.isArray(res.cookable) ? res.cookable : [];
      const near = Array.isArray(res.near_miss) ? res.near_miss : [];
      el('listCount').textContent = (cookable.length || near.length) ? `${cookable.length}/${near.length}` : '';
      const mode = res._mode || state.view;
      el('listTitle').textContent = (mode === 'simulate')
        ? t('cooking.list.simulate', 'Simulate')
        : t('cooking.list.explore', 'Explore');

      const sections = [
        { title: t('cooking.results.cookable', 'Cookable'), items: cookable },
        { title: t('cooking.results.near', 'Near miss'), items: near },
      ];

      let animIdx = 0;
      for (const sec of sections) {
        const wrap = document.createElement('div');
        wrap.className = 'result-section';
        const header = document.createElement('div');
        header.className = 'result-header';
        header.innerHTML = `<div class="panel-title">${escHtml(sec.title)}</div><div class="small muted">${sec.items.length}</div>`;
        wrap.appendChild(header);

        if (!sec.items.length) {
          const empty = document.createElement('div');
          empty.className = 'muted small';
          empty.textContent = t('cooking.results.none', 'None');
          wrap.appendChild(empty);
          box.appendChild(wrap);
          continue;
        }

        if (state.listView === 'dense') {
          for (const row of sec.items) {
            const name = String(row.name || '').trim();
            if (!name) continue;
            const missing = formatMissing(row.missing || []) || t('label.ok', 'OK');
            const score = Number(row.score || 0);
            const rule = row.rule_mode ? String(row.rule_mode).toUpperCase() : '';
            const meta = `p=${Number(row.priority || 0)} · w=${Number(row.weight || 0)} · s=${score.toFixed(1)}${rule ? ' · ' + rule : ''}`;
            const div = document.createElement('div');
            const isMiss = Array.isArray(row.missing) && row.missing.length > 0;
            div.className = `result-row ${isMiss ? 'is-miss' : 'is-ok'}`;
            div.style.animationDelay = `${Math.min(animIdx * 0.03, 0.4)}s`;
            animIdx += 1;
            div.innerHTML = `<div>${renderItem(name)}<div class="small muted">${escHtml(meta)}</div></div>` +
              `<div class="result-missing">${escHtml(missing || '')}</div>`;
            div.onclick = () => selectRecipe(name);
            wrap.appendChild(div);
          }
          box.appendChild(wrap);
          continue;
        }

        const grid = document.createElement('div');
        grid.className = 'result-grid';
        for (const row of sec.items) {
          const name = String(row.name || '').trim();
          if (!name) continue;
          const missing = formatMissing(row.missing || []) || t('label.ok', 'OK');
          const score = Number(row.score || 0);
          const rule = row.rule_mode ? String(row.rule_mode).toUpperCase() : '';
          const card = document.createElement('div');
          const isMiss = Array.isArray(row.missing) && row.missing.length > 0;
          card.className = `result-card ${isMiss ? 'is-miss' : 'is-ok'}`;
          card.style.animationDelay = `${Math.min(animIdx * 0.03, 0.4)}s`;
          animIdx += 1;
          card.innerHTML = `
            <div>${renderItem(name)}</div>
            <div class="result-meta">
              <span class="pill">p=${escHtml(Number(row.priority || 0))}</span>
              <span class="pill">w=${escHtml(Number(row.weight || 0))}</span>
              <span class="pill">s=${escHtml(score.toFixed(1))}</span>
              ${rule ? `<span class="pill">${escHtml(rule)}</span>` : ''}
            </div>
            <div class="result-missing">${escHtml(missing || '')}</div>
          `;
          card.onclick = () => selectRecipe(name);
          grid.appendChild(card);
        }
        wrap.appendChild(grid);
        box.appendChild(wrap);
      }
    }

    function _guessTagsFromId(iid) {
      const out = new Set();
      const name = String(iid || '').toLowerCase();
      for (const key in ING_GUESS) {
        for (const needle of ING_GUESS[key]) {
          if (name.includes(needle)) {
            out.add(key);
            break;
          }
        }
      }
      return Array.from(out);
    }

    function _normalizeIngredient(raw) {
      if (!raw) return null;
      const id = String(raw.id || raw.item_id || raw.name || '').trim();
      if (!id) return null;
      const tags = new Set();
      const rawTags = raw.tags;
      if (Array.isArray(rawTags)) {
        for (const t of rawTags) tags.add(String(t).toLowerCase());
      } else if (rawTags && typeof rawTags === 'object') {
        for (const t of Object.keys(rawTags)) tags.add(String(t).toLowerCase());
      }
      const foodtype = raw.foodtype ? String(raw.foodtype).toLowerCase().replace('foodtype.', '') : '';
      if (foodtype) tags.add(foodtype);
      if (!tags.size) {
        for (const t of _guessTagsFromId(id)) tags.add(t);
      }
      return {
        id: id,
        tags: Array.from(tags),
        uses: Number(raw.uses || 0),
      };
    }

    function _ingredientLabel(item) {
      const m = (state.assets && state.assets[item.id]) ? state.assets[item.id] : null;
      const enName = (m && m.name) ? m.name : item.id;
      const zhName = getI18nName(item.id);
      return resolveLabel(item.id, enName, zhName);
    }

    function _ingredientMatchesCategory(item, key) {
      if (key === 'all') return true;
      if (key === 'other') {
        for (const cat of ING_CATEGORIES) {
          if (cat.key === 'all' || cat.key === 'other') continue;
          if (_ingredientMatchesCategory(item, cat.key)) return false;
        }
        return true;
      }
      const cat = ING_CATEGORIES.find(c => c.key === key);
      if (!cat) return true;
      return (cat.tags || []).some(tag => item.tags.includes(tag));
    }

    function _ingredientQueryMatch(item) {
      const q = String(state.ingredientQuery || '').trim().toLowerCase();
      if (!q) return true;
      const label = _ingredientLabel(item).toLowerCase();
      return String(item.id).toLowerCase().includes(q) || label.includes(q);
    }

    function renderIngredientFilters() {
      const box = el('ingredientFilters');
      if (!box) return;
      box.innerHTML = '';
      const items = state.ingredients || [];
      for (const cat of ING_CATEGORIES) {
        const count = items.filter(it => _ingredientMatchesCategory(it, cat.key)).length;
        if (cat.key === 'other' && !count) continue;
        const btn = document.createElement('button');
        btn.className = 'ingredient-filter' + (state.ingredientFilter === cat.key ? ' active' : '');
        btn.textContent = `${cat.label()}${count ? ' (' + count + ')' : ''}`;
        btn.onclick = () => {
          state.ingredientFilter = cat.key;
          renderIngredientFilters();
          renderIngredientGrid();
        };
        box.appendChild(btn);
      }
    }

    function renderIngredientGrid() {
      const grid = el('ingredientGrid');
      if (!grid) return;
      grid.innerHTML = '';
      if (!state.ingredients.length) {
        grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty', 'Ingredient index not ready.'))}</div>`;
        return;
      }
      const items = state.ingredients.filter(it => _ingredientMatchesCategory(it, state.ingredientFilter)).filter(_ingredientQueryMatch);
      if (!items.length) {
        grid.innerHTML = `<div class="muted small">${escHtml(t('cooking.ingredients.empty_filter', 'No ingredients match.'))}</div>`;
        return;
      }
      for (const item of items) {
        const btn = document.createElement('button');
        btn.className = 'ingredient-item';
        const uses = item.uses ? `${item.uses} recipes` : '';
        const tags = item.tags.length ? item.tags.join(', ') : '';
        btn.title = `${item.id}${tags ? ' | ' + tags : ''}`;
        btn.innerHTML = `
          <div>${renderItem(item.id)}</div>
          <div class="ingredient-meta"><span>${escHtml(uses)}</span><span>${escHtml(tags)}</span></div>
        `;
        btn.onclick = (e) => {
          const delta = (e.shiftKey || e.altKey) ? -1 : 1;
          updateSlots(item.id, delta);
        };
        btn.oncontextmenu = (e) => {
          e.preventDefault();
          updateSlots(item.id, -1);
        };
        grid.appendChild(btn);
      }
    }

    function formatSlots(inv) {
      const keys = Object.keys(inv || {}).filter(Boolean).sort();
      return keys.map(k => `${k}=${inv[k]}`).join('\n');
    }

    function updateSlots(itemId, delta) {
      const slots = el('slots');
      if (!slots) return;
      const inv = parseSlots(slots.value);
      const cur = Number(inv[itemId] || 0);
      const next = cur + Number(delta || 0);
      if (next <= 0) delete inv[itemId];
      else inv[itemId] = Math.max(0, next);
      slots.value = formatSlots(inv);
      slots.dispatchEvent(new Event('input', { bubbles: true }));
    }

    async function loadIngredients() {
      try {
        const res = await fetchJson(api('/api/v1/cooking/ingredients'));
        const raw = Array.isArray(res.ingredients) ? res.ingredients : [];
        const items = raw.map(_normalizeIngredient).filter(Boolean);
        state.ingredients = items;
        state.ingredientSource = String(res.source || '');
      } catch (e) {
        state.ingredients = [];
        state.ingredientSource = '';
      }
      const hint = el('ingredientHint');
      if (hint && state.ingredientSource) {
        const srcLabel = (state.ingredientSource === 'cooking_ingredients')
          ? t('cooking.ingredients.source.tags', 'ingredient tags')
          : t('cooking.ingredients.source.card', 'card ingredients');
        hint.textContent = `${t('cooking.ingredients.hint', 'Click to add, Shift/Alt to remove')} · ${srcLabel}`;
      }
      renderIngredientFilters();
      renderIngredientGrid();
    }

    function renderGroupList() {
      const box = el('groupList');
      box.innerHTML = '';
      for (const g of state.groups) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeGroup === g.name ? ' active' : '');
        div.innerHTML = `<span class="name">${g.name}</span><span class="meta">${g.count ?? ''}</span>`;
        div.onclick = () => selectGroup(g.name);
        box.appendChild(div);
      }
    }

    function renderRecipeList() {
      if (state.view !== 'encyclopedia') {
        renderResultList();
        return;
      }
      const formulaEl = el('formula');
      if (formulaEl) formulaEl.textContent = '';
      const box = el('recipeList');
      box.innerHTML = '';
      el('listCount').textContent = state.recipes.length ? `${state.recipes.length}` : '';
      for (const nm of state.recipes) {
        const div = document.createElement('div');
        div.className = 'item' + (state.activeRecipe === nm ? ' active' : '');
        div.innerHTML = `<span class="name">${renderItem(nm)}</span><span class="meta"></span>`;
        div.onclick = () => selectRecipe(nm);
        box.appendChild(div);
      }
    }

    function renderRecipeDetail(rec) {
      if (!rec) {
        el('detail').innerHTML = `<div class="muted">${escHtml(t('cooking.detail.empty', 'Select a recipe.'))}</div>`;
        return;
      }

      const tags = (rec.tags || []).map(x => `<span class="chip">${x}</span>`).join('');
      const card = (rec.card_ingredients || []).map(row => {
        const item = row[0];
        const cnt = row[1];
        return `<div class="line"><span>•</span><span>${renderItem(item)} <span class="mono">x${escHtml(cnt)}</span></span></div>`;
      }).join('');


      const rule = rec.rule || null;

      function renderRule(rule, includeTitle = true) {
        if (!rule) return '';
        const kind = escHtml(rule.kind || '');
        const expr = escHtml(rule.expr || '');
        const cons = rule.constraints || null;
        const title = includeTitle
          ? `<div class="section-title">${escHtml(t('cooking.rule.title', 'Rule'))}${kind ? ` (${kind})` : ''}</div>`
          : '';

        let consHtml = '';
        if (cons) {
          const tags = (cons.tags || []).map(c => `<div class="line"><span>•</span><span class="mono">${escHtml(c.text || '')}</span></div>`).join('');
          const names = (cons.names || []).map(c => `<div class="line"><span>•</span><span class="mono">${escHtml(c.text || '')}</span></div>`).join('');
          const unp = (cons.unparsed || []).map(x => `<div class="line"><span>•</span><span class="mono">${escHtml(x)}</span></div>`).join('');
          const any = Boolean(tags || names || unp);
          consHtml = `
            <div style="margin-top:8px;">
              <div class="section-title">${escHtml(t('cooking.rule.constraints', 'Constraints (best-effort)'))}</div>
              ${tags ? `<div><div class="small muted">${escHtml(t('cooking.rule.constraints.tags', 'tags'))}</div><div class="list-lines">${tags}</div></div>` : ''}
              ${names ? `<div style="margin-top:6px;"><div class="small muted">${escHtml(t('cooking.rule.constraints.names', 'names'))}</div><div class="list-lines">${names}</div></div>` : ''}
              ${unp ? `<div style="margin-top:6px;"><div class="small muted">${escHtml(t('cooking.rule.constraints.unparsed', 'unparsed'))}</div><div class="list-lines">${unp}</div></div>` : ''}
              ${any ? '' : '<span class="muted">-</span>'}
            </div>
          `;
        }

        return `
          ${title}
          <div class="mono small" style="white-space:pre-wrap; line-height:1.35;">${expr || '<span class="muted">-</span>'}</div>
          ${consHtml}
        `;
      }

      const cardBody = card
        ? `<div class="list-lines">${card}</div>`
        : (rule ? renderRule(rule, false) : '<span class="muted">-</span>');
      const tuning = rec._tuning || {};
      const traceKey = (field) => rec?.name ? `cooking:${rec.name}:${field}` : '';
      const traceCache = state.tuningTrace || {};
      const fields = ['hunger', 'health', 'sanity', 'perishtime', 'cooktime'];

      function traceForField(field) {
        const raw = rec ? rec[field] : null;
        if (raw && typeof raw === 'object' && (raw.trace || raw.expr || raw.value !== undefined)) return raw;
        if (tuning && tuning[field]) return tuning[field];
        const key = traceKey(field);
        return key ? traceCache[key] : null;
      }

      function renderStat(field) {
        const raw = rec ? rec[field] : null;
        const tr = traceForField(field);
        const expr = tr ? (tr.expr ?? raw ?? '') : (raw ?? '');
        const val = tr && (tr.value !== null && tr.value !== undefined) ? tr.value : raw;
        const hasVal = (val !== null && val !== undefined && val !== '');
        const showExpr = expr && String(expr) !== String(val);
        const titleAttr = showExpr ? ` title="${escHtml(expr)}"` : '';

        const main = hasVal
          ? `<span class="mono"${titleAttr}>${escHtml(val)}</span>`
          : `<span class="mono">${escHtml(expr ?? '')}</span>`;

        const enabled = Boolean(state.tuningTraceEnabled);
        const key = traceKey(field);
        const btn = key
          ? `<button class="btn" data-cook-trace="${escHtml(field)}" ${enabled ? '' : 'disabled'} style="margin-left:6px; padding:2px 6px; font-size:11px;">${escHtml(t('btn.trace', 'Trace'))}</button>`
          : '';

        const details = tr
          ? `<details style="margin-top:6px;"><summary class="small muted">${escHtml(t('label.trace', 'Trace'))}</summary><pre>${escHtml(JSON.stringify(tr, null, 2))}</pre></details>`
          : '';

        const actions = btn ? `<span class="stat-actions">${btn}</span>` : '';
        return `<div class="stat-row">${main}${actions}</div>${details}`;
      }

      const extraRule = (card && rule)
        ? `<div style="margin-top:10px;">${renderRule(rule, true)}</div>`
        : '';
      const foodType = String(rec.foodtype || '').replace('FOODTYPE.','');
      const heroMeta = foodType ? `<span class="pill">${escHtml(foodType)}</span>` : '<span class="muted">-</span>';
      const statRows = [
        {
          label: t('label.priority', 'Priority'),
          value: `<span class="mono">${escHtml(rec.priority ?? '')}</span>`,
        },
        { label: t('label.hunger', 'Hunger'), value: renderStat('hunger') },
        { label: t('label.health', 'Health'), value: renderStat('health') },
        { label: t('label.sanity', 'Sanity'), value: renderStat('sanity') },
        { label: t('label.perish', 'Perish'), value: renderStat('perishtime') },
        { label: t('label.cooktime', 'Cooktime'), value: renderStat('cooktime') },
      ];
      const statCards = statRows.map(row => `
        <div class="stat-card">
          <div class="stat-label">${escHtml(row.label)}</div>
          <div class="stat-value">${row.value}</div>
        </div>
      `).join('');

      el('detail').innerHTML = `
        <div class="detail-hero">
          <div>
            <div class="hero-title">${renderItem(rec.name || '')}</div>
            <div class="hero-sub">${escHtml(foodType || '-')}</div>
          </div>
          <div class="hero-meta">${heroMeta}</div>
        </div>
        <div class="stat-grid">
          ${statCards}
        </div>
        <div class="section">
          <div class="section-title">${escHtml(t('label.tags', 'Tags'))}</div>
          <div class="chips">${tags || '<span class="muted">-</span>'}</div>
        </div>
        <div class="section">
          <div class="section-title">${escHtml(card ? t('cooking.card.ingredients', 'Card ingredients') : (rule ? t('cooking.rule.conditional', 'Recipe rule (conditional)') : t('cooking.card.ingredients', 'Card ingredients')))}</div>
          ${cardBody}
          ${extraRule}
        </div>
      `;

      for (const btn of el('detail').querySelectorAll('button[data-cook-trace]')) {
        const field = btn.getAttribute('data-cook-trace');
        if (!field || !rec.name) continue;
        btn.onclick = async () => {
          try {
            setError('');
            await fetchTuningTrace(`cooking:${rec.name}:${field}`);
            renderRecipeDetail(rec);
          } catch (e) {
            setError(String(e));
          }
        };
      }
    }

    async function loadMeta() {
      const m = await fetchJson(api('/api/v1/meta'));
      state.i18n = (m && m.i18n) ? m.i18n : { enabled: false };
      state.tuningTraceEnabled = Boolean(m && m.tuning_trace_enabled);
      applyLabelModeUI();
      await ensureUiStrings(uiLang());
      applyUiStrings();
      const sha = m.scripts_sha256_12 ? `sha:${m.scripts_sha256_12}` : '';
      const ae = m.analyzer_enabled ? 'analyzer:on' : 'analyzer:off';
      const te = m.tuning_enabled ? 'tuning:on' : 'tuning:off';
      el('meta').textContent = `${sha} | mode:${m.engine_mode || ''} | files:${m.scripts_file_count || ''} | ${ae} | ${te}`;
    }

    async function loadGroups() {
      setError('');

      if (state.mode === 'foodtypes') {
        el('groupTitle').textContent = t('cooking.group.foodtypes', 'FoodTypes');
        const res = await fetchJson(api('/api/v1/cooking/foodtypes'));
        state.groups = (res.foodtypes || []).map(t => ({ name: t.name, count: t.count }));
      } else if (state.mode === 'tags') {
        el('groupTitle').textContent = t('cooking.group.tags', 'Tags');
        const res = await fetchJson(api('/api/v1/cooking/tags'));
        state.groups = (res.tags || []).map(t => ({ name: t.name, count: t.count }));
      } else {
        el('groupTitle').textContent = t('cooking.group.all', 'All');
        const res = await fetchJson(api('/api/v1/cooking/recipes'));
        state.groups = [{ name: 'ALL', count: res.count || '' }];
      }

      state.activeGroup = null;
      state.recipes = [];
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectGroup(name) {
      setError('');
      state.activeGroup = name;
      renderGroupList();

      let url = '';
      if (state.mode === 'foodtypes') url = api(`/api/v1/cooking/foodtypes/${encodeURIComponent(name)}/recipes`);
      else if (state.mode === 'tags') url = api(`/api/v1/cooking/tags/${encodeURIComponent(name)}/recipes`);
      else url = api('/api/v1/cooking/recipes');

      const res = await fetchJson(url);
      state.recipes = (res.recipes || []);
      state.activeRecipe = null;
      state.activeRecipeData = null;

      el('listTitle').textContent = (state.mode === 'all')
        ? t('cooking.list.all_recipes', 'All recipes')
        : t('cooking.list.recipes', 'Recipes');
      renderRecipeList();
      renderRecipeDetail(null);
    }

    async function selectRecipe(name) {
      setError('');
      state.activeRecipe = name;
      renderRecipeList();
      const res = await fetchJson(api(`/api/v1/cooking/recipes/${encodeURIComponent(name)}`));
      state.activeRecipeData = res.recipe || null;
      // ensure name always present
      if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = name;
      renderRecipeDetail(state.activeRecipeData);
      focusDetail();
    }

    async function doSearch() {
      setError('');
      const q = el('q').value.trim();
      if (!q) return;
      setView('encyclopedia');
      const res = await fetchJson(api(`/api/v1/cooking/recipes/search?q=${encodeURIComponent(q)}&limit=200`));
      const results = (res.results || []).map(r => r.name).filter(Boolean);
      state.recipes = results;
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = `${t('label.search', 'Search')}: ${q}`;
    }

    async function showAll() {
      setError('');
      setView('encyclopedia');
      const res = await fetchJson(api('/api/v1/cooking/recipes'));
      state.recipes = (res.recipes || []);
      state.activeGroup = null;
      state.activeRecipe = null;
      state.activeRecipeData = null;
      renderGroupList();
      renderRecipeList();
      renderRecipeDetail(null);
      el('listTitle').textContent = t('cooking.list.all_recipes', 'All recipes');
    }

    async function doExplore() {
      setError('');
      const slots = parseSlots(el('slots').value);
      const res = await fetchJson(api('/api/v1/cooking/explore'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slots: slots, limit: 200 }),
      });

      if (!res.ok) {
        el('out').innerHTML = `<div class="err">${res.error || 'explore_failed'} (total=${res.total ?? ''})</div>`;
        return;
      }

      state.results = Object.assign({ _mode: 'explore' }, res);
      renderRecipeList();
      el('out').innerHTML = `<div class="small muted">${escHtml(t('cooking.results.summary', 'Explore results updated.'))}</div>`;
    }

    async function doSimulate() {
      setError('');
      const slots = parseSlots(el('slots').value);
      const total = Object.values(slots).reduce((acc, v) => acc + Number(v || 0), 0);
      if (total < 4) {
        await doExplore();
        return;
      }
      const res = await fetchJson(api('/api/v1/cooking/simulate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slots: slots, return_top: 20 }),
      });

      if (!res.ok) {
        el('out').innerHTML = `<div class="err">${res.error || 'simulation_failed'} (total=${res.total ?? ''})</div>`;
        return;
      }

      state.results = {
        _mode: 'simulate',
        formula: res.formula || '',
        cookable: res.cookable || [],
        near_miss: res.near_miss || [],
      };
      renderRecipeList();

      const result = res.result || '(none)';
      const reason = res.reason || '';
      el('out').innerHTML = `
        <div class="ok">Result: ${renderItem(result)} <span class="muted">${reason ? '('+reason+')' : ''}</span></div>
        <div class="small muted" style="margin-top:6px;">${escHtml(t('cooking.results.sim_summary', 'Candidates listed on the left.'))}</div>
      `;

      // auto-select result if exists
      if (res.recipe) {
        state.activeRecipe = result;
        state.activeRecipeData = res.recipe;
        if (state.activeRecipeData && !state.activeRecipeData.name) state.activeRecipeData.name = result;
        renderRecipeList();
        renderRecipeDetail(state.activeRecipeData);
      }
    }

    function toggleMode() {
      if (state.mode === 'foodtypes') state.mode = 'tags';
      else if (state.mode === 'tags') state.mode = 'all';
      else state.mode = 'foodtypes';
      loadGroups().catch(e => setError(String(e)));
    }

    // wire
    const navCraft = document.getElementById('navCraft');
    if (navCraft) navCraft.href = APP_ROOT + '/';

    const navCooking = document.getElementById('navCooking');
    if (navCooking) navCooking.href = APP_ROOT + '/cooking';

    const navCatalog = document.getElementById('navCatalog');
    if (navCatalog) navCatalog.href = APP_ROOT + '/catalog';


    const labelSel = el('labelMode');
    if (labelSel) {
      try { labelSel.value = state.labelMode || 'en'; } catch (e) {}
      labelSel.onchange = () => setLabelMode(labelSel.value).catch(e => setError(String(e)));
    }

    el('btnToggle').onclick = toggleMode;
    el('btnSearch').onclick = () => doSearch().catch(e => setError(String(e)));
    el('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') doSearch().catch(err => setError(String(err))); });
    el('btnExplore').onclick = () => {
      setView('explore');
      doExplore().catch(e => setError(String(e)));
    };
    el('btnSim').onclick = () => {
      setView('simulate');
      doSimulate().catch(e => setError(String(e)));
    };
    el('btnShowAll').onclick = () => showAll().catch(e => setError(String(e)));
    el('btnViewCards').onclick = () => setListView('card');
    el('btnViewDense').onclick = () => setListView('dense');

    const modeEncy = el('modeEncy');
    if (modeEncy) modeEncy.onclick = () => { setView('encyclopedia'); showAll().catch(e => setError(String(e))); };
    const modeExplore = el('modeExplore');
    if (modeExplore) modeExplore.onclick = () => { setView('explore'); doExplore().catch(e => setError(String(e))); };
    const modeSim = el('modeSim');
    if (modeSim) modeSim.onclick = () => { setView('simulate'); doSimulate().catch(e => setError(String(e))); };

    const ingSearch = el('ingredientSearch');
    if (ingSearch) {
      ingSearch.addEventListener('input', () => {
        state.ingredientQuery = ingSearch.value.trim();
        renderIngredientGrid();
      });
    }
    const ingClear = el('ingredientClear');
    if (ingClear) {
      ingClear.onclick = () => {
        const slots = el('slots');
        if (!slots) return;
        slots.value = '';
        slots.dispatchEvent(new Event('input', { bubbles: true }));
      };
    }

    let exploreTimer = null;
    const slotsInput = el('slots');
    if (slotsInput) {
      slotsInput.addEventListener('input', () => {
        if (state.view === 'encyclopedia') {
          setView('explore');
        }
        if (exploreTimer) clearTimeout(exploreTimer);
        exploreTimer = setTimeout(() => {
          if (state.view === 'simulate') doSimulate().catch(e => setError(String(e)));
          else doExplore().catch(e => setError(String(e)));
        }, 400);
      });
    }

    function initFromUrl() {
      const params = new URLSearchParams(window.location.search || '');
      const recipe = params.get('recipe');
      const q = params.get('q');
      if (recipe) {
        selectRecipe(recipe).catch(e => setError(String(e)));
        return;
      }
      if (q) {
        el('q').value = q;
        doSearch().catch(e => setError(String(e)));
      }
    }

    // init
    (async () => {
      try {
        await loadMeta();
        await ensureI18nNames(state.labelMode);
        await loadAssets();
        await loadIngredients();
        await loadGroups();
        setView(state.view);
        setListView(state.listView);
        await showAll();
        initFromUrl();
      } catch (e) {
        setError(String(e));
      }
    })();
  </script>
</body>
</html>
"""


def render_cooking_html(app_root: str = "") -> str:
    """Render the Cooking UI page."""
    from html import escape as _esc

    root = str(app_root or "")
    css = _SHARED_CSS.replace("__WAGSTAFF_APP_ROOT__", root)
    return _COOKING_TEMPLATE.replace("__WAGSTAFF_APP_ROOT__", _esc(root)).replace("__SHARED_CSS__", css)
