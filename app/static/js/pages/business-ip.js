/**
 * Business & Intellectual Property — service directory for URSB.
 * Covers business registration, IP filings, and SIMPO (movable property registry).
 */
import { esc } from '../ui.js';

export async function init(container, actions) {
  actions.innerHTML = '';

  container.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px 20px;margin-bottom:24px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:240px">
        <div style="font-weight:600;color:var(--text);margin-bottom:4px">Business &amp; Intellectual Property</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.55">
          All corporate, commercial, and creative legalities in Uganda are handled through the
          <strong>Uganda Registration Services Bureau (URSB)</strong> e-Services portal.
          Services include business name search, company registration, annual returns,
          IP filings, and the movable property security interest registry (SIMPO).
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--text3)">
        <span><span class="badge badge-accent" style="font-size:9px">URSB</span> — Uganda Registration Services Bureau</span>
        <span><span class="badge badge-info" style="font-size:9px">SIMPO</span> — Security Interest in Movable Property Registry</span>
      </div>
    </div>

    <div class="mb-5">
      <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">Business Registration</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
        ${serviceCard({
          title: 'Business Name Search & Reservation',
          authorities: ['URSB'],
          description: 'Search the URSB register to check availability of a proposed business or company name before filing a registration application. Approved names can be reserved for up to 30 days.',
          processingTime: 'Instant (search) · 1–3 days (reservation)',
          fee: 'UGX 20,000 (name reservation)',
          documents: [
            'Proposed business/company name (3 alternatives recommended)',
            'Nature of business / ISIC classification',
            'Applicant\'s national ID or passport',
          ],
          steps: [
            'Visit the URSB e-Services portal and create an account',
            'Navigate to "Name Search" and enter proposed names',
            'Review availability results instantly',
            'Pay reservation fee to hold the name for 30 days',
            'Proceed to full registration within the reservation window',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Business Name Registration',
          authorities: ['URSB'],
          description: 'Register a sole proprietorship or partnership trading under a business name (distinct from a limited company). Required to legally conduct business in Uganda.',
          processingTime: '3–5 business days',
          fee: 'UGX 25,000–50,000 (based on business type)',
          documents: [
            'Reserved or available business name',
            'National ID or passport of proprietor/partners',
            'Physical address and postal address of the business',
            'Nature of business description',
            'Partnership deed (for partnerships)',
          ],
          steps: [
            'Log in to URSB e-Services and navigate to "Business Registration"',
            'Complete the business name registration form (Form A)',
            'Upload required identification documents',
            'Pay registration fee via mobile money or bank',
            'Receive Certificate of Registration by email/download',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Company Registration (Local)',
          authorities: ['URSB'],
          description: 'Incorporate a private limited company, public limited company, or company limited by guarantee under the Companies Act, 2012. Provides limited liability protection to shareholders.',
          processingTime: '5–7 business days',
          fee: 'UGX 95,000 (private limited) · UGX 450,000+ (public limited)',
          documents: [
            'Memorandum and Articles of Association',
            'Statement of Nominal Capital (Form 1)',
            'Particulars of directors and secretary (Form 7)',
            'Statutory Declaration of Compliance (Form 4)',
            'National IDs or passports of all directors and shareholders',
            'Proof of registered office address',
          ],
          steps: [
            'Complete name reservation on URSB portal',
            'Draft Memorandum and Articles of Association',
            'Complete and submit Form 1, Form 7, and Form 4 on URSB e-Services',
            'Pay registration fees and stamp duty',
            'URSB reviews and issues Certificate of Incorporation',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Foreign Company Registration',
          authorities: ['URSB'],
          description: 'Register a foreign company branch or subsidiary in Uganda. Required before a foreign company can legally conduct business or enter contracts in Uganda.',
          processingTime: '7–14 business days',
          fee: 'USD 1,000 or equivalent in UGX',
          documents: [
            'Certified copy of the foreign company\'s Certificate of Incorporation',
            'Certified Memorandum and Articles of Association',
            'List of directors and their particulars',
            'Address of the company\'s registered office abroad',
            'Name and address of authorised local representative',
            'Certified copy of annual returns from home country (latest)',
          ],
          steps: [
            'Obtain certified and apostilled company documents from country of origin',
            'Complete Form 219 (foreign company particulars) on URSB portal',
            'Submit original certified documents and local representative consent',
            'Pay registration fees',
            'Receive Certificate of Registration of a Foreign Company',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Annual Returns Filing',
          authorities: ['URSB'],
          description: 'File annual statutory returns for your company or business name to keep the registration current. Non-filing attracts penalties and may result in deregistration.',
          processingTime: 'Same day (online submission)',
          fee: 'UGX 20,000–200,000 (based on entity type and turnover)',
          documents: [
            'Current list of directors, shareholders, and their shareholdings',
            'Company registered office address confirmation',
            'Annual financial summary (for some company types)',
            'Certificate of Incorporation reference number',
          ],
          steps: [
            'Log in to URSB e-Services with company credentials',
            'Navigate to "Annual Returns" and select the filing year',
            'Confirm or update director and shareholder information',
            'Pay the annual return fee',
            'Download the filed annual return acknowledgement',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}
      </div>
    </div>

    <div class="mb-5">
      <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">Intellectual Property</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
        ${serviceCard({
          title: 'Trademark Registration',
          authorities: ['URSB'],
          description: 'Protect your brand — logos, names, slogans, and product identifiers — through official trademark registration, valid for 10 years and renewable indefinitely.',
          processingTime: '6–12 months (including mandatory 60-day gazette publication)',
          fee: 'UGX 200,000 per class (application) + gazette fees',
          documents: [
            'Completed trademark application form (TM1)',
            'Clear representation of the mark (logo/wordmark at 400×400 px minimum)',
            'List of goods or services in relevant Nice Classification classes',
            'Applicant\'s national ID or certificate of incorporation',
            'Power of attorney (if filed through an IP agent)',
          ],
          steps: [
            'Conduct a trademark clearance search on the URSB database',
            'File application (Form TM1) on URSB e-Services',
            'URSB examines the application for distinctiveness and conflicts',
            'Accepted marks are published in the Uganda Gazette for 60 days',
            'If no opposition is filed, the certificate of registration is issued',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Patent Registration',
          authorities: ['URSB'],
          description: 'Protect inventions — new, industrially applicable products or processes — with a patent grant giving exclusive exploitation rights for 20 years.',
          processingTime: '18–36 months (substantive examination)',
          fee: 'UGX 300,000 (filing) + annual maintenance fees from year 3',
          documents: [
            'Patent application form (PA1)',
            'Full description of the invention (enabling disclosure)',
            'Claims defining the scope of protection',
            'Abstract (not more than 150 words)',
            'Drawings or diagrams (if applicable)',
            'Priority document (if claiming Paris Convention priority)',
          ],
          steps: [
            'Prepare technical description, claims, abstract, and drawings',
            'File application via URSB e-Services or in person',
            'Formal examination: URSB checks for completeness',
            'Publication in Uganda Gazette (18 months from filing date)',
            'Substantive examination and grant of patent certificate',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Copyright Registration',
          authorities: ['URSB'],
          description: 'Voluntarily register original literary, musical, artistic, or audio-visual works. While copyright arises automatically at creation, registration provides evidentiary proof of ownership.',
          processingTime: '5–10 business days',
          fee: 'UGX 50,000–150,000 (based on work type)',
          documents: [
            'Completed copyright registration form (CR1)',
            'Two copies of the work (electronic or printed)',
            'Statement of date of first publication/creation',
            'Applicant\'s national ID or passport',
            'Assignment or licence document (if registering a transferred right)',
          ],
          steps: [
            'Prepare two copies of the original work for deposit',
            'Complete Form CR1 on the URSB e-Services portal',
            'Upload digital copy of the work',
            'Pay registration fee',
            'Receive Certificate of Copyright Registration',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}

        ${serviceCard({
          title: 'Industrial Design Registration',
          authorities: ['URSB'],
          description: 'Protect the ornamental or aesthetic aspects of a product — shape, configuration, pattern, or colour — giving 5-year exclusive rights (renewable up to 15 years).',
          processingTime: '3–6 months',
          fee: 'UGX 150,000 (filing)',
          documents: [
            'Completed industrial design application form',
            'Photographs or drawings of the design from multiple angles',
            'Description of the design features',
            'Applicant\'s national ID or certificate of incorporation',
          ],
          steps: [
            'Prepare high-quality photographs or technical drawings of the design',
            'File application via URSB e-Services',
            'Formal examination by URSB',
            'Publication in the Uganda Gazette',
            'Certificate of Industrial Design Registration issued',
          ],
          portals: [
            { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          ],
        })}
      </div>
    </div>

    <div class="mb-5">
      <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:14px">Movable Property Registry</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
        ${serviceCard({
          title: 'SIMPO Registration',
          authorities: ['URSB'],
          description: 'Register or search security interests in movable property (vehicles, machinery, crops, livestock, receivables) used as collateral for loans. Required for lenders under the Chattel Securities Act.',
          processingTime: 'Same day (online registration)',
          fee: 'UGX 50,000 (registration) · UGX 10,000 (search)',
          documents: [
            'Security agreement or chattel mortgage document',
            'Description of the collateral (make, model, serial number for vehicles)',
            'National ID or TIN of the grantor (borrower) and secured party (lender)',
            'Loan or credit agreement details',
          ],
          steps: [
            'Secured party (lender) logs in to URSB SIMPO portal',
            'Enter collateral description and debtor/creditor details',
            'Pay registration fee via mobile money or bank transfer',
            'Receive SIMPO registration number and confirmation',
            'Search existing interests before accepting collateral using the search tool',
          ],
          portals: [
            { label: 'URSB SIMPO Registry', url: 'https://ursb.go.ug', primary: true },
          ],
        })}
      </div>
    </div>

    <div class="card" style="font-size:12px;color:var(--text3)">
      <div class="card-header"><span class="card-title" style="font-size:12px">Important Notes</span></div>
      <ul style="padding-left:18px;line-height:1.9;margin:0">
        <li>All URSB services require a registered e-Services account. Create one free account for all corporate and IP services.</li>
        <li>Trademark and patent applicants are strongly advised to engage a registered IP agent or advocate for complex applications.</li>
        <li>SIMPO searches are essential before accepting movable property as collateral — registered interests have priority over unregistered creditors.</li>
        <li>Annual return deadlines: companies must file within 42 days of the anniversary of incorporation. Late fees apply.</li>
        <li>Nice Classification (trademark classes): Uganda recognises all 45 international classes. One fee applies per class.</li>
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
          <div style="font-size:10px;color:var(--text3);margin-bottom:3px;text-transform:uppercase;letter-spacing:.4px">Government Fee</div>
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
