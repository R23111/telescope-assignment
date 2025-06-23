# Telescope Assignment

This repository contains a technical implementation for a system that processes company data using user-defined rules, supporting compound logical conditions and LLM-based evaluations. The backend is built with FastAPI and SQLAlchemy (async), with a PostgreSQL database orchestrated via Docker Compose.

## Getting Started

### Using Docker (Recommended)

To run the application with Docker:

```bash
docker-compose up --build
```

This will start:

- A PostgreSQL database container
- The FastAPI application server
- Automatic schema creation via SQLAlchemy

The application will be accessible at: `http://localhost:8000`

### Note on Docker base image:
> This project uses `python:3.11-slim` as the base image. While this image may show known vulnerabilities via automated scanners (e.g. Docker DX), it was chosen for its lightweight size and speed for prototyping. In a production environment, a more hardened image (such as one with pinned Debian versions or using distro-less) should be considered.

---

### DEV Setup

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install the dependencies:

```bash
pip install -r requirements-dev.txt
```

1. Configure your environment variables in a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/telescope
```

4. Ensure PostgreSQL is running locally and the database is created:

```bash
docker-compose up db
```

5. Run the development server:

```bash
uvicorn app.main:app --reload
```

---

## API Documentation

After starting the application, the interactive API documentation is available at:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Data Import

To import company data, use the following endpoint:

```
POST /import_company_data
```

Accepted input:

- A CSV file with the required fields
  - In the sample CSV, there is a typo in the field `employee_rowth_2Y`. The application accepts both the typo and the correct spelling `employee_growth_2Y`
- A JSON array matching the structure of the sample dataset

---

## LLM Operator Support

To use rules involving a `"LLM"` operator, you must configure access to a language model provider. For instance, using [OpenRouter.ai]:

1. Sign up at https://openrouter.ai
2. Obtain your API key
3. Add the following line to your `.env` file:

```env
OPENROUTER_API_KEY=your_api_key_here
```

---

## Project Structure

```
app/
├── api/            # FastAPI route definitions
├── core/           # Configurations, constants, and utilities
├── models/         # SQLAlchemy ORM models
├── schemas/        # Pydantic schemas (request/response)
├── services/       # Business logic (rule processing, LLM evaluation)
├── utils/          # Misc utility methods
└── main.py         # FastAPI application entry point
```


## API Endpoints:

### `/import_company_data` Endpoint

#### Description

`POST /import_company_data`

This endpoint allows you to import company data into the system. Data can be submitted either through a CSV file upload or via a JSON array. It ensures no duplicate entries are created by checking for existing records based on the `url` field.

It returns a summary detailing how many records were successfully imported, how many were skipped due to duplication, and how many failed due to errors.


#### Request Parameters

You must provide **either**:

* A CSV file (`multipart/form-data`) via the `file` field
  **or**
* A JSON array of companies in the request body via the `json_data` field.

> **Note**: If both are provided, the CSV file will take precedence.


#### Request Format

##### **Option 1: CSV Upload**

```bash
curl -X POST http://localhost:8000/import_company_data \
  -F "file=@companies.csv"
```

Expected CSV columns:

```
name,url,founded_year,total_employees,headquarters_city,employee_locations,employee_growth_2y,employee_growth_1y,employee_growth_6m,description,industry
```

##### **Option 2: JSON Payload**

```bash
curl -X POST http://localhost:8000/import_company_data \
  -H "Content-Type: application/json" \
  -d '[
    {
      "name": "Example Corp",
      "url": "https://example.com",
      "founded_year": 2010,
      "total_employees": 100,
      "headquarters_city": "San Francisco",
      "employee_locations": {"USA": 32, "Canada": 3, "UK": 2, "India": 1},
      "employee_growth_2y": 0.15,
      "employee_growth_1y": 0.10,
      "employee_growth_6m": 0.05,
      "description": "An innovative tech company.",
      "industry": "Technology"
    }
  ]'
```


#### Response Format

Returns a JSON object summarizing the import operation.

##### Example Response:

```json
{
  "imported_records": 1,
  "skipped_duplicates": 0,
  "record_errors": 0,
  "errors": []
}
```

If there are any errors, the `errors` list will include the names of companies that could not be imported.


### `/get_companies` Endpoint

#### Description

`GET /get_companies`

This endpoint retrieves a list of all companies that have been imported into the system. For each company, it returns both the raw company data and any features that were processed through defined rules.


#### Request Format

This endpoint does not require any request parameters.

##### Example:

```bash
curl -X GET http://localhost:8000/get_companies
```


#### Response Format

The response is a list of company objects, each including:

* `id`: Unique identifier for the company
* `url`: Company website
* `data`: Dictionary of company attributes excluding internal fields
* `processed_features`: List of rule-based features associated with the company
* `imported_at`: Timestamp when the company was first imported
* `last_processed_at`: Timestamp when the company was last processed

##### Example Response:

```json
[
  {
    "id": "f8ad45cb-27b0-42d7-9f7e-1bb4a3fca7dc",
    "url": "https://example.com",
    "data": {
      "name": "Example Corp",
      "founded_year": 2010,
      "total_employees": 100,
      "headquarters_city": "San Francisco",
      "employee_locations": "USA, Canada",
      "employee_growth_2y": 0.15,
      "employee_growth_1y": 0.10,
      "employee_growth_6m": 0.05,
      "description": "An innovative tech company.",
      "industry": "Technology"
    },
    "processed_features": [
      {
        "user_name": "Larissa",
        "company_name": "Example Corp",
        "feature_name": "is_saas",
        "value": true
      }
    ],
    "imported_at": "2025-06-20T14:32:12",
    "last_processed_at": "2025-06-23T09:55:48"
  }
]
```

If no companies have been imported or processed, an empty list is returned.


### `/create_rule` Endpoint

#### Description

`POST /create_rule`

This endpoint creates one or more rules for a specified user. If the user does not exist, it will automatically create the user before associating the rules.

Each rule defines a logical condition (or set of conditions) that is used during company data processing. The rule is tied to a user, and the endpoint ensures no duplicate rules are created.



#### Request Format

##### URL

```
POST /create_rule
```

##### JSON Body

```json
{
  "user_name": "User",
  "rules": [
    {
      "input": "noth_america_based",
      "feature_name": "noth_america_based",
      "operation": {
        "OR": [
          {
            "target_object": "headquarters_country",
            "operator": "EQUALS",
            "value": "Canada"
          },
          {
            "target_object": "headquarters_country",
            "operator": "EQUALS",
            "value": "USA"
          }
        ]
      },
      "match": 1,
      "default": 0
    },
    {
      "input": "age_feature",
      "feature_name": "age_feature",
      "operation": {
        "target_object": "company_age",
        "operator": "LESS_THAN",
        "value": 5
      },
      "match": 1,
      "default": 0
    },
    {
      "input": "is_saas",
      "feature_name": "is_saas_feature",
      "operation": {
        "target_object": "description",
        "operator": "LLM",
        "value": "Based on the description, is this company a SaaA company?"
      },
      "match": 1,
      "default": 0
    }
  ]
}
```

#### The LLM operator
The `value` of the operation should be a `True` or `False` question related to the `target_object`


#### The `operation` Field

Each rule includes an `operation` block that describes how the condition(s) should be evaluated. There are two valid formats for this field:

##### 1. **Single Condition**

For simple rules with only one condition:

```json
"operation": {
  "target_object": "company_age",
  "operator": "LESS_THAN",
  "value": 5
}
```

This evaluates whether the company age is less than 5.

##### 2. **Compound Conditions with Boolean Operators**

For multiple conditions joined by `AND` or `OR`:

```json
"operation": {
  "AND": [
    {
      "target_object": "industry",
      "operator": "EQUALS",
      "value": "Technology"
    },
    {
      "target_object": "employee_growth_1y",
      "operator": "GREATER_THAN",
      "value": 0.1
    }
  ]
}
```

This evaluates whether both sub-conditions are true.

You can use either `AND` or `OR` as the top-level key, and its value must be a list of condition objects.

Each condition object supports the following structure:

* `target_object`: the field of the company being evaluated
* `operator`: a comparison operation (e.g., `EQUALS`, `LESS_THAN`, `GREATER_THAN`)
* `value`: the value to compare against


#### Response Format

```json
{
  "success": true,
  "message": "Rule created successfully",
  "rule": {
    "user_name": "User",
    "rules": [
      {
        "input": "noth_america_based",
        "feature_name": "noth_america_based",
        "match": 1,
        "default": 0,
        "boolean_operator": "OR",
        "conditions": [
          {
            "target_object": "headquarters_country",
            "operator": "EQUALS",
            "value": "Canada"
          },
          {
            "target_object": "headquarters_country",
            "operator": "EQUALS",
            "value": "USA"
          }
        ]
      },
      {
        "input": "age_feature",
        "feature_name": "age_feature",
        "match": 0,
        "default": 0,
        "boolean_operator": "N/A",
        "conditions": [
          {
            "target_object": "company_age",
            "operator": "LESS_THAN",
            "value": "5"
          }
        ]
      }
    ]
  }
}
```

The `conditions` array and `boolean_operator` summarize the logical structure of the rule that was created.

### `/process_companies` Endpoint

#### Description

`POST /process_companies`

This endpoint processes a list of companies for a specific user by applying all rules that belong to that user. The results are stored in the database and returned as part of the response.

Each rule evaluation determines whether a specific feature matches a given condition. The result for each feature is determined by the `match` or `default` value associated with the rule.


#### Request Format

##### URL

```
POST /process_companies
```

##### JSON Body

```json
{
  "user_name": "User",
  "urls": [
    "https://example.com",
    "https://anothercompany.com"
  ]
}
```

* `user_name` (string): The name of the user whose rules will be applied.
* `urls` (array of strings): A list of company URLs to process.

> **Note:** The user must exist, and the companies must have already been imported into the system.


#### Response Format

Returns a list of companies and the evaluation results of all rules for each company.

##### Example Response

```json
[
  {
    "company": "Example Corp",
    "noth_america_based": 1,
    "age_feature": 0
  },
  {
    "company": "AnotherCompany",
    "noth_america_based": 0,
    "age_feature": 1
  }
]
```

Each item in the response contains:

* `company`: The name of the company.
* One or more feature keys (as defined by `feature_name` in each rule): The value is either `match` or `default`, depending on whether the rule matched.


#### Additional Information

* For each rule applied to each company, a record is created in the `processed_features` table.
* The `last_processed_at` timestamp of the company is updated.

This ensures traceability and allows historical inspection of rule evaluations over time.



### `/create_user` Endpoint

#### Description

`POST /create_user`

This endpoint creates a new user in the system based on a unique `user_name`. If the user already exists, the existing user record is returned instead of creating a duplicate.

#### Request Format

##### URL

```
POST /create_user
```

##### JSON Body

```json
{
  "user_name": "User"
}
```

* **user\_name**: A unique string identifier for the user.

#### Behavior

* If a user with the given `user_name` already exists in the database, that user is returned.
* If the `user_name` is unique, a new user record is created and returned.


#### Response Format

##### Success Response

```json
{
  "id": "2e71b86e-1f64-4c5e-bac9-c7e1c26f3c0a",
  "user_name": "Larissa"
}
```

* **id**: The unique identifier of the user.
* **user\_name**: The name of the user as provided in the request.


#### Status Codes

* `201 Created`: A new user was successfully created.
* `200 OK`: The user already existed and was returned without creating a new one.
