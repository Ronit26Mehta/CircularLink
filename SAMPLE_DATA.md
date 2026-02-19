# Sample Test Data — CircuLink Terminal

Use these credentials to register and test the application.

---

## Company 1: TechSteel Industries (Seller Focus)

**Registration Details:**

| Field | Value |
|---|---|
| **GSTIN** | `27AABCT1234M1Z5` |
| **Company Name** | TechSteel Industries Pvt Ltd |
| **Primary Product** | Steel Manufacturing & Metal Fabrication |
| **City** | Pune |
| **State** | Maharashtra |
| **Email** | operations@techsteel.in |
| **Address** | Plot 42, Chakan Industrial Area, Pune 410501 |
| **Latitude** | 18.5204 |
| **Longitude** | 73.8567 |
| **Google API Key** | *(Paste your own from [aistudio.google.com](https://aistudio.google.com))* |

**Use Case:** This company is a steel manufacturer generating metal scrap, slag, and other byproducts. Perfect for testing the **Seller (F3)** screen with AI byproduct prediction.

**Sample Products to Add Manually:**
- Steel slag (5000 tons)
- Metal cutting scrap (2500 kg)
- Iron oxide dust (800 kg)

---

## Company 2: GreenCycle Solutions (Buyer Focus)

**Registration Details:**

| Field | Value |
|---|---|
| **GSTIN** | `24AACCR5678P1Z9` |
| **Company Name** | GreenCycle Solutions Ltd |
| **Primary Product** | Recycling & Circular Economy Services |
| **City** | Ahmedabad |
| **State** | Gujarat |
| **Email** | procurement@greencycle.co.in |
| **Address** | 18/B, GIDC Vatva, Ahmedabad 382445 |
| **Latitude** | 23.0225 |
| **Longitude** | 72.5714 |
| **Google API Key** | *(Paste your own from [aistudio.google.com](https://aistudio.google.com))* |

**Use Case:** This company sources industrial waste for recycling. Perfect for testing the **Buyer (F2)** screen with intelligent search and matching.

**Sample Search Queries:**
- "plastic waste hdpe"
- "steel scrap"
- "paper cardboard"
- "copper wire"

---

## Quick Start Instructions

### Option 1: Register Both Companies (Recommended)

1. Launch CircuLink Terminal:
   ```bash
   circularlink
   ```

2. Register **Company 1** (TechSteel):
   - Click "Register" tab
   - Enter all TechSteel details from above
   - Paste your Google API key
   - Click "Register"

3. Logout (`F4` → Logout)

4. Register **Company 2** (GreenCycle):
   - Click "Register" tab
   - Enter all GreenCycle details
   - Use the **same** Google API key
   - Click "Register"

5. Now you can switch between companies by logging in with their respective GSTINs

### Option 2: Pre-populate Data (Advanced)

Create `~/.circularlink/companies.json` manually:

```json
{
  "comp-27AABCT1234M1Z5": {
    "id": "comp-27AABCT1234M1Z5",
    "gstin": "27AABCT1234M1Z5",
    "name": "TechSteel Industries Pvt Ltd",
    "primary_product": "Steel Manufacturing & Metal Fabrication",
    "city": "Pune",
    "state": "Maharashtra",
    "email": "operations@techsteel.in",
    "address": "Plot 42, Chakan Industrial Area, Pune 410501",
    "lat": 18.5204,
    "lon": 73.8567,
    "created_at": "2026-02-19T10:00:00"
  },
  "comp-24AACCR5678P1Z9": {
    "id": "comp-24AACCR5678P1Z9",
    "gstin": "24AACCR5678P1Z9",
    "name": "GreenCycle Solutions Ltd",
    "primary_product": "Recycling & Circular Economy Services",
    "city": "Ahmedabad",
    "state": "Gujarat",
    "email": "procurement@greencycle.co.in",
    "address": "18/B, GIDC Vatva, Ahmedabad 382445",
    "lat": 23.0225,
    "lon": 72.5714,
    "created_at": "2026-02-19T10:00:00"
  }
}
```

Then set your API key in `~/.circularlink/config.json`:

```json
{
  "api_key": "YOUR_GOOGLE_API_KEY_HERE",
  "current_company_id": "comp-27AABCT1234M1Z5"
}
```

---

## Testing Scenarios

### Seller Flow (TechSteel)
1. Login as TechSteel (`27AABCT1234M1Z5`)
2. Press `F3` (Sell: Inventory)
3. Click "Run AI Byproduct Scan" — Gemini will predict byproducts from "Steel Manufacturing"
4. Manually add products via "+ Add Product" button
5. View hazard screening results (status column)

### Buyer Flow (GreenCycle)
1. Login as GreenCycle (`24AACCR5678P1Z9`)
2. Press `F2` (Buy: Sourcing)
3. Click "Search" button
4. Enter query: "steel scrap"
5. Gemini expands keywords → fuzzy matching runs
6. View ranked results with scores (fuzzy + location weighted)

### Cross-Company Matching
1. Add products as TechSteel (seller)
2. Switch to GreenCycle (buyer)
3. Search for materials → should match TechSteel's listings
4. View match scores showing proximity (Pune ↔ Ahmedabad ~660 km)

### Dashboard (F1)
- View stats: total companies, products, matches
- See recent matches sorted by score
- Read LLM audit log (Gemini API calls)

---

## GSTIN Format Reference

```
27 AABCT 1234 M 1 Z 5
│  │     │    │ │ │ │
│  │     │    │ │ │ └─ Check digit
│  │     │    │ │ └─── Literal 'Z'
│  │     │    │ └───── Entity code (1-9, A-Z)
│  │     │    └─────── Entity type (C=Company, P=Partnership, etc)
│  │     └──────────── PAN last 4 digits
│  └────────────────── PAN first 5 chars
└───────────────────── State code (27=Maharashtra, 24=Gujarat)
```

---

## Google API Key Setup

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click "Get API Key"
3. Create new key or use existing
4. Copy the key — starts with `AIzaSy...`
5. Paste during registration or in KYC Settings (`F4`)

**Free Tier Limits:**
- Gemini 2.5 Flash: 15 RPM, 1M TPM, 1500 RPD
- Sufficient for testing and small-scale deployments

---

## Troubleshooting

**"Invalid GSTIN"**
- Ensure exact format: 15 characters, valid state code (01-38)
- Use provided sample GSTINs verbatim

**"GSTIN already registered"**
- Switch to Login tab instead of Register
- Or use the other company's GSTIN

**"No matches found"**
- Ensure at least one company has added products (F3)
- Products must have status "approved"
- Try broader search terms

**Hazard-blocked products**
- Products containing hazardous materials are auto-blocked
- Check hazardous.csv for restricted substances
- Blocked products never appear in buyer search

