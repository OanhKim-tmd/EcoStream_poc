"""PII Masking Engine for EcoStream Carbon Accounting Pipeline.

Masks personally identifiable information (PII) and business-sensitive data from
extracted document text BEFORE it is sent to any external LLM or cloud service.
All masking runs 100% locally on CPU — no network calls.

Design Principles:
    1. Preserve all NUMERICAL data needed for carbon math (kWh, tonnes, km, VND amounts).
    2. Replace all IDENTITY data (company names, tax IDs, addresses, person names,
       customer codes, meter IDs, contract numbers, bank accounts).
    3. Maintain a reversible mapping table that NEVER leaves the local machine.
    4. Be conservative — mask more rather than less. A false positive (masking a
       non-PII string) is harmless; a false negative (leaking real PII) is not.

Supported PII categories for Vietnamese business documents:
    - Mã số thuế (Tax ID): 10 or 13 digit patterns
    - Tên đơn vị / Tên khách hàng (Company names): CÔNG TY..., CTY..., DN...
    - Địa chỉ (Addresses): Lô, Số, KCN, Phường, Quận, TP...
    - Mã khách hàng EVN (Customer codes): PD..., PB..., PK..., PE...
    - Số công tơ (Meter IDs): EVN-xxx, meter serial numbers
    - Số hợp đồng (Contract numbers): HĐMBĐ-..., HĐ-...
    - Tên người (Person names after Vietnamese title keywords)
    - Số tài khoản ngân hàng (Bank account numbers)
    - Mã vận đơn (Waybill codes): LOG-..., AWB-..., BL-...
    - Mã mua hàng (PO codes): PO-...
    - Tên nhà vận chuyển / nhà cung cấp (Supplier/carrier names)
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class MaskMapping:
    """Reversible mapping between original PII values and their masked tokens.

    This object MUST stay on the local machine. It is the only link between
    anonymized text sent to cloud LLMs and the real customer identity.
    """
    _forward: Dict[str, str] = field(default_factory=dict)   # original -> token
    _reverse: Dict[str, str] = field(default_factory=dict)   # token -> original
    _counters: Dict[str, int] = field(default_factory=dict)  # category -> next_id

    def mask(self, original: str, category: str) -> str:
        """Return an anonymized token for `original`, reusing if already mapped."""
        original_stripped = original.strip()
        if not original_stripped:
            return original_stripped

        if original_stripped in self._forward:
            return self._forward[original_stripped]

        idx = self._counters.get(category, 0) + 1
        self._counters[category] = idx
        token = f"[{category}_{idx:03d}]"

        self._forward[original_stripped] = token
        self._reverse[token] = original_stripped
        return token

    def unmask(self, token: str) -> Optional[str]:
        """Recover the original value from a masked token."""
        return self._reverse.get(token)

    def unmask_text(self, masked_text: str) -> str:
        """Replace all tokens in text with their original values."""
        result = masked_text
        # Sort by token length descending to avoid partial replacements
        for token, original in sorted(self._reverse.items(), key=lambda x: -len(x[0])):
            result = result.replace(token, original)
        return result

    @property
    def summary(self) -> Dict[str, int]:
        """Count of masked items per category."""
        counts: Dict[str, int] = {}
        for token in self._reverse:
            cat = token.split("_")[0].lstrip("[")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def to_json(self) -> str:
        """Serialize mapping to JSON for secure local storage."""
        return json.dumps({
            "forward": self._forward,
            "reverse": self._reverse,
            "counters": self._counters,
        }, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MaskMapping":
        """Deserialize mapping from JSON."""
        data = json.loads(json_str)
        m = cls()
        m._forward = data["forward"]
        m._reverse = data["reverse"]
        m._counters = data["counters"]
        return m


class PIIMasker:
    """Masks Vietnamese business PII from extracted document text.

    Usage:
        masker = PIIMasker()
        masked_text, mapping = masker.mask_text(raw_text)
        # Send masked_text to cloud LLM safely
        # Later, recover originals:
        original_text = mapping.unmask_text(masked_text)
    """

    # ── Vietnamese Tax ID (Mã số thuế) ──────────────────────────────
    # 10-digit or 13-digit (10 digits + dash + 3 digits)
    RE_TAX_ID = re.compile(
        r'(?<![0-9])'
        r'(\d{10}(?:-\d{3})?)'
        r'(?![0-9])'
    )

    # ── EVN Customer Code (Mã khách hàng) ───────────────────────────
    # PD, PB, PK, PE followed by digits
    RE_EVN_CUSTOMER = re.compile(r'\b(P[DBKE]\d{8,15})\b')

    # ── EVN Meter ID (Số công tơ) ───────────────────────────────────
    RE_METER_ID = re.compile(r'\b(EVN[\w-]{3,30})\b', re.IGNORECASE)

    # ── Contract Number (Số hợp đồng) ──────────────────────────────
    RE_CONTRACT = re.compile(r'\b(H[ĐD](?:MB[ĐD])?[\w/-]{3,30})\b')

    # ── Waybill / Logistics Code ────────────────────────────────────
    RE_WAYBILL = re.compile(r'\b((?:LOG|AWB|BL|VĐ)[-\d]{2,15})\b', re.IGNORECASE)

    # ── Purchase Order Code ─────────────────────────────────────────
    RE_PO_CODE = re.compile(r'\b(PO[-\d]{2,15})\b', re.IGNORECASE)

    # ── Bank Account Number ─────────────────────────────────────────
    # Vietnamese bank accounts: 10-19 digit sequences near banking keywords
    RE_BANK_ACCOUNT = re.compile(
        r'(?:Tài khoản|TK|Số TK|STK)[:\s]*(\d{10,19})',
        re.IGNORECASE,
    )

    # ── Invoice Lookup Code ─────────────────────────────────────────
    RE_LOOKUP = re.compile(r'\b((?:EVN|PLX)[-\d]{6,25})\b', re.IGNORECASE)

    # ── CQT Code (Tax Authority Code) ──────────────────────────────
    RE_CQT = re.compile(r'\b(\d{4}CQT\d{10,30})\b')

    # ── Certificate ID (Chứng thư số) ──────────────────────────────
    RE_CERT = re.compile(r'\b(CA-[\w-]{10,40})\b')

    # ── Company Name patterns ──────────────────────────────────────
    # Vietnamese company names typically start with these phrases
    COMPANY_PREFIXES = [
        r'CÔNG TY(?:\s+CỔ PHẦN|\s+TNHH(?:\s+MTV)?|\s+CP)',
        r'CTY(?:\s+CP|\s+TNHH)',
        r'TẬP ĐOÀN',
        r'TỔNG CÔNG TY',
        r'DOANH NGHIỆP(?:\s+TƯ NHÂN)?',
        r'CHI NHÁNH',
        r'NHÀ MÁY',
    ]
    # Match company name: prefix + remaining uppercase Vietnamese words
    RE_COMPANY = re.compile(
        r'(' + '|'.join(COMPANY_PREFIXES) + r')'
        r'(?:\s+[A-ZÀ-Ỹ0-9&.,()-]+)+',
        re.UNICODE,
    )

    # ── Supplier / carrier names in CSV context ────────────────────
    # These appear after commas in freight logs and supplier spend files
    SUPPLIER_KEYWORDS = [
        r'Công ty(?:\s+CP|\s+TNHH|\s+MTV)?',
        r'Cty',
        r'Logistics',
        r'Vận tải',
        r'Chuyển phát',
        r'Đại lý',
        r'Bao bì',
        r'Nhựa',
        r'Dệt may',
        r'Chợ',
    ]
    RE_SUPPLIER = re.compile(
        r'(' + '|'.join(SUPPLIER_KEYWORDS) + r')'
        r'(?:\s+[\wÀ-ỹ0-9&.,()-]+)+',
        re.UNICODE,
    )

    # ── Vietnamese Address ─────────────────────────────────────────
    ADDRESS_MARKERS = [
        r'(?:Lô|Số|Tầng)\s+[\wÀ-ỹ/-]+',
        r'(?:KCN|Khu Công nghiệp|CCN|Cụm Công nghiệp)\s+[\wÀ-ỹ\s]+',
        r'(?:Phường|Xã|Thị trấn|TT\.?)\s+[\wÀ-ỹ\s]+',
        r'(?:Quận|Huyện|Thị xã|TX\.?|Q\.?)\s+[\wÀ-ỹ\s]+',
        r'(?:TP\.?|Thành phố|Tỉnh)\s+[\wÀ-ỹ\s]+',
    ]
    RE_ADDRESS = re.compile(
        r'((?:' + '|'.join(ADDRESS_MARKERS) + r')(?:[,\s]+(?:' + '|'.join(ADDRESS_MARKERS) + r'))*)',
        re.UNICODE,
    )

    # ── Person Names (after title keywords) ────────────────────────
    # Vietnamese person names: 2-4 syllables after trigger phrases
    PERSON_TRIGGERS = [
        r'Người lập biểu:\s*',
        r'Kế toán trưởng:\s*',
        r'Người bán hàng:\s*',
        r'(?:Cửa hàng trưởng|Giám đốc|Phó Giám đốc|Trưởng phòng):\s*',
        r'Ký bởi:\s*',
    ]
    RE_PERSON = re.compile(
        r'(?:' + '|'.join(PERSON_TRIGGERS) + r')'
        r'([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,4})',
        re.UNICODE,
    )

    # ── EVN Invoice Number & Serial ────────────────────────────────
    RE_INVOICE_NO = re.compile(r'(?:Số(?:\s*\(No\.\))?)[:\s]*(\d{6,8})', re.IGNORECASE)
    RE_SERIAL = re.compile(r'(?:Ký hiệu(?:\s*\(Serial\))?)[:\s]*(1[CK]\d{2}T\w{2,4})', re.IGNORECASE)

    def mask_text(self, text: str, mapping: Optional[MaskMapping] = None) -> Tuple[str, MaskMapping]:
        """Mask all PII in text, returning (masked_text, mapping).

        The mapping is needed later to unmask. It accumulates across calls
        if you pass the same mapping object, so the same company always gets
        the same token across multiple documents.
        """
        if mapping is None:
            mapping = MaskMapping()

        result = text

        # Order matters: mask specific patterns first, then broader ones.
        # This prevents partial matches from being clobbered.

        # 1. CQT codes (long, specific — mask first)
        result = self._mask_pattern(result, self.RE_CQT, "CQT", mapping)

        # 2. Certificate IDs
        result = self._mask_pattern(result, self.RE_CERT, "CERT", mapping)

        # 3. Bank accounts (before generic digit patterns)
        result = self._mask_pattern(result, self.RE_BANK_ACCOUNT, "BANK", mapping, group=1)

        # 4. EVN customer codes
        result = self._mask_pattern(result, self.RE_EVN_CUSTOMER, "CUST", mapping)

        # 5. Meter IDs
        result = self._mask_pattern(result, self.RE_METER_ID, "METER", mapping)

        # 6. Contract numbers
        result = self._mask_pattern(result, self.RE_CONTRACT, "CONTRACT", mapping)

        # 7. Waybill codes
        result = self._mask_pattern(result, self.RE_WAYBILL, "WAYBILL", mapping)

        # 8. PO codes
        result = self._mask_pattern(result, self.RE_PO_CODE, "PO", mapping)

        # 9. Lookup codes
        result = self._mask_pattern(result, self.RE_LOOKUP, "LOOKUP", mapping)

        # 10. Invoice numbers and serials
        result = self._mask_pattern(result, self.RE_INVOICE_NO, "INV_NO", mapping, group=1)
        result = self._mask_pattern(result, self.RE_SERIAL, "SERIAL", mapping, group=1)

        # 11. Person names (before company names, since some overlap)
        result = self._mask_person_names(result, mapping)

        # 12. Company names (uppercase, prominent)
        result = self._mask_pattern(result, self.RE_COMPANY, "COMPANY", mapping)

        # 13. Supplier / carrier names (mixed case)
        result = self._mask_pattern(result, self.RE_SUPPLIER, "SUPPLIER", mapping)

        # 14. Tax IDs (after company names so we don't break company lines)
        result = self._mask_tax_ids(result, mapping)

        # 15. Addresses (broadest pattern — last)
        result = self._mask_addresses(result, mapping)

        return result, mapping

    def _mask_pattern(
        self,
        text: str,
        pattern: re.Pattern,
        category: str,
        mapping: MaskMapping,
        group: int = 0,
    ) -> str:
        """Replace all matches of `pattern` (capturing group `group`) with masked tokens."""
        def replacer(match: re.Match) -> str:
            original = match.group(group)
            token = mapping.mask(original, category)
            if group == 0:
                return token
            # Preserve text before and after the captured group
            full = match.group(0)
            return full.replace(original, token, 1)

        return pattern.sub(replacer, text)

    def _mask_person_names(self, text: str, mapping: MaskMapping) -> str:
        """Mask Vietnamese person names that appear after known title keywords."""
        def replacer(match: re.Match) -> str:
            name = match.group(1)
            token = mapping.mask(name, "PERSON")
            return match.group(0).replace(name, token, 1)

        return self.RE_PERSON.sub(replacer, text)

    def _mask_tax_ids(self, text: str, mapping: MaskMapping) -> str:
        """Mask tax IDs with context awareness to avoid masking kWh or monetary values."""
        # Only mask digit sequences that appear near tax-related keywords
        tax_context = re.compile(
            r'(?:Mã số thuế|MST|Mã số thuế / Mã định danh)[:\s]*(\d{10}(?:-\d{3})?)',
            re.IGNORECASE,
        )

        def replacer(match: re.Match) -> str:
            tax_id = match.group(1)
            token = mapping.mask(tax_id, "TAX_ID")
            return match.group(0).replace(tax_id, token, 1)

        return tax_context.sub(replacer, text)

    def _mask_addresses(self, text: str, mapping: MaskMapping) -> str:
        """Mask addresses that appear after known address label keywords."""
        addr_context = re.compile(
            r'(?:Địa chỉ[^:]*|Địa chỉ sử dụng điện)[:\s]*(.*?)(?=\n|$)',
            re.IGNORECASE | re.UNICODE,
        )

        def replacer(match: re.Match) -> str:
            addr = match.group(1).strip()
            if len(addr) < 5:
                return match.group(0)
            token = mapping.mask(addr, "ADDRESS")
            return match.group(0).replace(addr, token, 1)

        return addr_context.sub(replacer, text)

    def verify_no_pii(self, masked_text: str, mapping: MaskMapping) -> List[str]:
        """Check if any original PII values still appear in the masked text.

        Returns a list of warnings for any leaked PII found.
        """
        warnings = []
        for original, token in mapping._forward.items():
            if original in masked_text:
                warnings.append(
                    f"PII LEAK: '{original}' (mapped to {token}) still found in masked text"
                )
        return warnings
