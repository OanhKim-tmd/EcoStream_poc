/**
 * Claude Dynamic Workflow: EcoStream AI Multi-Agent Carbon Accounting & Regulatory Mitigation Pipeline
 *
 * MOTIVATIONS & ARCHITECTURAL CONTEXT:
 * ====================================
 * 1. Heterogeneous Enterprise Ingestion:
 *    Enterprise carbon activity data (invoices, utility ledgers, waybills, fuel delivery slips) is inherently
 *    unstructured and multi-format (Excel workbooks with multiple tabs, merged cells, custom notes, PDFs, DOCX).
 *    Traditional rigid static parsers fail on real-world edge cases (e.g., "50 bình LPG 12kg", missing monthly EVN bills).
 *
 * 2. Domain-Driven Parallel Subagent Extraction (Blackboard Pattern):
 *    Specialized subagents extract domain-specific activities in parallel, isolate edge cases, and apply
 *    conservative IPCC/TCVN standard defaults with confidence deductions while logging anomalies for human review.
 *
 * 3. 100% Deterministic Carbon & Mitigation Math:
 *    LLMs are restricted to schema understanding, unit extraction, and assumption logging. All greenhouse gas (GHG)
 *    multiplications (E = Q * EF), Gaussian 95% CI uncertainty propagation (sigma = sqrt(sum(sigma_i^2))), and
 *    regulatory mitigation math (GPT = PT_CS - PT, Quota balance) are executed deterministically in Python.
 *
 * 4. Regulatory Compliance & Dual-Tier Disclosures:
 *    Strictly aligns with Vietnamese environmental law:
 *    - Thông tư 17/2022/TT-BTNMT (Corporate GHG Inventory across Scope 1, 2, 3 & 5-dimension reliability).
 *    - Nghị định 06/2022/NĐ-CP & NĐ 119/2025/NĐ-CP (Mẫu số 02 Phụ lục III - Facility GHG Mitigation & Quota Tracking).
 */

export const meta = {
  name: 'wf-ecostream',
  description: 'Enterprise multi-agent GHG inventory, Decree 06/2022 Mẫu 02 mitigation math, and dual-tier audit trail synthesis',
  phases: [
    {
      title: 'Ingestion & Schema Discovery',
      detail: 'Convert multi-format inputs with MarkItDown, catalog workbook sheets, and dynamically assign domain routing tasks',
    },
    {
      title: 'Domain Subagents Extraction',
      detail: 'Parallel extraction of Scope 1 fuel, Scope 2 EVN grid power, Scope 3 supply chain, and Mẫu 02 mitigation projects',
    },
    {
      title: 'Deterministic Math & Regulatory Synthesis',
      detail: 'Execute analytical 95% CI error propagation, evaluate 5-dimension reliability penalties, and generate Vietnamese audit deliverables',
    },
  ],
};

const inputFile = (typeof args !== 'undefined' && args?.input) ? args.input : 'data/samples/input.xlsx';

// ---------------------------------------------------------------------------
// Phase 1: Ingestion & Dynamic Schema Discovery
// ---------------------------------------------------------------------------
phase('Ingestion & Schema Discovery');
log(`Initiating MarkItDown ingestion and SHA-256 fingerprint caching for: ${inputFile}`);

const discoveryResult = await agent(
  `You are the Schema Discovery Agent for EcoStream.
Input target: "${inputFile}".

Tasks:
1. Ingest input documents using MarkItDown markdown converter from the ingestion cache.
2. Inspect all sheets and document sections (e.g., Nhiên liệu, Điện lưới EVN, Vận chuyển Logistics, Dự án Giảm nhẹ).
3. Catalog table structures, detect non-standard column headers, merged headers, and unit conventions.
4. Route each sheet to its corresponding domain subagent and write the execution plan to 'index.json' in the run workspace.`,
  {
    label: 'discovery:schema-catalog',
    phase: 'Ingestion & Schema Discovery',
    subagent_type: 'ag-discovery',
  }
);

log('Schema discovery complete. Cataloged domain sheets and initialized routing index.');

// ---------------------------------------------------------------------------
// Phase 2: Domain Subagents Extraction (Parallel Fan-Out)
// ---------------------------------------------------------------------------
phase('Domain Subagents Extraction');
log('Deploying 4 domain subagents in parallel to extract Scope 1, Scope 2, Scope 3, and Mitigation data.');

const SUBAGENT_CONFIGS = [
  {
    key: 'scope1',
    label: 'extract:scope1-fuel',
    subagent_type: 'ag-scope1-fuel',
    prompt: `You are the Scope 1 Fuel Analyst Agent (ag-scope1-fuel).
Process stationary and mobile combustion records from markdown inputs.
Key responsibilities:
- Parse fuel quantities (Diesel, Fuel Oil, Coal, LPG, Natural Gas).
- Handle non-standard packaging units (e.g., convert '50 bình LPG 12kg' -> 600 kg LPG).
- Impute missing densities (e.g., 0.84 kg/L for DO) when volume is provided without mass.
- If assumptions are made, record a QueryLog entry for human verifiers and an AssumptionLog entry with a 5% confidence penalty.
- Save structured extractions to 'intermediate/scope1_extracted.json'.`,
  },
  {
    key: 'scope2',
    label: 'extract:scope2-power',
    subagent_type: 'ag-scope2-power',
    prompt: `You are the Scope 2 Grid Power Analyst Agent (ag-scope2-power).
Process EVN utility invoices and electricity ledgers from markdown inputs.
Key responsibilities:
- Extract active energy (kWh), peak/normal/off-peak breakdowns, customer codes, and meter IDs.
- Detect temporal gaps (e.g., missing July invoice in a 12-month billing series).
- Apply conservative seasonal linear interpolation: kWh_t = (kWh_{t-1} + kWh_{t+1}) / 2 to prevent downstream blocking.
- Record missing bill queries in QueryLog and the interpolation rule in AssumptionLog with a 5% confidence penalty and +15% uncertainty markup.
- Save structured extractions to 'intermediate/scope2_extracted.json'.`,
  },
  {
    key: 'scope3',
    label: 'extract:scope3-supply',
    subagent_type: 'ag-scope3-supply',
    prompt: `You are the Scope 3 Supply Chain Analyst Agent (ag-scope3-supply).
Process freight waybills, transport logs, and supplier procurement ledgers.
Key responsibilities:
- Compute physical activity metrics: weight (tonnes) * distance (km) = tonne-km for freight.
- If physical transport metrics are missing, fallback to spend-based EEIO/EXIOBASE proxy emission factors.
- Record spend-based fallback assumptions in AssumptionLog with a 15% confidence penalty and +40% uncertainty markup.
- Save structured extractions to 'intermediate/scope3_extracted.json'.`,
  },
  {
    key: 'mitigation',
    label: 'extract:mitigation-quota',
    subagent_type: 'ag-mitigation-quota',
    prompt: `You are the Mitigation & Quota Compliance Agent (ag-mitigation-quota).
Process facility GHG mitigation projects, energy efficiency audits, solar rooftop logs, and MONRE quota allocations.
Key responsibilities:
- Extract baseline emissions (PT_CS) and actual post-project emissions (PT) for each mitigation measure.
- Extract allocated emission quota (Quota_alloc) under Decree 06/2022/NĐ-CP & amended NĐ 119/2025/NĐ-CP.
- Structure data conforming strictly to Mẫu số 02 Phụ lục III Nghị định 06/2022/NĐ-CP.
- Save structured extractions to 'intermediate/mitigation_extracted.json'.`,
  },
];

const extractions = await parallel(
  SUBAGENT_CONFIGS.map(config => () =>
    agent(config.prompt, {
      label: config.label,
      phase: 'Domain Subagents Extraction',
      subagent_type: config.subagent_type,
    })
  )
);

log('Domain extraction complete. All intermediate JSON records, QueryLogs, and AssumptionLogs written to blackboard.');

// ---------------------------------------------------------------------------
// Phase 3: Deterministic Math Verification & Regulatory Synthesis
// ---------------------------------------------------------------------------
phase('Deterministic Math & Regulatory Synthesis');
log('Executing deterministic carbon accounting, 95% CI error propagation, and synthesizing Vietnamese regulatory deliverables.');

const synthesisReport = await agent(
  `You are the Report Synthesizer Agent (ag-synthesizer).
Execute deterministic calculation and synthesis based on intermediate artifacts:

1. Ingest intermediate JSON extractions:
   - 'intermediate/scope1_extracted.json'
   - 'intermediate/scope2_extracted.json'
   - 'intermediate/scope3_extracted.json'
   - 'intermediate/mitigation_extracted.json'
   - 'intermediate/query_log.json'
   - 'intermediate/assumption_log.json'

2. Perform Deterministic Python Math:
   - Calculate emissions: E = Activity * EF for Scope 1, 2, 3.
   - Calculate analytical 95% CI error bounds: sigma_total = sqrt(sum(sigma_i^2)).
   - Calculate Mẫu 02 mitigation reduction: GPT = PT_CS - PT.
   - Calculate Quota surplus/deficit: Balance = Quota_alloc - Total_Actual_Emissions.
   - Evaluate 5-dimension reliability scores with penalty deductions from AssumptionLog.

3. Generate Formal Vietnamese Regulatory Deliverables in 'deliverables/':
   - 'Bao_cao_kiem_ke_va_giam_nhe_KNK.md' (Part I: Corporate Inventory, Part II: Mẫu 02 NĐ 06/2022, Part III: Audit Lineage).
   - 'Bao_cao_kiem_ke_va_giam_nhe_KNK.html' (Standalone printable interactive dashboard with radar charts & tables).
   - 'Bao_cao_Mau02_ND06.docx' (Official Word template for government submission).
   - 'final_inventory_summary.json' (Machine-readable inventory summary).`,
  {
    label: 'synth:final-report',
    phase: 'Deterministic Math & Regulatory Synthesis',
    subagent_type: 'ag-synthesizer',
  }
);

log('Workflow completed successfully. Final inventory, Mẫu 02 mitigation report, and audit logs are ready in deliverables/.');

return {
  status: 'COMPLETED',
  inputFile,
  discovery: discoveryResult,
  extractions,
  report: synthesisReport,
};
