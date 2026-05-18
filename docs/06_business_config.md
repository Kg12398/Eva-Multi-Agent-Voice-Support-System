# KG ElectroPower — Voice Agent Business Configuration

## Company Profile
- **Company Name:** KG ElectroPower
- **Industry:** Power Electronics / Green Energy
- **AI Assistant Name:** EVA (Electronic Voice Assistant)

## Product Catalog

| # | Product | Category | Common Models (fill later) |
|---|---------|----------|---------------------------|
| 1 | Solar Panel | Solar | |
| 2 | Inverter | Power Backup | |
| 3 | 3-Wheeler Battery | EV / Automotive | |
| 4 | Air Purifier | Home Appliance | |
| 5 | Oxygen Concentrator | Medical Device | |

## Top 5 Customer Issues

| # | Issue | Products Affected | Possible Causes |
|---|-------|-------------------|-----------------|
| 1 | Battery Not Charging | Inverter, 3-Wheeler | Charger issue, Battery failure, Loose connection |
| 2 | Inverter Not Turning ON | Inverter | Power supply issue, Internal fault, Fuse blown |
| 3 | Backup Time is Very Low | Inverter | Battery degradation, Overload usage, Old battery |
| 4 | Battery Draining Quickly | 3-Wheeler Battery | Overuse, Old battery, Charging problem |
| 5 | Inverter Beeping / Alarm | Inverter | Overload, Low battery, Fault indicator |

## Information to Collect from Caller

| Slot | Required? | Example |
|------|-----------|---------|
| customer_name | Yes | "Rajesh Kumar" |
| phone_number | Auto (from caller ID) | +91-9876543210 |
| product_category | Yes | "Inverter" |
| product_model | Optional | "KG-INV-2000" |
| serial_number | Optional | "KGEP-2024-XXXXX" |
| issue_description | Yes | "Inverter is not turning on" |
| purchase_date | Optional | For warranty check |

## Voice & Language

- **Primary Language:** English
- **Secondary Language:** Hindi
- **Note:** Start with English-only in Phase 1, add Hindi in Phase 2

## Greeting Message

**English:**
> "Hello, thank you for calling KG ElectroPower. This call may be recorded for quality purposes. My name is EVA, your virtual support assistant. How can I help you today?"

**Hindi (Phase 2):**
> "Namaste, KG ElectroPower mein aapka swagat hai. Mera naam EVA hai, main aapki virtual support assistant hoon. Main aapki kaise madad kar sakti hoon?"

## Escalation Rules

- **Method:** Ticket-based (no live human transfer)
- **Ticket Storage:** PostgreSQL
- **Notification:** Email to support team
- **Auto-Escalate When:**
  - 2 failed troubleshooting attempts
  - User explicitly asks for human help
  - Sentiment = angry/frustrated AND issue unresolved
  - Issue involves safety (Oxygen Concentrator malfunction)

## Closure Message

> "Thank you for calling KG ElectroPower. Your ticket number is [TICKET_ID]. Our team will follow up within 24 hours. Have a great day!"
