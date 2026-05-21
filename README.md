# Enterprise Dashboard with Streamlit and Zoho CRM

Base Streamlit application for reviewing company dashboards and, when ready,
connecting live data from Zoho CRM.

It includes:

- Basic login for the demo: `camilo.cast` / `123456`.
- OAuth connection using a Zoho `refresh_token`.
- Zoho CRM API v8 module reads.
- Demo dashboards for recruiter performance, call center performance, sales
  performance, marketing performance, and gross revenue.
- Call center staffing model with agents by city, normalized KPIs, a simple
  regression, and an 80% company growth target scenario.
- Cross-dimensional demo data by city, tenant, industry, and product.
- Gross revenue subtabs for overview, revenue mix, segments, and detail.
- Demo mode so the app can be reviewed before Zoho credentials are available.

## 1. Create the environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure Zoho

Copy the sample credentials file:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your Zoho credentials:

- `accounts_url`: OAuth domain for your region.
- `api_domain`: API domain for your region.
- `client_id`: Client ID from the Zoho API Console.
- `client_secret`: Client Secret from the Zoho API Console.
- `refresh_token`: refresh token used to generate access tokens.

Suggested scope for this first version:

```text
ZohoCRM.modules.ALL
```

For production, reduce scopes to read-only access for the modules you use.

## 3. Run the app

```bash
streamlit run app.py
```

## 4. Customize for your company

In `app.py` you can update:

- `DEAL_FIELDS`: fields from the `Deals` module.
- `LEAD_FIELDS`: fields from the `Leads` module.
- The modules loaded through `load_zoho_module("Deals", ...)` and
  `load_zoho_module("Leads", ...)`.

If your company uses Zoho Books, Desk, Analytics, or another Zoho product, the
dashboard structure can stay in place while `zoho_client.py` is adapted to those
endpoints.

## Official references

- Zoho CRM API v8: https://www.zoho.com/crm/developer/docs/api/v8/
- OAuth in Zoho CRM API v8: https://www.zoho.com/crm/developer/docs/api/v8/oauth-overview.html
- Get Records: https://www.zoho.com/crm/developer/docs/api/v8/get-records.html
