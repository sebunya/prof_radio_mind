/**
 * Civil Status & Life Events — service directory for NIRA, URSB, and CivicGate.
 * Purely informational; links out to official Ugandan government portals.
 */
import { serviceCard, notesCard } from '../civic-utils.js';

export async function init(container, actions) {
  actions.innerHTML = '';

  container.innerHTML = `
    <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);padding:16px 20px;margin-bottom:24px;display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start">
      <div style="flex:1;min-width:240px">
        <div style="font-weight:600;color:var(--text);margin-bottom:4px">Civil Status &amp; Life Events</div>
        <div style="font-size:13px;color:var(--text2);line-height:1.55">
          Register and obtain official documents for key life events through the
          <strong>National Identification &amp; Registration Authority (NIRA)</strong>,
          the <strong>Uganda Registration Services Bureau (URSB)</strong>,
          and the centralized <strong>CivicGate</strong> e-government portal.
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--text3)">
        <span><span class="badge badge-accent" style="font-size:9px">NIRA</span> — National Identification &amp; Registration Authority</span>
        <span><span class="badge badge-info" style="font-size:9px">URSB</span> — Uganda Registration Services Bureau</span>
        <span><span class="badge badge-muted" style="font-size:9px">CIVICGATE</span> — Centralized e-Government Portal</span>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px">
      ${serviceCard({
        title: 'Birth Certificate',
        authorities: ['NIRA', 'CivicGate'],
        description: 'Apply for a new birth certificate or certified replacement copy for any registered Ugandan birth. Required for school enrollment, national ID application, and passport issuance.',
        processingTime: '5–10 business days',
        fee: 'UGX 20,000 (new) · UGX 10,000 (certified copy)',
        documents: [
          'Completed birth registration form (LC I letter for rural areas)',
          'Hospital birth notification or midwife declaration',
          'Valid national IDs or passports of both parents',
          'Parents\' marriage certificate (where applicable)',
          'Affidavit for late registrations (>90 days after birth)',
        ],
        steps: [
          'Log in to CivicGate or visit the nearest NIRA registration centre',
          'Select "Birth Registration" and complete the application form',
          'Upload scanned supporting documents',
          'Pay the prescribed fee via mobile money or bank',
          'Collect certificate at the designated NIRA centre or via courier',
        ],
        portals: [
          { label: 'CivicGate Portal', url: 'https://civicgate.go.ug', primary: true },
          { label: 'NIRA Website', url: 'https://nira.go.ug', primary: false },
        ],
      })}

      ${serviceCard({
        title: 'Death Certificate',
        authorities: ['NIRA', 'CivicGate'],
        description: 'Register a death and obtain an official death certificate. Required for estate administration, property transfer, insurance claims, and pension disbursement.',
        processingTime: '3–7 business days',
        fee: 'UGX 10,000',
        documents: [
          'Medical certificate of cause of death (issued by doctor or hospital)',
          'National ID or passport of the deceased',
          'National ID of applicant (next of kin or authorised representative)',
          'Proof of relationship to the deceased',
          'Burial permit (if already obtained from local authority)',
        ],
        steps: [
          'Obtain the medical certificate of cause of death from the hospital or attending doctor',
          'Visit a NIRA sub-county office or apply via CivicGate',
          'Submit the application form with all supporting documents',
          'Pay the prescribed fee',
          'Collect the death certificate from the registration centre',
        ],
        portals: [
          { label: 'CivicGate Portal', url: 'https://civicgate.go.ug', primary: true },
          { label: 'NIRA Website', url: 'https://nira.go.ug', primary: false },
        ],
      })}

      ${serviceCard({
        title: 'Marriage Registration',
        authorities: ['URSB', 'CivicGate'],
        description: 'Register a legally conducted marriage and obtain an official marriage certificate recognised for immigration, spousal rights, life insurance, and all official purposes.',
        processingTime: '5–14 business days',
        fee: 'UGX 50,000 (Civil) · varies by denomination (Religious/Customary)',
        documents: [
          'Completed marriage registration return form',
          'Valid national IDs or passports of both spouses',
          'Two recent passport-size photographs of each spouse',
          'Signed declaration of single status (from each spouse)',
          'Marriage officer\'s certificate (for religious/denomination weddings)',
          'Witnesses\' national IDs (minimum 2 witnesses)',
        ],
        steps: [
          'Choose marriage type: Civil (URSB sub-office) or Religious (officiated by registrar)',
          'Submit notice of intended marriage at least 21 days before the ceremony',
          'Attend the ceremony with the officiating marriage officer',
          'File the marriage return with URSB within 30 days of the ceremony',
          'Collect the signed and sealed marriage certificate',
        ],
        portals: [
          { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          { label: 'CivicGate Portal', url: 'https://civicgate.go.ug', primary: false },
        ],
      })}

      ${serviceCard({
        title: 'Change of Name',
        authorities: ['NIRA', 'URSB'],
        description: 'Legally change your name or a child\'s name via deed poll and subsequent registration. Required before passport reissuance, academic records amendment, and updates to official correspondence.',
        processingTime: '14–21 business days',
        fee: 'UGX 100,000–150,000 (deed poll + gazette publication + registration)',
        documents: [
          'Completed change of name application form',
          'Original national ID and/or birth certificate',
          'Statutory declaration (sworn affidavit confirming the name change)',
          'Deed poll document executed before a Commissioner for Oaths',
          'Uganda Gazette notice of name change (published copy)',
          'Parental consent letter + both parents\' IDs (for minors)',
        ],
        steps: [
          'Engage a Commissioner for Oaths or advocate to draft and execute a deed poll',
          'Swear a statutory declaration before a magistrate or Commissioner for Oaths',
          'Advertise the name change in the Uganda Gazette (Uganda Printing & Publishing Corp.)',
          'Submit the deed poll, gazette copy, and declaration to NIRA/URSB for registration',
          'Update national ID, birth certificate, academic records, and bank accounts accordingly',
        ],
        portals: [
          { label: 'URSB e-Services', url: 'https://ursb.go.ug', primary: true },
          { label: 'NIRA Website', url: 'https://nira.go.ug', primary: false },
        ],
      })}
    </div>

    ${notesCard([
      'All fees quoted are indicative and subject to change. Confirm current fees on the official portal before payment.',
      'NIRA maintains biometric registration centres across all districts. Walk-in visits remain available for document collection.',
      'CivicGate provides a single sign-on for multiple government services. Create one account to access NIRA, URSB, and other agencies.',
      'Late birth registrations (older than 12 months) require an investigation and may be referred to the Registrar General.',
    ])}`;
}

