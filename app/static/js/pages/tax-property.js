/**
 * Taxation & Property — service directory for URA and UgNLIS.
 * Covers TIN registration, tax filing, tax clearance, and land title services.
 */
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';

  container.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px 20px;margin-bottom:24px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:240px">
        <div style="font-weight:600;color:var(--text);margin-bottom:4px">Taxation &amp; Property</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.55">
          Tax services are administered by the <strong>Uganda Revenue Authority (URA)</strong> via its
          e-Tax portal. Land and property services are provided by the Ministry of Lands through the
          <strong>Uganda National Land Information System (UgNLIS)</strong>.
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--text3)">
        <span><span class="badge badge-accent" style="font-size:9px">URA</span> — Uganda Revenue Authority</span>
        <span><span class="badge badge-info" style="font-size:9px">UgNLIS</span> — Uganda National Land Information System</span>
        <span><span class="badge badge-muted" style="font-size:9px">MLHUD</span> — Ministry of Lands, Housing &amp; Urban Development</span>
      </div>
    </div>

    <div class="mb-5">
      <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">Tax Services — Uganda Revenue Authority</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
        ${serviceCard({
          title: 'Taxpayer Identification Number (TIN)',
          authorities: ['URA'],
          description: 'Register for a TIN — the unique number required for employment, business operation, bank account opening, and government procurement. Mandatory for all individuals earning taxable income and all business entities.',
          processingTime: '1–3 business days (online) · Same day (in person)',
          fee: 'Free',
          documents: [
            'Valid national ID (citizens) or passport (non-citizens)',
            'Uganda work permit or student pass (for non-citizens)',
            'Certificate of Incorporation (for companies and NGOs)',
            'Physical business address and contact details',
            'Bank account details (optional, for faster tax refund processing)',
          ],
          steps: [
            'Visit the URA e-Tax portal (etax.ura.go.ug) and click "Register for TIN"',
            'Select applicant type: Individual, Non-Individual (Company), or NGO',
            'Complete the online form with personal or entity details',
            'Upload supporting documents',
            'Submit and receive TIN certificate by email within 1–3 working days',
          ],
          portals: [
            { label: 'URA e-Tax Portal', url: 'https://etax.ura.go.ug', primary: true },
            { label: 'URA Website', url: 'https://www.ura.go.ug', primary: false },
          ],
        })}

        ${serviceCard({
          title: 'Tax Filing (Monthly & Annual Returns)',
          authorities: ['URA'],
          description: 'File monthly and annual tax returns for all tax types: Value Added Tax (VAT), Pay As You Earn (PAYE), Withholding Tax, and Income Tax. Late filing attracts penalties of UGX 200,000+ per return.',
          processingTime: 'Instant (online submission)',
          fee: 'No filing fee · Late penalty: UGX 200,000/month (individuals) · UGX 2,000,000/month (companies)',
          documents: [
            'Valid TIN',
            'Monthly payroll records (for PAYE)',
            'Sales and purchase records (for VAT — monthly turnover threshold: UGX 150M/year)',
            'Audited financial statements (for annual income tax)',
            'Withholding tax certificates from clients/suppliers (where applicable)',
          ],
          steps: [
            'Log in to URA e-Tax portal using your TIN and password',
            'Select the tax type and filing period',
            'Enter income, expense, and tax computation data',
            'System auto-calculates tax liability',
            'Pay online via URA payment gateway or generate a Payment Registration Number (PRN) for bank payment',
          ],
          portals: [
            { label: 'URA e-Tax Portal', url: 'https://etax.ura.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Tax Clearance Certificate',
          authorities: ['URA'],
          description: 'A Tax Clearance Certificate confirms that an individual or entity has no outstanding tax obligations. Required for government tenders, immigration applications, and company share transfers.',
          processingTime: '3–5 business days',
          fee: 'Free',
          documents: [
            'Valid TIN',
            'All tax returns filed and up to date (PAYE, VAT, Income Tax)',
            'Payment of all outstanding tax assessments',
            'Proof of no outstanding audit objections',
          ],
          steps: [
            'Ensure all outstanding tax returns are filed and taxes paid',
            'Log in to URA e-Tax portal',
            'Navigate to "Clearance Certificate" under services',
            'Submit the clearance certificate request',
            'Download the certificate (valid for 6 months) once approved',
          ],
          portals: [
            { label: 'URA e-Tax Portal', url: 'https://etax.ura.go.ug', primary: true },
          ],
        })}
      </div>
    </div>

    <div class="mb-5">
      <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">Land &amp; Property Services — UgNLIS</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
        ${serviceCard({
          title: 'Land Title Search',
          authorities: ['UgNLIS', 'MLHUD'],
          description: 'Conduct an official search on any Ugandan land title to verify ownership, check for encumbrances (mortgages, caveats, court orders), and confirm land boundaries before purchase or investment.',
          processingTime: '1–3 business days',
          fee: 'UGX 50,000 per title (official search)',
          documents: [
            'Land title number (Volume, Folio, and Block reference)',
            'Or Plot number and district / municipality',
            'Applicant\'s national ID or passport',
            'TIN (for official search with legal implications)',
          ],
          steps: [
            'Log in to UgNLIS portal or visit a Zonal Land Office',
            'Enter the land title reference number or plot coordinates',
            'Submit the search request and pay the search fee',
            'Receive an official search report confirming ownership and encumbrances',
            'Use the report for due diligence before completing any property transaction',
          ],
          portals: [
            { label: 'UgNLIS Portal', url: 'https://ugnlis.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Land Title Transfer',
          authorities: ['UgNLIS', 'MLHUD'],
          description: 'Transfer ownership of registered land from seller to buyer using the UgNLIS system. Eliminates the need to physically visit the land registry for most transfer transactions.',
          processingTime: '14–30 business days',
          fee: '1% of purchase price (stamp duty) + UGX 50,000–100,000 (registration fees)',
          documents: [
            'Original land title (Certificate of Title)',
            'Sale agreement or transfer instrument (signed by both parties)',
            'National IDs or passports of buyer and seller',
            'Consent of the registered proprietor (if jointly owned)',
            'Proof of payment of stamp duty',
            'Land Form 1 (Transfer of Land) — completed and witnessed',
            'LC I / Local Council consent letter (for Mailo land)',
          ],
          steps: [
            'Conduct a land title search to confirm ownership and absence of caveats',
            'Execute a sale agreement before a Commissioner for Oaths',
            'Pay stamp duty at URA and obtain stamp duty receipt',
            'Lodge transfer documents at the relevant Zonal Land Office or via UgNLIS',
            'Pay registration fees and obtain new Certificate of Title in the buyer\'s name',
          ],
          portals: [
            { label: 'UgNLIS Portal', url: 'https://ugnlis.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Caveat & Encumbrance Search',
          authorities: ['UgNLIS', 'MLHUD'],
          description: 'Search for any caveats, mortgages, legal notices, or registered charges against a land title — critical due diligence before lending, purchasing, or development approvals.',
          processingTime: '1 business day',
          fee: 'UGX 25,000 (search fee)',
          documents: [
            'Land title reference (Volume, Folio, Block)',
            'Applicant\'s national ID or TIN',
          ],
          steps: [
            'Access UgNLIS portal and select "Encumbrance Search"',
            'Enter the title reference details',
            'Pay search fee online',
            'Download the official encumbrance report',
            'Review for any caveats, mortgages, or court orders before transacting',
          ],
          portals: [
            { label: 'UgNLIS Portal', url: 'https://ugnlis.go.ug', primary: true },
          ],
        })}
      </div>
    </div>

    <div class="card" style="font-size:12px;color:var(--text3)">
      <div class="card-header"><span class="card-title" style="font-size:12px">Important Notes</span></div>
      <ul style="padding-left:18px;line-height:1.9;margin:0">
        <li>A TIN is legally required for any formal employment contract, bank account (UGX accounts above threshold), and company director appointments.</li>
        <li>VAT registration is mandatory once annual turnover exceeds UGX 150 million. Voluntary registration is allowed below this threshold.</li>
        <li>URA e-Tax PRNs for bank payment expire in 48 hours — generate them close to payment date.</li>
        <li>Always conduct a fresh land title search immediately before and immediately after completing a property transaction, as caveats can be lodged at any time.</li>
        <li>Stamp duty is computed on the higher of the purchase price or the market value assessed by the Chief Government Valuer.</li>
        <li>LC I consent letters are specifically required for Mailo land transfers in Buganda region — not applicable to freehold or leasehold titles.</li>
      </ul>
    </div>`;
}

function serviceCard({ title, authorities, description, processingTime, fee, documents, steps, portals }) {
  return `
    <div style="border:1px solid var(--border);border-radius:var(--r);padding:20px;background:var(--bg2);display:flex;flex-direction:column;gap:14px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
        <h3 style="font-size:14px;font-weight:600;color:var(--text);margin:0">${esc(title)}</h3>
        <div style="display:flex;gap:5px;flex-wrap:wrap">
          ${authorities.map(a => `<span class="badge badge-accent" style="font-size:9px;padding:2px 7px">${esc(a)}</span>`).join('')}
        </div>
      </div>

      <p style="font-size:13px;color:var(--text2);line-height:1.55;margin:0">${esc(description)}</p>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Processing Time</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">${esc(processingTime)}</div>
        </div>
        <div style="background:rgba(255,255,255,.025);border:1px solid var(--border);border-radius:4px;padding:10px">
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Fee</div>
          <div style="font-size:12px;color:var(--text);font-weight:500">${esc(fee)}</div>
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
