"""Built-in knowledge base for Rahul Technologies — no tool call required."""

COMPANY_KNOWLEDGE = """
# Rahul Technologies — Company Knowledge Base

## Overview
Rahul Technologies is a premium Indian technology hardware company founded in 2010, headquartered
in Bengaluru, Karnataka. The company specialises in high-performance computer peripherals designed
for professionals, gamers, and enterprises.

## Mission
To deliver precision-engineered, ergonomically superior peripherals that enhance human productivity
and digital creativity at every price point.

## Vision
To become Asia's most trusted peripheral brand by 2030, known for quality, innovation, and
after-sales excellence.

## Core Values
- Engineering Excellence: Every product undergoes 1,200+ QA checks before shipment.
- Customer First: 24×7 multilingual support across 14 Indian languages.
- Sustainability: 40 % recycled packaging; carbon-neutral manufacturing target by 2028.
- Innovation: 18 % of annual revenue reinvested in R&D.

## Departments
- R&D (Research & Development)
- Manufacturing & Quality Assurance
- Sales & Distribution
- Customer Experience
- Marketing & Brand
- Finance & Operations
- Human Resources
- IT & Digital Infrastructure

## Product Lines

### Keyboards
| Series         | Type               | Switch Options          | Key Feature                         |
|----------------|--------------------|-------------------------|-------------------------------------|
| ProType X      | Mechanical         | Red, Blue, Brown        | PBT keycaps, per-key RGB, 1 ms poll |
| ProType S      | Silent Mechanical  | Silent Red, Silent Pink | Office-grade noise reduction        |
| AirType Slim   | Membrane           | Scissor                 | Ultra-thin 3.8 mm profile           |
| AirType Wireless| Wireless Membrane | Bluetooth 5.3 + 2.4 GHz| 120-hour battery life               |
| TactiKey 60    | 60 % Mechanical    | Gateron G-Pro           | Compact, hot-swap, aluminium case   |
| TactiKey TKL   | TKL Mechanical     | Gateron G-Pro           | Tenkeyless, CNC aluminium           |

### Mice
| Series           | Type        | DPI Range     | Key Feature                           |
|------------------|-------------|---------------|---------------------------------------|
| PrecisionPro X   | Wired       | 100–25,600    | PAW3395 sensor, 8 programmable buttons|
| PrecisionPro W   | Wireless    | 100–25,600    | 2.4 GHz + BT, 70-hour battery         |
| ErgoGlide M      | Ergonomic   | 400–8,000     | Vertical grip, customisable weights   |
| SwiftClick G     | Gaming      | 200–16,000    | 1000 Hz polling, optical switches     |
| SwiftClick G Pro | Gaming Pro  | 200–32,000    | PTFE feet, 60 g ultralight            |
| NanoMouse T      | Travel      | 800–3,200     | Foldable receiver, 18-month battery   |

## Manufacturing
- Primary facility: Bengaluru SEZ (50,000 sq ft)
- Secondary facility: Pune (20,000 sq ft — packaging & logistics)
- ISO 9001:2015 and ISO 14001:2015 certified
- In-house PCB fabrication and optical sensor calibration lab

## Support
- Warranty: 2 years on all products; 3 years on Pro-series
- Support channels: Email, Phone, Live Chat, WhatsApp
- Authorised service centres: 120+ across India

## Distribution
- Direct: rahultechnologies.com
- Offline: 5,000+ retail partners (Croma, Reliance Digital, local resellers)
- Online marketplaces: Amazon India, Flipkart, Meesho
- B2B: Corporate procurement portal for bulk orders

## Awards & Recognition
- "Best Indian Peripheral Brand" — TechRadar India 2022, 2023
- "Top 10 Gaming Hardware Brands in South Asia" — GadgetByte 2023
- CII National Award for Manufacturing Excellence 2023

## Employee Count
Approximately 2,400 employees as of 2025.

## Key Leadership
- CEO: Rahul Sharma (Founder)
- CTO: Dr Priya Menon
- CFO: Ankit Verma
- VP Sales: Suresh Nair
""".strip()

# Topics that can be answered from knowledge (no tool call)
KNOWLEDGE_KEYWORDS = [
    "overview", "about", "company", "mission", "vision", "values",
    "department", "product", "keyboard", "mouse", "mice",
    "manufacture", "manufacturing", "support", "warranty",
    "distribution", "award", "employee", "ceo", "cto", "cfo",
    "founder", "headquarter", "bengaluru", "history", "founded",
    "protype", "airtype", "tactikey", "precisionpro", "ergo",
    "swiftclick", "nanomouse", "lineup", "series", "feature",
    "leadership", "iso", "certification",
]
