/**
 * Legal, Security & Education — service directory for Uganda Police Force and CivicGate.
 * Covers Certificate of Good Conduct (Police Clearance) and academic document verification.
 */
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';

  container.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px 20px;margin-bottom:24px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:240px">
        <div style="font-weight:600;color:var(--text);margin-bottom:4px">Legal, Security &amp; Education</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.55">
          Police clearance certificates are processed by the
          <strong>Uganda Police Force (UPF) — Interpol Directorate</strong>.
          Academic document verification for Ugandan institutions is handled via the
          <strong>CivicGate</strong> portal.
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--text3)">
        <span><span class="badge badge-accent" style="font-size:9px">UPF</span> — Uganda Police Force (Interpol Directorate)</span>
        <span><span class="badge badge-info" style="font-size:9px">CIVICGATE</span> — Centralised e-Government Portal</span>
        <span><span class="badge badge-muted" style="font-size:9px">NCHE</span> — National Council for Higher Education</span>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px;margin-bottom:32px">
      ${goodConductCard()}
      ${academicVerificationCard()}
    </div>

    <!-- Fingerprint guide -->
    <div class="card mb-5">
      <div class="card-header">
        <span class="card-title">Fingerprint Capture — Overseas Applicants Guide</span>
        <span class="badge badge-warning" style="font-size:10px">Physical Step Required</span>
      </div>
      <div style="font-size:13px;color:var(--text2);line-height:1.6">
        <p style="margin:0 0 12px 0">
          If you are applying for a Certificate of Good Conduct from outside Uganda, fingerprint capture
          cannot be completed online. You have two options:
        </p>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px">
          <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:14px">
            <div style="font-weight:600;font-size:13px;margin-bottom:6px">Option A — Nearest Uganda High Commission</div>
            <div style="font-size:12px;color:var(--text2);line-height:1.7">
              Visit the Ugandan Embassy or High Commission in your country of residence.
              They can capture fingerprints on your behalf and forward the prints to the
              UPF Interpol Directorate in Kampala.
            </div>
          </div>
          <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:14px">
            <div style="font-weight:600;font-size:13px;margin-bottom:6px">Option B — Official Fingerprint Cards by Mail</div>
            <div style="font-size:12px;color:var(--text2);line-height:1.7">
              Request official fingerprint cards from the UPF Interpol Directorate by email.
              Have your fingerprints captured by a local police authority on those cards.
              Mail the completed cards directly to the Directorate in Kampala with your application.
            </div>
          </div>
        </div>
        <p style="margin:12px 0 0 0;font-size:12px;color:var(--text3)">
          UPF Interpol Directorate contact: <strong>interpoldirector@ugandapolice.go.ug</strong> ·
          Physical address: Interpol Directorate, Uganda Police HQ, Naguru, Kampala.
        </p>
      </div>
    </div>

    <!-- Reference table -->
    <div class="card">
      <div class="card-header"><span class="card-title">Common Use Cases &amp; Accepted Documents</span></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Purpose</th>
              <th>Certificate of Good Conduct</th>
              <th>Academic Verification</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            ${useCaseRow('Overseas employment application', true, false, 'Most foreign employers and immigration authorities require it')}
            ${useCaseRow('Ugandan immigration / permit renewal', true, false, 'Requested by DCIC for Class G work permit and some residence permits')}
            ${useCaseRow('Professional licensing abroad', true, true, 'Medical, legal, and engineering boards typically require both')}
            ${useCaseRow('Further academic study (international)', false, true, 'Universities require certified transcripts + degree verification')}
            ${useCaseRow('Admission to foreign bar / law society', true, true, 'Both conduct certificate and LLB degree verification required')}
            ${useCaseRow('Adoption proceedings', true, false, 'Required by the Ugandan courts and foreign authorities')}
            ${useCaseRow('Personal background record check', true, false, 'Issued for personal use — valid for 6 months')}
            ${useCaseRow('Employer recruitment due diligence', false, true, 'Employers may verify candidate academic credentials via CivicGate')}
          </tbody>
        </table>
      </div>
    </div>`;
}

function goodConductCard() {
  return `
    <div style="border:1px solid var(--border);border-radius:var(--r);padding:20px;background:var(--bg2);display:flex;flex-direction:column;gap:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <h3 style="font-size:15px;font-weight:600;color:var(--text);margin:0">Certificate of Good Conduct</h3>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <span class="badge badge-accent" style="font-size:9px;padding:2px 7px">UPF</span>
          <span class="badge badge-muted" style="font-size:9px;padding:2px 7px">Police Clearance</span>
        </div>
      </div>

      <p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0">
        An official police clearance certificate issued by the Uganda Police Force (Interpol Directorate)
        confirming the holder's criminal record status in Uganda. Required for employment abroad,
        immigration applications, professional licensing, and other legal purposes.
        <strong>Note:</strong> fingerprint capture requires an in-person visit or mailed fingerprint cards
        — it cannot be completed entirely online.
      </p>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Processing Time</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">7–21 business days (overseas: 30–45 days)</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Fee</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">UGX 50,000 (local) · USD 30 (overseas)</div>
        </div>
      </div>

      <div style="background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.2);border-radius:4px;padding:10px;font-size:12px;color:var(--warning)">
        ⚠ Physical fingerprinting is mandatory. Overseas applicants must visit the nearest Uganda Embassy or mail fingerprint cards.
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Required Documents</div>
        <ul style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          <li>Valid Ugandan national ID or passport</li>
          <li>Completed police clearance application form</li>
          <li>Recent passport-size photograph (white background)</li>
          <li>Official fingerprint capture form (completed at UPF HQ, Uganda Embassy, or submitted via mail)</li>
          <li>Proof of payment of prescribed fee (UGX 50,000 local / USD 30 overseas)</li>
          <li>Cover letter stating purpose of the certificate</li>
          <li>Previous passports (if you have had multiple — for identity verification)</li>
        </ul>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">How to Apply (In Uganda)</div>
        <ol style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          <li>Visit the UPF Interpol Directorate at Police HQ, Naguru, Kampala</li>
          <li>Collect and complete the application form</li>
          <li>Have fingerprints captured in person at the Directorate</li>
          <li>Pay UGX 50,000 via the UPF designated bank account and attach proof</li>
          <li>Submit the complete application package (form + photo + fingerprints + payment proof)</li>
          <li>Collect the certificate when notified or via the UPF online portal</li>
        </ol>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">How to Apply (Overseas)</div>
        <ol style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          <li>Email the UPF Interpol Directorate to request official fingerprint cards</li>
          <li>Visit your nearest Uganda High Commission or local police authority for fingerprinting on those cards</li>
          <li>Complete the application form and gather all supporting documents</li>
          <li>Pay USD 30 via bank transfer to the UPF designated account</li>
          <li>Mail completed fingerprint cards, application form, photograph, and payment proof to the Interpol Directorate</li>
          <li>Certificate is issued and returned by courier or collected at the Ugandan Embassy</li>
        </ol>
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:8px;border-top:1px solid var(--border)">
        <a href="https://police.go.ug" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">UPF Website ↗</a>
      </div>
    </div>`;
}

function academicVerificationCard() {
  return `
    <div style="border:1px solid var(--border);border-radius:var(--r);padding:20px;background:var(--bg2);display:flex;flex-direction:column;gap:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <h3 style="font-size:15px;font-weight:600;color:var(--text);margin:0">Academic Document Verification</h3>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          <span class="badge badge-accent" style="font-size:9px;padding:2px 7px">CivicGate</span>
          <span class="badge badge-info" style="font-size:9px;padding:2px 7px">NCHE</span>
        </div>
      </div>

      <p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0">
        Verify the authenticity of academic certificates, diplomas, degrees, and transcripts issued by
        Ugandan institutions for purposes of employment, further education abroad, or professional licensing.
        Verification is conducted through the CivicGate portal, with records sourced from NCHE
        (higher education) and the UNEB / UBTEB databases (pre-university and vocational).
      </p>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Processing Time</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">3–10 business days</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Fee</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">UGX 50,000–150,000 per document</div>
        </div>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Documents that Can Be Verified</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:var(--text2)">
          ${['University degrees and diplomas', 'Academic transcripts', 'UNEB O-Level certificates (UCE)', 'UNEB A-Level certificates (UACE)', 'UBTEB technical certificates', 'Vocational training certificates', 'Postgraduate certificates and diplomas', 'Medical and nursing qualification certificates'].map(d => `
            <div style="display:flex;align-items:center;gap:6px;padding:6px 8px;background:rgba(255,255,255,.025);border-radius:3px">
              <span style="color:var(--success);font-size:10px">✓</span>
              <span>${esc(d)}</span>
            </div>`).join('')}
        </div>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">Required Documents (Verification Request)</div>
        <ul style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          <li>Clear scanned copy of the certificate or transcript to be verified</li>
          <li>Full name as it appears on the certificate</li>
          <li>Year of graduation or award</li>
          <li>Name of the awarding institution</li>
          <li>Student/examination number (if known)</li>
          <li>Applicant's national ID or passport</li>
          <li>Purpose of verification (employment, further study, licensing)</li>
        </ul>
      </div>

      <div>
        <div style="font-size:10px;color:var(--text3);margin-bottom:6px;text-transform:uppercase;letter-spacing:.5px;font-weight:600">How to Request Verification</div>
        <ol style="font-size:12px;color:var(--text2);line-height:1.85;padding-left:16px;margin:0">
          <li>Create or log in to your CivicGate account</li>
          <li>Navigate to "Academic Document Verification" under Education Services</li>
          <li>Select the awarding institution type (University, UNEB, UBTEB, etc.)</li>
          <li>Upload the document and enter the required details</li>
          <li>Pay the verification fee via mobile money or bank</li>
          <li>Receive an official verification report or certificate of authenticity by email or download</li>
        </ol>
      </div>

      <div style="background:rgba(14,165,233,.06);border:1px solid rgba(14,165,233,.2);border-radius:4px;padding:10px;font-size:12px;color:var(--accent)">
        ℹ Employers and foreign universities can also initiate third-party verification directly through CivicGate without requiring the applicant's login.
      </div>

      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:8px;border-top:1px solid var(--border)">
        <a href="https://civicgate.go.ug" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm">CivicGate Portal ↗</a>
        <a href="https://www.nche.go.ug" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">NCHE Website ↗</a>
      </div>
    </div>`;
}

function useCaseRow(purpose, needsConduct, needsAcademic, note) {
  const tick = '<span class="badge badge-success" style="font-size:10px">Required</span>';
  const cross = '<span class="badge badge-muted" style="font-size:10px">Not Required</span>';
  return `<tr>
    <td style="font-weight:500">${esc(purpose)}</td>
    <td>${needsConduct ? tick : cross}</td>
    <td>${needsAcademic ? tick : cross}</td>
    <td class="text-3 text-xs">${esc(note)}</td>
  </tr>`;
}
