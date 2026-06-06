/**
 * Immigration Services (Beyond Standard Work & Tourism) — service directory for DCIC.
 * Covers student passes, dependant passes, special passes, and the EAC Tourist Visa.
 */
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';

  container.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px 20px;margin-bottom:24px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:240px">
        <div style="font-weight:600;color:var(--text);margin-bottom:4px">Immigration Services</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.55">
          Extended immigration categories administered by the
          <strong>Directorate of Citizenship and Immigration Control (DCIC)</strong> via
          the e-Immigration portal. Covers permits for students, dependants, short-term
          visitors, and regional travel under the East African Community framework.
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--text3)">
        <span><span class="badge badge-accent" style="font-size:9px">DCIC</span> — Directorate of Citizenship &amp; Immigration Control</span>
        <span><span class="badge badge-info" style="font-size:9px">EAC</span> — East African Community Joint Tourist Visa</span>
      </div>
    </div>

    <div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);border-radius:var(--r);padding:12px 16px;margin-bottom:24px;font-size:12px;color:var(--warning)">
      <strong>⚠ Important:</strong> All immigration passes and permits must be applied for before the expiry of your current valid immigration status. Overstaying any immigration document attracts fines of USD 50 per day. Always apply at least 3–4 weeks before your current status expires.
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px;margin-bottom:32px">
      ${serviceCard({
        title: 'Student Pass',
        authorities: ['DCIC'],
        badge: 'Students',
        badgeClass: 'badge-info',
        description: 'Issued to foreign nationals formally admitted and enrolled in a Ugandan educational institution. Grants legal temporary residency for the duration of the study programme.',
        validity: 'Duration of study programme (renewable annually)',
        processingTime: '5–10 business days after submission',
        fee: 'USD 100 per year',
        documents: [
          'Completed e-Immigration application form',
          'Valid passport (at least 6 months validity)',
          'Formal admission letter from a recognised Ugandan institution',
          'Evidence of payment of tuition fees (registration slip or receipt)',
          'Proof of accommodation in Uganda',
          'Bank statement or sponsorship letter showing financial capacity',
          'Valid medical/health insurance cover',
          'Two recent passport-size photographs (white background)',
          'Yellow fever vaccination certificate',
        ],
        steps: [
          'Obtain formal admission letter from a NCHE-accredited Ugandan institution',
          'Create an account on the DCIC e-Immigration portal (immigration.go.ug)',
          'Complete the Student Pass application form and upload all documents',
          'Pay USD 100 via the portal payment gateway',
          'DCIC reviews and, if approved, issues an approval notice',
          'Collect the Student Pass at the nearest immigration office or port of entry',
        ],
        portals: [
          { label: 'DCIC e-Immigration', url: 'https://immigration.go.ug', primary: true },
        ],
      })}

      ${serviceCard({
        title: 'Dependant Pass',
        authorities: ['DCIC'],
        badge: 'Dependants',
        badgeClass: 'badge-muted',
        description: 'Allows spouses, minor children, and other legal dependants of work permit holders or Ugandan citizens to legally reside in Uganda. Does not confer work rights independently.',
        validity: 'Tied to the primary permit/residence (same expiry)',
        processingTime: '5–10 business days',
        fee: 'USD 100 per year',
        documents: [
          'Completed e-Immigration application form',
          'Valid passport of the dependant (at least 6 months validity)',
          'Copy of the primary holder\'s valid work permit or residence permit',
          'Marriage certificate (for spouse) or birth certificate (for children)',
          'If citizen sponsor: copy of Ugandan national ID or passport',
          'Proof of shared residence / accommodation',
          'Two recent passport-size photographs (white background)',
          'Yellow fever vaccination certificate',
        ],
        steps: [
          'Confirm the primary work permit holder has a valid, active permit',
          'Log in to DCIC e-Immigration portal',
          'Complete the Dependant Pass application form',
          'Upload relationship documents (marriage/birth certificate)',
          'Pay fee and submit',
          'Collect Dependant Pass upon approval — must correspond with primary permit renewal',
        ],
        portals: [
          { label: 'DCIC e-Immigration', url: 'https://immigration.go.ug', primary: true },
        ],
      })}

      ${serviceCard({
        title: 'Special Pass',
        authorities: ['DCIC'],
        badge: 'Short-Term',
        badgeClass: 'badge-warning',
        description: 'A short-term legal status document valid for up to 3 months. Issued to foreigners who need temporary residency while resolving long-term permit applications, seeking medical treatment, attending short business assignments, or awaiting departure arrangements.',
        validity: 'Up to 3 months (extendable once)',
        processingTime: '2–5 business days',
        fee: 'USD 50 per month (or fraction thereof)',
        documents: [
          'Completed e-Immigration Special Pass application form',
          'Valid passport (at least 3 months validity beyond requested pass duration)',
          'Cover letter explaining the purpose and duration of the stay',
          'Supporting evidence (hospital letter for medical treatment, invitation letter for business, etc.)',
          'Proof of current lawful immigration status or pending permit application number',
          'Two recent passport-size photographs',
          'Proof of sufficient funds for stay duration',
        ],
        steps: [
          'Ensure you have a valid lawful basis for applying (medical, pending permit, short assignment)',
          'Log in to DCIC e-Immigration portal',
          'Select "Special Pass" from the permit menu and complete the form',
          'Upload supporting documentation and cover letter',
          'Pay USD 50 per month of requested pass duration',
          'Collect the Special Pass at the nearest immigration office',
        ],
        portals: [
          { label: 'DCIC e-Immigration', url: 'https://immigration.go.ug', primary: true },
        ],
      })}

      ${serviceCard({
        title: 'East African Tourist Visa (EAC Joint Visa)',
        authorities: ['DCIC'],
        badge: 'EAC Regional',
        badgeClass: 'badge-success',
        description: 'A joint visa enabling cross-border travel between Uganda, Kenya, and Rwanda on a single document. Ideal for tourists and business travellers visiting all three countries in one trip. Available only to eligible nationalities (check EAC list before applying).',
        validity: '90 days (single entry per country allowed, multiple re-entries across EAC)',
        processingTime: '3–5 business days (online) · On arrival at major entry points',
        fee: 'USD 100 (covers all three EAC countries)',
        documents: [
          'Valid passport (at least 6 months validity; 2 blank visa pages)',
          'Completed joint EAC visa application form',
          'Recent passport-size photograph (white background)',
          'Confirmed onward/return travel itinerary',
          'Proof of accommodation bookings in Uganda, Kenya, and/or Rwanda',
          'Bank statement or proof of sufficient funds (min USD 50 per day)',
          'Yellow fever vaccination certificate (mandatory for Uganda entry)',
          'Travel insurance covering all three countries',
        ],
        steps: [
          'Verify your nationality is on the eligible EAC Joint Visa list (not all nationalities qualify)',
          'Apply online via the DCIC e-Visa portal or on arrival at Entebbe, JKIA Nairobi, or Kigali',
          'Complete the single application form covering all three countries',
          'Pay the USD 100 single-entry EAC visa fee',
          'Receive visa approval in passport or e-Visa confirmation',
          'Enter any of the three countries as the first point of entry; visa is then valid across all three',
        ],
        portals: [
          { label: 'DCIC e-Visa Portal', url: 'https://evisa.immigration.go.ug', primary: true },
          { label: 'DCIC e-Immigration', url: 'https://immigration.go.ug', primary: false },
        ],
      })}
    </div>

    <div class="card" style="font-size:12px;color:var(--text3)">
      <div class="card-header"><span class="card-title" style="font-size:12px">Important Notes</span></div>
      <ul style="padding-left:18px;line-height:1.9;margin:0">
        <li>All immigration applications must be made while the applicant's current lawful immigration status is still valid.</li>
        <li>Uganda is a Yellow Fever endemic country — a valid Yellow Fever vaccination certificate is required at all entry points.</li>
        <li>The EAC Joint Tourist Visa does not permit employment in any of the three countries; a separate work permit is required.</li>
        <li>Student Pass holders must maintain full-time enrolment and may not engage in paid employment without a concurrent work permit.</li>
        <li>Dependant Pass holders wishing to work must independently apply for a Class G or appropriate work permit through their employer.</li>
        <li>The Special Pass may be extended once (maximum 6 months total). Further extensions require a substantive permit application.</li>
        <li>Biometric data (fingerprints and photograph) is collected at all Uganda immigration entry points.</li>
      </ul>
    </div>`;
}

function serviceCard({ title, authorities, badge, badgeClass, description, validity, processingTime, fee, documents, steps, portals }) {
  return `
    <div style="border:1px solid var(--border);border-radius:var(--r);padding:20px;background:var(--bg2);display:flex;flex-direction:column;gap:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <h3 style="font-size:14px;font-weight:600;color:var(--text);margin:0">${esc(title)}</h3>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          ${authorities.map(a => `<span class="badge badge-accent" style="font-size:9px;padding:2px 7px">${esc(a)}</span>`).join('')}
          <span class="badge ${badgeClass}" style="font-size:9px;padding:2px 7px">${esc(badge)}</span>
        </div>
      </div>

      <p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0">${esc(description)}</p>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
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
      </div>

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
