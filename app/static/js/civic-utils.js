/**
 * Shared UI helpers for Ugandan civic service pages.
 * All civic pages import serviceCard, sectionHeader, and notesCard from here.
 */
import { esc } from './ui.js';

/**
 * Renders a service card.
 * When `validity` is provided a 3-column meta grid is rendered (Validity / Processing / Fee);
 * otherwise a 2-column grid is rendered (Processing Time / Fee).
 * When `badge` is provided an extra badge appears in the card header.
 */
export function serviceCard({
  title,
  authorities = [],
  description,
  processingTime,
  fee,
  validity = null,
  badge = null,
  badgeClass = '',
  documents = [],
  steps = [],
  portals = [],
}) {
  const metaGrid = validity
    ? `<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Validity</div>
          <div style="font-size:11px;color:var(--text);font-weight:500">${esc(validity)}</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Processing</div>
          <div style="font-size:11px;color:var(--text);font-weight:500">${esc(processingTime)}</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Fee</div>
          <div style="font-size:11px;color:var(--text);font-weight:500">${esc(fee)}</div>
        </div>
      </div>`
    : `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Processing Time</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">${esc(processingTime)}</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Fee</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">${esc(fee)}</div>
        </div>
      </div>`;

  return `
    <div style="border:1px solid var(--border);border-radius:var(--r);padding:20px;background:var(--bg2);display:flex;flex-direction:column;gap:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <h3 style="font-size:14px;font-weight:600;color:var(--text);margin:0">${esc(title)}</h3>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          ${authorities.map(a => `<span class="badge badge-accent" style="font-size:9px;padding:2px 7px">${esc(a)}</span>`).join('')}
          ${badge ? `<span class="badge ${badgeClass}" style="font-size:9px;padding:2px 7px">${esc(badge)}</span>` : ''}
        </div>
      </div>

      <p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0">${esc(description)}</p>

      ${metaGrid}

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Required Documents</div>
        <ul style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          ${documents.map(d => `<li>${esc(d)}</li>`).join('')}
        </ul>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">How to Apply</div>
        <ol style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          ${steps.map(s => `<li>${esc(s)}</li>`).join('')}
        </ol>
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:8px;border-top:1px solid var(--border)">
        ${portals.map(p => `<a href="${p.url}" target="_blank" rel="noopener noreferrer" class="btn ${p.primary ? 'btn-primary' : 'btn-ghost'} btn-sm">${esc(p.label)} ↗</a>`).join('')}
      </div>
    </div>`;
}

export function sectionHeader(title) {
  return `<div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">${esc(title)}</div>`;
}

export function notesCard(notes = []) {
  return `
    <div class="card" style="font-size:12px;color:var(--text3)">
      <div class="card-header"><span class="card-title" style="font-size:12px">Important Notes</span></div>
      <ul style="padding-left:18px;line-height:1.9;margin:0">
        ${notes.map(n => `<li>${n}</li>`).join('')}
      </ul>
    </div>`;
}
