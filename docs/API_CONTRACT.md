# API Contract Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication required. For production, implement API keys or JWT tokens.

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check service health status

**Response:** `200 OK`

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### 2. Analyze Text

**Endpoint:** `POST /api/v1/analyze`

**Description:** Analyze diary entry text and extract actions

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | integer | Yes | User ID (must be > 0) |
| text | string | Yes | Text to analyze (1-10000 chars) |
| date | string | No | Date in ISO format (YYYY-MM-DD) |

**Example Request:**

```json
{
  "user_id": 12345,
  "text": "Сходил в зал, пожал сотку, приготовил курочку, почитал книгу про математику",
  "date": "2025-11-10"
}
```

**Response:** `200 OK`

```json
{
  "user_id": 12345,
  "date": "2025-11-10",
  "raw_text": null,
  "actions": [
    {
      "category": "спорт",
      "subcategory": null,
      "action": "сходил в зал",
      "type": "activity",
      "estimated_time_minutes": 90,
      "time_source": "model",
      "confidence": 0.92,
      "achievement_weight": null,
      "points": 9.0
    },
    {
      "category": "спорт",
      "subcategory": "бодибилдинг",
      "action": "пожал сотку",
      "type": "achievement",
      "estimated_time_minutes": 5,
      "time_source": "model",
      "confidence": 0.85,
      "achievement_weight": 15,
      "points": 15.0
    },
    {
      "category": "готовка",
      "subcategory": null,
      "action": "приготовил курочку",
      "type": "activity",
      "estimated_time_minutes": 40,
      "time_source": "model",
      "confidence": 0.9,
      "achievement_weight": null,
      "points": 4.0
    },
    {
      "category": "учёба",
      "subcategory": "математика",
      "action": "почитал книгу про математику",
      "type": "activity",
      "estimated_time_minutes": 60,
      "time_source": "model",
      "confidence": 0.88,
      "achievement_weight": null,
      "points": 6.0
    }
  ],
  "meta": {
    "used_heuristics": [
      "keyword_match",
      "time_extraction",
      "category_detection"
    ],
    "used_llm": false,
    "llm_latency_ms": null,
    "heuristic_latency_ms": 120,
    "errors": []
  }
}
```

**Response Fields:**

#### Action Object

| Field | Type | Description |
|-------|------|-------------|
| category | string | Main category (спорт, учёба, готовка, работа, творчество, саморазвитие, социальное, дом) |
| subcategory | string\|null | Optional subcategory |
| action | string | Description of the action |
| type | string | "activity" or "achievement" |
| estimated_time_minutes | integer | Estimated time in minutes |
| time_source | string | "text", "history", "model", or "default" |
| confidence | float | Confidence score (0.0-1.0) |
| achievement_weight | integer\|null | Weight for achievements (5-25) |
| points | float | Calculated points |

#### Meta Object

| Field | Type | Description |
|-------|------|-------------|
| used_heuristics | array | List of heuristics used |
| used_llm | boolean | Whether LLM was called |
| llm_latency_ms | integer\|null | LLM processing time |
| heuristic_latency_ms | integer\|null | Heuristic processing time |
| errors | array | Any errors encountered |

**Error Responses:**

`422 Unprocessable Entity` - Validation error

```json
{
  "detail": [
    {
      "loc": ["body", "user_id"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

`500 Internal Server Error` - Processing error

```json
{
  "detail": "Analysis failed: <error message>"
}
```

---

### 3. Get User Statistics

**Endpoint:** `GET /api/v1/stats/{user_id}`

**Description:** Get statistics for a specific user

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | integer | User ID |

**Response:** `200 OK`

```json
{
  "user_id": 12345,
  "total_templates": 42,
  "total_actions": 156
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| user_id | integer | User ID |
| total_templates | integer | Number of unique action templates |
| total_actions | integer | Total number of recorded actions |

---

### 4. Clear Cache

**Endpoint:** `DELETE /api/v1/cache`

**Description:** Clear the cache (admin/testing purposes)

**Response:** `200 OK`

```json
{
  "status": "success",
  "message": "Cache cleared"
}
```

---

### 5. Prometheus Metrics

**Endpoint:** `GET /metrics`

**Description:** Prometheus metrics for monitoring

**Response:** `200 OK` (text/plain)

```
# HELP nlp_requests_total Total number of analysis requests
# TYPE nlp_requests_total counter
nlp_requests_total{user_id="12345"} 42.0
...
```

---

## Error Handling

All endpoints follow standard HTTP status codes:

- `200 OK`: Successful request
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

Error responses include a `detail` field with error information.

---

## Rate Limiting

Default rate limits (configurable):
- LLM calls: 60/minute, 1000/hour per service
- No per-user rate limits currently implemented

---

## Time Source Priority

When determining `estimated_time_minutes`:

1. **text**: Explicitly mentioned in text (e.g., "2 часа")
2. **history**: From user's historical data
3. **model**: From LLM/heuristic estimation
4. **default**: Fallback default value (10 minutes)

---

## Points Calculation

- **Activities**: `points = estimated_time_minutes / 10`
- **Achievements**: `points = achievement_weight` (5-25 based on significance)

---

## Categories

Supported categories:
- **спорт**: Sports and fitness activities
- **учёба**: Learning and education
- **готовка**: Cooking
- **работа**: Work-related activities
- **творчество**: Creative activities
- **саморазвитие**: Self-development
- **социальное**: Social activities
- **дом**: Household chores

Each category may have optional subcategories.
